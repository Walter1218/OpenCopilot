"""Design Tokens for v5.0 UI — 替代所有硬编码颜色/字体/尺寸"""

# =============================================================================
# 颜色 Token（Dark Theme）
# =============================================================================

# 背景色
BG_PRIMARY = "rgba(25, 25, 32, 245)"       # 主背景（窗口 frame）
BG_ELEVATED = "rgba(35, 35, 45, 240)"      # 提升背景（Tab 内容区、卡片）
BG_INPUT = "rgba(20, 20, 28, 220)"         # 输入框背景
BG_HOVER = "rgba(55, 55, 70, 240)"         # hover 态
BG_SELECTED = "rgba(77, 166, 255, 40)"     # 选中态

# 文本色
TEXT_PRIMARY = "#e8e8f0"                    # 主文本
TEXT_SECONDARY = "#a0a0b8"                  # 次文本/描述
TEXT_TERTIARY = "#686880"                   # 辅助文本/占位
TEXT_ACCENT = "#4da6ff"                     # 强调文本（链接、标题）

# 主色调
ACCENT_CONTROL = "#4da6ff"                  # 主操作色
ACCENT_HOVER = "#66b8ff"                    # 主操作 hover
ACCENT_PRESSED = "#3d8ed9"                  # 主操作 pressed

# 状态色
STATUS_ONLINE = "#4ade80"                   # 在线/成功
STATUS_OFFLINE = "#f87171"                  # 离线/错误
STATUS_WARNING = "#fbbf24"                  # 警告

# 边框
STROKE_BORDER = "rgba(80, 80, 100, 120)"    # 常规边框
STROKE_FOCUS = "rgba(77, 166, 255, 200)"    # 聚焦边框
STROKE_SUBTLE = "rgba(60, 60, 75, 80)"      # 微弱边框

# 阴影
SHADOW_COLOR = "rgba(0, 0, 0, 180)"

# =============================================================================
# Primary / Secondary 按钮专用色
# =============================================================================

# Primary 按钮（填充式）
BTN_PRIMARY_BG = "rgba(77, 166, 255, 200)"
BTN_PRIMARY_HOVER = "rgba(77, 166, 255, 255)"
BTN_PRIMARY_TEXT = "#ffffff"

# Secondary 按钮（描边式）
BTN_SECONDARY_BG = "rgba(60, 60, 75, 180)"
BTN_SECONDARY_HOVER = "rgba(80, 80, 100, 220)"
BTN_SECONDARY_BORDER = "rgba(100, 100, 120, 150)"
BTN_SECONDARY_TEXT = "#c8c8d8"

# Action Bar 按钮
BTN_ACTION_BG = "rgba(50, 50, 65, 200)"
BTN_ACTION_HOVER = "rgba(70, 70, 90, 240)"

# =============================================================================
# 字体 Token
# =============================================================================

FONT_FAMILY = "Inter"  # 备选: SF Pro Text, system-ui

# (字号, 字重) — 对应设计稿 5 级层级
FONT_TITLE = (14, "bold")       # 窗口标题、Tab 选中标签
FONT_HEADING = (13, "bold")     # 面板标题、区域头部
FONT_BODY = (12, "normal")      # 内容文本、聊天消息、输入框
FONT_CAPTION = (11, "normal")   # 状态信息、标签、辅助文字
FONT_TINY = (10, "normal")      # 时间戳、快捷键提示、状态点

# =============================================================================
# 按钮尺寸 Token
# =============================================================================

# (高度px, padding) — 对应设计稿 4 级
BTN_LARGE_HEIGHT = 36
BTN_LARGE_PADDING = "10px 20px"

BTN_MEDIUM_HEIGHT = 28
BTN_MEDIUM_PADDING = "6px 14px"

BTN_SMALL_HEIGHT = 22
BTN_SMALL_PADDING = "4px 10px"

BTN_ICON_SIZE = 24
BTN_ICON_PADDING = "4px"

# =============================================================================
# 窗口尺寸 Token（设计稿硬性约束）
# =============================================================================

WINDOW_SMART_COPILOT = (680, 520)
WINDOW_WORKSPACE = (1000, 700)
WINDOW_WORKSPACE_MIN = (800, 550)
WINDOW_SETTINGS = (600, 500)
WINDOW_STUDIO = (1200, 800)
WINDOW_STUDIO_MIN = (900, 600)

# 内部布局
SIDEBAR_WIDTH = 180         # Workspace Sidebar
SETTINGS_SIDEBAR_WIDTH = 140  # Settings Sidebar
FRAME_MARGIN = 10            # frameless 窗口外边距
FRAME_RADIUS = 14            # 圆角半径
SHADOW_BLUR = 24             # 阴影模糊半径

# =============================================================================
# Context Strip 数据源定义
# =============================================================================

CONTEXT_SOURCES = [
    ("selection", "🎯 Selection", "当前选区"),
    ("active_doc", "📄 Active Doc", "活动文档"),
    ("browser", "🌐 Browser", "浏览器"),
    ("clipboard", "📋 Clipboard", "剪贴板"),
    ("file", "📁 File", "文件"),
]

# =============================================================================
# Work Tab Primary/Secondary Actions 定义
# =============================================================================

PRIMARY_ACTIONS = [
    ("explain", "✨ Explain", "解释选中内容"),
    ("fix", "🔧 Fix", "修复问题"),
    ("polish", "✍️ Polish", "润色优化"),
]

SECONDARY_ACTIONS = [
    ("translate", "🌐 Translate", "翻译"),
    ("code_review", "💻 Code Review", "代码审查"),
    ("more", "··· More", "更多操作"),
]

# =============================================================================
# Workspace Sidebar 导航项
# =============================================================================

WORKSPACE_NAV_ITEMS = [
    ("task", "📋 Task", "任务定义与管理"),
    ("chat", "💬 Chat", "连续对话"),
    ("files", "📁 Files", "最近文件与拖放区"),
    ("memory", "🧠 Memory", "知识图谱与记忆"),
    ("settings", "⚙️ Settings", "引擎/主题/快捷键"),
]

# =============================================================================
# Settings Sidebar 分区
# =============================================================================

SETTINGS_SECTIONS = [
    ("engine", "🔌 Engine", "Cloud/Local LLM 配置"),
    ("appearance", "🎨 Appearance", "主题/字体/语言"),
    ("shortcuts", "⌨️ Shortcuts", "快捷键绑定"),
    ("advanced", "🔧 Advanced", "高级配置与导出"),
]
