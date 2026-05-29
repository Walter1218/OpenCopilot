import re
import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN

def clean_markdown(text):
    """清理 Markdown 标记"""
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    return text.strip()

def apply_corporate_theme(slide, prs, is_title_slide=False):
    """应用现代化极简商务主题"""
    # 纯净白灰背景
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor(250, 250, 252)
    
    # 底部贯穿的品牌色线
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 
        Inches(0), prs.slide_height - Inches(0.1), 
        prs.slide_width, Inches(0.1)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor(0, 82, 204)
    shape.line.fill.background()

    if is_title_slide:
        # 封面几何装饰
        dec1 = slide.shapes.add_shape(
            MSO_SHAPE.RIGHT_TRIANGLE, 
            prs.slide_width - Inches(5), Inches(0), 
            Inches(5), prs.slide_height
        )
        dec1.fill.solid()
        dec1.fill.fore_color.rgb = RGBColor(235, 240, 248)
        dec1.line.fill.background()
        
        dec2 = slide.shapes.add_shape(
            MSO_SHAPE.RIGHT_TRIANGLE, 
            prs.slide_width - Inches(3.5), Inches(0), 
            Inches(3.5), prs.slide_height
        )
        dec2.fill.solid()
        dec2.fill.fore_color.rgb = RGBColor(0, 82, 204)
        dec2.line.fill.background()

def calculate_lines(text):
    """估算文本占据的物理行数，避免内容溢出"""
    # 宽屏文本框，24号字，一行约能容纳 40 个中文字符
    chars_per_line = 40
    lines = max(1, len(text) // chars_per_line + 1)
    return lines

def format_title_slide(slide, title_text):
    """格式化封面"""
    title_shape = slide.shapes.title
    title_shape.text = title_text
    
    # 将标题框居中并调整大小
    title_shape.width = Inches(8)
    title_shape.left = Inches(1)
    title_shape.top = Inches(2.5)
    
    for p in title_shape.text_frame.paragraphs:
        p.font.bold = True
        p.font.size = Pt(44)
        p.font.color.rgb = RGBColor(15, 25, 45)
        p.alignment = PP_ALIGN.LEFT

def generate_ppt_from_text(text, output_path="output.pptx"):
    prs = Presentation()
    
    # 16:9 宽屏
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    lines = text.split('\n')
    current_slide = None
    title_shape = None
    body_shape = None
    
    is_first_slide = True
    slide_content_lines = 0
    MAX_LINES_PER_SLIDE = 10
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 解析是否需要开启新页
        is_h1 = line.startswith('# ')
        is_h2 = line.startswith('## ')
        is_cn_num = re.match(r'^[一二三四五六七八九十]+、', line) is not None
        
        is_new_slide_marker = is_h1 or is_h2 or is_cn_num
        
        # 估算当前行占据的排版行数 (如果是标题，权重视为占用大一些)
        needed_lines = 2 if line.startswith('###') else calculate_lines(line)
        
        if current_slide is None or (slide_content_lines + needed_lines > MAX_LINES_PER_SLIDE) or is_new_slide_marker:
            
            layout_idx = 0 if is_first_slide else 1
            current_slide = prs.slides.add_slide(prs.slide_layouts[layout_idx])
            slide_content_lines = 0
            
            apply_corporate_theme(current_slide, prs, is_title_slide=is_first_slide)
            
            title_shape = current_slide.shapes.title
            body_shape = current_slide.placeholders[1] if layout_idx == 1 else None
            
            # 设置标题内容
            if is_new_slide_marker:
                raw_text = clean_markdown(re.sub(r'^#+\s*', '', line))
                if is_first_slide:
                    format_title_slide(current_slide, raw_text)
                else:
                    title_shape.text = raw_text
            else:
                if not is_first_slide:
                    title_shape.text = "续前页"
                else:
                    format_title_slide(current_slide, "报告内容")
            
            # 美化内容页标题
            if not is_first_slide:
                title_shape.width = Inches(11.333)
                title_shape.left = Inches(1)
                title_shape.top = Inches(0.5)
                title_shape.height = Inches(1.2)
                for p in title_shape.text_frame.paragraphs:
                    p.font.bold = True
                    p.font.size = Pt(36)
                    p.font.color.rgb = RGBColor(0, 82, 204)
                    p.alignment = PP_ALIGN.LEFT
                    
                # 调整正文文本框以适应全宽
                body_shape.width = Inches(11.333)
                body_shape.left = Inches(1)
                body_shape.top = Inches(1.8)
                body_shape.height = Inches(5.0)
                body_shape.text_frame.clear()
            
            is_first_slide = False
            
            if is_new_slide_marker:
                continue
                
        # ---------------- 内容写入逻辑 ----------------
        if not body_shape:
            continue
            
        p = body_shape.text_frame.paragraphs[0] if not body_shape.text_frame.text.strip() else body_shape.text_frame.add_paragraph()
        p.space_after = Pt(12)  # 增加段落间距，让排版呼吸感更好
        
        if line.startswith('### '):
            p.text = clean_markdown(line[4:])
            p.font.bold = True
            p.font.size = Pt(28)
            p.font.color.rgb = RGBColor(15, 25, 45)
            p.level = 0
            slide_content_lines += 2
            
        elif line.startswith('- ') or line.startswith('* '):
            p.text = clean_markdown(line[2:])
            p.font.size = Pt(22)
            p.font.color.rgb = RGBColor(60, 64, 67)
            p.level = 1
            slide_content_lines += needed_lines
            
        elif re.match(r'^\d+\.\s', line):
            p.text = clean_markdown(re.sub(r'^\d+\.\s', '', line))
            p.font.size = Pt(22)
            p.font.color.rgb = RGBColor(60, 64, 67)
            p.level = 1
            slide_content_lines += needed_lines
            
        else:
            if line.startswith('```'):
                continue
            p.text = clean_markdown(line)
            p.font.size = Pt(20)
            p.font.color.rgb = RGBColor(80, 84, 87)
            p.level = 0
            slide_content_lines += needed_lines
            
    # 兜底：如果没有任何内容
    if len(prs.slides) == 0:
        current_slide = prs.slides.add_slide(prs.slide_layouts[0])
        apply_corporate_theme(current_slide, prs, is_title_slide=True)
        format_title_slide(current_slide, "自动生成的幻灯片")
        
    prs.save(output_path)
    return os.path.abspath(output_path)

if __name__ == "__main__":
    pass