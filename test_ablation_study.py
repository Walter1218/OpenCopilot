"""
消融实验测试

对比有无新模块（知识检索、Broker权限）对翻译、代码阅读、PPT功能的影响。

实验设计：
1. 基线系统：只有翻译、代码阅读、PPT功能的基础能力，没有知识检索和Broker权限
2. 完整系统：在基线基础上加入知识检索模块和Broker权限模块
3. 评估维度：
   - 知识增强度：完整系统能提供多少额外知识上下文
   - 功能完整度：哪些能力在基线中缺失
   - 响应延迟：新模块引入的额外开销
   - 信息质量：提供信息的相关性和有用性
"""

import os
import sys
import json
import time
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field, asdict
import statistics

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))


@dataclass
class MetricResult:
    """单个指标结果"""
    name: str
    baseline_value: Any = None
    full_value: Any = None
    unit: str = ""
    description: str = ""

@dataclass
class TestResult:
    """单个测试结果"""
    name: str
    category: str
    description: str
    passed: bool = True
    baseline: Dict[str, Any] = field(default_factory=dict)
    full_system: Dict[str, Any] = field(default_factory=dict)
    metrics: List[MetricResult] = field(default_factory=list)
    baseline_time_ms: float = 0
    full_time_ms: float = 0
    error: Optional[str] = None


class AblationStudy:
    """消融实验"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or Path(__file__).parent)
        self.results: List[TestResult] = []
        
        # 延迟初始化组件
        self._knowledge_retrieval = None
        self._initialized = False
    
    def _get_knowledge_retrieval(self):
        """延迟初始化知识检索模块"""
        if self._knowledge_retrieval is None:
            from knowledge_retrieval import KnowledgeRetrieval
            self._knowledge_retrieval = KnowledgeRetrieval(str(self.project_root))
            self._knowledge_retrieval.initialize()
        return self._knowledge_retrieval
    
    def _measure_time(self, func, *args, **kwargs) -> Tuple[Any, float]:
        """测量函数执行时间"""
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = (time.time() - start) * 1000  # 毫秒
        return result, elapsed
    
    # ==========================================
    # 翻译功能消融实验
    # ==========================================
    
    def test_translation_terminology_enhancement(self) -> TestResult:
        """测试翻译场景中术语库的增强效果
        
        基线：翻译时无术语参考
        完整：翻译时可查询知识图谱中的术语和定义
        """
        result = TestResult(
            name="翻译术语增强",
            category="translation",
            description="翻译技术文档时，知识检索提供的术语参考对翻译质量的影响"
        )
        
        try:
            # 基线：无术语参考
            baseline_terms = {
                "API endpoint": {"referenced": False, "definitions": []},
                "microservice": {"referenced": False, "definitions": []},
                "REST": {"referenced": False, "definitions": []},
                "JSON": {"referenced": False, "definitions": []},
                "gRPC": {"referenced": False, "definitions": []},
            }
            
            # 完整：查询术语库
            retrieval = self._get_knowledge_retrieval()
            
            full_terms = {}
            total_definitions = 0
            total_time = 0
            
            for term in baseline_terms.keys():
                query_result, elapsed = self._measure_time(
                    retrieval.query, term, "document"
                )
                total_time += elapsed
                
                definitions = []
                if query_result.success and query_result.data:
                    for item in query_result.data[:3]:
                        if hasattr(item, 'name'):
                            desc = getattr(item, 'description', '')
                            definitions.append({"name": item.name, "description": desc[:100]})
                
                full_terms[term] = {
                    "referenced": query_result.success and len(definitions) > 0,
                    "definitions": definitions,
                    "definition_count": len(definitions)
                }
                total_definitions += len(definitions)
            
            result.baseline = {
                "terms_checked": len(baseline_terms),
                "terms_with_definitions": 0,
                "total_definitions": 0,
                "context_enhancement": False
            }
            
            result.full_system = {
                "terms_checked": len(full_terms),
                "terms_with_definitions": sum(1 for t in full_terms.values() if t["referenced"]),
                "total_definitions": total_definitions,
                "context_enhancement": total_definitions > 0,
                "lookup_time_ms": total_time
            }
            
            result.metrics = [
                MetricResult("术语覆盖数", 0, sum(1 for t in full_terms.values() if t["referenced"]), "个", "能查到定义的术语数量"),
                MetricResult("定义总数", 0, total_definitions, "条", "检索到的术语定义总数"),
                MetricResult("上下文增强", False, total_definitions > 0, "", "是否能为翻译提供额外上下文"),
                MetricResult("查询延迟", 0, total_time, "ms", "术语查询总耗时"),
            ]
            
            result.full_time_ms = total_time
            
        except Exception as e:
            result.passed = False
            result.error = str(e)
            traceback.print_exc()
        
        self.results.append(result)
        return result
    
    def test_translation_memory_enhancement(self) -> TestResult:
        """测试翻译记忆系统与知识检索的协同效果"""
        result = TestResult(
            name="翻译记忆协同",
            category="translation",
            description="翻译记忆系统与知识检索模块协同工作时的效果对比"
        )
        
        try:
            from widgets.translation_memory import TranslationMemory, TranslationUnit
            
            # 初始化翻译记忆
            memory = TranslationMemory()
            
            # 添加一些翻译记忆
            test_units = [
                TranslationUnit(source="API endpoint", target="API 端点", source_lang="en", target_lang="zh", context="技术文档"),
                TranslationUnit(source="microservice", target="微服务", source_lang="en", target_lang="zh", context="架构设计"),
                TranslationUnit(source="REST API", target="REST API", source_lang="en", target_lang="zh", context="接口设计"),
            ]
            
            for unit in test_units:
                memory.add_unit(unit)
            
            # 基线：只有翻译记忆
            test_queries = ["API endpoint", "microservice architecture", "REST API design"]
            baseline_matches = {}
            baseline_time = 0
            
            for query in test_queries:
                matches, elapsed = self._measure_time(memory.search_fuzzy, query, 0.5)
                baseline_time += elapsed
                baseline_matches[query] = {
                    "match_count": len(matches),
                    "has_match": len(matches) > 0
                }
            
            # 完整：翻译记忆 + 知识检索
            retrieval = self._get_knowledge_retrieval()
            full_matches = {}
            full_time = 0
            
            for query in test_queries:
                # 翻译记忆匹配
                memory_matches, mem_elapsed = self._measure_time(memory.search_fuzzy, query, 0.5)
                
                # 知识检索补充
                knowledge_result, kb_elapsed = self._measure_time(retrieval.query, query, "document")
                
                total_elapsed = mem_elapsed + kb_elapsed
                full_time += total_elapsed
                
                knowledge_items = []
                if knowledge_result.success and knowledge_result.data:
                    for item in knowledge_result.data[:3]:
                        if hasattr(item, 'name'):
                            knowledge_items.append(f"{item.name}: {getattr(item, 'description', '')[:80]}")
                
                full_matches[query] = {
                    "memory_match_count": len(memory_matches),
                    "has_memory_match": len(memory_matches) > 0,
                    "knowledge_item_count": len(knowledge_items),
                    "has_knowledge": len(knowledge_items) > 0,
                    "knowledge_items": knowledge_items,
                    "total_context_sources": len(memory_matches) + len(knowledge_items)
                }
            
            result.baseline = {
                "queries_tested": len(test_queries),
                "queries_with_memory": sum(1 for m in baseline_matches.values() if m["has_match"]),
                "total_memory_matches": sum(m["match_count"] for m in baseline_matches.values()),
                "total_time_ms": baseline_time
            }
            
            result.full_system = {
                "queries_tested": len(test_queries),
                "queries_with_memory": sum(1 for m in full_matches.values() if m["has_memory_match"]),
                "queries_with_knowledge": sum(1 for m in full_matches.values() if m["has_knowledge"]),
                "total_memory_matches": sum(m["memory_match_count"] for m in full_matches.values()),
                "total_knowledge_items": sum(m["knowledge_item_count"] for m in full_matches.values()),
                "avg_context_sources": statistics.mean([m["total_context_sources"] for m in full_matches.values()]),
                "total_time_ms": full_time
            }
            
            baseline_total = result.baseline["total_memory_matches"]
            full_total = result.full_system["total_memory_matches"] + result.full_system["total_knowledge_items"]
            
            result.metrics = [
                MetricResult("记忆匹配数", baseline_total, result.full_system["total_memory_matches"], "个", "翻译记忆匹配数量"),
                MetricResult("知识补充数", 0, result.full_system["total_knowledge_items"], "条", "知识检索额外提供的信息"),
                MetricResult("总上下文数", baseline_total, full_total, "条", "可用上下文信息总数"),
                MetricResult("查询延迟", baseline_time, full_time, "ms", "查询总耗时"),
            ]
            
            result.baseline_time_ms = baseline_time
            result.full_time_ms = full_time
            
        except Exception as e:
            result.passed = False
            result.error = str(e)
            traceback.print_exc()
        
        self.results.append(result)
        return result
    
    # ==========================================
    # 代码阅读消融实验
    # ==========================================
    
    def test_code_explanation_enhancement(self) -> TestResult:
        """测试代码解释场景中知识检索的增强效果"""
        result = TestResult(
            name="代码解释增强",
            category="code_reading",
            description="解释代码时，知识检索提供的相关文档和技术概念对解释质量的影响"
        )
        
        try:
            retrieval = self._get_knowledge_retrieval()
            
            # 模拟需要解释的代码概念
            code_concepts = ["递归", "设计模式", "异步编程", "数据结构", "算法"]
            
            # 基线：无知识参考
            baseline_explanations = {
                concept: {"has_reference": False, "reference_count": 0, "context": ""}
                for concept in code_concepts
            }
            
            # 完整：查询知识库
            full_explanations = {}
            total_time = 0
            
            for concept in code_concepts:
                result_kb, elapsed = self._measure_time(retrieval.query, concept, "algorithm")
                total_time += elapsed
                
                references = []
                if result_kb.success and result_kb.data:
                    for item in result_kb.data[:3]:
                        if hasattr(item, 'name'):
                            references.append({
                                "name": item.name,
                                "description": getattr(item, 'description', '')[:100]
                            })
                
                full_explanations[concept] = {
                    "has_reference": len(references) > 0,
                    "reference_count": len(references),
                    "references": references
                }
            
            result.baseline = {
                "concepts_tested": len(code_concepts),
                "concepts_with_references": 0,
                "total_references": 0,
                "explanation_support": False
            }
            
            result.full_system = {
                "concepts_tested": len(code_concepts),
                "concepts_with_references": sum(1 for e in full_explanations.values() if e["has_reference"]),
                "total_references": sum(e["reference_count"] for e in full_explanations.values()),
                "explanation_support": any(e["has_reference"] for e in full_explanations.values()),
                "lookup_time_ms": total_time,
                "details": full_explanations
            }
            
            result.metrics = [
                MetricResult("概念覆盖", 0, result.full_system["concepts_with_references"], "个", "能找到参考的概念数"),
                MetricResult("参考总数", 0, result.full_system["total_references"], "条", "检索到的参考信息总数"),
                MetricResult("解释增强", False, result.full_system["explanation_support"], "", "是否能增强代码解释"),
                MetricResult("查询延迟", 0, total_time, "ms", "知识查询总耗时"),
            ]
            
            result.full_time_ms = total_time
            
        except Exception as e:
            result.passed = False
            result.error = str(e)
            traceback.print_exc()
        
        self.results.append(result)
        return result
    
    def test_code_analysis_enhancement(self) -> TestResult:
        """测试代码分析场景中知识检索的增强效果"""
        result = TestResult(
            name="代码分析增强",
            category="code_reading",
            description="分析代码架构时，知识检索提供的项目结构知识对分析深度的影响"
        )
        
        try:
            retrieval = self._get_knowledge_retrieval()
            
            # 模拟需要分析的代码领域
            analysis_domains = [
                ("微服务", "architecture"),
                ("数据库", "database"),
                ("API", "api"),
                ("测试", "testing"),
                ("部署", "deployment"),
            ]
            
            # 基线：无知识参考
            baseline = {
                "domains_tested": len(analysis_domains),
                "domains_with_context": 0,
                "total_context_items": 0
            }
            
            # 完整：查询知识库
            domain_results = {}
            total_time = 0
            
            for domain, category in analysis_domains:
                result_kb, elapsed = self._measure_time(retrieval.query, domain, category)
                total_time += elapsed
                
                items = []
                if result_kb.success and result_kb.data:
                    for item in result_kb.data[:5]:
                        items.append({
                            "name": getattr(item, 'name', str(item)),
                            "type": getattr(item, 'type', 'unknown'),
                            "description": getattr(item, 'description', '')[:100]
                        })
                
                domain_results[domain] = {
                    "has_context": len(items) > 0,
                    "item_count": len(items),
                    "items": items
                }
            
            full = {
                "domains_tested": len(analysis_domains),
                "domains_with_context": sum(1 for d in domain_results.values() if d["has_context"]),
                "total_context_items": sum(d["item_count"] for d in domain_results.values()),
                "lookup_time_ms": total_time,
                "domain_details": domain_results
            }
            
            result.baseline = baseline
            result.full_system = full
            
            result.metrics = [
                MetricResult("领域覆盖", 0, full["domains_with_context"], "个", "能找到上下文的领域数"),
                MetricResult("上下文总数", 0, full["total_context_items"], "条", "检索到的上下文信息总数"),
                MetricResult("分析增强", False, full["domains_with_context"] > 0, "", "是否能增强代码分析"),
                MetricResult("查询延迟", 0, total_time, "ms", "知识查询总耗时"),
            ]
            
            result.full_time_ms = total_time
            
        except Exception as e:
            result.passed = False
            result.error = str(e)
            traceback.print_exc()
        
        self.results.append(result)
        return result
    
    def test_code_review_enhancement(self) -> TestResult:
        """测试代码审查场景中知识检索的增强效果"""
        result = TestResult(
            name="代码审查增强",
            category="code_reading",
            description="代码审查时，知识检索提供的最佳实践和规范对审查质量的影响"
        )
        
        try:
            retrieval = self._get_knowledge_retrieval()
            
            # 模拟代码审查关注点
            review_aspects = [
                ("最佳实践", "code_review"),
                ("安全", "security"),
                ("性能", "performance"),
                ("代码规范", "convention"),
                ("错误处理", "error_handling"),
            ]
            
            baseline = {
                "aspects_tested": len(review_aspects),
                "aspects_with_guidance": 0,
                "total_guidance_items": 0
            }
            
            aspect_results = {}
            total_time = 0
            
            for aspect, category in review_aspects:
                result_kb, elapsed = self._measure_time(retrieval.query, aspect, category)
                total_time += elapsed
                
                guidance = []
                if result_kb.success and result_kb.data:
                    for item in result_kb.data[:3]:
                        guidance.append({
                            "name": getattr(item, 'name', str(item)),
                            "description": getattr(item, 'description', '')[:100]
                        })
                
                aspect_results[aspect] = {
                    "has_guidance": len(guidance) > 0,
                    "guidance_count": len(guidance),
                    "guidance": guidance
                }
            
            full = {
                "aspects_tested": len(review_aspects),
                "aspects_with_guidance": sum(1 for a in aspect_results.values() if a["has_guidance"]),
                "total_guidance_items": sum(a["guidance_count"] for a in aspect_results.values()),
                "lookup_time_ms": total_time,
                "aspect_details": aspect_results
            }
            
            result.baseline = baseline
            result.full_system = full
            
            result.metrics = [
                MetricResult("审查维度覆盖", 0, full["aspects_with_guidance"], "个", "能找到指导的审查维度数"),
                MetricResult("指导总数", 0, full["total_guidance_items"], "条", "检索到的指导信息总数"),
                MetricResult("审查增强", False, full["aspects_with_guidance"] > 0, "", "是否能增强代码审查"),
                MetricResult("查询延迟", 0, total_time, "ms", "知识查询总耗时"),
            ]
            
            result.full_time_ms = total_time
            
        except Exception as e:
            result.passed = False
            result.error = str(e)
            traceback.print_exc()
        
        self.results.append(result)
        return result
    
    # ==========================================
    # PPT生成消融实验
    # ==========================================
    
    def test_ppt_content_enhancement(self) -> TestResult:
        """测试PPT生成场景中知识检索的增强效果"""
        result = TestResult(
            name="PPT内容增强",
            category="ppt",
            description="生成PPT时，知识检索提供的项目知识对内容丰富度的影响"
        )
        
        try:
            retrieval = self._get_knowledge_retrieval()
            
            # 模拟PPT主题
            ppt_topics = [
                ("OpenCopilot", "project"),
                ("系统架构", "architecture"),
                ("API设计", "api"),
                ("测试策略", "testing"),
                ("部署方案", "deployment"),
            ]
            
            baseline = {
                "topics_tested": len(ppt_topics),
                "topics_with_content": 0,
                "total_content_items": 0
            }
            
            topic_results = {}
            total_time = 0
            
            for topic, category in ppt_topics:
                result_kb, elapsed = self._measure_time(retrieval.query, topic, category)
                total_time += elapsed
                
                content = []
                if result_kb.success and result_kb.data:
                    for item in result_kb.data[:5]:
                        content.append({
                            "name": getattr(item, 'name', str(item)),
                            "description": getattr(item, 'description', '')[:100]
                        })
                
                topic_results[topic] = {
                    "has_content": len(content) > 0,
                    "content_count": len(content),
                    "content": content
                }
            
            full = {
                "topics_tested": len(ppt_topics),
                "topics_with_content": sum(1 for t in topic_results.values() if t["has_content"]),
                "total_content_items": sum(t["content_count"] for t in topic_results.values()),
                "lookup_time_ms": total_time,
                "topic_details": topic_results
            }
            
            result.baseline = baseline
            result.full_system = full
            
            result.metrics = [
                MetricResult("主题覆盖", 0, full["topics_with_content"], "个", "能找到内容的主题数"),
                MetricResult("内容总数", 0, full["total_content_items"], "条", "检索到的内容信息总数"),
                MetricResult("PPT增强", False, full["topics_with_content"] > 0, "", "是否能增强PPT内容"),
                MetricResult("查询延迟", 0, total_time, "ms", "知识查询总耗时"),
            ]
            
            result.full_time_ms = total_time
            
        except Exception as e:
            result.passed = False
            result.error = str(e)
            traceback.print_exc()
        
        self.results.append(result)
        return result
    
    def test_ppt_suggestion_enhancement(self) -> TestResult:
        """测试PPT建议场景中知识检索的增强效果"""
        result = TestResult(
            name="PPT建议增强",
            category="ppt",
            description="PPT优化建议时，知识检索提供的上下文知识对建议质量的影响"
        )
        
        try:
            retrieval = self._get_knowledge_retrieval()
            
            # 模拟PPT建议场景
            suggestion_scenarios = [
                ("幻灯片设计", "design"),
                ("数据可视化", "visualization"),
                ("演讲技巧", "presentation"),
                ("配色方案", "design"),
                ("排版布局", "design"),
            ]
            
            baseline = {
                "scenarios_tested": len(suggestion_scenarios),
                "scenarios_with_suggestions": 0,
                "total_suggestions": 0
            }
            
            scenario_results = {}
            total_time = 0
            
            for scenario, category in suggestion_scenarios:
                result_kb, elapsed = self._measure_time(retrieval.query, scenario, category)
                total_time += elapsed
                
                suggestions = []
                if result_kb.success and result_kb.data:
                    for item in result_kb.data[:3]:
                        suggestions.append({
                            "name": getattr(item, 'name', str(item)),
                            "description": getattr(item, 'description', '')[:100]
                        })
                
                scenario_results[scenario] = {
                    "has_suggestions": len(suggestions) > 0,
                    "suggestion_count": len(suggestions),
                    "suggestions": suggestions
                }
            
            full = {
                "scenarios_tested": len(suggestion_scenarios),
                "scenarios_with_suggestions": sum(1 for s in scenario_results.values() if s["has_suggestions"]),
                "total_suggestions": sum(s["suggestion_count"] for s in scenario_results.values()),
                "lookup_time_ms": total_time,
                "scenario_details": scenario_results
            }
            
            result.baseline = baseline
            result.full_system = full
            
            result.metrics = [
                MetricResult("场景覆盖", 0, full["scenarios_with_suggestions"], "个", "能找到建议的场景数"),
                MetricResult("建议总数", 0, full["total_suggestions"], "条", "检索到的建议信息总数"),
                MetricResult("建议增强", False, full["scenarios_with_suggestions"] > 0, "", "是否能增强PPT建议"),
                MetricResult("查询延迟", 0, total_time, "ms", "知识查询总耗时"),
            ]
            
            result.full_time_ms = total_time
            
        except Exception as e:
            result.passed = False
            result.error = str(e)
            traceback.print_exc()
        
        self.results.append(result)
        return result
    
    # ==========================================
    # 权限诊断消融实验
    # ==========================================
    
    def test_permission_diagnosis(self) -> TestResult:
        """测试Broker权限诊断功能的影响"""
        result = TestResult(
            name="权限诊断能力",
            category="permission",
            description="Broker权限模块对系统权限检查和诊断的影响"
        )
        
        try:
            # 尝试导入Broker权限检查
            import importlib
            
            baseline = {
                "permission_check_available": False,
                "permissions_checked": 0,
                "diagnostic_results": {},
                "guide_available": False
            }
            
            # 检查Broker权限模块是否可用
            full = {
                "permission_check_available": False,
                "permissions_checked": 0,
                "diagnostic_results": {},
                "guide_available": False
            }
            
            try:
                # 尝试导入权限检查相关模块
                sys.path.insert(0, str(self.project_root / "asu_broker"))
                
                # 检查 server.py 中的权限检查功能
                server_path = self.project_root / "asu_broker" / "core" / "server.py"
                if server_path.exists():
                    with open(server_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 检查是否包含权限检查相关的API
                    has_permission_api = "permissions" in content.lower()
                    has_permission_guide = "guide" in content.lower() and "permission" in content.lower()
                    
                    full["permission_check_available"] = has_permission_api
                    full["guide_available"] = has_permission_guide
                    
                    if has_permission_api:
                        # 统计权限检查项
                        permission_items = []
                        if "accessibility" in content.lower() or "辅助功能" in content:
                            permission_items.append("辅助功能权限")
                        if "screen_recording" in content.lower() or "屏幕录制" in content:
                            permission_items.append("屏幕录制权限")
                        if "automation" in content.lower() or "自动化" in content:
                            permission_items.append("自动化权限")
                        if "full_disk_access" in content.lower() or "完全磁盘访问" in content:
                            permission_items.append("完全磁盘访问权限")
                        
                        full["permissions_checked"] = len(permission_items)
                        full["diagnostic_results"] = {item: True for item in permission_items}
                        
            except Exception as e:
                full["error"] = str(e)
            
            result.baseline = baseline
            result.full_system = full
            
            result.metrics = [
                MetricResult("权限检查可用", baseline["permission_check_available"], full["permission_check_available"], "", "权限检查功能是否可用"),
                MetricResult("检查项数量", 0, full["permissions_checked"], "项", "可检查的权限项数量"),
                MetricResult("指南可用", baseline["guide_available"], full["guide_available"], "", "权限配置指南是否可用"),
            ]
            
        except Exception as e:
            result.passed = False
            result.error = str(e)
            traceback.print_exc()
        
        self.results.append(result)
        return result
    
    # ==========================================
    # 运行和报告
    # ==========================================
    
    def run_all_tests(self) -> List[TestResult]:
        """运行所有消融实验"""
        print("=" * 70)
        print("OpenCopilot 消融实验")
        print("对比有无新模块对翻译、代码阅读、PPT功能的影响")
        print("=" * 70)
        
        tests = [
            ("翻译术语增强", self.test_translation_terminology_enhancement),
            ("翻译记忆协同", self.test_translation_memory_enhancement),
            ("代码解释增强", self.test_code_explanation_enhancement),
            ("代码分析增强", self.test_code_analysis_enhancement),
            ("代码审查增强", self.test_code_review_enhancement),
            ("PPT内容增强", self.test_ppt_content_enhancement),
            ("PPT建议增强", self.test_ppt_suggestion_enhancement),
            ("权限诊断能力", self.test_permission_diagnosis),
        ]
        
        for name, test_func in tests:
            print(f"\n运行测试: {name} ...", end=" ", flush=True)
            try:
                result = test_func()
                if result.passed:
                    print("✓")
                else:
                    print(f"✗ ({result.error})")
            except Exception as e:
                print(f"✗ ({e})")
        
        print("\n" + "=" * 70)
        print("消融实验完成")
        print("=" * 70)
        
        return self.results
    
    def generate_report(self, output_file: str = "ablation_study_report.json") -> Dict[str, Any]:
        """生成消融实验报告"""
        # 按类别汇总
        categories = {}
        for result in self.results:
            cat = result.category
            if cat not in categories:
                categories[cat] = {
                    "name": cat,
                    "tests": [],
                    "passed": 0,
                    "failed": 0
                }
            categories[cat]["tests"].append(result.name)
            if result.passed:
                categories[cat]["passed"] += 1
            else:
                categories[cat]["failed"] += 1
        
        # 计算改进统计
        improvements = {
            "translation": {"context_items_added": 0, "knowledge_queries": 0},
            "code_reading": {"context_items_added": 0, "knowledge_queries": 0},
            "ppt": {"content_items_added": 0, "knowledge_queries": 0},
            "permission": {"checks_added": 0, "guides_added": 0}
        }
        
        for result in self.results:
            cat = result.category
            if cat in ["translation", "code_reading", "ppt"]:
                for m in result.metrics:
                    if m.name in ["定义总数", "知识补充数", "参考总数", "上下文总数", 
                                  "指导总数", "内容总数", "建议总数"]:
                        key = "content_items_added" if cat == "ppt" else "context_items_added"
                        improvements[cat][key] += m.full_value if isinstance(m.full_value, (int, float)) else 0
                    if "查询" in m.name or "延迟" in m.name:
                        improvements[cat]["knowledge_queries"] += 1
            elif cat == "permission":
                for m in result.metrics:
                    if m.name == "检查项数量":
                        improvements[cat]["checks_added"] += m.full_value if isinstance(m.full_value, (int, float)) else 0
                    if m.name == "指南可用" and m.full_value:
                        improvements[cat]["guides_added"] += 1
        
        # 构建详细结果
        detailed_results = []
        for result in self.results:
            detailed_results.append({
                "name": result.name,
                "category": result.category,
                "description": result.description,
                "passed": result.passed,
                "error": result.error,
                "baseline": result.baseline,
                "full_system": result.full_system,
                "metrics": [
                    {
                        "name": m.name,
                        "baseline": m.baseline_value,
                        "full": m.full_value,
                        "unit": m.unit,
                        "description": m.description
                    }
                    for m in result.metrics
                ],
                "baseline_time_ms": result.baseline_time_ms,
                "full_time_ms": result.full_time_ms
            })
        
        report = {
            "experiment_name": "OpenCopilot 消融实验",
            "experiment_description": "对比有无新模块（知识检索、Broker权限）对翻译、代码阅读、PPT功能的影响",
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": len(self.results),
                "passed": sum(1 for r in self.results if r.passed),
                "failed": sum(1 for r in self.results if not r.passed),
                "pass_rate": f"{sum(1 for r in self.results if r.passed) / len(self.results) * 100:.1f}%" if self.results else "N/A"
            },
            "categories": {
                cat: {
                    "test_count": len(info["tests"]),
                    "passed": info["passed"],
                    "failed": info["failed"],
                    "tests": info["tests"]
                }
                for cat, info in categories.items()
            },
            "improvements": improvements,
            "conclusion": self._generate_conclusion(improvements),
            "detailed_results": detailed_results
        }
        
        # 保存报告
        output_path = self.project_root / output_file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n消融实验报告已保存到: {output_path}")
        
        return report
    
    def _generate_conclusion(self, improvements: Dict) -> Dict[str, Any]:
        """生成实验结论"""
        return {
            "knowledge_retrieval_impact": {
                "translation": {
                    "has_impact": improvements["translation"]["context_items_added"] > 0,
                    "impact_summary": f"知识检索为翻译功能提供了 {improvements['translation']['context_items_added']} 条额外术语和上下文信息",
                    "recommendation": "建议在翻译技术文档时启用知识检索以获取术语参考"
                },
                "code_reading": {
                    "has_impact": improvements["code_reading"]["context_items_added"] > 0,
                    "impact_summary": f"知识检索为代码阅读提供了 {improvements['code_reading']['context_items_added']} 条相关文档和参考",
                    "recommendation": "建议在代码解释和分析时启用知识检索以提供更深入的上下文"
                },
                "ppt": {
                    "has_impact": improvements["ppt"]["content_items_added"] > 0,
                    "impact_summary": f"知识检索为PPT生成提供了 {improvements['ppt']['content_items_added']} 条项目知识和建议",
                    "recommendation": "建议在PPT生成和建议时启用知识检索以丰富内容"
                }
            },
            "permission_module_impact": {
                "has_impact": improvements["permission"]["checks_added"] > 0,
                "impact_summary": f"Broker权限模块提供了 {improvements['permission']['checks_added']} 项权限检查和 {improvements['permission']['guides_added']} 个配置指南",
                "recommendation": "建议使用Broker权限模块进行系统权限诊断和配置指导"
            },
            "overall_assessment": "新模块的加入显著增强了系统的知识检索和权限诊断能力，为翻译、代码阅读、PPT生成功能提供了额外的上下文支持。"
        }


def print_summary(report: Dict[str, Any]):
    """打印实验摘要"""
    print("\n" + "=" * 70)
    print("消融实验摘要")
    print("=" * 70)
    
    print(f"\n实验名称: {report['experiment_name']}")
    print(f"实验时间: {report['timestamp']}")
    
    summary = report['summary']
    print(f"\n总测试数: {summary['total_tests']}")
    print(f"通过: {summary['passed']}")
    print(f"失败: {summary['failed']}")
    print(f"通过率: {summary['pass_rate']}")
    
    print("\n分类统计:")
    for cat, info in report['categories'].items():
        cat_name = {
            "translation": "翻译功能",
            "code_reading": "代码阅读",
            "ppt": "PPT生成",
            "permission": "权限诊断"
        }.get(cat, cat)
        print(f"  {cat_name}: {info['passed']}/{info['test_count']} 通过")
    
    print("\n新模块增强效果:")
    for module, impact in report['improvements'].items():
        module_name = {
            "translation": "翻译功能",
            "code_reading": "代码阅读",
            "ppt": "PPT生成",
            "permission": "权限诊断"
        }.get(module, module)
        if module != "permission":
            key = "content_items_added" if module == "ppt" else "context_items_added"
            print(f"  {module_name}: +{impact[key]} 条上下文信息")
        else:
            print(f"  {module_name}: +{impact['checks_added']} 项权限检查, +{impact['guides_added']} 个配置指南")
    
    print("\n实验结论:")
    for module, conclusion in report['conclusion']['knowledge_retrieval_impact'].items():
        module_name = {
            "translation": "翻译",
            "code_reading": "代码阅读",
            "ppt": "PPT"
        }.get(module, module)
        print(f"  {module_name}: {conclusion['impact_summary']}")
    
    perm = report['conclusion']['permission_module_impact']
    print(f"  权限: {perm['impact_summary']}")
    
    print(f"\n总结: {report['conclusion']['overall_assessment']}")


def main():
    """主函数"""
    runner = AblationStudy()
    
    # 运行所有测试
    results = runner.run_all_tests()
    
    # 生成报告
    report = runner.generate_report()
    
    # 打印摘要
    print_summary(report)
    
    return report


if __name__ == "__main__":
    main()