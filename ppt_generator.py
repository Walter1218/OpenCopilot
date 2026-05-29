import re
import os
import urllib.request
from io import BytesIO
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def clean_markdown_bold(text):
    """移除 Markdown 中的加粗标记"""
    return re.sub(r'\*\*(.*?)\*\*', r'\1', text)

def add_decorative_shape(slide, prs):
    """为封面添加装饰性几何图形"""
    # 在左侧添加一个蓝色的竖条
    left = Inches(0)
    top = Inches(0)
    width = Inches(0.3)
    height = prs.slide_height
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor(0, 102, 204)
    shape.line.fill.background()

def add_placeholder_image(slide, prs):
    """为内容页右侧添加本地生成的装饰性占位图形，避免网络请求导致卡顿"""
    try:
        # 使用几何图形拼接出具有设计感的占位图
        img_width = Inches(4.5)
        img_height = prs.slide_height
        left = prs.slide_width - img_width
        top = Inches(0)
        
        # 底部浅灰蓝色大色块
        shape1 = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, img_width, img_height)
        shape1.fill.solid()
        shape1.fill.fore_color.rgb = RGBColor(235, 240, 245)
        shape1.line.fill.background()
        
        # 叠加深蓝色强调色块
        shape2 = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left + Inches(0.5), top + Inches(1.5), img_width - Inches(1.0), Inches(4.5))
        shape2.fill.solid()
        shape2.fill.fore_color.rgb = RGBColor(0, 102, 204)
        shape2.line.fill.background()
        
        # 叠加半透明点缀
        shape3 = slide.shapes.add_shape(MSO_SHAPE.OVAL, left + Inches(3.0), top + Inches(4.5), Inches(2.0), Inches(2.0))
        shape3.fill.solid()
        shape3.fill.fore_color.rgb = RGBColor(255, 153, 51)
        shape3.line.fill.background()
        
        return True
    except Exception as e:
        print(f"Failed to add placeholder shapes: {e}")
        return False

def generate_ppt_from_text(text, output_path="output.pptx"):
    prs = Presentation()
    
    # 设置为 16:9 宽屏比例
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    lines = text.split('\n')
    current_slide = None
    title_shape = None
    body_shape = None
    
    is_first_slide = True
    
    # 强制分块逻辑：单页内容超过 6 行自动分页
    slide_content_count = 0  # 记录当前页的内容行数，过多则自动分页
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 判断是否应该开启新一页：遇到一级/二级标题，或中文大写序号，或单页内容超过 6 行
        is_new_slide_marker = line.startswith('# ') or line.startswith('## ') or re.match(r'^[一二三四五六七八九十]+、', line)
        
        # 如果当前没有 current_slide，无论如何都需要新建一页
        if current_slide is None or slide_content_count >= 6 or is_new_slide_marker:
            
            layout_idx = 0 if is_first_slide else 1
            current_slide = prs.slides.add_slide(prs.slide_layouts[layout_idx])
            slide_content_count = 0
            
            title_shape = current_slide.shapes.title
            body_shape = current_slide.placeholders[1]
            
            if is_new_slide_marker:
                raw_text = re.sub(r'^#+\s*', '', line).strip()  # 移除 # 标记
                title_shape.text = clean_markdown_bold(raw_text)
            else:
                title_shape.text = "续前页"
            
            # 美化标题
            for p in title_shape.text_frame.paragraphs:
                p.font.bold = True
                if layout_idx == 0:
                    p.font.size = Pt(54)
                    p.font.color.rgb = RGBColor(0, 51, 102)
                    add_decorative_shape(current_slide, prs) # 封面加左侧装饰条
                else:
                    p.font.size = Pt(40)
                    p.font.color.rgb = RGBColor(0, 102, 204)
                    
                    # 调整文本框宽度，留出右侧放图片的空间，同时必须保留原有高度（python-pptx 改变 placeholder 宽度时会导致高度归零）
                    old_title_height = title_shape.height
                    old_body_height = body_shape.height
                    
                    title_shape.width = Inches(7.5)
                    title_shape.height = old_title_height
                    
                    body_shape.width = Inches(7.5)
                    body_shape.height = old_body_height
                    
                    # 插入配图
                    add_placeholder_image(current_slide, prs)
            
            body_shape.text = "" # 清空默认占位符内容
            is_first_slide = False
            
            if is_new_slide_marker:
                continue
            # 如果是因为超出长度自动分页，则继续往下执行，将当前 line 添加到 body 中
            
        # ---------------- 内容写入逻辑 ----------------
        if line.startswith('### '):
             if current_slide and body_shape:
                 # pptx 在给 text 赋值空字符串后，默认可能保留一个空段落。这里复用该段落或新增。
                 if not body_shape.text_frame.text.strip():
                     body_shape.text_frame.clear()
                     p = body_shape.text_frame.paragraphs[0]
                 else:
                     p = body_shape.text_frame.add_paragraph()
                     
                 p.text = clean_markdown_bold(line[4:].strip())
                 p.font.bold = True
                 p.font.size = Pt(28)
                 p.font.color.rgb = RGBColor(51, 51, 51)
                 p.level = 0
                 slide_content_count += 2
                 
        elif line.startswith('- ') or line.startswith('* '):
            if current_slide and body_shape:
                if not body_shape.text_frame.text.strip():
                     p = body_shape.text_frame.paragraphs[0]
                     body_shape.text_frame.clear() # 确保真正清空
                     p = body_shape.text_frame.paragraphs[0]
                else:
                     p = body_shape.text_frame.add_paragraph()
                     
                p.text = clean_markdown_bold(line[2:].strip())
                p.font.size = Pt(22)
                p.level = 1 if current_slide.slide_layout.name != "Title Slide" else 0
                slide_content_count += 1
                
        elif re.match(r'^\d+\.\s', line):
            if current_slide and body_shape:
                if not body_shape.text_frame.text.strip():
                     body_shape.text_frame.clear()
                     p = body_shape.text_frame.paragraphs[0]
                else:
                     p = body_shape.text_frame.add_paragraph()
                     
                p.text = clean_markdown_bold(re.sub(r'^\d+\.\s', '', line).strip())
                p.font.size = Pt(22)
                p.level = 1 if current_slide.slide_layout.name != "Title Slide" else 0
                slide_content_count += 1
                
        else:
            if current_slide and body_shape:
                if line.startswith('```'):
                    continue
                    
                if not body_shape.text_frame.text.strip():
                     body_shape.text_frame.clear()
                     p = body_shape.text_frame.paragraphs[0]
                else:
                     p = body_shape.text_frame.add_paragraph()
                     
                p.text = clean_markdown_bold(line)
                
                if current_slide.slide_layout.name == "Title Slide":
                    p.font.size = Pt(26)
                    p.font.color.rgb = RGBColor(102, 102, 102)
                    p.level = 0
                else:
                    p.font.size = Pt(20)
                    p.level = 1
                slide_content_count += 1
                
    # 兜底生成
    if len(prs.slides) == 0:
        current_slide = prs.slides.add_slide(prs.slide_layouts[1])
        title_shape = current_slide.shapes.title
        body_shape = current_slide.placeholders[1]
        
        title_shape.text = "自动生成的幻灯片"
        for p in title_shape.text_frame.paragraphs:
             p.font.bold = True
             p.font.color.rgb = RGBColor(0, 51, 102)
             
        title_shape.width = Inches(7.5)
        body_shape.width = Inches(7.5)
        add_placeholder_image(current_slide, prs)
        
        body_shape.text = text[:1000]
        
    prs.save(output_path)
    return os.path.abspath(output_path)
