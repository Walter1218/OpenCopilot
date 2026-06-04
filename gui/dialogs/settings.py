"""gui/dialogs/settings.py module"""
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QSpinBox, QCheckBox, QGroupBox, QFormLayout, QLineEdit, QFileDialog, QMessageBox
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
import os
from llm_provider import load_config, save_config
class SettingsDialog(QDialog):
    config_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ ASU 引擎设置")
        self.setMinimumSize(500, 400)
        self.config = load_config()
        self.setup_ui()
        
    def setup_ui(self):
        from PyQt6.QtWidgets import QGroupBox, QStackedWidget, QFormLayout, QRadioButton
        layout = QVBoxLayout(self)
        
        # 1. 引擎后端选择 (QButtonGroup)
        type_group = QGroupBox("选择 ASU 定制智能体后端引擎")
        type_layout = QHBoxLayout()
        self.radio_minimax = QRadioButton("云端 LLM (MiniMax)")
        self.radio_custom = QRadioButton("本地/第三方 LLM (Ollama/vLLM)")
        
        type_layout.addWidget(self.radio_minimax)
        type_layout.addWidget(self.radio_custom)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # 2. 动态面板 (QStackedWidget)
        self.stacked_widget = QStackedWidget()
        
        # 面板 A: MiniMax
        self.page_minimax = QWidget()
        layout_minimax = QFormLayout(self.page_minimax)
        
        default_minimax_key = self.config.get("minimax_api_key") or os.environ.get("MINIMAX_API_KEY", "")
        self.input_minimax_key = QLineEdit(default_minimax_key)
        self.input_minimax_key.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.input_minimax_key.setPlaceholderText("请输入 MiniMax API Key (若已在 .env 配置可留空)")
        layout_minimax.addRow("API Key:", self.input_minimax_key)
        layout_minimax.addRow(QLabel("默认模型: MiniMax-M2.7"))
        
        # 面板 B: Custom LLM (Ollama 等)
        self.page_custom = QWidget()
        layout_custom = QFormLayout(self.page_custom)
        self.input_custom_base = QLineEdit(self.config.get("local_api_base", "http://localhost:11434/v1"))
        self.input_custom_base.setPlaceholderText("例如: http://localhost:11434/v1")
        self.input_custom_key = QLineEdit(self.config.get("local_api_key", ""))
        self.input_custom_key.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.input_custom_key.setPlaceholderText("API Key (Ollama可不填)")
        
        custom_probe_layout = QHBoxLayout()
        self.btn_custom_scan = QPushButton("🔍 探测模型")
        self.btn_custom_scan.clicked.connect(self.scan_custom_models)
        self.combo_custom_model = QComboBox()
        self.combo_custom_model.setEditable(True)
        self.combo_custom_model.setCurrentText(self.config.get("local_model", "llama3"))
        custom_probe_layout.addWidget(self.combo_custom_model, stretch=1)
        custom_probe_layout.addWidget(self.btn_custom_scan)
        
        layout_custom.addRow("API Base URL:", self.input_custom_base)
        layout_custom.addRow("API Key (选填):", self.input_custom_key)
        layout_custom.addRow("可用模型:", custom_probe_layout)
        
        # 添加到 StackedWidget
        self.stacked_widget.addWidget(self.page_minimax)
        self.stacked_widget.addWidget(self.page_custom)
        layout.addWidget(self.stacked_widget)
        
        # 3. 底部按钮
        btn_box = QHBoxLayout()
        btn_save = QPushButton("保存并关闭")
        btn_save.clicked.connect(self.save_settings)
        btn_box.addStretch()
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)
        
        # 信号连接与状态初始化
        self.radio_minimax.toggled.connect(self.update_ui_state)
        self.radio_custom.toggled.connect(self.update_ui_state)
        
        provider_type = self.config.get("provider_type", "minimax")
        if provider_type == "local":
            self.radio_custom.setChecked(True)
        else:
            self.radio_minimax.setChecked(True)
            
        self.update_ui_state()

    def update_ui_state(self):
        if self.radio_minimax.isChecked():
            self.stacked_widget.setCurrentWidget(self.page_minimax)
        elif self.radio_custom.isChecked():
            self.stacked_widget.setCurrentWidget(self.page_custom)

    def scan_custom_models(self):
        self.btn_custom_scan.setEnabled(False)
        self.btn_custom_scan.setText("扫描中...")
        self.scanner = ModelScannerWorker(self.input_custom_base.text().strip())
        self.scanner.scan_finished.connect(self.on_custom_scan_finished)
        self.scanner.start()
        
    def on_custom_scan_finished(self, models, error_msg):
        self.btn_custom_scan.setEnabled(True)
        self.btn_custom_scan.setText("🔍 探测模型")
        if error_msg:
            QMessageBox.critical(self, "探测失败", error_msg)
        else:
            self.combo_custom_model.clear()
            self.combo_custom_model.addItems(models)
            QMessageBox.information(self, "探测成功", "已更新本地 LLM 列表。")
            
    def save_settings(self):
        if self.radio_minimax.isChecked():
            provider_type = "minimax"
        else:
            provider_type = "local"
            
        self.config["provider_type"] = provider_type
        self.config["minimax_api_key"] = self.input_minimax_key.text().strip()
        self.config["local_api_base"] = self.input_custom_base.text().strip()
        self.config["local_model"] = self.combo_custom_model.currentText().strip()
        self.config["local_api_key"] = self.input_custom_key.text().strip()
        
        save_config(self.config)
        self.config_updated.emit()
        self.accept()
        QMessageBox.information(self, "成功", "配置已保存，下一次划词将生效！")

