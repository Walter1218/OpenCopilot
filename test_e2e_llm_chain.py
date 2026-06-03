"""
OpenCopilot 端到端全链路真实 LLM 调用测试

测试策略：
  - 只控制输入，调用完整的 OpenCopilot 业务代码
  - 对输出做结构/语义断言（非精确匹配）
  - 覆盖所有核心链路：Provider → Agent Server → API Gateway

链路 1: MiMoProvider 直接调用 → MiMo API
链路 2: Agent Server (18888) → Pipeline → MiMoProvider → MiMo API
链路 3: API Gateway (8088) → _call_agent_pipeline → Agent Server → Pipeline → MiMo API

运行方式:
  python test_e2e_llm_chain.py
"""

import os
import sys
import json
import time
import uuid
import signal
import subprocess
import traceback
from typing import Optional

import httpx

# 确保项目根目录在 path 中
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# ==========================================
# 测试配置
# ==========================================
AGENT_PORT = 18888
API_PORT = 8088
AGENT_BASE_URL = f"http://127.0.0.1:{AGENT_PORT}"
API_BASE_URL = f"http://127.0.0.1:{API_PORT}"

# 测试结果收集
TEST_RESULTS = []
PASS_COUNT = 0
FAIL_COUNT = 0


def record_test(name: str, passed: bool, detail: str = ""):
    global PASS_COUNT, FAIL_COUNT
    if passed:
        PASS_COUNT += 1
        status = "PASS"
    else:
        FAIL_COUNT += 1
        status = "FAIL"
    TEST_RESULTS.append({"name": name, "status": status, "detail": detail})
    icon = "✅" if passed else "❌"
    print(f"  {icon} [{status}] {name}" + (f" — {detail}" if detail and not passed else ""))


def assert_true(condition: bool, name: str, detail: str = ""):
    record_test(name, condition, detail)


def assert_not_empty(value, name: str):
    if value is None:
        record_test(name, False, "值为 None")
    elif isinstance(value, str) and len(value.strip()) == 0:
        record_test(name, False, "值为空字符串")
    elif isinstance(value, (list, dict)) and len(value) == 0:
        record_test(name, False, "值为空容器")
    else:
        record_test(name, True)


def assert_no_error_marker(value: str, name: str):
    """断言输出中不包含错误标记"""
    error_markers = ["[MiMo API Error]", "[MiMo 连接失败]", "[Agent Error]", "[连接后台智能体失败]", "[Agent Server Error]"]
    for marker in error_markers:
        if marker in value:
            record_test(name, False, f"包含错误标记: {marker}")
            return
    record_test(name, True)


def assert_contains_keywords(value: str, keywords: list, name: str):
    """断言输出中至少包含一个关键词"""
    found = any(kw in value for kw in keywords)
    if found:
        record_test(name, True)
    else:
        record_test(name, False, f"未找到任何关键词: {keywords}")


def assert_response_time(elapsed: float, max_seconds: float, name: str):
    """断言响应时间"""
    record_test(name, elapsed < max_seconds, f"耗时 {elapsed:.1f}s > {max_seconds}s")


# ==========================================
# 服务管理
# ==========================================
agent_process: Optional[subprocess.Popen] = None
api_process: Optional[subprocess.Popen] = None


def start_agent_server():
    """启动 Agent Server (18888)"""
    global agent_process
    print("\n🚀 启动 Agent Server (port 18888)...")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    agent_process = subprocess.Popen(
        [sys.executable, "asu_custom_agent.py"],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    # 等待服务就绪
    for _ in range(30):
        try:
            resp = httpx.get(f"{AGENT_BASE_URL}/health", timeout=2.0)
            if resp.status_code == 200:
                print("  ✅ Agent Server 已就绪")
                return True
        except Exception:
            pass
        time.sleep(1)
    print("  ❌ Agent Server 启动超时")
    return False


def start_api_gateway():
    """启动 API Gateway (8088)"""
    global api_process
    print("\n🚀 启动 API Gateway (port 8088)...")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    api_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "smart_copilot_api:app",
         "--host", "127.0.0.1", "--port", str(API_PORT)],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    # 等待服务就绪
    for _ in range(20):
        try:
            resp = httpx.get(f"{API_BASE_URL}/health", timeout=2.0)
            if resp.status_code == 200:
                print("  ✅ API Gateway 已就绪")
                return True
        except Exception:
            pass
        time.sleep(1)
    print("  ❌ API Gateway 启动超时")
    return False


def stop_services():
    """停止所有服务"""
    global agent_process, api_process
    print("\n🛑 停止服务...")
    for proc, name in [(api_process, "API Gateway"), (agent_process, "Agent Server")]:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            print(f"  ✅ {name} 已停止")


# ==========================================
# 链路 1: MiMoProvider 直接调用测试
# ==========================================
def test_chain1_mimo_direct():
    """链路 1: MiMoProvider → MiMo API"""
    print("\n" + "=" * 60)
    print("链路 1: MiMoProvider 直接调用 → MiMo API")
    print("=" * 60)

    from llm_provider import MiMoProvider

    provider = MiMoProvider()

    # 1.1 非流式调用
    print("\n  [1.1] 非流式调用...")
    messages = [
        {"role": "system", "content": "你是一个简洁的助手，请用一句话回答。"},
        {"role": "user", "content": "1+1等于几？只回答数字。"},
    ]
    t0 = time.time()
    result = provider._do_non_stream(messages)
    elapsed = time.time() - t0

    content = result.get("content", "")
    assert_not_empty(content, "[1.1a] 非流式返回内容非空")
    assert_no_error_marker(content, "[1.1b] 非流式无错误标记")
    assert_contains_keywords(content, ["2", "二"], "[1.1c] 非流式语义正确（包含'2'或'二'）")
    assert_response_time(elapsed, 30.0, "[1.1d] 非流式响应时间 < 30s")

    # 1.2 流式调用
    print("  [1.2] 流式调用...")
    chunks = []
    t0 = time.time()
    for chunk in provider.stream_chat("请说'你好世界'", system_prompt="请只输出指定内容"):
        if isinstance(chunk, str):
            chunks.append(chunk)
    elapsed = time.time() - t0
    full_text = "".join(chunks)

    assert_not_empty(full_text, "[1.2a] 流式返回内容非空")
    assert_no_error_marker(full_text, "[1.2b] 流式无错误标记")
    assert_response_time(elapsed, 30.0, "[1.2c] 流式响应时间 < 30s")

    # 1.3 带历史消息的流式调用
    print("  [1.3] 带历史消息的流式调用...")
    history_messages = [
        {"role": "system", "content": "你是一个简洁的助手。"},
        {"role": "user", "content": "我叫小明"},
        {"role": "assistant", "content": "你好，小明！"},
        {"role": "user", "content": "我叫什么名字？只回答名字。"},
    ]
    chunks = []
    t0 = time.time()
    for chunk in provider.stream_chat_with_history(history_messages):
        if isinstance(chunk, str):
            chunks.append(chunk)
    elapsed = time.time() - t0
    full_text = "".join(chunks)

    assert_not_empty(full_text, "[1.3a] 历史消息流式返回非空")
    assert_no_error_marker(full_text, "[1.3b] 历史消息流式无错误标记")
    assert_contains_keywords(full_text, ["小明"], "[1.3c] 历史消息语义正确（记住'小明'）")
    assert_response_time(elapsed, 30.0, "[1.3d] 历史消息流式响应时间 < 30s")

    # 1.4 计费统计
    print("  [1.4] 计费统计...")
    stats = provider.get_usage_stats()
    assert_true(stats.get("total_requests", 0) > 0, "[1.4a] 计费统计有请求记录")
    assert_true(stats.get("total_input_tokens", 0) > 0, "[1.4b] 计费统计有输入 token")
    assert_true(stats.get("total_output_tokens", 0) > 0, "[1.4c] 计费统计有输出 token")
    assert_true(stats.get("total_cost_cny", 0) > 0, "[1.4d] 计费统计有费用")
    assert_true("billing_mode" in stats, "[1.4e] 计费统计包含 billing_mode")


# ==========================================
# 链路 2: Agent Server 直接调用测试
# ==========================================
def call_agent_sse(text: str, action_type: str = "default",
                   session_id: str = None, is_new_task: bool = True,
                   enable_web_search: bool = False,
                   timeout: float = 180.0) -> dict:
    """调用 Agent Server SSE 接口，返回 {content, annotations, elapsed, error}"""
    if not session_id:
        session_id = str(uuid.uuid4())

    payload = {
        "text": text,
        "action_type": action_type,
        "session_id": session_id,
        "is_new_task": is_new_task,
        "context_source": "chat",
        "context_meta": {},
    }
    if enable_web_search:
        payload["enable_web_search"] = True

    t0 = time.time()
    full_text = ""
    annotations = []
    error = None

    try:
        with httpx.Client(timeout=httpx.Timeout(connect=10.0, read=timeout, write=10.0, pool=10.0)) as client:
            with client.stream("POST", f"{AGENT_BASE_URL}/v1/agent/chat", json=payload) as resp:
                if resp.status_code != 200:
                    return {"content": f"[HTTP {resp.status_code}] {resp.text}", "annotations": [], "elapsed": time.time() - t0, "error": f"HTTP {resp.status_code}"}
                for line in resp.iter_lines():
                    if line == "data: [DONE]":
                        break
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            chunk = data.get("chunk", "")
                            if chunk:
                                full_text += chunk
                            ann = data.get("annotations")
                            if ann:
                                annotations.extend(ann)
                        except json.JSONDecodeError:
                            pass
    except httpx.ReadTimeout:
        error = "ReadTimeout"
    except httpx.ConnectTimeout:
        error = "ConnectTimeout"
    except Exception as e:
        error = str(e)

    elapsed = time.time() - t0
    return {"content": full_text, "annotations": annotations, "elapsed": elapsed, "error": error}


def test_chain2_agent_server():
    """链路 2: Agent Server (18888) → Pipeline → MiMoProvider → MiMo API"""
    print("\n" + "=" * 60)
    print("链路 2: Agent Server → Pipeline → MiMoProvider → MiMo API")
    print("=" * 60)

    # 2.1 健康检查
    print("  [2.1] Agent Server 健康检查...")
    try:
        resp = httpx.get(f"{AGENT_BASE_URL}/health", timeout=5.0)
        assert_true(resp.status_code == 200, "[2.1a] Agent Server 健康检查返回 200")
        data = resp.json()
        assert_true(data.get("status") == "ok", "[2.1b] Agent Server 状态为 ok")
    except Exception as e:
        record_test("[2.1a] Agent Server 健康检查", False, str(e))
        return  # Agent 不可用则跳过后续测试

    # 2.2 能力查询
    print("  [2.2] Agent Server 能力查询...")
    try:
        resp = httpx.get(f"{AGENT_BASE_URL}/capabilities", timeout=5.0)
        assert_true(resp.status_code == 200, "[2.2a] 能力查询返回 200")
        caps = resp.json()
        assert_true("capabilities" in caps, "[2.2b] 能力查询包含 capabilities 字段")
        cap_names = list(caps.get("capabilities", {}).keys())
        assert_true(len(cap_names) >= 5, f"[2.2c] 能力数量 >= 5 (实际: {len(cap_names)})")
    except Exception as e:
        record_test("[2.2a] 能力查询", False, str(e))

    # 2.3 普通对话 (action_type=default)
    print("  [2.3] 普通对话 (action_type=default)...")
    result = call_agent_sse("请说'测试成功'", action_type="default", timeout=120.0)
    if result.get("error"):
        record_test("[2.3a] 普通对话返回内容非空", False, f"请求异常: {result['error']}")
    else:
        assert_not_empty(result["content"], "[2.3a] 普通对话返回内容非空")
        assert_no_error_marker(result["content"], "[2.3b] 普通对话无错误标记")
        assert_response_time(result["elapsed"], 120.0, "[2.3c] 普通对话响应时间 < 120s")

    # 2.4 编码辅助 (action_type=coding) - 使用简短 prompt 避免 LLM 响应过长
    print("  [2.4] 编码辅助 (action_type=coding)...")
    result = call_agent_sse(
        "用Python写一个hello world",
        action_type="coding",
        timeout=180.0,
    )
    if result.get("error"):
        record_test("[2.4a] 编码辅助返回内容非空", False, f"请求异常: {result['error']}")
    else:
        assert_not_empty(result["content"], "[2.4a] 编码辅助返回内容非空")
        assert_no_error_marker(result["content"], "[2.4b] 编码辅助无错误标记")
        assert_contains_keywords(result["content"], ["python", "print", "hello", "def"], "[2.4c] 编码辅助包含代码相关内容")
        assert_response_time(result["elapsed"], 120.0, "[2.4d] 编码辅助响应时间 < 120s")

    # 2.5 多轮对话 (同一 session_id)
    print("  [2.5] 多轮对话 (同一 session_id)...")
    session_id = str(uuid.uuid4())
    # 第一轮
    r1 = call_agent_sse("我叫小红", action_type="chat", session_id=session_id, is_new_task=True)
    if r1.get("error"):
        record_test("[2.5a] 多轮对话第一轮返回非空", False, f"请求异常: {r1['error']}")
    else:
        assert_not_empty(r1["content"], "[2.5a] 多轮对话第一轮返回非空")
    # 第二轮
    r2 = call_agent_sse("我叫什么名字？只回答名字。", action_type="chat", session_id=session_id, is_new_task=False)
    if r2.get("error"):
        record_test("[2.5b] 多轮对话第二轮返回非空", False, f"请求异常: {r2['error']}")
    else:
        assert_not_empty(r2["content"], "[2.5b] 多轮对话第二轮返回非空")
        assert_no_error_marker(r2["content"], "[2.5c] 多轮对话第二轮无错误标记")
        assert_contains_keywords(r2["content"], ["小红"], "[2.5d] 多轮对话记住上下文（'小红'）")

    # 2.6 PPT 相关 (action_type=ppt)
    print("  [2.6] PPT 相关 (action_type=ppt)...")
    result = call_agent_sse("帮我写一个关于AI的PPT标题", action_type="ppt", timeout=180.0)
    if result.get("error"):
        record_test("[2.6a] PPT 返回内容非空", False, f"请求异常: {result['error']}")
    else:
        assert_not_empty(result["content"], "[2.6a] PPT 返回内容非空")
        assert_no_error_marker(result["content"], "[2.6b] PPT 无错误标记")
        assert_response_time(result["elapsed"], 120.0, "[2.6c] PPT 响应时间 < 120s")

    # 2.7 追踪查询
    print("  [2.7] 追踪查询...")
    try:
        resp = httpx.get(f"{AGENT_BASE_URL}/traces/stats", timeout=5.0)
        assert_true(resp.status_code == 200, "[2.7a] 追踪统计返回 200")
        stats = resp.json()
        assert_true(isinstance(stats, dict), "[2.7b] 追踪统计返回字典")
    except Exception as e:
        record_test("[2.7a] 追踪查询", False, str(e))


# ==========================================
# 链路 3: API Gateway → Agent Server 测试
# ==========================================
def test_chain3_api_gateway():
    """链路 3: API Gateway (8088) → _call_agent_pipeline → Agent Server → Pipeline → MiMo"""
    print("\n" + "=" * 60)
    print("链路 3: API Gateway → Agent Server → Pipeline → MiMo API")
    print("=" * 60)

    # 3.1 API Gateway 健康检查
    print("  [3.1] API Gateway 健康检查...")
    try:
        resp = httpx.get(f"{API_BASE_URL}/health", timeout=5.0)
        assert_true(resp.status_code == 200, "[3.1a] API Gateway 健康检查返回 200")
    except Exception as e:
        record_test("[3.1a] API Gateway 健康检查", False, str(e))
        return

    # 3.2 /api/chat 非流式
    print("  [3.2] /api/chat 非流式对话...")
    payload = {
        "message": "请说'API测试成功'",
        "context_source": "chat",
    }
    t0 = time.time()
    try:
        resp = httpx.post(f"{API_BASE_URL}/api/chat", json=payload, timeout=120.0)
        elapsed = time.time() - t0
        assert_true(resp.status_code == 200, f"[3.2a] /api/chat 返回 200 (实际: {resp.status_code})")
        if resp.status_code == 200:
            data = resp.json()
            response_text = data.get("response", "")
            assert_not_empty(response_text, "[3.2b] /api/chat 返回 response 非空")
            assert_no_error_marker(response_text, "[3.2c] /api/chat 无错误标记")
            assert_response_time(elapsed, 60.0, "[3.2d] /api/chat 响应时间 < 60s")
    except Exception as e:
        record_test("[3.2a] /api/chat", False, str(e))

    # 3.3 /api/chat/stream 流式
    print("  [3.3] /api/chat/stream 流式对话...")
    payload = {
        "message": "用一句话介绍Python",
        "context_source": "chat",
        "stream": True,
    }
    t0 = time.time()
    full_text = ""
    try:
        with httpx.Client(timeout=httpx.Timeout(connect=10.0, read=120.0)) as client:
            with client.stream("POST", f"{API_BASE_URL}/api/chat/stream", json=payload) as resp:
                assert_true(resp.status_code == 200, f"[3.3a] /api/chat/stream 返回 200 (实际: {resp.status_code})")
                for line in resp.iter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            data = json.loads(line[6:])
                            chunk = data.get("chunk", "")
                            if chunk:
                                full_text += chunk
                        except json.JSONDecodeError:
                            pass
        elapsed = time.time() - t0
        assert_not_empty(full_text, "[3.3b] /api/chat/stream 返回内容非空")
        assert_no_error_marker(full_text, "[3.3c] /api/chat/stream 无错误标记")
        assert_response_time(elapsed, 60.0, "[3.3d] /api/chat/stream 响应时间 < 60s")
    except Exception as e:
        record_test("[3.3a] /api/chat/stream", False, str(e))

    # 3.4 /api/text/process 文本处理
    print("  [3.4] /api/text/process 文本翻译...")
    payload = {
        "text": "Hello, how are you?",
        "action": "translate",
        "target_language": "zh",
    }
    try:
        resp = httpx.post(f"{API_BASE_URL}/api/text/process", json=payload, timeout=120.0)
        assert_true(resp.status_code == 200, f"[3.4a] /api/text/process 返回 200 (实际: {resp.status_code})")
        if resp.status_code == 200:
            data = resp.json()
            processed = data.get("processed", "")
            assert_not_empty(processed, "[3.4b] /api/text/process 返回 processed 非空")
            assert_contains_keywords(processed, ["你好", "你", "吗"], "[3.4c] 翻译语义正确（包含中文问候）")
    except Exception as e:
        record_test("[3.4a] /api/text/process", False, str(e))

    # 3.5 /api/coding/review 代码审查
    print("  [3.5] /api/coding/review 代码审查...")
    payload = {
        "code": "def add(a, b):\n    return a + b",
        "language": "python",
    }
    try:
        resp = httpx.post(f"{API_BASE_URL}/api/coding/review", json=payload, timeout=120.0)
        assert_true(resp.status_code == 200, f"[3.5a] /api/coding/review 返回 200 (实际: {resp.status_code})")
        if resp.status_code == 200:
            data = resp.json()
            review = data.get("review", data.get("result", ""))
            assert_not_empty(review, "[3.5b] /api/coding/review 返回 review 非空")
    except Exception as e:
        record_test("[3.5a] /api/coding/review", False, str(e))

    # 3.6 系统状态
    print("  [3.6] /api/system/status 系统状态...")
    try:
        resp = httpx.get(f"{API_BASE_URL}/api/system/status", timeout=10.0)
        assert_true(resp.status_code == 200, f"[3.6a] /api/system/status 返回 200 (实际: {resp.status_code})")
        if resp.status_code == 200:
            data = resp.json()
            assert_true("agent_online" in data, "[3.6b] 系统状态包含 agent_online")
            assert_true(data.get("agent_online") is True, "[3.6c] Agent 在线状态为 True")
    except Exception as e:
        record_test("[3.6a] /api/system/status", False, str(e))

    # 3.7 配置查询
    print("  [3.7] /api/config 配置查询...")
    try:
        resp = httpx.get(f"{API_BASE_URL}/api/config", timeout=10.0)
        assert_true(resp.status_code == 200, f"[3.7a] /api/config 返回 200 (实际: {resp.status_code})")
        if resp.status_code == 200:
            data = resp.json()
            assert_true("provider_type" in data or "config" in data, "[3.7b] 配置包含 provider_type")
    except Exception as e:
        record_test("[3.7a] /api/config", False, str(e))


# ==========================================
# 链路 4: ASUCustomAgentClient 测试
# ==========================================
def test_chain4_asu_client():
    """链路 4: ASUCustomAgentClient → Agent Server → Pipeline → MiMo"""
    print("\n" + "=" * 60)
    print("链路 4: ASUCustomAgentClient → Agent Server → MiMo API")
    print("=" * 60)

    from llm_provider import ASUCustomAgentClient

    client = ASUCustomAgentClient()

    # 4.1 stream_agent_task
    print("  [4.1] stream_agent_task 默认任务...")
    chunks = []
    t0 = time.time()
    try:
        for chunk in client.stream_agent_task(
            text="请说'客户端测试成功'",
            action_type="default",
            session_id=str(uuid.uuid4()),
            is_new_task=True,
        ):
            if isinstance(chunk, str):
                chunks.append(chunk)
        elapsed = time.time() - t0
        full_text = "".join(chunks)
        assert_not_empty(full_text, "[4.1a] stream_agent_task 返回内容非空")
        assert_no_error_marker(full_text, "[4.1b] stream_agent_task 无错误标记")
        assert_response_time(elapsed, 120.0, "[4.1c] stream_agent_task 响应时间 < 120s")
    except Exception as e:
        record_test("[4.1a] stream_agent_task", False, str(e))

    # 4.2 stream_chat (兼容旧接口)
    print("  [4.2] stream_chat 兼容接口...")
    chunks = []
    t0 = time.time()
    try:
        for chunk in client.stream_chat("1+1等于几？只回答数字。"):
            if isinstance(chunk, str):
                chunks.append(chunk)
        elapsed = time.time() - t0
        full_text = "".join(chunks)
        assert_not_empty(full_text, "[4.2a] stream_chat 返回内容非空")
        assert_no_error_marker(full_text, "[4.2b] stream_chat 无错误标记")
        assert_response_time(elapsed, 60.0, "[4.2c] stream_chat 响应时间 < 60s")
    except Exception as e:
        record_test("[4.2a] stream_chat", False, str(e))

    # 4.3 stream_chat_with_history (兼容旧接口)
    print("  [4.3] stream_chat_with_history 兼容接口...")
    messages = [
        {"role": "system", "content": "你是一个助手"},
        {"role": "user", "content": "我叫小蓝"},
        {"role": "assistant", "content": "你好小蓝！"},
        {"role": "user", "content": "我叫什么名字？只回答名字。"},
    ]
    chunks = []
    try:
        for chunk in client.stream_chat_with_history(messages):
            if isinstance(chunk, str):
                chunks.append(chunk)
        full_text = "".join(chunks)
        assert_not_empty(full_text, "[4.3a] stream_chat_with_history 返回非空")
        assert_no_error_marker(full_text, "[4.3b] stream_chat_with_history 无错误标记")
    except Exception as e:
        record_test("[4.3a] stream_chat_with_history", False, str(e))


# ==========================================
# 链路 5: FailoverProvider 测试
# ==========================================
def test_chain5_failover():
    """链路 5: FailoverProvider 故障转移"""
    print("\n" + "=" * 60)
    print("链路 5: FailoverProvider 故障转移测试")
    print("=" * 60)

    from llm_provider import FailoverProvider

    provider = FailoverProvider()

    # 5.1 正常调用
    print("  [5.1] FailoverProvider 正常调用...")
    chunks = []
    t0 = time.time()
    try:
        for chunk in provider.stream_chat("请说'故障转移测试成功'", system_prompt="请只输出指定内容"):
            if isinstance(chunk, str):
                chunks.append(chunk)
        elapsed = time.time() - t0
        full_text = "".join(chunks)
        assert_not_empty(full_text, "[5.1a] FailoverProvider 返回内容非空")
        assert_no_error_marker(full_text, "[5.1b] FailoverProvider 无错误标记")
        assert_response_time(elapsed, 60.0, "[5.1c] FailoverProvider 响应时间 < 60s")
    except Exception as e:
        record_test("[5.1a] FailoverProvider", False, str(e))

    # 5.2 Failover 状态查询
    print("  [5.2] FailoverProvider 状态查询...")
    status = provider.get_status()
    assert_true("current_provider" in status, "[5.2a] 状态包含 current_provider")
    assert_true("providers" in status, "[5.2b] 状态包含 providers 列表")
    assert_true(len(status.get("providers", [])) > 0, "[5.2c] providers 列表非空")


# ==========================================
# 主测试流程
# ==========================================
def main():
    print("=" * 60)
    print("OpenCopilot 端到端全链路 LLM 调用测试")
    print("=" * 60)
    print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"项目: {PROJECT_ROOT}")

    try:
        # ---- 链路 1: MiMoProvider 直接调用（无需服务） ----
        test_chain1_mimo_direct()

        # ---- 启动 Agent Server ----
        if not start_agent_server():
            print("\n⚠️ Agent Server 无法启动，跳过链路 2-5 测试")
            print_summary()
            return

        # ---- 链路 2: Agent Server 直接调用 ----
        test_chain2_agent_server()

        # ---- 链路 4: ASUCustomAgentClient ----
        test_chain4_asu_client()

        # ---- 链路 5: FailoverProvider ----
        test_chain5_failover()

        # ---- 启动 API Gateway ----
        if start_api_gateway():
            # ---- 链路 3: API Gateway → Agent Server ----
            test_chain3_api_gateway()
        else:
            print("\n⚠️ API Gateway 无法启动，跳过链路 3 测试")

    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被中断")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        traceback.print_exc()
    finally:
        stop_services()

    print_summary()


def print_summary():
    """打印测试总结"""
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)
    print(f"  通过: {PASS_COUNT}")
    print(f"  失败: {FAIL_COUNT}")
    print(f"  总计: {PASS_COUNT + FAIL_COUNT}")
    print(f"  通过率: {PASS_COUNT / max(1, PASS_COUNT + FAIL_COUNT) * 100:.1f}%")

    if FAIL_COUNT > 0:
        print("\n  ❌ 失败项:")
        for r in TEST_RESULTS:
            if r["status"] == "FAIL":
                print(f"    - {r['name']}: {r['detail']}")

    # 保存报告
    report_path = os.path.join(PROJECT_ROOT, "test_e2e_llm_report.json")
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": PASS_COUNT + FAIL_COUNT,
        "passed": PASS_COUNT,
        "failed": FAIL_COUNT,
        "pass_rate": f"{PASS_COUNT / max(1, PASS_COUNT + FAIL_COUNT) * 100:.1f}%",
        "results": TEST_RESULTS,
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n  📄 报告已保存: {report_path}")


if __name__ == "__main__":
    main()
