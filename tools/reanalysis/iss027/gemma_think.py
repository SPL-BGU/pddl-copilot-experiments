import json, re, statistics as S
from collections import Counter, defaultdict
from pathlib import Path
R=Path("/Users/omereliyahu/personal/pddl-copilot-experiments/results")
MARK={"<|channel>":"<|channel>","<channel|>":"<channel|>","starts 'thought\\n'":None,"<|think|>":"<|think|>","<start_of_turn>":"<start_of_turn>","<think>":"<think>","<|turn>":"<|turn>","<|tool_call>":"<|tool_call>"}
EMPTY="<|channel>thought\n<channel|>"
def load(f):
    d={}
    for ln in open(f,errors="replace"):
        try:o=json.loads(ln)
        except: continue
        d[tuple(o["key"])]=o["result"]
    return d
def keynorm(k): k=list(k); k[7]="*"; return tuple(k)
def scan(texts):
    c=Counter()
    for t in texts:
        if t.startswith(EMPTY): c["starts_with_EMPTY_thought_channel"]+=1
        elif "<|channel>" in t: c["has <|channel> (non-empty)"]+=1
        if t.lstrip().startswith("thought\n") or t.lstrip().startswith("thought "): c["starts 'thought'"]+=1
        for m in ("<|channel>","<channel|>","<|think|>","<start_of_turn>","<think>","<|turn>","<|tool_call>"):
            if m in t: c[m]+=1
    return c
for corpus in ("sweep5v2-live","sweep6-live"):
    for cond in ("no-tools","tools_all_minimal"):
        off=load(R/corpus/f"slurm_vllm_gemma4_26b-a4b_off_{cond}"/"trials.jsonl")
        on=load(R/corpus/f"slurm_vllm_gemma4_26b-a4b_on_{cond}"/"trials.jsonl")
        offn={keynorm(k):v for k,v in off.items()}; onn={keynorm(k):v for k,v in on.items()}
        common=sorted(set(offn)&set(onn))
        print(f"\n=== {corpus} {cond}: off {len(off)} on {len(on)} paired {len(common)}")
        bytask=defaultdict(lambda: defaultdict(list))
        for k in common:
            a,b=offn[k],onn[k]
            t=a["task"]
            for lab,r in (("off",a),("on",b)):
                tok=r.get("tokens") or {}
                bytask[t][lab+"_comp"].append(tok.get("completion") or 0)
                bytask[t][lab+"_len"].append(len(r.get("response") or ""))
                bytask[t][lab+"_think"].append(len(r.get("thinking") or ""))
                bytask[t][lab+"_ok"].append(bool(r["success"]))
                bytask[t][lab+"_trunc"].append(r.get("done_reason")=="length")
                if r.get("tool_selected") is not None: bytask[t][lab+"_sel"].append(bool(r["tool_selected"]))
            bytask[t]["diff"].append((b.get("tokens") or {}).get("completion",0)-(a.get("tokens") or {}).get("completion",0))
            bytask[t]["same_resp"].append((a.get("response") or "")==(b.get("response") or ""))
        for t,d in bytask.items():
            n=len(d["diff"])
            line=f"{t:16s} n={n} comp median off/on {S.median(d['off_comp']):.0f}/{S.median(d['on_comp']):.0f} mean {S.mean(d['off_comp']):.0f}/{S.mean(d['on_comp']):.0f} | resp len med {S.median(d['off_len']):.0f}/{S.median(d['on_len']):.0f} | thinking-field nonempty {sum(x>0 for x in d['off_think'])}/{sum(x>0 for x in d['on_think'])} | identical resp {sum(d['same_resp'])} | success {sum(d['off_ok'])}/{sum(d['on_ok'])} | len-cut {sum(d['off_trunc'])}/{sum(d['on_trunc'])}"
            if d.get("off_sel"): line+=f" | tool_selected {sum(d['off_sel'])}/{sum(d['on_sel'])}"
            print(line)
        print(" markers off:", dict(scan([(r.get('response') or '') for r in off.values()])))
        print(" markers on :", dict(scan([(r.get('response') or '') for r in on.values()])))
