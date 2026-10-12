"""t494: spec audit 의 era 판정과 drift 포함 여부를 나란히 본다."""
import json

audit = json.load(open(".moai/reports/t494/audit.json"))
drift = {r["SPECID"]: r for r in json.load(open(".moai/reports/t494/drift.json"))["Records"]}
print({k: v for k, v in audit.items() if not isinstance(v, list)})
rows = {}
for f in audit["drift_findings"]:
    rows.setdefault(f["spec_id"], []).append(f)
for sid in sorted(rows):
    fs = rows[sid]
    eras = sorted({f.get("era") for f in fs})
    types = [f"{f['finding_type']}:{f['severity']}:{json.dumps(f.get('details'), ensure_ascii=False)[:90]}" for f in fs]
    r = drift.get(sid)
    print(f"{'IN ' if r else 'OUT'} {sid:32} era={eras} {types}")
listed = set(rows)
print("in drift but no audit finding:", sorted(set(drift) - listed))
