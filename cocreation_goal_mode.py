#!/usr/bin/env python3
"""
PPT共创功能 - Goal模式

目标：利用AI生成prompt，不断尝试产出正确的产物，除非用户强制终止

核心思想：
1. 定义目标（goal）
2. AI生成prompt
3. 执行并验证结果
4. 如果不符合目标，自动调整prompt重试
5. 直到达到目标或用户强制终止
"""

import sys
import os
import time
import json
import copy
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class GoalType(Enum):
    """目标类型"""
    TEXT_TO_TABLE = "text_to_table"
    TEXT_TO_CHART = "text_to_chart"
    TEXT_TO_FLOWCHART = "text_to_flowchart"
    IMAGE_CHANGE = "image_change"
    TABLE_ADD_ROW = "table_add_row"
    TABLE_FORMAT = "table_format"
    CHART_CHANGE_TYPE = "chart_change_type"
    CHART_UPDATE_DATA = "chart_update_data"
    FLOWCHART_ADD_STEP = "flowchart_add_step"
    OPTIMIZE_TITLE = "optimize_title"
    ADD_BULLET = "add_bullet"
    SIMPLIFY = "simplify"


@dataclass
class Goal:
    """目标定义"""
    goal_type: GoalType
    description: str
    slide_index: int
    validation_rules: Dict[str, Any]
    max_attempts: int = 99
    current_attempt: int = 0


@dataclass
class AttemptResult:
    """尝试结果"""
    success: bool
    actions: List[Dict]
    quality_score: float
    error_message: str = ""
    prompt_used: str = ""


class GoalMode:
    """Goal模式：不断尝试直到达成目标"""
    
    def __init__(self):
        self.test_slides = None
        self.original_slide = None
        self.goal = None
        self.attempts = []
        self.max_attempts = 99
    
    def reset_slides(self, slides: List[Dict]):
        """重置测试数据"""
        self.test_slides = copy.deepcopy(slides)
    
    def set_goal(self, goal: Goal):
        """设置目标"""
        self.goal = goal
        self.original_slide = copy.deepcopy(self.test_slides[goal.slide_index])
        self.attempts = []
    
    def generate_prompt(self, attempt: int, feedback: str = "") -> str:
        """生成prompt，根据尝试次数和反馈调整"""
        slide = self.test_slides[self.goal.slide_index]
        
        # 基础prompt
        base_prompt = f"""PPT 共 {len(self.test_slides)} 页，当前第 {self.goal.slide_index + 1} 页。

当前幻灯片：
```json
{json.dumps(slide, ensure_ascii=False, indent=2)}
```

用户指令：{self.goal.description}

"""
        
        # 根据目标类型添加特定要求
        if self.goal.goal_type == GoalType.TEXT_TO_TABLE:
            base_prompt += """请将当前内容转换为表格格式。

【必须返回的数据结构】：
{
  "actions": [
    {
      "action": "update",
      "slide_index": {slide_index},
      "field": "content_type",
      "value": "table"
    },
    {
      "action": "update",
      "slide_index": {slide_index},
      "field": "table_data",
      "value": {
        "columns": ["列名1", "列名2", "列名3"],
        "rows": [
          ["值1", "值2", "值3"],
          ["值4", "值5", "值6"]
        ]
      }
    }
  ]
}

【重要】：
1. 必须返回纯JSON格式
2. table_data必须包含columns和rows字段
3. columns是列名数组，rows是数据数组
4. 每行数据必须与列名对应
"""
        
        elif self.goal.goal_type == GoalType.TEXT_TO_CHART:
            base_prompt += """请将当前内容转换为图表格式。

【必须返回的数据结构】：
{
  "actions": [
    {
      "action": "update",
      "slide_index": {slide_index},
      "field": "content_type",
      "value": "chart"
    },
    {
      "action": "update",
      "slide_index": {slide_index},
      "field": "chart_data",
      "value": {
        "labels": ["标签1", "标签2", "标签3"],
        "datasets": [
          {
            "label": "数据系列1",
            "data": [100, 200, 300],
            "color": "#4da6ff"
          }
        ]
      }
    }
  ]
}

【重要】：
1. 必须返回纯JSON格式
2. chart_data必须包含labels和datasets字段
3. labels是X轴标签数组
4. datasets是数据系列数组，每个系列包含label、data、color
"""
        
        elif self.goal.goal_type == GoalType.TEXT_TO_FLOWCHART:
            base_prompt += """请将当前内容转换为流程图格式。

【必须返回的数据结构】：
{
  "actions": [
    {
      "action": "update",
      "slide_index": {slide_index},
      "field": "content_type",
      "value": "flowchart"
    },
    {
      "action": "update",
      "slide_index": {slide_index},
      "field": "flowchart_data",
      "value": {
        "title": "流程图标题",
        "steps": ["步骤1", "步骤2", "步骤3"]
      }
    }
  ]
}

【重要】：
1. 必须返回纯JSON格式
2. flowchart_data必须包含title和steps字段
3. steps是步骤数组，每个步骤是一个字符串
4. 步骤应该按逻辑顺序排列
"""
        
        elif self.goal.goal_type == GoalType.IMAGE_CHANGE:
            base_prompt += """请为当前幻灯片添加配图描述。

【必须返回的数据结构】：
{
  "actions": [
    {
      "action": "update",
      "slide_index": {slide_index},
      "field": "image_desc",
      "value": "配图描述内容"
    }
  ]
}

【重要】：
1. 必须返回纯JSON格式
2. image_desc是图片描述字符串
3. 描述应该与内容相关
"""
        
        else:
            base_prompt += """请执行操作。

返回格式：{{"actions": [修改指令1, 修改指令2, ...]}}
"""
        
        # 添加反馈（如果有）
        if feedback and attempt > 1:
            base_prompt += f"""

【上次尝试反馈】：
{feedback}

请根据反馈调整输出，确保符合要求。
"""
        
        # 添加尝试次数提示
        if attempt > 1:
            base_prompt += f"""

【当前是第{attempt}次尝试，请务必严格按照要求的格式返回】
"""
        
        return base_prompt
    
    def validate_result(self, actions: List[Dict]) -> tuple[bool, float, str]:
        """验证结果是否符合目标"""
        if not actions:
            return False, 0.0, "未返回任何actions"
        
        slide_index = self.goal.slide_index
        validation_rules = self.goal.validation_rules
        
        # 获取应用后的数据
        test_slide = copy.deepcopy(self.test_slides[slide_index])
        
        # 应用actions
        for action in actions:
            if action.get("action") == "update":
                field = action.get("field")
                value = action.get("value")
                
                # 兼容各种字段名
                if field in ["table_data", "table_config"] and isinstance(value, dict):
                    test_slide["table_data"] = value
                elif field in ["chart_data", "chart_config"] and isinstance(value, dict):
                    test_slide["chart_data"] = value
                elif field in ["flowchart_data", "flowchart_config", "content"] and isinstance(value, dict):
                    test_slide["flowchart_data"] = value
                elif field == "image_desc" and isinstance(value, str):
                    test_slide["image_desc"] = value
                elif field in ["content_type", "layout"] and isinstance(value, str):
                    test_slide["content_type"] = value
        
        # 验证规则
        passed_checks = 0
        total_checks = 0
        feedback_parts = []
        
        for rule_name, rule_check in validation_rules.items():
            total_checks += 1
            if rule_check(test_slide):
                passed_checks += 1
            else:
                feedback_parts.append(f"❌ {rule_name}")
        
        quality_score = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        success = quality_score >= 80  # 80%以上算成功
        
        feedback = "; ".join(feedback_parts) if feedback_parts else "所有检查通过"
        
        return success, quality_score, feedback
    
    def call_ai(self, prompt: str) -> str:
        """调用AI生成响应"""
        try:
            from opencopilot.agent.caller import call_agent_pipeline_sync
            
            full_text = ""
            for chunk in call_agent_pipeline_sync(
                prompt,
                action_type="chat",
                session_id=f"goal_mode_{int(time.time())}",
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
    
    def run(self) -> tuple[bool, List[AttemptResult]]:
        """运行goal模式"""
        if not self.goal:
            return False, []
        
        print(f"\n🎯 Goal模式启动")
        print(f"   目标: {self.goal.description}")
        print(f"   最大尝试次数: {self.max_attempts}")
        
        for attempt in range(1, self.max_attempts + 1):
            print(f"\n{'='*60}")
            print(f"🔄 第{attempt}次尝试")
            print(f"{'='*60}")
            
            # 生成prompt
            feedback = self.attempts[-1].error_message if self.attempts else ""
            prompt = self.generate_prompt(attempt, feedback)
            
            # 调用AI
            print("  📤 调用AI...")
            start_time = time.time()
            response = self.call_ai(prompt)
            elapsed = time.time() - start_time
            
            if not response:
                result = AttemptResult(
                    success=False,
                    actions=[],
                    quality_score=0.0,
                    error_message="AI调用失败",
                    prompt_used=prompt
                )
                self.attempts.append(result)
                continue
            
            print(f"  ✅ AI响应: {len(response)} 字符, 耗时 {elapsed:.2f}s")
            
            # 解析响应
            actions = self.parse_ai_response(response)
            print(f"  📋 解析到 {len(actions)} 个actions")
            
            if not actions:
                result = AttemptResult(
                    success=False,
                    actions=[],
                    quality_score=0.0,
                    error_message="未解析到actions",
                    prompt_used=prompt
                )
                self.attempts.append(result)
                continue
            
            # 验证结果
            success, quality_score, feedback = self.validate_result(actions)
            print(f"  📊 质量得分: {quality_score:.1f}%")
            print(f"  📝 反馈: {feedback}")
            
            result = AttemptResult(
                success=success,
                actions=actions,
                quality_score=quality_score,
                error_message=feedback if not success else "",
                prompt_used=prompt
            )
            self.attempts.append(result)
            
            # 如果成功，返回
            if success:
                print(f"\n✅ 目标达成！第{attempt}次尝试成功")
                return True, self.attempts
            
            print(f"  ⚠️ 未达标，继续尝试...")
        
        print(f"\n❌ 达到最大尝试次数({self.max_attempts})，目标未达成")
        return False, self.attempts


def create_validation_rules(goal_type: GoalType) -> Dict[str, Any]:
    """创建验证规则"""
    if goal_type == GoalType.TEXT_TO_TABLE:
        return {
            "table_data存在": lambda slide: "table_data" in slide,
            "table_data有columns字段": lambda slide: "columns" in slide.get("table_data", {}),
            "table_data有rows字段": lambda slide: "rows" in slide.get("table_data", {}),
            "rows数量>=3": lambda slide: len(slide.get("table_data", {}).get("rows", [])) >= 3
        }
    elif goal_type == GoalType.TEXT_TO_CHART:
        return {
            "chart_data存在": lambda slide: "chart_data" in slide,
            "chart_data有labels字段": lambda slide: "labels" in slide.get("chart_data", {}),
            "chart_data有datasets字段": lambda slide: "datasets" in slide.get("chart_data", {}),
            "labels数量>=3": lambda slide: len(slide.get("chart_data", {}).get("labels", [])) >= 3
        }
    elif goal_type == GoalType.TEXT_TO_FLOWCHART:
        return {
            "flowchart_data存在": lambda slide: "flowchart_data" in slide,
            "flowchart_data有title字段": lambda slide: "title" in slide.get("flowchart_data", {}),
            "flowchart_data有steps字段": lambda slide: "steps" in slide.get("flowchart_data", {}),
            "steps数量>=3": lambda slide: len(slide.get("flowchart_data", {}).get("steps", [])) >= 3
        }
    elif goal_type == GoalType.IMAGE_CHANGE:
        return {
            "image_desc存在": lambda slide: "image_desc" in slide,
            "image_desc非空": lambda slide: bool(slide.get("image_desc", "").strip())
        }
    else:
        return {}


def main():
    """主函数：演示goal模式"""
    print("\n" + "🚀"*30)
    print("PPT共创 - Goal模式演示")
    print("🚀"*30)
    
    # 测试数据
    test_slides = [
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
    
    # 定义目标
    goals = [
        Goal(
            goal_type=GoalType.TEXT_TO_TABLE,
            description="将销售数据转换为表格格式",
            slide_index=0,
            validation_rules=create_validation_rules(GoalType.TEXT_TO_TABLE),
            max_attempts=99  # 使用99次默认上限
        ),
        Goal(
            goal_type=GoalType.TEXT_TO_CHART,
            description="将销售数据转换为柱状图",
            slide_index=0,
            validation_rules=create_validation_rules(GoalType.TEXT_TO_CHART),
            max_attempts=99  # 使用99次默认上限
        ),
        Goal(
            goal_type=GoalType.TEXT_TO_FLOWCHART,
            description="将技术架构转换为流程图",
            slide_index=1,
            validation_rules=create_validation_rules(GoalType.TEXT_TO_FLOWCHART),
            max_attempts=99  # 使用99次默认上限
        ),
        Goal(
            goal_type=GoalType.IMAGE_CHANGE,
            description="为销售报告添加配图描述",
            slide_index=0,
            validation_rules=create_validation_rules(GoalType.IMAGE_CHANGE),
            max_attempts=99  # 使用99次默认上限
        )
    ]
    
    # 运行所有目标
    results = []
    for goal in goals:
        print(f"\n{'='*60}")
        print(f"🎯 目标: {goal.description}")
        print(f"{'='*60}")
        
        goal_mode = GoalMode()
        goal_mode.reset_slides(test_slides)
        goal_mode.set_goal(goal)
        goal_mode.max_attempts = goal.max_attempts
        
        success, attempts = goal_mode.run()
        results.append({
            "goal": goal.description,
            "success": success,
            "attempts": len(attempts),
            "quality_score": attempts[-1].quality_score if attempts else 0
        })
    
    # 生成报告
    print("\n" + "="*60)
    print("📊 Goal模式测试报告")
    print("="*60)
    
    total_goals = len(results)
    achieved_goals = sum(1 for r in results if r["success"])
    
    print(f"\n总体统计:")
    print(f"  - 总目标数: {total_goals}")
    print(f"  - 达成目标: {achieved_goals}")
    print(f"  - 成功率: {achieved_goals/total_goals*100:.1f}%")
    
    print(f"\n详细结果:")
    for r in results:
        status = "✅" if r["success"] else "❌"
        print(f"  {status} {r['goal']}: 尝试{r['attempts']}次, 质量{r['quality_score']:.1f}%")
    
    return achieved_goals == total_goals


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
