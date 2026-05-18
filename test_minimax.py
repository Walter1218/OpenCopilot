import os
from llm_provider import ProviderFactory
os.environ["MINIMAX_API_KEY"] = "sk-cp-5Ta1Ur5ytb4uy4HPVW9Pu6Gcox0-maiU4TGZ-GQs22JeGHPY-7jhoh2n0boUE6IUp9ilRJrMPQjaVNOP9Z61Lw-8qY8k7p0huF-vxcI6MuqNdaD3Jjxgap0"
provider = ProviderFactory.create_provider()
for chunk in provider.stream_chat("Hello", system_prompt="You are a helper."):
    print(chunk, end="", flush=True)
print("\nDone")
