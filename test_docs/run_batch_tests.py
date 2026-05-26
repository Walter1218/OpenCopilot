#!/usr/bin/env python3
"""批量文档修订测试 - 极端案例验证"""
import httpx, json, os, re, time

AGENT_URL = "http://127.0.0.1:18888/v1/agent/chat"
TEST_DIR = os.path.dirname(os.path.abspath(__file__))

def read_file(name):
    with open(os.path.join(TEST_DIR, name), 'r') as f:
        return f.read()

def test_revision(name, file_name, selection, doc_content=None):
    """执行一次修订测试并返回结果"""
    if doc_content is None:
        doc_content = read_file(file_name)

    payload = {
        "text": selection,
        "action_type": "revision",
        "session_id": f"batch_{name}",
        "is_new_task": True,
        "context_source": "revision",
        "context_meta": {"file_name": file_name, "language": file_name.split(".")[-1]},
        "context_envelope": {
            "source": "ide", "content": doc_content,
            "selection": selection, "task": "文档修订",
            "meta": {"file_name": file_name}
        }
    }

    print(f"  [{name}] Sending ({len(doc_content)} doc / {len(selection)} sel)...", end=" ", flush=True)
    start = time.time()
    full = ""
    try:
        with httpx.Client(timeout=httpx.Timeout(120.0, connect=5.0), verify=False) as c:
            with c.stream("POST", AGENT_URL, json=payload) as r:
                for line in r.iter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try: full += json.loads(line[6:])["chunk"]
                        except: pass
        elapsed = time.time() - start
        display = re.sub(r'<think>.*?</think>', '', full, flags=re.DOTALL)
        if '<think>' in display:
            display = display.split('<think>')[0]
        print(f"✅ {elapsed:.0f}s, {len(full)} raw / {len(display)} disp")
        return {"success": True, "raw": full, "display": display, "elapsed": elapsed}
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ {elapsed:.0f}s: {e}")
        return {"success": False, "error": str(e), "elapsed": elapsed}


if __name__ == "__main__":
    results = {}
    fail_count = 0

    # ====== 测试 5: 预算报告 - 数字联动（极端：多处数字依赖） ======
    doc5 = read_file("budget_report.md")
    results["t5_budget"] = test_revision(
        "t5_budget", "budget_report.md",
        "2025 年度市场部总预算 800 万元",
        doc5
    )

    # ====== 测试 6: 预算报告 - Q4 具体数字修改 ======
    results["t6_budget_q4"] = test_revision(
        "t6_budget_q4", "budget_report.md",
        "SEM | 80 | 60 | ROI 从 3.2 降至 2.8",
        doc5
    )

    # ====== 测试 7: API 文档 - 版本号变更联动 ======
    doc7 = read_file("api_spec.md")
    results["t7_api_version"] = test_revision(
        "t7_api_version", "api_spec.md",
        "Payment Gateway API v2.3 接口文档",
        doc7
    )

    # ====== 测试 8: 产品规格 - 型号参数修改 ======
    doc8 = read_file("product_spec.md")
    results["t8_product_spec"] = test_revision(
        "t8_product_spec", "product_spec.md",
        "SL-P100 | 星空灰 | 1999 元",
        doc8
    )

    # ====== 测试 9: 中英混杂 + 术语不一致 ======
    doc9 = read_file("mixed_release_note.md")
    results["t9_mixed_lang"] = test_revision(
        "t9_mixed_lang", "mixed_release_note.md",
        "需要注意特权代理需在原生终端运行",
        doc9
    )

    # ====== 测试 10: 极短文档 ======
    doc10 = read_file("tiny_doc.md")
    results["t10_tiny"] = test_revision(
        "t10_tiny", "tiny_doc.md",
        "价格是 100 元",
        doc10
    )

    # ====== 测试 11: 维修手册 .docx（含表格） ======
    # 先通过 Broker 读 .docx
    try:
        TOKEN = open(os.path.expanduser("~/.asu_broker_token")).read().strip()
        r = httpx.post("http://127.0.0.1:18889/api/v1/system/fs/office/read",
                       json={"file_path": os.path.join(TEST_DIR, "repair_manual.docx")},
                       headers={"Authorization": f"Bearer {TOKEN}"}, timeout=15.0)
        if r.status_code == 200:
            doc11 = r.json()["data"]["content"]
            results["t11_docx_table"] = test_revision(
                "t11_docx_table", "repair_manual.docx",
                "SL-P300 整机质保 3 年",
                doc11
            )
        else:
            results["t11_docx_table"] = {"success": False, "error": f"Broker read failed: {r.text}"}
    except Exception as e:
        results["t11_docx_table"] = {"success": False, "error": f"Broker exception: {e}"}

    # ====== 测试 12: 长文档 - 大量重复文本 ======
    try:
        r = httpx.post("http://127.0.0.1:18889/api/v1/system/fs/office/read",
                       json={"file_path": os.path.join(TEST_DIR, "long_whitepaper.docx")},
                       headers={"Authorization": f"Bearer {TOKEN}"}, timeout=15.0)
        if r.status_code == 200:
            doc12 = r.json()["data"]["content"]
            results["t12_long"] = test_revision(
                "t12_long", "long_whitepaper.docx",
                "项目负责人为张总，联系邮箱 zhang@corp.com",
                doc12
            )
        else:
            results["t12_long"] = {"success": False, "error": f"Broker read failed: {r.text}"}
    except Exception as e:
        results["t12_long"] = {"success": False, "error": f"Broker exception: {e}"}

    # ── 统计 ──
    for name, r in results.items():
        if not r.get("success"):
            fail_count += 1
            print(f"  ⚠️ {name}: FAILED - {r.get('error','')}")

    success_count = len(results) - fail_count
    print(f"\n{'='*50}")
    print(f"  Total: {len(results)}  |  ✅ {success_count}  |  ❌ {fail_count}")
    print(f"{'='*50}")

    # 保存
    out = {k: {"display": v.get("display",""), "raw": v.get("raw",""),
               "success": v.get("success"), "elapsed": v.get("elapsed"),
               "error": v.get("error","")} for k, v in results.items()}
    with open(os.path.join(TEST_DIR, "_batch_results.json"), 'w') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Results saved to _batch_results.json")
