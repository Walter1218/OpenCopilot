"""
共创模式各功能模块 —— 质量评测

覆盖五大内容类型的 16 个操作，每题满分 10 分：
  结构有效性(1) + 目标准确性(1) + 内容相关性(3) + 内容质量(3) + 格式丰富度(2)

测试内容类型：
  text:    优化标题、添加要点、换版式、精简内容、转图表
  table:   格式化表格、添加行、排序数据
  chart:   更换图表类型、添加图例
  flowchart: 添加步骤、美化样式
  image:   更换图片、添加说明
  global:  转换为表格、转换为流程图
"""
import sys, os, json, re, uuid, time
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import Counter, defaultdict

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ========== 测试样本数据 ==========

# 各内容类型的样本幻灯片
TEXT_SLIDES = [
    {"type": "title", "layout": "center", "title": "Q3 产品路线图", "subtitle": "产品团队"},
    {"type": "content", "layout": "text_only", "title": "核心功能",
     "items": [
         {"level": 0, "text": "用户可以通过语音指令控制智能家居设备", "content_type": "text"},
         {"level": 0, "text": "AI 助手能够理解上下文连续对话", "content_type": "text"},
         {"level": 0, "text": "支持多设备无缝协同工作", "content_type": "text"},
         {"level": 0, "text": "内置安全隐私保护机制", "content_type": "text"},
         {"level": 0, "text": "提供实时数据分析和可视化看板", "content_type": "text"},
     ]},
    {"type": "content", "layout": "three_columns", "title": "竞品对比",
     "items": [
         {"level": 0, "text": "我们：AI 原生架构，零学习成本", "content_type": "text"},
         {"level": 0, "text": "竞品A：功能丰富但学习曲线陡峭", "content_type": "text"},
         {"level": 0, "text": "竞品B：价格优势明显但功能有限", "content_type": "text"},
     ]},
    {"type": "ending", "layout": "center", "title": "谢谢", "subtitle": "Q & A"},
]

TABLE_SLIDES = [
    {"type": "title", "layout": "center", "title": "Q2 销售业绩汇报", "subtitle": "销售部"},
    {"type": "content", "layout": "text_only", "title": "各区域销售额",
     "items": [
         {"level": 0, "text": "华东", "content_type": "table",
          "table_data": {"title": "区域销售明细", "columns": ["区域", "Q1", "Q2", "增长率"],
                         "rows": [["华东", "1200万", "1350万", "12.5%"],
                                  ["华南", "980万", "1050万", "7.1%"],
                                  ["华北", "870万", "920万", "5.7%"],
                                  ["西部", "450万", "510万", "13.3%"]]}},
     ]},
    {"type": "ending", "layout": "center", "title": "谢谢", "subtitle": "Q & A"},
]

CHART_SLIDES = [
    {"type": "title", "layout": "center", "title": "用户增长分析", "subtitle": "数据分析"},
    {"type": "content", "layout": "image_right", "title": "月度活跃用户趋势",
     "items": [
         {"level": 0, "text": "MAU 从 50 万增长至 120 万", "content_type": "chart", "chart_type": "bar",
          "chart_data": {"title": "月度活跃用户", "labels": ["1月","2月","3月","4月","5月","6月"],
                         "datasets": [{"label": "MAU", "data": [50,62,78,95,108,120], "color": "#4da6ff"}]}},
     ]},
    {"type": "ending", "layout": "center", "title": "谢谢", "subtitle": "Q & A"},
]

FLOWCHART_SLIDES = [
    {"type": "title", "layout": "center", "title": "用户注册流程", "subtitle": "产品设计"},
    {"type": "content", "layout": "text_only", "title": "注册步骤",
     "items": [
         {"level": 0, "text": "步骤1: 填写手机号", "content_type": "flowchart",
          "flowchart_data": {"title": "用户注册流程", "nodes": [
              {"id": "n1", "text": "填写手机号", "shape": "start"},
              {"id": "n2", "text": "获取验证码", "shape": "process"},
              {"id": "n3", "text": "验证通过?", "shape": "decision"},
              {"id": "n4", "text": "设置密码", "shape": "process"},
              {"id": "n5", "text": "注册完成", "shape": "end"},
          ], "edges": [{"from":"n1","to":"n2"},{"from":"n2","to":"n3"},{"from":"n3","to":"n4","label":"是"},{"from":"n3","to":"n2","label":"否"},{"from":"n4","to":"n5"}]}},
     ]},
    {"type": "ending", "layout": "center", "title": "谢谢", "subtitle": "Q & A"},
]

# ===== 行业样本数据 =====

# 金融 - 投资组合分析
FINANCE_SLIDES = [
    {"type": "title", "layout": "center", "title": "2026 H1 投资组合分析", "subtitle": "资产管理部"},
    {"type": "content", "layout": "text_only", "title": "资产配置概况",
     "items": [
         {"level": 0, "text": "固定收益类：占比 45%，年化收益 4.2%", "content_type": "text"},
         {"level": 0, "text": "权益类：占比 35%，年化收益 12.8%", "content_type": "text"},
         {"level": 0, "text": "另类投资：占比 15%，年化收益 8.5%", "content_type": "text"},
         {"level": 0, "text": "现金管理：占比 5%，年化收益 2.1%", "content_type": "text"},
     ]},
    {"type": "content", "layout": "text_only", "title": "风险指标",
     "items": [
         {"level": 0, "text": "组合夏普比率 1.82，最大回撤 5.3%", "content_type": "table",
          "table_data": {"title": "风险评估", "columns": ["指标", "数值", "基准"],
                         "rows": [["夏普比率", "1.82", "1.50"],
                                  ["最大回撤", "5.3%", "7.0%"],
                                  ["年化波动率", "8.7%", "10.5%"],
                                  ["信息比率", "1.15", "1.00"]]}},
     ]},
    {"type": "ending", "layout": "center", "title": "谢谢", "subtitle": "Q & A"},
]

# 医疗 - 药品临床试验
HEALTHCARE_SLIDES = [
    {"type": "title", "layout": "center", "title": "新药 XR-301 临床试验报告", "subtitle": "临床研究部"},
    {"type": "content", "layout": "text_only", "title": "试验概况",
     "items": [
         {"level": 0, "text": "III 期临床试验，入组 1200 名受试者", "content_type": "text"},
         {"level": 0, "text": "随机双盲安慰剂对照设计", "content_type": "text"},
         {"level": 0, "text": "主要终点：24 周无进展生存率", "content_type": "text"},
     ]},
    {"type": "content", "layout": "image_right", "title": "疗效数据",
     "items": [
         {"level": 0, "text": "总体响应率 78.5% vs 安慰剂 42.1%", "content_type": "chart", "chart_type": "bar",
          "chart_data": {"title": "疗效对比", "labels": ["整体响应率","无进展生存率","症状缓解率"],
                         "datasets": [{"label": "XR-301", "data": [78.5,72.3,85.1], "color": "#4da6ff"},
                                     {"label": "安慰剂", "data": [42.1,38.5,35.7], "color": "#cccccc"}]}},
     ]},
    {"type": "ending", "layout": "center", "title": "谢谢", "subtitle": "Q & A"},
]

# 教育 - 在线课程设计
EDUCATION_SLIDES = [
    {"type": "title", "layout": "center", "title": "Python 数据分析实战课程", "subtitle": "教学研发中心"},
    {"type": "content", "layout": "text_only", "title": "课程大纲",
     "items": [
         {"level": 0, "text": "模块一：Python 基础与数据处理（4周）", "content_type": "text"},
         {"level": 0, "text": "模块二：NumPy 与 Pandas 实战（3周）", "content_type": "text"},
         {"level": 0, "text": "模块三：数据可视化与 Matplotlib（2周）", "content_type": "text"},
         {"level": 0, "text": "模块四：机器学习入门（3周）", "content_type": "text"},
         {"level": 0, "text": "模块五：实战项目与答辩（4周）", "content_type": "text"},
     ]},
    {"type": "content", "layout": "text_only", "title": "学习路径",
     "items": [
         {"level": 0, "text": "报名 → 基础测试 → 选课 → 学习 → 考试 → 认证", "content_type": "flowchart",
          "flowchart_data": {"title": "学习路径", "nodes": [
              {"id": "e1", "text": "在线报名", "shape": "start"},
              {"id": "e2", "text": "基础测试", "shape": "process"},
              {"id": "e3", "text": "分班学习", "shape": "process"},
              {"id": "e4", "text": "期末考核", "shape": "decision"},
              {"id": "e5", "text": "颁发证书", "shape": "end"},
          ], "edges": [{"from":"e1","to":"e2"},{"from":"e2","to":"e3"},{"from":"e3","to":"e4"},{"from":"e4","to":"e5"}]}},
     ]},
    {"type": "ending", "layout": "center", "title": "谢谢", "subtitle": "Q & A"},
]

# 制造 - 质量管控
MANUFACTURING_SLIDES = [
    {"type": "title", "layout": "center", "title": "Q3 质量管理体系评审", "subtitle": "质控中心"},
    {"type": "content", "layout": "text_only", "title": "关键指标",
     "items": [
         {"level": 0, "text": "产品合格率：99.2%（目标 99.5%）", "content_type": "table",
          "table_data": {"title": "质量指标看板", "columns": ["指标", "Q3 实际", "目标值", "状态"],
                         "rows": [["产品合格率", "99.2%", "99.5%", "未达标"],
                                  ["客户投诉率", "0.3%", "0.5%", "达标"],
                                  ["产线稼动率", "94.8%", "93.0%", "超额"],
                                  ["一次通过率", "96.1%", "95.0%", "超额"]]}},
     ]},
    {"type": "content", "layout": "text_only", "title": "检验流程",
     "items": [
         {"level": 0, "text": "来料检验 → 制程检验 → 成品检验 → 出货检验", "content_type": "flowchart",
          "flowchart_data": {"title": "质量检验流程", "nodes": [
              {"id": "q1", "text": "来料检验IQC", "shape": "start"},
              {"id": "q2", "text": "制程巡检IPQC", "shape": "process"},
              {"id": "q3", "text": "成品检验FQC", "shape": "process"},
              {"id": "q4", "text": "出货检验OQC", "shape": "process"},
              {"id": "q5", "text": "合格放行", "shape": "end"},
          ], "edges": [{"from":"q1","to":"q2"},{"from":"q2","to":"q3"},{"from":"q3","to":"q4"},{"from":"q4","to":"q5"}]}},
     ]},
    {"type": "ending", "layout": "center", "title": "谢谢", "subtitle": "Q & A"},
]

# 零售 - 季度销售分析
RETAIL_SLIDES = [
    {"type": "title", "layout": "center", "title": "Q3 门店销售分析", "subtitle": "运营管理部"},
    {"type": "content", "layout": "text_only", "title": "品类销售排行",
     "items": [
         {"level": 0, "text": "各品类销售数据", "content_type": "table",
          "table_data": {"title": "品类销售 Top5", "columns": ["品类", "销售额(万)", "同比增长", "占比"],
                         "rows": [["生鲜食品", "3280", "+15.2%", "28.5%"],
                                  ["家电数码", "2650", "+8.7%", "23.0%"],
                                  ["服装鞋帽", "1980", "+5.1%", "17.2%"],
                                  ["美妆个护", "1520", "+22.3%", "13.2%"],
                                  ["家居用品", "1080", "-2.1%", "9.4%"]]}},
     ]},
    {"type": "content", "layout": "image_right", "title": "月度趋势",
     "items": [
         {"level": 0, "text": "月度销售额走势", "content_type": "chart", "chart_type": "bar",
          "chart_data": {"title": "月度销售额", "labels": ["7月","8月","9月"],
                         "datasets": [{"label": "线上", "data": [4200,3850,5100], "color": "#4da6ff"},
                                     {"label": "线下", "data": [6800,7150,6900], "color": "#ff6b6b"}]}},
     ]},
    {"type": "ending", "layout": "center", "title": "谢谢", "subtitle": "Q & A"},
]

# 科技 - SaaS 产品发布
TECH_SLIDES = [
    {"type": "title", "layout": "center", "title": "DevFlow 2.0 产品发布会", "subtitle": "研发效能平台"},
    {"type": "content", "layout": "text_only", "title": "核心升级",
     "items": [
         {"level": 0, "text": "AI 代码审查：自动检测 200+ 种代码缺陷模式", "content_type": "text"},
         {"level": 0, "text": "智能 CI/CD：构建时间缩短 60%，自动故障回滚", "content_type": "text"},
         {"level": 0, "text": "全链路可观测：集成日志、指标、链路追踪", "content_type": "text"},
     ]},
    {"type": "content", "layout": "three_columns", "title": "竞品对比",
     "items": [
         {"level": 0, "text": "DevFlow 2.0：原生 AI 引擎，零配置", "content_type": "text"},
         {"level": 0, "text": "GitLab Premium：功能全但学习成本高", "content_type": "text"},
         {"level": 0, "text": "Jenkins X：开源灵活但运维复杂", "content_type": "text"},
     ]},
    {"type": "ending", "layout": "center", "title": "谢谢", "subtitle": "Q & A"},
]

IMAGE_SLIDES = [
    {"type": "title", "layout": "center", "title": "新产品发布", "subtitle": "市场部"},
    {"type": "content", "layout": "image_right", "title": "旗舰产品 X1",
     "items": [
         {"level": 0, "text": "超薄机身仅 5.8mm", "content_type": "text"},
         {"level": 0, "text": "搭载自研 M3 芯片", "content_type": "text"},
         {"level": 0, "text": "产品展示图", "content_type": "image",
          "image_data": {"url": "", "description": "产品正面45度产品图"}},
     ]},
    {"type": "ending", "layout": "center", "title": "谢谢", "subtitle": "Q & A"},
]

VALID_ACTIONS = {"update", "add_item", "remove_item", "update_item", "add_slide", "remove_slide", "full_replace"}
VALID_LAYOUTS = {"center", "text_only", "image_right", "image_left", "three_columns", "two_columns"}
VALID_CONTENT_TYPES = {"text", "image", "flowchart", "icon", "table", "chart"}


# ========== 评分函数 ==========

def score_structural_validity(actions: List[Dict]) -> float:
    """结构有效性评分：JSON 可解析 + action 类型合法"""
    if not actions:
        return 0.0
    score = 0.0
    for a in actions:
        if isinstance(a, dict) and "action" in a:
            if a["action"] in VALID_ACTIONS:
                score += 1.0
            elif a["action"] == "full_replace":
                if "slides" in a and isinstance(a["slides"], list):
                    score += 0.8  # partial credit
            else:
                score += 0.3  # unknown action, some credit for JSON
        else:
            score += 0.2  # JSON but no action
    return min(1.0, score / max(1, len(actions)))


def score_target_accuracy(actions: List[Dict], slides: List[Dict]) -> float:
    """目标准确性评分：slide_index/item_index 在有效范围内"""
    if not actions:
        return 0.0
    checks = 0
    passed = 0
    for a in actions:
        action = a.get("action", "")
        if action in ("update", "update_item", "add_item", "remove_item"):
            si = a.get("slide_index", -1)
            if si != -1:
                checks += 1
                if 0 <= si < len(slides):
                    passed += 1
        if action in ("update_item", "remove_item"):
            si = a.get("slide_index", -1)
            ii = a.get("item_index", -1)
            if si != -1 and ii != -1 and 0 <= si < len(slides):
                items = slides[si].get("items", [])
                checks += 1
                if 0 <= ii < len(items):
                    passed += 1
        if action == "add_slide":
            idx = a.get("index", -1)
            if idx != -1:
                checks += 1
                if 0 <= idx <= len(slides):
                    passed += 1
        if action == "remove_slide":
            idx = a.get("index", -1)
            if idx != -1:
                checks += 1
                if 0 <= idx < len(slides):
                    passed += 1
    if checks == 0:
        return 0.5  # no slide reference needed (e.g., full_replace)
    return passed / checks


def score_content_relevance(actions: List[Dict], instruction: str) -> float:
    """内容相关性评分：响应内容与指令的语义匹配度"""
    if not actions:
        return 0.0
    total = 0.0
    keywords = set(instruction.lower().replace("的", "").replace("把", "").replace("在", "").split())
    keywords = {k for k in keywords if len(k) >= 2}

    for a in actions:
        action = a.get("action", "")
        score = 0.0

        # 提取生成的内容文本
        texts = []
        if action == "update":
            val = a.get("value", "")
            texts.append(str(val) if not isinstance(val, str) else val)
        elif action == "add_item":
            item = a.get("item", {})
            t = item.get("text", item.get("title", ""))
            texts.append(str(t) if not isinstance(t, str) else t)
            if "table_data" in item:
                td = item["table_data"]
                texts.extend(str(c) for c in td.get("columns", []))
                for row in td.get("rows", []):
                    texts.extend(str(c) for c in row)
        elif action == "update_item":
            val = a.get("value", "")
            texts.append(str(val) if not isinstance(val, str) else val)
        elif action == "full_replace":
            for s in a.get("slides", []):
                texts.append(str(s.get("title", "")))
                for item in s.get("items", []):
                    t = item.get("text", "")
                    texts.append(str(t) if not isinstance(t, str) else t)

        combined = " ".join(str(t) for t in texts).lower()

        # 检查关键词命中
        hits = sum(1 for kw in keywords if kw in combined)
        if keywords:
            hit_rate = hits / min(len(keywords), 5)
            score += hit_rate * 1.5

        # 检查内容是否过于通用（没有具体信息）
        if len(combined) >= 10 and combined not in ("新要点", "新标题", ""):
            score += 0.5

        # 检查是否包含特定数值/专有名词（具体性）
        if re.search(r'\d+', combined):
            score += 0.5

        total += min(1.5, score)

    return min(3.0, total)


def score_content_quality(actions: List[Dict]) -> float:
    """内容质量评分：生成内容的深度、具体性和语言质量"""
    if not actions:
        return 0.0
    total = 0.0
    for a in actions:
        action = a.get("action", "")
        score = 0.0

        texts = []
        if action == "update":
            val = a.get("value", "")
            texts.append(str(val) if not isinstance(val, str) else val)
        elif action == "add_item":
            item = a.get("item", {})
            t = item.get("text", item.get("title", ""))
            texts.append(str(t) if not isinstance(t, str) else t)
            # 富格式加分
            if item.get("content_type") in ("table", "chart", "flowchart"):
                score += 0.5
            if "table_data" in item:
                td = item["table_data"]
                if len(td.get("columns", [])) >= 2 and len(td.get("rows", [])) >= 2:
                    score += 0.5
            if "chart_data" in item:
                cd = item["chart_data"]
                if len(cd.get("labels", [])) >= 2 and len(cd.get("datasets", [])) >= 1:
                    score += 0.5
            if "flowchart_data" in item:
                fd = item["flowchart_data"]
                if len(fd.get("nodes", [])) >= 2:
                    score += 0.5
        elif action == "update_item":
            val = a.get("value", "")
            texts.append(str(val) if not isinstance(val, str) else val)
        elif action in ("remove_item", "remove_slide"):
            score = 1.0  # 删除操作，只要索引正确即可
        elif action == "add_slide":
            slide = a.get("slide", {})
            t = slide.get("title", "")
            texts.append(str(t) if not isinstance(t, str) else t)
            if slide.get("items"):
                score += 0.3

        # 文本长度与信息量
        for t in texts:
            t = str(t)
            if len(t) >= 20:
                score += 1.0
            elif len(t) >= 10:
                score += 0.7
            elif len(t) >= 3:
                score += 0.3
            # 避免套话
            generic = {"新要点", "新标题", "测试", "内容", "示例", "NA", "-"}
            if t.strip() in generic:
                score -= 0.5

        # 多样性加分：是否使用了具体命名
        if any(c.isupper() for c in " ".join(texts)):
            score += 0.2

        total += min(1.5, score)

    return min(3.0, total)


def score_format_richness(actions: List[Dict]) -> float:
    """格式丰富度评分：是否合理使用 table/chart/flowchart 等富格式"""
    if not actions:
        return 0.0
    total = 0.0
    for a in actions:
        action = a.get("action", "")
        rich_types = 0
        if action == "update":
            # layout 改变也算格式改进
            if a.get("field") == "layout" and a.get("value") in ("image_right", "three_columns", "two_columns"):
                rich_types += 1
        if action == "add_item":
            item = a.get("item", {})
            ct = item.get("content_type", "text")
            if ct in ("table", "chart", "flowchart"):
                rich_types += 1
            if "table_data" in item or "chart_data" in item or "flowchart_data" in item:
                rich_types += 1
        if action == "full_replace":
            for s in a.get("slides", []):
                for item in s.get("items", []):
                    ct = item.get("content_type", "text")
                    if ct in ("table", "chart", "flowchart"):
                        rich_types += 1

        total += min(2.0, rich_types * 0.8)
    return min(2.0, total)


def compute_score(actions: List[Dict], slides: List[Dict], instruction: str) -> Dict:
    """综合评分"""
    s1 = score_structural_validity(actions)
    s2 = score_target_accuracy(actions, slides)
    s3 = score_content_relevance(actions, instruction)
    s4 = score_content_quality(actions)
    s5 = score_format_richness(actions)
    total = s1 + s2 + s3 + s4 + s5
    return {
        "total": round(total, 1),
        "structural": round(s1, 2),
        "target_accuracy": round(s2, 2),
        "relevance": round(s3, 1),
        "quality": round(s4, 1),
        "format_richness": round(s5, 1),
        "grade": _grade(total),
    }


def _grade(total: float) -> str:
    if total >= 8.5: return "A+ 优秀"
    if total >= 7.0: return "A  良好"
    if total >= 5.5: return "B  一般"
    if total >= 4.0: return "C  需改进"
    return "D  差"


# ========== 测试执行 ==========

def call_ai(slides: List[Dict], instruction: str) -> List[Dict]:
    """调用 AI 共创接口，返回解析后的动作列表"""
    from opencopilot.agent.caller import call_agent_pipeline_sync

    context = json.dumps({
        "current_slides": slides,
        "instruction": instruction,
    }, ensure_ascii=False)

    full = ""
    for chunk in call_agent_pipeline_sync(
        text=context, action_type="ppt",
        context_source="ppt_editor", is_new_task=True,
        session_id=f"q_{uuid.uuid4().hex[:8]}"
    ):
        full += chunk

    # 解析 JSON
    cleaned = re.sub(r'<[^>]*>', '', full)
    actions = []

    # 1. Try JSON array
    arr_match = re.search(r'\[.*\]', cleaned, re.DOTALL)
    if arr_match:
        try:
            parsed = json.loads(arr_match.group(0))
            if isinstance(parsed, list):
                actions.extend(p for p in parsed if isinstance(p, dict) and "action" in p)
        except json.JSONDecodeError:
            pass

    # 2. Try line-by-line JSON  
    if not actions:
        for line in cleaned.split('\n'):
            line = line.strip()
            if line.startswith('{') and line.endswith('}'):
                try:
                    obj = json.loads(line)
                    if "action" in obj:
                        actions.append(obj)
                except json.JSONDecodeError:
                    pass

    # 3. Try extracting individual JSON objects with balanced braces
    if not actions:
        i = 0
        while i < len(cleaned):
            start = cleaned.find('{', i)
            if start < 0:
                break
            depth = 0
            in_string = False
            escape = False
            end = start
            for j in range(start, len(cleaned)):
                c = cleaned[j]
                if escape:
                    escape = False
                    continue
                if c == '\\':
                    escape = True
                    continue
                if c == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        end = j + 1
                        break
            if end > start:
                try:
                    obj = json.loads(cleaned[start:end])
                    if isinstance(obj, dict):
                        if "action" in obj:
                            actions.append(obj)
                        elif "slides" in obj:
                            actions.append({"action": "full_replace", "slides": obj["slides"]})
                except json.JSONDecodeError:
                    pass
            i = end if end > start else start + 1

    return actions


def run_test(label: str, slides: List[Dict], instruction: str) -> Dict:
    """运行单个测试并评分"""
    print(f"\n  🧪 {label}...")
    print(f"     指令: {instruction[:60]}...")

    try:
        t0 = time.time()
        actions = call_ai(slides, instruction)
        elapsed = round(time.time() - t0, 1)

        if not actions:
            print(f"     ⚠️  未解析出动作 ({elapsed}s)")
            return {
                "label": label, "actions": 0, "time_s": elapsed,
                "score": {"total": 0, "grade": "D  差 (无动作)"},
                "action_types": [],
            }

        score = compute_score(actions, slides, instruction)
        action_types = [a.get("action", "?") for a in actions]
        print(f"     {'✅' if score['total'] >= 4 else '❌'} "
              f"{score['grade']} | {score['total']}/10 | "
              f"{elapsed}s | 动作: {action_types}")

        return {
            "label": label, "actions": len(actions), "time_s": elapsed,
            "score": score, "action_types": action_types,
        }
    except Exception as e:
        print(f"     ❌ 异常: {e}")
        return {
            "label": label, "actions": 0, "time_s": 0,
            "score": {"total": 0, "grade": f"异常: {str(e)[:30]}"},
            "action_types": [],
        }


# ========== 测试用例定义 ==========

# (label, content_type, slides, instruction)
TEST_CASES = [
    # ---- TEXT 类操作 (5) ----
    ("T1 优化标题", "text", TEXT_SLIDES,
     "把第二页的标题优化得更有吸引力，突出 AI 智能感"),
    ("T2 添加要点", "text", TEXT_SLIDES,
     "在核心功能页添加一个要点：多模态交互能力"),
    ("T3 换版式", "text", TEXT_SLIDES,
     "把核心功能页的版式改为 image_right，适合图文并茂展示"),
    ("T4 精简内容", "text", TEXT_SLIDES,
     "精简竞品对比页的内容，保留最核心的差异点"),
    ("T5 转图表", "text", TEXT_SLIDES,
     "分析竞品对比页的内容，把适合的部分转换为图表展示"),

    # ---- TABLE 类操作 (3) ----
    ("T6 格式化表格", "table", TABLE_SLIDES,
     "优化区域销售明细表格的格式，让数据更清晰易读"),
    ("T7 添加行", "table", TABLE_SLIDES,
     "为区域销售表格添加一行「华中」地区的数据"),
    ("T8 排序数据", "table", TABLE_SLIDES,
     "对区域销售表格按增长率从高到低排序"),

    # ---- CHART 类操作 (2) ----
    ("T9 更换图表类型", "chart", CHART_SLIDES,
     "月度活跃用户这个柱状图改成折线图，更能体现增长趋势"),
    ("T10 添加图例", "chart", CHART_SLIDES,
     "为用户增长图表添加更详细的图例说明"),

    # ---- FLOWCHART 类操作 (2) ----
    ("T11 添加步骤", "flowchart", FLOWCHART_SLIDES,
     "在注册流程的验证码之后，增加「人机验证」步骤"),
    ("T12 美化样式", "flowchart", FLOWCHART_SLIDES,
     "美化注册流程图的样式，让它更专业"),

    # ---- IMAGE 类操作 (2) ----
    ("T13 更换图片", "image", IMAGE_SLIDES,
     "产品展示图换成侧面轮廓图，突出超薄特性"),
    ("T14 添加说明", "image", IMAGE_SLIDES,
     "为产品展示图添加详细的技术参数说明文字"),

    # ---- 全局转换 (2) ----
    ("T15 转换为表格", "global", TEXT_SLIDES,
     "把竞品对比页的三列内容转换为结构化表格"),
    ("T16 转换为流程图", "global", FLOWCHART_SLIDES,
     "确认注册流程的步骤，如有遗漏请补充完整"),

    # ========== 行业扩展用例 (10) ==========
    # ---- 金融 (2) ----
    ("I1 金融·转饼图", "finance", FINANCE_SLIDES,
     "把资产配置概况页的数据转换为饼图，直观展示各资产类别占比"),
    ("I2 金融·排序数据", "finance", FINANCE_SLIDES,
     "把风险评估表格按数值列从优到劣排序"),

    # ---- 医疗 (2) ----
    ("I3 医疗·优化标题", "healthcare", HEALTHCARE_SLIDES,
     "把试验概况页的标题优化得更专业、更有科学感"),
    ("I4 医疗·换图表类型", "healthcare", HEALTHCARE_SLIDES,
     "把疗效数据的柱状图改为折线图，更适合展示治疗效果随时间的变化"),

    # ---- 教育 (2) ----
    ("I5 教育·转表格", "education", EDUCATION_SLIDES,
     "把课程大纲转换为结构化表格，便于对比各模块信息"),
    ("I6 教育·添加步骤", "education", EDUCATION_SLIDES,
     "在学习路径中添加「中期测评」和「结业项目」两个步骤"),

    # ---- 制造 (2) ----
    ("I7 制造·排序数据", "manufacturing", MANUFACTURING_SLIDES,
     "把质量指标看板表格按达标状态排序，未达标的排前面"),
    ("I8 制造·添加步骤", "manufacturing", MANUFACTURING_SLIDES,
     "在质量检验流程的成品检验和出货检验之间增加「第三方抽检」步骤"),

    # ---- 零售 (1) ----
    ("I9 零售·添加行", "retail", RETAIL_SLIDES,
     "在品类销售表格中添加「母婴用品」品类的一行数据"),

    # ---- 科技 (1) ----
    ("I10 科技·转图表", "tech", TECH_SLIDES,
     "把竞品对比的内容转换为表格展示，同时把核心升级的数据转化为图表"),
]


# ========== 主函数 ==========

def main():
    print("=" * 70)
    print("  🏆 共创模式各功能模块 —— 质量评测")
    print("=" * 70)
    print(f"  测试用例: {len(TEST_CASES)} 个")
    print(f"  覆盖类型: text / table / chart / flowchart / image / global")
    print(f"  满分: 10 分 (结构1 + 目标1 + 相关性3 + 质量3 + 格式2)")
    print()

    results = []
    for label, ct, slides, instruction in TEST_CASES:
        print(f"[{ct}] {label}")
        r = run_test(label, slides, instruction)
        r["content_type"] = ct
        results.append(r)

    # ========== 汇总报告 ==========
    print(f"\n\n{'=' * 70}")
    print(f"  📊 综合质量报告")
    print(f"{'=' * 70}")

    # 按内容类型分组汇总
    by_type = defaultdict(list)
    for r in results:
        by_type[r["content_type"]].append(r)

    print(f"\n{'─' * 70}")
    print(f"  📋 按内容类型汇总")
    print(f"{'─' * 70}")
    type_names = {
        "text": "文本页操作", "table": "表格页操作",
        "chart": "图表页操作", "flowchart": "流程图操作",
        "image": "图片页操作", "global": "全局转换",
        "finance": "🏦 金融行业", "healthcare": "🏥 医疗行业",
        "education": "📚 教育行业", "manufacturing": "🏭 制造行业",
        "retail": "🛒 零售行业", "tech": "💻 科技行业",
    }

    for ct in ["text", "table", "chart", "flowchart", "image", "global",
               "finance", "healthcare", "education", "manufacturing", "retail", "tech"]:
        items = by_type[ct]
        if not items:
            continue
        scores = [it["score"]["total"] for it in items]
        avg = sum(scores) / len(scores)
        grades = [it["score"]["grade"] for it in items]
        print(f"\n  🔹 {type_names.get(ct, ct)}  ({len(items)} 项)")
        print(f"     平均分: {avg:.1f}/10")
        for it in items:
            s = it["score"]
            # Use .get for safety
            st = s.get('structural', 0)
            ta = s.get('target_accuracy', 0)
            rl = s.get('relevance', 0)
            ql = s.get('quality', 0)
            fr = s.get('format_richness', 0)
            print(f"     {'✅' if s.get('total', 0) >= 4 else '❌'} [{s.get('grade', '?')}] "
                  f"{it['label']:20s} {s.get('total', 0):.1f}/10 | "
                  f"S{st:.1f} T{ta:.1f} "
                  f"R{rl:.1f} Q{ql:.1f} F{fr:.1f}")

    # 按评分维度汇总
    print(f"\n{'─' * 70}")
    print(f"  📋 按评分维度汇总")
    print(f"{'─' * 70}")

    dims = ["structural", "target_accuracy", "relevance", "quality", "format_richness"]
    dim_names = {"structural": "结构有效性", "target_accuracy": "目标准确性",
                 "relevance": "内容相关性", "quality": "内容质量", "format_richness": "格式丰富度"}
    for dim in dims:
        vals = [r["score"].get(dim, 0.0) for r in results]
        avg = sum(vals) / max(1, len(vals))
        bar = "█" * int(avg * 5) + "░" * (25 - int(avg * 5))
        print(f"  {dim_names[dim]:10s}  avg {avg:.2f}  {bar[:30]}")

    # 总分统计
    all_scores = [r["score"]["total"] for r in results]
    print(f"\n{'─' * 70}")
    print(f"  📋 总体统计")
    print(f"{'─' * 70}")
    print(f"  测试总数:    {len(results)}")
    print(f"  平均分:      {sum(all_scores)/len(all_scores):.1f}/10")
    print(f"  最高分:      {max(all_scores):.1f}/10")
    print(f"  最低分:      {min(all_scores):.1f}/10")
    print(f"  优秀(≥8.5):  {sum(1 for s in all_scores if s >= 8.5)}/{len(results)}")
    print(f"  良好(≥7.0):  {sum(1 for s in all_scores if s >= 7.0)}/{len(results)}")
    print(f"  需改进(<4):  {sum(1 for s in all_scores if s < 4.0)}/{len(results)}")

    # Action 类型分布
    all_actions = []
    for r in results:
        all_actions.extend(r["action_types"])
    print(f"\n  动作类型分布: {dict(Counter(all_actions))}")

    print(f"\n{'=' * 70}")
    print(f"  测试完成")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
