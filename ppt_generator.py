import re
import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

def clean_markdown_bold(text):
    """移除 Markdown 中的加粗标记，避免显示在 PPT 中"""
    return re.sub(r'\*\*(.*?)\*\*', r'\1', text)

def generate_ppt_from_text(text, output_path="output.pptx"):
    """
    将 Markdown 文本转换为专业排版的 PPTX。
    支持：
    # 封面标题
    ## 页面标题
    ### 页面子标题 (加粗段落)
    - / * / 1. 列表内容
    """
    prs = Presentation()
    
    # 设置幻灯片尺寸为 16:9 宽屏比例
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    lines = text.split('\n')
    current_slide = None
    title_shape = None
    body_shape = None
    
    is_first_slide = True
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('# '):
            # 第一个遇到的 # 作为 PPT 封面 (Title Slide)
            # 后续的 # 作为带大标题的普通页 (Title and Content)
            layout_idx = 0 if is_first_slide else 1
            slide_layout = prs.slide_layouts[layout_idx]
            current_slide = prs.slides.add_slide(slide_layout)
            
            title_shape = current_slide.shapes.title
            if layout_idx == 0:
                body_shape = current_slide.placeholders[1]
            else:
                body_shape = current_slide.placeholders[1]
                
            raw_text = line[2:].strip()
            title_shape.text = clean_markdown_bold(raw_text)
            
            # 美化标题样式
            for p in title_shape.text_frame.paragraphs:
                p.font.bold = True
                if layout_idx == 0:
                    p.font.size = Pt(54)
                    p.font.color.rgb = RGBColor(0, 51, 102) # 深蓝色
                else:
                    p.font.size = Pt(40)
                    p.font.color.rgb = RGBColor(0, 51, 102)
            
            # 清空默认的 body 占位符内容
            if body_shape:
                body_shape.text = ""
                
            is_first_slide = False
            
        elif line.startswith('## '):
             # 二级标题作为新的一页 (Title and Content)
             slide_layout = prs.slide_layouts[1]
             current_slide = prs.slides.add_slide(slide_layout)
             title_shape = current_slide.shapes.title
             body_shape = current_slide.placeholders[1]
             
             raw_text = line[3:].strip()
             title_shape.text = clean_markdown_bold(raw_text)
             
             for p in title_shape.text_frame.paragraphs:
                 p.font.bold = True
                 p.font.size = Pt(36)
                 p.font.color.rgb = RGBColor(0, 102, 204) # 亮蓝色
                 
             body_shape.text = ""
             is_first_slide = False
             
        elif line.startswith('### '):
             # 三级标题作为页面内的加粗重点段落
             if current_slide and body_shape:
                 p = body_shape.text_frame.add_paragraph()
                 p.text = clean_markdown_bold(line[4:].strip())
                 p.font.bold = True
                 p.font.size = Pt(28)
                 p.font.color.rgb = RGBColor(51, 51, 51)
                 p.level = 0
                 
        elif line.startswith('- ') or line.startswith('* '):
            if current_slide and body_shape:
                p = body_shape.text_frame.add_paragraph()
                p.text = clean_markdown_bold(line[2:].strip())
                p.font.size = Pt(24)
                # 封面页无级别缩进，普通页有缩进
                p.level = 1 if current_slide.slide_layout.name != "Title Slide" else 0
                
        elif re.match(r'^\d+\.\s', line):
            if current_slide and body_shape:
                p = body_shape.text_frame.add_paragraph()
                p.text = clean_markdown_bold(re.sub(r'^\d+\.\s', '', line).strip())
                p.font.size = Pt(24)
                p.level = 1 if current_slide.slide_layout.name != "Title Slide" else 0
                
        else:
            # 普通文本
            if current_slide and body_shape:
                # 忽略代码块标记
                if line.startswith('```'):
                    continue
                p = body_shape.text_frame.add_paragraph()
                p.text = clean_markdown_bold(line)
                
                # 如果是在封面页，当作副标题处理（灰色居中）
                if current_slide.slide_layout.name == "Title Slide":
                    p.font.size = Pt(28)
                    p.font.color.rgb = RGBColor(102, 102, 102)
                    p.level = 0
                else:
                    p.font.size = Pt(22)
                    p.level = 1
                
    # 如果完全没有解析出幻灯片，兜底生成一页
    if len(prs.slides) == 0:
        slide_layout = prs.slide_layouts[1]
        current_slide = prs.slides.add_slide(slide_layout)
        title_shape = current_slide.shapes.title
        body_shape = current_slide.placeholders[1]
        
        title_shape.text = "自动生成的幻灯片"
        for p in title_shape.text_frame.paragraphs:
             p.font.bold = True
             p.font.color.rgb = RGBColor(0, 51, 102)
             
        body_shape.text = text[:1000] # 截断避免过长
        
    prs.save(output_path)
    return os.path.abspath(output_path)
