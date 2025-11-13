from typing import Dict, List, Callable, Any, Tuple
from dataclasses import dataclass

@dataclass
class GenerationAttempt:
    """单次生成尝试的结果"""
    content: str
    quality: str
    issues: List[str]
    passed_checks: List[str]
    attempt_number: int


class RetryManager:
    """重试管理器，负责管理生成重试逻辑"""

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.attempts: List[GenerationAttempt] = []

    async def generate_with_retry(self, generate_func: Callable, check_func: Callable,
                                  generate_args: Dict, check_extra_args: Dict) -> Tuple[str, Dict]:
        """
        带重试的生成过程

        Args:
            generate_func: 生成函数
            check_func: 检查函数
            generate_args: 生成参数
            check_extra_args: 检查函数需要的额外参数（除了generated_result）

        Returns:
            最终结果和元数据
        """
        self.attempts.clear()

        for attempt in range(self.max_retries):
            print(f"Generation attempt {attempt + 1}/{self.max_retries}")

            # 生成内容
            generated_content = await generate_func(**generate_args)

            # 准备检查函数的参数
            check_args = {**check_extra_args, 'generated_result': generated_content}

            # 检查可靠性
            check_result = await check_func(**check_args)

            # 记录尝试结果
            attempt_result = GenerationAttempt(
                content=generated_content,
                quality=check_result['quality'],
                issues=check_result['issues'],
                passed_checks=check_result['passed_checks'],
                attempt_number=attempt + 1
            )
            self.attempts.append(attempt_result)

            print(f"Attempt {attempt + 1} quality: {check_result['quality']}")

            # 检查是否满足质量要求
            if self._is_quality_acceptable(check_result['quality']):
                print(f"Quality acceptable after {attempt + 1} attempts")
                return self._build_final_result(attempt_result, is_reliable=True)

        # 所有尝试都未达到要求，返回最佳结果
        best_attempt = self._get_best_attempt()
        print(f"All attempts failed to meet quality threshold, using best result")
        return self._build_final_result(best_attempt, is_reliable=False)

    def _is_quality_acceptable(self, quality: str) -> bool:
        """检查质量是否可接受"""
        quality_order = {"low": 0, "medium": 1, "high": 2}
        return quality_order[quality] >= quality_order["medium"]  # 中等质量以上可接受

    def _get_best_attempt(self) -> GenerationAttempt:
        """获取最佳尝试结果"""
        quality_order = {"low": 0, "medium": 1, "high": 2}
        return max(self.attempts, key=lambda x: quality_order[x.quality])

    def _build_final_result(self, attempt: GenerationAttempt, is_reliable: bool) -> Tuple[str, Dict]:
        """构建最终结果"""
        metadata = {
            'reliable': is_reliable,
            'quality': attempt.quality,
            'attempts': len(self.attempts),
            'final_attempt': attempt.attempt_number,
            'issues': attempt.issues,
            'passed_checks': attempt.passed_checks,
            'all_attempts': [
                {
                    'attempt_number': a.attempt_number,
                    'quality': a.quality,
                    'issues': a.issues
                }
                for a in self.attempts
            ]
        }

        return attempt.content, metadata