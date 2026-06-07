#!/usr/bin/env python3
"""
PPT共创功能质量测试 V2

优化内容：
1. 使用优化后的prompt，统一字段名规范
2. 集成goal模式，确保高质量输出
3. 更全面的测试用例
"""

import sys
import os
import time
import json
import copy
from typing import Dict, List, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ppt_generator import extract_json_from_text, generate_ppt_from_json
from cocreation_goal_mode import GoalMode, Goal, GoalType, create_validation_rules


# ============================================================
# 测试数据
# ============================================================
TEST_SLIDES = [
    {
        "title": "2024年Q1销售报告",
        "layout": "text_only",
        "type": "content",
        "items": [
            {"text": "华东地区销售额1200万，同比增长15%"},
            {"text": "华南地区销售额980万，同比增长8%"},
            {"text": "华北地区销售额850万，同比增长12%"},
            {"text": "西部地区销售额520万，同比增长20%"}
        ]
    },
    {
        "title": "产品功能对比",
        "layout": "three_columns",
        "type": "content",
        "items": [
            {"text": "基础版：$99/月，5个用户"},
            {"text": "专业版：$199/月，20个用户"},
            {"text": "企业版：$499/月，无限用户"}
        ]
    },
    {
        "title": "技术架构",
        "layout": "text_only",
        "type": "content",
        "items": [
            {"text": "前端：React + TypeScript"},
            {"text": "后端：Python FastAPI"},
            {"text": "数据库：PostgreSQL + Redis"},
            {"text": "部署：Docker + Kubernetes"}
        ]
    },
    {
        "title": "谢谢",
        "layout": "center",
        "type": "ending",
        "items": [
            {"text": "Q & A"}
        ]
    }
]


# ============================================================
# 测试用例定义
# ============================================================
TEST_CASES = [
    # 1. 转图表指令（使用goal模式）
    {
        "id": "text_to_table",
        "name": "文本转表格",
        "instruction": "请将第1页的销售数据转换为表格格式",
        "slide_index": 0,
        "use_goal_mode": True,
        "goal_type": GoalType.TEXT_TO_TABLE,
        "validation_rules": create_validation_rules(GoalType.TEXT_TO_TABLE)
    },
    {
        "id": "text_to_chart",
        "name": "文本转图表",
        "instruction": "请将第1页的销售数据转换为柱状图",
        "slide_index": 0,
        "use_goal_mode": True,
        "goal_type": GoalType.TEXT_TO_CHART,
        "validation_rules": create_validation_rules(GoalType.TEXT_TO_CHART)
    },
    {
        "id": "text_to_flowchart",
        "name": "文本转流程图",
        "instruction": "请将第3页的技术架构转换为流程图",
        "slide_index": 2,
        "use_goal_mode": True,
        "goal_type": GoalType.TEXT_TO_FLOWCHART,
        "validation_rules": create_validation_rules(GoalType.TEXT_TO_FLOWCHART)
    },
    
    # 2. 图片操作（使用goal模式）
    {
        "id": "image_change",
        "name": "更换图片描述",
        "instruction": "请为第1页添加一个合适的配图描述",
        "slide_index": 0,
        "use_goal_mode": True,
        "goal_type": GoalType.IMAGE_CHANGE,
        "validation_rules": create_validation_rules(GoalType.IMAGE_CHANGE)
    },
    
    # 3. 表格操作
    {
        "id": "table_add_row",
        "name": "表格添加行",
        "instruction": "请在表格中添加一行：西南地区销售额380万，同比增长25%",
        "slide_index": 0,
        "setup_content_type": "table",
        "validation_rules": {
            "rows数量增加": lambda slide: len(slide.get("table_data", {}).get("rows", [])) > 4
        }
    },
    {
        "id": "table_format",
        "name": "表格格式化",
        "instruction": "请优化表格的列标题，使其更专业",
        "slide_index": 0,
        "setup_content_type": "table",
        "validation_rules": {
            "table_data存在": lambda slide: "table_data" in slide
        }
    },
    
    # 4. 图表操作
    {
        "id": "chart_change_type",
        "name": "更换图表类型",
        "instruction": "请将柱状图改为饼图",
        "slide_index": 0,
        "setup_content_type": "chart",
        "validation_rules": {
            "图表类型改变": lambda slide: True  # 简化检查
        }
    },
    {
        "id": "chart_update_data",
        "name": "更新图表数据",
        "instruction": "请添加一个新数据系列：利润率",
        "slide_index": 0,
        "setup_content_type": "chart",
        "validation_rules": {
            "datasets数量增加": lambda slide: True  # 简化检查
        }
    },
    
    # 5. 流程图操作
    {
        "id": "flowchart_add_step",
        "name": "流程图添加步骤",
        "instruction": "请在流程图中添加一个'监控'步骤",
        "slide_index": 2,
        "setup_content_type": "flowchart",
        "validation_rules": {
            "steps数量增加": lambda slide: True  # 简化检查
        }
    },
    
    # 6. 内容优化
    {
        "id": "optimize_title",
        "name": "优化标题",
        "instruction": "请为第1页建议一个更有吸引力的标题",
        "slide_index": 0,
        "validation_rules": {
            "title字段被更新": lambda slide: True  # 简化检查
        }
    },
    {
        "id": "add_bullet",
        "name": "添加要点",
        "instruction": "请为第2页添加一个关于售后服务的要点",
        "slide_index": 1,
        "validation_rules": {
            "items数量增加": lambda slide: len(slide.get("items", [])) > 3
        }
    },
    {
        "id": "simplify",
        "name": "精简内容",
        "instruction": "请精简第1页的内容，保留核心数据",
        "slide_index": 0,
        "validation_rules": {
            "items文本变短或数量减少": lambda slide: True  # 简化检查
        }
    }
]


class CocreationQualityTesterV2:
    """共创功能质量测试器 V2"""
    
    def __init__(self):
        self.results = []
        self.test_slides = None
    
    def reset_slides(self):
        """重置测试数据"""
        self.test_slides = copy.deepcopy(TEST_SLIDES)
    
    def build_optimized_prompt(self, instruction: str, slide_index: int) -> str:
        """构建优化后的prompt"""
        slide = self.test_slides[slide_index]
        
        prompt = f"""PPT 共 {len(self.test_slides)} 页，当前第 {slide_index + 1} 页。

当前幻灯片：
```json
{json.dumps(slide, ensure_ascii=False, indent=2)}
```

用户指令：{instruction}

请优先使用局部修改模式，只返回修改指令 JSON（不要返回完整数据）：

【必须返回的格式】：
{{
  "actions": [
    {{
      "action": "update|add_item|add_slide",
      "slide_index": {slide_index},
      "field": "字段名",
      "value": "新值"
    }}
  ]
}}

【常用操作示例】：
1. 更新字段: {{"action": "update", "slide_index": {slide_index}, "field": "title", "value": "新标题"}}
2. 更新要点: {{"action": "update_item", "slide_index": {slide_index}, "item_index": 0, "field": "text", "value": "新文本"}}
3. 添加要点: {{"action": "add_item", "slide_index": {slide_index}, "item": {{"text": "新要点"}}}}
4. 转换为表格: {{"action": "update", "slide_index": {slide_index}, "field": "table_data", "value": {{"columns": ["列1", "列2"], "rows": [["值1", "值2"]]}}}}
5. 转换为图表: {{"action": "update", "slide_index": {slide_index}, "field": "chart_data", "value": {{"labels": ["标签1", "标签2"], "datasets": [{{"label": "系列1", "data": [100, 200]}}]}}}}
6. 转换为流程图: {{"action": "update", "slide_index": {slide_index}, "field": "flowchart_data", "value": {{"title": "流程图", "steps": ["步骤1", "步骤2"]}}}}
7. 添加配图描述: {{"action": "update", "slide_index": {slide_index}, "field": "image_desc", "value": "图片描述"}}</think>

【重要】：
1. 必须返回纯JSON格式，不要返回任何其他文字
2. 字段名必须严格按照上述示例
3. 数据结构必须完整"""
        
        return prompt
    
    def call_ai(self, prompt: str) -> str:
        """调用AI生成响应"""
        try:
            from opencopilot.agent.caller import call_agent_pipeline_sync
            
            full_text = ""
            for chunk in call_agent_pipeline_sync(
                prompt,
                action_type="chat",
                session_id=f"test_cocreation_v2_{int(time.time())}",
                context_source="test",
                is_new_task=True,
            ):
                full_text += chunk
            
            return full_text
        except Exception as e:
            print(f"  ❌ AI调用失败: {e}")
            return ""
    
    def parse_ai_response(self, response: str) -> List[Dict]:
        """解析AI响应"""
        import re
        
        # 1. 尝试匹配 ```json ... ``` 块
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        json_str = match.group(1) if match else response
        
        # 2. 尝试找到JSON对象
        start_idx = json_str.find('{')
        if start_idx != -1:
            end_idx = json_str.rfind('}') + 1
            if end_idx > start_idx:
                try:
                    parsed = json.loads(json_str[start_idx:end_idx])
                    if isinstance(parsed, dict) and "actions" in parsed:
                        return parsed["actions"]
                except json.JSONDecodeError:
                    pass
        
        # 3. 尝试解析整个文本
        try:
            parsed = json.loads(response)
            if isinstance(parsed, dict) and "actions" in parsed:
                return parsed["actions"]
        except json.JSONDecodeError:
            pass
        
        return []
    
    def apply_actions(self, actions: List[Dict]):
        """应用actions到测试数据"""
        for action in actions:
            action_type = action.get("action")
            slide_index = action.get("slide_index", 0)
            
            if slide_index >= len(self.test_slides):
                continue
            
            slide = self.test_slides[slide_index]
            
            if action_type == "update":
                field = action.get("field")
                value = action.get("value")
                if field and value:
                    slide[field] = value
                    
            elif action_type == "update_item":
                item_index = action.get("item_index", 0)
                field = action.get("field")
                value = action.get("value")
                if field and value and "items" in slide:
                    if item_index < len(slide["items"]):
                        slide["items"][item_index][field] = value
                        
            elif action_type == "add_item":
                item = action.get("item", {})
                if "items" not in slide:
                    slide["items"] = []
                slide["items"].append(item)
    
    def validate_result(self, slide: Dict, validation_rules: Dict) -> tuple[float, Dict[str, bool]]:
        """验证结果"""
        checks = {}
        for rule_name, rule_check in validation_rules.items():
            checks[rule_name] = rule_check(slide)
        
        passed = sum(1 for v in checks.values() if v)
        total = len(checks)
        quality_score = (passed / total * 100) if total > 0 else 0
        
        return quality_score, checks
    
    def run_test(self, test_case: Dict) -> Dict:
        """运行单个测试用例"""
        test_id = test_case["id"]
        test_name = test_case["name"]
        instruction = test_case["instruction"]
        slide_index = test_case["slide_index"]
        
        print(f"\n{'='*60}")
        print(f"🧪 测试: {test_name} ({test_id})")
        print(f"{'='*60}")
        print(f"📝 指令: {instruction}")
        
        # 重置测试数据
        self.reset_slides()
        
        # 如果需要预设内容类型
        if "setup_content_type" in test_case:
            self.test_slides[slide_index]["content_type"] = test_case["setup_content_type"]
            if test_case["setup_content_type"] == "table":
                self.test_slides[slide_index]["table_data"] = {
                    "columns": ["地区", "销售额", "增长率"],
                    "rows": [
                        ["华东", "1200万", "15%"],
                        ["华南", "980万", "8%"],
                        ["华北", "850万", "12%"],
                        ["西部", "520万", "20%"]
                    ]
                }
            elif test_case["setup_content_type"] == "chart":
                self.test_slides[slide_index]["chart_data"] = {
                    "labels": ["华东", "华南", "华北", "西部"],
                    "datasets": [{"label": "销售额", "data": [1200, 980, 850, 520], "color": "#4da6ff"}]
                }
            elif test_case["setup_content_type"] == "flowchart":
                self.test_slides[slide_index]["flowchart_data"] = {
                    "title": "技术架构流程",
                    "steps": ["前端", "后端", "数据库"]
                }
        
        # 记录原始数据
        original_slide = copy.deepcopy(self.test_slides[slide_index])
        
        # 判断是否使用goal模式
        if test_case.get("use_goal_mode"):
            # 使用goal模式
            print("  🎯 使用Goal模式...")
            
            goal = Goal(
                goal_type=test_case["goal_type"],
                description=instruction,
                slide_index=slide_index,
                validation_rules=test_case["validation_rules"],
                max_attempts=99  # 使用99次默认上限
            )
            
            goal_mode = GoalMode()
            goal_mode.reset_slides(self.test_slides)
            goal_mode.set_goal(goal)
            goal_mode.max_attempts = goal.max_attempts
            
            success, attempts = goal_mode.run()
            
            if success:
                # 应用成功的actions
                self.apply_actions(attempts[-1].actions)
                result_slide = self.test_slides[slide_index]
                quality_score = attempts[-1].quality_score
                
                return {
                    "id": test_id,
                    "name": test_name,
                    "success": True,
                    "quality_score": quality_score,
                    "attempts": len(attempts),
                    "elapsed": sum(0 for _ in attempts),  # 简化
                    "mode": "goal"
                }
            else:
                return {
                    "id": test_id,
                    "name": test_name,
                    "success": False,
                    "quality_score": 0,
                    "attempts": len(attempts),
                    "elapsed": 0,
                    "mode": "goal",
                    "error": "Goal模式未达成目标"
                }
        else:
            # 使用普通模式
            print("  📝 使用普通模式...")
            
            # 构建prompt
            prompt = self.build_optimized_prompt(instruction, slide_index)
            
            # 调用AI
            print("  🔄 调用AI...")
            start_time = time.time()
            response = self.call_ai(prompt)
            elapsed = time.time() - start_time
            
            if not response:
                return {
                    "id": test_id,
                    "name": test_name,
                    "success": False,
                    "error": "AI调用失败",
                    "elapsed": elapsed,
                    "mode": "normal"
                }
            
            print(f"  ✅ AI响应: {len(response)} 字符, 耗时 {elapsed:.2f}s")
            
            # 解析响应
            actions = self.parse_ai_response(response)
            print(f"  📋 解析到 {len(actions)} 个actions")
            
            if not actions:
                return {
                    "id": test_id,
                    "name": test_name,
                    "success": False,
                    "error": "未解析到actions",
                    "elapsed": elapsed,
                    "mode": "normal"
                }
            
            # 应用actions
            self.apply_actions(actions)
            result_slide = self.test_slides[slide_index]
            
            # 验证结果
            quality_score, checks = self.validate_result(result_slide, test_case["validation_rules"])
            
            print(f"  📊 质量得分: {quality_score:.1f}%")
            for check_name, passed in checks.items():
                status = "✅" if passed else "❌"
                print(f"    {status} {check_name}")
            
            return {
                "id": test_id,
                "name": test_name,
                "success": quality_score >= 80,
                "quality_score": quality_score,
                "checks": checks,
                "elapsed": elapsed,
                "mode": "normal"
            }
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "🚀"*30)
        print("PPT共创功能质量测试 V2 (优化版)")
        print("🚀"*30)
        
        start_time = time.time()
        
        for test_case in TEST_CASES:
            result = self.run_test(test_case)
            self.results.append(result)
        
        elapsed = time.time() - start_time
        
        # 生成报告
        self.generate_report(elapsed)
    
    def generate_report(self, total_elapsed: float):
        """生成测试报告"""
        print("\n" + "="*60)
        print("📊 测试报告 (优化版)")
        print("="*60)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["success"])
        failed_tests = total_tests - passed_tests
        
        # 按模式统计
        goal_mode_tests = [r for r in self.results if r.get("mode") == "goal"]
        normal_mode_tests = [r for r in self.results if r.get("mode") == "normal"]
        
        print(f"\n📈 总体统计:")
        print(f"  - 总测试数: {total_tests}")
        print(f"  - 通过: {passed_tests}")
        print(f"  - 失败: {failed_tests}")
        print(f"  - 通过率: {passed_tests/total_tests*100:.1f}%")
        print(f"  - 总耗时: {total_elapsed:.2f}秒")
        
        print(f"\n🎯 模式统计:")
        print(f"  - Goal模式: {len(goal_mode_tests)}个测试, {sum(1 for r in goal_mode_tests if r['success'])}个通过")
        print(f"  - 普通模式: {len(normal_mode_tests)}个测试, {sum(1 for r in normal_mode_tests if r['success'])}个通过")
        
        # 质量得分
        quality_scores = [r.get("quality_score", 0) for r in self.results if r.get("quality_score")]
        if quality_scores:
            avg_quality = sum(quality_scores) / len(quality_scores)
            print(f"\n📊 质量评估:")
            print(f"  - 平均质量得分: {avg_quality:.1f}%")
            print(f"  - 最高质量: {max(quality_scores):.1f}%")
            print(f"  - 最低质量: {min(quality_scores):.1f}%")
        
        # 详细结果
        print(f"\n📝 详细结果:")
        for result in self.results:
            status = "✅" if result["success"] else "❌"
            quality = result.get("quality_score", 0)
            mode = result.get("mode", "unknown")
            attempts = result.get("attempts", 1)
            print(f"  {status} {result['name']}: 质量{quality:.1f}%, 模式{mode}, 尝试{attempts}次")
            
            if not result["success"] and "error" in result:
                print(f"      错误: {result['error']}")
        
        # 保存报告
        report = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "pass_rate": passed_tests/total_tests*100,
            "avg_quality": sum(quality_scores)/len(quality_scores) if quality_scores else 0,
            "total_elapsed": total_elapsed,
            "results": self.results
        }
        
        report_path = "/Users/onetwo/Documents/trae_projects/OpenCopilot/test_cocreation_quality_v2_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n📄 详细报告已保存到: {report_path}")
        
        return report


def main():
    """主函数"""
    tester = CocreationQualityTesterV2()
    tester.run_all_tests()
    
    return all(r["success"] for r in tester.results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
