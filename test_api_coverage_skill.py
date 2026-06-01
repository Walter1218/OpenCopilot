#!/usr/bin/env python3
"""
API 覆盖率检测脚本

检测所有 Skill 功能是否 100% 接口化
"""

import os
import sys
import json
import asyncio
import aiohttp
from typing import Dict, List, Any, Set
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入 Skill 模块
from skill_architecture import (
    KnowledgeSkill, CodingSkill, PPTSkill,
    EvaluationSkill, FileSkill, FormatSkill, PersonaSkill,
    SkillContext, SkillRegistry
)


class APICoverageAnalyzer:
    """API 覆盖率分析器"""
    
    def __init__(self, base_url: str = "http://localhost:8088"):
        self.base_url = base_url
        self.session = None
        
        # 所有 Skill 及其支持的意图
        self.skills = {
            "knowledge_skill": KnowledgeSkill(),
            "coding_skill": CodingSkill(),
            "ppt_skill": PPTSkill(),
            "evaluation_skill": EvaluationSkill(),
            "file_skill": FileSkill(),
            "format_skill": FormatSkill(),
            "persona_skill": PersonaSkill()
        }
        
        # 现有 API 端点
        self.existing_endpoints: Set[str] = set()
        
        # 覆盖率结果
        self.coverage_results: Dict[str, Any] = {}
    
    async def analyze(self) -> Dict[str, Any]:
        """分析 API 覆盖率"""
        print("=" * 60)
        print("API 覆盖率分析")
        print("=" * 60)
        
        # 1. 获取现有 API 端点
        await self._fetch_existing_endpoints()
        
        # 2. 分析每个 Skill 的意图
        skill_intents = self._analyze_skill_intents()
        
        # 3. 检查覆盖率
        coverage = self._check_coverage(skill_intents)
        
        # 4. 生成报告
        report = self._generate_report(coverage)
        
        return report
    
    async def _fetch_existing_endpoints(self):
        """获取现有 API 端点"""
        print("\n1. 获取现有 API 端点...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/openapi.json") as response:
                    if response.status == 200:
                        openapi_spec = await response.json()
                        paths = openapi_spec.get("paths", {})
                        
                        for path, methods in paths.items():
                            for method in methods.keys():
                                if method.lower() in ["get", "post", "put", "delete"]:
                                    endpoint = f"{method.upper()} {path}"
                                    self.existing_endpoints.add(endpoint)
                        
                        print(f"   找到 {len(self.existing_endpoints)} 个 API 端点")
                    else:
                        print(f"   无法获取 OpenAPI 规范: {response.status}")
        except Exception as e:
            print(f"   获取 API 端点失败: {e}")
    
    def _analyze_skill_intents(self) -> Dict[str, List[str]]:
        """分析每个 Skill 的意图"""
        print("\n2. 分析 Skill 意图...")
        
        skill_intents = {}
        
        for skill_name, skill in self.skills.items():
            intents = skill.metadata.intents
            skill_intents[skill_name] = intents
            print(f"   {skill_name}: {len(intents)} 个意图")
        
        return skill_intents
    
    def _check_coverage(self, skill_intents: Dict[str, List[str]]) -> Dict[str, Any]:
        """检查覆盖率"""
        print("\n3. 检查覆盖率...")
        
        coverage = {
            "total_intents": 0,
            "covered_intents": 0,
            "uncovered_intents": [],
            "skill_coverage": {}
        }
        
        # 意图到 API 端点的映射
        intent_to_endpoint = {
            # KnowledgeSkill
            "knowledge_query": "POST /api/knowledge/query",
            "knowledge_build": "POST /api/knowledge/build",
            "knowledge_export": "POST /api/knowledge/export",
            "search_entity": "POST /api/knowledge/search-entity",
            "find_related": "POST /api/knowledge/find-related",
            "find_path": "POST /api/knowledge/find-path",
            "get_statistics": "GET /api/knowledge/statistics",
            
            # CodingSkill
            "bug_fix": "POST /api/coding/bug-fix",
            "code_review": "POST /api/coding/review",
            "explain": "POST /api/coding/explain",
            "refactor": "POST /api/coding/refactor",
            "enhance_api": "POST /api/coding/enhance-api",
            "analyze": "POST /api/coding/analyze",
            "coding": "POST /api/coding/analyze",
            
            # PPTSkill
            "ppt_generate": "POST /api/ppt/generate",
            "ppt_suggest": "POST /api/ppt/suggest",
            "ppt_check": "POST /api/ppt/check",
            "ppt_analyze": "POST /api/ppt/analyze",
            "ppt_convert": "POST /api/content/convert",
            "ppt_cocreate": "POST /api/ppt/cocreation",
            "presentation": "POST /api/ppt/generate",
            "slides": "POST /api/ppt/generate",
            
            # EvaluationSkill
            "evaluate": "POST /api/evaluation/evaluate",
            "quality_check": "POST /api/evaluation/quality-check",
            "score": "POST /api/evaluation/score",
            "review": "POST /api/evaluation/evaluate",
            "assess": "POST /api/evaluation/evaluate",
            
            # FileSkill
            "file_read": "POST /api/file/read",
            "file_write": "POST /api/file/write",
            "file_convert": "POST /api/file/convert",
            "file_list": "POST /api/file/list",
            "file_delete": "POST /api/file/delete",
            "read_file": "POST /api/file/read",
            "write_file": "POST /api/file/write",
            "convert_file": "POST /api/file/convert",
            
            # FormatSkill
            "md_to_docx": "POST /api/format/md-to-docx",
            "md_to_pptx": "POST /api/format/md-to-pptx",
            "text_to_table": "POST /api/format/text-to-table",
            "format_convert": "POST /api/format/md-to-docx",
            "markdown_convert": "POST /api/format/md-to-docx",
            "document_convert": "POST /api/format/md-to-docx",
            
            # PersonaSkill
            "persona_list": "POST /api/persona/list",
            "persona_get": "POST /api/persona/get",
            "persona_save": "POST /api/persona/save",
            "persona_delete": "POST /api/persona/delete",
            "persona": "POST /api/persona/list",
            "角色管理": "POST /api/persona/list",
            "人设管理": "POST /api/persona/list"
        }
        
        for skill_name, intents in skill_intents.items():
            covered = 0
            uncovered = []
            
            for intent in intents:
                coverage["total_intents"] += 1
                
                endpoint = intent_to_endpoint.get(intent)
                if endpoint and endpoint in self.existing_endpoints:
                    covered += 1
                    coverage["covered_intents"] += 1
                else:
                    uncovered.append(intent)
                    coverage["uncovered_intents"].append({
                        "skill": skill_name,
                        "intent": intent,
                        "expected_endpoint": endpoint
                    })
            
            coverage["skill_coverage"][skill_name] = {
                "total": len(intents),
                "covered": covered,
                "uncovered": uncovered,
                "coverage_rate": covered / len(intents) if intents else 0.0
            }
        
        return coverage
    
    def _generate_report(self, coverage: Dict[str, Any]) -> Dict[str, Any]:
        """生成报告"""
        print("\n4. 生成报告...")
        
        total = coverage["total_intents"]
        covered = coverage["covered_intents"]
        coverage_rate = covered / total if total > 0 else 0.0
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_intents": total,
                "covered_intents": covered,
                "uncovered_intents": total - covered,
                "coverage_rate": coverage_rate
            },
            "skill_coverage": coverage["skill_coverage"],
            "uncovered_intents": coverage["uncovered_intents"],
            "existing_endpoints": sorted(list(self.existing_endpoints))
        }
        
        return report
    
    def print_report(self, report: Dict[str, Any]):
        """打印报告"""
        print("\n" + "=" * 60)
        print("API 覆盖率报告")
        print("=" * 60)
        
        summary = report["summary"]
        print(f"\n总意图数: {summary['total_intents']}")
        print(f"已覆盖: {summary['covered_intents']}")
        print(f"未覆盖: {summary['uncovered_intents']}")
        print(f"覆盖率: {summary['coverage_rate']:.1%}")
        
        print("\n各 Skill 覆盖率:")
        print("-" * 40)
        
        for skill_name, skill_cov in report["skill_coverage"].items():
            status = "✅" if skill_cov["coverage_rate"] == 1.0 else "⚠️"
            print(f"{status} {skill_name}: {skill_cov['coverage_rate']:.1%} ({skill_cov['covered']}/{skill_cov['total']})")
            
            if skill_cov["uncovered"]:
                for intent in skill_cov["uncovered"]:
                    print(f"   - {intent}")
        
        if report["uncovered_intents"]:
            print("\n未覆盖的意图:")
            print("-" * 40)
            for item in report["uncovered_intents"]:
                print(f"  {item['skill']}.{item['intent']}")
                if item["expected_endpoint"]:
                    print(f"    预期端点: {item['expected_endpoint']}")
        
        print("\n现有 API 端点:")
        print("-" * 40)
        for endpoint in report["existing_endpoints"]:
            print(f"  {endpoint}")
        
        print("\n" + "=" * 60)


async def main():
    """主函数"""
    analyzer = APICoverageAnalyzer()
    report = await analyzer.analyze()
    analyzer.print_report(report)
    
    # 保存报告
    report_path = "api_coverage_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n报告已保存到: {report_path}")
    
    return report


if __name__ == "__main__":
    asyncio.run(main())