"""
渲染指令系统端到端 LLM 测试

验证 Agent Pipeline 在真实 LLM 调用下：
1. 能否正确返回渲染指令格式
2. 渲染指令能否正确执行
3. 输出质量是否符合预期

注意：这些测试消耗真实的 LLM token，已标记为 @pytest.mark.slow。
运行前请确保 LLM 服务配置正确。
"""

from __future__ import annotations

import os
import re
import sys
import json
import uuid
import signal
import threading
from typing import List, Dict, Any
from pathlib import Path

import pytest

# ── 项目根目录注入 ──
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


# ── 超时装饰器 ──
try:
    from pytest_timeout import timeout as _timeout_decorator
    def _timeout(seconds: int):
        return pytest.mark.timeout(seconds, method="signal")
except ImportError:
    def _timeout(seconds: int):
        def decorator(func):
            return func
        return decorator


# ── 常量 ──
LLM_TIMEOUT_SECONDS = 90
COLLECT_TIMEOUT_SECONDS = 85
MIN_RENDER_COMMANDS = 1


# ── 辅助函数 ──

def _check_llm_available() -> tuple[bool, str]:
    """检查 LLM 服务是否可用"""
    try:
        from llm_provider import load_config
        cfg = load_config()
        provider_type = cfg.get("provider_type", "mimo")
        
        if provider_type == "mimo":
            api_key = cfg.get("mimo_api_key") or os.environ.get("XIAOMI_API_KEY") or os.environ.get("MIMO_API_KEY")
            if not api_key:
                return False, "MiMo API key 未配置"
        elif provider_type == "minimax":
            api_key = cfg.get("minimax_api_key") or os.environ.get("MINIMAX_API_KEY")
            if not api_key:
                return False, "MiniMax API key 未配置"
        elif provider_type == "local":
            api_base = cfg.get("local_api_base", "http://localhost:11434/v1")
            return True, f"Local provider ({api_base})"
        else:
            return False, f"未知的 provider_type: {provider_type}"
        
        return True, f"{provider_type} provider 已配置"
    except Exception as e:
        return False, f"检查 LLM 配置时出错: {e}"


def _collect_pipeline_output(
    prompt: str,
    action_type: str,
    context_source: str = "test",
    context_meta: dict | None = None,
    timeout: int = COLLECT_TIMEOUT_SECONDS,
) -> tuple[str, int]:
    """调用 call_agent_pipeline_sync 并收集全部输出"""
    from opencopilot.agent.caller import call_agent_pipeline_sync
    
    full_text = ""
    chunk_count = 0
    cancel_event = threading.Event()
    
    def _alarm_handler(signum, frame):
        cancel_event.set()
        raise TimeoutError(f"LLM 调用超时（>{timeout}秒）")
    
    old_handler = None
    try:
        old_handler = signal.signal(signal.SIGALRM, _alarm_handler)
        signal.alarm(timeout)
        
        for chunk in call_agent_pipeline_sync(
            text=prompt,
            action_type=action_type,
            session_id=f"e2e-render-{uuid.uuid4().hex[:8]}",
            context_source=context_source,
            context_meta=context_meta or {},
            is_new_task=True,
            cancel_event=cancel_event,
            timeout=timeout,
        ):
            full_text += chunk
            chunk_count += 1
            if cancel_event.is_set():
                break
        
        signal.alarm(0)
    except TimeoutError:
        raise RuntimeError(f"LLM 调用超时（>{timeout}秒）")
    except Exception as e:
        raise RuntimeError(f"LLM 调用失败: {e}")
    finally:
        if old_handler is not None:
            signal.signal(signal.SIGALRM, old_handler)
        signal.alarm(0)
    
    return full_text, chunk_count


def _parse_render_commands(response: str) -> List[Dict[str, Any]]:
    """从 AI 响应解析渲染指令"""
    from opencopilot.capabilities.ppt.render_command import RenderCommandParser
    
    commands = RenderCommandParser.parse(response)
    return [cmd.to_dict() for cmd in commands]


def _validate_render_command(cmd: Dict[str, Any]) -> tuple[bool, str]:
    """验证渲染指令的结构完整性"""
    # 必须字段
    required_fields = ["render_type", "source_text"]
    for field in required_fields:
        if field not in cmd:
            return False, f"缺少必须字段: {field}"
    
    # render_type 有效性
    valid_types = {"text", "table", "chart", "flowchart", "image_right", "image_left", "image_top", "quote", "highlight", "code"}
    if cmd["render_type"] not in valid_types:
        return False, f"无效的 render_type: {cmd['render_type']}"
    
    # render_params 存在性
    if "render_params" not in cmd:
        return False, "缺少 render_params"
    
    return True, "OK"


def _validate_chart_params(params: Dict[str, Any]) -> tuple[bool, str]:
    """验证图表参数"""
    if "chart_type" not in params:
        return False, "图表类型缺少 chart_type"
    
    valid_chart_types = {"bar", "line", "pie", "scatter", "area"}
    if params["chart_type"] not in valid_chart_types:
        return False, f"无效的 chart_type: {params['chart_type']}"
    
    if "chart_data" not in params:
        return False, "图表类型缺少 chart_data"
    
    chart_data = params["chart_data"]
    if "labels" not in chart_data and "categories" not in chart_data:
        return False, "chart_data 缺少 labels/categories"
    
    if "values" not in chart_data and "data" not in chart_data:
        return False, "chart_data 缺少 values/data"
    
    return True, "OK"


def _validate_table_params(params: Dict[str, Any]) -> tuple[bool, str]:
    """验证表格参数"""
    if "table_data" not in params:
        return False, "表格类型缺少 table_data"
    
    table_data = params["table_data"]
    if "headers" not in table_data and "columns" not in table_data:
        return False, "table_data 缺少 headers/columns"
    
    if "rows" not in table_data and "data" not in table_data:
        return False, "table_data 缺少 rows/data"
    
    return True, "OK"


def _validate_flowchart_params(params: Dict[str, Any]) -> tuple[bool, str]:
    """验证流程图参数"""
    if "flowchart_data" not in params:
        return False, "流程图类型缺少 flowchart_data"
    
    flowchart_data = params["flowchart_data"]
    if "nodes" not in flowchart_data and "steps" not in flowchart_data:
        return False, "flowchart_data 缺少 nodes/steps"
    
    return True, "OK"


# ── 测试数据 ──

SAMPLE_SLIDES = [
    {
        "type": "content",
        "layout": "text_only",
        "title": "公司概况",
        "items": [
            {"text": "成立于2020年，专注于AI技术研发"},
            {"text": "团队规模50人，核心成员来自BAT"}
        ]
    },
    {
        "type": "content",
        "layout": "text_only",
        "title": "财务数据",
        "items": [
            {"text": "2024年营收8.5亿元，同比增长25%"},
            {"text": "2025年预计营收12.8亿元，净利润率15%"}
        ]
    }
]

SAMPLE_ORIGINAL_TEXT = """
一、公司概况
成立于2020年，专注于AI技术研发，团队规模50人，核心成员来自BAT。

二、财务数据
2024年营收8.5亿元，同比增长25%。
2025年预计营收12.8亿元，净利润率15%。

三、产品线
- 智能助手：月活用户100万
- 企业解决方案：服务50+大型企业
- 开发者平台：API调用量日均1000万次
"""


# ── 测试类 ──

@pytest.mark.slow
class TestRenderCommandE2E:
    """渲染指令系统端到端测试 - 调用真实 LLM"""
    
    @pytest.fixture(scope="class")
    def llm_available(self):
        """Fixture: 检查 LLM 是否可用"""
        available, msg = _check_llm_available()
        if not available:
            pytest.skip(f"LLM 服务不可用: {msg}")
        return True
    
    @pytest.fixture(scope="class")
    def chart_render_output(self, llm_available):
        """Fixture: 调用 LLM 生成图表渲染指令"""
        prompt = f"""你是一个PPT编辑助手。用户想要将以下内容转换为柱状图。

当前幻灯片数据：
{json.dumps(SAMPLE_SLIDES[1], ensure_ascii=False, indent=2)}

请将"财务数据"中的营收数据转换为柱状图。

输出格式：
```json
{{
  "render_commands": [
    {{
      "source_text": "原文片段",
      "render_type": "chart",
      "render_params": {{
        "chart_type": "bar",
        "title": "图表标题",
        "chart_data": {{
          "labels": ["标签1", "标签2"],
          "values": [数值1, 数值2]
        }}
      }}
    }}
  ]
}}
```

请只返回JSON，不要其他文字。"""
        
        try:
            full_text, chunk_count = _collect_pipeline_output(
                prompt=prompt,
                action_type="chat",
                context_source="ppt_editor",
            )
        except RuntimeError as e:
            pytest.fail(f"LLM 调用失败: {e}")
        
        return {"text": full_text, "chunks": chunk_count}
    
    @pytest.fixture(scope="class")
    def table_render_output(self, llm_available):
        """Fixture: 调用 LLM 生成表格渲染指令"""
        prompt = f"""你是一个PPT编辑助手。用户想要将以下内容转换为表格。

原始文本：
{SAMPLE_ORIGINAL_TEXT}

请将"产品线"部分转换为表格。

输出格式：
```json
{{
  "render_commands": [
    {{
      "source_text": "原文片段",
      "render_type": "table",
      "render_params": {{
        "title": "表格标题",
        "table_data": {{
          "headers": ["列1", "列2"],
          "rows": [["值1", "值2"]]
        }}
      }}
    }}
  ]
}}
```

请只返回JSON，不要其他文字。"""
        
        try:
            full_text, chunk_count = _collect_pipeline_output(
                prompt=prompt,
                action_type="chat",
                context_source="ppt_editor",
            )
        except RuntimeError as e:
            pytest.fail(f"LLM 调用失败: {e}")
        
        return {"text": full_text, "chunks": chunk_count}
    
    @pytest.fixture(scope="class")
    def flowchart_render_output(self, llm_available):
        """Fixture: 调用 LLM 生成流程图渲染指令"""
        prompt = f"""你是一个PPT编辑助手。用户想要将以下步骤转换为流程图。

步骤内容：
1. 需求分析：收集用户需求，明确功能范围
2. 架构设计：设计系统架构，确定技术方案
3. 编码实现：编写代码，完成功能开发
4. 测试验证：执行测试用例，确保质量
5. 部署上线：部署到生产环境，正式发布

输出格式：
```json
{{
  "render_commands": [
    {{
      "source_text": "原文片段",
      "render_type": "flowchart",
      "render_params": {{
        "title": "流程图标题",
        "flowchart_data": {{
          "nodes": [
            {{"id": "1", "label": "步骤1", "type": "start"}},
            {{"id": "2", "label": "步骤2", "type": "process"}}
          ],
          "edges": [
            {{"from": "1", "to": "2"}}
          ]
        }}
      }}
    }}
  ]
}}
```

请只返回JSON，不要其他文字。"""
        
        try:
            full_text, chunk_count = _collect_pipeline_output(
                prompt=prompt,
                action_type="chat",
                context_source="ppt_editor",
            )
        except RuntimeError as e:
            pytest.fail(f"LLM 调用失败: {e}")
        
        return {"text": full_text, "chunks": chunk_count}
    
    # ── 图表渲染指令测试 ──
    
    def test_chart_output_not_empty(self, chart_render_output):
        """验证：图表渲染指令输出不为空"""
        assert chart_render_output["text"], "LLM 输出不应为空"
        assert chart_render_output["chunks"] > 0, "应至少有一个 chunk"
    
    def test_chart_output_is_valid_json(self, chart_render_output):
        """验证：图表输出是有效的 JSON"""
        text = chart_render_output["text"]
        # 尝试提取 JSON
        json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试直接解析
            json_str = text.strip()
        
        try:
            data = json.loads(json_str)
            assert isinstance(data, dict), "输出应该是字典类型"
            assert "render_commands" in data, "输出应包含 render_commands 字段"
        except json.JSONDecodeError as e:
            pytest.fail(f"输出不是有效的 JSON: {e}\n原始输出: {text[:500]}")
    
    def test_chart_render_commands_parsed(self, chart_render_output):
        """验证：能正确解析出渲染指令"""
        commands = _parse_render_commands(chart_render_output["text"])
        assert len(commands) >= MIN_RENDER_COMMANDS, f"应至少解析出 {MIN_RENDER_COMMANDS} 条渲染指令，实际: {len(commands)}"
    
    def test_chart_render_command_structure(self, chart_render_output):
        """验证：渲染指令结构完整"""
        commands = _parse_render_commands(chart_render_output["text"])
        for i, cmd in enumerate(commands):
            is_valid, msg = _validate_render_command(cmd)
            assert is_valid, f"渲染指令 {i} 结构无效: {msg}"
    
    def test_chart_render_type_is_chart(self, chart_render_output):
        """验证：渲染类型是 chart"""
        commands = _parse_render_commands(chart_render_output["text"])
        assert len(commands) > 0, "应至少有一条渲染指令"
        
        chart_commands = [cmd for cmd in commands if cmd.get("render_type") == "chart"]
        assert len(chart_commands) > 0, "应至少有一条 chart 类型的渲染指令"
    
    def test_chart_params_valid(self, chart_render_output):
        """验证：图表参数有效"""
        commands = _parse_render_commands(chart_render_output["text"])
        chart_commands = [cmd for cmd in commands if cmd.get("render_type") == "chart"]
        
        for cmd in chart_commands:
            params = cmd.get("render_params", {})
            is_valid, msg = _validate_chart_params(params)
            assert is_valid, f"图表参数无效: {msg}"
    
    def test_chart_data_has_values(self, chart_render_output):
        """验证：图表数据包含实际数值"""
        commands = _parse_render_commands(chart_render_output["text"])
        chart_commands = [cmd for cmd in commands if cmd.get("render_type") == "chart"]
        
        for cmd in chart_commands:
            chart_data = cmd.get("render_params", {}).get("chart_data", {})
            labels = chart_data.get("labels", chart_data.get("categories", []))
            values = chart_data.get("values", chart_data.get("data", []))
            
            assert len(labels) > 0, "图表应有标签"
            assert len(values) > 0, "图表应有数值"
            assert len(labels) == len(values), "标签和数值数量应匹配"
    
    # ── 表格渲染指令测试 ──
    
    def test_table_output_not_empty(self, table_render_output):
        """验证：表格渲染指令输出不为空"""
        assert table_render_output["text"], "LLM 输出不应为空"
    
    def test_table_render_commands_parsed(self, table_render_output):
        """验证：能正确解析出表格渲染指令"""
        commands = _parse_render_commands(table_render_output["text"])
        table_commands = [cmd for cmd in commands if cmd.get("render_type") == "table"]
        assert len(table_commands) > 0, "应至少有一条 table 类型的渲染指令"
    
    def test_table_params_valid(self, table_render_output):
        """验证：表格参数有效"""
        commands = _parse_render_commands(table_render_output["text"])
        table_commands = [cmd for cmd in commands if cmd.get("render_type") == "table"]
        
        for cmd in table_commands:
            params = cmd.get("render_params", {})
            is_valid, msg = _validate_table_params(params)
            assert is_valid, f"表格参数无效: {msg}"
    
    def test_table_data_structure(self, table_render_output):
        """验证：表格数据结构正确"""
        commands = _parse_render_commands(table_render_output["text"])
        table_commands = [cmd for cmd in commands if cmd.get("render_type") == "table"]
        
        for cmd in table_commands:
            table_data = cmd.get("render_params", {}).get("table_data", {})
            headers = table_data.get("headers", table_data.get("columns", []))
            rows = table_data.get("rows", table_data.get("data", []))
            
            assert len(headers) > 0, "表格应有表头"
            assert len(rows) > 0, "表格应有数据行"
            
            # 每行的列数应与表头匹配
            for row in rows:
                assert len(row) == len(headers), f"行数据列数 ({len(row)}) 应与表头列数 ({len(headers)}) 匹配"
    
    # ── 流程图渲染指令测试 ──
    
    def test_flowchart_output_not_empty(self, flowchart_render_output):
        """验证：流程图渲染指令输出不为空"""
        assert flowchart_render_output["text"], "LLM 输出不应为空"
    
    def test_flowchart_render_commands_parsed(self, flowchart_render_output):
        """验证：能正确解析出流程图渲染指令"""
        commands = _parse_render_commands(flowchart_render_output["text"])
        flowchart_commands = [cmd for cmd in commands if cmd.get("render_type") == "flowchart"]
        assert len(flowchart_commands) > 0, "应至少有一条 flowchart 类型的渲染指令"
    
    def test_flowchart_params_valid(self, flowchart_render_output):
        """验证：流程图参数有效"""
        commands = _parse_render_commands(flowchart_render_output["text"])
        flowchart_commands = [cmd for cmd in commands if cmd.get("render_type") == "flowchart"]
        
        for cmd in flowchart_commands:
            params = cmd.get("render_params", {})
            is_valid, msg = _validate_flowchart_params(params)
            assert is_valid, f"流程图参数无效: {msg}"
    
    def test_flowchart_has_nodes_and_edges(self, flowchart_render_output):
        """验证：流程图包含节点和边"""
        commands = _parse_render_commands(flowchart_render_output["text"])
        flowchart_commands = [cmd for cmd in commands if cmd.get("render_type") == "flowchart"]
        
        for cmd in flowchart_commands:
            flowchart_data = cmd.get("render_params", {}).get("flowchart_data", {})
            nodes = flowchart_data.get("nodes", flowchart_data.get("steps", []))
            
            assert len(nodes) >= 2, "流程图应至少有2个节点"
            
            # 每个节点应有 id 和 label
            for node in nodes:
                assert "id" in node or "step" in node, "节点应有 id 字段"
                assert "label" in node or "name" in node or "text" in node, "节点应有 label 字段"


@pytest.mark.slow
class TestRenderCommandExecution:
    """渲染指令执行测试 - 验证指令能正确执行"""
    
    def test_execute_chart_command(self):
        """验证：执行图表渲染指令"""
        from opencopilot.capabilities.ppt.render_command import RenderCommand
        from opencopilot.capabilities.ppt.render_executor import RenderExecutor
        
        slides_data = [
            {
                "type": "content",
                "layout": "text_only",
                "title": "财务数据",
                "items": [{"text": "2024年营收8.5亿元"}]
            }
        ]
        
        executor = RenderExecutor(slides_data, "这是原文")
        
        cmd = RenderCommand(
            source_text="2024年营收8.5亿元",
            render_type="chart",
            render_params={
                "chart_type": "bar",
                "title": "营收趋势",
                "chart_data": {
                    "labels": ["2024年"],
                    "values": [8.5]
                }
            },
            slide_index=0
        )
        
        result = executor.execute(cmd)
        assert result.success, f"执行应成功: {result.message}"
        assert result.slide_index == 0
    
    def test_execute_table_command(self):
        """验证：执行表格渲染指令"""
        from opencopilot.capabilities.ppt.render_command import RenderCommand
        from opencopilot.capabilities.ppt.render_executor import RenderExecutor
        
        slides_data = [
            {
                "type": "content",
                "layout": "text_only",
                "title": "产品对比",
                "items": []
            }
        ]
        
        executor = RenderExecutor(slides_data, "这是原文")
        
        cmd = RenderCommand(
            source_text="产品对比",
            render_type="table",
            render_params={
                "title": "产品对比",
                "table_data": {
                    "headers": ["产品", "价格", "评分"],
                    "rows": [
                        ["产品A", "100元", "4.5"],
                        ["产品B", "200元", "4.8"]
                    ]
                }
            },
            slide_index=0
        )
        
        result = executor.execute(cmd)
        assert result.success, f"执行应成功: {result.message}"
    
    def test_execute_flowchart_command(self):
        """验证：执行流程图渲染指令"""
        from opencopilot.capabilities.ppt.render_command import RenderCommand
        from opencopilot.capabilities.ppt.render_executor import RenderExecutor
        
        slides_data = [
            {
                "type": "content",
                "layout": "text_only",
                "title": "开发流程",
                "items": []
            }
        ]
        
        executor = RenderExecutor(slides_data, "这是原文")
        
        cmd = RenderCommand(
            source_text="开发流程",
            render_type="flowchart",
            render_params={
                "title": "开发流程",
                "flowchart_data": {
                    "nodes": [
                        {"id": "1", "label": "需求分析", "type": "start"},
                        {"id": "2", "label": "编码", "type": "process"},
                        {"id": "3", "label": "测试", "type": "end"}
                    ],
                    "edges": [
                        {"from": "1", "to": "2"},
                        {"from": "2", "to": "3"}
                    ]
                }
            },
            slide_index=0
        )
        
        result = executor.execute(cmd)
        assert result.success, f"执行应成功: {result.message}"


@pytest.mark.slow
class TestRenderCommandQuality:
    """渲染指令质量测试 - 验证输出质量"""
    
    @pytest.fixture(scope="class")
    def quality_test_output(self):
        """Fixture: 调用 LLM 生成多种渲染指令"""
        available, msg = _check_llm_available()
        if not available:
            pytest.skip(f"LLM 服务不可用: {msg}")
        
        prompt = f"""你是一个PPT编辑助手。请根据以下内容，生成合适的渲染指令。

原始文本：
{SAMPLE_ORIGINAL_TEXT}

要求：
1. 将"财务数据"部分转换为图表
2. 将"产品线"部分转换为表格

输出格式：
```json
{{
  "render_commands": [
    {{
      "source_text": "原文片段",
      "render_type": "chart 或 table",
      "render_params": {{...}}
    }}
  ]
}}
```

请只返回JSON，不要其他文字。"""
        
        try:
            full_text, chunk_count = _collect_pipeline_output(
                prompt=prompt,
                action_type="chat",
                context_source="ppt_editor",
            )
        except RuntimeError as e:
            pytest.fail(f"LLM 调用失败: {e}")
        
        return {"text": full_text, "chunks": chunk_count}
    
    def test_multiple_render_commands(self, quality_test_output):
        """验证：应生成多条渲染指令"""
        commands = _parse_render_commands(quality_test_output["text"])
        assert len(commands) >= 2, f"应至少生成2条渲染指令，实际: {len(commands)}"
    
    def test_mixed_render_types(self, quality_test_output):
        """验证：应包含多种渲染类型"""
        commands = _parse_render_commands(quality_test_output["text"])
        render_types = set(cmd.get("render_type") for cmd in commands)
        assert len(render_types) >= 2, f"应至少有2种渲染类型，实际: {render_types}"
    
    def test_source_text_not_empty(self, quality_test_output):
        """验证：source_text 不应为空"""
        commands = _parse_render_commands(quality_test_output["text"])
        for i, cmd in enumerate(commands):
            assert cmd.get("source_text"), f"渲染指令 {i} 的 source_text 不应为空"
    
    def test_render_params_not_empty(self, quality_test_output):
        """验证：render_params 不应为空"""
        commands = _parse_render_commands(quality_test_output["text"])
        for i, cmd in enumerate(commands):
            assert cmd.get("render_params"), f"渲染指令 {i} 的 render_params 不应为空"


# ── 快速测试（不调用 LLM）──

class TestRenderCommandParserQuick:
    """渲染指令解析器快速测试（不调用 LLM）"""
    
    def test_parse_new_format(self):
        """测试：解析新格式（render_commands）"""
        response = '''
```json
{
  "render_commands": [
    {
      "source_text": "2024年营收8.5亿元",
      "render_type": "chart",
      "render_params": {
        "chart_type": "bar",
        "title": "营收趋势"
      }
    }
  ]
}
```
'''
        commands = _parse_render_commands(response)
        assert len(commands) == 1
        assert commands[0]["render_type"] == "chart"
    
    def test_parse_old_format_returns_empty(self):
        """测试：旧格式返回空（由 CoCreationWidget 处理）"""
        response = '''
```json
{
  "action": "update",
  "slide_index": 0,
  "field": "title",
  "value": "新标题"
}
```
'''
        commands = _parse_render_commands(response)
        assert len(commands) == 0
    
    def test_parse_mixed_format(self):
        """测试：混合格式"""
        response = '''
这是说明文字。

```json
{
  "render_commands": [
    {
      "source_text": "数据",
      "render_type": "table",
      "render_params": {"title": "表格"}
    }
  ]
}
```

更多说明。
'''
        commands = _parse_render_commands(response)
        assert len(commands) == 1
        assert commands[0]["render_type"] == "table"
    
    def test_parse_no_json_returns_empty(self):
        """测试：无 JSON 返回空"""
        response = "这是一段纯文本，没有 JSON 数据。"
        commands = _parse_render_commands(response)
        assert len(commands) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
