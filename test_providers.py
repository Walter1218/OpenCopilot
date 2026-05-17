import sys
import json
from llm_provider import ProviderFactory, OpenClawCLIProvider

def test_provider():
    try:
        provider = ProviderFactory.create_provider()
        print(f"Created provider: {type(provider).__name__}")
        
        if isinstance(provider, OpenClawCLIProvider):
            print(f"Agent name configured: {provider.agent_name}")
            print("Testing stream_chat...")
            for chunk in provider.stream_chat("hello"):
                print(chunk, end="", flush=True)
            print("\nStream chat test passed.")
        else:
            print("Not using OpenClaw provider. Please set provider_type to 'openclaw' in config.json")
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    test_provider()
