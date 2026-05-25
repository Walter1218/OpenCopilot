import os
import subprocess
import time
import requests
import json

PORT = 18888
URL = f"http://127.0.0.1:{PORT}/v1/agent/chat"

# Clean DB before start to ensure fresh state
DB_PATH = "asu_agent.db"
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

def start_agent():
    print("启动 Agent...")
    proc = subprocess.Popen(["python", "asu_custom_agent.py"])
    time.sleep(2) # wait for server to start
    return proc

def send_chat(text, session_id, action_type="default"):
    print(f"发送请求: '{text}' (session={session_id}, action={action_type})")
    payload = {
        "text": text,
        "session_id": session_id,
        "action_type": action_type,
        "context_source": "chat"
    }
    
    resp = requests.post(URL, json=payload, stream=True)
    full_text = ""
    for line in resp.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith("data: "):
                data_str = line_str[6:]
                if data_str == "[DONE]":
                    break
                try:
                    data_json = json.loads(data_str)
                    full_text += data_json.get("chunk", "")
                except:
                    pass
    print(f"收到回复: {full_text}")
    return full_text

# 验证 1: 记忆持久化
proc = start_agent()

print("\n--- 验证 1: 记忆持久化 ---")
session_id = "test_memory_123"
send_chat("请记住这个神秘代码: RED_DRAGON_007。直接回复'已记住'，不需要解释。", session_id)

print("\n[杀掉 Agent 进程以清空内存]")
proc.terminate()
proc.wait()

print("\n[重新启动 Agent 进程]")
proc = start_agent()

print("\n追问之前的神秘代码...")
answer1 = send_chat("我刚才告诉你的神秘代码是什么？直接告诉我代码，不需要别的解释。", session_id)
if "RED_DRAGON_007" in answer1:
    print("\n✅ 验证 1 成功：系统重启后记忆成功从 SQLite 中恢复！")
else:
    print("\n❌ 验证 1 失败：未能恢复记忆。")

# 验证 2: Persona 热加载
print("\n--- 验证 2: Persona 热加载 ---")

code_persona_path = os.path.join("personas", "code.md")
with open(code_persona_path, "r", encoding="utf-8") as f:
    original_code_persona = f.read()

new_code_persona = original_code_persona + "\n必须在回答的末尾加上一句：'喵喵喵！'"
with open(code_persona_path, "w", encoding="utf-8") as f:
    f.write(new_code_persona)

print("动态修改了 personas/code.md, 追加了'喵喵喵！'的要求...")

answer2 = send_chat("给我解释一下 print('hello world') 是什么意思", session_id="test_persona_456", action_type="code")

if "喵喵喵" in answer2:
    print("\n✅ 验证 2 成功：Persona 热加载生效（无需重启服务）！")
else:
    print("\n❌ 验证 2 失败：Persona 未热更新。")

# 恢复现场
with open(code_persona_path, "w", encoding="utf-8") as f:
    f.write(original_code_persona)

print("\n[清理环境]")
proc.terminate()
proc.wait()
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
