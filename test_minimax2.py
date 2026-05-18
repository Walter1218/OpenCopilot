import os
import httpx
import json

api_key = "sk-cp-5Ta1Ur5ytb4uy4HPVW9Pu6Gcox0-maiU4TGZ-GQs22JeGHPY-7jhoh2n0boUE6IUp9ilRJrMPQjaVNOP9Z61Lw-8qY8k7p0huF-vxcI6MuqNdaD3Jjxgap0"
base_url = "https://api.minimax.chat/v1/text/chatcompletion_v2"
default_model = "MiniMax-Text-01"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}
payload = {
    "model": default_model,
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": True
}
print("Sending request...")
try:
    with httpx.Client() as client:
        with client.stream("POST", base_url, headers=headers, json=payload, timeout=30.0) as response:
            print("Status:", response.status_code)
            for line in response.iter_lines():
                print("LINE:", line)
except Exception as e:
    print("ERROR:", e)
