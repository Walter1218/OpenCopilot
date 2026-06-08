"""
PPT 渲染执行器

执行渲染指令，将 RenderCommand 转换为 slides_data 更新。

核心职责：
- 执行渲染指令（调用 ContentConvertSkill 等能力）
- 更新 slides_data
- 维护原文↔幻灯片映射
- 提供埋点和日志
"""

import json
import time
import uuid
from typing import List, Dict, Any, Optional, Tuple

from .render_command import (
    RenderCommand, RenderGroup, RenderResult,
    convert_render_command_to_slide_json
)


class RenderExecutor:
    """
    渲染执行器
    
    执行渲染指令，更新 slides_data。
    """
    
    def __init__(self, slides_data: List[Dict], original_text: str = ""):
        """
        Args:
            slides_data: 幻灯片数据列表（会被修改）
            original_text: 原始文档文本
        """
        self.slides_data = slides_data
        self.original_text = original_text
        self._trace_id = uuid.uuid4().hex[:8]
        
        # 埋点追踪
        self._render_history: List[Dict] = []
    
    def execute(self, command: RenderCommand) -> RenderResult:
        """
        执行单条渲染指令
        
        Args:
            command: 渲染指令
            
        Returns:
            渲染结果
        """
        start_time = time.time()
        trace_id = command.trace_id or self._trace_id
        
        try:
            # 1. 验证指令
            validation_error = self._validate_command(command)
            if validation_error:
                return RenderResult(
                    success=False,
                    slide_index=command.slide_index,
                    message=f"指令验证失败: {validation_error}",
                    trace_id=trace_id
                )
            
            # 2. 确定目标幻灯片
            slide_index = command.slide_index
            if slide_index < 0 or slide_index >= len(self.slides_data):
                # 新建幻灯片
                slide_index = self._create_new_slide(command)
            
            # 3. 执行渲染
            slide_data = self._render_to_slide(command, slide_index)
            
            # 4. 更新 slides_data
            self.slides_data[slide_index] = slide_data
            
            # 5. 记录历史
            elapsed_ms = (time.time() - start_time) * 1000
            self._render_history.append({
                "trace_id": trace_id,
                "command_id": command.command_id,
                "render_type": command.render_type,
                "slide_index": slide_index,
                "elapsed_ms": elapsed_ms,
                "success": True,
            })
            
            # 6. 埋点
            self._log_render_event(command, slide_index, elapsed_ms, True)
            
            return RenderResult(
                success=True,
                slide_index=slide_index,
                slide_data=slide_data,
                source_ranges=[command.source_range] if command.source_range else [],
                message=f"渲染成功: {command.render_type}",
                trace_id=trace_id
            )
            
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self._log_render_event(command, command.slide_index, elapsed_ms, False, str(e))
            
            return RenderResult(
                success=False,
                slide_index=command.slide_index,
                message=f"渲染失败: {e}",
                trace_id=trace_id
            )
    
    def execute_group(self, group: RenderGroup) -> List[RenderResult]:
        """
        执行渲染组（多条指令合并为一页）
        
        Args:
            group: 渲染组
            
        Returns:
            渲染结果列表
        """
        results = []
        
        # 确定目标幻灯片
        slide_index = group.target_slide
        if slide_index < 0 or slide_index >= len(self.slides_data):
            # 新建幻灯片
            slide_index = self._create_new_slide_from_group(group)
        
        # 合并所有指令到同一页
        merged_slide = self.slides_data[slide_index].copy()
        merged_slide.setdefault("items", [])
        
        for cmd in group.commands:
            try:
                # 渲染单条指令
                item_data = self._render_to_item(cmd)
                merged_slide["items"].append(item_data)
                
                results.append(RenderResult(
                    success=True,
                    slide_index=slide_index,
                    message=f"渲染成功: {cmd.render_type}",
                    trace_id=cmd.trace_id
                ))
            except Exception as e:
                results.append(RenderResult(
                    success=False,
                    slide_index=slide_index,
                    message=f"渲染失败: {e}",
                    trace_id=cmd.trace_id
                ))
        
        # 更新 slides_data
        self.slides_data[slide_index] = merged_slide
        
        return results
    
    def _validate_command(self, command: RenderCommand) -> Optional[str]:
        """验证渲染指令"""
        if not command.render_type:
            return "缺少 render_type"
        
        if command.render_type not in {
            "text", "table", "chart", "flowchart",
            "image_right", "image_left", "image_top",
            "quote", "highlight", "code"
        }:
            return f"不支持的 render_type: {command.render_type}"
        
        return None
    
    def _create_new_slide(self, command: RenderCommand) -> int:
        """新建幻灯片"""
        new_slide = {
            "type": "content",
            "layout": "text_only",
            "title": command.render_params.get("title", ""),
            "items": []
        }
        self.slides_data.append(new_slide)
        return len(self.slides_data) - 1
    
    def _create_new_slide_from_group(self, group: RenderGroup) -> int:
        """从渲染组新建幻灯片"""
        new_slide = {
            "type": "content",
            "layout": group.layout,
            "title": "",
            "items": []
        }
        self.slides_data.append(new_slide)
        return len(self.slides_data) - 1
    
    def _render_to_slide(self, command: RenderCommand, slide_index: int) -> Dict[str, Any]:
        """将渲染指令应用到幻灯片"""
        slide = self.slides_data[slide_index].copy()
        
        # 根据 slot 更新不同位置
        if command.slot == "title":
            slide["title"] = command.render_params.get(
                "title",
                command.render_params.get("text", command.source_text),
            )
        else:
            if command.render_type in ("image_right", "image_left", "image_top"):
                slide["layout"] = command.render_type
            # 默认更新 items
            item_data = self._render_to_item(command)
            slide.setdefault("items", []).append(item_data)
        
        return slide
    
    def _render_to_item(self, command: RenderCommand) -> Dict[str, Any]:
        """将渲染指令转换为 item 数据"""
        if command.render_type == "chart":
            return {
                "content_type": "chart",
                "chart_type": command.render_params.get("chart_type", "bar"),
                "chart_data": command.render_params.get("chart_data", {}),
                "text": command.source_text
            }
        elif command.render_type == "table":
            return {
                "content_type": "table",
                "table_data": command.render_params.get("table_data", {}),
                "text": command.source_text
            }
        elif command.render_type == "flowchart":
            return {
                "content_type": "flowchart",
                "flowchart_data": command.render_params.get("flowchart_data", {}),
                "text": command.source_text
            }
        elif command.render_type == "quote":
            # 引用样式
            return {
                "content_type": "text",
                "text": command.source_text,
                "style": "quote",
                "source": command.render_params.get("source", "")
            }
        elif command.render_type == "highlight":
            # 高亮要点
            return {
                "content_type": "text",
                "text": command.source_text,
                "style": "highlight",
                "highlight_color": command.render_params.get("color", "#FFD700")
            }
        elif command.render_type == "code":
            # 代码块
            return {
                "content_type": "text",
                "text": command.source_text,
                "style": "code",
                "language": command.render_params.get("language", "")
            }
        elif command.render_type in ("image_right", "image_left", "image_top"):
            # 图文混排
            return {
                "content_type": "image",
                "text": command.source_text,
                "layout": command.render_type,
                "image_url": command.render_params.get("image_url", ""),
                "image_desc": command.render_params.get("image_desc", "")
            }
        else:
            # 默认文本
            return {
                "content_type": "text",
                "text": command.render_params.get("text", command.source_text)
            }
    
    def _log_render_event(
        self,
        command: RenderCommand,
        slide_index: int,
        elapsed_ms: float,
        success: bool,
        error: str = ""
    ):
        """记录渲染事件日志"""
        try:
            from opencopilot.agent.observability import PipelineObservability
            obs = PipelineObservability.get_instance()
            
            event_data = {
                "trace_id": command.trace_id or self._trace_id,
                "command_id": command.command_id,
                "render_type": command.render_type,
                "slide_index": slide_index,
                "elapsed_ms": round(elapsed_ms, 2),
                "success": success,
                "source_range": command.source_range,
                "instruction": command.instruction[:50] if command.instruction else "",
            }
            if error:
                event_data["error"] = error
            
            event_name = "RENDER_COMMAND_SUCCESS" if success else "RENDER_COMMAND_FAILED"
            obs.gui_log(
                f"RenderCommand {event_name} | {json.dumps(event_data, ensure_ascii=False)}",
                session_id=f"render_{self._trace_id}",
                event=event_name
            )
        except Exception:
            pass
    
    def get_render_history(self) -> List[Dict]:
        """获取渲染历史"""
        return self._render_history.copy()


# ============================================================
# 渲染调度器（高层接口）
# ============================================================

class RenderDispatcher:
    """
    渲染调度器
    
    协调 RenderCommandParser、RenderExecutor 和现有组件。
    提供统一的渲染入口。
    """
    
    def __init__(self, slides_data: List[Dict], original_text: str = ""):
        self.slides_data = slides_data
        self.original_text = original_text
        self.executor = RenderExecutor(slides_data, original_text)
        self._trace_id = uuid.uuid4().hex[:8]
    
    def dispatch_from_ai_response(
        self,
        response: str,
        current_index: int = 0
    ) -> Tuple[List[RenderResult], List[Dict]]:
        """
        从 AI 响应分发渲染指令
        
        Args:
            response: AI 响应文本
            current_index: 当前幻灯片索引
            
        Returns:
            (渲染结果列表, 旧格式 actions 列表)
        """
        from .render_command import RenderCommandParser
        
        # 1. 尝试解析为渲染指令
        commands = RenderCommandParser.parse(response, self.original_text)
        
        if commands:
            # 设置默认 slide_index
            for cmd in commands:
                if cmd.slide_index < 0:
                    cmd.slide_index = current_index
                
                # 设置 trace_id
                if not cmd.trace_id:
                    cmd.trace_id = self._trace_id
            
            # 执行渲染
            results = []
            for cmd in commands:
                result = self.executor.execute(cmd)
                results.append(result)
            
            # 埋点
            self._log_dispatch_event(len(commands), len([r for r in results if r.success]))
            
            return results, []
        
        # 2. 回退：返回空结果，让 CoCreationWidget 处理旧格式
        return [], []
    
    def dispatch_from_render_commands(
        self,
        commands: List[RenderCommand],
        current_index: int = 0
    ) -> List[RenderResult]:
        """
        直接执行渲染指令列表
        
        Args:
            commands: 渲染指令列表
            current_index: 当前幻灯片索引
            
        Returns:
            渲染结果列表
        """
        # 设置默认 slide_index
        for cmd in commands:
            if cmd.slide_index < 0:
                cmd.slide_index = current_index
            
            # 设置 trace_id
            if not cmd.trace_id:
                cmd.trace_id = self._trace_id
        
        # 执行渲染
        results = []
        for cmd in commands:
            result = self.executor.execute(cmd)
            results.append(result)
        
        # 埋点
        self._log_dispatch_event(len(commands), len([r for r in results if r.success]))
        
        return results
    
    def _log_dispatch_event(self, total: int, success: int):
        """记录分发事件"""
        try:
            from opencopilot.agent.observability import PipelineObservability
            obs = PipelineObservability.get_instance()
            
            obs.gui_log(
                f"RenderDispatcher | total={total} success={success}",
                session_id=f"dispatch_{self._trace_id}",
                event="RENDER_DISPATCH"
            )
        except Exception:
            pass
