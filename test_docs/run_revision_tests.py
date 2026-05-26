#!/usr/bin/env python3
"""文档修订模式测试脚本 - 模拟用户拖拽选中文档后触发全文联动修订"""

import httpx
import json
import time
import os

AGENT_URL = "http://127.0.0.1:18888/v1/agent/chat"
RESULT_DIR = os.path.dirname(os.path.abspath(__file__))

def read_file(filename):
    path = os.path.join(RESULT_DIR, filename)
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def run_test(name, full_doc, selection, file_name):
    """执行一轮修订测试，返回 SSE 流中所有 chunk 拼接的完整响应"""
    payload = {
        "text": selection,
        "action_type": "revision",
        "session_id": f"test_revision_{name}",
        "is_new_task": True,
        "context_source": "revision",
        "context_meta": {
            "file_name": file_name,
            "language": "markdown",
            "task": "文档修订"
        },
        "context_envelope": {
            "source": "ide",
            "content": full_doc,
            "selection": selection,
            "task": "文档修订",
            "meta": {"file_name": file_name, "language": "markdown"}
        }
    }
    
    print(f"\n[TEST] {name}")
    print(f"  Selection ({len(selection)} chars): {selection[:80]}...")
    print(f"  Full doc ({len(full_doc)} chars)")
    print("  Sending...", flush=True)
    
    full_response = ""
    try:
        with httpx.Client(timeout=120.0, verify=False) as client:
            with client.stream("POST", AGENT_URL, json=payload) as response:
                for line in response.iter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            data = json.loads(line[6:])
                            chunk = data.get("chunk", "")
                            full_response += chunk
                        except Exception:
                            pass
        print(f"  ✅ Done ({len(full_response)} chars)")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        full_response = f"[ERROR] {e}"
    
    return full_response

if __name__ == "__main__":
    results = {}
    
    # ========== 测试 1: 项目规划书 - 日期/人员一致性 ==========
    doc1 = read_file("project_plan.md")
    selection1 = "项目总负责人为张伟"
    results["test1_project_plan"] = {
        "doc_name": "project_plan.md",
        "doc_content": doc1,
        "selection": selection1,
        "result": run_test("test1_project_plan", doc1, selection1, "project_plan.md")
    }
    
    # ========== 测试 2: 技术规格书 - 模块名称变更 ==========
    doc2 = read_file("tech_spec.md")
    selection2 = "采用 PyQt6 双图层架构，全屏穿透特效层负责光标视觉效果，局部可交互卡片层承载 AI 对话"
    results["test2_tech_spec"] = {
        "doc_name": "tech_spec.md",
        "doc_content": doc2,
        "selection": selection2,
        "result": run_test("test2_tech_spec", doc2, selection2, "tech_spec.md")
    }
    
    # ========== 测试 3: 会议纪要 - 矛盾数字修正 ==========
    doc3 = read_file("meeting_notes.md")
    selection3 = "Q3 有 2 位同事离职（前端张三、后端李四），预计 Q4 可补充 3 位新同事"
    results["test3_meeting_notes"] = {
        "doc_name": "meeting_notes.md",
        "doc_content": doc3,
        "selection": selection3,
        "result": run_test("test3_meeting_notes", doc3, selection3, "meeting_notes.md")
    }
    
    # 保存结果
    outpath = os.path.join(RESULT_DIR, "revision_test_results.json")
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 全部测试完成，结果保存至: {outpath}")
