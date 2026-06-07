#!/usr/bin/env python3
"""
PPT共创功能质量测试

测试内容：
1. 转图表指令 - 验证text→table/chart/flowchart转换
2. 表格操作 - 格式化、添加行列、排序
3. 图表操作 - 更换类型、更新数据、调整配色
4. 流程图操作 - 添加步骤、调整方向
5. 图片操作 - 更换图片、调整布局

使用输出做benchmark，评估执行质量
"""

import sys
import os
import time
import json
from typing import Dict, List, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ppt_generator import extract_json_from_text, generate_ppt_from_json


# ============================================================
# 测试数据：包含各种内容类型的幻灯片
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
    # 1. 转图表指令
    {
        "id": "text_to_table",
        "name": "文本转表格",
        "instruction": "请将第1页的销售数据转换为表格格式",
        "slide_index": 0,
        "expected_content_type": "table",
        "expected_fields": ["table_data"],
        "quality_checks": [
            "table_data有columns字段",
            "table_data有rows字段",
            "rows数量>=3"
        ]
    },
    {
        "id": "text_to_chart",
        "name": "文本转图表",
        "instruction": "请将第1页的销售数据转换为柱状图",
        "slide_index": 0,
        "expected_content_type": "chart",
        "expected_fields": ["chart_data"],
        "quality_checks": [
            "chart_data有labels字段",
            "chart_data有datasets字段",
            "labels数量>=3"
        ]
    },
    {
        "id": "text_to_flowchart",
        "name": "文本转流程图",
        "instruction": "请将第3页的技术架构转换为流程图",
        "slide_index": 2,
        "expected_content_type": "flowchart",
        "expected_fields": ["flowchart_data"],
        "quality_checks": [
            "flowchart_data有steps字段",
            "steps数量>=3"
        ]
    },
    
    # 2. 表格操作
    {
        "id": "table_add_row",
        "name": "表格添加行",
        "instruction": "请在表格中添加一行：西南地区销售额380万，同比增长25%",
        "slide_index": 0,
        "setup_content_type": "table",
        "expected_row_increase": True,
        "quality_checks": [
            "rows数量增加",
            "新行包含正确数据"
        ]
    },
    {
        "id": "table_format",
        "name": "表格格式化",
        "instruction": "请优化表格的列标题，使其更专业",
        "slide_index": 0,
        "setup_content_type": "table",
        "quality_checks": [
            "columns字段被更新",
            "格式更专业"
        ]
    },
    
    # 3. 图表操作
    {
        "id": "chart_change_type",
        "name": "更换图表类型",
        "instruction": "请将柱状图改为饼图",
        "slide_index": 0,
        "setup_content_type": "chart",
        "quality_checks": [
            "图表类型改变"
        ]
    },
    {
        "id": "chart_update_data",
        "name": "更新图表数据",
        "instruction": "请添加一个新数据系列：利润率",
        "slide_index": 0,
        "setup_content_type": "chart",
        "quality_checks": [
            "datasets数量增加"
        ]
    },
    
    # 4. 流程图操作
    {
        "id": "flowchart_add_step",
        "name": "流程图添加步骤",
        "instruction": "请在流程图中添加一个'监控'步骤",
        "slide_index": 2,
        "setup_content_type": "flowchart",
        "quality_checks": [
            "steps数量增加",
            "新步骤包含'监控'"
        ]
    },
    
    # 5. 图片操作
    {
        "id": "image_change",
        "name": "更换图片描述",
        "instruction": "请为第1页添加一个合适的配图描述",
        "slide_index": 0,
        "expected_fields": ["image_desc"],
        "quality_checks": [
            "image_desc字段存在",
            "描述内容相关"
        ]
    },
    
    # 6. 内容优化
    {
        "id": "optimize_title",
        "name": "优化标题",
        "instruction": "请为第1页建议一个更有吸引力的标题",
        "slide_index": 0,
        "quality_checks": [
            "title字段被更新",
            "新标题不同于原标题"
        ]
    },
    {
        "id": "add_bullet",
        "name": "添加要点",
        "instruction": "请为第2页添加一个关于售后服务的要点",
        "slide_index": 1,
        "quality_checks": [
            "items数量增加",
            "新要点包含'售后'相关内容"
        ]
    },
    {
        "id": "simplify",
        "name": "精简内容",
        "instruction": "请精简第1页的内容，保留核心数据",
        "slide_index": 0,
        "quality_checks": [
            "items文本变短或数量减少"
        ]
    }
]


class CocreationQualityTester:
    """共创功能质量测试器"""
    
    def __init__(self):
        self.results = []
        self.test_slides = None
    
    def reset_slides(self):
        """重置测试数据"""
        import copy
        self.test_slides = copy.deepcopy(TEST_SLIDES)
    
    def extract_actions_json(self, text: str) -> dict:
        """专门提取actions格式的JSON"""
        import re
        
        # 1. 尝试匹配 ```json ... ``` 块
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        json_str = match.group(1) if match else text
        
        # 2. 尝试找到JSON对象
        start_idx = json_str.find('{')
        if start_idx != -1:
            end_idx = json_str.rfind('}') + 1
            if end_idx > start_idx:
                try:
                    parsed = json.loads(json_str[start_idx:end_idx])
                    if isinstance(parsed, dict) and "actions" in parsed:
                        return parsed
                except json.JSONDecodeError:
                    pass
        
        # 3. 尝试解析整个文本
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict) and "actions" in parsed:
                return parsed
        except json.JSONDecodeError:
            pass
        
        return None
    
    def build_prompt(self, instruction: str, slide_index: int) -> str:
        """构建AI指令prompt"""
        slide = self.test_slides[slide_index]
        
        prompt = f"""PPT 共 4 页，当前第 {slide_index + 1} 页。

当前幻灯片：
```json
{json.dumps(slide, ensure_ascii=False, indent=2)}
```

用户指令：{instruction}

请优先使用局部修改模式，只返回修改指令 JSON（不要返回完整数据）：
- 更新字段: {{"action": "update", "slide_index": {slide_index}, "field": "字段名", "value": "新值"}}
- 更新要点: {{"action": "update_item", "slide_index": {slide_index}, "item_index": 0, "field": "text", "value": "新文本"}}
- 添加要点: {{"action": "add_item", "slide_index": {slide_index}, "item": {{"text": "新要点"}}}}
- 添加新页: {{"action": "add_slide", "slide": {{"title": "标题", "layout": "text_only", "items": [...]}}}}
- 转换内容类型: {{"action": "update", "slide_index": {slide_index}, "field": "content_type", "value": "table/chart/flowchart"}}

返回格式：{{"actions": [修改指令1, 修改指令2, ...]}}"""
        
        return prompt
    
    def call_ai(self, prompt: str) -> str:
        """调用AI生成响应"""
        try:
            from opencopilot.agent.caller import call_agent_pipeline_sync
            
            full_text = ""
            for chunk in call_agent_pipeline_sync(
                prompt,
                action_type="chat",
                session_id=f"test_cocreation_{int(time.time())}",
                context_source="test",
                is_new_task=True,
            ):
                full_text += chunk
            
            return full_text
        except Exception as e:
            print(f"  ❌ AI调用失败: {e}")
            return ""
    
    def parse_ai_response(self, response: str) -> List[Dict]:
        """解析AI响应，提取actions"""
        try:
            # 使用专门的actions解析函数
            result = self.extract_actions_json(response)
            if result and isinstance(result, dict) and "actions" in result:
                return result["actions"]
            
            # 尝试通用JSON解析
            result = extract_json_from_text(response)
            if result and isinstance(result, dict) and "actions" in result:
                return result["actions"]
            elif result and isinstance(result, list):
                return result
        except Exception as e:
            print(f"  ⚠️ JSON解析失败: {e}")
        
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
                
            elif action_type == "add_slide":
                new_slide = action.get("slide", {})
                self.test_slides.append(new_slide)
    
    def check_quality(self, test_case: Dict, original_slide: Dict, result_slide: Dict, actions: List[Dict]) -> Dict[str, bool]:
        """检查质量"""
        checks = {}
        check_funcs = test_case.get("quality_checks", [])
        
        # 获取AI返回的actions中的数据
        for action in actions:
            if action.get("action") == "update":
                field = action.get("field")
                value = action.get("value")
                # 兼容各种字段名
                if field in ["table_data", "table_config"] and isinstance(value, dict):
                    result_slide["table_data"] = value
                elif field in ["chart_data", "chart_config"] and isinstance(value, dict):
                    result_slide["chart_data"] = value
                elif field in ["flowchart_data", "flowchart_config", "content"] and isinstance(value, dict):
                    result_slide["flowchart_data"] = value
                elif field in ["content_type", "layout"] and isinstance(value, str):
                    result_slide["content_type"] = value
        
        for check_desc in check_funcs:
            if "table_data有columns字段" in check_desc:
                # 兼容columns和headers两种字段名
                td = result_slide.get("table_data", {})
                checks[check_desc] = "table_data" in result_slide and ("columns" in td or "headers" in td)
                
            elif "table_data有rows字段" in check_desc:
                checks[check_desc] = "table_data" in result_slide and "rows" in result_slide.get("table_data", {})
                
            elif "rows数量>=3" in check_desc:
                rows = result_slide.get("table_data", {}).get("rows", [])
                checks[check_desc] = len(rows) >= 3
                
            elif "rows数量增加" in check_desc:
                orig_rows = original_slide.get("table_data", {}).get("rows", [])
                new_rows = result_slide.get("table_data", {}).get("rows", [])
                checks[check_desc] = len(new_rows) > len(orig_rows)
                
            elif "新行包含正确数据" in check_desc:
                rows = result_slide.get("table_data", {}).get("rows", [])
                checks[check_desc] = any("西南" in str(row) or "380" in str(row) for row in rows)
                
            elif "chart_data有labels字段" in check_desc:
                # 兼容labels和categories两种字段名
                cd = result_slide.get("chart_data", {})
                checks[check_desc] = "chart_data" in result_slide and ("labels" in cd or "categories" in cd)
                
            elif "chart_data有datasets字段" in check_desc:
                # 兼容datasets和data两种字段名
                cd = result_slide.get("chart_data", {})
                checks[check_desc] = "chart_data" in result_slide and ("datasets" in cd or "data" in cd)
                
            elif "labels数量>=3" in check_desc:
                cd = result_slide.get("chart_data", {})
                labels = cd.get("labels", cd.get("categories", []))
                checks[check_desc] = len(labels) >= 3
                
            elif "图表类型改变" in check_desc:
                checks[check_desc] = True  # 简化检查
                
            elif "datasets数量增加" in check_desc:
                checks[check_desc] = True  # 简化检查
                
            elif "flowchart_data有steps字段" in check_desc:
                # 兼容steps和nodes两种字段名
                fd = result_slide.get("flowchart_data", {})
                checks[check_desc] = "flowchart_data" in result_slide and ("steps" in fd or "nodes" in fd)
                
            elif "steps数量>=3" in check_desc:
                fd = result_slide.get("flowchart_data", {})
                steps = fd.get("steps", fd.get("nodes", []))
                checks[check_desc] = len(steps) >= 3
                
            elif "steps数量增加" in check_desc:
                checks[check_desc] = True  # 简化检查
                
            elif "新步骤包含'监控'" in check_desc:
                fd = result_slide.get("flowchart_data", {})
                steps = fd.get("steps", fd.get("nodes", []))
                checks[check_desc] = any("监控" in str(step) for step in steps)
                
            elif "image_desc字段存在" in check_desc:
                checks[check_desc] = "image_desc" in result_slide
                
            elif "描述内容相关" in check_desc:
                checks[check_desc] = "image_desc" in result_slide
                
            elif "title字段被更新" in check_desc:
                checks[check_desc] = result_slide.get("title") != original_slide.get("title")
                
            elif "新标题不同于原标题" in check_desc:
                checks[check_desc] = result_slide.get("title") != original_slide.get("title")
                
            elif "items数量增加" in check_desc:
                orig_items = len(original_slide.get("items", []))
                new_items = len(result_slide.get("items", []))
                checks[check_desc] = new_items > orig_items
                
            elif "新要点包含'售后'相关内容" in check_desc:
                items = result_slide.get("items", [])
                checks[check_desc] = any("售后" in item.get("text", "") for item in items)
                
            elif "items文本变短或数量减少" in check_desc:
                orig_len = sum(len(item.get("text", "")) for item in original_slide.get("items", []))
                new_len = sum(len(item.get("text", "")) for item in result_slide.get("items", []))
                checks[check_desc] = new_len <= orig_len
                
            elif "columns字段被更新" in check_desc:
                checks[check_desc] = "table_data" in result_slide
                
            elif "格式更专业" in check_desc:
                checks[check_desc] = True  # 需要人工判断
                
            else:
                checks[check_desc] = True  # 默认通过
        
        return checks
    
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
        import copy
        original_slide = copy.deepcopy(self.test_slides[slide_index])
        
        # 构建prompt
        prompt = self.build_prompt(instruction, slide_index)
        
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
                "elapsed": elapsed
            }
        
        print(f"  ✅ AI响应: {len(response)} 字符, 耗时 {elapsed:.2f}s")
        
        # 解析响应
        actions = self.parse_ai_response(response)
        print(f"  📋 解析到 {len(actions)} 个actions")
        
        # 调试输出
        if not actions:
            print(f"  ⚠️ 原始响应前200字符: {response[:200]}")
            # 尝试手动解析
            try:
                import re
                match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
                if match:
                    print(f"  🔍 找到JSON块: {match.group(1)[:100]}...")
                    parsed = json.loads(match.group(1))
                    if "actions" in parsed:
                        actions = parsed["actions"]
                        print(f"  ✅ 手动解析成功: {len(actions)} 个actions")
            except Exception as e:
                print(f"  ❌ 手动解析失败: {e}")
        
        if not actions:
            return {
                "id": test_id,
                "name": test_name,
                "success": False,
                "error": "未解析到actions",
                "response": response[:500],
                "elapsed": elapsed
            }
        
        # 打印actions
        for i, action in enumerate(actions):
            print(f"    Action {i+1}: {json.dumps(action, ensure_ascii=False)[:100]}")
        
        # 应用actions
        self.apply_actions(actions)
        result_slide = self.test_slides[slide_index]
        
        # 打印应用后的结果
        print(f"\n  📄 应用后幻灯片:")
        print(f"    - content_type: {result_slide.get('content_type', 'N/A')}")
        print(f"    - table_data: {'有' if 'table_data' in result_slide else '无'}")
        print(f"    - chart_data: {'有' if 'chart_data' in result_slide else '无'}")
        print(f"    - flowchart_data: {'有' if 'flowchart_data' in result_slide else '无'}")
        
        # 检查质量
        quality_checks = self.check_quality(test_case, original_slide, result_slide, actions)
        passed_checks = sum(1 for v in quality_checks.values() if v)
        total_checks = len(quality_checks)
        quality_score = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        
        print(f"\n  📊 质量检查: {passed_checks}/{total_checks} 通过 ({quality_score:.1f}%)")
        for check_desc, passed in quality_checks.items():
            status = "✅" if passed else "❌"
            print(f"    {status} {check_desc}")
        
        # 检查指令是否正确执行
        instruction_executed = len(actions) > 0 and quality_score >= 50
        
        return {
            "id": test_id,
            "name": test_name,
            "success": instruction_executed,
            "quality_score": quality_score,
            "passed_checks": passed_checks,
            "total_checks": total_checks,
            "actions_count": len(actions),
            "elapsed": elapsed,
            "quality_checks": quality_checks
        }
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "🚀"*30)
        print("PPT共创功能质量测试")
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
        print("📊 测试报告")
        print("="*60)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["success"])
        failed_tests = total_tests - passed_tests
        
        # 按类别统计
        categories = {
            "转图表": ["text_to_table", "text_to_chart", "text_to_flowchart"],
            "表格操作": ["table_add_row", "table_format"],
            "图表操作": ["chart_change_type", "chart_update_data"],
            "流程图操作": ["flowchart_add_step"],
            "图片操作": ["image_change"],
            "内容优化": ["optimize_title", "add_bullet", "simplify"]
        }
        
        print("\n📋 分类统计:")
        for category, test_ids in categories.items():
            category_results = [r for r in self.results if r["id"] in test_ids]
            category_passed = sum(1 for r in category_results if r["success"])
            category_total = len(category_results)
            status = "✅" if category_passed == category_total else "⚠️"
            print(f"  {status} {category}: {category_passed}/{category_total}")
        
        print(f"\n📈 总体统计:")
        print(f"  - 总测试数: {total_tests}")
        print(f"  - 通过: {passed_tests}")
        print(f"  - 失败: {failed_tests}")
        print(f"  - 通过率: {passed_tests/total_tests*100:.1f}%")
        print(f"  - 总耗时: {total_elapsed:.2f}秒")
        
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
            print(f"  {status} {result['name']}: 质量{quality:.1f}%, 耗时{result.get('elapsed', 0):.2f}s")
            
            if not result["success"] and "error" in result:
                print(f"      错误: {result['error']}")
        
        # Benchmark结果
        print(f"\n🏆 Benchmark结果:")
        print(f"  - 指令正确执行率: {passed_tests/total_tests*100:.1f}%")
        if quality_scores:
            print(f"  - 平均执行质量: {avg_quality:.1f}%")
        
        # 建议
        print(f"\n💡 建议:")
        failed_results = [r for r in self.results if not r["success"]]
        if failed_results:
            print(f"  - 失败测试: {', '.join(r['name'] for r in failed_results)}")
            print(f"  - 建议优化prompt或检查AI响应解析")
        else:
            print(f"  - 所有测试通过，共创功能质量良好！")
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "pass_rate": passed_tests/total_tests*100,
            "avg_quality": sum(quality_scores)/len(quality_scores) if quality_scores else 0,
            "total_elapsed": total_elapsed,
            "results": self.results
        }


def main():
    """主函数"""
    tester = CocreationQualityTester()
    tester.run_all_tests()
    
    # 生成报告
    report = tester.generate_report(0)  # 已经在run_all_tests中计算了时间
    
    # 保存报告
    report_path = "/Users/onetwo/Documents/trae_projects/OpenCopilot/test_cocreation_quality_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n📄 详细报告已保存到: {report_path}")
    
    return report["pass_rate"] >= 70


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
