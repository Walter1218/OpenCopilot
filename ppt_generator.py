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
    """为内容页右侧添加配图"""
    try:
        # 使用 picsum 获取随机高质量配图 (商业/抽象风格偏好可以用特定种子，这里用随机)
        url = "https://picsum.photos/600/800/?blur=2"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            image_stream = BytesIO(response.read())
            
        # 图片放置在右侧
        img_width = Inches(5.33)
        img_height = prs.slide_height
        left = prs.slide_width - img_width
        top = Inches(0)
        
        slide.shapes.add_picture(image_stream, left, top, img_width, img_height)
        return True
    except Exception as e:
        print(f"Failed to fetch image: {e}")
        # 如果网络失败，用装饰色块替代
        left = prs.slide_width - Inches(3)
        top = Inches(0)
        width = Inches(3)
        height = prs.slide_height
        shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor(240, 240, 245)
        shape.line.fill.background()
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
    
    # 强制分块逻辑：如果大模型没有输出任何 # 或 ##，我们需要人为分块
    has_headers = any(line.strip().startswith('#') for line in lines)
    
    slide_content_count = 0  # 记录当前页的内容行数，过多则自动分页
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 判断是否应该开启新一页：遇到一级/二级标题，或中文大写序号，或单页内容超过 8 行且没有 Markdown 标题
        is_new_slide_marker = line.startswith('# ') or line.startswith('## ') or re.match(r'^[一二三四五六七八九十]+、', line)
        if (not has_headers and slide_content_count >= 8) or is_new_slide_marker:
            
            layout_idx = 0 if is_first_slide else 1
            current_slide = prs.slides.add_slide(prs.slide_layouts[layout_idx])
            slide_content_count = 0
            
            title_shape = current_slide.shapes.title
            body_shape = current_slide.placeholders[1] if layout_idx == 1 else current_slide.placeholders[1]
                
            raw_text = re.sub(r'^#+\s*', '', line).strip()  # 移除 # 标记
            title_shape.text = clean_markdown_bold(raw_text)
            
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
                    
                    # 调整文本框宽度，留出右侧放图片的空间
                    title_shape.width = Inches(7.5)
                    body_shape.width = Inches(7.5)
                    # 插入配图
                    add_placeholder_image(current_slide, prs)
            
            body_shape.text = ""
            is_first_slide = False
            continue
            
        elif line.startswith('### '):
             if current_slide and body_shape:
                 p = body_shape.text_frame.add_paragraph()
                 p.text = clean_markdown_bold(line[4:].strip())
                 p.font.bold = True
                 p.font.size = Pt(28)
                 p.font.color.rgb = RGBColor(51, 51, 51)
                 p.level = 0
                 slide_content_count += 2
                 
        elif line.startswith('- ') or line.startswith('* '):
            if current_slide and body_shape:
                p = body_shape.text_frame.add_paragraph()
                p.text = clean_markdown_bold(line[2:].strip())
                p.font.size = Pt(22)
                p.level = 1 if current_slide.slide_layout.name != "Title Slide" else 0
                slide_content_count += 1
                
        elif re.match(r'^\d+\.\s', line):
            if current_slide and body_shape:
                p = body_shape.text_frame.add_paragraph()
                p.text = clean_markdown_bold(re.sub(r'^\d+\.\s', '', line).strip())
                p.font.size = Pt(22)
                p.level = 1 if current_slide.slide_layout.name != "Title Slide" else 0
                slide_content_count += 1
                
        else:
            if current_slide and body_shape:
                if line.startswith('```'):
                    continue
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
