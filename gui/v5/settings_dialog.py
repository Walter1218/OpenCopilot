"""SettingsDialogV5 — Unified Settings 弹窗壳 (600×500)

Sidebar(140px) + Content Area(460px)，4 分区:
Engine / Appearance / Shortcuts / Advanced
"""
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QStackedWidget,
    QLineEdit, QComboBox, QCheckBox, QSlider,
    QFormLayout, QWidget, QFileDialog, QMessageBox,
)

from gui.v5 import tokens as T
from gui.v5.telemetry import telemetry
from gui.v5 import bridge


class _TestConnectionWorker(QThread):
    """在子线程中测试 LLM 连接，避免阻塞 UI"""
    result_signal = pyqtSignal(dict)

    def __init__(self, provider_type, api_base, api_key, model):
        super().__init__()
        self.provider_type = provider_type
        self.api_base = api_base
        self.api_key = api_key
        self.model = model

    def run(self):
        result = bridge.test_llm_connection(
            self.provider_type, self.api_base, self.api_key, self.model
        )
        self.result_signal.emit(result)


class SettingsDialogV5(QDialog):
    """Unified Settings — 单实例弹窗"""

    def __init__(self, nav, initial_section: str = "engine"):
        super().__init__()
        self.nav = nav
        self._init_ui()
        self.select_section(initial_section)
        telemetry().settings_event("V5_SET_OPEN", section=initial_section)

    def _init_ui(self):
        self.setWindowTitle("Settings")
        self.resize(*T.WINDOW_SETTINGS)
        self.setMinimumSize(500, 400)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {T.BG_PRIMARY};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── 左侧 Sidebar ──
        sidebar = QFrame()
        sidebar.setFixedWidth(T.SETTINGS_SIDEBAR_WIDTH)
        sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {T.BG_ELEVATED};
                border-right: 1px solid {T.STROKE_SUBTLE};
            }}
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 16, 0, 16)
        sidebar_layout.setSpacing(2)

        # 标题
        title = QLabel("⚙️ Settings")
        title.setStyleSheet(
            f"color: {T.TEXT_ACCENT}; font-weight: bold; "
            f"font-size: {T.FONT_TITLE[0]}px; padding: 0 12px 10px 12px; "
            "background: transparent; border: none;"
        )
        sidebar_layout.addWidget(title)

        # 导航按钮
        self._nav_buttons = {}
        section_index = {}
        for idx, (sid, label, _tip) in enumerate(T.SETTINGS_SECTIONS):
            btn = QPushButton(f"  {label}")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(_tip)
            btn.setStyleSheet(self._nav_btn_style(selected=(idx == 0)))
            btn.clicked.connect(lambda checked, i=idx: self._on_nav_clicked(i))
            sidebar_layout.addWidget(btn)
            self._nav_buttons[sid] = btn
            section_index[sid] = idx

        sidebar_layout.addStretch()
        layout.addWidget(sidebar)

        # ── 右侧 Content Area ──
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("QStackedWidget { background: transparent; border: none; }")

        # Engine Panel
        self._stack.addWidget(self._create_engine_panel())
        # Appearance Panel
        self._stack.addWidget(self._create_appearance_panel())
        # Shortcuts Panel
        self._stack.addWidget(self._create_shortcuts_panel())
        # Advanced Panel
        self._stack.addWidget(self._create_advanced_panel())

        layout.addWidget(self._stack, stretch=1)

        self._section_indices = section_index

    # =========================================================================
    # 公共方法
    # =========================================================================

    def select_section(self, section_id: str):
        """跳转到指定分区"""
        idx = self._section_indices.get(section_id, 0)
        self._stack.setCurrentIndex(idx)
        for sid, btn in self._nav_buttons.items():
            is_selected = (sid == section_id)
            btn.setChecked(is_selected)
            btn.setStyleSheet(self._nav_btn_style(selected=is_selected))

    # =========================================================================
    # 事件
    # =========================================================================

    def _on_nav_clicked(self, index: int):
        self._stack.setCurrentIndex(index)
        sid = T.SETTINGS_SECTIONS[index][0]
        telemetry().settings_event("V5_SET_SWITCH", section=sid)
        for s, btn in self._nav_buttons.items():
            is_selected = (s == sid)
            btn.setChecked(is_selected)
            btn.setStyleSheet(self._nav_btn_style(selected=is_selected))

    # ── Engine 事件 ──

    def _on_save_engine(self):
        """保存引擎配置"""
        provider = "local" if self._engine_backend.currentIndex() == 1 else "cloud"
        api_base = self._engine_api_base.text().strip()
        api_key = self._engine_api_key.text().strip()
        model = self._engine_model.text().strip()
        ok = bridge.save_engine_config(provider, api_key, model, api_base)
        if ok:
            self._engine_status.setText("● Saved")
            self._engine_status.setStyleSheet(
                f"color: {T.STATUS_ONLINE}; font-size: {T.FONT_CAPTION[0]}px; "
                "background: transparent; border: none;"
            )
            telemetry().settings_event("V5_SET_ENGINE_SAVE", provider=provider)
            print(f"[v5] Settings: 引擎配置已保存 (provider={provider})")
        else:
            self._engine_status.setText("● Save Failed")
            self._engine_status.setStyleSheet(
                f"color: #FF5555; font-size: {T.FONT_CAPTION[0]}px; "
                "background: transparent; border: none;"
            )

    def _on_test_connection(self):
        """测试 LLM 连接（异步）"""
        provider = "local" if self._engine_backend.currentIndex() == 1 else "cloud"
        self._engine_status.setText("● Testing...")
        self._engine_status.setStyleSheet(
            f"color: {T.TEXT_SECONDARY}; font-size: {T.FONT_CAPTION[0]}px; "
            "background: transparent; border: none;"
        )
        self._engine_test_btn.setEnabled(False)

        worker = _TestConnectionWorker(
            provider_type=provider,
            api_base=self._engine_api_base.text().strip(),
            api_key=self._engine_api_key.text().strip(),
            model=self._engine_model.text().strip(),
        )
        worker.result_signal.connect(self._on_test_result)
        worker.finished.connect(lambda: self._engine_test_btn.setEnabled(True))
        self._test_worker = worker
        worker.start()

    def _on_test_result(self, result: dict):
        """处理测试结果"""
        if result.get("success"):
            self._engine_status.setText(f"● {result.get('message', 'Connected')}")
            self._engine_status.setStyleSheet(
                f"color: {T.STATUS_ONLINE}; font-size: {T.FONT_CAPTION[0]}px; "
                "background: transparent; border: none;"
            )
        else:
            self._engine_status.setText(f"● {result.get('message', 'Failed')}")
            self._engine_status.setStyleSheet(
                f"color: #FF5555; font-size: {T.FONT_CAPTION[0]}px; "
                "background: transparent; border: none;"
            )
        print(f"[v5] Settings: 连接测试结果 = {result}")

    # ── Appearance 事件 ──

    def _on_theme_clicked(self, theme_name: str):
        """切换主题"""
        for name, btn in self._theme_buttons.items():
            is_selected = (name == theme_name.lower())
            btn.setChecked(is_selected)
            btn.setStyleSheet(self._theme_chip_style(selected=is_selected))
        ok = bridge.save_appearance(theme=theme_name.lower())
        telemetry().settings_event("V5_SET_APPEARANCE_THEME", theme=theme_name.lower())
        print(f"[v5] Settings: 主题切换 → {theme_name.lower()}, saved={ok}")

    def _on_font_size_changed(self, value: int):
        """字体大小变更"""
        self._font_size_label.setText(f"Font Size: {value}px")
        ok = bridge.save_appearance(font_size=value)
        print(f"[v5] Settings: 字体大小 → {value}px, saved={ok}")

    # ── Shortcuts 事件 ──

    def _on_shortcut_edited(self, action_name: str, key_sequence: str):
        """快捷键编辑"""
        if action_name in self._shortcuts_data:
            self._shortcuts_data[action_name]["key_sequence"] = key_sequence

    def _on_save_shortcuts(self):
        """保存快捷键配置"""
        ok = bridge.save_shortcuts(self._shortcuts_data)
        telemetry().settings_event("V5_SET_SHORTCUTS_SAVE", count=len(self._shortcuts_data))
        print(f"[v5] Settings: 快捷键已保存, saved={ok}")

    # ── Advanced 事件 ──

    def _on_export_config(self):
        """导出配置"""
        result = bridge.do_export_config()
        if result.get("success"):
            telemetry().settings_event("V5_SET_EXPORT", path=result.get("file_path", ""))
            print(f"[v5] Settings: 配置导出 → {result.get('file_path')}")

    def _on_import_config(self):
        """导入配置（弹文件选择框）"""
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Config", "", "JSON Files (*.json)"
        )
        if path:
            result = bridge.do_import_config(path)
            telemetry().settings_event("V5_SET_IMPORT", path=path,
                                       success=result.get("success", False))
            print(f"[v5] Settings: 配置导入 ← {path}, result={result}")

    def _on_reset_all(self):
        """重置全部配置"""
        result = bridge.do_reset_config("")
        if result.get("success"):
            sections = result.get("reset_sections", [])
            telemetry().settings_event("V5_SET_RESET", sections=sections)
            print(f"[v5] Settings: 配置已重置, sections={sections}")

    # =========================================================================
    # 面板创建
    # =========================================================================

    def _create_engine_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header = QLabel("🔌 Engine")
        header.setStyleSheet(self._header_style())
        layout.addWidget(header)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # 加载当前配置
        config = bridge.get_config()

        # Backend 选择
        self._engine_backend = QComboBox()
        self._engine_backend.addItems(["Cloud LLM", "Local LLM"])
        current_provider = config.get("provider_type", "cloud")
        if current_provider == "local":
            self._engine_backend.setCurrentIndex(1)
        self._engine_backend.setStyleSheet(self._combo_style())
        form.addRow(self._form_label("Backend:"), self._engine_backend)

        # API Base
        self._engine_api_base = QLineEdit()
        self._engine_api_base.setPlaceholderText("https://api.minimax.chat/v1 (Cloud) / http://localhost:11434/v1 (Local)")
        self._engine_api_base.setText(
            config.get(f"{current_provider}_api_base", "")
            or ("https://api.minimax.chat/v1" if current_provider != "local" else "http://localhost:11434/v1")
        )
        self._engine_api_base.setStyleSheet(self._input_style())
        form.addRow(self._form_label("API Base:"), self._engine_api_base)

        # API Key
        self._engine_api_key = QLineEdit()
        self._engine_api_key.setPlaceholderText("sk-...")
        self._engine_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._engine_api_key.setText(config.get(f"{current_provider}_api_key", ""))
        self._engine_api_key.setStyleSheet(self._input_style())
        form.addRow(self._form_label("API Key:"), self._engine_api_key)

        # Model
        self._engine_model = QLineEdit()
        self._engine_model.setPlaceholderText("MiniMax-M1 / Ollama 模型名")
        self._engine_model.setText(config.get(f"{current_provider}_model", ""))
        self._engine_model.setStyleSheet(self._input_style())
        form.addRow(self._form_label("Model:"), self._engine_model)

        layout.addLayout(form)

        # Status + Buttons
        status_row = QHBoxLayout()
        self._engine_status = QLabel("● Ready")
        self._engine_status.setStyleSheet(
            f"color: {T.STATUS_ONLINE}; font-size: {T.FONT_CAPTION[0]}px; "
            "background: transparent; border: none;"
        )
        status_row.addWidget(self._engine_status)
        status_row.addStretch()

        save_btn = QPushButton("Save")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(self._cta_btn_style())
        save_btn.clicked.connect(self._on_save_engine)
        self._engine_save_btn = save_btn

        test_btn = QPushButton("Test Connection")
        test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        test_btn.setStyleSheet(self._outline_btn_style())
        test_btn.clicked.connect(self._on_test_connection)
        self._engine_test_btn = test_btn

        status_row.addWidget(test_btn)
        status_row.addWidget(save_btn)
        layout.addLayout(status_row)

        layout.addStretch()
        return panel

    def _create_appearance_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header = QLabel("🎨 Appearance")
        header.setStyleSheet(self._header_style())
        layout.addWidget(header)

        # 加载当前配置
        app = bridge.get_appearance()
        current_theme = app.get("theme", "dark")
        current_font_size = app.get("font_size", 12)

        # Theme
        theme_label = QLabel("Theme")
        theme_label.setStyleSheet(self._sub_header_style())
        layout.addWidget(theme_label)
        theme_row = QHBoxLayout()
        self._theme_buttons = {}
        for name in ["Dark", "Light", "System"]:
            btn = QPushButton(name)
            btn.setCheckable(True)
            is_selected = (name.lower() == current_theme)
            btn.setChecked(is_selected)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(self._theme_chip_style(selected=is_selected))
            btn.clicked.connect(lambda checked, n=name: self._on_theme_clicked(n))
            theme_row.addWidget(btn)
            self._theme_buttons[name.lower()] = btn
        theme_row.addStretch()
        layout.addLayout(theme_row)

        # Font Size
        self._font_size_label = QLabel(f"Font Size: {current_font_size}px")
        self._font_size_label.setStyleSheet(self._sub_header_style())
        layout.addWidget(self._font_size_label)
        self._font_slider = QSlider(Qt.Orientation.Horizontal)
        self._font_slider.setRange(8, 24)
        self._font_slider.setValue(current_font_size)
        self._font_slider.valueChanged.connect(self._on_font_size_changed)
        self._font_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 4px; background: {T.STROKE_BORDER}; border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                width: 14px; height: 14px; margin: -5px 0;
                background: {T.ACCENT_CONTROL}; border-radius: 7px;
            }}
        """)
        layout.addWidget(self._font_slider)

        layout.addStretch()
        return panel

    def _create_shortcuts_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header = QLabel("⌨️ Shortcuts")
        header.setStyleSheet(self._header_style())
        layout.addWidget(header)

        # 从 Bridge 加载快捷键配置
        config = bridge.get_shortcuts()
        shortcuts_data = config.get("shortcuts", {})
        self._shortcuts_data = dict(shortcuts_data)  # 用于保存编辑

        if shortcuts_data:
            for action_name, sc_info in shortcuts_data.items():
                key_seq = sc_info.get("key_sequence", "")
                row = QHBoxLayout()
                lbl = QLabel(action_name)
                lbl.setStyleSheet(
                    f"color: {T.TEXT_PRIMARY}; font-size: {T.FONT_BODY[0]}px; "
                    "background: transparent; border: none;"
                )
                key_edit = QLineEdit()
                key_edit.setFixedWidth(120)
                key_edit.setText(key_seq)
                key_edit.setPlaceholderText("输入快捷键")
                key_edit.setStyleSheet(self._input_style())
                key_edit.textChanged.connect(
                    lambda text, a=action_name: self._on_shortcut_edited(a, text)
                )
                row.addWidget(lbl)
                row.addStretch()
                row.addWidget(key_edit)
                layout.addLayout(row)
        else:
            no_data = QLabel("暂无快捷键配置")
            no_data.setStyleSheet(
                f"color: {T.TEXT_SECONDARY}; font-size: {T.FONT_BODY[0]}px; "
                "background: transparent; border: none;"
            )
            layout.addWidget(no_data)

        # Save 按钮
        save_row = QHBoxLayout()
        save_row.addStretch()
        save_btn = QPushButton("Save Shortcuts")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(self._cta_btn_style())
        save_btn.clicked.connect(self._on_save_shortcuts)
        save_row.addWidget(save_btn)
        layout.addLayout(save_row)

        layout.addStretch()
        return panel

    def _create_advanced_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header = QLabel("🔧 Advanced")
        header.setStyleSheet(self._header_style())
        layout.addWidget(header)

        # Auto Save
        auto_save = QCheckBox("Auto Save conversations")
        auto_save.setChecked(True)
        auto_save.setStyleSheet(
            f"QCheckBox {{ color: {T.TEXT_PRIMARY}; font-size: {T.FONT_BODY[0]}px; }}"
        )
        layout.addWidget(auto_save)

        # Export Format
        form = QFormLayout()
        fmt_combo = QComboBox()
        fmt_combo.addItems(["Markdown", "Plain Text", "HTML"])
        fmt_combo.setStyleSheet(self._combo_style())
        form.addRow(self._form_label("Export:"), fmt_combo)
        layout.addLayout(form)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        for label, handler in [
            ("Export Config", self._on_export_config),
            ("Import Config", self._on_import_config),
            ("Reset All", self._on_reset_all),
        ]:
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(self._outline_btn_style())
            btn.clicked.connect(handler)
            btn_row.addWidget(btn)
        layout.addLayout(btn_row)

        layout.addStretch()
        return panel

    # =========================================================================
    # 样式工具
    # =========================================================================

    @staticmethod
    def _nav_btn_style(selected=False):
        if selected:
            return (
                f"QPushButton {{ background: {T.BG_SELECTED}; color: {T.TEXT_ACCENT}; "
                f"border: none; border-radius: 6px; padding: 8px 12px; "
                f"font-size: {T.FONT_BODY[0]}px; font-weight: bold; text-align: left; }}"
            )
        return (
            f"QPushButton {{ background: transparent; color: {T.TEXT_SECONDARY}; "
            f"border: none; border-radius: 6px; padding: 8px 12px; "
            f"font-size: {T.FONT_BODY[0]}px; text-align: left; }}"
            f"QPushButton:hover {{ background: {T.BG_HOVER}; color: {T.TEXT_PRIMARY}; }}"
        )

    @staticmethod
    def _header_style():
        return (
            f"color: {T.TEXT_PRIMARY}; font-weight: bold; "
            f"font-size: 16px; background: transparent; border: none;"
        )

    @staticmethod
    def _sub_header_style():
        return (
            f"color: {T.TEXT_SECONDARY}; font-size: {T.FONT_BODY[0]}px; "
            f"font-weight: bold; background: transparent; border: none;"
        )

    @staticmethod
    def _form_label(text):
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {T.TEXT_SECONDARY}; font-size: {T.FONT_BODY[0]}px; "
            "background: transparent; border: none;"
        )
        return lbl

    @staticmethod
    def _input_style():
        return f"""
            QLineEdit {{
                background-color: {T.BG_INPUT}; color: {T.TEXT_PRIMARY};
                border: 1px solid {T.STROKE_BORDER}; border-radius: 6px;
                padding: 6px 10px; font-size: {T.FONT_BODY[0]}px;
            }}
            QLineEdit:focus {{ border: 1px solid {T.STROKE_FOCUS}; }}
        """

    @staticmethod
    def _combo_style():
        return f"""
            QComboBox {{
                background-color: {T.BG_ELEVATED}; color: {T.TEXT_PRIMARY};
                border: 1px solid {T.STROKE_BORDER}; border-radius: 6px;
                padding: 5px 10px; font-size: {T.FONT_BODY[0]}px;
            }}
            QComboBox:hover {{ border: 1px solid {T.STROKE_FOCUS}; }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background: {T.BG_ELEVATED}; color: {T.TEXT_PRIMARY};
                border: 1px solid {T.STROKE_BORDER};
                selection-background-color: {T.BG_SELECTED};
            }}
        """

    @staticmethod
    def _cta_btn_style():
        return f"""
            QPushButton {{
                background-color: {T.BTN_PRIMARY_BG}; color: {T.BTN_PRIMARY_TEXT};
                border: none; border-radius: 6px;
                padding: {T.BTN_MEDIUM_PADDING};
                font-size: {T.FONT_BODY[0]}px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {T.BTN_PRIMARY_HOVER}; }}
        """

    @staticmethod
    def _outline_btn_style():
        return f"""
            QPushButton {{
                background-color: {T.BTN_SECONDARY_BG}; color: {T.BTN_SECONDARY_TEXT};
                border: 1px solid {T.BTN_SECONDARY_BORDER}; border-radius: 6px;
                padding: {T.BTN_SMALL_PADDING};
                font-size: {T.FONT_CAPTION[0]}px;
            }}
            QPushButton:hover {{
                background-color: {T.BTN_SECONDARY_HOVER}; color: {T.TEXT_PRIMARY};
            }}
        """

    @staticmethod
    def _theme_chip_style(selected=False):
        if selected:
            return (
                f"QPushButton {{ background: {T.BG_SELECTED}; color: {T.TEXT_ACCENT}; "
                f"border: 1px solid {T.STROKE_FOCUS}; border-radius: 6px; "
                f"padding: 6px 14px; font-size: {T.FONT_BODY[0]}px; font-weight: bold; }}"
            )
        return (
            f"QPushButton {{ background: {T.BG_ELEVATED}; color: {T.TEXT_SECONDARY}; "
            f"border: 1px solid {T.STROKE_SUBTLE}; border-radius: 6px; "
            f"padding: 6px 14px; font-size: {T.FONT_BODY[0]}px; }}"
            f"QPushButton:hover {{ background: {T.BG_HOVER}; color: {T.TEXT_PRIMARY}; }}"
        )
