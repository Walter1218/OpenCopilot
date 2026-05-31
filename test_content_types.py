#!/usr/bin/env python3
"""
内容类型检测测试脚本

测试所有泛化内容类型的识别能力。
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from ppt_cocreation.context_analyzer import ContextAnalyzer, ContentType


def test_content_type_detection():
    """测试内容类型检测"""
    analyzer = ContextAnalyzer()
    
    test_cases = [
        # (内容, 期望类型, 描述)
        
        # === 基础类型 ===
        ("Q1增长10%，Q2增长15%", ContentType.DATA_COMPARISON, "数据对比"),
        ("2024年1月至3月销售额", ContentType.TIME_SERIES, "时间序列"),
        ("第一步：需求分析\n第二步：设计\n第三步：开发", ContentType.PROCESS, "流程步骤"),
        ("姓名：张三，年龄：30岁，职位：工程师", ContentType.PERSON_ATTRIBUTES, "人物属性"),
        ("- 优点1\n- 优点2\n- 优点3", ContentType.LIST, "列表"),
        
        # === 新增泛化类型 ===
        
        # 问题-解决方案
        ("问题：用户流失率高\n解决方案：优化用户体验", ContentType.PROBLEM_SOLUTION, "问题-解决方案"),
        ("痛点：系统响应慢\n如何解决：升级服务器配置", ContentType.PROBLEM_SOLUTION, "问题-解决方案"),
        
        # 优缺点对比
        ("优点：速度快\n缺点：成本高", ContentType.PROS_CONS, "优缺点对比"),
        ("优势在于：技术领先\n劣势在于：市场推广不足", ContentType.PROS_CONS, "优缺点对比"),
        
        # 功能特点
        ("产品特点：支持多平台、具备高可用性、提供智能推荐", ContentType.FEATURE_LIST, "功能特点"),
        ("核心功能：数据分析、智能推荐、自动化报告", ContentType.FEATURE_LIST, "功能特点"),
        
        # 案例分析
        ("案例：某公司通过我们的方案提升了30%效率", ContentType.CASE_STUDY, "案例分析"),
        ("例如：客户A使用后，成本降低了20%", ContentType.CASE_STUDY, "案例分析"),
        
        # 定义/概念
        ("人工智能是指由人工制造的智能系统", ContentType.DEFINITION, "定义/概念"),
        ("什么是机器学习？机器学习是AI的一个分支", ContentType.DEFINITION, "定义/概念"),
        
        # 总结/结论
        ("总结：本次项目取得了显著成果", ContentType.SUMMARY, "总结/结论"),
        ("综上所述，我们的方案具有明显优势", ContentType.SUMMARY, "总结/结论"),
        
        # 引用/名言
        ("乔布斯曾说过：简洁是最终的复杂", ContentType.QUOTE, "引用/名言"),
        ('"创新是区分领导者和追随者的唯一标准" - 乔布斯', ContentType.QUOTE, "引用/名言"),
        
        # 统计数据
        ("据统计，80%的用户对产品满意", ContentType.STATISTICS, "统计数据"),
        ("数据显示，平均增长率达到15%", ContentType.STATISTICS, "统计数据"),
        
        # 通用对比
        ("对比：方案A vs 方案B", ContentType.COMPARISON, "通用对比"),
        ("前者成本高但效果好，后者成本低但效果一般", ContentType.COMPARISON, "通用对比"),
        
        # 组织架构
        ("CEO\n├── CTO\n│   ├── 开发部\n│   └── 测试部\n└── CFO", ContentType.ORGANIZATION, "组织架构"),
        
        # 时间线
        ("里程碑：\n- 2024年1月：项目启动\n- 2024年6月：完成开发\n- 2024年12月：正式上线", ContentType.TIMELINE, "时间线"),
        
        # 论点/论据
        ("论点：远程办公更高效\n论据：多项研究表明...", ContentType.ARGUMENT, "论点/论据"),
    ]
    
    print("=" * 70)
    print("内容类型检测测试")
    print("=" * 70)
    
    pass_count = 0
    fail_count = 0
    fail_cases = []
    
    for content, expected_type, description in test_cases:
        result = analyzer.analyze_content(content)
        detected_type = result.content_type
        confidence = result.confidence
        
        is_pass = detected_type == expected_type
        status = "✅" if is_pass else "❌"
        
        if is_pass:
            pass_count += 1
        else:
            fail_count += 1
            fail_cases.append({
                "description": description,
                "expected": expected_type.value,
                "detected": detected_type.value,
                "confidence": confidence
            })
        
        print(f"{status} {description:15} | 期望: {expected_type.value:20} | 检测: {detected_type.value:20} | 置信度: {confidence:.2f}")
    
    print("\n" + "=" * 70)
    print(f"测试汇总: {pass_count}/{pass_count + fail_count} 通过, {fail_count} 失败")
    print(f"通过率: {pass_count/(pass_count + fail_count)*100:.1f}%")
    
    if fail_cases:
        print("\n失败案例:")
        for case in fail_cases:
            print(f"  - {case['description']}: 期望 {case['expected']}, 检测 {case['detected']}")
    
    print("=" * 70)
    
    return fail_count == 0


def test_llm_classify_func():
    """测试 LLM 分类函数接口"""
    print("\n" + "=" * 70)
    print("LLM 分类函数接口测试")
    print("=" * 70)
    
    # 模拟 LLM 分类函数
    def mock_llm_classify(prompt: str) -> dict:
        # 这里只是模拟，实际使用时会调用真正的 LLM
        if "问题" in prompt and "解决方案" in prompt:
            return {"content_type": "problem_solution", "confidence": 0.9, "reason": "包含问题和解决方案"}
        elif "优点" in prompt and "缺点" in prompt:
            return {"content_type": "pros_cons", "confidence": 0.85, "reason": "包含优缺点对比"}
        else:
            return {"content_type": "text", "confidence": 0.6, "reason": "无法确定具体类型"}
    
    # 测试带 LLM 的分析器
    analyzer = ContextAnalyzer(llm_classify_func=mock_llm_classify)
    
    test_content = "问题：系统响应慢\n解决方案：升级服务器配置"
    
    # 不使用 LLM
    result1 = analyzer.analyze_content(test_content, use_llm=False)
    print(f"不使用 LLM: {result1.content_type.value} (置信度: {result1.confidence:.2f})")
    
    # 使用 LLM
    result2 = analyzer.analyze_content(test_content, use_llm=True)
    print(f"使用 LLM:   {result2.content_type.value} (置信度: {result2.confidence:.2f})")
    
    print("=" * 70)
    
    return True


def main():
    """运行所有测试"""
    print("开始内容类型检测测试...\n")
    
    # 测试正则模式
    success1 = test_content_type_detection()
    
    # 测试 LLM 分类函数
    success2 = test_llm_classify_func()
    
    print("\n" + "=" * 70)
    print("最终结果")
    print("=" * 70)
    print(f"正则模式测试: {'✅ 通过' if success1 else '❌ 失败'}")
    print(f"LLM 接口测试: {'✅ 通过' if success2 else '❌ 失败'}")
    print("=" * 70)
    
    return success1 and success2


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
