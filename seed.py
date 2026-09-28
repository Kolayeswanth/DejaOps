import json
from memory import init_bank, retain_incident, retain_runbook, BANK_ID

def load(p):
    return json.load(open(p, encoding="utf-8"))

print("Seeding bank:", BANK_ID)
init_bank()
failed = []
for rb in load("data/runbooks.json"):
    try:
        retain_runbook(rb); print("runbook", rb["id"])
    except Exception as e:
        failed.append(("runbook", rb["id"], str(e)))
incs = load("data/incidents.json")
for n, inc in enumerate(incs, 1):
    try:
        retain_incident(inc); print(f"{n}/{len(incs)} {inc['id']}")
    except Exception as e:
        failed.append(("incident", inc["id"], str(e)))
print("Seeding done. Failed:", failed if failed else "none")