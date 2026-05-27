#!/usr/bin/env python3
"""
OpenCopilot 划词功能评价系统演示

演示6大划词场景的评价功能：
1. 自动模式 - 类型判断 + 翻译/解释/总结
2. 翻译 - 信达雅
3. 代码解析 - 功能总结 + 漏洞发现
4. 润色 - 语病修正 + 专业度提升
5. 全文修订 - 修订质量 + 联动发现
6. 自定义指令 - 指令遵循度
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.evaluation_tools import (
    evaluate_auto, evaluate_translate, evaluate_code,
    evaluate_polish, evaluate_revision, evaluate_custom,
    OpenCopilotEvaluator, ActionScene
)


def print_separator(title: str):
    """打印分隔线"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_report(report):
    """打印评价报告"""
    print(f"\n📊 评价结果")
    print(f"   场景: {report.scene_label}")
    print(f"   总分: {report.total_score:.1f}/5.0 ({report.level})")
    print(f"\n📋 各维度得分:")
    for result in report.results:
        status = "✅" if result.score >= 4.0 else "⚠️" if result.score >= 3.0 else "❌"
        print(f"   {status} {result.dimension_label}: {result.score:.1f}/5.0 - {result.feedback}")
        if result.suggestions:
            for suggestion in result.suggestions:
                print(f"      💡 {suggestion}")
    print(f"\n{report.summary}")
    print(f"\n{report.improvement_plan}")


def demo_auto():
    """演示自动模式评价"""
    print_separator("1. 自动模式评价")

    # 测试用例1：英文翻译
    print("\n📝 测试用例1：英文输入 → 翻译")
    report = evaluate_auto(
        input_text="Hello World, how are you?",
        output_text="你好世界，你好吗？"
    )
    print_report(report)

    # 测试用例2：代码解释
    print("\n📝 测试用例2：代码输入 → 解释")
    report = evaluate_auto(
        input_text="def add(a, b):\n    return a + b",
        output_text="功能：实现两数相加\n参数：a, b 为数字类型\n返回值：两数之和"
    )
    print_report(report)

    # 测试用例3：普通文本总结
    print("\n📝 测试用例3：普通文本 → 总结")
    report = evaluate_auto(
        input_text="今天天气很好，阳光明媚，适合出门散步。公园里有很多人在锻炼身体。",
        output_text="天气晴朗，公园锻炼人群众多。"
    )
    print_report(report)


def demo_translate():
    """演示翻译评价"""
    print_separator("2. 翻译评价")

    # 测试用例1：简单翻译
    print("\n📝 测试用例1：简单英文翻译")
    report = evaluate_translate(
        input_text="The quick brown fox jumps over the lazy dog.",
        output_text="敏捷的棕色狐狸跳过了懒惰的狗。"
    )
    print_report(report)

    # 测试用例2：专业术语翻译
    print("\n📝 测试用例2：专业术语翻译")
    report = evaluate_translate(
        input_text="Machine Learning is a subset of Artificial Intelligence.",
        output_text="机器学习是人工智能的一个子集。"
    )
    print_report(report)

    # 测试用例3：口语化翻译（应该扣分）
    print("\n📝 测试用例3：口语化翻译（应该扣分）")
    report = evaluate_translate(
        input_text="This movie is really good.",
        output_text="这个电影挺好的。"
    )
    print_report(report)


def demo_code():
    """演示代码解析评价"""
    print_separator("3. 代码解析评价")

    # 测试用例1：简单函数
    print("\n📝 测试用例1：简单函数解析")
    report = evaluate_code(
        input_code="def add(a, b):\n    return a + b",
        output_text="## 功能总结\n实现两数相加功能。\n\n## 潜在问题\n缺少类型检查。\n\n## 优化建议\n建议添加类型提示：\n```python\ndef add(a: int, b: int) -> int:\n    return a + b\n```"
    )
    print_report(report)

    # 测试用例2：有安全漏洞的代码
    print("\n📝 测试用例2：有安全漏洞的代码")
    report = evaluate_code(
        input_code="def query(user_input):\n    sql = \"SELECT * FROM users WHERE name = '\" + user_input + \"'\"\n    return execute(sql)",
        output_text="## 功能总结\n根据用户名查询用户信息。\n\n## 潜在问题\n存在SQL注入风险，直接拼接用户输入到SQL语句中。\n\n## 优化建议\n使用参数化查询：\n```python\ndef query(user_input):\n    sql = \"SELECT * FROM users WHERE name = ?\"\n    return execute(sql, (user_input,))\n```"
    )
    print_report(report)


def demo_polish():
    """演示润色评价"""
    print_separator("4. 润色评价")

    # 测试用例1：口语转正式
    print("\n📝 测试用例1：口语转正式")
    report = evaluate_polish(
        input_text="我觉得这个方案挺好的，应该没问题。",
        output_text="该方案可行性较高，建议予以采纳。"
    )
    print_report(report)

    # 测试用例2：语病修正
    print("\n📝 测试用例2：语病修正")
    report = evaluate_polish(
        input_text="他跑的很快，做的很好。",
        output_text="他跑得很快，做得很好。"
    )
    print_report(report)

    # 测试用例3：专业度提升
    print("\n📝 测试用例3：专业度提升")
    report = evaluate_polish(
        input_text="我们把代码改一下，搞定这个bug。",
        output_text="我们对代码进行修改，修复此缺陷。"
    )
    print_report(report)


def demo_revision():
    """演示全文修订评价"""
    print_separator("5. 全文修订评价")

    # 测试用例1：简单修订（无联动）
    print("\n📝 测试用例1：简单修订（无联动）")
    report = evaluate_revision(
        selection="项目总负责人为张伟",
        full_document="# 项目规划书\n\n## 1. 项目概述\n本项目旨在...\n\n## 2. 团队组织\n项目总负责人为张伟\n\n## 3. 资源与预算\n...",
        output_text="## 📝 修订后文本\n张伟担任项目总负责人，负责项目整体推进与资源协调。\n\n## 🔍 联动影响分析\n✅ 全文未发现需要联动修改的位置\n\n## 💡 修订说明\n将陈述句式调整为更自然的主动表述，并补充了项目总负责人的核心职责描述。"
    )
    print_report(report)

    # 测试用例2：有联动的修订
    print("\n📝 测试用例2：有联动的修订")
    report = evaluate_revision(
        selection="Q3有2位同事离职（前端张三、后端李四）",
        full_document="# 团队报告\n\n当前研发团队总人数35人。\n\n## Q3变动\nQ3有2位同事离职（前端张三、后端李四），预计Q4可补充3位新同事。",
        output_text="## 📝 修订后文本\nQ3末有2位同事离职（前端张三、后端李四），预计Q4可补充3位新同事，届时团队规模将恢复至36人。\n\n## 🔍 联动影响分析\n- **位置**：第四部分'团队与资源'第一句\n- **原文**：当前研发团队总人数35人\n- **建议**：Q3末研发团队在册35人\n- **原因**：与修订后的'Q3末'时间节点保持一致，避免'当前'一词在Q3复盘文档中的歧义\n\n## 💡 修订说明\n1. 补全'Q3末'时间限定，使时间范围更加明确\n2. 补充'届时团队规模将恢复至36人'，形成完整的数量变化闭环"
    )
    print_report(report)


def demo_custom():
    """演示自定义指令评价"""
    print_separator("6. 自定义指令评价")

    # 测试用例1：翻译指令
    print("\n📝 测试用例1：翻译为日语")
    report = evaluate_custom(
        instruction="翻译为日语",
        input_text="Hello World",
        output_text="ハローワールド"
    )
    print_report(report)

    # 测试用例2：修改指令
    print("\n📝 测试用例2：修改为更正式的表达")
    report = evaluate_custom(
        instruction="将以下文本修改为更正式的商务表达",
        input_text="你好，我想问一下价格。",
        output_text="尊敬的客户，您好。请问贵司产品报价如何？"
    )
    print_report(report)

    # 测试用例3：指令遵循度低
    print("\n📝 测试用例3：指令遵循度低（应该扣分）")
    report = evaluate_custom(
        instruction="翻译为法语",
        input_text="Hello World",
        output_text="你好世界"  # 翻译成了中文，不是法语
    )
    print_report(report)


def demo_common():
    """演示跨场景通用维度评价"""
    print_separator("7. 跨场景通用维度评价")

    evaluator = OpenCopilotEvaluator()

    # 测试用例1：输出长度控制
    print("\n📝 测试用例1：输出长度控制")
    report = evaluator.evaluate(
        scene="auto",
        input_text="短文本",
        output_text="短文本的处理结果"
    )
    print_report(report)

    # 测试用例2：错误处理
    print("\n📝 测试用例2：错误处理")
    report = evaluator.evaluate(
        scene="auto",
        input_text="",
        output_text="请输入需要处理的文本"
    )
    print_report(report)

    # 测试用例3：一致性
    print("\n📝 测试用例3：一致性")
    report = evaluator.evaluate(
        scene="auto",
        input_text="测试文本",
        output_text="测试结果：处理完成。"
    )
    print_report(report)


def demo_edge_cases():
    """演示边界情况处理维度评价"""
    print_separator("8. 边界情况处理维度评价")

    evaluator = OpenCopilotEvaluator()

    # 测试用例1：空输入处理
    print("\n📝 测试用例1：空输入处理")
    report = evaluator.evaluate(
        scene="auto",
        input_text="",
        output_text="请输入需要处理的文本"
    )
    print_report(report)

    # 测试用例2：无效输入处理
    print("\n📝 测试用例2：无效输入处理")
    report = evaluator.evaluate(
        scene="auto",
        input_text="asdfghjkl",
        output_text="无法识别输入内容，请重新输入"
    )
    print_report(report)

    # 测试用例3：模糊指令处理
    print("\n📝 测试用例3：模糊指令处理")
    report = evaluator.evaluate(
        scene="custom",
        input_text="原始文本",
        output_text="请问您希望如何修改？请提供更具体的指令。",
        instruction="修改一下"
    )
    print_report(report)


def demo_summary():
    """演示汇总统计"""
    print_separator("9. 汇总统计")

    evaluator = OpenCopilotEvaluator()

    # 创建测试用例
    test_cases = [
        ("auto", "Hello World", "你好世界", None, None, None),
        ("auto", "def add(a, b): return a + b", "功能：两数相加", None, None, None),
        ("translate", "The quick brown fox", "敏捷的棕色狐狸", None, None, None),
        ("translate", "Machine Learning", "机器学习", None, None, None),
        ("code", "def add(a, b): return a + b", "功能：两数相加", None, None, None),
        ("polish", "我觉得挺好的", "该方案可行性较高", None, None, None),
        ("polish", "他跑的很快", "他跑得很快", None, None, None),
        ("revision", "项目总负责人为张伟", "📝 修订后文本：...", None, None, "完整文档..."),
        ("custom", "Hello World", "ハローワールド", None, "翻译为日语", None),
    ]

    # 运行所有测试
    results_by_scene = {}
    for scene, input_text, output_text, reference, instruction, full_document in test_cases:
        report = evaluator.evaluate(
            scene=scene,
            input_text=input_text,
            output_text=output_text,
            reference=reference,
            instruction=instruction,
            full_document=full_document
        )

        if scene not in results_by_scene:
            results_by_scene[scene] = []
        results_by_scene[scene].append(report.total_score)

    # 打印汇总
    print("\n📊 各场景平均分：\n")
    for scene, scores in results_by_scene.items():
        avg_score = sum(scores) / len(scores)
        level = "优秀" if avg_score >= 4.5 else "良好" if avg_score >= 3.5 else "合格" if avg_score >= 2.5 else "需改进"
        print(f"   {scene:12s}: {avg_score:.1f}/5.0 ({level}) - {len(scores)}个测试用例")

    all_scores = [s for scores in results_by_scene.values() for s in scores]
    total_avg = sum(all_scores) / len(all_scores)
    total_level = "优秀" if total_avg >= 4.5 else "良好" if total_avg >= 3.5 else "合格" if total_avg >= 2.5 else "需改进"
    print(f"\n   {'总体':12s}: {total_avg:.1f}/5.0 ({total_level}) - {len(all_scores)}个测试用例")


def main():
    """主函数"""
    print("🚀 OpenCopilot 划词功能评价系统演示")
    print("=" * 80)
    print("本演示展示围绕划词6大核心场景设计的评价体系")
    print("=" * 80)

    # 运行各场景演示
    demo_auto()
    demo_translate()
    demo_code()
    demo_polish()
    demo_revision()
    demo_custom()
    demo_common()
    demo_edge_cases()
    demo_summary()

    print("\n" + "=" * 80)
    print("  演示完成！")
    print("=" * 80)
    print("\n💡 提示：")
    print("   - 评价维度围绕划词功能设计，更精准地评估AI输出质量")
    print("   - 每个场景有独立的评价维度和权重")
    print("   - 包含跨场景通用维度：输出长度控制、错误处理、一致性")
    print("   - 包含边界情况维度：空输入处理、无效输入处理、模糊指令处理")
    print("   - 评价结果可指导Prompt优化和功能改进")
    print("   - 详细文档请查看 Quality_Evaluation_Framework.md")


if __name__ == "__main__":
    main()
