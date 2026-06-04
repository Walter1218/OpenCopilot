from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
"""CAD Manager + main()"""
import sys
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QCursor, QAction
from typing import Dict, Any
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QStyle, QMessageBox
from cursor_effects import CursorOverlay
from gui.window import AICardWindow
from gui.workspace import AgentWorkspace
from gui.workers.mouse import MouseListenerWorker
from gui.workers.health import AgentHealthWorker
from gui.shared import check_accessibility_permission
from llm_provider import ProviderFactory
class CopilotManager:
    def __init__(self):
        # UI 与 Agent 生命周期完全解耦：
        # CopilotManager 不持有、不启动、也不终止 Agent 子进程。
        # Agent 作为独立的 OS 级守护进程运行（见 deploy/com.asu.agent.plist）。
        self.provider = ProviderFactory.create_provider()
        self._is_shutting_down = False

        # 三个独立图层：
        # 1. 光标特效图层（全屏、鼠标穿透）
        self.cursor_overlay = CursorOverlay()
        # 2. 智能卡片图层（双击右键，快捷交互）
        self.ai_card = AICardWindow(self.provider)
        # 3. 任务工作台图层（三击右键，任务定义 + 独立对话）
        self.workspace = AgentWorkspace(self.provider, parent_manager=self)

        # 三击 vs 双击仲裁状态
        self._pending_clicks = 0
        self._pending_click_x = 0
        self._pending_click_y = 0
        self._click_resolve_timer = None

        # 启动鼠标监听
        self.mouse_thread = MouseListenerWorker()
        self.mouse_thread.mouse_moved.connect(self.cursor_overlay.update_cursor_position)
        self.mouse_thread.right_clicked.connect(self._on_right_clicked)
        self.mouse_thread.global_click.connect(self._on_global_click)
        self.mouse_thread.listener_error.connect(self._on_mouse_listener_error)
        self.mouse_thread.listener_died.connect(self._restart_mouse_listener)
        self.mouse_thread.start()

        # 任务上下文同步：工作台任务 → 快捷卡片
        self.workspace.task_changed.connect(self._sync_task_context)

        self._init_tray()

        # 启动时异步探活 Agent，将结果回传给 UI
        self._ping_agent()

    def _init_tray(self):
        self.tray = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("[ASU] 当前系统不可用托盘，跳过托盘初始化。")
            return

        app = QApplication.instance()
        icon = QIcon()
        if app and app.windowIcon() and not app.windowIcon().isNull():
            icon = app.windowIcon()
        if icon.isNull() and app:
            icon = app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)

        self.tray = QSystemTrayIcon(icon, app)
        self.tray.setToolTip("ASU Smart Copilot")

        tray_menu = QMenu()
        action_show_quick = QAction("重新显示快捷卡片", self.tray)
        action_show_workspace = QAction("显示任务工作台", self.tray)
        action_hide_all = QAction("隐藏全部窗口", self.tray)
        action_quit = QAction("退出 Smart Copilot", self.tray)

        action_show_quick.triggered.connect(self._show_quick_card)
        action_show_workspace.triggered.connect(self._show_workspace)
        action_hide_all.triggered.connect(self._hide_all_windows)
        action_quit.triggered.connect(self._quit_application)

        tray_menu.addAction(action_show_quick)
        tray_menu.addAction(action_show_workspace)
        tray_menu.addSeparator()
        tray_menu.addAction(action_hide_all)
        tray_menu.addSeparator()
        tray_menu.addAction(action_quit)

        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._show_quick_card()

    def _show_quick_card(self):
        pos = QCursor.pos()
        self.ai_card.show_card(pos.x(), pos.y())

    def _show_workspace(self):
        pos = QCursor.pos()
        self.workspace.show_workspace(pos.x(), pos.y())

    def _hide_all_windows(self):
        self.ai_card.hide_card()
        self.workspace.hide_workspace()

    def _quit_application(self):
        if self._is_shutting_down:
            return
        self._is_shutting_down = True

        self.cleanup()

        self.ai_card._allow_close = True
        self.workspace._allow_close = True
        self.ai_card.close()
        self.workspace.close()
        self.cursor_overlay.close()

        if self.tray:
            self.tray.hide()

        app = QApplication.instance()
        if app:
            app.quit()

    def _sync_task_context(self, task):
        """工作台设定的任务合并到快捷卡片（不覆盖 IDE/浏览器来源信息）。"""
        if task:
            self.ai_card.task_context = task
        else:
            self.ai_card.task_context = ""

    def _on_right_clicked(self, x, y, count):
        """右键点击仲裁：用 QTimer 区分双击 vs 三击。"""
        self._pending_clicks = count
        self._pending_click_x = x
        self._pending_click_y = y

        if count == 2:
            # 可能是双击，但也可能是三击的中间状态，延迟判决
            if self._click_resolve_timer is None:
                self._click_resolve_timer = QTimer()
                self._click_resolve_timer.setSingleShot(True)
                self._click_resolve_timer.timeout.connect(self._resolve_right_clicks)
            self._click_resolve_timer.start(400)  # 等待 400ms 看有没有第三次点击
        elif count >= 3:
            # 三击确认，立即执行
            if self._click_resolve_timer:
                self._click_resolve_timer.stop()
            self._resolve_right_clicks()

    def _resolve_right_clicks(self):
        """根据最终点击次数决定行为。"""
        clicks = self._pending_clicks
        self._pending_clicks = 0

        if clicks == 2:
            self._on_double_right_click(self._pending_click_x, self._pending_click_y)
        elif clicks >= 3:
            self._on_triple_right_click(self._pending_click_x, self._pending_click_y)

    def _on_double_right_click(self, x, y):
        pos = QCursor.pos()
        # 呼出卡片前尝试通过 Broker 无感读取高亮文本
        probe = SystemProbeClient()
        selected = ""
        if probe.is_broker_alive():
            selected = probe.get_selection() or ""
        
        self.ai_card.show_card(pos.x(), pos.y(), selected_text=selected)

    def _on_triple_right_click(self, x, y):
        pos = QCursor.pos()
        self.workspace.show_workspace(pos.x(), pos.y())

    def _on_global_click(self, x, y):
        self.cursor_overlay.add_ripple(x, y)

    def _on_mouse_listener_error(self, err: str):
        print("[ASU] 鼠标监听启动失败：")
        print(err)
        QMessageBox.warning(
            None,
            "OpenCopilot 权限提示",
            "无法监听全局鼠标事件。\n\n请在系统设置中授予当前终端「辅助功能（Accessibility）」权限，\n然后完全退出并重新运行：\n\n  bash scripts/start_ui.sh"
        )

    def _restart_mouse_listener(self):
        """listener 非正常退出时自动重启（1.5 秒延迟防抖）。"""
        print("[ASU] 鼠标监听线程异常退出，1.5 秒后自动重启...")
        QTimer.singleShot(1500, self._do_restart_listener)

    def _do_restart_listener(self):
        if self._is_shutting_down:
            return
        old = self.mouse_thread
        self.mouse_thread = MouseListenerWorker()
        self.mouse_thread.mouse_moved.connect(self.cursor_overlay.update_cursor_position)
        self.mouse_thread.right_clicked.connect(self._on_right_clicked)
        self.mouse_thread.global_click.connect(self._on_global_click)
        self.mouse_thread.listener_error.connect(self._on_mouse_listener_error)
        self.mouse_thread.listener_died.connect(self._restart_mouse_listener)
        self.mouse_thread.start()
        if old and old.isRunning():
            old.wait(2000)
        print("[ASU] 鼠标监听已重启。")

    def cleanup(self):
        # UI 退出时只终止监听线程与定时器，绝不干涉 Agent 守护进程生命周期。
        if self._click_resolve_timer:
            self._click_resolve_timer.stop()

        if self.mouse_thread and self.mouse_thread.isRunning():
            self.mouse_thread.stop()
            self.mouse_thread.wait(1200)

        if hasattr(self, "_health_worker") and self._health_worker.isRunning():
            self._health_worker.quit()
            self._health_worker.wait(500)

    def _ping_agent(self):
        """异步向 Agent 发送探活请求，完成后通过信号更新 UI 状态。"""
        self._health_worker = AgentHealthWorker()
        self._health_worker.health_result.connect(self._on_agent_health)
        self._health_worker.start()

    def _on_agent_health(self, is_alive: bool, active_sessions: int):
        """收到探活结果后，通知 AI 卡片和工作台更新显示状态。"""
        if is_alive:
            print(f"[ASU] 守护服务在线 (活跃会话: {active_sessions})")
        else:
            print("[ASU] 守护服务离线，UI 进入只读状态。请启动 Agent 守护进程。")
        self.ai_card.set_agent_status(is_alive)
        self.workspace.set_agent_status(is_alive)

def main():
    """Smart Copilot 主入口"""
    app = QApplication(sys.argv)
    if not check_accessibility_permission():
        print("❌ 辅助功能权限未授予，Smart Copilot 无法监听鼠标事件。")
        print("   请在系统设置中授权后重新运行。")
    app.setQuitOnLastWindowClosed(False)
    manager = CopilotManager()
    print("🚀 ASU Smart Copilot 已启动！")
    ret = app.exec()
    manager.cleanup()
    sys.exit(ret)


if __name__ == '__main__':
    main()