import json, re
from pathlib import Path
from collections import Counter
REPO=Path("/Users/omereliyahu/personal/pddl-copilot-experiments")
AFF={("satellite",p) for p in ("p02","p03","p04","p05")}
for cell in sorted((REPO/"results/sweep5v2-live").glob("*no-tools")):
    c=Counter()
    for ln in open(cell/"trials.jsonl",errors="replace"):
        try: o=json.loads(ln)
        except: continue
        r=o["result"]; d,p=r["domain_name"],r["problem_name"]
        if r["task"]!="solve" or not ((d,p) in AFF or d=="pogo_stick"): continue
        resp=r.get("response") or ""
        if len(resp)!=500: continue
        raw=resp.lstrip()
        c["at_cap"]+=1; c["at_cap_success"]+=bool(r["success"])
        jsonstart = raw.startswith("{") or raw.startswith("```json")
        # plan entries visible
        entries=re.findall(r'"\(?([A-Za-z][^"]*)\)?"', raw)
        up=[e for e in entries if re.search(r"[A-Z]",e) and e.split()[0] not in ("plan",)]
        if jsonstart:
            c["json_start"]+=1
            if not r["success"]:
                c["json_start_failed"]+=1
                if up:
                    c["json_failed_upper_plan_entry"]+=1
                    print("  ",cell.name,d,p,o["key"][5],r["failure_reason"],repr(raw[:160]))
        else:
            c["text_start"]+=1
            if raw.startswith("<|channel>") : c["leaked_prefix"]+=1
    print(cell.name, dict(c))
