"""
Agent执行器
负责单个Agent的LLM调用和响应生成
支持工具调用（Tool Calling）
"""

from typing import Dict, Any, Optional, Callable, AsyncIterator, List
from open_notebook.graphs.utils import provision_langchain_model
from open_notebook.thinking_workshop.agent_manager import AgentConfig
from langchain_core.tools import BaseTool
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger


class AgentExecutor:
    """Agent执行器（支持工具调用）"""

    def __init__(self, agent_config: AgentConfig, tools: List[BaseTool] = None):
        """
        初始化Agent执行器

        Args:
            agent_config: Agent配置
            tools: 工具列表（可选）
        """
        self.config = agent_config
        self.tools = tools or []
        self.has_tools = len(self.tools) > 0

        if self.has_tools:
            logger.info(f"Agent {self.config.id} 配置了 {len(self.tools)} 个工具: "
                       f"{[t.name for t in self.tools]}")

    async def execute(
        self,
        topic: str,
        context: Dict[str, Any],
        previous_messages: Optional[Dict[str, str]] = None,
        streaming: bool = False,
        stream_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        执行Agent生成响应

        Args:
            topic: 讨论主题
            context: 上下文信息(标题、摘要等)
            previous_messages: 之前Agent的发言 {agent_id: message}
            streaming: 是否使用流式输出
            stream_callback: 流式输出回调函数

        Returns:
            包含响应内容和工具调用记录的字典:
            {
                "content": "Agent响应内容",
                "tool_calls": [
                    {
                        "tool": "web_search",
                        "input": "查询内容",
                        "output": "搜索结果"
                    }
                ]
            }
        """
        logger.info(f"[AgentExecutor.execute] 开始执行，agent={self.config.id}, streaming={streaming}, has_tools={self.has_tools}")

        # 1. 构建system prompt
        system_prompt = self.config.system_prompt
        logger.info(f"[AgentExecutor.execute] System prompt 已构建，长度={len(system_prompt)}")

        # 2. 构建user prompt
        logger.info(f"[AgentExecutor.execute] 准备构建 user prompt")
        user_prompt = self._build_user_prompt(topic, context, previous_messages)
        logger.info(f"[AgentExecutor.execute] User prompt 已构建，长度={len(user_prompt)}")

        # 3. 调用LLM（带或不带工具）
        try:
            if self.has_tools:
                # 使用Tool Calling Agent
                # 注意：工具调用模式暂不支持真正的流式输出，因为需要等待工具执行完成
                logger.info(f"[AgentExecutor.execute] 使用工具调用模式，工具数量={len(self.tools)}")
                logger.info(f"[AgentExecutor.execute] 工具调用模式暂不支持流式输出，使用批量模式")
                result = await self._execute_with_tools(
                    system_prompt, user_prompt, streaming=False, stream_callback=None
                )
            else:
                # 原有逻辑：直接LLM调用
                logger.info(f"[AgentExecutor.execute] 使用直接LLM调用模式")
                if streaming:
                    logger.info(f"[AgentExecutor.execute] 调用 _call_llm_streaming()")
                    content = await self._call_llm_streaming(
                        system_prompt, user_prompt, stream_callback
                    )
                else:
                    logger.info(f"[AgentExecutor.execute] 调用 _call_llm()")
                    content = await self._call_llm(system_prompt, user_prompt)
                result = {"content": content, "tool_calls": []}

            logger.info(f"[AgentExecutor.execute] Agent {self.config.id} 生成响应: {len(result['content'])} 字符, "
                       f"{len(result.get('tool_calls', []))} 次工具调用")
            return result

        except Exception as e:
            logger.error(f"[AgentExecutor.execute] Agent {self.config.id} 执行失败: {e}")
            logger.exception(e)
            raise

    def _build_user_prompt(
        self,
        topic: str,
        context: Dict[str, Any],
        previous_messages: Optional[Dict[str, str]]
    ) -> str:
        """构建用户提示词"""
        # 基础变量
        template_vars = {
            "topic": topic,
            **context  # title, abstract, etc.
        }

        # 添加前序Agent的发言
        if previous_messages:
            # 将之前的发言格式化
            formatted_previous = self._format_previous_messages(previous_messages)
            template_vars.update(formatted_previous)
        else:
            # 第一轮没有前序消息，填充空字符串（这是正常情况，不需要警告）
            template_vars["previous_opinions"] = ""
            template_vars["supporter_opinion"] = ""
            template_vars["critic_opinion"] = ""
            template_vars["visionary_ideas"] = ""
            template_vars["pragmatist_ideas"] = ""
            template_vars["futurist_ideas"] = ""

        # 使用模板生成
        try:
            user_prompt = self.config.user_prompt_template.format(**template_vars)
        except KeyError as e:
            # 如果某些变量缺失,填充空字符串
            # 只对非预期的缺失打warning
            missing_var = str(e).strip("'")
            expected_missing = ["previous_opinions", "supporter_opinion", "critic_opinion",
                              "visionary_ideas", "pragmatist_ideas", "futurist_ideas"]

            if missing_var not in expected_missing:
                logger.warning(f"意外的模板变量缺失: {e}, 使用空字符串替代")

            # 补充缺失的变量
            missing_keys = [key for key in self.config.user_prompt_template.split('{')[1:]
                          if key.split('}')[0] not in template_vars]
            for key in missing_keys:
                key_name = key.split('}')[0]
                template_vars[key_name] = ""
            user_prompt = self.config.user_prompt_template.format(**template_vars)

        return user_prompt

    def _format_previous_messages(self, messages: Dict[str, str]) -> Dict[str, str]:
        """格式化前序消息"""
        formatted = {}

        # 为常见的Agent ID提供特殊格式化
        if "supporter" in messages:
            formatted["supporter_opinion"] = messages["supporter"]

        if "critic" in messages:
            formatted["critic_opinion"] = messages["critic"]

        if "visionary" in messages:
            formatted["visionary_ideas"] = messages["visionary"]

        if "pragmatist" in messages:
            formatted["pragmatist_ideas"] = messages["pragmatist"]

        if "futurist" in messages:
            formatted["futurist_ideas"] = messages["futurist"]

        # 生成previous_opinions: 包含所有前序消息的综合文本
        if messages:
            opinions_parts = []
            for agent_id, msg in messages.items():
                # 添加agent标识
                opinions_parts.append(f"\n【{agent_id}的观点】\n{msg}")
            formatted["previous_opinions"] = "\n".join(opinions_parts)
        else:
            formatted["previous_opinions"] = ""

        # 添加原始消息
        for agent_id, msg in messages.items():
            formatted[f"{agent_id}_message"] = msg

        return formatted

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """调用LLM（非流式）"""
        # 准备内容用于token计算和模型选择
        content = f"{system_prompt}\n\n{user_prompt}"

        # 尝试使用openai-compatible提供商（如果配置了环境变量）
        import os
        llm = None

        if os.getenv("OPENAI_COMPATIBLE_BASE_URL"):
            # 直接使用openai-compatible提供商
            try:
                from esperanto import AIFactory
                logger.info("使用OpenAI Compatible提供商")
                model = AIFactory.create_language(
                    provider="openai-compatible",
                    model_name="gpt-4o-mini",
                    config={
                        "temperature": self.config.temperature,
                        "max_tokens": 850,
                        "streaming": False
                    }
                )
                llm = model.to_langchain()
            except Exception as e:
                logger.warning(f"无法使用OpenAI Compatible提供商: {e}, 回退到默认模型")

        # 如果openai-compatible不可用，使用默认模型
        if llm is None:
            llm = await provision_langchain_model(
                content=content,
                model_id=None,  # 使用默认chat模型
                default_type="chat",
                temperature=self.config.temperature
            )

        # 构建消息
        from langchain_core.messages import HumanMessage, SystemMessage
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        # 调用LLM
        response = await llm.ainvoke(messages)

        return response.content

    async def _call_llm_streaming(
        self,
        system_prompt: str,
        user_prompt: str,
        callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """调用LLM（流式输出）"""
        # 准备内容用于token计算和模型选择
        content = f"{system_prompt}\n\n{user_prompt}"

        # 尝试使用openai-compatible提供商（如果配置了环境变量）
        import os
        llm = None

        if os.getenv("OPENAI_COMPATIBLE_BASE_URL"):
            # 直接使用openai-compatible提供商
            try:
                from esperanto import AIFactory
                logger.info("使用OpenAI Compatible提供商（流式）")
                model = AIFactory.create_language(
                    provider="openai-compatible",
                    model_name="gpt-4o-mini",
                    config={
                        "temperature": self.config.temperature,
                        "max_tokens": 850,
                        "streaming": True
                    }
                )
                llm = model.to_langchain()
            except Exception as e:
                logger.warning(f"无法使用OpenAI Compatible提供商: {e}, 回退到默认模型")

        # 如果openai-compatible不可用，使用默认模型
        if llm is None:
            llm = await provision_langchain_model(
                content=content,
                model_id=None,
                default_type="chat",
                temperature=self.config.temperature
            )

        # 构建消息
        from langchain_core.messages import HumanMessage, SystemMessage
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        # 流式调用LLM
        full_response = ""
        async for chunk in llm.astream(messages):
            if hasattr(chunk, 'content'):
                text = chunk.content
                full_response += text
                # 调用回调函数实时输出
                if callback and text:
                    callback(text)

        return full_response

    async def _execute_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        streaming: bool = False,
        stream_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        使用工具的Agent执行（ReAct Agent模式）

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            streaming: 是否启用流式输出（注意：工具调用时流式支持有限）
            stream_callback: 流式回调

        Returns:
            包含内容和工具调用记录的字典
        """
        logger.info(f"[_execute_with_tools] 开始执行，工具数量={len(self.tools)}")

        # 1. 获取LLM
        logger.info(f"[_execute_with_tools] 准备获取LLM")
        llm = await self._get_llm()
        logger.info(f"[_execute_with_tools] LLM 已获取: {type(llm).__name__}")

        # 2. 创建Agent（使用新的create_agent API）
        logger.info(f"[_execute_with_tools] 准备创建Agent，工具列表={[t.name for t in self.tools]}")
        try:
            agent_executor = create_agent(
                model=llm,
                tools=self.tools,
                system_prompt=system_prompt  # 系统提示词
            )
            logger.info(f"[_execute_with_tools] Agent 已创建")
        except Exception as e:
            logger.error(f"[_execute_with_tools] 创建Agent失败: {e}")
            logger.exception(e)
            raise

        # 3. 执行Agent
        try:
            # 准备输入消息
            messages = [HumanMessage(content=user_prompt)]

            # 如果启用流式且有回调，使用 astream_events
            if streaming and stream_callback:
                logger.info(f"[_execute_with_tools] 准备调用 agent_executor.astream_events() (流式模式)")

                tool_calls = []
                final_content = ""
                current_content = ""

                # 使用 astream_events 获取事件流
                async for event in agent_executor.astream_events(
                    {"messages": messages},
                    version="v2"
                ):
                    kind = event.get("event")

                    # 调试：记录所有事件类型
                    if kind not in ["on_chat_model_stream", "on_tool_start", "on_tool_end"]:
                        logger.debug(f"[_execute_with_tools] 收到事件: {kind}")

                    # 处理 LLM 流式输出
                    if kind == "on_chat_model_stream":
                        chunk = event.get("data", {}).get("chunk")
                        if chunk and hasattr(chunk, "content"):
                            content = chunk.content
                            if content:
                                current_content += content
                                # 调用回调函数实时输出
                                stream_callback(content)
                                logger.debug(f"[_execute_with_tools] 捕获流式内容: {len(content)} 字符")

                    # 处理工具调用
                    elif kind == "on_tool_start":
                        tool_name = event.get("name", "unknown")
                        tool_input = event.get("data", {}).get("input", {})
                        logger.info(f"[_execute_with_tools] 工具开始: {tool_name}")
                        tool_calls.append({
                            "tool": tool_name,
                            "input": str(tool_input),
                            "output": ""
                        })

                    elif kind == "on_tool_end":
                        tool_output = event.get("data", {}).get("output")
                        if tool_calls:
                            tool_output_str = str(tool_output)
                            tool_calls[-1]["output"] = tool_output_str

                            # 详细诊断日志
                            logger.info(f"[工具输出-流式] 工具名称: {tool_calls[-1]['tool']}")
                            logger.info(f"[工具输出-流式] 输出类型: {type(tool_output)}")
                            logger.info(f"[工具输出-流式] 输出长度: {len(tool_output_str)} 字符")
                            logger.info(f"[工具输出-流式] 是否为空: {tool_output_str == '' or tool_output_str == 'None'}")
                            logger.info(f"[工具输出-流式] 前200字符: {tool_output_str[:200]}")
                            logger.info(f"[_execute_with_tools] 工具完成: {tool_calls[-1]['tool']}")

                    # 尝试捕获 Agent 的最终输出（可能在不同的事件中）
                    elif kind == "on_chain_end":
                        output = event.get("data", {}).get("output")
                        if output and isinstance(output, dict):
                            messages_out = output.get("messages", [])
                            if messages_out:
                                last_msg = messages_out[-1]
                                if hasattr(last_msg, "content") and last_msg.content:
                                    if not current_content:  # 只在还没捕获到内容时使用
                                        current_content = last_msg.content
                                        logger.info(f"[_execute_with_tools] 从 on_chain_end 获取内容: {len(current_content)} 字符")

                # 如果没有捕获到内容，获取最终结果
                if not current_content:
                    logger.info(f"[_execute_with_tools] 流式模式未捕获内容，调用 ainvoke 获取最终结果")
                    result = await agent_executor.ainvoke({"messages": messages})
                    for msg in result.get("messages", []):
                        if hasattr(msg, 'type') and msg.type == 'ai' and hasattr(msg, 'content'):
                            final_content = msg.content
                            break
                else:
                    final_content = current_content

                logger.info(f"[_execute_with_tools] 流式执行完成")

                return {
                    "content": final_content,
                    "tool_calls": tool_calls
                }

            else:
                # 非流式模式：使用原有的阻塞调用
                logger.info(f"[_execute_with_tools] 准备调用 agent_executor.ainvoke() (非流式模式)")

                result = await agent_executor.ainvoke({"messages": messages})
                logger.info(f"[_execute_with_tools] agent_executor.ainvoke() 完成")

                # 4. 提取工具调用记录和最终响应
                tool_calls = []
                final_content = ""

                # 遍历消息历史提取工具调用
                for msg in result.get("messages", []):
                    # 检查是否是AI消息且包含工具调用
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            tool_calls.append({
                                "tool": tool_call.get("name", "unknown"),
                                "input": str(tool_call.get("args", {})),
                                "output": ""  # 输出在下一条消息中
                            })

                    # 检查是否是工具消息（包含工具输出）
                    if hasattr(msg, 'type') and msg.type == 'tool':
                        if tool_calls:
                            # 将输出添加到最后一个工具调用
                            tool_output = str(msg.content)
                            tool_calls[-1]["output"] = tool_output

                            # 详细诊断日志
                            logger.info(f"[工具输出] 工具名称: {tool_calls[-1]['tool']}")
                            logger.info(f"[工具输出] 输出类型: {type(msg.content)}")
                            logger.info(f"[工具输出] 输出长度: {len(tool_output)} 字符")
                            logger.info(f"[工具输出] 是否为空: {tool_output == '' or tool_output == 'None'}")
                            logger.info(f"[工具输出] 前200字符: {tool_output[:200]}")
                            logger.info(f"工具调用: {tool_calls[-1]['tool']}({str(tool_calls[-1]['input'])[:100]}...)")

                    # 最后一条AI消息是最终响应
                    if hasattr(msg, 'type') and msg.type == 'ai' and hasattr(msg, 'content'):
                        final_content = msg.content

                return {
                    "content": final_content,
                    "tool_calls": tool_calls
                }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"工具调用失败: {error_msg}")

            # 检查是否是API限流或400错误
            if "400" in error_msg or "rate" in error_msg.lower():
                logger.warning("检测到API限流或400错误，可能是并发请求导致")

            # 只在debug模式打印完整堆栈
            if logger.isEnabledFor(logging.DEBUG):
                import traceback
                traceback.print_exc()

            # 降级：返回错误信息，不中断执行
            return {
                "content": f"[工具调用失败: {error_msg[:100]}...] 继续基于已有信息分析...",
                "tool_calls": []
            }

    async def _get_llm(self):
        """
        获取LLM实例（支持工具调用）

        Returns:
            配置好的LLM实例
        """
        import os

        logger.info(f"[_get_llm] 开始获取LLM")

        # 准备内容用于token计算和模型选择
        content = f"{self.config.system_prompt[:500]}"

        # 尝试使用openai-compatible提供商（如果配置了环境变量）
        if os.getenv("OPENAI_COMPATIBLE_BASE_URL"):
            try:
                logger.info(f"[_get_llm] 检测到 OPENAI_COMPATIBLE_BASE_URL，使用 openai-compatible 提供商")
                from esperanto import AIFactory
                model = AIFactory.create_language(
                    provider="openai-compatible",
                    model_name="gpt-4o-mini",  # 使用支持工具调用的模型
                    config={
                        "temperature": self.config.temperature,
                        "max_tokens": 1500,
                    }
                )
                logger.info(f"[_get_llm] OpenAI Compatible 模型创建成功")
                return model.to_langchain()
            except Exception as e:
                logger.warning(f"[_get_llm] 无法使用OpenAI Compatible提供商: {e}, 回退到默认模型")

        # 如果openai-compatible不可用，使用默认模型
        logger.info(f"[_get_llm] 使用默认模型（通过 provision_langchain_model）")
        llm = await provision_langchain_model(
            content=content,
            model_id=None,  # 使用默认chat模型
            default_type="chat",
            temperature=self.config.temperature
        )
        logger.info(f"[_get_llm] 默认模型获取成功: {type(llm).__name__}")

        return llm


# 测试代码
if __name__ == "__main__":
    import asyncio
    from open_notebook.thinking_workshop.agent_manager import AgentManager

    async def test():
        # 加载配置
        manager = AgentManager()
        supporter_config = manager.get_agent("dialectical_mode", "supporter")

        # 创建执行器
        executor = AgentExecutor(supporter_config)

        # 测试执行
        context = {
            "title": "Attention Is All You Need",
            "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
            "context": "这是一篇提出Transformer架构的论文"
        }

        response = await executor.execute(
            topic="评审Transformer论文",
            context=context
        )

        print(f"Agent响应:\n{response}")

    asyncio.run(test())
