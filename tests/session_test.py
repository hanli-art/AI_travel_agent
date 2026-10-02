"""P2 会话隔离测试：验证不同 session_id 的对话上下文互不干扰。

用法（需先启动服务）：
    python tests/session_test.py
"""
import sqlite3
import sys
import time

import requests

BASE = "http://127.0.0.1:8000"
DB = r"D:\shixun\ai_agent\data\conversations.db"

STAMP = int(time.time())
SESSION_A = f"p2_test_a_{STAMP}"
SESSION_B = f"p2_test_b_{STAMP}"


def chat(message: str, session_id: str) -> str:
    r = requests.post(
        f"{BASE}/chat",
        json={"message": message, "user_id": "p2_test", "session_id": session_id},
        timeout=300,
    )
    return r.json().get("reply", "")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print(f"会话A={SESSION_A}")
    print(f"会话B={SESSION_B}\n")

    print("[会话A-第1轮] 告知预算与人数")
    chat("请记住：我的行程预算是 5000 元，出行人数是 3 人。", SESSION_A)

    print("[会话A-第2轮] 追问（同一会话应能答出）")
    reply_a = chat("我刚才告诉你的预算和人数分别是多少？", SESSION_A)
    print("  ->", reply_a[:200].replace("\n", " "))

    print("\n[会话B-第1轮] 同样追问（新会话应答不出）")
    reply_b = chat("我刚才告诉你的预算和人数分别是多少？", SESSION_B)
    print("  ->", reply_b[:200].replace("\n", " "))

    print("\n=== 数据库消息分布 ===")
    conn = sqlite3.connect(DB)
    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    ]
    print("表:", tables)
    for table in tables:
        cols = [c[1] for c in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if "session_id" in cols:
            rows = conn.execute(
                f"SELECT session_id, COUNT(*) FROM {table} "
                f"WHERE session_id LIKE 'p2_test_%' GROUP BY session_id"
            ).fetchall()
            print(f"  {table}: {rows}")
    conn.close()

    ok_context = "5000" in reply_a
    ok_isolated = "5000" not in reply_b
    print(
        f"\n结果: 同会话上下文={'通过' if ok_context else '失败'} / "
        f"跨会话隔离={'通过' if ok_isolated else '失败'}"
    )
    sys.exit(0 if (ok_context and ok_isolated) else 1)


if __name__ == "__main__":
    main()
