import os
import httpx
import json

api_key = "sk-cp-5Ta1Ur5ytb4uy4HPVW9Pu6Gcox0-maiU4TGZ-GQs22JeGHPY-7jhoh2n0boUE6IUp9ilRJrMPQjaVNOP9Z61Lw-8qY8k7p0huF-vxcI6MuqNdaD3Jjxgap0"
base_url = "https://api.minimax.chat/v1/chat/completions"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}
payload = {
    "model": "MiniMax-Text-01",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": True
}

with httpx.Client() as client:
    response = client.post(base_url, headers=headers, json=payload)
    print("MiniMax-Text-01 Response:", response.status_code, response.text)

payload["model"] = "MiniMax-M2.7"
with httpx.Client() as client:
    response = client.post(base_url, headers=headers, json=payload)
    print("MiniMax-M2.7 Response:", response.status_code, response.text)

