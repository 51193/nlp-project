import os
import subprocess

from ai_prompter import Prompter
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from open_notebook.domain.notebook import Source
from open_notebook.domain.transformation import DefaultPrompts, Transformation
from open_notebook.graphs.utils import provision_langchain_model
from open_notebook.utils import clean_thinking_content
from open_notebook.utils.reliability_check import ReliabilityChecker
from open_notebook.utils.result_formatter import ResultFormatter
from open_notebook.utils.retry_manager import RetryManager


class TransformationState(TypedDict):
    input_text: str
    source: Source
    transformation: Transformation
    output: str
    response_language: str


async def run_transformation(state: dict, config: RunnableConfig) -> dict:
    source_obj = state.get("source")
    source: Source = source_obj if isinstance(source_obj, Source) else None  # type: ignore[assignment]
    content = state.get("input_text")
    assert source or content, "No content to transform"
    transformation: Transformation = state["transformation"]
    if not content:
        content = source.full_text
    transformation_template_text = transformation.prompt
    default_prompts: DefaultPrompts = DefaultPrompts(transformation_instructions=None)
    if default_prompts.transformation_instructions:
        transformation_template_text = f"{default_prompts.transformation_instructions}\n\n{transformation_template_text}"
    response_language = state.get("response_language")
    language_prompt = f"\n\n# LANGUAGE REQUIREMENT\nAlways respond in {response_language}. Do not use any other language."
    transformation_template_text = f"{transformation_template_text}{language_prompt}\n\n# INPUT"
    system_prompt = Prompter(template_text=transformation_template_text).render(
        data=state
    )
    content_str = str(content) if content else ""
    payload = [SystemMessage(content=system_prompt), HumanMessage(content=content_str)]
    chain = await provision_langchain_model(
        str(payload),
        config.get("configurable", {}).get("model_id"),
        "transformation",
        max_tokens=5055,
    )

    # response = await chain.ainvoke(payload)

    # Clean thinking content from the response
    # response_content = response.content if isinstance(response.content, str) else str(response.content)
    # cleaned_content = clean_thinking_content(response_content)

    #if source:
    #    await source.add_insight(transformation.title, cleaned_content)

    reliability_checker = ReliabilityChecker(max_retries=3)
    retry_manager = RetryManager(max_retries=3)

    async def generate_content():
        """生成内容的内部函数"""
        response = await chain.ainvoke(payload)
        response_content = response.content if isinstance(response.content, str) else str(response.content)
        return clean_thinking_content(response_content)

    async def check_content(transformation_prompt: str, original_content: str,
                            generated_result: str, config: dict):
        """检查内容的内部函数 - 修复参数签名"""
        return await reliability_checker.check_reliability(
            transformation_prompt=transformation_prompt,
            original_content=original_content,
            generated_result=generated_result,
            config=config
        )

    # 执行带可靠性检查的生成
    final_output, reliability_metrics = await retry_manager.generate_with_retry(
        generate_func=generate_content,
        check_func=check_content,
        generate_args={},
        check_extra_args={  # 使用新的参数名
            'transformation_prompt': transformation_template_text,
            'original_content': content_str,
            'config': config.get("configurable", {})
        }
    )

    # 格式化最终结果
    final_output_with_note = ResultFormatter.add_reliability_note(final_output, reliability_metrics)

    try:
        # 使用正确的路径
        python_exe = r'D:\mess\NLP\tts\.venv\Scripts\python.exe'
        script_path = r'D:\mess\NLP\tts\tts_runner.py'

        # 检查文件是否存在
        if not os.path.exists(python_exe):
            print(f"Python解释器不存在: {python_exe}")
        if not os.path.exists(script_path):
            print(f"TTS脚本不存在: {script_path}")

        text_to_speak = final_output_with_note.replace('"', '\\"')

        # 使用subprocess运行
        subprocess.run([
            python_exe,
            script_path,
            text_to_speak
        ])

    except Exception as e:
        print(f"TTS播放失败: {e}")

    # 调试信息（可选）
    if reliability_metrics.get('quality') == 'low':
        debug_info = ResultFormatter.get_detailed_debug_info(reliability_metrics)
        print(f"Low quality generation debug info:\n{debug_info}")

    # ... 原有的存储和返回代码 ...
    if source:
        insight_title = transformation.title
        if not reliability_metrics.get('reliable', True):
            insight_title = f"[需核查] {insight_title}"
        await source.add_insight(insight_title, final_output_with_note)

    return {
        #"output": cleaned_content,
        "output" : final_output_with_note,
    }


agent_state = StateGraph(TransformationState)
agent_state.add_node("agent", run_transformation)  # type: ignore[type-var]
agent_state.add_edge(START, "agent")
agent_state.add_edge("agent", END)
graph = agent_state.compile()
