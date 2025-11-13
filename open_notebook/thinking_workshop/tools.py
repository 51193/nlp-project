"""
思维工坊工具集
提供Agent可使用的工具，包括网络搜索、计算器、文档读取等
"""

from typing import List, Dict, Any, Optional
from langchain_core.tools import StructuredTool, BaseTool
from langchain_tavily import TavilySearch
import ast
import operator
import os
from loguru import logger


class WorkshopTools:
    """工具工厂类"""

    @staticmethod
    def create_web_search() -> BaseTool:
        """
        创建网络搜索工具（基于Tavily）

        Tavily是专为AI优化的搜索引擎，提供高质量、可引用的搜索结果

        注意：必须配置TAVILY_API_KEY才能使用此工具
        """
        # 检查API Key
        if not os.getenv("TAVILY_API_KEY"):
            error_msg = "TAVILY_API_KEY未设置，无法使用web_search工具。请在.env文件中配置TAVILY_API_KEY"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # TavilySearch已经是一个完整的工具，直接返回
        logger.info("成功创建Tavily搜索工具")
        return TavilySearch()

    @staticmethod
    def create_calculator() -> BaseTool:
        """
        创建计算器工具（安全版本）

        使用AST解析实现安全的数学表达式计算，避免eval的安全风险
        """
        # 安全的数学运算白名单
        safe_operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
            ast.Mod: operator.mod,
        }

        def safe_eval(expr: str) -> str:
            """Safely evaluate mathematical expressions"""
            try:
                # Remove whitespace
                expr = expr.strip()

                # Check for empty input
                if not expr:
                    return "Error: Expression is empty"

                # Parse AST
                tree = ast.parse(expr, mode='eval')

                def _eval(node):
                    if isinstance(node, ast.Constant):  # Python 3.8+ numeric constant
                        return node.value
                    elif isinstance(node, ast.Num):     # Python 3.7 compatibility
                        return node.n
                    elif isinstance(node, ast.BinOp):   # Binary operation
                        op_type = type(node.op)
                        if op_type not in safe_operators:
                            raise ValueError(f"Unsupported operator: {op_type.__name__}")
                        left = _eval(node.left)
                        right = _eval(node.right)
                        return safe_operators[op_type](left, right)
                    elif isinstance(node, ast.UnaryOp): # Unary operation
                        op_type = type(node.op)
                        if op_type not in safe_operators:
                            raise ValueError(f"Unsupported operator: {op_type.__name__}")
                        operand = _eval(node.operand)
                        return safe_operators[op_type](operand)
                    else:
                        raise ValueError(f"Unsupported expression type: {type(node).__name__}")

                result = _eval(tree.body)

                # Format result
                if isinstance(result, float):
                    # If integer result, display as integer
                    if result.is_integer():
                        return f"Result: {int(result)}"
                    else:
                        # Keep 4 decimal places
                        return f"Result: {result:.4f}"
                else:
                    return f"Result: {result}"

            except ZeroDivisionError:
                return "Error: Division by zero"
            except Exception as e:
                return f"Calculation error: {str(e)}"

        return StructuredTool.from_function(
            func=safe_eval,
            name="calculator",
            description="""计算数学表达式，验证数据准确性。

支持的运算：
- 加法: +
- 减法: -
- 乘法: *
- 除法: /
- 幂运算: **
- 取模: %
- 负数: -x

使用场景：
- 验证论文中的数据计算
- 计算性能提升百分比
- 核对统计数字的准确性
- 分析实验结果的变化率

输入格式：数学表达式（字符串）
输出格式：计算结果或错误信息

示例：
- calculator("(28.4 - 26.3) / 26.3 * 100")  # 计算提升百分比
- calculator("2 ** 10")  # 计算2的10次方
- calculator("1024 / 8")  # 计算除法

注意：
- 只支持数学运算，不支持变量和函数
- 表达式要准确，避免语法错误
"""
        )

    @staticmethod
    def create_notebook_reader(notebook_id: Optional[str] = None) -> BaseTool:
        """
        Create notebook content reader tool that reads ALL content from database

        Args:
            notebook_id: The notebook ID to read from
        """
        def read_notebook(query: str) -> str:
            """
            Read ALL content from the notebook's sources and notes.
            Provides complete context for the agent to think and analyze.

            Args:
                query: Topic or aspect to focus on (optional hint, not used for filtering)

            Returns:
                Complete content of all sources and notes in the notebook
            """
            import asyncio
            import threading
            from open_notebook.domain.notebook import Notebook, Source, Note

            # Debug logging
            logger.info(f"[notebook_reader] Reading complete notebook content (query hint: '{query}')")
            logger.info(f"[notebook_reader] Notebook ID: {notebook_id}")

            if not notebook_id:
                logger.warning("[notebook_reader] No notebook_id provided!")
                return "No notebook specified"

            def run_async_in_new_thread(coro):
                """Run async code in a new thread with its own event loop"""
                result_container = [None]
                exception_container = [None]

                def thread_target():
                    try:
                        # Create new event loop for this thread
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            logger.info(f"[notebook_reader] Running in new thread with new event loop")
                            result_container[0] = new_loop.run_until_complete(coro)
                            logger.info(f"[notebook_reader] Thread execution completed successfully")
                        finally:
                            new_loop.close()
                    except Exception as e:
                        logger.error(f"[notebook_reader] Thread execution error: {e}")
                        logger.exception(e)
                        exception_container[0] = e

                thread = threading.Thread(target=thread_target)
                thread.start()
                thread.join(timeout=30)  # Add timeout to prevent hanging

                if thread.is_alive():
                    logger.error("[notebook_reader] Thread timeout after 30s")
                    return None

                if exception_container[0]:
                    logger.error(f"[notebook_reader] Raising exception from thread: {exception_container[0]}")
                    raise exception_container[0]
                return result_container[0]

            try:
                # Get notebook
                logger.info(f"[notebook_reader] Step 1: Getting notebook {notebook_id}")
                notebook = run_async_in_new_thread(Notebook.get(notebook_id))

                if notebook is None:
                    error_msg = f"[notebook_reader] ERROR: Notebook.get() returned None for {notebook_id}"
                    logger.error(error_msg)
                    return f"ERROR: Could not fetch notebook {notebook_id}. Database connection may have failed."

                if not notebook:
                    logger.error(f"[notebook_reader] Notebook {notebook_id} not found")
                    return f"Notebook {notebook_id} not found in database"

                logger.info(f"[notebook_reader] Step 2: Getting sources and notes")
                # Get sources and notes lists (without content initially)
                sources = run_async_in_new_thread(notebook.get_sources())
                notes = run_async_in_new_thread(notebook.get_notes())

                if sources is None:
                    logger.error(f"[notebook_reader] ERROR: get_sources() returned None")
                    sources = []
                if notes is None:
                    logger.error(f"[notebook_reader] ERROR: get_notes() returned None")
                    notes = []

                logger.info(f"[notebook_reader] Found {len(sources)} sources and {len(notes)} notes in notebook")

                # Build complete notebook content
                content_parts = []
                content_parts.append("# Complete Notebook Content\n\n")
                content_parts.append(f"This notebook contains {len(sources)} sources and {len(notes)} notes.\n\n")

                # Add all sources with FULL content
                sources_added = 0
                if sources:
                    content_parts.append("## Sources (Papers, Articles, Documents)\n\n")
                    for i, source in enumerate(sources[:5], 1):  # Limit to 5 sources to manage token count
                        try:
                            logger.info(f"[notebook_reader] Fetching source {i}/{min(len(sources), 5)}: {source.id}")
                            # Fetch full source with content
                            full_source = run_async_in_new_thread(Source.get(source.id))

                            if full_source is None:
                                logger.warning(f"[notebook_reader] Source.get() returned None for {source.id}")
                                continue

                            if full_source and full_source.full_text:
                                content_parts.append(f"### Source {i}: {full_source.title}\n\n")
                                # Limit each source to 4000 characters to manage context
                                text = full_source.full_text[:4000]
                                if len(full_source.full_text) > 4000:
                                    text += "\n\n... (remaining content truncated)"
                                content_parts.append(text)
                                content_parts.append("\n\n---\n\n")
                                sources_added += 1
                                logger.info(f"[notebook_reader] ✓ Added source: {full_source.title} ({len(full_source.full_text)} chars)")
                            else:
                                logger.warning(f"[notebook_reader] Source {source.id} has no full_text")
                        except Exception as e:
                            logger.error(f"[notebook_reader] Error fetching source {source.id}: {e}")
                            logger.exception(e)
                            continue

                # Add all notes with FULL content
                notes_added = 0
                if notes:
                    content_parts.append("## Notes (User's Analysis and Thoughts)\n\n")
                    for i, note in enumerate(notes[:10], 1):  # Limit to 10 notes
                        try:
                            logger.info(f"[notebook_reader] Fetching note {i}/{min(len(notes), 10)}: {note.id}")
                            # Fetch full note with content
                            full_note = run_async_in_new_thread(Note.get(note.id))

                            if full_note is None:
                                logger.warning(f"[notebook_reader] Note.get() returned None for {note.id}")
                                continue

                            if full_note and full_note.content:
                                content_parts.append(f"### Note {i}: {full_note.title}\n\n")
                                # Limit each note to 2000 characters
                                text = full_note.content[:2000]
                                if len(full_note.content) > 2000:
                                    text += "\n\n... (remaining content truncated)"
                                content_parts.append(text)
                                content_parts.append("\n\n---\n\n")
                                notes_added += 1
                                logger.info(f"[notebook_reader] ✓ Added note: {full_note.title} ({len(full_note.content)} chars)")
                            else:
                                logger.warning(f"[notebook_reader] Note {note.id} has no content")
                        except Exception as e:
                            logger.error(f"[notebook_reader] Error fetching note {note.id}: {e}")
                            logger.exception(e)
                            continue

                result = ''.join(content_parts)
                logger.info(f"[notebook_reader] SUCCESS: Returning {len(result)} chars total (sources: {sources_added}/{len(sources)}, notes: {notes_added}/{len(notes)})")

                if len(result) < 100:  # If very little content
                    warning_msg = f"WARNING: This notebook appears to be empty or contains no readable content. (sources: {len(sources)}, notes: {len(notes)})"
                    logger.warning(f"[notebook_reader] {warning_msg}")
                    return warning_msg

                return result

            except Exception as e:
                error_msg = f"ERROR reading notebook: {str(e)}"
                logger.error(f"[notebook_reader] {error_msg}")
                logger.exception(e)
                return error_msg

        return StructuredTool.from_function(
            func=read_notebook,
            name="notebook_reader",
            description="""Read the COMPLETE content of the user's notebook (all sources and notes).

This tool provides the FULL text of all papers, articles, documents (sources) and user's notes in the notebook.
It does NOT search or filter - it returns EVERYTHING for you to read and analyze.

Use this tool when you need to:
- Understand the complete context of the notebook
- Analyze papers or documents in detail
- Review user's notes and thoughts
- Find information across multiple sources
- Get a comprehensive view before forming opinions

The tool returns:
- Complete text of all sources (papers, PDFs, articles, web pages)
- Complete text of all user notes
- Full content without filtering or summarization

Note: Content may be truncated if very long to fit within context limits.
After calling this tool, you will have all the information needed to provide thoughtful analysis.
"""
        )

    @staticmethod
    def get_tools_by_ids(
        tool_ids: List[str],
        notebook_id: Optional[str] = None
    ) -> List[BaseTool]:
        """
        Get tool instances by ID list

        Args:
            tool_ids: Tool ID list, e.g. ["tavily_search", "notebook_reader"]
            notebook_id: Notebook ID (for notebook_reader tool)

        Returns:
            List of tool instances
        """
        tools = []

        for tool_id in tool_ids:
            try:
                # Support both "web_search" (legacy) and "tavily_search" (correct)
                if tool_id in ["web_search", "tavily_search"]:
                    tools.append(WorkshopTools.create_web_search())
                    logger.info(f"Added tool: tavily_search (via {tool_id})")

                elif tool_id == "calculator":
                    tools.append(WorkshopTools.create_calculator())
                    logger.info(f"Added tool: calculator")

                elif tool_id == "notebook_reader":
                    tools.append(WorkshopTools.create_notebook_reader(notebook_id))
                    logger.info(f"Added tool: notebook_reader (notebook_id={notebook_id})")

                else:
                    logger.warning(f"Unknown tool ID: {tool_id}")

            except Exception as e:
                logger.error(f"Failed to create tool {tool_id}: {e}")

        return tools


# 测试代码
if __name__ == "__main__":
    import asyncio

    def test_calculator():
        """测试计算器工具"""
        print("=" * 80)
        print("测试: 计算器工具")
        print("=" * 80)

        calc = WorkshopTools.create_calculator()

        test_cases = [
            "(28.4 - 26.3) / 26.3 * 100",  # 百分比计算
            "2 ** 10",                      # 幂运算
            "1024 / 8",                     # 除法
            "5 * (3 + 2)",                  # 复合运算
            "10 / 0",                       # 除零错误
            "invalid",                       # 语法错误
        ]

        for expr in test_cases:
            result = calc.func(expr)
            print(f"\n表达式: {expr}")
            print(f"结果: {result}")

    def test_notebook_reader():
        """测试笔记本读取工具"""
        print("\n\n" + "=" * 80)
        print("测试: 笔记本读取工具")
        print("=" * 80)

        # 模拟笔记本内容
        notebook_content = """
        # Transformer论文分析

        ## 性能数据
        - WMT2014英德翻译: 28.4 BLEU
        - 训练时间: 相比前作缩短70%
        - 参数量: 65M (base), 213M (large)

        ## 创新点
        1. 完全基于attention机制
        2. 可并行化训练
        3. 长距离依赖处理能力强

        ## 影响力
        引用次数极高，成为NLP领域的里程碑工作
        """

        reader = WorkshopTools.create_notebook_reader(notebook_content)

        test_queries = [
            "性能数据",
            "BLEU",
            "创新点",
            "不存在的内容",
        ]

        for query in test_queries:
            result = reader.func(query)
            print(f"\n查询: {query}")
            print(f"结果:\n{result}")
            print("-" * 40)

    # 运行测试
    test_calculator()
    test_notebook_reader()

    print("\n\n" + "=" * 80)
    print("工具测试完成！")
    print("=" * 80)
