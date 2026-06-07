#!/usr/bin/env python3
"""测试 _repair_json_string 和 extract_json_from_text 的鲁棒性"""
import sys
import json
sys.path.insert(0, '/Users/onetwo/Documents/trae_projects/OpenCopilot')
from ppt_generator import _repair_json_string, extract_json_from_text


def check_repair(name, broken_json, expect_success=True):
    """测试 _repair_json_string"""
    repaired = _repair_json_string(broken_json)
    try:
        parsed = json.loads(repaired)
        if expect_success:
            print(f"  ✅ {name}: 修复成功")
            return True
        else:
            print(f"  ❌ {name}: 不应成功但成功了")
            return False
    except json.JSONDecodeError as e:
        if not expect_success:
            print(f"  ✅ {name}: 预期的失败 - {e}")
            return True
        else:
            print(f"  ❌ {name}: 修复失败 - {e}")
            print(f"     修复后前100字: {repaired[:100]}")
            return False


def check_extract(name, text, expect_slides=True):
    """测试 extract_json_from_text"""
    result = extract_json_from_text(text)
    if result is None:
        if expect_slides:
            print(f"  ❌ {name}: 返回 None")
            return False
        else:
            print(f"  ✅ {name}: 预期返回 None")
            return True

    if isinstance(result, dict) and "slides" in result:
        slides = result["slides"]
        if expect_slides and isinstance(slides, list) and len(slides) > 0:
            print(f"  ✅ {name}: 解析出 {len(slides)} 个 slides")
            return True
        elif not expect_slides:
            print(f"  ❌ {name}: 不应有 slides 但有 {len(slides)} 个")
            return False
        else:
            print(f"  ❌ {name}: slides 为空或非列表")
            return False
    elif isinstance(result, list):
        if expect_slides and len(result) > 0:
            print(f"  ✅ {name}: 解析出 {len(result)} 个 slides (list)")
            return True
        else:
            print(f"  ❌ {name}: 列表为空或不应有结果")
            return False
    else:
        print(f"  ❌ {name}: 未知返回类型 {type(result)}")
        return False


def main():
    passed = 0
    total = 0

    print("=" * 80)
    print("Part 1: _repair_json_string 单元测试")
    print("=" * 80)

    tests = [
        # 1. 正常 JSON 不动
        ("正常JSON", '{"title":"test","slides":[{"type":"content","title":"page1"}]}', True),
        # 2. 缺冒号
        ("缺冒号", '{"title":"test","slides":[{"type":"content","title":"page1","level:0}]}', True),
        # 3. 多处缺冒号
        ("多处缺冒号", '{"title":"test","slides":[{"type":"content","title":"p1","level:0,"text":"hi"}]}', True),
        # 4. }{ 缺少逗号
        ("}{ 缺逗号", '{"title":"test","slides":[{"type":"content","title":"p1"}{"type":"content","title":"p2"}]}', True),
        # 5. 尾随逗号
        ("尾随逗号", '{"title":"test","slides":[{"type":"content","title":"p1",}]}', True),
        # 6. 尾随逗号 + 缺冒号组合
        ("尾随逗号+缺冒号", '{"title":"test","slides":[{"type":"content","title":"p1","level:0,}]}', True),
        # 7. 字符串值内逗号不被误修
        ("值内逗号", '{"title":"hello, world","slides":[{"type":"content","title":"a, b, c"}]}', True),
        # 8. 字符串值内冒号不被误修
        ("值内冒号", '{"title":"时间: 2024","slides":[{"type":"content","title":"步骤: 第一步"}]}', True),
        # 9. 值间缺逗号 ""
        ("值间缺逗号", '{"title":"test","slides":[{"type":"content""title":"p1"}]}', True),
        # 10. 多尾随逗号
        ("多尾随逗号", '{"title":"test","slides":[{"type":"content","title":"p1","items":["a","b",],}],}', True),
        # 11. 大型 JSON（模拟 27 页 PPT）
        ("大型JSON(27页)", None, True),  # 下面单独构造
    ]

    for name, broken, expect in tests:
        total += 1
        if name == "大型JSON(27页)":
            # 构造 27 页大型 JSON 并注入多种错误
            slides = []
            for i in range(27):
                slides.append({
                    "type": "content",
                    "layout": "text_only",
                    "title": f"第{i+1}页标题",
                    "items": [
                        {"level": 0, "text": f"要点A{i}"},
                        {"level": 1, "text": f"要点B{i}"},
                    ],
                    "source_excerpt": f"这是第{i+1}页的原文摘录"
                })
            big_json = json.dumps({"title": "大型测试PPT", "slides": slides}, ensure_ascii=False)
            # 注入错误：3处缺冒号 + 2处尾随逗号
            broken = big_json
            # 缺冒号: "level": 0 → "level:0 (3处)
            for i, idx in enumerate([200, 600, 1200]):
                pos = broken.find('"level": 0', idx)
                if pos != -1:
                    broken = broken[:pos] + '"level:0' + broken[pos + len('"level": 0'):]
            # 尾随逗号: 在某些 } 前加 ,
            for target in ['}]}', '}]}']:
                idx = broken.rfind(target)
                if idx != -1:
                    broken = broken[:idx] + ',' + broken[idx:]
            if check_repair(name, broken, expect):
                passed += 1
        else:
            if check_repair(name, broken, expect):
                passed += 1

    print()
    print("=" * 80)
    print("Part 2: extract_json_from_text 集成测试")
    print("=" * 80)

    # 1. 正常 JSON
    total += 1
    if check_extract("正常JSON", '{"title":"test","slides":[{"type":"content","title":"p1"}]}'):
        passed += 1

    # 2. 带 ```json 代码块
    total += 1
    md_json = '```json\n{"title":"test","slides":[{"type":"content","title":"p1"}]}\n```'
    if check_extract("代码块JSON", md_json):
        passed += 1

    # 3. 带前缀文字 + JSON
    total += 1
    prefix_json = '好的，以下是生成的PPT大纲：\n{"title":"test","slides":[{"type":"content","title":"p1"}]}'
    if check_extract("前缀+JSON", prefix_json):
        passed += 1

    # 4. 语法错误 JSON（可修复）
    total += 1
    broken_json = '{"title":"test","slides":[{"type":"content","title":"p1","level:0,}]}'
    if check_extract("语法错误JSON", broken_json):
        passed += 1

    # 5. 被截断的 JSON
    total += 1
    truncated = '{"title":"test","slides":[{"type":"content","title":"p1"},{"type":"content","title":"p2"'
    if check_extract("截断JSON", truncated):
        passed += 1

    # 6. Markdown 降级
    total += 1
    md_text = "# 标题\n\n## 第一页\n- 要点1\n- 要点2\n\n## 第二页\n- 要点3\n"
    if check_extract("Markdown降级", md_text):
        passed += 1

    # 7. 完整的多页 PPT JSON（模拟真实 AI 输出）
    total += 1
    real_ppt = {
        "title": "AI Agent 研究报告",
        "slides": [
            {"type": "title", "layout": "center", "title": "AI Agent 研究报告", "subtitle": "2024", "items": [], "source_excerpt": "AI Agent研究"},
            {"type": "content", "layout": "text_only", "title": "核心架构", "items": [
                {"level": 0, "text": "感知模块"},
                {"level": 0, "text": "推理模块"},
            ], "source_excerpt": "核心架构包括感知和推理"},
            {"type": "content", "layout": "chart", "title": "市场趋势", "items": [
                {"content_type": "chart", "chart_type": "bar", "chart_data": {
                    "title": "市场规模",
                    "labels": ["2022", "2023", "2024"],
                    "datasets": [{"label": "亿元", "data": [100, 200, 500]}]
                }}
            ], "source_excerpt": "市场趋势数据"},
            {"type": "ending", "layout": "center", "title": "谢谢", "subtitle": "Q & A", "items": [], "source_excerpt": ""},
        ]
    }
    real_json = json.dumps(real_ppt, ensure_ascii=False)
    if check_extract("真实PPT JSON", real_json):
        passed += 1

    # 8. 带语法错误的真实 PPT JSON
    total += 1
    broken_real = real_json
    # 注入 2 处缺冒号
    pos = broken_real.find('"level": 0')
    if pos != -1:
        broken_real = broken_real[:pos] + '"level:0' + broken_real[pos + len('"level": 0'):]
    # 注入 1 处尾随逗号
    pos = broken_real.rfind('}]}')
    if pos != -1:
        broken_real = broken_real[:pos] + ',}]}'  + broken_real[pos+4:]
    if check_extract("语法错误的真实PPT", broken_real):
        passed += 1

    print()
    print("=" * 80)
    print(f"结果: {passed}/{total} 通过")
    print("=" * 80)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
