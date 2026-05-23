"""测试当前 Provider 的流式输出能力。"""
import sys
from llm_provider import ProviderFactory, ASUCustomAgentClient

def test_provider():
    try:
        provider = ProviderFactory.create_provider()
        print(f"Created provider: {type(provider).__name__}")

        if isinstance(provider, ASUCustomAgentClient):
            print(f"Agent endpoint: {provider.api_base}")
            print("Testing stream_agent_task...")
            for chunk in provider.stream_agent_task("hello", action_type="default", session_id="test", is_new_task=True):
                print(chunk, end="", flush=True)
            print("\nStream test passed.")
        else:
            print(f"Unknown provider type: {type(provider).__name__}")
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    test_provider()
