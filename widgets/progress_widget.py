"""
进度反馈组件
支持进度条、状态显示、预估时间、多步骤进度
"""
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QGroupBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer


class ProgressWidget(QWidget):
    """进度反馈组件"""
    
    # 信号定义
    cancelled = pyqtSignal()  # 取消信号
    completed = pyqtSignal()  # 完成信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
        # 状态变量
        self.start_time = None
        self.current_progress = 0
        self.is_cancelled = False
        self.estimated_total = 100
        
        # 定时器用于更新预估时间
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_estimated_time)
        self.timer.start(1000)  # 每秒更新一次
    
    def setup_ui(self):
        """设置UI布局"""
        layout = QVBoxLayout(self)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
        
        # 状态信息区域
        info_layout = QHBoxLayout()
        
        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: gray;")
        info_layout.addWidget(self.status_label)
        
        # 预估时间标签
        self.estimated_label = QLabel("")
        self.estimated_label.setStyleSheet("color: gray;")
        info_layout.addWidget(self.estimated_label)
        
        # 百分比标签
        self.percent_label = QLabel("0%")
        self.percent_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(self.percent_label)
        
        layout.addLayout(info_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._on_cancel)
        button_layout.addWidget(self.cancel_btn)
        
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._on_pause)
        button_layout.addWidget(self.pause_btn)
        
        layout.addLayout(button_layout)
    
    def start(self, total=100):
        """开始进度"""
        self.estimated_total = total
        self.start_time = time.time()
        self.current_progress = 0
        self.is_cancelled = False
        
        # 更新UI
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(0)
        self.status_label.setText("处理中...")
        self.percent_label.setText("0%")
        self.estimated_label.setText("计算中...")
        
        # 启用按钮
        self.cancel_btn.setEnabled(True)
        self.pause_btn.setEnabled(True)
    
    def update(self, progress, status=""):
        """更新进度"""
        if self.is_cancelled:
            return False
        
        self.current_progress = progress
        
        # 更新进度条
        self.progress_bar.setValue(progress)
        
        # 更新百分比
        if self.estimated_total > 0:
            percent = int((progress / self.estimated_total) * 100)
            self.percent_label.setText(f"{percent}%")
        
        # 更新状态
        if status:
            self.status_label.setText(status)
        
        # 检查是否完成
        if progress >= self.estimated_total:
            self._on_complete()
        
        return True
    
    def _update_estimated_time(self):
        """更新预估时间"""
        if not self.start_time or self.current_progress == 0:
            return
        
        if self.current_progress >= self.estimated_total:
            self.estimated_label.setText("已完成")
            return
        
        # 计算预估剩余时间
        elapsed = time.time() - self.start_time
        speed = self.current_progress / elapsed
        remaining = (self.estimated_total - self.current_progress) / speed
        
        # 格式化时间
        if remaining < 60:
            time_text = f"剩余 {int(remaining)} 秒"
        elif remaining < 3600:
            minutes = int(remaining / 60)
            seconds = int(remaining % 60)
            time_text = f"剩余 {minutes} 分 {seconds} 秒"
        else:
            hours = int(remaining / 3600)
            minutes = int((remaining % 3600) / 60)
            time_text = f"剩余 {hours} 小时 {minutes} 分"
        
        self.estimated_label.setText(time_text)
    
    def _on_complete(self):
        """完成事件"""
        self.cancel_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.status_label.setText("完成")
        self.estimated_label.setText("已完成")
        self.percent_label.setText("100%")
        
        # 发送完成信号
        self.completed.emit()
    
    def _on_cancel(self):
        """取消事件"""
        self.is_cancelled = True
        self.cancel_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.status_label.setText("已取消")
        self.estimated_label.setText("")
        
        # 发送取消信号
        self.cancelled.emit()
    
    def _on_pause(self):
        """暂停事件"""
        # 这里可以实现暂停逻辑
        pass
    
    def reset(self):
        """重置"""
        self.start_time = None
        self.current_progress = 0
        self.is_cancelled = False
        
        # 更新UI
        self.progress_bar.setValue(0)
        self.status_label.setText("就绪")
        self.estimated_label.setText("")
        self.percent_label.setText("0%")
        
        # 禁用按钮
        self.cancel_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
    
    def get_progress(self):
        """获取当前进度"""
        return self.current_progress
    
    def get_status(self):
        """获取状态"""
        return self.status_label.text()
    
    def is_running(self):
        """是否正在运行"""
        return self.start_time is not None and not self.is_cancelled


class MultiStepProgressWidget(QWidget):
    """多步骤进度组件"""
    
    # 信号定义
    cancelled = pyqtSignal()
    completed = pyqtSignal()
    step_changed = pyqtSignal(int, str)  # 步骤改变信号 (step_index, step_name)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.steps = []
        self.current_step = 0
        self.step_progress = 0
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI布局"""
        layout = QVBoxLayout(self)
        
        # 步骤标签
        self.step_label = QLabel("步骤 0/0")
        self.step_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.step_label)
        
        # 步骤名称
        self.step_name_label = QLabel("")
        layout.addWidget(self.step_name_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # 状态信息
        info_layout = QHBoxLayout()
        
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: gray;")
        info_layout.addWidget(self.status_label)
        
        self.percent_label = QLabel("0%")
        self.percent_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(self.percent_label)
        
        layout.addLayout(info_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._on_cancel)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def add_step(self, name, weight=1):
        """添加步骤"""
        self.steps.append({"name": name, "weight": weight})
        self._update_step_label()
    
    def start(self):
        """开始"""
        if not self.steps:
            return
        
        self.current_step = 0
        self.step_progress = 0
        
        # 更新UI
        self._update_step_label()
        self.step_name_label.setText(self.steps[0]["name"])
        self.status_label.setText("处理中...")
        self.percent_label.setText("0%")
        
        # 启用按钮
        self.cancel_btn.setEnabled(True)
        
        # 发送步骤改变信号
        self.step_changed.emit(0, self.steps[0]["name"])
    
    def update_step_progress(self, progress):
        """更新当前步骤进度"""
        self.step_progress = progress
        
        # 计算总体进度
        overall = self._calculate_overall_progress()
        self.progress_bar.setValue(int(overall))
        self.percent_label.setText(f"{int(overall)}%")
    
    def next_step(self):
        """进入下一步"""
        if self.current_step < len(self.steps) - 1:
            self.current_step += 1
            self.step_progress = 0
            
            # 更新UI
            self._update_step_label()
            self.step_name_label.setText(self.steps[self.current_step]["name"])
            
            # 发送步骤改变信号
            self.step_changed.emit(self.current_step, self.steps[self.current_step]["name"])
            
            return True
        return False
    
    def _calculate_overall_progress(self):
        """计算总体进度"""
        if not self.steps:
            return 0
        
        # 计算总权重
        total_weight = sum(step["weight"] for step in self.steps)
        
        # 计算当前进度
        current_weight = 0
        for i, step in enumerate(self.steps):
            if i < self.current_step:
                current_weight += step["weight"]
            elif i == self.current_step:
                current_weight += step["weight"] * (self.step_progress / 100)
        
        return (current_weight / total_weight) * 100
    
    def _update_step_label(self):
        """更新步骤标签"""
        self.step_label.setText(f"步骤 {self.current_step + 1}/{len(self.steps)}")
    
    def _on_cancel(self):
        """取消事件"""
        self.cancel_btn.setEnabled(False)
        self.status_label.setText("已取消")
        
        # 发送取消信号
        self.cancelled.emit()
    
    def complete(self):
        """完成"""
        self.cancel_btn.setEnabled(False)
        self.status_label.setText("完成")
        self.percent_label.setText("100%")
        self.progress_bar.setValue(100)
        
        # 发送完成信号
        self.completed.emit()
    
    def reset(self):
        """重置"""
        self.current_step = 0
        self.step_progress = 0
        
        # 更新UI
        self.progress_bar.setValue(0)
        self.step_label.setText("步骤 0/0")
        self.step_name_label.setText("")
        self.status_label.setText("就绪")
        self.percent_label.setText("0%")
        
        # 禁用按钮
        self.cancel_btn.setEnabled(False)
    
    def get_current_step(self):
        """获取当前步骤"""
        return self.current_step
    
    def get_current_step_name(self):
        """获取当前步骤名称"""
        if 0 <= self.current_step < len(self.steps):
            return self.steps[self.current_step]["name"]
        return None
    
    def get_overall_progress(self):
        """获取总体进度"""
        return self._calculate_overall_progress()


class ProgressManager:
    """进度管理器"""
    
    def __init__(self):
        self.callbacks = []
        self.progress_widget = None
        self.multi_step_widget = None
    
    def set_progress_widget(self, widget):
        """设置进度组件"""
        self.progress_widget = widget
    
    def set_multi_step_widget(self, widget):
        """设置多步骤进度组件"""
        self.multi_step_widget = widget
    
    def add_callback(self, callback):
        """添加回调"""
        self.callbacks.append(callback)
    
    def update_progress(self, progress, status=""):
        """更新进度"""
        if self.progress_widget:
            self.progress_widget.update(progress, status)
        
        # 调用回调
        for callback in self.callbacks:
            callback(progress, status)
    
    def update_step_progress(self, progress):
        """更新步骤进度"""
        if self.multi_step_widget:
            self.multi_step_widget.update_step_progress(progress)
    
    def next_step(self):
        """进入下一步"""
        if self.multi_step_widget:
            return self.multi_step_widget.next_step()
        return False
    
    def reset(self):
        """重置"""
        if self.progress_widget:
            self.progress_widget.reset()
        
        if self.multi_step_widget:
            self.multi_step_widget.reset()
