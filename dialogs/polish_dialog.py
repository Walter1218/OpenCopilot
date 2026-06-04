"""
润色专用界面
支持文本润色、风格选择、对比查看等功能
"""
from PyQt6.QtWidgets import *
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QComboBox, QGroupBox, QApplication, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class PolishDialog(QWidget):
    """润色专用界面"""
    
    # 信号定义
    polish_completed = pyqtSignal(str, str)  # 润色完成信号 (原文, 润色后)
    style_changed = pyqtSignal(str)  # 风格改变信号
    
    # 支持的润色风格
    POLISH_STYLES = {
        "formal": "正式",
        "casual": "随意",
        "concise": "简洁",
        "detailed": "详细",
        "academic": "学术",
        "business": "商务"
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("文本润色")
        self.setMinimumSize(800, 600)
        
        # 状态变量
        self.original_text = ""
        self.polished_text = ""
        self.polish_style = "formal"
        self.polish_history = []
        
        # 初始化UI
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """设置UI布局"""
        layout = QVBoxLayout(self)
        
        # 风格选择区域
        style_group = QGroupBox("润色风格")
        style_layout = QHBoxLayout(style_group)
        
        style_layout.addWidget(QLabel("选择风格:"))
        self.style_combo = QComboBox()
        for code, name in self.POLISH_STYLES.items():
            self.style_combo.addItem(name, code)
        style_layout.addWidget(self.style_combo)
        
        # 风格说明
        self.style_desc_label = QLabel("正式: 适合商务邮件、正式报告")
        self.style_desc_label.setStyleSheet("color: gray; font-style: italic;")
        style_layout.addWidget(self.style_desc_label)
        
        style_layout.addStretch()
        
        layout.addWidget(style_group)
        
        # 文本编辑区域
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 原始文本区域
        original_group = QGroupBox("原始文本")
        original_layout = QVBoxLayout(original_group)
        self.original_edit = QTextEdit()
        self.original_edit.setPlaceholderText("请输入要润色的文本...")
        original_layout.addWidget(self.original_edit)
        
        # 原始文本统计
        self.original_count_label = QLabel("字符数: 0 | 段落数: 0")
        self.original_count_label.setStyleSheet("color: gray;")
        original_layout.addWidget(self.original_count_label)
        
        splitter.addWidget(original_group)
        
        # 润色结果区域
        polished_group = QGroupBox("润色结果")
        polished_layout = QVBoxLayout(polished_group)
        self.polished_edit = QTextEdit()
        self.polished_edit.setReadOnly(True)
        self.polished_edit.setPlaceholderText("润色结果将显示在这里...")
        polished_layout.addWidget(self.polished_edit)
        
        # 润色结果统计
        self.polished_count_label = QLabel("字符数: 0 | 段落数: 0")
        self.polished_count_label.setStyleSheet("color: gray;")
        polished_layout.addWidget(self.polished_count_label)
        
        splitter.addWidget(polished_group)
        
        # 设置分割比例
        splitter.setSizes([400, 400])
        
        layout.addWidget(splitter)
        
        # 操作按钮区域
        button_layout = QHBoxLayout()
        
        self.polish_btn = QPushButton("润色")
        self.polish_btn.setDefault(True)
        button_layout.addWidget(self.polish_btn)
        
        self.compare_btn = QPushButton("对比")
        self.compare_btn.setEnabled(False)
        button_layout.addWidget(self.compare_btn)
        
        self.apply_btn = QPushButton("应用")
        self.apply_btn.setEnabled(False)
        button_layout.addWidget(self.apply_btn)
        
        self.clear_btn = QPushButton("清空")
        button_layout.addWidget(self.clear_btn)
        
        self.copy_btn = QPushButton("复制结果")
        self.copy_btn.setEnabled(False)
        button_layout.addWidget(self.copy_btn)
        
        layout.addLayout(button_layout)
        
        # 对比结果显示区域
        self.compare_group = QGroupBox("对比结果")
        compare_layout = QVBoxLayout(self.compare_group)
        self.compare_edit = QTextEdit()
        self.compare_edit.setReadOnly(True)
        self.compare_edit.setMaximumHeight(100)
        compare_layout.addWidget(self.compare_edit)
        
        layout.addWidget(self.compare_group)
        self.compare_group.hide()  # 默认隐藏
        
        # 状态栏
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.status_label)
    
    def connect_signals(self):
        """连接信号和槽"""
        self.polish_btn.clicked.connect(self.polish)
        self.compare_btn.clicked.connect(self.compare_texts)
        self.apply_btn.clicked.connect(self.apply_polish)
        self.clear_btn.clicked.connect(self.clear_all)
        self.copy_btn.clicked.connect(self.copy_result)
        self.original_edit.textChanged.connect(self.update_original_count)
        self.style_combo.currentIndexChanged.connect(self.on_style_changed)
    
    def set_original_text(self, text):
        """设置原始文本"""
        self.original_text = text
        self.original_edit.setPlainText(text)
    
    def set_polish_style(self, style):
        """设置润色风格"""
        if style not in self.POLISH_STYLES:
            return False
        
        self.polish_style = style
        
        # 更新下拉框
        index = self.style_combo.findData(style)
        if index >= 0:
            self.style_combo.setCurrentIndex(index)
        
        # 更新风格说明
        style_desc = {
            "formal": "正式: 适合商务邮件、正式报告",
            "casual": "随意: 适合日常交流、社交媒体",
            "concise": "简洁: 移除冗余，突出重点",
            "detailed": "详细: 补充细节，丰富内容",
            "academic": "学术: 适合论文、研究报告",
            "business": "商务: 适合商业文档、合同"
        }
        self.style_desc_label.setText(style_desc.get(style, ""))
        
        return True
    
    def polish(self):
        """执行润色"""
        self.original_text = self.original_edit.toPlainText().strip()
        
        if not self.original_text:
            self.status_label.setText("请输入要润色的文本")
            return False
        
        # 更新状态
        self.status_label.setText("正在润色...")
        self.polish_btn.setEnabled(False)
        
        try:
            # 这里应该调用实际的润色API
            # 暂时使用模拟润色
            self.polished_text = self._simulate_polish(
                self.original_text,
                self.polish_style
            )
            
            # 显示润色结果
            self.polished_edit.setPlainText(self.polished_text)
            
            # 启用按钮
            self.compare_btn.setEnabled(True)
            self.apply_btn.setEnabled(True)
            self.copy_btn.setEnabled(True)
            
            # 更新状态
            self.status_label.setText("润色完成")
            
            # 保存到历史记录
            self._save_to_history()
            
            # 发送信号
            self.polish_completed.emit(self.original_text, self.polished_text)
            
            return True
            
        except Exception as e:
            self.status_label.setText(f"润色失败: {str(e)}")
            return False
            
        finally:
            self.polish_btn.setEnabled(True)
    
    def _simulate_polish(self, text, style):
        """模拟润色（实际应用中应替换为真实API调用）"""
        # 简单的模拟润色逻辑
        if style == "formal":
            # 正式风格
            if "不太好" in text:
                return "本报告需要进一步完善，建议进行相应修改。"
            elif "问题" in text:
                return "该文档存在若干问题，需要进行修订。"
            else:
                return f"经过正式润色的文本: {text}"
        
        elif style == "casual":
            # 随意风格
            if "不太好" in text:
                return "这个报告得改改，有点问题。"
            elif "问题" in text:
                return "这文档有点问题，得修修。"
            else:
                return f"随意风格的文本: {text}"
        
        elif style == "concise":
            # 简洁风格
            if "不太好" in text:
                return "报告需修改。"
            elif "问题" in text:
                return "文档有问题。"
            else:
                return f"简洁版: {text[:50]}..."
        
        elif style == "detailed":
            # 详细风格
            if "不太好" in text:
                return "经过仔细分析，本报告在内容组织、逻辑结构和语言表达方面均存在不足之处，建议进行全面修订和完善。"
            elif "问题" in text:
                return "经过详细检查，发现该文档存在多个问题，包括格式不规范、内容不完整、逻辑不清晰等，需要逐项进行修正。"
            else:
                return f"详细润色后的文本: {text}"
        
        elif style == "academic":
            # 学术风格
            if "不太好" in text:
                return "本研究论文在方法论和数据分析方面存在不足，建议进行深入修订。"
            elif "问题" in text:
                return "该学术论文存在若干问题，需要进行严谨的学术审查和修改。"
            else:
                return f"学术风格的文本: {text}"
        
        elif style == "business":
            # 商务风格
            if "不太好" in text:
                return "尊敬的领导/同事，本报告需要进一步完善，建议安排时间进行讨论和修改。"
            elif "问题" in text:
                return "尊敬的领导/同事，该文档存在若干问题，需要及时处理。"
            else:
                return f"商务风格的文本: {text}"
        
        else:
            return f"润色后的文本: {text}"
    
    def compare_texts(self):
        """对比原始文本和润色后的文本"""
        if not self.original_text or not self.polished_text:
            return None
        
        # 计算变化
        original_length = len(self.original_text)
        polished_length = len(self.polished_text)
        length_change = polished_length - original_length
        length_change_percent = (length_change / original_length * 100) if original_length > 0 else 0
        
        # 生成对比结果
        compare_text = f"""
原始文本长度: {original_length} 字符
润色后长度: {polished_length} 字符
长度变化: {length_change} 字符 ({length_change_percent:.1f}%)

原始文本:
{self.original_text[:200]}{'...' if len(self.original_text) > 200 else ''}

润色后:
{self.polished_text[:200]}{'...' if len(self.polished_text) > 200 else ''}
"""
        
        # 显示对比结果
        self.compare_edit.setPlainText(compare_text)
        self.compare_group.show()
        
        return {
            "original_length": original_length,
            "polished_length": polished_length,
            "length_change": length_change,
            "length_change_percent": length_change_percent,
            "original": self.original_text,
            "polished": self.polished_text
        }
    
    def apply_polish(self):
        """应用润色结果"""
        if not self.polished_text:
            return False
        
        # 将润色结果设置为原始文本
        self.original_text = self.polished_text
        self.original_edit.setPlainText(self.polished_text)
        
        # 清空润色结果
        self.polished_text = ""
        self.polished_edit.clear()
        
        # 禁用按钮
        self.compare_btn.setEnabled(False)
        self.apply_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)
        
        # 隐藏对比结果
        self.compare_group.hide()
        
        # 更新状态
        self.status_label.setText("已应用润色结果")
        
        return True
    
    def clear_all(self):
        """清空所有内容"""
        self.original_text = ""
        self.polished_text = ""
        
        self.original_edit.clear()
        self.polished_edit.clear()
        self.compare_edit.clear()
        
        # 隐藏对比结果
        self.compare_group.hide()
        
        # 禁用按钮
        self.compare_btn.setEnabled(False)
        self.apply_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)
        
        # 更新状态
        self.status_label.setText("已清空")
    
    def copy_result(self):
        """复制润色结果"""
        if not self.polished_text:
            return
        
        clipboard = QApplication.clipboard()
        clipboard.setText(self.polished_text)
        
        # 更新状态
        self.status_label.setText("已复制到剪贴板")
    
    def _save_to_history(self):
        """保存润色到历史记录"""
        record = {
            "original": self.original_text,
            "polished": self.polished_text,
            "style": self.polish_style
        }
        
        self.polish_history.append(record)
        
        # 限制历史记录数量
        if len(self.polish_history) > 100:
            self.polish_history.pop(0)
    
    def update_original_count(self):
        """更新原始文本统计"""
        text = self.original_edit.toPlainText()
        self.original_text = text
        
        # 统计字符数和段落数
        char_count = len(text)
        paragraph_count = len([p for p in text.split('\n') if p.strip()])
        
        self.original_count_label.setText(f"字符数: {char_count} | 段落数: {paragraph_count}")
    
    def on_style_changed(self, index):
        """风格改变事件"""
        self.polish_style = self.style_combo.currentData()
        
        # 更新风格说明
        style_desc = {
            "formal": "正式: 适合商务邮件、正式报告",
            "casual": "随意: 适合日常交流、社交媒体",
            "concise": "简洁: 移除冗余，突出重点",
            "detailed": "详细: 补充细节，丰富内容",
            "academic": "学术: 适合论文、研究报告",
            "business": "商务: 适合商业文档、合同"
        }
        self.style_desc_label.setText(style_desc.get(self.polish_style, ""))
        
        # 发送信号
        self.style_changed.emit(self.polish_style)
    
    def get_original_text(self):
        """获取原始文本"""
        return self.original_text
    
    def get_polished_text(self):
        """获取润色后的文本"""
        return self.polished_text
    
    def get_polish_style(self):
        """获取润色风格"""
        return self.polish_style
    
    def get_polish_history(self):
        """获取润色历史"""
        return self.polish_history
