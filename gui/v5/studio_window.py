"""StudioWindowV5 — PPT 共创工作台 4-Panel 窗口壳 (~1200×800)"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSplitter, QTextEdit, QLineEdit,
    QFrame, QGraphicsDropShadowEffect, QApplication,
    QColorDialog, QSizePolicy
)

from gui.v5 import tokens as T
from gui.v5.telemetry import telemetry
from gui.v5 import bridge

# 导入已实现的PPT共创组件
from opencopilot.capabilities.ppt.preview_panel import PreviewPanel
from opencopilot.capabilities.ppt.outline_panel import OutlinePanel
from opencopilot.capabilities.ppt.ai_chat_widget import AICopilotChatWidget
from opencopilot.capabilities.ppt.source_panel import SourcePanel

# 预设主题配置
PPT_THEMES = {
    "professional": {
        "name": "专业蓝",
        "primary_color": "#1a73e8",
        "secondary_color": "#4285f4",
        "background_color": "#ffffff",
        "text_color": "#202124",
        "accent_color": "#1967d2"
    },
    "creative": {
        "name": "创意紫",
        "primary_color": "#9c27b0",
        "secondary_color": "#ce93d8",
        "background_color": "#fafafa",
        "text_color": "#212121",
        "accent_color": "#7b1fa2"
    },
    "nature": {
        "name": "自然绿",
        "primary_color": "#2e7d32",
        "secondary_color": "#66bb6a",
        "background_color": "#f1f8e9",
        "text_color": "#1b5e20",
        "accent_color": "#388e3c"
    },
    "sunset": {
        "name": "日落橙",
        "primary_color": "#ef6c00",
        "secondary_color": "#ff9800",
        "background_color": "#fff3e0",
        "text_color": "#e65100",
        "accent_color": "#f57c00"
    }
}


class StudioWindowV5(QWidget):
    """PPT 共创工作台：Source | Thumbs+Outline | Preview + AI Chat"""
    
    # 主题变化信号
    theme_changed = pyqtSignal(dict)

    def __init__(self, nav):
        super().__init__()
        self.nav = nav
        self.slides_data = []
        self._source_matcher = None  # SourceMatcher 实例（双向联动核心）
        self._syncing = False         # 信号循环守卫标志
        self.current_theme = PPT_THEMES["professional"]  # 默认主题
        self._init_ui()
        telemetry().window_event("V5_SWIN_CREATE", "studio_window")

    def _init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.resize(*T.WINDOW_STUDIO)
        self.setMinimumSize(*T.WINDOW_STUDIO_MIN)

        # 外层 Frame
        self._frame = QFrame(self)
        self._frame.setStyleSheet(f"""
            QFrame {{
                background-color: {T.BG_PRIMARY};
                border-radius: {T.FRAME_RADIUS}px;
                border: 1.5px solid {T.STROKE_BORDER};
            }}
        """)
        self._frame.resize(T.WINDOW_STUDIO[0] - 20, T.WINDOW_STUDIO[1] - 20)
        self._frame.move(T.FRAME_MARGIN, T.FRAME_MARGIN)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(T.SHADOW_BLUR)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 5)
        self._frame.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self._frame)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(6)

        # ── Title Bar ──
        title_bar = QHBoxLayout()
        title_label = QLabel("🚦 PPT 人机共创工作台")
        title_label.setStyleSheet(
            f"color: {T.TEXT_ACCENT}; font-weight: bold; "
            f"font-size: {T.FONT_TITLE[0]}px; background: transparent; border: none;"
        )

        self._stats_label = QLabel("幻灯片:0  要点:0  原文:0%")
        self._stats_label.setStyleSheet(
            f"color: {T.TEXT_SECONDARY}; font-size: {T.FONT_CAPTION[0]}px; "
            "background: transparent; border: none;"
        )

        btn_close = QPushButton("✕")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; "
            f"font-size: 14px; color: #888; }}"
            f"QPushButton:hover {{ color: #ff5555; }}"
        )
        btn_close.clicked.connect(self.close)

        title_bar.addWidget(title_label)
        title_bar.addStretch()
        title_bar.addWidget(self._stats_label)
        title_bar.addWidget(btn_close)
        layout.addLayout(title_bar)

        # ── 4-Panel Splitter ──
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Panel 1: Source (原文) - 使用SourcePanel组件实现双向联动
        self._source_panel = SourcePanel()
        # 连接信号：原文位置点击 → 跳转到对应幻灯片
        self._source_panel.position_clicked.connect(self._on_source_position_clicked)
        # 连接信号：原文选中文本 → 加入当前幻灯片
        self._source_panel.text_selected.connect(self._on_source_text_selected)
        # 连接信号：重新生成幻灯片
        self._source_panel.regenerate_slide_requested.connect(self._on_regenerate_slide)
        splitter.addWidget(self._source_panel)

        # Panel 2: Outline (大纲) - 集成OutlinePanel组件
        self._outline_panel_widget = OutlinePanel()
        # 连接信号：大纲选择 → 预览切换
        self._outline_panel_widget.slide_selected.connect(self._on_outline_slide_selected)
        # 连接信号：大纲修改 → 预览更新
        self._outline_panel_widget.slide_changed.connect(self._on_outline_slide_changed)
        splitter.addWidget(self._outline_panel_widget)

        # Panel 3: Preview (预览) - 集成PreviewPanel组件
        self._preview_panel_widget = PreviewPanel()
        # 连接信号：预览区双击编辑 → 大纲表单聚焦
        self._preview_panel_widget.renderer.edit_requested.connect(self._on_edit_requested)
        # 连接信号：预览区切换 → 大纲选中
        self._preview_panel_widget.slide_changed.connect(self._on_preview_slide_changed)
        splitter.addWidget(self._preview_panel_widget)

        # 比例: 25% : 30% : 45%
        splitter.setSizes([300, 360, 540])
        layout.addWidget(splitter, stretch=1)

        # ── AI Chat 集成区 ──
        self._ai_chat_widget = AICopilotChatWidget()
        # 连接信号：AI修改 → 全局刷新
        self._ai_chat_widget.slides_updated.connect(self._on_ai_slides_updated)
        layout.addWidget(self._ai_chat_widget)

        # ── 底部按钮栏 ──
        bottom_bar = QHBoxLayout()
        
        # 主题选择区域
        theme_label = QLabel("🎨 主题:")
        theme_label.setStyleSheet(f"color: {T.TEXT_PRIMARY}; font-size: 12px;")
        bottom_bar.addWidget(theme_label)
        
        # 添加主题色块按钮
        self._theme_buttons = []
        for theme_id, theme_info in PPT_THEMES.items():
            theme_btn = QPushButton()
            theme_btn.setFixedSize(24, 24)
            theme_btn.setToolTip(theme_info["name"])
            theme_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme_info["primary_color"]};
                    border: 2px solid {theme_info["secondary_color"]};
                    border-radius: 12px;
                }}
                QPushButton:hover {{
                    border-color: {T.TEXT_PRIMARY};
                    border-width: 3px;
                }}
            """)
            theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            theme_btn.clicked.connect(lambda checked, tid=theme_id: self._on_theme_selected(tid))
            theme_btn.setProperty("theme_id", theme_id)
            self._theme_buttons.append(theme_btn)
            bottom_bar.addWidget(theme_btn)
        
        # 自定义颜色按钮
        custom_color_btn = QPushButton("+")
        custom_color_btn.setFixedSize(24, 24)
        custom_color_btn.setToolTip("自定义主题颜色")
        custom_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {T.BG_ELEVATED};
                border: 2px dashed {T.STROKE_BORDER};
                border-radius: 12px;
                color: {T.TEXT_PRIMARY};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {T.BG_HOVER};
                border-color: {T.ACCENT_CONTROL};
            }}
        """)
        custom_color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        custom_color_btn.clicked.connect(self._on_custom_color)
        bottom_bar.addWidget(custom_color_btn)
        
        bottom_bar.addStretch()
        
        for label, tip, handler in [
            ("取消", "关闭工作台", self.close),
            ("🔍 全屏预览", "全屏幻灯片预览", self._on_fullscreen_preview),
            ("💾 导出 PPT", "导出为 .pptx 文件", self._on_export_ppt),
        ]:
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tip)
            is_cta = "导出" in label
            btn.setStyleSheet(self._bottom_btn_style(cta=is_cta))
            btn.clicked.connect(handler)
            bottom_bar.addWidget(btn)
        layout.addLayout(bottom_bar)

    # =========================================================================
    # 公共方法
    # =========================================================================

    def load_text(self, text: str):
        """加载文本到 Source Panel（由 NavigationManager 调用）"""
        t = telemetry()
        t.emit("V5_SWIN_LOAD_TEXT", text_len=len(text))

        if not text or not text.strip():
            self._stats_label.setText("幻灯片:0  要点:0  原文:0字符")
            return

        # 将文本加载到 Source Panel
        self._source_panel.set_original_text(text.strip())

        # 更新统计标签
        char_count = len(text.strip())
        self._stats_label.setText(
            f"幻灯片:0  要点:0  原文:{char_count}字符"
        )
        print(f"[v5] StudioWindow: 加载文本 → {char_count} 字符")

    def load_slides(self, slides: list):
        """加载 slides 到各个面板（由 NavigationManager 调用）"""
        t = telemetry()
        t.emit("V5_SWIN_LOAD_SLIDES", slide_count=len(slides))

        if not slides:
            return

        try:
            self.slides_data = slides

            # 构建原文与幻灯片的映射关系（双向联动核心）
            source_text = self._source_panel.text_edit.toPlainText()
            if source_text and slides:
                from opencopilot.capabilities.ppt.source_matcher import SourceMatcher
                self._source_matcher = SourceMatcher()
                self._source_matcher.build_mappings(source_text, slides)
                self._source_panel.set_source_matcher(self._source_matcher)
                print(f"[v5] StudioWindow: SourceMatcher 初始化完成，映射数: {len(self._source_matcher.mappings)}")
            else:
                self._source_matcher = None

            # 更新大纲面板
            self._outline_panel_widget.set_slides_data(slides)

            # 更新预览面板
            self._preview_panel_widget.set_slides_data(slides)

            # 更新AI Chat组件
            self._ai_chat_widget.set_slides_data(slides)

            # 更新统计标签
            char_count = len(self._source_panel.text_edit.toPlainText())
            self._stats_label.setText(
                f"幻灯片:{len(slides)}  要点:{len(slides)}  原文:{char_count}字符"
            )
            print(f"[v5] StudioWindow: 加载 slides → {len(slides)} 页")
        except Exception as e:
            print(f"[ERROR] StudioWindow.load_slides: {e}")
            self._stats_label.setText(f"❌ 加载失败: {str(e)[:50]}")

    # =========================================================================
    # 信号处理方法
    # =========================================================================

    def _on_outline_slide_selected(self, index: int):
        """大纲面板选择幻灯片 → 切换预览 + 高亮原文"""
        if self._syncing:
            return
        self._syncing = True
        try:
            t = telemetry()
            t.emit("V5_SWIN_OUTLINE_SELECT", slide_index=index)

            # 更新预览面板
            self._preview_panel_widget.set_current_slide(index)

            # 双向联动：高亮原文中对应的内容
            self._source_panel.highlight_slide_content(index)

            # 更新AI Chat组件的当前索引
            self._ai_chat_widget.set_slides_data(self.slides_data, current_index=index)

            # 更新统计标签
            char_count = len(self._source_panel.text_edit.toPlainText())
            self._stats_label.setText(
                f"幻灯片:{len(self.slides_data)}  当前:{index+1}  原文:{char_count}字符"
            )
        except Exception as e:
            print(f"[ERROR] StudioWindow._on_outline_slide_selected: {e}")
        finally:
            self._syncing = False

    def _on_outline_slide_changed(self, index: int, slide_data: dict):
        """大纲面板修改幻灯片内容 → 更新预览"""
        t = telemetry()
        t.emit("V5_SWIN_OUTLINE_CHANGE", slide_index=index)

        # 更新本地数据
        if 0 <= index < len(self.slides_data):
            self.slides_data[index] = slide_data

        # 刷新预览面板
        self._preview_panel_widget.set_slides_data(self.slides_data)

        print(f"[v5] StudioWindow: 大纲修改 → 幻灯片 {index+1}")

    def _on_preview_slide_changed(self, index: int):
        """预览区切换幻灯片 → 同步大纲选中 + 高亮原文"""
        if self._syncing:
            return
        self._syncing = True
        try:
            t = telemetry()
            t.emit("V5_SWIN_PREVIEW_CHANGE", slide_index=index)

            # 更新大纲面板选中状态（blockSignals 避免循环触发）
            self._outline_panel_widget.slide_list.blockSignals(True)
            self._outline_panel_widget.slide_list.setCurrentRow(index)
            self._outline_panel_widget.slide_list.blockSignals(False)

            # 双向联动：高亮原文中对应的内容
            self._source_panel.highlight_slide_content(index)

            # 更新AI Chat组件的当前索引
            self._ai_chat_widget.set_slides_data(self.slides_data, current_index=index)

            # 更新统计标签
            char_count = len(self._source_panel.text_edit.toPlainText())
            self._stats_label.setText(
                f"幻灯片:{len(self.slides_data)}  当前:{index+1}  原文:{char_count}字符"
            )
        except Exception as e:
            print(f"[ERROR] StudioWindow._on_preview_slide_changed: {e}")
        finally:
            self._syncing = False

    def _on_ai_slides_updated(self, updated_slides: list):
        """AI修改幻灯片 → 刷新大纲和预览"""
        t = telemetry()
        t.emit("V5_SWIN_AI_UPDATE", slide_count=len(updated_slides))

        # 更新本地数据
        self.slides_data = updated_slides

        # 刷新大纲面板
        self._outline_panel_widget.set_slides_data(updated_slides)

        # 刷新预览面板
        self._preview_panel_widget.set_slides_data(updated_slides)

        # 更新统计标签
        self._stats_label.setText(
            f"幻灯片:{len(updated_slides)}  已更新  原文:{len(self._source_panel.text_edit.toPlainText())}字符"
        )
        print(f"[v5] StudioWindow: AI更新 → {len(updated_slides)} 页")

    def _on_edit_requested(self, element_type: str, element_index: int, text: str):
        """预览区双击编辑 → 聚焦大纲表单"""
        t = telemetry()
        t.emit("V5_SWIN_EDIT_REQUESTED", element_type=element_type, element_index=element_index)

        # 根据元素类型聚焦到大纲面板的对应字段
        if element_type == "title":
            # 聚焦标题编辑框
            self._outline_panel_widget.title_edit.setFocus()
            self._outline_panel_widget.title_edit.selectAll()
        elif element_type == "subtitle":
            # 聚焦副标题编辑框
            self._outline_panel_widget.subtitle_edit.setFocus()
            self._outline_panel_widget.subtitle_edit.selectAll()
        elif element_type == "item":
            # 聚焦到对应的要点编辑器
            if 0 <= element_index < len(self._outline_panel_widget.item_editors):
                editor = self._outline_panel_widget.item_editors[element_index]
                editor.setFocus()
                editor.content_edit.selectAll()

        print(f"[v5] StudioWindow: 编辑请求 → {element_type}[{element_index}]")

    # =========================================================================
    # 主题相关方法
    # =========================================================================

    def _on_theme_selected(self, theme_id: str):
        """主题被选中"""
        if theme_id not in PPT_THEMES:
            return
        
        theme = PPT_THEMES[theme_id]
        self.current_theme = theme
        
        # 更新主题按钮样式
        self._update_theme_button_styles()
        
        # 应用主题到预览面板
        self._apply_theme_to_preview(theme)
        
        # 发送主题变化信号
        self.theme_changed.emit(theme)
        
        # 更新统计标签
        self._stats_label.setText(f"🎨 已切换主题: {theme['name']}")
        
        # 记录遥测
        t = telemetry()
        t.emit("V5_SWIN_THEME_CHANGE", theme_id=theme_id, theme_name=theme["name"])
        
        print(f"[v5] StudioWindow: 主题切换 → {theme['name']}")

    def _update_theme_button_styles(self):
        """更新主题按钮样式，高亮当前选中的主题"""
        for btn in self._theme_buttons:
            theme_id = btn.property("theme_id")
            if theme_id and theme_id in PPT_THEMES:
                theme = PPT_THEMES[theme_id]
                is_selected = theme == self.current_theme
                
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {theme["primary_color"]};
                        border: {'3px solid' if is_selected else '2px solid'} {T.TEXT_PRIMARY if is_selected else theme["secondary_color"]};
                        border-radius: 12px;
                    }}
                    QPushButton:hover {{
                        border-color: {T.TEXT_PRIMARY};
                        border-width: 3px;
                    }}
                """)

    def _apply_theme_to_preview(self, theme: dict):
        """应用主题到预览面板"""
        # 这里可以扩展为应用到整个预览面板
        # 目前只是打印主题信息
        print(f"[v5] StudioWindow: 应用主题到预览 - {theme['name']}")

    def _on_custom_color(self):
        """自定义颜色"""
        color = QColorDialog.getColor(
            QColor(self.current_theme.get("primary_color", "#1a73e8")),
            self,
            "选择主题主色"
        )
        
        if color.isValid():
            hex_color = color.name()
            
            # 创建自定义主题
            custom_theme = {
                "name": "自定义",
                "primary_color": hex_color,
                "secondary_color": self._lighten_color(hex_color, 0.3),
                "background_color": "#ffffff",
                "text_color": "#202124",
                "accent_color": self._darken_color(hex_color, 0.2)
            }
            
            # 更新当前主题
            self.current_theme = custom_theme
            
            # 更新主题按钮样式
            self._update_theme_button_styles()
            
            # 应用主题到预览面板
            self._apply_theme_to_preview(custom_theme)
            
            # 发送主题变化信号
            self.theme_changed.emit(custom_theme)
            
            # 更新统计标签
            self._stats_label.setText(f"🎨 自定义主题: {hex_color}")
            
            # 记录遥测
            t = telemetry()
            t.emit("V5_SWIN_CUSTOM_COLOR", color=hex_color)
            
            print(f"[v5] StudioWindow: 自定义颜色 → {hex_color}")

    def _lighten_color(self, hex_color: str, factor: float) -> str:
        """使颜色变亮"""
        try:
            # 移除#前缀
            hex_color = hex_color.lstrip('#')
            
            # 转换为RGB
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            # 变亮
            r = min(255, int(r + (255 - r) * factor))
            g = min(255, int(g + (255 - g) * factor))
            b = min(255, int(b + (255 - b) * factor))
            
            # 转换回hex
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return hex_color

    def _darken_color(self, hex_color: str, factor: float) -> str:
        """使颜色变暗"""
        try:
            # 移除#前缀
            hex_color = hex_color.lstrip('#')
            
            # 转换为RGB
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            # 变暗
            r = max(0, int(r * (1 - factor)))
            g = max(0, int(g * (1 - factor)))
            b = max(0, int(b * (1 - factor)))
            
            # 转换回hex
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return hex_color

    def get_current_theme(self) -> dict:
        """获取当前主题"""
        return self.current_theme

    def set_theme(self, theme: dict):
        """设置主题"""
        self.current_theme = theme
        self._update_theme_button_styles()
        self._apply_theme_to_preview(theme)
        self.theme_changed.emit(theme)

    # =========================================================================
    # 生命周期
    # =========================================================================

    def closeEvent(self, event):
        t = telemetry()
        t.emit("V5_SWIN_CLOSE", slides_count=len(self.slides_data))
        super().closeEvent(event)

    # =========================================================================
    # 原文面板事件处理（双向联动功能）
    # =========================================================================

    def _on_source_position_clicked(self, pos: int):
        """原文面板中点击某个位置 → 跳转到对应的幻灯片"""
        if self._syncing:
            return
        if not self.slides_data:
            return

        self._syncing = True
        try:
            # 使用 SourceMatcher 查找对应幻灯片
            if not self._source_matcher:
                self._stats_label.setText("⚠️ 原文匹配器未初始化，请先加载幻灯片")
                return

            # find_slide_for_position 返回 Optional[Tuple[int, Optional[int]]]
            result = self._source_matcher.find_slide_for_position(pos)
            if result is None:
                self._stats_label.setText(f"⚠️ 该位置未关联任何幻灯片 (pos={pos})")
                return

            slide_index, item_index = result
            if slide_index < 0 or slide_index >= len(self.slides_data):
                return

            # 更新大纲选中（blockSignals 防止循环触发 _on_outline_slide_selected）
            self._outline_panel_widget.slide_list.blockSignals(True)
            self._outline_panel_widget.slide_list.setCurrentRow(slide_index)
            self._outline_panel_widget.slide_list.blockSignals(False)

            # 更新预览面板
            self._preview_panel_widget.set_current_slide(slide_index)

            # 高亮原文中对应的内容（双向联动）
            self._source_panel.highlight_slide_content(slide_index, item_index)

            # 更新AI Chat组件
            self._ai_chat_widget.set_slides_data(self.slides_data, current_index=slide_index)

            # 更新统计标签
            char_count = len(self._source_panel.text_edit.toPlainText())
            self._stats_label.setText(
                f"幻灯片:{len(self.slides_data)}  当前:{slide_index+1}  原文:{char_count}字符"
            )
            print(f"[v5] StudioWindow: 原文位置点击 → 幻灯片 {slide_index+1} (pos={pos})")
        except Exception as e:
            print(f"[ERROR] StudioWindow._on_source_position_clicked: {e}")
            self._stats_label.setText(f"❌ 跳转失败: {str(e)[:50]}")
        finally:
            self._syncing = False

    def _on_source_text_selected(self, text: str, start: int, end: int):
        """原文面板中选中文本 → 加入当前幻灯片"""
        if not text or not self.slides_data:
            return

        try:
            # 获取当前幻灯片索引（通过 slide_list.currentRow）
            current_index = self._outline_panel_widget.slide_list.currentRow()
            if current_index < 0 or current_index >= len(self.slides_data):
                current_index = 0

            # 将选中的文本加入当前幻灯片的 items
            slide = self.slides_data[current_index]
            if "items" not in slide:
                slide["items"] = []
            slide["items"].append({"level": 0, "text": text})

            # 更新大纲和预览面板
            self._outline_panel_widget.set_slides_data(self.slides_data)
            self._preview_panel_widget.set_slides_data(self.slides_data)

            # 重新构建 SourceMatcher 映射（因为幻灯片内容已变化）
            source_text = self._source_panel.text_edit.toPlainText()
            if source_text:
                from opencopilot.capabilities.ppt.source_matcher import SourceMatcher
                self._source_matcher = SourceMatcher()
                self._source_matcher.build_mappings(source_text, self.slides_data)
                self._source_panel.set_source_matcher(self._source_matcher)

            self._stats_label.setText(
                f"✅ 已将选中文本加入幻灯片 {current_index + 1}"
            )
            print(f"[v5] StudioWindow: 选中文本已加入幻灯片 {current_index+1} ({len(text)}字)")
        except Exception as e:
            print(f"[ERROR] StudioWindow._on_source_text_selected: {e}")
            self._stats_label.setText(f"❌ 添加失败: {str(e)[:50]}")

    def _on_regenerate_slide(self, selected_text: str, expression_type: str):
        """原文面板请求重新生成当前幻灯片"""
        if not self.slides_data or not selected_text:
            return

        try:
            # 获取当前幻灯片索引
            current_index = self._outline_panel_widget.slide_list.currentRow()
            if current_index < 0 or current_index >= len(self.slides_data):
                current_index = 0

            # 构建 AI 指令
            instruction = (
                f"请根据以下选中的原文内容，重新生成第 {current_index + 1} 页幻灯片。\n\n"
                f"要求：\n"
                f"1. 使用选中的原文内容作为核心素材\n"
                f"2. 采用「{expression_type}」的表达方式\n"
                f"3. 保持与原有大纲的逻辑一致性\n"
                f"4. 生成适合当前表达方式的结构化内容\n\n"
                f"选中的原文内容：\n{selected_text}\n\n"
                f"当前幻灯片索引：{current_index}\n"
                f"请返回修改该幻灯片的 JSON 指令。"
            )

            # 通过 AI Chat 组件发送指令
            self._ai_chat_widget.send_instruction(instruction)

            self._stats_label.setText(
                f"🔄 正在根据选中文本重新生成幻灯片 {current_index + 1}..."
            )
            print(f"[v5] StudioWindow: 重新生成请求 → 幻灯片 {current_index+1}, 表达方式={expression_type}")
        except Exception as e:
            print(f"[ERROR] StudioWindow._on_regenerate_slide: {e}")
            self._stats_label.setText(f"❌ 重新生成失败: {str(e)[:50]}")

    # =========================================================================
    # 非AI 事件处理
    # =========================================================================

    def _on_export_ppt(self):
        """导出 PPT（非AI: 直接调用 bridge）"""
        t = telemetry()
        t.emit("V5_SWIN_EXPORT_PPT", slides_count=len(self.slides_data))

        if not self.slides_data:
            self._stats_label.setText("⚠️ 无幻灯片数据可导出")
            print("[v5] StudioWindow: 导出失败 — slides_data 为空")
            return

        result = bridge.do_export_ppt(self.slides_data)
        if result.get("success"):
            self._stats_label.setText(
                f"✅ 已导出: {result.get('filename', '')} "
                f"({result.get('slide_count', 0)} 页, "
                f"{result.get('file_size', 0) / 1024:.0f}KB)"
            )
            print(f"[v5] StudioWindow: PPT 导出 → {result.get('file_path')}")
        else:
            self._stats_label.setText(f"❌ 导出失败: {result.get('message', '')}")
            print(f"[v5] StudioWindow: PPT 导出失败 — {result.get('message')}")

    def _on_fullscreen_preview(self):
        """全屏预览（调用PreviewPanel的全屏预览功能）"""
        t = telemetry()
        t.emit("V5_SWIN_FULLSCREEN", slides_count=len(self.slides_data))

        if not self.slides_data:
            self._stats_label.setText("⚠️ 无幻灯片数据可预览")
            return

        # 调用PreviewPanel的全屏预览
        self._preview_panel_widget._on_fullscreen()

    # =========================================================================
    # 工厂方法
    # =========================================================================

    @staticmethod
    def _create_panel(title: str, placeholder: str) -> tuple[QFrame, QTextEdit]:
        """创建面板，返回 (panel, text_edit) 元组以便后续更新内容"""
        panel = QFrame()
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {T.BG_ELEVATED};
                border-radius: 8px;
                border: 1px solid {T.STROKE_SUBTLE};
            }}
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QLabel(title)
        header.setStyleSheet(
            f"color: {T.TEXT_PRIMARY}; font-weight: bold; "
            f"font-size: {T.FONT_HEADING[0]}px; "
            "background: transparent; border: none;"
        )
        layout.addWidget(header)

        content = QTextEdit()
        content.setReadOnly(True)
        content.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        content.setPlainText(placeholder)
        content.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                color: {T.TEXT_TERTIARY};
                font-size: {T.FONT_BODY[0]}px;
                border: none;
            }}
        """)
        layout.addWidget(content, stretch=1)
        return panel, content

    @staticmethod
    def _bottom_btn_style(cta=False):
        if cta:
            return f"""
                QPushButton {{
                    background-color: {T.BTN_PRIMARY_BG};
                    color: {T.BTN_PRIMARY_TEXT};
                    border: none; border-radius: 8px;
                    padding: {T.BTN_MEDIUM_PADDING};
                    font-size: {T.FONT_BODY[0]}px; font-weight: bold;
                }}
                QPushButton:hover {{ background-color: {T.BTN_PRIMARY_HOVER}; }}
            """
        return f"""
            QPushButton {{
                background-color: {T.BTN_ACTION_BG};
                color: {T.TEXT_SECONDARY};
                border: 1px solid {T.STROKE_SUBTLE};
                border-radius: 8px;
                padding: {T.BTN_MEDIUM_PADDING};
                font-size: {T.FONT_BODY[0]}px;
            }}
            QPushButton:hover {{
                background-color: {T.BTN_ACTION_HOVER};
                color: {T.TEXT_PRIMARY};
            }}
        """
