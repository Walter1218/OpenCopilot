"""V5Plus Design Tokens — 扩展 v5 tokens，新增 PPT 共创 E2E 专属常量"""
from gui.v5 import tokens as T

# =============================================================================
# 窗口尺寸
# =============================================================================

WINDOW_COCREATION = (1200, 800)
WINDOW_COCREATION_MIN = (1000, 650)

# =============================================================================
# Stage 2 — 策略卡片配色
# =============================================================================

STRATEGY_PYRAMID_COLOR = "#4da6ff"   # 金字塔式（蓝）
STRATEGY_NARRATIVE_COLOR = "#a78bfa"  # 叙事式（紫）
STRATEGY_COMPARISON_COLOR = "#34d399" # 对比式（绿）

STRATEGY_CARDS = [
    {
        "key": "pyramid",
        "icon": "▲",
        "label": "金字塔式",
        "subtitle": "结论先行",
        "color": STRATEGY_PYRAMID_COLOR,
        "template": "核心结论 → 支撑论据 → 数据证据 → 下一步",
        "scenario": "汇报、总结",
    },
    {
        "key": "narrative",
        "icon": "◆",
        "label": "叙事式",
        "subtitle": "问题驱动",
        "color": STRATEGY_NARRATIVE_COLOR,
        "template": "现状痛点 → 解决思路 → 技术实现 → 预期收益",
        "scenario": "方案介绍",
    },
    {
        "key": "comparison",
        "icon": "◇",
        "label": "对比式",
        "subtitle": "方案论证",
        "color": STRATEGY_COMPARISON_COLOR,
        "template": "背景需求 → 方案对比 → 推荐详解 → 实施风险",
        "scenario": "决策论证",
    },
]

# 演讲时长选项
DURATION_OPTIONS = [
    ("5", "5 分钟"),
    ("10", "10 分钟"),
    ("15", "15 分钟"),
    ("30", "30 分钟"),
]

# =============================================================================
# Stage 3 — 面板布局
# =============================================================================

SPLIT_CENTER = 60  # 中间 PPT 编辑区宽度百分比
SPLIT_RIGHT = 40   # 右侧原文面板宽度百分比

# 版式标签
LAYOUT_TAGS = [
    ("center", "center", "居中标题"),
    ("text", "text_only", "纯文字"),
    ("3-col", "three_columns", "三栏"),
    ("chart", "chart", "图表"),
    ("flow", "flowchart", "流程"),
    ("table", "table", "表格"),
    ("image", "image_right", "图文"),
]

# 缩略图尺寸
THUMB_WIDTH = 72
THUMB_HEIGHT = 40

# =============================================================================
# 段落类型热力图配色
# =============================================================================

PARAGRAPH_TYPE_COLORS = {
    "background": "#6b7280",   # 背景（灰）
    "architecture": "#3b82f6", # 架构（蓝）
    "data": "#f59e0b",         # 数据（黄）
    "comparison": "#8b5cf6",   # 对比（紫）
    "process": "#10b981",      # 流程（绿）
    "summary": "#ef4444",      # 总结（红）
    "intro": "#6366f1",        # 引言（靛蓝）
    "other": "#78716c",        # 其他（石色）
}

# =============================================================================
# 映射标签颜色（对应幻灯片序号）
# =============================================================================

SLIDE_TAG_COLORS = [
    "#4da6ff", "#a78bfa", "#34d399", "#f59e0b",
    "#ef4444", "#ec4899", "#06b6d4", "#84cc16",
]

# =============================================================================
# 复用 v5 基础 token（便捷引用）
# =============================================================================

BG_PRIMARY = T.BG_PRIMARY
BG_ELEVATED = T.BG_ELEVATED
BG_INPUT = T.BG_INPUT
BG_HOVER = T.BG_HOVER
BG_SELECTED = T.BG_SELECTED
TEXT_PRIMARY = T.TEXT_PRIMARY
TEXT_SECONDARY = T.TEXT_SECONDARY
TEXT_TERTIARY = T.TEXT_TERTIARY
TEXT_ACCENT = T.TEXT_ACCENT
ACCENT_CONTROL = T.ACCENT_CONTROL
ACCENT_HOVER = T.ACCENT_HOVER
STATUS_ONLINE = T.STATUS_ONLINE
STATUS_WARNING = T.STATUS_WARNING
STATUS_OFFLINE = T.STATUS_OFFLINE
STROKE_BORDER = T.STROKE_BORDER
STROKE_FOCUS = T.STROKE_FOCUS
STROKE_SUBTLE = T.STROKE_SUBTLE
BTN_PRIMARY_BG = T.BTN_PRIMARY_BG
BTN_PRIMARY_HOVER = T.BTN_PRIMARY_HOVER
BTN_PRIMARY_TEXT = T.BTN_PRIMARY_TEXT
BTN_ACTION_BG = T.BTN_ACTION_BG
BTN_ACTION_HOVER = T.BTN_ACTION_HOVER
FONT_TITLE = T.FONT_TITLE
FONT_HEADING = T.FONT_HEADING
FONT_BODY = T.FONT_BODY
FONT_CAPTION = T.FONT_CAPTION
FONT_TINY = T.FONT_TINY
FRAME_MARGIN = T.FRAME_MARGIN
FRAME_RADIUS = T.FRAME_RADIUS
SHADOW_BLUR = T.SHADOW_BLUR
BTN_LARGE_HEIGHT = T.BTN_LARGE_HEIGHT
BTN_MEDIUM_HEIGHT = T.BTN_MEDIUM_HEIGHT
BTN_MEDIUM_PADDING = T.BTN_MEDIUM_PADDING
