# 思维工坊 (Thinking Workshop)

多智能体协作思维系统,为Open Notebook提供辩证分析和头脑风暴功能。

## 概述

思维工坊允许用户召唤多个AI专家到笔记本中,从不同视角分析问题、激发创意、辅助决策。

## 核心模式

### 1. 辩证分析模式 (Dialectical Analysis)
**适用场景**: 论文评审、方案评估、优缺点分析

**参与Agent**:
- 👍 **支持者** (Supporter) - 发现优点和创新点
- 🔍 **批评者** (Critic) - 指出问题和不足
- ⚖️ **综合者** (Synthesizer) - 整合观点,给出建议

**工作流**: 顺序执行 (支持者 → 批评者 → 综合者)

### 2. 发散头脑风暴模式 (Divergent Brainstorming)
**适用场景**: 研究选题、创意生成、问题解决

**参与Agent**:
- 🚀 **愿景家** (Visionary) - 大胆创新,不受约束
- 🛠️ **实用主义者** (Pragmatist) - 评估可行性
- 🔮 **未来学家** (Futurist) - 关注前沿技术
- 🧩 **整合者** (Integrator) - 提炼Top3创意

**工作流**: 混合模式 (前三者并行发散 → 整合者综合)

## 架构设计

```
思维工坊
├── agent_profiles.yaml      # Agent配置(persona, prompts, temperature)
├── agent_manager.py          # 配置加载和管理
├── agent_executor.py         # 单个Agent的LLM调用
└── workflow_engine.py        # LangGraph工作流编排
```

### 核心组件

#### AgentConfig
Agent的完整配置,包括:
- 基本信息: id, name, role, persona
- UI元素: color, avatar
- LLM参数: temperature
- Prompts: system_prompt, user_prompt_template

#### WorkflowEngine
基于LangGraph的工作流引擎:
- 支持顺序工作流 (sequential)
- 支持混合工作流 (mixed - 并行+顺序)
- 管理Agent间的消息传递
- 生成结构化的最终报告

#### AgentExecutor
执行单个Agent:
- 复用项目的ModelManager
- 支持temperature控制
- 格式化前序消息作为上下文

## 使用示例

### 基础用法

```python
from open_notebook.thinking_workshop.workflow_engine import WorkflowEngine

# 创建工作流引擎
engine = WorkflowEngine("dialectical_mode")

# 准备上下文
context = {
    "title": "Attention Is All You Need",
    "abstract": "论文摘要...",
    "context": "这是一篇提出Transformer架构的论文"
}

# 运行讨论
result = await engine.run(
    topic="评审Transformer论文",
    context=context
)

# 获取结果
print(result["final_report"])  # Markdown格式的报告
print(result["messages"])       # 所有Agent的消息历史
```

### 头脑风暴示例

```python
engine = WorkflowEngine("brainstorm_mode")

context = {
    "background": "当前知识图谱功能已实现,但可视化不够直观"
}

result = await engine.run(
    topic="如何改进知识图谱的可视化?",
    context=context
)
```

## 技术集成

### 模型管理
复用Open Notebook的ModelManager:
```python
from open_notebook.config import get_model_manager

model_manager = get_model_manager()
llm = model_manager.provision_langchain_model()
```

### 工作流引擎
基于LangGraph的StateGraph:
```python
from langgraph.graph import StateGraph, END

workflow = StateGraph(WorkshopState)
workflow.add_node("agent_id", agent_function)
workflow.compile()
```

## 配置说明

### Agent配置 (agent_profiles.yaml)

```yaml
dialectical_mode:
  name: "辩证分析模式"
  agents:
    - id: supporter
      name: "支持者"
      temperature: 0.8
      system_prompt: |
        你的角色定义...
      user_prompt_template: |
        请评审: {title}
        {context}
```

### Temperature设置

- **1.0** - 最高创造力 (愿景家)
- **0.9** - 高创造力 (批评者)
- **0.8** - 中高创造力 (支持者)
- **0.75-0.85** - 中等创造力 (整合者、未来学家)
- **0.6-0.7** - 偏理性 (实用主义者、综合者)

## 扩展性

### 添加新模式

1. 在 `agent_profiles.yaml` 中定义新模式
2. 配置Agents和workflow
3. 工作流引擎会自动支持

### 自定义Agent

修改 `agent_profiles.yaml` 中的:
- `system_prompt`: Agent的角色定义
- `user_prompt_template`: 用户输入的模板
- `temperature`: 创造力参数

## 测试

运行完整测试:
```bash
cd /path/to/project
uv run python test_thinking_workshop_core.py
```

测试Agent配置加载:
```bash
uv run python -m open_notebook.thinking_workshop.agent_manager
```

## 开发路线图

### 阶段1: 核心引擎 ✅
- [x] Agent配置系统
- [x] Agent执行器
- [x] 工作流引擎
- [ ] 测试验证

### 阶段2: API集成 ⏳
- [ ] 领域模型 (WorkshopSession)
- [ ] 服务层 (ThinkingWorkshopService)
- [ ] REST API (POST/GET endpoints)

### 阶段3: 前端集成 ⏳
- [ ] 模板选择器
- [ ] 实时讨论展示
- [ ] 报告查看器

## 相关文档

- [开发计划](../../思维工坊开发计划.md) - 完整的开发计划和进度
- [当前进度](../../思维工坊_当前进度.md) - 最新进度摘要
- [项目文档](../../CLAUDE.md) - Open Notebook项目指南

## License

MIT License (继承自Open Notebook项目)
