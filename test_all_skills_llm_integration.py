#!/usr/bin/env python3
"""
所有Skill的LLM完整能力验证测试

真正调用大模型API，验证所有Skill的LLM集成能力。
"""

import asyncio
import sys
import os
import json
import time
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from skill_architecture.models import SkillContext
from skill_architecture.coding_skill import CodingSkill
from skill_architecture.knowledge_skill import KnowledgeSkill
from skill_architecture.ppt_skill import PPTSkill
from skill_architecture.evaluation_skill import EvaluationSkill
from skill_architecture.file_skill import FileSkill
from skill_architecture.format_skill import FormatSkill
from skill_architecture.persona_skill import PersonaSkill
from llm_provider import MiniMaxProvider


class LLMProviderAdapter:
    """将MiniMaxProvider的stream_chat适配为generate接口"""
    def __init__(self, provider):
        self.provider = provider
    
    async def generate(self, prompt: str) -> str:
        response_parts = []
        for chunk in self.provider.stream_chat(prompt):
            response_parts.append(chunk)
        return "".join(response_parts)


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


async def setup_llm():
    """初始化LLM提供者"""
    print("\n[1/2] 初始化LLM提供者...")
    try:
        minimax_provider = MiniMaxProvider()
        adapter = LLMProviderAdapter(minimax_provider)
        print("   OK MiniMax提供者初始化成功")
        return adapter
    except Exception as e:
        print(f"   FAIL LLM提供者初始化失败: {e}")
        return None


async def setup_skills(llm_adapter):
    """初始化所有Skill"""
    print("\n[2/2] 初始化所有Skill...")
    skills = {}
    skill_classes = {
        "CodingSkill": CodingSkill,
        "KnowledgeSkill": KnowledgeSkill,
        "PPTSkill": PPTSkill,
        "EvaluationSkill": EvaluationSkill,
        "FileSkill": FileSkill,
        "FormatSkill": FormatSkill,
        "PersonaSkill": PersonaSkill,
    }
    
    for name, cls in skill_classes.items():
        try:
            config = {"project_root": PROJECT_ROOT, "llm_provider": llm_adapter}
            skill = cls(config)
            success = await skill.initialize()
            status = "OK" if success else "WARN(未完全初始化)"
            skills[name] = skill
            print(f"   {status} {name}")
        except Exception as e:
            print(f"   FAIL {name}: {e}")
    
    print(f"\n   成功初始化 {len(skills)} 个Skill")
    return skills


# ==================== 测试用例 ====================

async def run_test(name, skill, context):
    """运行单个测试"""
    print(f"\n  测试: {name}")
    start = time.time()
    try:
        result = await skill.execute(context)
        duration = time.time() - start
        success = result.success
        data = result.data if result.data else {}
        error = getattr(result, 'error', '') or ''
        preview = str(data)[:300]
        print(f"    {'OK' if success else 'FAIL'} ({duration:.2f}s)")
        if error:
            print(f"    错误: {error[:200]}")
        print(f"    预览: {preview[:150]}...")
        return {"name": name, "passed": success, "duration": duration, "data_preview": preview, "error": error}
    except Exception as e:
        duration = time.time() - start
        print(f"    EXCEPTION ({duration:.2f}s): {e}")
        return {"name": name, "passed": False, "duration": duration, "error": str(e)}


async def test_coding_skills(skills):
    """CodingSkill测试"""
    print("\n" + "=" * 60)
    print("CodingSkill 测试")
    print("=" * 60)
    skill = skills.get("CodingSkill")
    if not skill:
        return []
    
    results = []
    
    # Bug修复
    ctx = SkillContext(intent="bug_fix", input_data={
        "code": "def avg(nums): return sum(nums)/len(nums)\navg([])",
        "language": "python",
        "bug_description": "空列表导致除零错误"
    })
    results.append(await run_test("Bug修复", skill, ctx))
    
    # 代码审查
    ctx = SkillContext(intent="code_review", input_data={
        "code": "def process(data):\n    result=[]\n    for i in data:\n        if i>0: result.append(i*2)\n    return result",
        "language": "python"
    })
    results.append(await run_test("代码审查", skill, ctx))
    
    # 代码解释
    ctx = SkillContext(intent="explain", input_data={
        "code": "def fib(n):\n    if n<=1: return n\n    return fib(n-1)+fib(n-2)",
        "language": "python",
        "user_message": "请解释这段代码的逻辑"
    })
    results.append(await run_test("代码解释", skill, ctx))
    
    # 代码重构
    ctx = SkillContext(intent="refactor", input_data={
        "code": "def get_user(uid):\n    import sqlite3\n    conn=sqlite3.connect('db')\n    c=conn.cursor()\n    c.execute(f'SELECT * FROM users WHERE id={uid}')\n    return c.fetchone()",
        "language": "python",
        "user_message": "修复SQL注入漏洞并改进代码结构"
    })
    results.append(await run_test("代码重构", skill, ctx))
    
    # 代码分析
    ctx = SkillContext(intent="analyze", input_data={
        "code": "class Cache:\n    def __init__(self): self.data={}\n    def get(self,k): return self.data.get(k)\n    def set(self,k,v): self.data[k]=v",
        "language": "python",
        "user_message": "分析这段代码的架构设计"
    })
    results.append(await run_test("代码分析", skill, ctx))
    
    return results


async def test_knowledge_skills(skills):
    """KnowledgeSkill测试"""
    print("\n" + "=" * 60)
    print("KnowledgeSkill 测试")
    print("=" * 60)
    skill = skills.get("KnowledgeSkill")
    if not skill:
        return []
    
    results = []
    
    # 知识图谱统计
    ctx = SkillContext(intent="get_statistics", input_data={})
    results.append(await run_test("知识图谱统计", skill, ctx))
    
    # 知识查询
    ctx = SkillContext(intent="knowledge_query", input_data={"query": "Python"})
    results.append(await run_test("知识查询", skill, ctx))
    
    # 实体搜索
    ctx = SkillContext(intent="search_entity", input_data={"query": "Skill"})
    results.append(await run_test("实体搜索", skill, ctx))
    
    # 知识导出
    ctx = SkillContext(intent="knowledge_export", input_data={"format": "json"})
    results.append(await run_test("知识导出", skill, ctx))
    
    return results


async def test_ppt_skills(skills):
    """PPTSkill测试"""
    print("\n" + "=" * 60)
    print("PPTSkill 测试")
    print("=" * 60)
    skill = skills.get("PPTSkill")
    if not skill:
        return []
    
    results = []
    
    # PPT生成（使用Markdown格式）
    ctx = SkillContext(intent="ppt_generate", input_data={
        "action": "generate",
        "content": "# AI发展历史\n\n## 1950s 图灵时代\n- 图灵测试提出\n- 人工智能概念诞生\n\n## 1980s 专家系统\n- 知识工程兴起\n- 专家系统广泛应用\n\n## 2010s 深度学习\n- 神经网络复兴\n- AlphaGo击败人类\n\n## 2020s 大语言模型\n- GPT系列\n- 多模态AI",
        "title": "AI发展历史",
        "output_dir": PROJECT_ROOT
    })
    results.append(await run_test("PPT生成", skill, ctx))
    
    # PPT建议（需要context字段）
    ctx = SkillContext(intent="ppt_suggest", input_data={
        "action": "suggest",
        "context": {
            "title": "机器学习算法介绍",
            "slides": [
                {"title": "引言", "content": "机器学习概述"},
                {"title": "监督学习", "content": "分类和回归"}
            ]
        },
        "focus": "content"
    })
    results.append(await run_test("PPT建议", skill, ctx))
    
    # PPT检查（需要context字段）
    ctx = SkillContext(intent="ppt_check", input_data={
        "action": "check",
        "context": {
            "title": "测试PPT",
            "slides": [
                {"title": "引言", "content": "项目背景介绍"},
                {"title": "方法", "content": "技术方案详细说明"},
                {"title": "结果", "content": "实验数据分析"}
            ]
        }
    })
    results.append(await run_test("PPT检查", skill, ctx))
    
    # PPT分析（需要context字段）
    ctx = SkillContext(intent="ppt_analyze", input_data={
        "action": "analyze",
        "context": {
            "title": "技术方案汇报",
            "slides": [
                {"title": "引言", "content": "项目背景"},
                {"title": "方法", "content": "技术方案"},
                {"title": "结果", "content": "数据分析"}
            ]
        }
    })
    results.append(await run_test("PPT分析", skill, ctx))
    
    return results


async def test_evaluation_skills(skills):
    """EvaluationSkill测试"""
    print("\n" + "=" * 60)
    print("EvaluationSkill 测试")
    print("=" * 60)
    skill = skills.get("EvaluationSkill")
    if not skill:
        return []
    
    results = []
    
    # 内容评价
    ctx = SkillContext(intent="evaluate", input_data={
        "content": "Python是一种广泛使用的高级编程语言，以其简洁易读的语法而闻名。",
        "scene": "polish"
    })
    results.append(await run_test("内容评价(polish)", skill, ctx))
    
    # 翻译评价
    ctx = SkillContext(intent="evaluate", input_data={
        "content": "Python is a widely-used high-level programming language known for its clean and readable syntax.",
        "scene": "translate",
        "input_text": "Python是一种广泛使用的高级编程语言，以其简洁易读的语法而闻名。"
    })
    results.append(await run_test("翻译评价", skill, ctx))
    
    # 代码评价
    ctx = SkillContext(intent="evaluate", input_data={
        "content": "def hello():\n    print('Hello, World!')",
        "scene": "code"
    })
    results.append(await run_test("代码评价", skill, ctx))
    
    return results


async def test_file_skills(skills):
    """FileSkill测试"""
    print("\n" + "=" * 60)
    print("FileSkill 测试")
    print("=" * 60)
    skill = skills.get("FileSkill")
    if not skill:
        return []
    
    results = []
    
    # 目录列表
    ctx = SkillContext(intent="file_list", input_data={
        "action": "list",
        "directory": PROJECT_ROOT,
        "pattern": "*.md"
    })
    results.append(await run_test("目录列表", skill, ctx))
    
    # 文件读取
    test_file = os.path.join(PROJECT_ROOT, "README.md")
    if os.path.exists(test_file):
        ctx = SkillContext(intent="file_read", input_data={
            "action": "read",
            "file_path": test_file,
            "format": "text"
        })
        results.append(await run_test("文件读取(README.md)", skill, ctx))
    
    return results


async def test_format_skills(skills):
    """FormatSkill测试"""
    print("\n" + "=" * 60)
    print("FormatSkill 测试")
    print("=" * 60)
    skill = skills.get("FormatSkill")
    if not skill:
        return []
    
    results = []
    
    # 文本转表格
    ctx = SkillContext(intent="text_to_table", input_data={
        "content": "姓名,年龄,职业\n张三,25,工程师\n李四,30,设计师",
        "output_format": "markdown"
    })
    results.append(await run_test("文本转表格", skill, ctx))
    
    # Markdown转Word
    ctx = SkillContext(intent="md_to_docx", input_data={
        "content": "# 测试标题\n\n这是测试内容",
        "output_path": os.path.join(PROJECT_ROOT, "test_format_output.docx")
    })
    results.append(await run_test("Markdown转Word", skill, ctx))
    
    return results


async def test_persona_skills(skills):
    """PersonaSkill测试"""
    print("\n" + "=" * 60)
    print("PersonaSkill 测试")
    print("=" * 60)
    skill = skills.get("PersonaSkill")
    if not skill:
        return []
    
    results = []
    
    # 人设列表
    ctx = SkillContext(intent="persona_list", input_data={})
    results.append(await run_test("人设列表", skill, ctx))
    
    # 获取人设
    ctx = SkillContext(intent="persona_get", input_data={"persona_id": "default"})
    results.append(await run_test("获取人设(default)", skill, ctx))
    
    # 获取code人设
    ctx = SkillContext(intent="persona_get", input_data={"persona_id": "code"})
    results.append(await run_test("获取人设(code)", skill, ctx))
    
    return results


# ==================== 主流程 ====================

def generate_report(all_results, total_time):
    """生成并保存报告"""
    passed = [r for r in all_results if r.get("passed")]
    failed = [r for r in all_results if not r.get("passed")]
    
    report = {
        "test_name": "所有Skill的LLM完整能力验证测试",
        "test_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_tests": len(all_results),
        "passed": len(passed),
        "failed": len(failed),
        "pass_rate": f"{len(passed)/len(all_results)*100:.1f}%" if all_results else "0%",
        "total_duration": f"{total_time:.2f}s",
        "results": all_results
    }
    
    report_file = os.path.join(PROJECT_ROOT, "all_skills_llm_integration_report.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # 打印摘要
    print("\n" + "=" * 60)
    print("测试报告摘要")
    print("=" * 60)
    print(f"  总测试数: {len(all_results)}")
    print(f"  通过:     {len(passed)}")
    print(f"  失败:     {len(failed)}")
    print(f"  通过率:   {report['pass_rate']}")
    print(f"  总耗时:   {report['total_duration']}")
    
    if failed:
        print("\n  失败的测试:")
        for t in failed:
            err = t.get("error", "结果为False")
            print(f"    - {t['name']}: {err}")
    
    print(f"\n  报告已保存: {report_file}")
    return report


async def cleanup_skills(skills):
    """清理资源"""
    print("\n清理资源...")
    for name, skill in skills.items():
        try:
            await skill.cleanup()
            print(f"  OK {name}")
        except Exception as e:
            print(f"  FAIL {name}: {e}")


async def main():
    print("=" * 60)
    print("所有Skill的LLM完整能力验证测试")
    print("=" * 60)
    
    # 初始化
    llm_adapter = await setup_llm()
    if not llm_adapter:
        print("LLM初始化失败，退出")
        sys.exit(1)
    
    skills = await setup_skills(llm_adapter)
    if not skills:
        print("无Skill初始化成功，退出")
        sys.exit(1)
    
    # 运行所有测试
    start_time = time.time()
    all_results = []
    
    all_results.extend(await test_coding_skills(skills))
    all_results.extend(await test_knowledge_skills(skills))
    all_results.extend(await test_ppt_skills(skills))
    all_results.extend(await test_evaluation_skills(skills))
    all_results.extend(await test_file_skills(skills))
    all_results.extend(await test_format_skills(skills))
    all_results.extend(await test_persona_skills(skills))
    
    total_time = time.time() - start_time
    
    # 生成报告
    report = generate_report(all_results, total_time)
    
    # 清理
    await cleanup_skills(skills)
    
    # 退出码
    sys.exit(0 if report.get("failed", 0) == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
