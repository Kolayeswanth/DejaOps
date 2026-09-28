import json, os
from memory import init_bank, retain_incident, retain_runbook, BANK_ID

load = lambda p: json.load(open(p, encoding="utf-8"))
done_file = f"data/.seeded_{BANK_ID}.txt"
done = set(open(done_file).read().split()) if os.path.exists(done_file) else set()
def mark(k):
    open(done_file, "a").write(k + "\n"); done.add(k)

print("Seeding bank:", BANK_ID, "| already done:", len(done))
init_bank()
failed = []
for rb in load("data/runbooks.json"):
    k = "rb:" + rb["id"]
    if k in done: continue
    try:
        retain_runbook(rb); mark(k); print("runbook", rb["id"])
    except Exception as e:
        failed.append((k, str(e)))
incs = load("data/incidents.json")
for n, inc in enumerate(incs, 1):
    k = "inc:" + inc["id"]
    if k in done: continue
    try:
        retain_incident(inc); mark(k); print(f"{n}/{len(incs)} {inc['id']}")
    except Exception as e:
        failed.append((k, str(e)))
print("Done. Failed:", failed or "none")