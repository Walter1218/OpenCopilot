#!/usr/bin/env python3
"""
PPT HTML预览器 - 将PPT内容转换为HTML预览
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PPT 预览</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f5f5f5;
            padding: 40px;
        }
        
        .slide-container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .slide {
            width: 100%;
            aspect-ratio: 16/9;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            margin-bottom: 40px;
            padding: 60px;
            position: relative;
            overflow: hidden;
            page-break-after: always;
        }
        
        .slide::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 8px;
            background: linear-gradient(90deg, #0052cc, #00b4d8);
        }
        
        .slide-title {
            font-size: 36px;
            font-weight: 700;
            color: #0052cc;
            margin-bottom: 40px;
            line-height: 1.2;
        }
        
        .slide-subtitle {
            font-size: 18px;
            color: #666;
            margin-top: 10px;
            font-weight: 400;
        }
        
        .content-area {
            display: flex;
            flex-direction: column;
            gap: 16px;
        }
        
        .item-level-0 {
            font-size: 20px;
            color: #1a1a2e;
            font-weight: 600;
            padding: 12px 0;
            border-left: 4px solid #0052cc;
            padding-left: 16px;
        }
        
        .item-level-1 {
            font-size: 16px;
            color: #3c4043;
            padding: 8px 0 8px 32px;
            position: relative;
        }
        
        .item-level-1::before {
            content: '•';
            position: absolute;
            left: 16px;
            color: #0052cc;
        }
        
        /* Three columns layout */
        .three-columns {
            display: flex;
            gap: 30px;
            margin-top: 20px;
        }
        
        .column {
            flex: 1;
            background: #f8f9fa;
            border-radius: 12px;
            padding: 24px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        
        .column-icon {
            width: 60px;
            height: 60px;
            background: linear-gradient(135deg, #0052cc, #00b4d8);
            border-radius: 50%;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 24px;
            font-weight: bold;
        }
        
        .column-title {
            font-size: 18px;
            font-weight: 700;
            color: #0052cc;
            text-align: center;
            margin-bottom: 16px;
        }
        
        .column-items {
            width: 100%;
        }
        
        .column-item {
            font-size: 14px;
            color: #3c4043;
            padding: 8px 0;
            border-bottom: 1px solid #e9ecef;
        }
        
        .column-item:last-child {
            border-bottom: none;
        }
        
        /* Title slide */
        .title-slide {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            background: linear-gradient(135deg, #0052cc 0%, #00b4d8 100%);
            color: white;
        }
        
        .title-slide .slide-title {
            color: white;
            font-size: 48px;
            margin-bottom: 20px;
        }
        
        .title-slide .slide-subtitle {
            color: rgba(255,255,255,0.9);
            font-size: 24px;
        }
        
        /* Ending slide */
        .ending-slide {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: white;
        }
        
        .ending-slide .slide-title {
            color: white;
            font-size: 60px;
        }
        
        .ending-slide .slide-subtitle {
            color: rgba(255,255,255,0.8);
            font-size: 28px;
            margin-top: 20px;
        }
        
        /* Chart slide */
        .chart-container {
            margin-top: 30px;
            background: #f8f9fa;
            border-radius: 12px;
            padding: 30px;
            height: 400px;
            display: flex;
            align-items: flex-end;
            justify-content: space-around;
        }
        
        .chart-bar {
            width: 80px;
            background: linear-gradient(180deg, #0052cc, #00b4d8);
            border-radius: 8px 8px 0 0;
            position: relative;
            transition: height 0.5s ease;
        }
        
        .chart-bar-label {
            position: absolute;
            bottom: -30px;
            left: 50%;
            transform: translateX(-50%);
            font-size: 12px;
            color: #666;
            white-space: nowrap;
        }
        
        .chart-bar-value {
            position: absolute;
            top: -25px;
            left: 50%;
            transform: translateX(-50%);
            font-size: 14px;
            font-weight: bold;
            color: #0052cc;
        }
        
        /* Page number */
        .page-number {
            position: absolute;
            bottom: 20px;
            right: 30px;
            font-size: 14px;
            color: #999;
        }
        
        @media print {
            body {
                background: white;
                padding: 0;
            }
            .slide {
                box-shadow: none;
                margin: 0;
                border-radius: 0;
            }
        }
    </style>
</head>
<body>
    <div class="slide-container">
        {{slides}}
    </div>
</body>
</html>"""

SLIDE_TEMPLATE = """
<div class="slide {slide_class}">
    <div class="slide-title">{title}{subtitle}</div>
    {content}
    <div class="page-number">{page_num} / {total_pages}</div>
</div>
"""

COLUMN_TEMPLATE = """
<div class="three-columns">
    {columns}
</div>
"""

COLUMN_ITEM_TEMPLATE = """
<div class="column">
    <div class="column-icon">{icon}</div>
    <div class="column-title">{title}</div>
    <div class="column-items">
        {items}
    </div>
</div>
"""


def generate_html_preview(slides_data, output_path="preview.html"):
    """生成HTML预览"""
    slides_html = []
    
    for i, slide in enumerate(slides_data):
        slide_type = slide.get("type", "content")
        title = slide.get("title", "")
        subtitle = slide.get("subtitle", "")
        items = slide.get("items", [])
        layout = slide.get("layout", "text_only")
        
        # 确定幻灯片类名
        if slide_type == "title":
            slide_class = "title-slide"
        elif slide_type == "ending":
            slide_class = "ending-slide"
        else:
            slide_class = ""
        
        # 生成副标题HTML
        subtitle_html = f'<div class="slide-subtitle">{subtitle}</div>' if subtitle else ''
        
        # 生成内容HTML
        if slide_type == "title" or slide_type == "ending":
            content_html = ""
        elif layout == "three_columns":
            # 三列布局
            columns_html = []
            # 按level=0分组
            columns = []
            current_col = []
            for item in items:
                if item.get("level", 0) == 0 and current_col:
                    columns.append(current_col)
                    current_col = [item]
                else:
                    current_col.append(item)
            if current_col:
                columns.append(current_col)
            
            # 如果第1列只有一个概述项，将其合并到标题中
            if len(columns) > 3 and len(columns[0]) == 1:
                overview_text = columns[0][0].get("text", "")
                title = f"{title}<br><small style='font-size: 18px; color: #666;'>{overview_text}</small>"
                columns = columns[1:]
            
            # 生成列HTML
            icons = ["C", "U", "T", "Q"]  # 图标字母
            for j, col in enumerate(columns[:3]):
                if j < len(icons):
                    icon = icons[j]
                else:
                    icon = str(j+1)
                
                items_html = ""
                for item in col[1:]:  # 跳过标题
                    items_html += f'<div class="column-item">{item.get("text", "")}</div>'
                
                columns_html.append(COLUMN_ITEM_TEMPLATE.format(
                    icon=icon,
                    title=col[0].get("text", ""),
                    items=items_html
                ))
            
            content_html = COLUMN_TEMPLATE.format(columns="".join(columns_html))
        else:
            # 普通布局
            content_html = '<div class="content-area">'
            for item in items:
                level = item.get("level", 0)
                text = item.get("text", "")
                if level == 0:
                    content_html += f'<div class="item-level-0">{text}</div>'
                else:
                    content_html += f'<div class="item-level-1">{text}</div>'
            content_html += '</div>'
        
        # 生成幻灯片HTML
        slide_html = SLIDE_TEMPLATE.format(
            slide_class=slide_class,
            title=title,
            subtitle=subtitle_html,
            content=content_html,
            page_num=i+1,
            total_pages=len(slides_data)
        )
        
        slides_html.append(slide_html)
    
    # 生成完整HTML
    full_html = HTML_TEMPLATE.replace("{{slides}}", "\n".join(slides_html))
    
    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    return output_path


def main():
    # 读取JSON文件
    json_path = os.path.expanduser("~/Documents/trae_projects/OpenCopilot/output/AI_Agent_深度研究报告_完整版.json")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 生成HTML预览
    output_dir = os.path.expanduser("~/Documents/trae_projects/OpenCopilot/output")
    os.makedirs(output_dir, exist_ok=True)
    
    html_path = os.path.join(output_dir, "AI_Agent_研究报告_预览.html")
    generate_html_preview(data['slides'], html_path)
    
    print(f"✅ HTML预览已生成: {html_path}")
    
    # 打开HTML文件
    import subprocess
    subprocess.run(['open', html_path])


if __name__ == "__main__":
    main()
