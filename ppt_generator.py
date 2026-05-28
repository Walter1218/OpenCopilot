import re
import os
from pptx import Presentation
from pptx.util import Inches, Pt

def generate_ppt_from_text(text, output_path="output.pptx"):
    """
    极简的从 Markdown 提取标题和列表并生成 PPT 的工具。
    期待大模型输出格式：
    # 第一页标题
    - 内容点1
    - 内容点2
    
    # 第二页标题
    - 内容点1
    """
    prs = Presentation()
    
    # 用简单的正则或按行解析
    lines = text.split('\n')
    current_slide = None
    title_shape = None
    body_shape = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('# '):
            # 新的一页 (Title Slide)
            slide_layout = prs.slide_layouts[1] # Title and Content
            current_slide = prs.slides.add_slide(slide_layout)
            title_shape = current_slide.shapes.title
            body_shape = current_slide.placeholders[1]
            title_shape.text = line[2:].strip()
            # clear the default text in body
            body_shape.text = ""
        elif line.startswith('## '):
             if not current_slide:
                 slide_layout = prs.slide_layouts[1]
                 current_slide = prs.slides.add_slide(slide_layout)
                 title_shape = current_slide.shapes.title
                 body_shape = current_slide.placeholders[1]
                 title_shape.text = line[3:].strip()
                 body_shape.text = ""
             else:
                 if body_shape:
                     p = body_shape.text_frame.add_paragraph()
                     p.text = line[3:].strip()
                     p.font.bold = True
                     p.level = 0
        elif line.startswith('- ') or line.startswith('* '):
            if current_slide and body_shape:
                p = body_shape.text_frame.add_paragraph()
                p.text = line[2:].strip()
                p.level = 1 if current_slide else 0
        elif re.match(r'^\d+\.\s', line):
            if current_slide and body_shape:
                p = body_shape.text_frame.add_paragraph()
                p.text = re.sub(r'^\d+\.\s', '', line).strip()
                p.level = 1 if current_slide else 0
        else:
            # 普通文本
            if current_slide and body_shape:
                # 忽略代码块标记
                if line.startswith('```'):
                    continue
                p = body_shape.text_frame.add_paragraph()
                p.text = line
                p.level = 1 if current_slide else 0
                
    # 如果完全没有解析出幻灯片，可能大模型没有按格式输出，我们强行生成一页
    if len(prs.slides) == 0:
        slide_layout = prs.slide_layouts[1]
        current_slide = prs.slides.add_slide(slide_layout)
        title_shape = current_slide.shapes.title
        body_shape = current_slide.placeholders[1]
        title_shape.text = "生成的幻灯片"
        body_shape.text = text[:1000] # 截断避免过长
        
    prs.save(output_path)
    return os.path.abspath(output_path)
