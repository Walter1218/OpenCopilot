"""AgentWorkspace - 任务工作台"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal
from gui.workers.chat import ChatWorker
from llm_provider import ProviderFactory
class AgentWorkspace(QWidget):
    """独立智能体工作台 —— 三连击右键唤出。

    用于：定义任务背景、独立对话、全局设置。
    设定的任务上下文会自动注入到双击右键快捷卡片的 AI 请求中。
    """
    task_changed = pyqtSignal(str)  # 任务变更时通知 CopilotManager

    def __init__(self, provider, parent_manager=None):
        super().__init__()
        self.provider = provider
        self.parent_manager = parent_manager
        self.chat_worker = None
        self.current_task = ""
        self.session_id = str(uuid.uuid4())
        self._temp_chat_pos = 0
        self._pending_hide = False
        self._allow_close = False
        self._user_initiated_hide = False  # 区分用户主动隐藏 vs 系统自动隐藏
        self._init_ui()

    def _init_ui(self):
        # 不用 Qt.Tool：macOS 会在父窗口失焦时自动隐藏 Tool 窗口
        # 用 WA_ShowWithoutActivating 控制首次显示不抢焦点
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self._resize_margin = 14
        self._resizing = False
        self._resize_edge = None
        self._resize_start_geo = None
        self._resize_start_pos = None
        self.resize(520, 480)

        # 外层 Frame
        self.frame = QFrame(self)
        self.frame.setStyleSheet("""
            QFrame {
                background-color: rgba(25, 25, 32, 245);
                border-radius: 14px;
                border: 1.5px solid rgba(77, 166, 255, 80);
            }
        """)
        self.frame.resize(500, 460)
        self.frame.move(10, 10)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(0, 6)
        self.frame.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.frame)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # --- 标题栏 ---
        title_layout = QHBoxLayout()
        self.title_label = QLabel("🧠 ASU Agent Workspace")
        self.title_label.setStyleSheet(
            "color: #4da6ff; font-weight: bold; font-size: 14px; background: transparent; border: none;"
        )

        self.btn_settings = QPushButton("⚙️")
        self.btn_settings.setStyleSheet("""
            QPushButton { background: transparent; border: none; font-size: 14px; }
            QPushButton:hover { color: #fff; }
        """)
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.clicked.connect(self._open_settings)

        self.btn_close = QPushButton("✕")
        self.btn_close.setStyleSheet("""
            QPushButton { background: transparent; border: none; font-size: 14px; color: #888; }
            QPushButton:hover { color: #ff5555; }
        """)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.hide_workspace)

        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        title_layout.addWidget(self.btn_settings)
        title_layout.addWidget(self.btn_close)
        layout.addLayout(title_layout)

        # --- 任务定义区 ---
        task_label = QLabel("📋 当前任务（注入到所有划词请求中）")
        task_label.setStyleSheet("color: #aaa; font-size: 11px; background: transparent; border: none;")
        layout.addWidget(task_label)

        task_input_layout = QHBoxLayout()
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("例：我正在审查支付模块的安全漏洞...")
        self.task_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(40, 40, 50, 200);
                color: #eee; border: 1px solid rgba(100, 100, 120, 150);
                border-radius: 6px; padding: 6px 10px; font-size: 12px;
            }
            QLineEdit:focus { border: 1px solid #4da6ff; }
        """)
        self.task_input.returnPressed.connect(self._save_task)

        self.btn_save_task = QPushButton("设定")
        self.btn_save_task.setStyleSheet("""
            QPushButton {
                background-color: #4da6ff; color: #000; border-radius: 6px;
                padding: 6px 14px; font-weight: bold; font-size: 12px;
            }
            QPushButton:hover { background-color: #66b3ff; }
        """)
        self.btn_save_task.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_task.clicked.connect(self._save_task)

        task_input_layout.addWidget(self.task_input, stretch=1)
        self.btn_paste_task = QPushButton("📋")
        self.btn_paste_task.setToolTip("从剪贴板粘贴")
        self.btn_paste_task.setStyleSheet("""
            QPushButton {
                background-color: rgba(120, 80, 220, 180); color: #fff;
                border-radius: 6px; padding: 6px 8px; font-size: 12px;
                border: 1px solid rgba(120, 80, 220, 255);
            }
            QPushButton:hover { background-color: rgba(120, 80, 220, 255); }
        """)
        self.btn_paste_task.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_paste_task.clicked.connect(self._paste_task_from_clipboard)
        task_input_layout.addWidget(self.btn_paste_task)
        task_input_layout.addWidget(self.btn_save_task)
        layout.addLayout(task_input_layout)

        # 当前任务状态标签
        self.task_status = QLabel("")
        self.task_status.setStyleSheet(
            "color: #42f554; font-size: 11px; background: transparent; border: none;"
        )
        self.task_status.hide()
        layout.addWidget(self.task_status)

        # --- 对话区 ---
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: transparent; color: #eee; font-size: 13px;
                border: none; line-height: 1.5;
            }
            QScrollBar:vertical { width: 6px; background: transparent; }
            QScrollBar::handle:vertical { background: rgba(255,255,255,40); border-radius: 3px; }
        """)
        layout.addWidget(self.chat_display, stretch=1)

        # --- 输入栏 ---
        input_layout = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("输入消息，按 Enter 发送...")
        self.chat_input.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.chat_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(40, 40, 50, 200); color: #fff;
                border: 1px solid rgba(100, 100, 120, 150);
                border-radius: 6px; padding: 6px 10px; font-size: 13px;
            }
            QLineEdit:focus { border: 1px solid #4da6ff; }
        """)
        self.chat_input.returnPressed.connect(self._send_message)

        self.btn_send = QPushButton("发送")
        self.btn_send.setStyleSheet("""
            QPushButton {
                background-color: #4da6ff; color: #000; border-radius: 6px;
                padding: 6px 14px; font-weight: bold;
            }
            QPushButton:hover { background-color: #66b3ff; }
        """)
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.clicked.connect(self._send_message)

        input_layout.addWidget(self.chat_input, stretch=1)
        input_layout.addWidget(self.btn_send)
        layout.addLayout(input_layout)

    def _paste_task_from_clipboard(self):
        """从剪贴板粘贴到任务输入框。"""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text and text.strip():
            self.task_input.setText(text.strip())
            self._save_task()

    def _save_task(self):
        task = self.task_input.text().strip()
        self.current_task = task
        if task:
            self.task_status.setText(f"✅ 激活任务: {task}")
            self.task_status.show()
            self.task_changed.emit(task)
            self._append_message("系统", f"任务已设定: {task}")
        else:
            self.task_status.hide()
            self.task_changed.emit("")
            self._append_message("系统", "任务已清除。")

    def _send_message(self):
        text = self.chat_input.text().strip()
        if not text:
            return
        self.chat_input.clear()
        self._append_message("你", text)
        self._append_message("AI", "思考中...", is_temp=True)

        if self.chat_worker and self.chat_worker.isRunning():
            self.chat_worker.stop()
            self.chat_worker.wait()

        # 聊天模式，带当前任务上下文 + 任务描述作为 source_text
        meta = {}
        if self.current_task:
            meta["task"] = self.current_task
            meta["source_text"] = self.current_task  # 让 Agent 知道上下文
            meta["source_type"] = "workspace_task"
            
        # 核心修复：工作台也需要注入系统级别的全局状态感知（焦点应用、历史应用）
        if self.parent_manager and hasattr(self.parent_manager, 'ai_card'):
            meta["current_active_app"] = self.parent_manager.ai_card.current_active_app
            meta["recent_apps"] = getattr(self.parent_manager.ai_card, 'recent_apps', [])
            
        print(f"[ASU] Workspace Chat | session={self.session_id[:8]}... | has_task={bool(self.current_task)} | meta_keys={list(meta.keys())}")
        self.chat_worker = ChatWorker(
            self.provider, text, self.session_id,
            context_source="chat", context_meta=meta
        )
        self.chat_worker.text_updated.connect(self._on_chat_update)
        self.chat_worker.finished_signal.connect(lambda: None)
        self.chat_worker.start()

    def _append_message(self, role, text, is_temp=False):
        color = "#4da6ff" if role == "你" else "#42f554" if role == "AI" else "#aaaaaa"
        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)

        if is_temp:
            self._temp_chat_pos = cursor.position()

        self.chat_display.insertHtml(
            f'<b style="color:{color};">{role}:</b> {text}<br><br>'
        )
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_chat_update(self, text):
        cursor = self.chat_display.textCursor()
        cursor.setPosition(self._temp_chat_pos)
        cursor.movePosition(cursor.MoveOperation.End, cursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertHtml(md_render(text))
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _open_settings(self):
        """打开统一设置对话框"""
        # 创建主设置对话框
        main_dialog = QDialog(self)
        main_dialog.setWindowTitle("⚙️ 设置")
        main_dialog.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(main_dialog)
        
        # 创建标签页
        tabs = QTabWidget()
        
        # 标签1: 引擎设置（旧的LLM配置）
        engine_tab = QWidget()
        engine_layout = QVBoxLayout(engine_tab)
        engine_settings = SettingsDialog(main_dialog)  # 旧的SettingsDialog
        engine_layout.addWidget(engine_settings)
        tabs.addTab(engine_tab, "🔧 引擎设置")
        
        # 标签2: 个性化设置（新的设置）
        personal_tab = QWidget()
        personal_layout = QVBoxLayout(personal_tab)
        personal_settings = NewSettingsDialog(main_dialog)  # 新的SettingsDialog
        personal_layout.addWidget(personal_settings)
        tabs.addTab(personal_tab, "🎨 个性化")
        
        # 标签3: 主题设置
        theme_tab = self._create_theme_tab(main_dialog)
        tabs.addTab(theme_tab, "🌈 主题")
        
        # 标签4: 快捷键设置
        shortcut_tab = self._create_shortcut_tab(main_dialog)
        tabs.addTab(shortcut_tab, "⌨️ 快捷键")
        
        layout.addWidget(tabs)
        
        # 关闭按钮
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(main_dialog.close)
        layout.addWidget(btn_close)
        
        main_dialog.exec()
    
    def _create_theme_tab(self, parent):
        """创建主题设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 主题选择
        theme_group = QGroupBox("选择主题")
        theme_layout = QVBoxLayout()
        
        current_theme = self.theme_manager.current_theme
        themes = self.theme_manager.get_themes()  # 使用正确的方法名
        
        for theme_id, theme_info in themes.items():
            radio = QRadioButton(theme_info.name)
            radio.setChecked(theme_id == current_theme)
            radio.toggled.connect(lambda checked, t=theme_id: self._apply_theme(t) if checked else None)
            theme_layout.addWidget(radio)
        
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)
        
        # 主题预览
        preview_label = QLabel("主题预览区域")
        preview_label.setMinimumHeight(100)
        preview_label.setStyleSheet("background-color: #2b2b2b; color: #fff; padding: 10px;")
        layout.addWidget(preview_label)
        
        layout.addStretch()
        return tab
    
    def _create_shortcut_tab(self, parent):
        """创建快捷键设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 快捷键列表
        shortcut_group = QGroupBox("快捷键配置")
        shortcut_layout = QVBoxLayout()
        
        shortcuts = self.shortcut_manager.get_shortcuts()  # 使用正确的方法名
        for key, info in shortcuts.items():
            row = QHBoxLayout()
            row.addWidget(QLabel(info.name))
            row.addWidget(QLabel(info.key))
            row.addStretch()
            shortcut_layout.addLayout(row)
        
        shortcut_group.setLayout(shortcut_layout)
        layout.addWidget(shortcut_group)
        
        layout.addStretch()
        return tab
    
    def _apply_settings(self, settings):
        """应用新设置"""
        # 应用主题
        if 'theme' in settings:
            self.theme_manager.switch_theme(settings['theme'])
            self._apply_theme(settings['theme'])
        
        # 应用其他设置
        print(f"[ASU] 设置已更新: {settings}")
    
    def _apply_theme(self, theme_name):
        """应用主题到UI"""
        config = self.theme_manager.get_theme_config(theme_name)
        if config:
            self.frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {config.get('background', 'rgba(30, 30, 35, 240)')};
                    border-radius: 12px;
                    border: 1px solid rgba(100, 100, 100, 100);
                }}
            """)
    
    def open_batch_dialog(self):
        """打开批量处理对话框"""
        dialog = BatchDialog(self)
        dialog.exec()
    
    def _on_file_dropped(self, file_path, file_info):
        """处理文件拖入（信号发两个参数: file_path, file_info）"""
        print(f"[ASU] 文件拖入: {file_path}, info={file_info}")
        self._handle_file_drop(file_path)
    
    def _show_text_context_menu(self, position):
        """显示文本右键菜单"""
        selected_text = self.text_edit.textCursor().selectedText()
        menu = TextContextMenu(selected_text)
        
        # 添加自定义菜单项
        menu.addSeparator()
        action_terminology = menu.addAction("📚 术语库管理")
        action_memory = menu.addAction("💾 翻译记忆")
        
        action = menu.exec(self.text_edit.mapToGlobal(position))
        
        if action:
            if action == action_terminology:
                self._open_terminology_dialog()
            elif action == action_memory:
                self._open_translation_memory_dialog()
            else:
                # 处理标准菜单项
                self._handle_context_action(action.text(), selected_text)
    
    def _handle_context_action(self, action_text, selected_text):
        """处理右键菜单动作"""
        if not selected_text:
            return
        
        if "翻译" in action_text:
            self.trigger_ai("translate")
        elif "润色" in action_text:
            self.trigger_ai("polish")
        elif "代码解析" in action_text:
            self.trigger_ai("code")
        elif "复制" in action_text:
            QApplication.clipboard().setText(selected_text)
    
    def _open_terminology_dialog(self):
        """打开术语库管理对话框"""
        dialog = TerminologyDialog(self)
        dialog.exec()
    
    def _open_translation_memory_dialog(self):
        """打开翻译记忆对话框"""
        # 显示翻译记忆统计
        count = len(self.translation_memory.units)
        QMessageBox.information(self, "翻译记忆", f"翻译记忆中共有 {count} 条记录")

    def _reload_provider(self):
        self.provider = ProviderFactory.create_provider()

    def set_agent_status(self, is_online: bool):
        """根据 Agent 守护服务的探活结果更新工作台的状态提示。"""
        # 工作台暂时只打印日志，后续可扩展为托盘状态更新
        if not is_online:
            print("[AgentWorkspace] 守护服务离线，聊天功能可能不可用。")

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        text = event.mimeData().text()
        if text:
            self.task_input.setText(text)
            self._save_task()

    # ---- 拖拽缩放支持 ----
    def _get_resize_edge(self, pos):
        m = self._resize_margin
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        b, r = y > h - m, x > w - m
        t, l = y < m, x < m
        if b and r: return 'br'
        if b and l: return 'bl'
        if t and r: return 'tr'
        if t and l: return 'tl'
        if b: return 'b'
        if r: return 'r'
        if t: return 't'
        if l: return 'l'
        return None

    _EDGE_CURSORS = {
        'l': Qt.CursorShape.SizeHorCursor, 'r': Qt.CursorShape.SizeHorCursor,
        't': Qt.CursorShape.SizeVerCursor, 'b': Qt.CursorShape.SizeVerCursor,
        'tl': Qt.CursorShape.SizeFDiagCursor, 'br': Qt.CursorShape.SizeFDiagCursor,
        'tr': Qt.CursorShape.SizeBDiagCursor, 'bl': Qt.CursorShape.SizeBDiagCursor,
    }

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._get_resize_edge(event.pos())
            if edge:
                self._resizing = True; self._resize_edge = edge
                self._resize_start_geo = self.geometry()
                self._resize_start_pos = event.globalPosition().toPoint()
                QApplication.setOverrideCursor(self._EDGE_CURSORS[edge])
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing:
            delta = event.globalPosition().toPoint() - self._resize_start_pos
            g = self._resize_start_geo; e = self._resize_edge
            x, y, w, h = g.x(), g.y(), g.width(), g.height()
            min_w, min_h = 380, 300
            if 'r' in e: w = max(min_w, g.width() + delta.x())
            if 'l' in e: x = g.x() + delta.x(); w = max(min_w, g.width() - delta.x())
            if 'b' in e: h = max(min_h, g.height() + delta.y())
            if 't' in e: y = g.y() + delta.y(); h = max(min_h, g.height() - delta.y())
            self.setGeometry(x, y, w, h)
            self.frame.resize(w - 20, h - 22)
            return
        edge = self._get_resize_edge(event.pos())
        self.setCursor(self._EDGE_CURSORS.get(edge, Qt.CursorShape.ArrowCursor))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resizing:
            QApplication.restoreOverrideCursor()
            self._resizing = False; self._resize_edge = None
        super().mouseReleaseEvent(event)

    def show_workspace(self, x, y):
        self.session_id = str(uuid.uuid4())
        self.chat_display.clear()
        if self.current_task:
            self._append_message("系统", f"当前任务: {self.current_task}")

        pos = QCursor.pos()
        screen = QApplication.screenAt(pos) or QApplication.primaryScreen()
        sr = screen.geometry()
        w, h = self.width(), self.height()

        tx = pos.x() + 20
        ty = pos.y() + 20
        if tx + w > sr.right():
            tx = pos.x() - w - 20
        if ty + h > sr.bottom():
            ty = pos.y() - h - 20
        tx = max(sr.left(), min(tx, sr.right() - w))
        ty = max(sr.top(), min(ty, sr.bottom() - h))

        self.move(tx, ty)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.show()
        self.raise_()  # macOS: 确保浮窗在最前面
        make_panel_persistent(self)  # 设置 NSPanel 不随失焦隐藏
        self.chat_input.setFocus()

    def hide_workspace(self):
        self._pending_hide = False
        self._user_initiated_hide = True
        self.hide()
        if self.chat_worker and self.chat_worker.isRunning():
            self.chat_worker.stop()

    def hideEvent(self, event):
        """拦截 macOS 对 Tool 窗口的自动隐藏：只在用户主动隐藏时才允许。"""
        if self._user_initiated_hide or self._allow_close:
            self._user_initiated_hide = False
            super().hideEvent(event)
        else:
            event.ignore()
            QTimer.singleShot(0, self._force_reshow)

    def _force_reshow(self):
        """macOS 失焦后重新显示并置顶。"""
        if not self._user_initiated_hide and not self._allow_close:
            self.show()
            self.raise_()
            make_panel_persistent(self)

    def closeEvent(self, event):
        if self._allow_close:
            event.accept()
            return
        self.hide_workspace()
        event.ignore()


# ==========================================
# 5. 总调度管理器与生命周期管理
# ==========================================
