import re
import os
import json
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN

def clean_markdown(text):
    """清理 Markdown 标记，返回纯文本（兼容旧调用）"""
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    return text.strip()


def parse_inline_formatting(text):
    """
    解析内联格式，返回 (clean_text, runs_info)
    runs_info = [{"text": "...", "bold": True/False, "italic": True/False}, ...]
    """
    runs = []
    # 正则匹配 **bold** 或 *italic* 片段
    pattern = r'(\*\*(.+?)\*\*|\*(.+?)\*)'
    last_end = 0
    for match in re.finditer(pattern, text):
        # 前置普通文本
        if match.start() > last_end:
            plain = text[last_end:match.start()]
            if plain:
                runs.append({"text": plain, "bold": False, "italic": False})
        # 格式化文本
        if match.group(2):  # **bold**
            runs.append({"text": match.group(2), "bold": True, "italic": False})
        elif match.group(3):  # *italic*
            runs.append({"text": match.group(3), "bold": False, "italic": True})
        last_end = match.end()
    # 尾部普通文本
    if last_end < len(text):
        runs.append({"text": text[last_end:], "bold": False, "italic": False})
    
    if not runs:
        runs.append({"text": text, "bold": False, "italic": False})
    
    clean = "".join(r["text"] for r in runs)
    return clean, runs


def _apply_formatted_paragraph(paragraph, text):
    """将含 **bold** / *italic* 的文本应用到 paragraph，正确设置 run 样式"""
    _, runs = parse_inline_formatting(text)
    # 清空默认 run
    for run in paragraph.runs:
        run.text = ""
    for i, r in enumerate(runs):
        if i == 0 and paragraph.runs:
            run = paragraph.runs[0]
            run.text = r["text"]
        else:
            run = paragraph.add_run()
            run.text = r["text"]
        run.font.bold = r["bold"]
        run.font.italic = r["italic"]

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

def add_placeholder_image(slide, prs):
    """为 image_right 版式添加右侧配图占位"""
    try:
        img_width = Inches(4.5)
        img_height = prs.slide_height
        left = prs.slide_width - img_width
        top = Inches(0)
        
        # 使用几何图形拼接出具有设计感的占位图
        shape1 = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, img_width, img_height)
        shape1.fill.solid()
        shape1.fill.fore_color.rgb = RGBColor(235, 240, 245)
        shape1.line.fill.background()
        
        shape2 = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left + Inches(0.5), top + Inches(1.5), img_width - Inches(1.0), Inches(4.5))
        shape2.fill.solid()
        shape2.fill.fore_color.rgb = RGBColor(0, 102, 204)
        shape2.line.fill.background()
        
        shape3 = slide.shapes.add_shape(MSO_SHAPE.OVAL, left + Inches(3.0), top + Inches(4.5), Inches(2.0), Inches(2.0))
        shape3.fill.solid()
        shape3.fill.fore_color.rgb = RGBColor(255, 153, 51)
        shape3.line.fill.background()
    except Exception as e:
        pass

def format_content_slide(slide, title_text, items, layout_type="text_only", prs=None, slide_data=None):
    """格式化内容页，支持多种版式：text_only / table / code / image_right / three_columns"""
    title_shape = slide.shapes.title
    
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

    # ---- 表格布局 ----
    if layout_type == "table" and slide_data and "table_data" in slide_data:
        table_rows = slide_data["table_data"]
        if len(table_rows) >= 2:
            # 解析表头（第一行）和数据行
            header_cells = [c.strip() for c in table_rows[0].strip('|').split('|')]
            data_rows = []
            for row in table_rows[1:]:
                # 跳过分隔行 (|---|---|)
                if re.match(r'^[\|\s\-:]+$', row):
                    continue
                cells = [c.strip() for c in row.strip('|').split('|')]
                data_rows.append(cells)
            
            num_cols = len(header_cells)
            num_rows = len(data_rows) + 1  # +1 for header
            
            if num_cols > 0 and data_rows:
                table_left = Inches(1)
                table_top = Inches(1.8)
                table_width = Inches(11.333)
                table_height = Inches(min(4.5, 0.4 * num_rows + 0.5))
                
                table_shape = slide.shapes.add_table(
                    num_rows, num_cols, table_left, table_top, table_width, table_height
                )
                table = table_shape.table
                
                # 设置列宽
                col_width = table_width / num_cols
                for c in range(num_cols):
                    table.columns[c].width = int(col_width)
                
                # 表头行
                for c, cell_text in enumerate(header_cells):
                    cell = table.cell(0, c)
                    cell.text = cell_text
                    for p in cell.text_frame.paragraphs:
                        p.font.bold = True
                        p.font.size = Pt(16)
                        p.font.color.rgb = RGBColor(255, 255, 255)
                        p.alignment = PP_ALIGN.CENTER
                    # 表头背景色
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = RGBColor(0, 82, 204)
                
                # 数据行
                for r_idx, row in enumerate(data_rows):
                    for c_idx, cell_text in enumerate(row):
                        if c_idx < num_cols:
                            cell = table.cell(r_idx + 1, c_idx)
                            cell.text = clean_markdown(cell_text)
                            for p in cell.text_frame.paragraphs:
                                p.font.size = Pt(14)
                                p.font.color.rgb = RGBColor(15, 25, 45)
                            # 交替行背景
                            if r_idx % 2 == 1:
                                cell.fill.solid()
                                cell.fill.fore_color.rgb = RGBColor(240, 244, 250)
                return
    
    # ---- 代码布局 ----
    if layout_type == "code" and slide_data and "code_text" in slide_data:
        code_text = slide_data["code_text"]
        code_lang = slide_data.get("code_lang", "")
        
        # 代码块背景
        bg_shape = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(0.8), Inches(1.8),
            Inches(11.6), Inches(5.0)
        )
        bg_shape.fill.solid()
        bg_shape.fill.fore_color.rgb = RGBColor(40, 44, 52)
        bg_shape.line.fill.background()
        
        # 代码文本
        code_box = slide.shapes.add_textbox(
            Inches(1.2), Inches(2.0),
            Inches(10.8), Inches(4.5)
        )
        tf = code_box.text_frame
        tf.word_wrap = True
        
        for i, codeline in enumerate(code_text.split('\n')):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = codeline
            p.font.name = "Courier New"
            p.font.size = Pt(14)
            p.font.color.rgb = RGBColor(200, 210, 220)
            p.space_after = Pt(2)
        
        # 语言标签
        if code_lang:
            lang_label = slide.shapes.add_textbox(
                Inches(9.5), Inches(1.85),
                Inches(2.8), Inches(0.3)
            )
            lp = lang_label.text_frame.paragraphs[0]
            lp.text = code_lang
            lp.font.size = Pt(10)
            lp.font.color.rgb = RGBColor(150, 160, 170)
            lp.font.italic = True
            lp.alignment = PP_ALIGN.RIGHT
        return

    # ---- 其他布局 ----
    body_shape = slide.placeholders[1]
    
    if layout_type == "image_right":
        body_shape.width = Inches(7.5)
        if prs:
            add_placeholder_image(slide, prs)
    elif layout_type == "three_columns":
        body_shape.text_frame.clear()
        col_width = Inches(3.5)
        for i in range(min(3, len(items))):
            left_pos = Inches(1) + i * Inches(3.8)
            txBox = slide.shapes.add_textbox(left_pos, Inches(2.0), col_width, Inches(4.0))
            tf = txBox.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            _apply_formatted_paragraph(p, items[i].get("text", ""))
            p.font.size = Pt(24)
            p.font.color.rgb = RGBColor(15, 25, 45)
            p.alignment = PP_ALIGN.CENTER
            icon = slide.shapes.add_shape(MSO_SHAPE.OVAL, left_pos + Inches(1.25), Inches(1.2), Inches(1.0), Inches(1.0))
            icon.fill.solid()
            icon.fill.fore_color.rgb = RGBColor(235, 240, 248)
            icon.line.fill.background()
        return
    else:
        body_shape.width = Inches(11.333)
        
    body_shape.left = Inches(1)
    body_shape.top = Inches(1.8)
    body_shape.height = Inches(5.0)
    body_shape.text_frame.clear()
    
    for item in items:
        level = item.get("level", 0)
        text = item.get("text", "")
        if not text:
            continue
            
        p = body_shape.text_frame.paragraphs[0] if not body_shape.text_frame.text.strip() else body_shape.text_frame.add_paragraph()
        _apply_formatted_paragraph(p, text)
        p.level = level
        p.space_after = Pt(12)
        
        if level == 0:
            p.font.size = Pt(28)
            p.font.color.rgb = RGBColor(15, 25, 45)
        else:
            p.font.size = Pt(22)
            p.font.color.rgb = RGBColor(60, 64, 67)

def extract_json_from_text(text):
    """从大模型的混合输出中提取 JSON 数据，或降级解析 Markdown 为 PPT 大纲"""
    # 1. 尝试匹配 ```json ... ``` 块（支持对象 {} 或数组 []）
    match = re.search(r'```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```', text, re.DOTALL)
    json_str = match.group(1) if match else text

    # 2. 尝试直接解析 JSON
    try:
        start_obj = json_str.find('{')
        start_arr = json_str.find('[')
        start_idx = -1
        
        if start_obj != -1 and start_arr != -1:
            start_idx = min(start_obj, start_arr)
        else:
            start_idx = max(start_obj, start_arr)
            
        if start_idx != -1:
            end_idx = -1
            if json_str[start_idx] == '{':
                end_idx = json_str.rfind('}') + 1
            else:
                end_idx = json_str.rfind(']') + 1
                
            if end_idx > start_idx:
                clean_str = json_str[start_idx:end_idx]
                parsed = json.loads(clean_str)
                
                # 兼容两种格式：
                # 1. {"title": "...", "slides": [...]} - 完整格式，直接返回
                # 2. {"slides": [...]} - 部分格式，返回完整对象
                # 3. [...] - 数组格式，直接返回
                if isinstance(parsed, dict) and "slides" in parsed:
                    return parsed  # 返回完整字典，保留 title 等字段
                elif isinstance(parsed, list):
                    return parsed
    except Exception:
        pass
        
    # 3. 如果 JSON 解析失败，但包含 Markdown 标题，则降级将 Markdown 转换为 JSON 结构
    if '# ' in text or '## ' in text:
        slides = []
        current_slide = None
        table_buffer = []       # 累积表格行
        in_table = False        # 是否在表格中
        in_code_block = False   # 是否在代码块中
        code_buffer = []        # 累积代码行
        code_lang = ""          # 代码语言

        def flush_table():
            """将累积的表格行写入当前 slide"""
            nonlocal table_buffer, in_table
            if current_slide and table_buffer:
                current_slide["layout"] = "table"
                current_slide["table_data"] = table_buffer.copy()
                current_slide["items"] = current_slide.get("items", [])
            table_buffer = []
            in_table = False

        def flush_code():
            """将累积的代码块写入当前 slide"""
            nonlocal code_buffer, code_lang, in_code_block
            if current_slide and code_buffer:
                current_slide["layout"] = "code"
                current_slide["code_lang"] = code_lang
                current_slide["code_text"] = "\n".join(code_buffer)
                current_slide["items"] = current_slide.get("items", [])
            code_buffer = []
            code_lang = ""
            in_code_block = False

        for line in text.split('\n'):
            stripped = line.strip()
            
            # 代码块检测
            if stripped.startswith('```'):
                if in_code_block:
                    flush_code()
                else:
                    flush_table()  # 先刷新可能的表格
                    code_lang = stripped[3:].strip()
                    in_code_block = True
                continue
            if in_code_block:
                code_buffer.append(line)
                continue
            
            # 表格检测（包含 | 且下一行是 |---| 分隔符）
            if '|' in stripped and stripped.strip('|').strip():
                if not in_table:
                    flush_code()  # 刷新可能的代码块
                    # 检查是否真的是表格（需要后续行也存在）
                    in_table = True
                table_buffer.append(stripped)
                continue
            elif in_table and stripped.strip():
                # 可能是表格的 continuation
                if '|' in stripped:
                    table_buffer.append(stripped)
                    continue
                else:
                    flush_table()
            
            # 空行处理
            if not stripped:
                flush_table()
                flush_code()
                continue
            
            flush_table()
            flush_code()
            
            if stripped.startswith('# '):
                if current_slide: slides.append(current_slide)
                current_slide = {"type": "title", "layout": "center", "title": stripped[2:].strip(), "subtitle": "", "items": []}
            elif stripped.startswith('## '):
                if current_slide: slides.append(current_slide)
                current_slide = {"type": "content", "layout": "text_only", "title": stripped[3:].strip(), "items": []}
            elif stripped.startswith('- ') or stripped.startswith('* '):
                if current_slide:
                    if "items" not in current_slide: current_slide["items"] = []
                    current_slide["items"].append({"level": 0, "text": stripped[2:].strip()})
            else:
                if current_slide and current_slide.get("type") == "content":
                    if "items" not in current_slide: current_slide["items"] = []
                    current_slide["items"].append({"level": 0, "text": stripped})

        # 刷新残留缓冲区
        flush_table()
        flush_code()
        if current_slide:
            slides.append(current_slide)
        if slides:
            return slides
            
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
            layout_type = slide_data.get("layout", "text_only")
            format_content_slide(slide, slide_data.get("title", "内容"), slide_data.get("items", []), layout_type, prs, slide_data)
            
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