import re
from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from open_notebook.graphs.utils import provision_langchain_model


class ReliabilityChecker:
    """可靠性检查器，使用自然语言格式提高鲁棒性"""

    def __init__(self, max_retries: int = 3, quality_threshold: str = "medium"):
        self.max_retries = max_retries
        self.quality_threshold = quality_threshold
        self.quality_order = {"low": 0, "medium": 1, "high": 2}

    async def check_reliability(self, transformation_prompt: str, original_content: str,
                                generated_result: str, config: dict) -> Dict:
        """
        执行可靠性检查 - 使用自然语言格式提高鲁棒性
        """
        try:
            evaluation_prompt = self._build_evaluation_prompt(
                transformation_prompt, original_content, generated_result
            )

            evaluation_result = await self._call_evaluation_model(evaluation_prompt, config)
            return self._parse_natural_language_result(evaluation_result)

        except Exception as e:
            print(f"Reliability check failed: {str(e)}")
            return self._get_fallback_result(str(e))

    def _build_evaluation_prompt(self, transformation_prompt: str, original_content: str,
                                 generated_result: str) -> str:
        """构建评估提示词 - 使用自然语言格式"""
        return f"""
请对以下转换结果进行质量评估：

**转换任务：**
{transformation_prompt}

**原始内容（片段）：**
{original_content[:1500]}...

**生成结果：**
{generated_result}

请从以下方面进行检查：

检查项目：
1. 信息准确性：结果是否准确反映原始内容的关键信息
2. 任务符合度：是否完整完成了转换任务的要求  
3. 逻辑一致性：内容是否存在矛盾或不合逻辑之处
4. 语言质量：语言是否通顺、专业、符合要求
5. 完整性：是否涵盖了原始内容的关键要点

请按照以下格式回复：

质量等级：high/medium/low
通过检查：信息准确性，任务符合度，语言质量
未通过检查：逻辑一致性，完整性
具体问题：
1. 问题描述1
2. 问题描述2

说明：
- 质量等级：high表示高质量，medium表示中等质量，low表示低质量
- 通过检查：列出所有通过的检查项目
- 未通过检查：列出所有未通过的检查项目
- 具体问题：详细描述发现的问题
"""

    async def _call_evaluation_model(self, evaluation_prompt: str, config: dict) -> str:
        """调用评估模型"""
        messages = [
            SystemMessage(content="你是一个严格的质量评估专家，请客观评估内容质量。请严格按照要求的格式回复。"),
            HumanMessage(content=evaluation_prompt)
        ]

        # 这里需要根据你的实际环境调整模型调用方式
        evaluation_chain = await provision_langchain_model(
            str(messages),
            config.get("configurable", {}).get("model_id"),
            "transformation",
            max_tokens=800,
        )

        response = await evaluation_chain.ainvoke(messages)
        return response.content if isinstance(response.content, str) else str(response.content)

    def _parse_natural_language_result(self, response_text: str) -> Dict:
        """
        解析自然语言格式的评估结果
        使用关键词匹配和正则表达式提高鲁棒性
        """
        try:
            # 初始化默认值
            result = {
                'quality': 'low',
                'passed_checks': [],
                'failed_checks': [],
                'issues': [],
                'raw_response': response_text
            }

            # 解析质量等级
            quality_match = re.search(r'质量等级\s*：\s*(\w+)', response_text)
            if quality_match:
                quality = quality_match.group(1).lower()
                if quality in ['high', 'medium', 'low']:
                    result['quality'] = quality
                elif '高' in quality:
                    result['quality'] = 'high'
                elif '中' in quality:
                    result['quality'] = 'medium'
                elif '低' in quality:
                    result['quality'] = 'low'

            # 解析通过的检查
            passed_match = re.search(r'通过检查\s*：\s*([^\n]+)', response_text)
            if passed_match:
                passed_text = passed_match.group(1)
                result['passed_checks'] = self._extract_check_items(passed_text)

            # 解析未通过的检查
            failed_match = re.search(r'未通过检查\s*：\s*([^\n]+)', response_text)
            if failed_match:
                failed_text = failed_match.group(1)
                result['failed_checks'] = self._extract_check_items(failed_text)

            # 解析具体问题
            issues_match = re.search(r'具体问题\s*：\s*(.+?)(?=\n\n|\n[^\d]|$)', response_text, re.DOTALL)
            if issues_match:
                issues_text = issues_match.group(1)
                result['issues'] = self._extract_issues(issues_text)

            # 如果解析结果为空，尝试备用解析方法
            if not result['passed_checks'] and not result['failed_checks']:
                self._fallback_parsing(response_text, result)

            print(f"Parsed reliability result: quality={result['quality']}, "
                        f"passed={len(result['passed_checks'])}, "
                        f"failed={len(result['failed_checks'])}, "
                        f"issues={len(result['issues'])}")

            return result

        except Exception as e:
            print(f"Natural language parsing failed: {str(e)}")
            return self._get_fallback_result(f"解析错误: {str(e)}")

    def _extract_check_items(self, text: str) -> List[str]:
        """从文本中提取检查项目"""
        items = []
        # 多种分隔符支持：逗号、顿号、空格
        for separator in [',', '，', '、', ' ']:
            if separator in text:
                items = [item.strip() for item in text.split(separator) if item.strip()]
                break

        # 如果没有找到分隔符，尝试直接使用整个文本
        if not items and text.strip():
            items = [text.strip()]

        return items

    def _extract_issues(self, text: str) -> List[str]:
        """从文本中提取问题列表"""
        issues = []

        # 尝试按数字序号提取
        numbered_issues = re.findall(r'\d+\.\s*([^\n]+)', text)
        if numbered_issues:
            issues = [issue.strip() for issue in numbered_issues if issue.strip()]
        else:
            # 尝试按行分割
            lines = text.split('\n')
            issues = [line.strip() for line in lines if line.strip() and not line.isspace()]

        return issues

    def _fallback_parsing(self, response_text: str, result: Dict):
        """备用解析方法，使用关键词匹配"""
        text_lower = response_text.lower()

        # 关键词匹配质量等级
        if '高质量' in text_lower or 'high' in text_lower:
            result['quality'] = 'high'
        elif '中等质量' in text_lower or 'medium' in text_lower:
            result['quality'] = 'medium'
        elif '低质量' in text_lower or 'low' in text_lower:
            result['quality'] = 'low'

        # 关键词匹配检查项目
        check_items = ['信息准确性', '任务符合度', '逻辑一致性', '语言质量', '完整性']
        for item in check_items:
            if item in response_text:
                # 简单判断：如果附近有负面词汇，认为是未通过
                item_index = response_text.find(item)
                snippet = response_text[max(0, item_index - 20):min(len(response_text), item_index + 20)]
                negative_words = ['不', '未', '缺少', '缺乏', '错误', '问题', '失败']

                if any(word in snippet for word in negative_words):
                    result['failed_checks'].append(item)
                else:
                    result['passed_checks'].append(item)

    def _get_fallback_result(self, error_msg: str) -> Dict:
        """获取回退结果"""
        return {
            'quality': 'low',
            'passed_checks': [],
            'failed_checks': ['评估过程出错'],
            'issues': [f'评估错误: {error_msg}'],
            'raw_response': ''
        }

    def is_acceptable_quality(self, quality: str) -> bool:
        """检查质量是否可接受"""
        return self.quality_order[quality] >= self.quality_order[self.quality_threshold]