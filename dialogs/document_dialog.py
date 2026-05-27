"""
文档处理专用界面
支持文档加载、内容提取、格式转换等功能
"""
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QFileDialog, QMessageBox, QComboBox, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class DocumentDialog(QWidget):
    """文档处理专用界面"""
    
    # 信号定义
    document_loaded = pyqtSignal(str)  # 文档加载信号
    content_extracted = pyqtSignal(str)  # 内容提取信号
    document_saved = pyqtSignal(str)  # 文档保存信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("文档处理")
        self.setMinimumSize(800, 600)
        
        # 状态变量
        self.file_path = None
        self.content = None
        self.extracted_content = None
        
        # 初始化UI
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """设置UI布局"""
        layout = QVBoxLayout(self)
        
        # 文件选择区域
        file_group = QGroupBox("文件选择")
        file_layout = QHBoxLayout(file_group)
        
        self.file_label = QLabel("未选择文件")
        self.file_label.setStyleSheet("color: gray; font-style: italic;")
        file_layout.addWidget(self.file_label)
        
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.setFixedWidth(80)
        file_layout.addWidget(self.browse_btn)
        
        layout.addWidget(file_group)
        
        # 内容提取设置区域
        extract_group = QGroupBox("内容提取设置")
        extract_layout = QHBoxLayout(extract_group)
        
        extract_layout.addWidget(QLabel("提取类型:"))
        self.extract_type_combo = QComboBox()
        self.extract_type_combo.addItems(["全部内容", "仅标题", "仅段落", "自定义"])
        extract_layout.addWidget(self.extract_type_combo)
        
        extract_layout.addWidget(QLabel("输出格式:"))
        self.output_format_combo = QComboBox()
        self.output_format_combo.addItems(["Markdown", "纯文本", "HTML"])
        extract_layout.addWidget(self.output_format_combo)
        
        layout.addWidget(extract_group)
        
        # 内容显示区域
        content_group = QGroupBox("文档内容")
        content_layout = QVBoxLayout(content_group)
        
        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("文档内容将显示在这里...")
        content_layout.addWidget(self.content_edit)
        
        layout.addWidget(content_group)
        
        # 操作按钮区域
        button_layout = QHBoxLayout()
        
        self.extract_btn = QPushButton("提取内容")
        self.extract_btn.setEnabled(False)
        button_layout.addWidget(self.extract_btn)
        
        self.convert_btn = QPushButton("格式转换")
        self.convert_btn.setEnabled(False)
        button_layout.addWidget(self.convert_btn)
        
        self.save_btn = QPushButton("保存")
        self.save_btn.setEnabled(False)
        button_layout.addWidget(self.save_btn)
        
        self.clear_btn = QPushButton("清空")
        button_layout.addWidget(self.clear_btn)
        
        layout.addLayout(button_layout)
        
        # 状态栏
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.status_label)
    
    def connect_signals(self):
        """连接信号和槽"""
        self.browse_btn.clicked.connect(self.browse_file)
        self.extract_btn.clicked.connect(self.extract_content)
        self.convert_btn.clicked.connect(self.convert_format)
        self.save_btn.clicked.connect(self.save_document)
        self.clear_btn.clicked.connect(self.clear_content)
        self.extract_type_combo.currentTextChanged.connect(self.on_extract_type_changed)
    
    def browse_file(self):
        """浏览并选择文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择文档文件",
            "",
            "文档文件 (*.txt *.md *.docx *.pdf);;所有文件 (*)"
        )
        
        if file_path:
            self.load_document(file_path)
    
    def load_document(self, file_path):
        """加载文档内容"""
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "错误", f"文件不存在: {file_path}")
            return False
        
        try:
            # 根据文件类型读取内容
            if file_path.endswith('.txt') or file_path.endswith('.md'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.content = f.read()
            elif file_path.endswith('.docx'):
                # 这里需要集成python-docx库
                # 暂时使用模拟
                self.content = f"[DOCX文件内容模拟] {file_path}"
            elif file_path.endswith('.pdf'):
                # 这里需要集成PyPDF2库
                # 暂时使用模拟
                self.content = f"[PDF文件内容模拟] {file_path}"
            else:
                QMessageBox.warning(self, "错误", f"不支持的文件格式: {file_path}")
                return False
            
            self.file_path = file_path
            self.file_label.setText(os.path.basename(file_path))
            self.file_label.setStyleSheet("color: black;")
            self.content_edit.setPlainText(self.content)
            
            # 启用按钮
            self.extract_btn.setEnabled(True)
            self.convert_btn.setEnabled(True)
            self.save_btn.setEnabled(True)
            
            # 更新状态
            self.status_label.setText(f"已加载: {os.path.basename(file_path)}")
            
            # 发送信号
            self.document_loaded.emit(file_path)
            
            return True
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载文件失败: {str(e)}")
            return False
    
    def extract_content(self):
        """提取文档内容"""
        if not self.content:
            QMessageBox.warning(self, "警告", "没有可提取的内容")
            return
        
        extract_type = self.extract_type_combo.currentText()
        
        if extract_type == "全部内容":
            self.extracted_content = self.content
        elif extract_type == "仅标题":
            lines = self.content.split('\n')
            headings = [line for line in lines if line.startswith('#')]
            self.extracted_content = '\n'.join(headings)
        elif extract_type == "仅段落":
            lines = self.content.split('\n')
            paragraphs = [line for line in lines if line.strip() and not line.startswith('#')]
            self.extracted_content = '\n'.join(paragraphs)
        else:
            # 自定义提取逻辑
            self.extracted_content = self.content
        
        # 显示提取结果
        self.content_edit.setPlainText(self.extracted_content)
        
        # 更新状态
        self.status_label.setText(f"已提取内容 ({len(self.extracted_content)} 字符)")
        
        # 发送信号
        self.content_extracted.emit(self.extracted_content)
    
    def convert_format(self):
        """转换文档格式"""
        if not self.content:
            QMessageBox.warning(self, "警告", "没有可转换的内容")
            return
        
        output_format = self.output_format_combo.currentText()
        
        if output_format == "Markdown":
            converted_content = self.content
        elif output_format == "纯文本":
            # 移除Markdown格式
            lines = self.content.split('\n')
            plain_lines = []
            for line in lines:
                # 移除标题标记
                if line.startswith('#'):
                    line = line.lstrip('#').strip()
                # 移除加粗和斜体
                line = line.replace('**', '').replace('*', '')
                plain_lines.append(line)
            converted_content = '\n'.join(plain_lines)
        elif output_format == "HTML":
            # 简单的Markdown到HTML转换
            converted_content = self._markdown_to_html(self.content)
        else:
            converted_content = self.content
        
        # 显示转换结果
        self.content_edit.setPlainText(converted_content)
        
        # 更新状态
        self.status_label.setText(f"已转换为 {output_format} 格式")
    
    def _markdown_to_html(self, markdown_text):
        """简单的Markdown到HTML转换"""
        html_lines = []
        lines = markdown_text.split('\n')
        
        for line in lines:
            # 标题转换
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                title = line.lstrip('#').strip()
                html_lines.append(f"<h{level}>{title}</h{level}>")
            # 列表转换
            elif line.startswith('- ') or line.startswith('* '):
                item = line[2:].strip()
                html_lines.append(f"<li>{item}</li>")
            # 普通段落
            elif line.strip():
                html_lines.append(f"<p>{line}</p>")
        
        return '\n'.join(html_lines)
    
    def save_document(self):
        """保存文档"""
        if not self.content and not self.extracted_content:
            QMessageBox.warning(self, "警告", "没有可保存的内容")
            return
        
        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存文档",
            "",
            "文本文件 (*.txt);;Markdown文件 (*.md);;所有文件 (*)"
        )
        
        if file_path:
            try:
                content_to_save = self.extracted_content if self.extracted_content else self.content
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content_to_save)
                
                # 更新状态
                self.status_label.setText(f"已保存: {os.path.basename(file_path)}")
                
                # 发送信号
                self.document_saved.emit(file_path)
                
                QMessageBox.information(self, "成功", f"文档已保存到: {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存文件失败: {str(e)}")
    
    def clear_content(self):
        """清空内容"""
        self.content = None
        self.extracted_content = None
        self.file_path = None
        
        self.file_label.setText("未选择文件")
        self.file_label.setStyleSheet("color: gray; font-style: italic;")
        self.content_edit.clear()
        
        # 禁用按钮
        self.extract_btn.setEnabled(False)
        self.convert_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        
        # 更新状态
        self.status_label.setText("已清空")
    
    def on_extract_type_changed(self, extract_type):
        """提取类型改变事件"""
        if extract_type == "自定义":
            # 这里可以弹出自定义提取对话框
            pass
    
    def get_content(self):
        """获取当前内容"""
        return self.content
    
    def get_extracted_content(self):
        """获取提取的内容"""
        return self.extracted_content
    
    def get_file_path(self):
        """获取文件路径"""
        return self.file_path
    
    def set_content(self, content):
        """设置内容"""
        self.content = content
        self.content_edit.setPlainText(content)
        
        # 启用按钮
        self.extract_btn.setEnabled(True)
        self.convert_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
