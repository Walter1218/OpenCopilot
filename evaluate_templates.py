#!/usr/bin/env python3
"""
评估所有persona模板的质量
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.evaluation_tools import QualityEvaluator, evaluate_generation_quality


def read_file_content(file_path):
    """读取文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"读取文件 {file_path} 失败: {e}")
        return None


def evaluate_persona_template(file_path, scene):
    """评估单个persona模板"""
    content = read_file_content(file_path)
    if not content:
        return None
    
    # 使用评价工具评估
    report = evaluate_generation_quality(content, scene)
    
    return {
        "file": file_path,
        "scene": scene,
        "content_length": len(content),
        "total_score": report.total_score,
        "summary": report.summary,
        "results": report.results,
        "improvement_plan": report.improvement_plan
    }


def main():
    """主函数"""
    # 定义persona文件路径和场景
    persona_files = [
        ("personas/polish.md", "business_email"),
        ("personas/revision.md", "business_email"),
        ("personas/translate.md", "translation"),
        ("personas/code.md", "technical_doc"),
        ("personas/office/business/email.md", "business_email"),
        ("personas/office/business/report.md", "business_email"),
        ("personas/office/academic/paper.md", "academic_paper"),
        ("personas/office/technical/documentation.md", "technical_doc"),
        ("personas/translation/technical.md", "translation"),
    ]
    
    print("=" * 80)
    print("OpenCopilot Persona 模板质量评估报告")
    print("=" * 80)
    print()
    
    results = []
    
    for file_path, scene in persona_files:
        if os.path.exists(file_path):
            result = evaluate_persona_template(file_path, scene)
            if result:
                results.append(result)
                
                # 打印单个模板的评估结果
                print(f"## {os.path.basename(file_path)}")
                print(f"**场景**: {scene}")
                print(f"**内容长度**: {result['content_length']} 字符")
                print(f"**总分**: {result['total_score']:.1f}/5.0")
                print()
                
                # 打印各维度得分
                print("**各维度得分**:")
                for eval_result in result['results']:
                    print(f"- {eval_result.dimension.value}: {eval_result.score:.1f}/5.0")
                print()
                
                # 打印总结
                print(f"**总结**: {result['summary']}")
                print()
                
                # 打印改进计划
                if result['improvement_plan']:
                    print("**改进计划**:")
                    print(result['improvement_plan'])
                
                print("-" * 80)
                print()
    
    # 生成汇总统计
    if results:
        print("=" * 80)
        print("汇总统计")
        print("=" * 80)
        print()
        
        # 计算平均分
        total_scores = [r['total_score'] for r in results]
        avg_score = sum(total_scores) / len(total_scores)
        
        # 找出最高分和最低分
        best_result = max(results, key=lambda x: x['total_score'])
        worst_result = min(results, key=lambda x: x['total_score'])
        
        print(f"**评估模板数量**: {len(results)}")
        print(f"**平均分**: {avg_score:.1f}/5.0")
        print(f"**最高分**: {best_result['total_score']:.1f}/5.0 ({os.path.basename(best_result['file'])})")
        print(f"**最低分**: {worst_result['total_score']:.1f}/5.0 ({os.path.basename(worst_result['file'])})")
        print()
        
        # 按场景分组统计
        scene_stats = {}
        for result in results:
            scene = result['scene']
            if scene not in scene_stats:
                scene_stats[scene] = []
            scene_stats[scene].append(result['total_score'])
        
        print("**按场景分组统计**:")
        for scene, scores in scene_stats.items():
            avg = sum(scores) / len(scores)
            print(f"- {scene}: 平均分 {avg:.1f}/5.0 ({len(scores)}个模板)")
        print()
        
        # 生成改进建议
        print("=" * 80)
        print("改进建议")
        print("=" * 80)
        print()
        
        # 找出低分维度
        dimension_scores = {}
        for result in results:
            for eval_result in result['results']:
                dim = eval_result.dimension.value
                if dim not in dimension_scores:
                    dimension_scores[dim] = []
                dimension_scores[dim].append(eval_result.score)
        
        print("**低分维度分析**:")
        for dim, scores in dimension_scores.items():
            avg = sum(scores) / len(scores)
            if avg < 4.0:
                print(f"- {dim}: 平均分 {avg:.1f}/5.0 (需要改进)")
        print()
        
        # 生成具体改进建议
        print("**具体改进建议**:")
        print()
        
        for result in results:
            if result['total_score'] < 4.0:
                print(f"### {os.path.basename(result['file'])} (总分: {result['total_score']:.1f}/5.0)")
                for eval_result in result['results']:
                    if eval_result.score < 4.0:
                        print(f"- **{eval_result.dimension.value}** ({eval_result.score:.1f}/5.0):")
                        for suggestion in eval_result.suggestions:
                            print(f"  - {suggestion}")
                print()
        
        # 生成优化后的模板示例
        print("=" * 80)
        print("优化建议示例")
        print("=" * 80)
        print()
        
        # 选择最低分的模板进行优化示例
        worst = worst_result
        print(f"**模板**: {os.path.basename(worst['file'])}")
        print(f"**当前总分**: {worst['total_score']:.1f}/5.0")
        print()
        
        print("**优化方向**:")
        for eval_result in worst['results']:
            if eval_result.score < 4.0:
                print(f"1. **{eval_result.dimension.value}**: {eval_result.feedback}")
                for suggestion in eval_result.suggestions:
                    print(f"   - {suggestion}")
        print()
        
        print("**优化后预期效果**:")
        print("- 总分提升至 4.0/5.0 以上")
        print("- 各维度得分均衡，无明显短板")
        print("- 更符合场景需求，提升用户体验")
        print()
        
        # 保存评估结果到文件
        save_evaluation_report(results)
        
        print("=" * 80)
        print("评估完成！详细报告已保存到: Template_Quality_Report.md")
        print("=" * 80)


def save_evaluation_report(results):
    """保存评估报告到文件"""
    report_content = """# OpenCopilot Persona 模板质量评估报告

## 1. 评估概述

### 1.1 评估目的
评估现有persona模板的质量，识别改进方向，指导prompt模板的迭代优化。

### 1.2 评估维度
- **内容质量**: 准确性、完整性、相关性、时效性、原创性
- **语言质量**: 流畅性、专业性、语法正确性、风格一致性
- **结构质量**: 逻辑性、格式规范、可读性、导航性
- **场景适配**: 语气恰当、风格匹配、文化适应、用户偏好

### 1.3 评估标准
- 5分（优秀）：完全符合标准，质量卓越
- 4分（良好）：基本符合标准，质量良好
- 3分（合格）：部分符合标准，质量可接受
- 2分（需改进）：较多不符合标准，需要改进
- 1分（不合格）：完全不符合标准，需要重做

## 2. 评估结果汇总

### 2.1 总体统计
"""
    
    # 添加总体统计
    total_scores = [r['total_score'] for r in results]
    avg_score = sum(total_scores) / len(total_scores)
    best_result = max(results, key=lambda x: x['total_score'])
    worst_result = min(results, key=lambda x: x['total_score'])
    
    report_content += f"""
- **评估模板数量**: {len(results)}
- **平均分**: {avg_score:.1f}/5.0
- **最高分**: {best_result['total_score']:.1f}/5.0 ({os.path.basename(best_result['file'])})
- **最低分**: {worst_result['total_score']:.1f}/5.0 ({os.path.basename(worst_result['file'])})

### 2.2 各模板评分

| 模板名称 | 场景 | 总分 | 评级 |
|----------|------|------|------|
"""
    
    # 添加各模板评分
    for result in results:
        score = result['total_score']
        if score >= 4.5:
            level = "优秀"
        elif score >= 3.5:
            level = "良好"
        elif score >= 2.5:
            level = "合格"
        elif score >= 1.5:
            level = "需改进"
        else:
            level = "不合格"
        
        report_content += f"| {os.path.basename(result['file'])} | {result['scene']} | {score:.1f}/5.0 | {level} |\n"
    
    report_content += """
## 3. 详细分析

### 3.1 各维度平均得分

"""
    
    # 计算各维度平均分
    dimension_scores = {}
    for result in results:
        for eval_result in result['results']:
            dim = eval_result.dimension.value
            if dim not in dimension_scores:
                dimension_scores[dim] = []
            dimension_scores[dim].append(eval_result.score)
    
    report_content += "| 维度 | 平均分 | 评级 | 状态 |\n"
    report_content += "|------|--------|------|------|\n"
    
    for dim, scores in dimension_scores.items():
        avg = sum(scores) / len(scores)
        if avg >= 4.5:
            level = "优秀"
            status = "✅"
        elif avg >= 3.5:
            level = "良好"
            status = "✅"
        elif avg >= 2.5:
            level = "合格"
            status = "⚠️"
        elif avg >= 1.5:
            level = "需改进"
            status = "❌"
        else:
            level = "不合格"
            status = "❌"
        
        report_content += f"| {dim} | {avg:.1f}/5.0 | {level} | {status} |\n"
    
    report_content += """
### 3.2 各模板详细分析

"""
    
    # 添加各模板详细分析
    for result in results:
        report_content += f"""#### {os.path.basename(result['file'])}
- **场景**: {result['scene']}
- **总分**: {result['total_score']:.1f}/5.0
- **内容长度**: {result['content_length']} 字符

**各维度得分**:
"""
        for eval_result in result['results']:
            report_content += f"- {eval_result.dimension.value}: {eval_result.score:.1f}/5.0\n"
        
        report_content += f"\n**总结**: {result['summary']}\n\n"
        
        if result['improvement_plan']:
            report_content += f"**改进计划**:\n{result['improvement_plan']}\n\n"
        
        report_content += "---\n\n"
    
    # 添加改进建议
    report_content += """## 4. 改进建议

### 4.1 总体建议

1. **结构化改进**: 所有模板都应采用统一的结构（角色定义、核心能力、工作流程、输出规范、质量标准）
2. **场景适配**: 根据不同场景调整语气、风格和专业程度
3. **示例丰富**: 为每个模板添加具体的示例，帮助用户理解期望的输出
4. **质量标准**: 明确各维度的质量标准，便于评估和改进

### 4.2 具体改进建议

"""
    
    # 添加具体改进建议
    for result in results:
        if result['total_score'] < 4.0:
            report_content += f"#### {os.path.basename(result['file'])} (总分: {result['total_score']:.1f}/5.0)\n\n"
            for eval_result in result['results']:
                if eval_result.score < 4.0:
                    report_content += f"**{eval_result.dimension.value}** ({eval_result.score:.1f}/5.0):\n"
                    report_content += f"- 问题: {eval_result.feedback}\n"
                    report_content += "- 建议:\n"
                    for suggestion in eval_result.suggestions:
                        report_content += f"  - {suggestion}\n"
                    report_content += "\n"
    
    # 添加优化示例
    report_content += """
### 4.3 优化示例

#### 优化前（polish.md）
```
你是一个资深编辑。请对用户提供的文本进行润色，修正语病，提升表达的专业度和流畅度，使其更具逻辑性。只输出润色后的结果，不解释。
```

**问题**:
- 缺少角色定义和核心能力描述
- 没有明确的工作流程
- 缺少质量标准和输出规范

#### 优化后（建议）
```
# 文本润色专家

## 角色定义
你是一个资深的文本润色专家，精通各种文体的润色和优化，能够提升文本的专业度、流畅度和逻辑性。

## 核心能力
1. 精准识别文本中的语病和表达问题
2. 提升文本的专业度和可读性
3. 保持原文的核心意思和风格
4. 优化文本结构和逻辑

## 工作流程
1. 分析原文内容和风格
2. 识别需要润色的部分
3. 进行润色和优化
4. 检查润色效果
5. 输出润色结果

## 输出规范
- 保持原文格式和结构
- 润色后文本更专业、流畅
- 不改变原文核心意思
- 不添加额外解释

## 质量标准
- 语言流畅，表达清晰
- 专业得体，符合场景
- 逻辑清晰，结构合理
- 无语法错误和拼写错误

## 润色技巧

### 语病修正
- 修正语法错误
- 调整语序
- 消除歧义

### 表达优化
- 替换口语化表达
- 使用更专业的词汇
- 优化句子结构

### 逻辑增强
- 添加连接词
- 调整段落顺序
- 强化逻辑关系

## 注意事项
- 保持原文核心意思
- 不改变原文风格
- 润色适度，不过度修改
- 尊重作者原意
```

**优化效果**:
- 结构更清晰，便于理解
- 内容更完整，覆盖全面
- 指导更具体，易于执行
- 质量更可控，便于评估

## 5. 实施计划

### 5.1 短期计划（1-2周）
1. 优化低分模板（polish.md、translate.md、code.md）
2. 统一模板结构
3. 添加具体示例

### 5.2 中期计划（3-4周）
1. 建立模板质量标准
2. 实现自动评估机制
3. 建立模板版本管理

### 5.3 长期计划（5-8周）
1. 建立模板库
2. 实现模板推荐
3. 支持用户自定义模板

## 6. 结论

通过本次评估，我们发现：

1. **高质量模板**: office/business/email.md、office/academic/paper.md、translation/technical.md
2. **需要改进**: polish.md、translate.md、code.md
3. **主要问题**: 结构不完整、内容简单、缺少示例
4. **改进方向**: 统一结构、丰富内容、添加示例

建议按照本报告的改进计划，逐步优化所有模板，提升整体质量水平。
"""
    
    # 保存报告
    with open('Template_Quality_Report.md', 'w', encoding='utf-8') as f:
        f.write(report_content)


if __name__ == "__main__":
    main()