from typing import Dict


class ResultFormatter:
    """结果格式化器，负责格式化最终输出"""

    @staticmethod
    def add_reliability_note(content: str, metadata: Dict) -> str:
        """
        在内容顶部添加可靠性说明，底部添加评估报告

        Args:
            content: 原始内容
            metadata: 可靠性元数据

        Returns:
            带说明和评估报告的格式化内容
        """
        top_note = ResultFormatter._build_reliability_note(metadata)
        bottom_report = ResultFormatter._build_evaluation_report(metadata)

        return f"{top_note}\n\n{content}\n\n{bottom_report}"

    @staticmethod
    def _build_reliability_note(metadata: Dict) -> str:
        """构建可靠性说明"""
        attempts_count = metadata.get('attempts', 1)
        quality = metadata.get('quality', 'low')
        is_reliable = metadata.get('reliable', False)

        quality_descriptions = {
            'high': '高质量',
            'medium': '中等质量',
            'low': '质量待改进'
        }

        quality_desc = quality_descriptions.get(quality, '未知质量')

        if attempts_count == 1:
            if is_reliable:
                return f"[一次性生成成功，评估为{quality_desc}]"
            else:
                return f"[单次生成，评估为{quality_desc}，建议人工核查]"
        else:
            reliability_status = "通过" if is_reliable else "未通过"
            return f"[经过 {attempts_count} 次尝试生成，质量评估{reliability_status}，等级: {quality_desc}]"

    @staticmethod
    def _build_evaluation_report(metadata: Dict) -> str:
        """构建详细的评估报告"""
        report_lines = []
        report_lines.append("\n\n")
        report_lines.append("--- 可靠性评估报告 ---")

        # 基本信息
        quality = metadata.get('quality', 'low')
        is_reliable = metadata.get('reliable', False)
        attempts_count = metadata.get('attempts', 1)
        final_attempt = metadata.get('final_attempt', 1)

        quality_descriptions = {
            'high': '高质量',
            'medium': '中等质量',
            'low': '质量待改进'
        }

        report_lines.append(f"最终质量: {quality_descriptions.get(quality, '未知')} ({quality})")
        report_lines.append(f"可靠性状态: {'✓ 通过' if is_reliable else '✗ 未通过'}")
        report_lines.append(f"生成尝试: {final_attempt}/{attempts_count} 次")

        # 检查结果
        passed_checks = metadata.get('passed_checks', [])
        failed_checks = metadata.get('failed_checks', [])

        if passed_checks:
            report_lines.append("\n✓ 通过的检查项:")
            for check in passed_checks:
                report_lines.append(f"  • {check}")

        if failed_checks:
            report_lines.append("\n✗ 未通过的检查项:")
            for check in failed_checks:
                report_lines.append(f"  • {check}")

        # 具体问题
        issues = metadata.get('issues', [])
        if issues:
            report_lines.append("\n⚠️ 发现的具体问题:")
            for i, issue in enumerate(issues, 1):
                report_lines.append(f"  {i}. {issue}")

        # 质量改进建议
        if quality == 'low' and failed_checks:
            report_lines.append("\n💡 质量改进建议:")
            if '信息准确性' in failed_checks:
                report_lines.append("  • 建议检查生成内容是否准确反映原始信息")
            if '任务符合度' in failed_checks:
                report_lines.append("  • 建议确保生成内容完全符合任务要求")
            if '逻辑一致性' in failed_checks:
                report_lines.append("  • 建议检查内容是否存在逻辑矛盾")
            if '语言质量' in failed_checks:
                report_lines.append("  • 建议优化语言表达和专业性")
            if '完整性' in failed_checks:
                report_lines.append("  • 建议补充缺失的关键信息")

        # 各次尝试的简要信息
        all_attempts = metadata.get('all_attempts', [])
        if len(all_attempts) > 1:
            report_lines.append("\n📊 各次尝试质量对比:")
            for attempt in all_attempts:
                status_icon = "✓" if attempt['attempt_number'] == final_attempt else " "
                report_lines.append(
                    f"  {status_icon} 尝试#{attempt['attempt_number']}: {quality_descriptions.get(attempt['quality'], '未知')}")

        report_lines.append("--- 报告结束 ---")

        return "\n".join(report_lines)

    @staticmethod
    def get_detailed_debug_info(metadata: Dict) -> str:
        """获取详细的调试信息"""
        debug_info = []
        debug_info.append("=== 可靠性检查调试信息 ===")
        debug_info.append(f"最终质量: {metadata.get('quality', 'unknown')}")
        debug_info.append(f"是否可靠: {metadata.get('reliable', False)}")
        debug_info.append(f"总尝试次数: {metadata.get('attempts', 0)}")
        debug_info.append(f"最终使用第几次尝试: {metadata.get('final_attempt', 0)}")

        if metadata.get('issues'):
            debug_info.append("发现的问题:")
            for issue in metadata['issues']:
                debug_info.append(f"  - {issue}")

        if metadata.get('passed_checks'):
            debug_info.append("通过的检查:")
            for check in metadata['passed_checks']:
                debug_info.append(f"  ✓ {check}")

        # 所有尝试的详细信息
        if metadata.get('all_attempts'):
            debug_info.append("各次尝试详情:")
            for attempt in metadata['all_attempts']:
                debug_info.append(f"  尝试#{attempt['attempt_number']}: 质量={attempt['quality']}")

        return "\n".join(debug_info)