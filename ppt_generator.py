import re
import os
import json
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
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor(250, 250, 252)
    
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 
        Inches(0), prs.slide_height - Inches(0.1), 
        prs.slide_width, Inches(0.1)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor(0, 82, 204)
    shape.line.fill.background()

    if is_title_slide:
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

def format_title_slide(slide, title_text, subtitle_text=""):
    """格式化封面"""
    title_shape = slide.shapes.title
    title_shape.text = clean_markdown(title_text)
    
    title_shape.width = Inches(8)
    title_shape.left = Inches(1)
    title_shape.top = Inches(2.5)
    
    for p in title_shape.text_frame.paragraphs:
        p.font.bold = True
        p.font.size = Pt(44)
        p.font.color.rgb = RGBColor(15, 25, 45)
        p.alignment = PP_ALIGN.LEFT
        
    if subtitle_text and len(slide.placeholders) > 1:
        subtitle_shape = slide.placeholders[1]
        subtitle_shape.text = clean_markdown(subtitle_text)
        subtitle_shape.width = Inches(8)
        subtitle_shape.left = Inches(1)
        subtitle_shape.top = Inches(3.8)
        for p in subtitle_shape.text_frame.paragraphs:
            p.font.size = Pt(24)
            p.font.color.rgb = RGBColor(100, 100, 110)
            p.alignment = PP_ALIGN.LEFT

def format_content_slide(slide, title_text, items):
    """格式化内容页"""
    title_shape = slide.shapes.title
    body_shape = slide.placeholders[1]
    
    title_shape.text = clean_markdown(title_text)
    title_shape.width = Inches(11.333)
    title_shape.left = Inches(1)
    title_shape.top = Inches(0.5)
    title_shape.height = Inches(1.2)
    
    for p in title_shape.text_frame.paragraphs:
        p.font.bold = True
        p.font.size = Pt(36)
        p.font.color.rgb = RGBColor(0, 82, 204)
        p.alignment = PP_ALIGN.LEFT
        
    body_shape.width = Inches(11.333)
    body_shape.left = Inches(1)
    body_shape.top = Inches(1.8)
    body_shape.height = Inches(5.0)
    body_shape.text_frame.clear()
    
    for item in items:
        level = item.get("level", 0)
        text = clean_markdown(item.get("text", ""))
        if not text:
            continue
            
        p = body_shape.text_frame.paragraphs[0] if not body_shape.text_frame.text.strip() else body_shape.text_frame.add_paragraph()
        p.text = text
        p.level = level
        p.space_after = Pt(12)
        
        if level == 0:
            p.font.bold = True
            p.font.size = Pt(28)
            p.font.color.rgb = RGBColor(15, 25, 45)
        else:
            p.font.size = Pt(22)
            p.font.color.rgb = RGBColor(60, 64, 67)

def extract_json_from_text(text):
    """从大模型的混合输出中提取 JSON 数组"""
    # 尝试找到被 ```json ``` 包裹的内容
    match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
            
    # 尝试直接解析
    try:
        start_idx = text.find('[')
        end_idx = text.rfind(']') + 1
        if start_idx != -1 and end_idx > start_idx:
            return json.loads(text[start_idx:end_idx])
    except:
        pass
        
    return None

def generate_ppt_from_json(json_data, output_path="output.pptx"):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    for slide_data in json_data:
        slide_type = slide_data.get("type", "content")
        
        if slide_type == "title":
            slide = prs.slides.add_slide(prs.slide_layouts[0])
            apply_corporate_theme(slide, prs, is_title_slide=True)
            format_title_slide(slide, slide_data.get("title", "演示文稿"), slide_data.get("subtitle", ""))
            
        elif slide_type == "content":
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            apply_corporate_theme(slide, prs, is_title_slide=False)
            format_content_slide(slide, slide_data.get("title", "内容"), slide_data.get("items", []))
            
    if len(prs.slides) == 0:
        slide = prs.slides.add_slide(prs.slide_layouts[0])
        apply_corporate_theme(slide, prs, is_title_slide=True)
        format_title_slide(slide, "自动生成的幻灯片")
        
    prs.save(output_path)
    return os.path.abspath(output_path)

def generate_ppt_from_text(text, output_path="output.pptx"):
    """入口函数，兼容 JSON 提取与旧版降级处理"""
    json_data = extract_json_from_text(text)
    
    if json_data and isinstance(json_data, list):
        return generate_ppt_from_json(json_data, output_path)
    
    # 如果没提取到 JSON，说明大模型没有按规范输出（或者走的是旧流程），抛出异常让上层处理
    raise ValueError("无法从内容中提取出有效的幻灯片 JSON 结构。")

if __name__ == "__main__":
    pass