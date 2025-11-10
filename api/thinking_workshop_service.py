"""
思维工坊服务层
提供业务逻辑和工作流协调
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from open_notebook.domain.notebook import Notebook
from open_notebook.domain.thinking_workshop import (
    AgentMessage,
    WorkshopSession,
    WorkshopTemplate,
)
from open_notebook.exceptions import DatabaseOperationError, NotFoundError
from open_notebook.thinking_workshop.agent_manager import AgentManager
from open_notebook.thinking_workshop.workflow_engine import WorkflowEngine


class ThinkingWorkshopService:
    """思维工坊服务"""

    def __init__(self):
        self.agent_manager = AgentManager()
        logger.info("ThinkingWorkshopService initialized")

    async def create_session(
        self,
        notebook_id: str,
        mode: str,
        topic: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> WorkshopSession:
        """
        Create thinking workshop session

        Args:
            notebook_id: Notebook ID
            mode: Mode ID (dialectical_mode, brainstorm_mode)
            topic: Discussion topic
            context: Context information

        Returns:
            WorkshopSession object
        """
        try:
            # Verify notebook exists
            notebook = await Notebook.get(notebook_id)
            if not notebook:
                raise NotFoundError(f"Notebook not found: {notebook_id}")

            # Verify mode
            try:
                mode_config = self.agent_manager.get_mode(mode)
            except ValueError as e:
                raise ValueError(f"Invalid mode: {mode}. Available modes: {self.agent_manager.list_modes()}")

            # Create session
            session = WorkshopSession(
                notebook_id=notebook_id,
                mode=mode,
                topic=topic,
                context=context or {},
                agent_count=len(mode_config.agents),
                status="created",
            )

            # Save to database
            await session.save()

            logger.info(
                f"Created workshop session: {session.id}, mode: {mode}, topic: {topic}, notebook: {notebook_id}"
            )
            return session

        except NotFoundError:
            raise
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error creating workshop session: {e}")
            raise DatabaseOperationError(f"Failed to create session: {str(e)}")

    async def run_session_streaming(
        self,
        session_id: str,
        stream_callback: Optional[callable] = None
    ) -> WorkshopSession:
        """
        Run workshop session with streaming support

        Args:
            session_id: Session ID
            stream_callback: Callback function(agent_id, round, chunk) for streaming

        Returns:
            Completed WorkshopSession
        """
        try:
            # Load session
            session = await WorkshopSession.get(session_id)
            if not session:
                raise NotFoundError(f"Session not found: {session_id}")

            # Check session status
            if session.status == "completed":
                logger.warning(f"Session {session_id} already completed")
                return session

            # Update status
            session.set_status("in_progress")
            await session.save()

            logger.info(f"Running workshop session with streaming: {session_id}, mode: {session.mode}")

            # Get notebook_id from session
            notebook_id = session.notebook_id
            logger.info(f"[Workshop] Notebook ID: {notebook_id}")

            # Create workflow engine with notebook_id and streaming
            logger.info(f"[Workshop] Creating WorkflowEngine for mode: {session.mode}")
            from open_notebook.thinking_workshop.workflow_engine import WorkflowEngine

            try:
                engine = WorkflowEngine(
                    mode_id=session.mode,
                    notebook_id=notebook_id,
                )
                logger.info(f"[Workshop] WorkflowEngine created successfully")
            except Exception as e:
                logger.error(f"[Workshop] Failed to create WorkflowEngine: {e}")
                raise

            # Run workflow with streaming enabled
            logger.info(f"[Workshop] Starting workflow execution with streaming")
            try:
                result = await engine.run(
                    topic=session.topic,
                    context=session.context,
                    streaming=True,
                    stream_callback=stream_callback
                )
                logger.info(f"[Workshop] Workflow execution completed")
            except Exception as e:
                logger.error(f"[Workshop] Workflow execution failed: {e}")
                logger.exception(e)
                raise

            # Update session - add messages
            for msg_data in result["messages"]:
                # Get agent name
                agent_name = self._get_agent_name(session.mode, msg_data["agent_id"])

                # Extract tool calls
                tool_calls = msg_data.get("tool_calls", [])

                message = AgentMessage(
                    agent_id=msg_data["agent_id"],
                    agent_name=agent_name,
                    content=msg_data["content"],
                    round_number=msg_data["round"],
                    timestamp=msg_data["timestamp"],
                    tool_calls=tool_calls,
                    error=msg_data.get("error", False),
                )
                session.add_message(message)

            # Update final report and status
            session.final_report = result.get("final_report")
            session.set_status("completed")

            await session.save()

            logger.info(
                f"Workshop session completed: {session_id}, "
                f"messages: {len(session.messages)}, "
                f"rounds: {session.total_rounds}"
            )

            return session

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error running workshop session {session_id}: {e}")
            # Mark session as failed
            try:
                session = await WorkshopSession.get(session_id)
                if session:
                    session.set_status("failed")
                    await session.save()
            except:
                pass
            raise DatabaseOperationError(f"Failed to run session: {str(e)}")

    async def run_session(self, session_id: str) -> WorkshopSession:
        """
        运行思维工坊会话

        Args:
            session_id: 会话ID

        Returns:
            完成后的WorkshopSession
        """
        try:
            # 加载会话
            session = await WorkshopSession.get(session_id)
            if not session:
                raise NotFoundError(f"Session not found: {session_id}")

            # 检查会话状态
            if session.status == "completed":
                logger.warning(f"Session {session_id} already completed")
                return session

            # 更新状态
            session.set_status("in_progress")
            await session.save()

            logger.info(f"Running workshop session: {session_id}, mode: {session.mode}")

            # Get notebook_id from session
            notebook_id = session.notebook_id

            # Debug logging
            logger.info(f"[Workshop] Notebook ID: {notebook_id}")

            # Create workflow engine with notebook_id
            # The notebook_reader tool will query the database directly
            engine = WorkflowEngine(
                mode_id=session.mode,
                notebook_id=notebook_id,
            )

            # 运行工作流
            result = await engine.run(
                topic=session.topic,
                context=session.context,
            )

            # 更新会话 - 添加消息
            for msg_data in result["messages"]:
                # 获取agent名称
                agent_name = self._get_agent_name(session.mode, msg_data["agent_id"])

                # 提取工具调用记录（如果有）
                tool_calls = msg_data.get("tool_calls", [])

                message = AgentMessage(
                    agent_id=msg_data["agent_id"],
                    agent_name=agent_name,
                    content=msg_data["content"],
                    round_number=msg_data["round"],
                    timestamp=msg_data["timestamp"],
                    tool_calls=tool_calls,
                    error=msg_data.get("error", False),
                )
                session.add_message(message)

            # 更新最终报告和状态
            session.final_report = result.get("final_report")
            session.set_status("completed")

            await session.save()

            logger.info(
                f"Workshop session completed: {session_id}, "
                f"messages: {len(session.messages)}, "
                f"rounds: {session.total_rounds}"
            )

            return session

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error running workshop session {session_id}: {e}")
            # 标记会话为失败
            try:
                session = await WorkshopSession.get(session_id)
                if session:
                    session.set_status("failed")
                    await session.save()
            except:
                pass
            raise DatabaseOperationError(f"Failed to run session: {str(e)}")

    def _get_agent_name(self, mode: str, agent_id: str) -> str:
        """获取Agent名称"""
        try:
            agent_config = self.agent_manager.get_agent(mode, agent_id)
            return agent_config.name
        except Exception:
            return agent_id

    async def get_session(self, session_id: str) -> WorkshopSession:
        """获取会话"""
        try:
            # 确保session_id有正确的表前缀
            if not session_id.startswith("workshop_session:"):
                session_id = f"workshop_session:{session_id}"

            session = await WorkshopSession.get(session_id)
            if not session:
                raise NotFoundError(f"Session not found: {session_id}")
            return session
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error fetching session {session_id}: {e}")
            raise DatabaseOperationError(f"Failed to get session: {str(e)}")

    async def list_sessions(
        self, notebook_id: str, limit: int = 50
    ) -> List[WorkshopSession]:
        """列出笔记本的所有会话"""
        try:
            from open_notebook.database.repository import repo_query

            # 查询该笔记本的所有会话
            query = """
                SELECT * FROM workshop_session
                WHERE notebook_id = $notebook_id
                ORDER BY created DESC
                LIMIT $limit
            """
            results = await repo_query(
                query, {"notebook_id": notebook_id, "limit": limit}
            )

            sessions = []
            for result in results:
                try:
                    session = WorkshopSession(**result)
                    sessions.append(session)
                except Exception as e:
                    logger.error(f"Error parsing session: {e}")
                    continue

            return sessions
        except Exception as e:
            logger.error(f"Error listing sessions for notebook {notebook_id}: {e}")
            raise DatabaseOperationError(f"Failed to list sessions: {str(e)}")

    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        try:
            session = await self.get_session(session_id)
            await session.delete()
            logger.info(f"Deleted workshop session: {session_id}")
            return True
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            raise DatabaseOperationError(f"Failed to delete session: {str(e)}")

    def list_templates(self) -> List[WorkshopTemplate]:
        """列出所有可用模板"""
        try:
            templates = []

            for mode_id in self.agent_manager.list_modes():
                mode_config = self.agent_manager.get_mode(mode_id)

                # 构建Agent列表
                agents = []
                for agent_config in mode_config.agents:
                    agents.append(
                        {
                            "id": agent_config.id,
                            "name": agent_config.name,
                            "role": agent_config.role,
                            "avatar": agent_config.avatar,
                            "color": agent_config.color,
                            "persona": agent_config.persona,
                        }
                    )

                # 确定用例和时间
                if mode_id == "dialectical_mode":
                    use_cases = ["Paper Review", "Program Evaluation", "Pros and Cons"]
                    estimated_time = "2-3min"
                    icon = "⚖"
                elif mode_id == "brainstorm_mode":
                    use_cases = ["Topic Selection", "Idea Generation" "Brainstorming"]
                    estimated_time = "3-5min"
                    icon = "💡"
                else:
                    use_cases = []
                    estimated_time = "unknown"
                    icon = "🤔"

                template = WorkshopTemplate(
                    mode_id=mode_id,
                    name=mode_config.name,
                    description=mode_config.description,
                    icon=icon,
                    agents=agents,
                    use_cases=use_cases,
                    estimated_time=estimated_time,
                )
                templates.append(template)

            logger.info(f"Listed {len(templates)} workshop templates")
            return templates

        except Exception as e:
            logger.error(f"Error listing templates: {e}")
            raise DatabaseOperationError(f"Failed to list templates: {str(e)}")


# 全局服务实例
_service: Optional[ThinkingWorkshopService] = None


def get_workshop_service() -> ThinkingWorkshopService:
    """获取服务单例"""
    global _service
    if _service is None:
        _service = ThinkingWorkshopService()
    return _service
