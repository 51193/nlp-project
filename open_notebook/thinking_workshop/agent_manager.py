"""
Agent配置管理器
负责加载、解析和管理Agent配置
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import yaml
from pathlib import Path


@dataclass
class AgentConfig:
    """Agent配置"""
    id: str
    name: str
    role: str
    persona: str
    color: str
    avatar: str
    temperature: float
    system_prompt: str
    user_prompt_template: str
    tools: List[str] = None  # 工具ID列表,如 ["web_search", "calculator"]

    def __post_init__(self):
        """初始化后处理"""
        if self.tools is None:
            self.tools = []


@dataclass
class WorkflowStep:
    """工作流步骤"""
    agent: Optional[str] = None
    agents: Optional[List[str]] = None  # 用于并行步骤
    description: str = ""
    context: List[str] = None
    phase: Optional[str] = None
    parallel: bool = False


@dataclass
class ModeConfig:
    """模式配置"""
    name: str
    description: str
    agents: List[AgentConfig]
    workflow_type: str
    workflow_rounds: int
    workflow_steps: List[WorkflowStep]


class AgentManager:
    """Agent配置管理器"""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            # 默认配置文件路径
            config_path = Path(__file__).parent / "agent_profiles.yaml"

        self.config_path = Path(config_path)
        self.modes: Dict[str, ModeConfig] = {}
        self.load_config()

    def load_config(self):
        """加载配置文件"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        # 解析每个模式
        for mode_id, mode_data in config_data.items():
            self.modes[mode_id] = self._parse_mode(mode_id, mode_data)

    def _parse_mode(self, mode_id: str, mode_data: dict) -> ModeConfig:
        """解析模式配置"""
        # 解析Agents
        agents = []
        for agent_data in mode_data['agents']:
            agent = AgentConfig(
                id=agent_data['id'],
                name=agent_data['name'],
                role=agent_data['role'],
                persona=agent_data['persona'],
                color=agent_data['color'],
                avatar=agent_data['avatar'],
                temperature=agent_data['temperature'],
                system_prompt=agent_data['system_prompt'].strip(),
                user_prompt_template=agent_data['user_prompt_template'].strip(),
                tools=agent_data.get('tools', [])  # 解析工具列表,默认为空列表
            )
            agents.append(agent)

        # 解析Workflow
        workflow = mode_data['workflow']
        steps = []
        for step_data in workflow['steps']:
            step = WorkflowStep(
                agent=step_data.get('agent'),
                agents=step_data.get('agents'),
                description=step_data.get('description', ''),
                context=step_data.get('context', []),
                phase=step_data.get('phase'),
                parallel=step_data.get('parallel', False)
            )
            steps.append(step)

        return ModeConfig(
            name=mode_data['name'],
            description=mode_data['description'],
            agents=agents,
            workflow_type=workflow['type'],
            workflow_rounds=workflow['rounds'],
            workflow_steps=steps
        )

    def get_mode(self, mode_id: str) -> ModeConfig:
        """获取模式配置"""
        if mode_id not in self.modes:
            raise ValueError(f"Unknown mode: {mode_id}")
        return self.modes[mode_id]

    def get_agent(self, mode_id: str, agent_id: str) -> AgentConfig:
        """获取特定Agent配置"""
        mode = self.get_mode(mode_id)
        for agent in mode.agents:
            if agent.id == agent_id:
                return agent
        raise ValueError(f"Agent {agent_id} not found in mode {mode_id}")

    def list_modes(self) -> List[str]:
        """列出所有可用模式"""
        return list(self.modes.keys())


# 测试代码
if __name__ == "__main__":
    manager = AgentManager()

    # 测试加载
    print("可用模式:", manager.list_modes())

    # 测试辩证模式
    dialectical = manager.get_mode("dialectical_mode")
    print(f"\n模式: {dialectical.name}")
    print(f"描述: {dialectical.description}")
    print(f"Agents: {[a.name for a in dialectical.agents]}")

    # 测试获取特定Agent
    supporter = manager.get_agent("dialectical_mode", "supporter")
    print(f"\nAgent: {supporter.name}")
    print(f"角色: {supporter.role}")
    print(f"Prompt长度: {len(supporter.system_prompt)}")
