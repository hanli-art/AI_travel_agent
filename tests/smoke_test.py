"""P0 冒烟测试：验证服务启动、首页可访问、/chat 接口链路通畅。

用法：
    python tests/smoke_test.py                # 轻量测试（不触发工具调用）
    python tests/smoke_test.py "福州到杭州6天5夜自驾游路线"   # 自定义提问
"""
import sys

import requests

BASE = "http://127.0.0.1:8000"


def test_home() -> bool:
    r = requests.get(f"{BASE}/", timeout=10)
    print(f"[首页] status={r.status_code} 内容长度={len(r.text)}")
    return r.status_code == 200


def test_chat(message: str) -> bool:
    print(f"[提问] {message}")
    r = requests.post(
        f"{BASE}/chat",
        json={"message": message, "user_id": "smoke_test"},
        timeout=300,
    )
    data = r.json()
    reply = data.get("reply", "")
    print(f"[响应] status={r.status_code} 回复长度={len(reply)}")
    print("-" * 60)
    print(reply[:1500])
    print("-" * 60)
    return r.status_code == 200 and len(reply) > 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    msg = sys.argv[1] if len(sys.argv) > 1 else "你好，请用一句话介绍你自己"
    ok_home = test_home()
    ok_chat = test_chat(msg)
    print(f"\n结果: 首页={'通过' if ok_home else '失败'} / 对话={'通过' if ok_chat else '失败'}")
    sys.exit(0 if (ok_home and ok_chat) else 1)
