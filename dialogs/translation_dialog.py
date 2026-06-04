"""
翻译专用界面
支持多语言翻译、语言切换、翻译历史等功能
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QComboBox, QGroupBox, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class TranslationDialog(QWidget):
    """翻译专用界面"""
    
    # 信号定义
    translation_completed = pyqtSignal(str, str)  # 翻译完成信号 (原文, 译文)
    language_changed = pyqtSignal(str, str)  # 语言改变信号 (源语言, 目标语言)
    
    # 支持的语言
    SUPPORTED_LANGUAGES = {
        "zh": "中文",
        "en": "英文",
        "ja": "日文",
        "ko": "韩文",
        "fr": "法文",
        "de": "德文",
        "es": "西班牙文",
        "ru": "俄文"
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("翻译")
        self.setMinimumSize(900, 600)
        
        # 状态变量
        self.source_text = ""
        self.translated_text = ""
        self.source_lang = "zh"
        self.target_lang = "en"
        self.translation_history = []
        
        # 初始化UI
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """设置UI布局"""
        layout = QVBoxLayout(self)
        
        # 语言选择区域
        lang_group = QGroupBox("语言设置")
        lang_layout = QHBoxLayout(lang_group)
        
        # 源语言选择
        lang_layout.addWidget(QLabel("源语言:"))
        self.source_lang_combo = QComboBox()
        for code, name in self.SUPPORTED_LANGUAGES.items():
            self.source_lang_combo.addItem(name, code)
        lang_layout.addWidget(self.source_lang_combo)
        
        # 交换按钮
        self.swap_btn = QPushButton("⇄")
        self.swap_btn.setFixedSize(40, 30)
        self.swap_btn.setToolTip("交换语言")
        lang_layout.addWidget(self.swap_btn)
        
        # 目标语言选择
        lang_layout.addWidget(QLabel("目标语言:"))
        self.target_lang_combo = QComboBox()
        for code, name in self.SUPPORTED_LANGUAGES.items():
            self.target_lang_combo.addItem(name, code)
        self.target_lang_combo.setCurrentIndex(1)  # 默认选择英文
        lang_layout.addWidget(self.target_lang_combo)
        
        layout.addWidget(lang_group)
        
        # 文本输入区域
        text_group = QGroupBox("翻译内容")
        text_layout = QHBoxLayout(text_group)
        
        # 源文本区域
        source_group = QGroupBox("原文")
        source_layout = QVBoxLayout(source_group)
        self.source_edit = QTextEdit()
        self.source_edit.setPlaceholderText("请输入要翻译的文本...")
        self.source_edit.setMaximumHeight(200)
        source_layout.addWidget(self.source_edit)
        
        # 源文本统计
        self.source_count_label = QLabel("字符数: 0")
        self.source_count_label.setStyleSheet("color: gray;")
        source_layout.addWidget(self.source_count_label)
        
        text_layout.addWidget(source_group)
        
        # 翻译结果区域
        target_group = QGroupBox("译文")
        target_layout = QVBoxLayout(target_group)
        self.target_edit = QTextEdit()
        self.target_edit.setReadOnly(True)
        self.target_edit.setPlaceholderText("翻译结果将显示在这里...")
        self.target_edit.setMaximumHeight(200)
        target_layout.addWidget(self.target_edit)
        
        # 目标文本统计
        self.target_count_label = QLabel("字符数: 0")
        self.target_count_label.setStyleSheet("color: gray;")
        target_layout.addWidget(self.target_count_label)
        
        text_layout.addWidget(target_group)
        
        layout.addWidget(text_group)
        
        # 操作按钮区域
        button_layout = QHBoxLayout()
        
        self.translate_btn = QPushButton("翻译")
        self.translate_btn.setDefault(True)
        button_layout.addWidget(self.translate_btn)
        
        self.clear_btn = QPushButton("清空")
        button_layout.addWidget(self.clear_btn)
        
        self.copy_btn = QPushButton("复制译文")
        self.copy_btn.setEnabled(False)
        button_layout.addWidget(self.copy_btn)
        
        self.history_btn = QPushButton("历史记录")
        button_layout.addWidget(self.history_btn)
        
        layout.addLayout(button_layout)
        
        # 状态栏
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.status_label)
    
    def connect_signals(self):
        """连接信号和槽"""
        self.translate_btn.clicked.connect(self.translate)
        self.swap_btn.clicked.connect(self.swap_languages)
        self.clear_btn.clicked.connect(self.clear_all)
        self.copy_btn.clicked.connect(self.copy_translation)
        self.history_btn.clicked.connect(self.show_history)
        self.source_edit.textChanged.connect(self.update_source_count)
        self.target_edit.textChanged.connect(self.update_target_count)
        self.source_lang_combo.currentIndexChanged.connect(self.on_source_lang_changed)
        self.target_lang_combo.currentIndexChanged.connect(self.on_target_lang_changed)
    
    def set_source_text(self, text):
        """设置源文本"""
        self.source_text = text
        self.source_edit.setPlainText(text)
    
    def set_languages(self, source_lang, target_lang):
        """设置语言"""
        self.source_lang = source_lang
        self.target_lang = target_lang
        
        # 更新下拉框
        source_index = self.source_lang_combo.findData(source_lang)
        if source_index >= 0:
            self.source_lang_combo.setCurrentIndex(source_index)
        
        target_index = self.target_lang_combo.findData(target_lang)
        if target_index >= 0:
            self.target_lang_combo.setCurrentIndex(target_index)
    
    def translate(self):
        """执行翻译（通过 Agent Pipeline 调用 LLM）"""
        self.source_text = self.source_edit.toPlainText().strip()
        
        if not self.source_text:
            self.status_label.setText("请输入要翻译的文本")
            return False
        
        # 更新状态
        self.status_label.setText("正在翻译...")
        self.translate_btn.setEnabled(False)
        QApplication.processEvents()
        
        try:
            self.translated_text = self._do_translate(
                self.source_text,
                self.source_lang,
                self.target_lang
            )
            
            # 显示翻译结果
            self.target_edit.setPlainText(self.translated_text)
            self.copy_btn.setEnabled(True)
            self.status_label.setText("翻译完成")
            
            # 保存到历史记录
            self._save_to_history()
            self.translation_completed.emit(self.source_text, self.translated_text)
            
            return True
            
        except Exception as e:
            self.status_label.setText(f"翻译失败: {str(e)}")
            return False
            
        finally:
            self.translate_btn.setEnabled(True)
    
    def _do_translate(self, text, source_lang, target_lang):
        """通过 Agent Pipeline 执行真实翻译"""
        # 构建翻译 prompt（与 API /api/text/translate 保持一致）
        lang_map = {
            "zh": "中文", "en": "英文", "ja": "日文",
            "ko": "韩文", "fr": "法文", "de": "德文",
            "es": "西班牙文", "ru": "俄文",
        }
        target_name = lang_map.get(target_lang, target_lang)
        prompt = f"请将以下文本翻译成{target_name}：\n\n{text}"
        
        # 调用 Agent Pipeline（同步生成器，内部 daemon 线程跑 async）
        from opencopilot.agent.caller import call_agent_pipeline_sync
        
        chunks = []
        try:
            for chunk in call_agent_pipeline_sync(
                text=prompt,
                action_type="translate",
                context_source="chat",
                context_meta={"task": "translate", "source_lang": source_lang, "target_lang": target_lang},
                timeout=60.0,
            ):
                chunks.append(chunk)
        except Exception:
            # Pipeline 失败时回退到简单提示
            return f"[翻译失败] 请检查 Agent 服务是否正常运行。\n原文: {text}"
        
        result = "".join(chunks).strip()
        
        # 如果 LLM 不可用，返回明确提示
        if not result:
            return f"[翻译服务暂不可用]\n原文: {text}"
        
        return result
    
    def swap_languages(self):
        """交换语言和文本"""
        # 交换语言
        self.source_lang, self.target_lang = self.target_lang, self.source_lang
        
        # 更新下拉框
        source_index = self.source_lang_combo.findData(self.source_lang)
        target_index = self.target_lang_combo.findData(self.target_lang)
        
        if source_index >= 0:
            self.source_lang_combo.setCurrentIndex(source_index)
        if target_index >= 0:
            self.target_lang_combo.setCurrentIndex(target_index)
        
        # 交换文本
        self.source_text, self.translated_text = self.translated_text, self.source_text
        
        # 更新显示
        self.source_edit.setPlainText(self.source_text)
        self.target_edit.setPlainText(self.translated_text)
        
        # 发送信号
        self.language_changed.emit(self.source_lang, self.target_lang)
    
    def clear_all(self):
        """清空所有内容"""
        self.source_text = ""
        self.translated_text = ""
        
        self.source_edit.clear()
        self.target_edit.clear()
        
        # 禁用复制按钮
        self.copy_btn.setEnabled(False)
        
        # 更新状态
        self.status_label.setText("已清空")
    
    def copy_translation(self):
        """复制翻译结果"""
        if not self.translated_text:
            return
        
        clipboard = QApplication.clipboard()
        clipboard.setText(self.translated_text)
        
        # 更新状态
        self.status_label.setText("已复制到剪贴板")
    
    def show_history(self):
        """显示翻译历史"""
        if not self.translation_history:
            self.status_label.setText("暂无翻译历史")
            return
        
        # 这里应该弹出历史记录对话框
        # 暂时显示最后一条记录
        last_record = self.translation_history[-1]
        self.status_label.setText(
            f"最近翻译: {last_record['source'][:20]}... -> {last_record['target'][:20]}..."
        )
    
    def _save_to_history(self):
        """保存翻译到历史记录"""
        record = {
            "source": self.source_text,
            "target": self.translated_text,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang
        }
        
        self.translation_history.append(record)
        
        # 限制历史记录数量
        if len(self.translation_history) > 100:
            self.translation_history.pop(0)
    
    def update_source_count(self):
        """更新源文本字符数"""
        text = self.source_edit.toPlainText()
        self.source_text = text
        self.source_count_label.setText(f"字符数: {len(text)}")
    
    def update_target_count(self):
        """更新目标文本字符数"""
        text = self.target_edit.toPlainText()
        self.target_count_label.setText(f"字符数: {len(text)}")
    
    def on_source_lang_changed(self, index):
        """源语言改变事件"""
        self.source_lang = self.source_lang_combo.currentData()
        self.language_changed.emit(self.source_lang, self.target_lang)
    
    def on_target_lang_changed(self, index):
        """目标语言改变事件"""
        self.target_lang = self.target_lang_combo.currentData()
        self.language_changed.emit(self.source_lang, self.target_lang)
    
    def get_source_text(self):
        """获取源文本"""
        return self.source_text
    
    def get_translated_text(self):
        """获取翻译文本"""
        return self.translated_text
    
    def get_source_lang(self):
        """获取源语言"""
        return self.source_lang
    
    def get_target_lang(self):
        """获取目标语言"""
        return self.target_lang
    
    def get_translation_history(self):
        """获取翻译历史"""
        return self.translation_history
