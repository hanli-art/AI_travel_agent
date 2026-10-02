"""P3 端到端验收：调用运行中的 /chat 接口，保存中文回复作为验收证据。"""
import json
import os
import sys
import time

import requests

BASE = "http://127.0.0.1:8000"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "p3_acceptance_reply.md")

MSG = "请帮我规划从福建省福州市福州飞南路86号到浙江省杭州市雷峰塔进行6天5夜自驾游路线"


def main():
    payload = {"message": MSG, "user_id": "user_001", "session_id": "p3-acceptance"}
    t0 = time.time()
    resp = requests.post(f"{BASE}/chat", json=payload, timeout=300)
    resp.raise_for_status()
    data = resp.json()
    reply = data.get("reply", "")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(reply)
    print(f"HTTP {resp.status_code} | elapsed={time.time() - t0:.1f}s | reply_len={len(reply)}")
    print(f"saved -> {OUT}")
    print("----- first 400 chars -----")
    print(reply[:400])


if __name__ == "__main__":
    main()
