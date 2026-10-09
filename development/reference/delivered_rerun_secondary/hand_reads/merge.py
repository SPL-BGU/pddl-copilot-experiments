"""Merge the two independent E4 hand reads; list disagreements; apply adjudications.

    python merge.py <reads dir> <packets dir> [adjudications.json]  -> e4_readings.json
"""
import glob
import json
import sys
from pathlib import Path

CATS = {"NO_FINAL_ANSWER", "TOOL_INPUT_ERROR", "SUMMARY_ONLY", "ABRIDGED", "WRONG_WRAPPER",
        "NUMERIC_OMITTED", "WRONG_FACTS", "OTHER"}
reads, packets = Path(sys.argv[1]), Path(sys.argv[2])
adj = json.loads(Path(sys.argv[3]).read_text()) if len(sys.argv) > 3 else {}
idx = json.loads((packets / "index.json").read_text())
meta = {e["id"]: e for e in idx}


def load(prefix):
    out = {}
    for f in sorted(glob.glob(str(reads / f"{prefix}_batch*.json"))):
        for r in json.loads(Path(f).read_text()):
            if r["id"] in out:
                sys.exit(f"duplicate id {r['id']} in {prefix}")
            if r["category"] not in CATS or r["human_correct"] not in {"yes", "no", "unclear"}:
                sys.exit(f"bad label in {f}: {r}")
            out[r["id"]] = r
    return out


A, B = load("A"), load("B")
ids = set(meta)
for name, X in (("A", A), ("B", B)):
    if set(X) != ids:
        print(f"reader {name}: {len(set(X) & ids)} of {len(ids)} ids; missing "
              f"{sorted(ids - set(X))[:5]}; unknown {sorted(set(X) - ids)[:5]}")
both = sorted(ids & set(A) & set(B))
cat_agree = sum(A[i]["category"] == B[i]["category"] for i in both)
cor_agree = sum(A[i]["human_correct"] == B[i]["human_correct"] for i in both)
dis = [i for i in both if A[i]["category"] != B[i]["category"]
       or A[i]["human_correct"] != B[i]["human_correct"]]
print(f"rows read by both: {len(both)}; category agree {cat_agree}; correct agree {cor_agree}; "
      f"disagreements {len(dis)}; adjudicated {len(set(dis) & set(adj))}")
rows = []
for i in sorted(ids):
    a, b = A.get(i), B.get(i)
    if i in adj:
        cat, cor = adj[i]["category"], adj[i]["human_correct"]
        how = "rule applied to an agreed row" if adj[i].get("consistency") else "third reading"
    elif a and b and i not in dis:
        cat, cor, how = a["category"], a["human_correct"], "agreed"
    else:
        cat = cor = None
        how = "pending"
    m = meta[i]
    rows.append({"id": i, "model": m["model"], "task": m["task"], "arm": m["arm"],
                 "category": cat, "human_correct": cor, "how": how,
                 "reader_a": a, "reader_b": b, "adjudication": adj.get(i)})
pending = [r["id"] for r in rows if r["how"] == "pending"]
Path(reads / "disagreements.json").write_text(json.dumps(
    [{"id": i, "file": meta[i]["file"], "A": A[i], "B": B[i]} for i in dis if i not in adj],
    indent=1))
if pending:
    print(f"{len(pending)} rows still pending; see disagreements.json")
    sys.exit(1)
RULES = (
    "Adjudication rules, written before the third reading and applied to every row, "
    "agreed or not. (1) An answer that writes every step out with its full state (facts "
    "and numbers) in a form the grader does not read is WRONG_WRAPPER whatever its "
    "content, as in the Q1 definition (`reanalysis_transcripts.md` §1.1: WRONG_WRAPPER "
    "comes before WRONG_FACTS); content errors are recorded as human_correct = no. "
    "An answer that also leaves out numbers is not a full state, so it falls to "
    "NUMERIC_OMITTED (facts right) or WRONG_FACTS (facts wrong). (2) One JSON array "
    "whose states are nested under a 'state' key with boolean written as {} is a schema "
    "the grader does not read: WRONG_WRAPPER. (3) A per-step change list (full state "
    "only at step 0) is ABRIDGED; it counts as right only if the step-0 state is "
    "complete and every stated change is right, so every state can be rebuilt. (4) A "
    "wrong draft followed by an explicitly corrected full version is judged on the "
    "corrected version.")
out = {"method": ("Each row was read in full by two independent readers (reader A: Claude Opus "
                  "agent; reader B: Claude Sonnet agent), each with only the packet and the fixed "
                  "rubric; disagreements were settled by a third reading (Claude Opus, the "
                  "session that ran the analysis), recorded per row. The simulate packets carry "
                  "a mechanical reading aid (JSON-per-line parse compared with the oracle) that "
                  "readers confirmed by eye."),
       "agreement": {"n": len(both), "category_agree": cat_agree, "correct_agree": cor_agree,
                     "disagreements": len(dis),
                     "rule_applied_to_agreed": sum(1 for v in adj.values() if v.get("consistency"))},
       "rules": RULES,
       "rows": rows}
Path(reads / "e4_readings.json").write_text(json.dumps(out, indent=1))
print("wrote e4_readings.json")
