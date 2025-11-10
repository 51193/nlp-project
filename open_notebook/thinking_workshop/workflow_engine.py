"""
工作流引擎
基于LangGraph实现多Agent协作工作流
支持工具调用集成
"""

from typing import TypedDict, List, Dict, Any, Optional, Annotated
from typing_extensions import TypedDict as ExtTypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from open_notebook.thinking_workshop.agent_manager import AgentManager, ModeConfig
from open_notebook.thinking_workshop.agent_executor import AgentExecutor
from open_notebook.thinking_workshop.tools import WorkshopTools
from datetime import datetime
from loguru import logger


def merge_messages(left: List[Dict], right: List[Dict]) -> List[Dict]:
    """合并消息列表"""
    if not left:
        return right
    if not right:
        return left
    return left + right


def merge_available_messages(left: Dict[str, str], right: Dict[str, str]) -> Dict[str, str]:
    """合并可用消息字典"""
    if not left:
        return right
    if not right:
        return left
    result = left.copy()
    result.update(right)
    return result


class WorkshopState(ExtTypedDict):
    """工作流状态"""
    mode: str
    topic: str
    context: Dict[str, Any]
    current_round: int
    max_rounds: int

    # Agent消息历史 - 使用Annotated支持并发更新
    messages: Annotated[List[Dict[str, Any]], merge_messages]

    # 当前可用的消息 - 使用Annotated支持并发更新
    available_messages: Annotated[Dict[str, str], merge_available_messages]

    # 最终输出
    final_report: Optional[str]


class WorkflowEngine:
    """工作流引擎（支持工具调用）"""

    def __init__(self, mode_id: str, notebook_id: Optional[str] = None):
        """
        Initialize workflow engine

        Args:
            mode_id: Mode ID
            notebook_id: Notebook ID (optional, for notebook_reader tool to query database)
        """
        self.mode_id = mode_id
        self.agent_manager = AgentManager()
        self.mode_config = self.agent_manager.get_mode(mode_id)
        self.notebook_id = notebook_id

        # Create Agent executors (with tools)
        self.executors = {}
        for agent_config in self.mode_config.agents:
            # Get tools based on configuration
            tool_ids = agent_config.tools if agent_config.tools else []
            tools = WorkshopTools.get_tools_by_ids(tool_ids, notebook_id)

            # 创建执行器
            self.executors[agent_config.id] = AgentExecutor(
                agent_config=agent_config,
                tools=tools
            )

            logger.info(f"Agent {agent_config.id} 配置了 {len(tools)} 个工具: {tool_ids}")

        # 构建工作流
        self.workflow = self._build_workflow()

    def _build_workflow(self):
        """构建LangGraph工作流"""
        # 根据模式类型构建不同的拓扑
        if self.mode_config.workflow_type == "sequential":
            return self._build_sequential_workflow()
        elif self.mode_config.workflow_type == "mixed":
            return self._build_mixed_workflow()
        else:
            raise ValueError(f"Unknown workflow type: {self.mode_config.workflow_type}")

    def _build_sequential_workflow(self):
        """
        构建顺序工作流(用于辩证分析)

        支持多轮对话：
        - 循环agent: 前n-1个agent会循环执行rounds轮
        - 最终agent: 最后1个agent只在所有轮次结束后执行一次

        例如: supporter → critic → supporter → critic → ... → synthesizer
        """
        workflow = StateGraph(WorkshopState)
        steps = self.mode_config.workflow_steps

        # 区分循环agents和最终agent
        if len(steps) > 1:
            loop_steps = steps[:-1]  # 前n-1个步骤会循环
            final_step = steps[-1]   # 最后一个步骤只执行一次
        else:
            loop_steps = steps
            final_step = None

        # 为循环的Agents创建节点
        for step in loop_steps:
            agent_id = step.agent
            context_agents = step.context if step.context else []

            async def agent_node(state: WorkshopState, aid=agent_id, ctx=context_agents):
                return await self._execute_agent(state, aid, ctx)

            workflow.add_node(agent_id, agent_node)

        # 为最终Agent创建节点
        if final_step:
            final_id = final_step.agent
            final_context = final_step.context if final_step.context else []

            async def final_node(state: WorkshopState):
                return await self._execute_agent(state, final_id, final_context)

            workflow.add_node(final_id, final_node)

        # 创建轮次递增节点
        def increment_round(state: WorkshopState) -> dict:
            """递增轮次计数"""
            logger.info(f"完成Round {state['current_round']}, 准备下一轮")
            return {"current_round": state["current_round"] + 1}

        workflow.add_node("increment_round", increment_round)

        # 创建条件判断函数
        def should_continue(state: WorkshopState) -> str:
            """判断是否继续下一轮"""
            if state["current_round"] <= state["max_rounds"]:
                logger.info(f"继续下一轮 ({state['current_round']}/{state['max_rounds']})")
                return "continue"
            else:
                logger.info(f"完成所有轮次，进入最终总结")
                return "finish"

        # 连接节点
        workflow.set_entry_point(loop_steps[0].agent)

        # 循环部分的顺序连接
        for i in range(len(loop_steps) - 1):
            workflow.add_edge(loop_steps[i].agent, loop_steps[i+1].agent)

        # 最后一个循环agent连接到round递增节点
        workflow.add_edge(loop_steps[-1].agent, "increment_round")

        # 条件边：判断是否继续循环
        workflow.add_conditional_edges(
            "increment_round",
            should_continue,
            {
                "continue": loop_steps[0].agent,  # 继续下一轮，回到第一个agent
                "finish": final_step.agent if final_step else END  # 结束循环
            }
        )

        # 最终agent连接到结束
        if final_step:
            workflow.add_edge(final_step.agent, END)

        return workflow.compile()

    def _build_mixed_workflow(self):
        """构建混合工作流(用于头脑风暴)"""
        workflow = StateGraph(WorkshopState)

        # 找到发散和整合阶段
        diverge_step = None
        integrate_step = None

        for step in self.mode_config.workflow_steps:
            if step.phase == "diverge":
                diverge_step = step
            elif step.phase == "integrate":
                integrate_step = step

        if not diverge_step or not integrate_step:
            raise ValueError("Mixed workflow requires both diverge and integrate phases")

        # 创建一个空的开始节点作为唯一入口点
        async def start_node(state: WorkshopState):
            """初始化节点，直接返回state"""
            return state

        workflow.add_node("start", start_node)

        # 创建发散阶段的节点(并行执行的Agent)
        for agent_id in diverge_step.agents:
            async def diverge_node(state: WorkshopState, aid=agent_id):
                return await self._execute_agent(state, aid, [])

            workflow.add_node(agent_id, diverge_node)

        # 创建整合阶段的节点
        integrator_id = integrate_step.agents[0]
        context_agents = integrate_step.context if integrate_step.context else []

        async def integrate_node(state: WorkshopState):
            return await self._execute_agent(state, integrator_id, context_agents)

        workflow.add_node("integrate", integrate_node)

        # 连接节点
        # 设置唯一的入口点
        workflow.set_entry_point("start")

        # 从start节点并行分发到所有diverge节点
        for agent_id in diverge_step.agents:
            workflow.add_edge("start", agent_id)

        # 所有发散节点都连接到整合节点
        for agent_id in diverge_step.agents:
            workflow.add_edge(agent_id, "integrate")

        # 整合节点连接到结束
        workflow.add_edge("integrate", END)

        return workflow.compile()

    async def _execute_agent(
        self,
        state: WorkshopState,
        agent_id: str,
        context_agents: List[str]
    ) -> dict:
        """
        执行单个Agent（支持工具调用）

        重要：返回部分更新而不是整个state，以配合Annotated reducer正确合并
        """
        logger.info(f"[_execute_agent] 开始执行Agent: {agent_id}, Round: {state['current_round']}")

        # 获取执行器
        executor = self.executors[agent_id]
        logger.info(f"[_execute_agent] 获取到执行器: {agent_id}")

        # 准备前序消息
        previous_messages = {}
        if context_agents:
            for ctx_agent_id in context_agents:
                if ctx_agent_id in state["available_messages"]:
                    previous_messages[ctx_agent_id] = state["available_messages"][ctx_agent_id]
        logger.info(f"[_execute_agent] 前序消息准备完成，context_agents={context_agents}")

        # 准备流式回调（如果启用）
        stream_callback = None
        if hasattr(self, 'streaming') and self.streaming and hasattr(self, 'stream_callback'):
            # 创建带agent_id前缀的回调
            def agent_stream_callback(text: str):
                if self.stream_callback:
                    self.stream_callback(agent_id, state['current_round'], text)

            stream_callback = agent_stream_callback
            logger.info(f"[_execute_agent] 流式回调已配置")
        else:
            logger.info(f"[_execute_agent] 未配置流式回调，streaming={hasattr(self, 'streaming') and self.streaming}")

        # 执行（返回包含tool_calls的字典）
        try:
            logger.info(f"[_execute_agent] 准备调用 executor.execute()")
            result = await executor.execute(
                topic=state["topic"],
                context=state["context"],
                previous_messages=previous_messages,
                streaming=hasattr(self, 'streaming') and self.streaming,
                stream_callback=stream_callback
            )
            logger.info(f"[_execute_agent] executor.execute() 完成")

            # 创建新消息（包含工具调用记录）
            message = {
                "agent_id": agent_id,
                "content": result["content"],
                "tool_calls": result.get("tool_calls", []),  # 新增：工具调用记录
                "round": state["current_round"],
                "timestamp": datetime.now().isoformat()
            }

            logger.info(f"Agent {agent_id} 完成，响应长度: {len(result['content'])}, "
                       f"工具调用: {len(result.get('tool_calls', []))}次")

            # 如果有流式回调，发送完整消息（批量模式）
            if hasattr(self, 'streaming') and self.streaming and hasattr(self, 'stream_callback') and self.stream_callback:
                logger.info(f"[_execute_agent] 发送批量消息到流式回调")
                # 发送完整内容作为一个大块
                if result["content"]:
                    self.stream_callback(agent_id, state['current_round'], result["content"])

            # 只返回新增的部分，而不是整个state
            # Annotated reducer会自动合并
            return {
                "messages": [message],  # 只包含新消息
                "available_messages": {agent_id: result["content"]}  # 只包含当前agent的消息内容
            }

        except Exception as e:
            logger.error(f"Agent {agent_id} 执行失败: {e}")
            # 返回错误消息
            return {
                "messages": [{
                    "agent_id": agent_id,
                    "content": f"[Error] {str(e)}",
                    "tool_calls": [],
                    "round": state["current_round"],
                    "timestamp": datetime.now().isoformat(),
                    "error": True
                }],
                "available_messages": {}
            }

    async def run(
        self,
        topic: str,
        context: Dict[str, Any],
        streaming: bool = True,  # 默认启用流式输出
        stream_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        运行工作流

        Args:
            topic: 讨论主题
            context: 上下文(title, abstract等)
            streaming: 是否启用流式输出（默认True）
            stream_callback: 流式输出回调函数

        Returns:
            包含所有消息和最终报告的字典
        """
        logger.info(f"[WorkflowEngine.run] 开始执行，streaming={streaming}")

        # 保存流式配置到实例变量
        self.streaming = streaming
        self.stream_callback = stream_callback
        logger.info(f"[WorkflowEngine.run] 流式配置已保存")

        # 初始化状态
        initial_state: WorkshopState = {
            "mode": self.mode_id,
            "topic": topic,
            "context": context,
            "current_round": 1,
            "max_rounds": self.mode_config.workflow_rounds,
            "messages": [],
            "available_messages": {},
            "final_report": None
        }
        logger.info(f"[WorkflowEngine.run] 初始状态已创建，max_rounds={self.mode_config.workflow_rounds}")

        # 运行工作流
        logger.info(f"[WorkflowEngine.run] 准备调用 workflow.ainvoke()，mode={self.mode_id}")
        try:
            final_state = await self.workflow.ainvoke(initial_state)
            logger.info(f"[WorkflowEngine.run] workflow.ainvoke() 完成")
        except Exception as e:
            logger.error(f"[WorkflowEngine.run] workflow.ainvoke() 失败: {e}")
            logger.exception(e)
            raise

        # 生成最终报告
        logger.info(f"[WorkflowEngine.run] 准备生成最终报告")
        final_state["final_report"] = self._generate_report(final_state)

        logger.info(f"[WorkflowEngine.run] 工作流完成,共{len(final_state['messages'])}条消息")

        return final_state

    def _format_tool_output_summary(self, tool_call: dict) -> str:
        """Format tool output as a short summary (like frontend)"""
        tool_name = tool_call.get('tool', 'unknown')
        output = str(tool_call.get('output', ''))

        # notebook_reader: Show document names only
        if tool_name == 'notebook_reader' and 'Complete Notebook Content' in output:
            import re
            sources_match = re.search(r'This notebook contains (\d+) sources? and (\d+) notes?', output)
            if sources_match:
                sources_count = sources_match.group(1)
                notes_count = sources_match.group(2)

                # Extract source titles
                source_titles = re.findall(r'### Source \d+: (.+)\n', output)

                summary = f"Read {sources_count} source(s) and {notes_count} note(s)"
                if source_titles:
                    summary += f" ({', '.join(source_titles[:3])}"
                    if len(source_titles) > 3:
                        summary += f" and {len(source_titles) - 3} more"
                    summary += ")"
                return summary

        # tavily_search / web_search: Show result count and top result
        try:
            import json
            parsed = json.loads(output)
            if 'results' in parsed and isinstance(parsed['results'], list):
                result_count = len(parsed['results'])
                first_title = parsed['results'][0].get('title', 'No title') if parsed['results'] else 'No results'
                first_url = parsed['results'][0].get('url', '') if parsed['results'] else ''
                return f"Found {result_count} web results. Top: \"{first_title[:50]}\" ({first_url})"
        except:
            pass

        # Default: Truncate to 150 chars
        if len(output) <= 150:
            return output
        return output[:150] + "..."

    def _generate_report(self, state: WorkshopState) -> str:
        """Generate final report (concise format without full tool outputs)"""
        report_lines = []

        # Title section
        report_lines.append("=" * 80)
        report_lines.append(f"  {self.mode_config.name} - Discussion Report")
        report_lines.append("=" * 80)
        report_lines.append("")
        report_lines.append(f"📌 Topic: {state['topic']}")
        report_lines.append(f"📝 Mode: {self.mode_config.description}")

        if state['messages']:
            report_lines.append(f"⏰ Time: {state['messages'][0]['timestamp']}")

        report_lines.append(f"🔄 Rounds: {state['max_rounds']} rounds")
        report_lines.append(f"💬 Messages: {len([m for m in state['messages'] if not m.get('error')])} messages")
        report_lines.append("")
        report_lines.append("=" * 80)

        # 按Agent组织消息（显示所有轮次）
        for agent_config in self.mode_config.agents:
            agent_id = agent_config.id
            agent_messages = [
                msg for msg in state["messages"]
                if msg["agent_id"] == agent_id and not msg.get("error")
            ]

            if agent_messages:
                report_lines.append("")
                report_lines.append(f"## {agent_config.avatar} {agent_config.name}")
                report_lines.append("")

                # 按轮次组织
                for round_num in range(1, state['max_rounds'] + 2):  # +2包括最后的synthesizer
                    round_messages = [m for m in agent_messages if m['round'] == round_num]
                    if round_messages:
                        if len(agent_messages) > 1:  # 如果有多轮，显示轮次
                            report_lines.append(f"### Round {round_num}")
                            report_lines.append("")

                        for msg in round_messages:
                            # Display tool calls summary (if any) - SHORT VERSION with better formatting
                            if msg.get("tool_calls"):
                                report_lines.append("**🔧 Tools Used:**")
                                report_lines.append("")
                                for i, tool_call in enumerate(msg["tool_calls"], 1):
                                    tool_name = tool_call.get('tool', 'unknown')
                                    summary = self._format_tool_output_summary(tool_call)
                                    report_lines.append(f"- **{tool_name}**: {summary}")
                                report_lines.append("")

                            # Display agent response content
                            report_lines.append("**💬 Response:**")
                            report_lines.append("")
                            content = msg['content']
                            report_lines.append(content)
                            report_lines.append("")

        report_lines.append("=" * 80)
        report_lines.append("📊 Report Generated Successfully")
        report_lines.append("=" * 80)

        return "\n".join(report_lines)


# 测试代码
if __name__ == "__main__":
    import asyncio

    async def test_dialectical():
        """测试辩证分析模式"""
        engine = WorkflowEngine("dialectical_mode")

        context = {
            "title": "Attention Is All You Need",
            "abstract": "提出了Transformer架构,完全基于注意力机制...",
            "context": "这是一篇2017年的论文,提出了Transformer架构。"
        }

        result = await engine.run(
            topic="评审Transformer论文",
            context=context
        )

        print("=" * 80)
        print("辩证分析结果:")
        print("=" * 80)
        print(result["final_report"])
        print("\n消息数量:", len(result["messages"]))

    async def test_brainstorm():
        """测试头脑风暴模式"""
        engine = WorkflowEngine("brainstorm_mode")

        context = {
            "background": "知识图谱已实现基础功能,但可视化不够直观"
        }

        result = await engine.run(
            topic="如何改进知识图谱的可视化?",
            context=context
        )

        print("=" * 80)
        print("头脑风暴结果:")
        print("=" * 80)
        print(result["final_report"])

    # 运行测试
    print("测试1: 辩证分析模式")
    asyncio.run(test_dialectical())

    print("\n\n测试2: 头脑风暴模式")
    asyncio.run(test_brainstorm())
