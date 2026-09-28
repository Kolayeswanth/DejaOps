"""Run before every demo:  python check_setup.py"""
import os
from memory import client, BANK_ID
print("Memory bank in use:", BANK_ID)
try:
    m = client.list_memories(bank_id=BANK_ID, limit=2000)
    rows = getattr(m, "items", None) or getattr(m, "results", None) or []
    print("Stored memories (max 200):", len(rows))
except Exception as e:
    print("list_memories failed:", e)
try:
    r = client.recall(bank_id=BANK_ID, query="incident", max_tokens=500, budget="low")
    print("Hindsight recall OK, results:", len(r.results))
except Exception as e:
    print("Hindsight FAILED:", e)
try:
    from groq import Groq
    Groq(api_key=os.environ["GROQ_API_KEY"]).chat.completions.create(
        model="openai/gpt-oss-120b", messages=[{"role": "user", "content": "ping"}], max_tokens=16)
    print("Groq OK")
except Exception as e:
    print("Groq FAILED:", e)