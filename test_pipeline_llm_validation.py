import sys
import json
import httpx
import time

AGENT_URL = "http://127.0.0.1:18888"

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

results = []
passed = 0
failed = 0

def record(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  {GREEN}PASS{RESET} {name}")
        results.append({"name": name, "status": "PASS", "detail": detail})
    else:
        failed += 1
        print(f"  {RED}FAIL{RESET} {name} — {detail}")
        results.append({"name": name, "status": "FAIL", "detail": detail})


def send_chat(text, action_type="default", session_id=None):
    import uuid
    payload = {
        "action_type": action_type,
        "text": text,
        "session_id": session_id or str(uuid.uuid4()),
    }
    chunks = []
    try:
        with httpx.Client(timeout=600.0) as client:
            with client.stream("POST", f"{AGENT_URL}/v1/agent/chat", json=payload) as resp:
                if resp.status_code != 200:
                    return {"error": f"HTTP {resp.status_code}", "chunks": []}
                for line in resp.iter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            data = json.loads(line[6:])
                            chunks.append(data.get("chunk", ""))
                        except:
                            pass
    except Exception as e:
        return {"error": str(e), "chunks": chunks}
    return {"chunks": chunks, "full": "".join(chunks)}


print(f"{BOLD}{CYAN}{'='*70}{RESET}")
print(f"{BOLD}{CYAN}  OpenCopilot 管线 LLM 验证 (600s超时){RESET}")
print(f"{BOLD}{CYAN}{'='*70}{RESET}")
print()

# ====== 测试0: 健康检查 ======
print(f"{BOLD}测试0: Agent 存活探针{RESET}")
try:
    r = httpx.get(f"{AGENT_URL}/health", timeout=3.0)
    record("健康检查端点", r.status_code == 200, f"status={r.status_code}")
except Exception as e:
    record("健康检查端点", False, str(e))

# ====== 测试1: 普通对话，走全7层管线 ======
print(f"\n{BOLD}测试1: 全管线 → LLM 返回{RESET}")
print(f"  {YELLOW}请求: '一句话介绍Python'{RESET}")
t1 = time.time()
resp1 = send_chat("一句话介绍Python", session_id="test001")
t1_elapsed = time.time() - t1

if resp1.get("full"):
    full1 = resp1["full"]
    has_content = len(full1) > 10
    record("LLM返回内容", has_content, f"{t1_elapsed:.1f}s, {len(full1)}字符")
    if full1:
        print(f"    {CYAN}响应: {full1[:150]}...{RESET}" if len(full1) > 150 else f"    {CYAN}响应: {full1}{RESET}")
else:
    record("LLM返回内容", False, resp1.get("error","?"))

# ====== 测试2: 权限保护 ======
print(f"\n{BOLD}测试2: SecurityGuard 新会话首次注册{RESET}")
t2 = time.time()
resp2 = send_chat("hello", session_id="test002")
t2_elapsed = time.time() - t2
full2 = resp2.get("full", "")
# 新会话应该先被拦截，然后 auto-register 后通过
ok2 = len(full2) > 5 and "权限" not in full2
record("新会话自动注册", ok2, f"{t2_elapsed:.1f}s, 返回{len(full2)}字符")
if full2:
    print(f"    {CYAN}响应: {full2[:120]}...{RESET}" if len(full2) > 120 else f"    {CYAN}响应: {full2}{RESET}")

# ====== 测试3: 多轮对话记忆 ======
print(f"\n{BOLD}测试3: MemoryManager 多轮记忆{RESET}")
session_mem = "mem_test_01"
send_chat("我叫张三，今年25岁", session_id=session_mem)
resp3b = send_chat("我叫什么名字？", session_id=session_mem)
full3b = resp3b.get("full", "")
has_memory = "张三" in full3b
record("多轮记忆", has_memory, f"记忆召回: {has_memory}")
print(f"    {CYAN}响应: {full3b[:150]}...{RESET}")

# ====== 测试4: 翻译 Persona ======
print(f"\n{BOLD}测试4: Persona 翻译角色{RESET}")
resp4 = send_chat("Hello World", action_type="translate")
full4 = resp4.get("full", "")
has_cn = any("\u4e00" <= c <= "\u9fff" for c in full4)
record("翻译Persona", has_cn, f"含中文: {has_cn}")
print(f"    {CYAN}响应: {full4[:120]}...{RESET}")

# ====== 测试5: 代码执行路由 ======
print(f"\n{BOLD}测试5: CapabilityRouter 代码执行{RESET}")
resp5 = send_chat("运行python代码: print(1+1)")
full5 = resp5.get("full", "")
record("代码执行路由", len(full5) > 0)
print(f"    {CYAN}响应: {full5[:200]}{RESET}")

# ====== 测试6: 复杂任务自动规划 ======
print(f"\n{BOLD}测试6: Planner 自动规划{RESET}")
t6 = time.time()
resp6 = send_chat("帮我设计一个用户注册系统的方案，包括前端页面、后端API、数据库设计三个模块")
t6_elapsed = time.time() - t6
full6 = resp6.get("full", "")
has_structure = any(kw in full6 for kw in ["注册","数据库","API","前端","后端","模块"]) and len(full6) > 50
record("自动规划", has_structure, f"{t6_elapsed:.1f}s, {len(full6)}字符")
print(f"    {CYAN}响应: {full6[:200]}...{RESET}")

# ====== 测试7: 正常内容不拦截 ======
print(f"\n{BOLD}测试7: 正常请求不受规影响{RESET}")
resp7 = send_chat("请帮我分析这段文本的质量")
full7 = resp7.get("full", "")
record("正常请求通过", len(full7) > 20, f"{len(full7)}字符")

# ====== 汇总 ======
print(f"\n{BOLD}{CYAN}{'='*70}{RESET}")
print(f"{BOLD}{CYAN}  验证结果汇总{RESET}")
print(f"{BOLD}{CYAN}{'='*70}{RESET}")
total = passed + failed
for r in results:
    icon = f"{GREEN}✓{RESET}" if r["status"] == "PASS" else f"{RED}✗{RESET}"
    print(f"  {icon} {r['name']}")
print(f"\n  总计: {total}  |  {GREEN}通过: {passed}{RESET}  |  {RED}失败: {failed}{RESET}  |  通过率: {passed/total*100:.0f}%")

json_path = "/tmp/pipeline_validation_results.json"
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump({"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "passed": passed, "failed": failed, "total": total, "results": results}, f, ensure_ascii=False, indent=2)
print(f"\n结果: {json_path}")
sys.exit(0 if failed == 0 else 1)
