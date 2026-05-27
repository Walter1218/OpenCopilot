"""
个性化设置对话框
支持外观、行为、办公场景等设置
"""
import json
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QFormLayout, QLabel, QComboBox, QSpinBox, QCheckBox,
    QPushButton, QGroupBox, QSlider, QLineEdit, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class SettingsDialog(QDialog):
    """个性化设置对话框"""
    
    # 信号定义
    settings_changed = pyqtSignal(dict)  # 设置改变信号
    
    # 默认设置
    DEFAULT_SETTINGS = {
        "theme": "dark",
        "font_size": 12,
        "font_family": "Arial",
        "auto_save": True,
        "auto_translate": False,
        "show_shortcuts": True,
        "language": "zh",
        "office_mode": False,
        "recent_files_limit": 10,
        "default_export_format": "docx"
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("个性化设置")
        self.setMinimumSize(600, 500)
        
        # 设置数据
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.settings_file = "settings.json"
        
        # 初始化UI
        self.setup_ui()
        
        # 加载设置
        self.load_settings()
    
    def setup_ui(self):
        """设置UI布局"""
        layout = QVBoxLayout(self)
        
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 外观设置
        self.appearance_tab = self._create_appearance_tab()
        self.tabs.addTab(self.appearance_tab, "外观")
        
        # 行为设置
        self.behavior_tab = self._create_behavior_tab()
        self.tabs.addTab(self.behavior_tab, "行为")
        
        # 办公设置
        self.office_tab = self._create_office_tab()
        self.tabs.addTab(self.office_tab, "办公")
        
        # 高级设置
        self.advanced_tab = self._create_advanced_tab()
        self.tabs.addTab(self.advanced_tab, "高级")
        
        layout.addWidget(self.tabs)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.apply_btn = QPushButton("应用")
        self.apply_btn.clicked.connect(self.apply_settings)
        button_layout.addWidget(self.apply_btn)
        
        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.reset_btn = QPushButton("重置默认")
        self.reset_btn.clicked.connect(self.reset_to_default)
        button_layout.addWidget(self.reset_btn)
        
        layout.addLayout(button_layout)
    
    def _create_appearance_tab(self):
        """创建外观设置标签页"""
        tab = QWidget()
        layout = QFormLayout(tab)
        
        # 主题设置
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["暗色", "亮色", "办公"])
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        layout.addRow("主题:", self.theme_combo)
        
        # 字体大小
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(12)
        self.font_size_spin.valueChanged.connect(self._on_font_size_changed)
        layout.addRow("字体大小:", self.font_size_spin)
        
        # 字体族
        self.font_family_combo = QComboBox()
        self.font_family_combo.addItems(["Arial", "Times New Roman", "Courier New", "SimSun", "SimHei"])
        self.font_family_combo.currentTextChanged.connect(self._on_font_family_changed)
        layout.addRow("字体:", self.font_family_combo)
        
        # 显示快捷键
        self.show_shortcuts_check = QCheckBox("在菜单中显示快捷键")
        self.show_shortcuts_check.stateChanged.connect(self._on_show_shortcuts_changed)
        layout.addRow("快捷键:", self.show_shortcuts_check)
        
        return tab
    
    def _create_behavior_tab(self):
        """创建行为设置标签页"""
        tab = QWidget()
        layout = QFormLayout(tab)
        
        # 自动保存
        self.auto_save_check = QCheckBox("自动保存文档")
        self.auto_save_check.stateChanged.connect(self._on_auto_save_changed)
        layout.addRow("自动保存:", self.auto_save_check)
        
        # 自动翻译
        self.auto_translate_check = QCheckBox("自动翻译复制的文本")
        self.auto_translate_check.stateChanged.connect(self._on_auto_translate_changed)
        layout.addRow("自动翻译:", self.auto_translate_check)
        
        # 语言设置
        self.language_combo = QComboBox()
        self.language_combo.addItems(["中文", "English", "日本語", "한국어"])
        self.language_combo.currentTextChanged.connect(self._on_language_changed)
        layout.addRow("界面语言:", self.language_combo)
        
        # 最近文件数量
        self.recent_files_spin = QSpinBox()
        self.recent_files_spin.setRange(5, 50)
        self.recent_files_spin.setValue(10)
        self.recent_files_spin.valueChanged.connect(self._on_recent_files_changed)
        layout.addRow("最近文件数:", self.recent_files_spin)
        
        return tab
    
    def _create_office_tab(self):
        """创建办公设置标签页"""
        tab = QWidget()
        layout = QFormLayout(tab)
        
        # 办公模式
        self.office_mode_check = QCheckBox("启用办公模式")
        self.office_mode_check.stateChanged.connect(self._on_office_mode_changed)
        layout.addRow("办公模式:", self.office_mode_check)
        
        # 默认导出格式
        self.export_format_combo = QComboBox()
        self.export_format_combo.addItems(["docx", "pdf", "txt", "md"])
        self.export_format_combo.currentTextChanged.connect(self._on_export_format_changed)
        layout.addRow("默认导出格式:", self.export_format_combo)
        
        # 默认翻译语言
        self.default_translate_combo = QComboBox()
        self.default_translate_combo.addItems(["中文→英文", "英文→中文", "中文→日文", "日文→中文"])
        self.default_translate_combo.currentTextChanged.connect(self._on_default_translate_changed)
        layout.addRow("默认翻译:", self.default_translate_combo)
        
        return tab
    
    def _create_advanced_tab(self):
        """创建高级设置标签页"""
        tab = QWidget()
        layout = QFormLayout(tab)
        
        # 配置文件路径
        self.config_path_edit = QLineEdit()
        self.config_path_edit.setReadOnly(True)
        layout.addRow("配置文件:", self.config_path_edit)
        
        # 导出配置
        export_layout = QHBoxLayout()
        self.export_btn = QPushButton("导出配置")
        self.export_btn.clicked.connect(self.export_settings)
        export_layout.addWidget(self.export_btn)
        
        self.import_btn = QPushButton("导入配置")
        self.import_btn.clicked.connect(self.import_settings)
        export_layout.addWidget(self.import_btn)
        
        layout.addRow("配置管理:", export_layout)
        
        return tab
    
    def _on_theme_changed(self, theme_text):
        """主题改变事件"""
        theme_map = {"暗色": "dark", "亮色": "light", "办公": "office"}
        self.settings["theme"] = theme_map.get(theme_text, "dark")
    
    def _on_font_size_changed(self, size):
        """字体大小改变事件"""
        self.settings["font_size"] = size
    
    def _on_font_family_changed(self, family):
        """字体族改变事件"""
        self.settings["font_family"] = family
    
    def _on_show_shortcuts_changed(self, state):
        """显示快捷键改变事件"""
        self.settings["show_shortcuts"] = state == Qt.CheckState.Checked.value
    
    def _on_auto_save_changed(self, state):
        """自动保存改变事件"""
        self.settings["auto_save"] = state == Qt.CheckState.Checked.value
    
    def _on_auto_translate_changed(self, state):
        """自动翻译改变事件"""
        self.settings["auto_translate"] = state == Qt.CheckState.Checked.value
    
    def _on_language_changed(self, language_text):
        """语言改变事件"""
        language_map = {"中文": "zh", "English": "en", "日本語": "ja", "한국어": "ko"}
        self.settings["language"] = language_map.get(language_text, "zh")
    
    def _on_recent_files_changed(self, value):
        """最近文件数改变事件"""
        self.settings["recent_files_limit"] = value
    
    def _on_office_mode_changed(self, state):
        """办公模式改变事件"""
        self.settings["office_mode"] = state == Qt.CheckState.Checked.value
    
    def _on_export_format_changed(self, format_text):
        """导出格式改变事件"""
        self.settings["default_export_format"] = format_text
    
    def _on_default_translate_changed(self, translate_text):
        """默认翻译改变事件"""
        # 这里可以保存翻译方向
        pass
    
    def load_settings(self):
        """加载设置"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    self.settings.update(loaded_settings)
            except Exception as e:
                print(f"加载设置失败: {e}")
        
        # 更新UI
        self._update_ui_from_settings()
    
    def save_settings(self):
        """保存设置"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存设置失败: {e}")
            return False
    
    def _update_ui_from_settings(self):
        """根据设置更新UI"""
        # 主题
        theme_map = {"dark": "暗色", "light": "亮色", "office": "办公"}
        theme_text = theme_map.get(self.settings["theme"], "暗色")
        self.theme_combo.setCurrentText(theme_text)
        
        # 字体大小
        self.font_size_spin.setValue(self.settings["font_size"])
        
        # 字体族
        self.font_family_combo.setCurrentText(self.settings["font_family"])
        
        # 显示快捷键
        self.show_shortcuts_check.setChecked(self.settings["show_shortcuts"])
        
        # 自动保存
        self.auto_save_check.setChecked(self.settings["auto_save"])
        
        # 自动翻译
        self.auto_translate_check.setChecked(self.settings["auto_translate"])
        
        # 语言
        language_map = {"zh": "中文", "en": "English", "ja": "日本語", "ko": "한국어"}
        language_text = language_map.get(self.settings["language"], "中文")
        self.language_combo.setCurrentText(language_text)
        
        # 最近文件数
        self.recent_files_spin.setValue(self.settings["recent_files_limit"])
        
        # 办公模式
        self.office_mode_check.setChecked(self.settings["office_mode"])
        
        # 导出格式
        self.export_format_combo.setCurrentText(self.settings["default_export_format"])
        
        # 配置文件路径
        self.config_path_edit.setText(os.path.abspath(self.settings_file))
    
    def apply_settings(self):
        """应用设置"""
        if self.save_settings():
            self.settings_changed.emit(self.settings)
            QMessageBox.information(self, "成功", "设置已保存")
        else:
            QMessageBox.warning(self, "错误", "保存设置失败")
    
    def accept(self):
        """确定"""
        self.apply_settings()
        super().accept()
    
    def reset_to_default(self):
        """重置为默认设置"""
        reply = QMessageBox.question(
            self,
            "确认重置",
            "确定要重置所有设置为默认值吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.settings = self.DEFAULT_SETTINGS.copy()
            self._update_ui_from_settings()
            QMessageBox.information(self, "成功", "设置已重置为默认值")
    
    def export_settings(self):
        """导出设置"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出设置",
            "",
            "JSON文件 (*.json)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.settings, f, indent=2, ensure_ascii=False)
                QMessageBox.information(self, "成功", f"设置已导出到: {file_path}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"导出失败: {e}")
    
    def import_settings(self):
        """导入设置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入设置",
            "",
            "JSON文件 (*.json)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    imported_settings = json.load(f)
                    self.settings.update(imported_settings)
                    self._update_ui_from_settings()
                QMessageBox.information(self, "成功", "设置已导入")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"导入失败: {e}")
    
    def get_settings(self):
        """获取当前设置"""
        return self.settings.copy()
    
    def set_setting(self, key, value):
        """设置单个设置项"""
        self.settings[key] = value
        self._update_ui_from_settings()
    
    def get_setting(self, key):
        """获取单个设置项"""
        return self.settings.get(key)
