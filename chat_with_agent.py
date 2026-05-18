import sys
import subprocess
import os
import uuid
from llm_provider import ProviderFactory

def is_agent_running():
    # 检查 18888 端口是否在监听
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:18888/v1/agent/chat", timeout=1)
        return True
    except Exception as e:
        if hasattr(e, 'code') and e.code == 404: # 我们定制的服务对于GET可能返回404，说明活着
            return True
        return False

def main():
    print("🤖 正在初始化与 ASU 定制智能体的连接...")
    
    if not is_agent_running():
        print("⚠️ 未检测到后台智能体服务运行在 18888 端口。")
        print("正在尝试在后台启动 ASU 定制智能体...")
        try:
            agent_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "asu_custom_agent.py")
            subprocess.Popen(
                [sys.executable, agent_script], 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            import time
            time.sleep(2) # 等待服务启动
        except Exception as e:
            print(f"❌ 启动服务失败: {e}")
            return

    # 获取 ASUCustomAgentClient
    provider = ProviderFactory.create_provider()
    session_id = str(uuid.uuid4())
    
    print("✅ 连接准备就绪。输入你的问题开始对话 (输入 'quit' 或 'exit' 退出):\n")
    
    # 首次触发默认状态
    is_new_task = True
    
    while True:
        try:
            user_input = input("你: ")
            if user_input.lower() in ['quit', 'exit']:
                print("👋 再见！")
                break
            
            if not user_input.strip():
                continue
                
            print("智能体: ", end="", flush=True)
            
            for chunk in provider.stream_agent_task(user_input, action_type="default", session_id=session_id, is_new_task=is_new_task):
                print(chunk, end="", flush=True)
                
            print("\n")
            is_new_task = False # 后续都在同一 session 进行
            
        except KeyboardInterrupt:
            print("\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")

if __name__ == "__main__":
    main()
