import json, glob, re, os, shutil
allinc = []
for f in sorted(glob.glob("data/batches/*.json")):
    t = open(f, encoding="utf-8").read().strip()
    t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    data = json.loads(t)
    print(f, len(data))
    allinc += data
ids = [i["id"] for i in allinc]
dupes = sorted({x for x in ids if ids.count(x) > 1})
if dupes:
    raise SystemExit(f"Duplicate ids: {dupes}")
allinc.sort(key=lambda i: i["date"])
if os.path.exists("data/incidents.json"):
    shutil.copy("data/incidents.json", "data/incidents.backup.json")
json.dump(allinc, open("data/incidents.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("Merged", len(allinc), "incidents")