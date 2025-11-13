"""
思维工坊API路由
提供RESTful接口用于多智能体协作讨论
"""

from typing import Any, Dict, List, Optional
import asyncio
import json

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel, Field

from api.thinking_workshop_service import get_workshop_service
from open_notebook.exceptions import DatabaseOperationError, NotFoundError

router = APIRouter()


# ============ 请求/响应模型 ============


class CreateSessionRequest(BaseModel):
    """Create session request"""

    notebook_id: str = Field(..., description="Notebook ID")
    mode: str = Field(
        ..., description="Thinking mode (dialectical_mode, brainstorm_mode)"
    )
    topic: str = Field(..., description="Discussion topic")
    context: Optional[Dict[str, Any]] = Field(None, description="Context information (optional)")


class AgentMessageResponse(BaseModel):
    """Agent消息响应"""

    agent_id: str
    agent_name: str
    content: str
    round_number: int
    timestamp: str
    message_type: str = "statement"
    references: List[str] = Field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    error: bool = False


class SessionResponse(BaseModel):
    """会话响应"""

    id: str = Field(..., description="会话ID")
    notebook_id: str = Field(..., description="笔记本ID")
    mode: str = Field(..., description="思维模式")
    topic: str = Field(..., description="讨论主题")
    status: str = Field(..., description="会话状态")
    messages: List[Dict[str, Any]] = Field(default_factory=list, description="消息列表")
    final_report: Optional[str] = Field(None, description="最终报告（Markdown格式）")
    created: Optional[str] = Field(None, description="创建时间")
    updated: Optional[str] = Field(None, description="更新时间")
    total_rounds: int = Field(0, description="总轮次")
    agent_count: int = Field(0, description="参与Agent数量")


class TemplateResponse(BaseModel):
    """模板响应"""

    mode_id: str = Field(..., description="模式ID")
    name: str = Field(..., description="模式名称")
    description: str = Field(..., description="模式描述")
    icon: str = Field(..., description="图标")
    agents: List[Dict[str, str]] = Field(..., description="Agent列表")
    use_cases: List[str] = Field(..., description="使用场景")
    estimated_time: str = Field(..., description="预计耗时")


class ReportResponse(BaseModel):
    """报告响应"""

    session_id: str = Field(..., description="会话ID")
    report: str = Field(..., description="报告内容（Markdown）")
    format: str = Field("markdown", description="报告格式")


class SuccessResponse(BaseModel):
    """成功响应"""

    success: bool = Field(True, description="操作是否成功")
    message: str = Field(..., description="消息")


# ============ API端点 ============


@router.get("/workshops/templates", response_model=List[TemplateResponse])
async def list_templates():
    """
    列出所有可用的思维工坊模板

    Returns:
        模板列表，包含模式信息和Agent配置
    """
    try:
        service = get_workshop_service()
        templates = service.list_templates()

        return [
            TemplateResponse(
                mode_id=t.mode_id,
                name=t.name,
                description=t.description,
                icon=t.icon,
                agents=t.agents,
                use_cases=t.use_cases,
                estimated_time=t.estimated_time,
            )
            for t in templates
        ]
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list templates: {str(e)}"
        )


@router.post("/workshops/sessions", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest, background_tasks: BackgroundTasks
):
    """
    创建新的思维工坊会话并在后台开始执行

    Args:
        request: 创建请求，包含笔记本ID、模式、主题等
        background_tasks: FastAPI后台任务

    Returns:
        会话信息（状态为created或in_progress）
    """
    try:
        service = get_workshop_service()

        # 创建会话
        session = await service.create_session(
            notebook_id=request.notebook_id,
            mode=request.mode,
            topic=request.topic,
            context=request.context,
        )

        # 在后台异步运行会话
        background_tasks.add_task(service.run_session, session.id)

        logger.info(f"Created and queued workshop session: {session.id}")

        return SessionResponse(**session.to_dict())

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseOperationError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating workshop session: {e}")
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        )


@router.get("/workshops/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """
    获取会话详情

    Args:
        session_id: 会话ID（可以带或不带workshop_session:前缀）

    Returns:
        会话详情，包含所有消息和状态
    """
    try:
        service = get_workshop_service()
        session = await service.get_session(session_id)

        return SessionResponse(**session.to_dict())

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseOperationError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching session {session_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/workshops/notebooks/{notebook_id}/sessions", response_model=List[SessionResponse]
)
async def list_notebook_sessions(
    notebook_id: str, limit: int = Query(50, description="返回结果数量限制")
):
    """
    列出笔记本的所有思维工坊会话

    Args:
        notebook_id: 笔记本ID
        limit: 最多返回的会话数量

    Returns:
        会话列表
    """
    try:
        service = get_workshop_service()
        sessions = await service.list_sessions(notebook_id, limit)

        return [SessionResponse(**s.to_dict()) for s in sessions]

    except DatabaseOperationError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing sessions for notebook {notebook_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        )


@router.delete("/workshops/sessions/{session_id}", response_model=SuccessResponse)
async def delete_session(session_id: str):
    """
    删除会话

    Args:
        session_id: 会话ID

    Returns:
        成功消息
    """
    try:
        service = get_workshop_service()
        await service.delete_session(session_id)

        return SuccessResponse(
            success=True, message=f"Session {session_id} deleted successfully"
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseOperationError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        )


@router.get("/workshops/sessions/{session_id}/report", response_model=ReportResponse)
async def get_session_report(session_id: str):
    """
    获取会话的最终报告（Markdown格式）

    Args:
        session_id: 会话ID

    Returns:
        Markdown格式的报告
    """
    try:
        service = get_workshop_service()
        session = await service.get_session(session_id)

        if not session.final_report:
            raise HTTPException(
                status_code=400,
                detail="Report not ready yet. Session may still be running.",
            )

        return ReportResponse(
            session_id=session.id or "",
            report=session.final_report,
            format="markdown",
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseOperationError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching report for session {session_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        )


@router.post("/workshops/sessions/stream")
async def create_and_stream_session(request: CreateSessionRequest):
    """
    Create and stream workshop session in real-time using Server-Sent Events (SSE)

    This endpoint:
    1. Creates a new session
    2. Immediately starts running it with streaming enabled
    3. Streams agent responses character-by-character via SSE

    Args:
        request: Session creation request

    Returns:
        SSE stream with events:
        - session_created: Initial session info
        - agent_start: Agent begins speaking
        - agent_chunk: Character/chunk from agent
        - agent_complete: Agent finished speaking
        - session_complete: All agents finished
        - error: If something goes wrong
    """
    try:
        service = get_workshop_service()

        # Create session
        session = await service.create_session(
            notebook_id=request.notebook_id,
            mode=request.mode,
            topic=request.topic,
            context=request.context,
        )

        logger.info(f"Created workshop session for streaming: {session.id}")

        async def event_generator():
            """Generate SSE events as the workshop runs"""
            # Create queue for events
            event_queue = asyncio.Queue()

            # Track current agent state
            current_agent_state = {
                'agent_id': None,
                'round': None,
                'content': ''
            }

            # Heartbeat task to prevent buffering
            async def heartbeat():
                """Send periodic keepalive comments to flush buffers"""
                logger.info("[HEARTBEAT] Task starting")
                try:
                    counter = 0
                    while True:
                        await asyncio.sleep(2)  # Send heartbeat every 2 seconds
                        counter += 1
                        logger.info(f"[HEARTBEAT] Sending keepalive #{counter}")
                        try:
                            event_queue.put_nowait({'type': 'heartbeat'})
                            logger.info(f"[HEARTBEAT] Keepalive #{counter} queued successfully")
                        except asyncio.QueueFull:
                            logger.warning(f"[HEARTBEAT] Queue full at #{counter}")
                except asyncio.CancelledError:
                    logger.info(f"[HEARTBEAT] Task cancelled after {counter} beats")
                    raise
                except Exception as e:
                    logger.error(f"[HEARTBEAT] Unexpected error: {e}")
                    raise

            try:
                logger.info(f"[SSE] Starting event generator for session {session.id}")
                # Send session created event
                yield f"event: session_created\ndata: {json.dumps({'session_id': session.id, 'status': 'in_progress'})}\n\n"
                logger.info(f"[SSE] Sent session_created event")

                # Stream callback - called for each chunk
                def stream_callback(agent_id: str, round_num: int, chunk: str):
                    # Check if new agent started
                    if agent_id != current_agent_state['agent_id'] or round_num != current_agent_state['round']:
                        # Send agent start event (use put_nowait for sync callback)
                        try:
                            event_queue.put_nowait({
                                'type': 'agent_start',
                                'agent_id': agent_id,
                                'round': round_num
                            })
                        except asyncio.QueueFull:
                            logger.warning("Event queue full, dropping agent_start event")
                        current_agent_state['agent_id'] = agent_id
                        current_agent_state['round'] = round_num
                        current_agent_state['content'] = ''

                    # Send chunk event (use put_nowait for sync callback)
                    current_agent_state['content'] += chunk
                    try:
                        event_queue.put_nowait({
                            'type': 'agent_chunk',
                            'agent_id': agent_id,
                            'round': round_num,
                            'chunk': chunk
                        })
                    except asyncio.QueueFull:
                        logger.warning("Event queue full, dropping chunk event")

                # Run the session with streaming in a background task
                async def run_workflow():
                    try:
                        logger.info(f"[SSE] Starting workflow execution for session {session.id}")
                        result = await service.run_session_streaming(
                            session_id=session.id,
                            stream_callback=stream_callback
                        )
                        logger.info(f"[SSE] Workflow execution completed for session {session.id}")
                        await event_queue.put({'type': 'session_complete', 'session_id': session.id})
                    except Exception as e:
                        logger.error(f"[SSE] Workflow execution error: {e}")
                        await event_queue.put({'type': 'error', 'error': str(e)})
                    finally:
                        await event_queue.put({'type': 'done'})

                # Start workflow in background
                logger.info(f"[SSE] Creating workflow task")
                workflow_task = asyncio.create_task(run_workflow())
                logger.info(f"[SSE] Workflow task created")

                # Start heartbeat task
                heartbeat_task = asyncio.create_task(heartbeat())
                logger.info(f"[SSE] Heartbeat task created, waiting for events")

                # Yield events from queue
                logger.info(f"[SSE] 开始从队列读取事件")
                while True:
                    event = await event_queue.get()

                    if event['type'] == 'heartbeat':
                        # Send SSE comment (ignored by browser but flushes buffers)
                        logger.debug("[SSE] Received heartbeat, sending keepalive")
                        yield ": keepalive\n\n"
                        continue

                    logger.info(f"[SSE] 收到事件: {event['type']}")

                    if event['type'] == 'done':
                        logger.info(f"[SSE] 收到 done 事件，结束流式传输")
                        heartbeat_task.cancel()  # Stop heartbeat
                        break
                    elif event['type'] == 'agent_start':
                        data = json.dumps({'agent_id': event['agent_id'], 'round': event['round']})
                        yield f"event: agent_start\ndata: {data}\n\n"
                        yield ": flush\n\n"  # Force flush immediately after
                        logger.info(f"[SSE] 发送 agent_start 事件")
                    elif event['type'] == 'agent_chunk':
                        data = json.dumps({'agent_id': event['agent_id'], 'round': event['round'], 'chunk': event['chunk']})
                        yield f"event: agent_chunk\ndata: {data}\n\n"
                        yield ": flush\n\n"  # Force flush immediately after
                        logger.debug(f"[SSE] 发送 agent_chunk 事件")
                    elif event['type'] == 'session_complete':
                        data = json.dumps({'session_id': event['session_id']})
                        yield f"event: session_complete\ndata: {data}\n\n"
                        yield ": flush\n\n"  # Force flush immediately after
                        logger.info(f"[SSE] 发送 session_complete 事件")
                    elif event['type'] == 'error':
                        data = json.dumps({'error': event['error']})
                        yield f"event: error\ndata: {data}\n\n"
                        yield ": flush\n\n"  # Force flush immediately after
                        logger.error(f"[SSE] 发送 error 事件: {event['error']}")

                # Wait for workflow to complete
                logger.info(f"[SSE] 等待 workflow 任务完成")
                await workflow_task
                logger.info(f"[SSE] Workflow 任务已完成")

            except Exception as e:
                logger.error(f"Error in SSE stream: {e}")
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating streaming session: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
