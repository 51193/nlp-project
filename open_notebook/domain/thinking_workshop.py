"""
思维工坊领域模型
定义思维工坊会话和相关数据结构
"""

from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional

from loguru import logger
from pydantic import BaseModel, Field

from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.base import ObjectModel
from open_notebook.exceptions import DatabaseOperationError


class AgentMessage(BaseModel):
    """Agent消息"""

    agent_id: str
    agent_name: str
    content: str
    round_number: int
    timestamp: str
    message_type: str = "statement"  # statement, question, rebuttal, synthesis
    references: List[str] = Field(default_factory=list)  # 引用的来源
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)  # 工具调用记录
    error: bool = False


class WorkshopSession(ObjectModel):
    """思维工坊会话"""

    table_name: ClassVar[str] = "workshop_session"

    # 基础信息
    notebook_id: str
    mode: str  # dialectical_mode, brainstorm_mode
    topic: str

    # 状态
    status: str = "created"  # created, in_progress, completed, failed

    # 配置
    config: Dict[str, Any] = Field(default_factory=dict)

    # 上下文（传递给Agent的信息）
    context: Dict[str, Any] = Field(default_factory=dict)

    # 消息历史
    messages: List[Dict[str, Any]] = Field(default_factory=list)

    # 最终输出
    final_report: Optional[str] = None

    # 统计信息
    total_rounds: int = 0
    agent_count: int = 0

    def add_message(self, message: AgentMessage) -> None:
        """添加消息"""
        message_dict = {
            "agent_id": message.agent_id,
            "agent_name": message.agent_name,
            "content": message.content,
            "round_number": message.round_number,
            "timestamp": message.timestamp,
            "message_type": message.message_type,
            "references": message.references,
            "tool_calls": message.tool_calls,
            "error": message.error,
        }
        self.messages.append(message_dict)
        self.total_rounds = max(self.total_rounds, message.round_number)

    def set_status(self, status: str) -> None:
        """更新状态"""
        self.status = status

    def get_messages_by_agent(self, agent_id: str) -> List[Dict[str, Any]]:
        """获取特定Agent的所有消息"""
        return [msg for msg in self.messages if msg["agent_id"] == agent_id]

    def get_messages_by_round(self, round_number: int) -> List[Dict[str, Any]]:
        """获取特定轮次的所有消息"""
        return [msg for msg in self.messages if msg["round_number"] == round_number]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于API响应）"""
        return {
            "id": self.id,
            "notebook_id": self.notebook_id,
            "mode": self.mode,
            "topic": self.topic,
            "status": self.status,
            "config": self.config,
            "context": self.context,
            "messages": self.messages,
            "final_report": self.final_report,
            "created": self.created.isoformat() if self.created else None,
            "updated": self.updated.isoformat() if self.updated else None,
            "total_rounds": self.total_rounds,
            "agent_count": self.agent_count,
        }

    async def get_notebook(self) -> Optional["Notebook"]:
        """获取关联的笔记本"""
        try:
            from open_notebook.domain.notebook import Notebook

            return await Notebook.get(self.notebook_id)
        except Exception as e:
            logger.error(
                f"Error fetching notebook for session {self.id}: {str(e)}"
            )
            return None


class WorkshopTemplate(BaseModel):
    """工坊模板（用于前端展示可用模式）"""

    mode_id: str
    name: str
    description: str
    icon: str
    agents: List[Dict[str, str]]  # {id, name, role, avatar, color}
    use_cases: List[str]
    estimated_time: str  # "2-3分钟"
