import json
from memory import init_bank, retain_incident, retain_runbook

init_bank()
for rb in json.load(open("data/runbooks.json")):
    retain_runbook(rb); print("runbook", rb["id"])
incs = json.load(open("data/incidents.json"))
for i, inc in enumerate(incs, 1):
    retain_incident(inc); print(f"{i}/{len(incs)} {inc['id']}")
print("Seeding done.")