import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from loguru import logger

from open_notebook.domain.models import model_manager


router = APIRouter()

ALLOWED_MIME_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/ogg",
    "audio/webm",
    "audio/mp4",
    "audio/aac",
    "audio/flac",
}
MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25 MB


class AudioTranscriptionResponse(BaseModel):
    text: str = Field(..., description="转写后的文本内容")
    language: Optional[str] = Field(None, description="模型推断或指定的语言")
    raw_response: Optional[Dict[str, Any]] = Field(
        default=None, description="底层模型返回的原始结果（调试用途）"
    )


async def _call_transcribe(model: Any, file_path: str, **kwargs) -> Any:
    """
    Call the best-available transcription method on the speech-to-text model.
    Supports sync/async `transcribe` or `atranscribe` implementations.
    """
    transcribe_fn = None

    if hasattr(model, "atranscribe"):
        transcribe_fn = getattr(model, "atranscribe")
        if asyncio.iscoroutinefunction(transcribe_fn):
            return await transcribe_fn(file_path, **kwargs)
        return transcribe_fn(file_path, **kwargs)

    if hasattr(model, "transcribe"):
        transcribe_fn = getattr(model, "transcribe")
        if asyncio.iscoroutinefunction(transcribe_fn):
            return await transcribe_fn(file_path, **kwargs)
        return transcribe_fn(file_path, **kwargs)

    raise RuntimeError("当前语音模型不支持 transcribe 调用")


def _extract_text(result: Any) -> str:
    """
    Attempt to extract the first non-empty string from common STT responses,
    including SDK response objects, nested dict/list structures, etc.
    """

    prioritized_attrs = (
        "text",
        "transcript",
        "transcription",
        "output",
        "content",
        "result",
    )

    def _search(value: Any) -> Optional[str]:
        if value is None:
            return None

        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None

        # Objects with common attributes (e.g., SDK models)
        for attr in prioritized_attrs:
            if hasattr(value, attr):
                found = _search(getattr(value, attr))
                if found:
                    return found

        # Dataclass / custom objects
        if hasattr(value, "__dict__"):
            found = _search(vars(value))
            if found:
                return found

        if isinstance(value, dict):
            for key in prioritized_attrs:
                if key in value:
                    found = _search(value[key])
                    if found:
                        return found
            for nested in value.values():
                found = _search(nested)
                if found:
                    return found

        if isinstance(value, (list, tuple)):
            for item in value:
                found = _search(item)
                if found:
                    return found

        return None

    extracted = _search(result)
    if extracted:
        return extracted

    logger.warning("语音模型返回内容无法解析文本: {}", result)
    raise ValueError("语音模型未返回可用文本")


@router.post("/audio/transcriptions", response_model=AudioTranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(..., description="要转写的音频文件"),
    language: Optional[str] = Form(
        default=None, description="传递给模型的语言提示，如 zh、en"
    ),
    prompt: Optional[str] = Form(
        default=None, description="可选提示词，帮助模型更好地识别"
    ),
):
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="不支持的音频格式")

    try:
        stt_model = await model_manager.get_speech_to_text()
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(f"加载语音模型失败: {exc}")
        raise HTTPException(status_code=500, detail="语音模型初始化失败")

    if not stt_model:
        raise HTTPException(status_code=400, detail="尚未配置默认语音转文字模型")

    suffix = Path(file.filename or "audio").suffix or ".webm"
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp_path = temp_file.name
    total_bytes = 0

    try:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > MAX_AUDIO_BYTES:
                raise HTTPException(status_code=400, detail="音频文件过大，最大支持 25MB")
            temp_file.write(chunk)
        temp_file.flush()
        temp_file.close()

        kwargs: Dict[str, Any] = {}
        if language:
            kwargs["language"] = language
        if prompt:
            kwargs["prompt"] = prompt

        logger.info(
            "开始语音转写: file=%s size=%s language=%s",
            file.filename,
            total_bytes,
            language,
        )

        raw_result = await _call_transcribe(stt_model, temp_path, **kwargs)
        text = _extract_text(raw_result)

        return AudioTranscriptionResponse(
            text=text, language=language, raw_response=raw_result if isinstance(raw_result, dict) else None
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"语音转写失败: {exc}")
        raise HTTPException(status_code=500, detail="语音转写失败，请稍后重试")
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass

