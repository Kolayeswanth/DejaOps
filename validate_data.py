import json
from datetime import datetime

def load(p):
    return json.load(open(p, encoding="utf-8"))

inc, rbs, demo = load("data/incidents.json"), load("data/runbooks.json"), load("data/demo_alerts.json")
err, warn = [], []

for name, d in (("incidents", inc), ("runbooks", rbs), ("demo_alerts", demo)):
    if not isinstance(d, list):
        err.append(f"{name}.json must be a list")

ids = [i.get("id") for i in inc]
if len(ids) != len(set(ids)):
    err.append("duplicate incident ids")
rb_ids = {r.get("id"): r for r in rbs}

for i in inc:
    for k in ("id","date","service","severity","alert","logs","root_cause","actions",
              "resolution_minutes","runbook","postmortem"):
        if k not in i:
            err.append(f"{i.get('id')} missing {k}")
    for a in i.get("actions", []):
        if a.get("result") not in ("worked", "failed"):
            err.append(f"{i.get('id')} bad action result: {a.get('result')}")
    if i.get("runbook") not in rb_ids:
        warn.append(f"{i.get('id')} references unknown runbook {i.get('runbook')}")

for r in rbs:
    for k in ("id","title","status","steps"):
        if k not in r:
            err.append(f"runbook {r.get('id')} missing {k}")
    if r.get("status") == "deprecated" and not (r.get("deprecated_on") and r.get("replaced_by")):
        err.append(f"deprecated runbook {r.get('id')} needs deprecated_on and replaced_by")

rb12 = rb_ids.get("RB-12", {})
if rb12.get("status") != "deprecated" or rb12.get("replaced_by") != "RB-31" or "RB-31" not in rb_ids:
    err.append("RB-12 must be deprecated (2026-06-10) and replaced by an existing RB-31")

cut = datetime.fromisoformat("2026-06-10T00:00:00+00:00")
for i in inc:
    if "redis" in (i["service"] + i["alert"]).lower():
        d = datetime.fromisoformat(i["date"].replace("Z", "+00:00"))
        if d < cut and i["runbook"] != "RB-12": warn.append(f"{i['id']} Redis before cutoff should use RB-12")
        if d >= cut and i["runbook"] != "RB-31": warn.append(f"{i['id']} Redis after cutoff should use RB-31")

pool = [i["id"] for i in inc if "pgbouncer" in json.dumps(i).lower()
        and any("scal" in a["step"].lower() and a["result"] == "failed" for a in i["actions"])]
print("Pool-exhaustion incidents where scaling failed:", pool, "(expect 3-4)")
print("Incidents:", len(inc), "| Runbooks:", len(rbs), "| Demo alerts:", len(demo))
for e in err: print("ERROR:", e)
for w in warn: print("warn:", w)
print("OK to seed" if not err else "FIX ERRORS FIRST")