"""Merge the two independent reads of the Gemma no-call sample -> nocall_readings.json."""
import json
import sys
from pathlib import Path

reads, packets = Path(sys.argv[1]), Path(sys.argv[2])
idx = [e["id"] for e in json.loads((packets / "index.json").read_text())]
A = {r["id"]: r for r in json.loads((reads / "A_nocall.json").read_text())}
B = {r["id"]: r for r in json.loads((reads / "B_nocall.json").read_text())}
assert set(A) == set(B) == set(idx), (len(A), len(B), len(idx))
F = ("ends_in_verdict", "verdict", "matches_mechanical", "right", "tool_attempt", "mentions_tool")
agree = {f: sum(str(A[i][f]).lower() == str(B[i][f]).lower() for i in idx) for f in F}
dis = [{"id": i, **{f: (A[i][f], B[i][f]) for f in F if str(A[i][f]).lower() != str(B[i][f]).lower()},
        "A_note": A[i].get("note"), "B_note": B[i].get("note")}
       for i in idx if any(str(A[i][f]).lower() != str(B[i][f]).lower() for f in F)]
n = len(idx)


def both(f, v):
    return sum(str(A[i][f]).lower() == v and str(B[i][f]).lower() == v for i in idx)


counts = {
    "answers read (each by both readers)": n,
    "end in a clear final verdict (both readers)": both("ends_in_verdict", "yes"),
    "verdict right (both readers)": both("right", "yes"),
    "reader's verdict equals the grader's parsed verdict (both readers)": both("matches_mechanical", "yes"),
    "try to call a tool (either reader)": sum(str(A[i]["tool_attempt"]).lower() == "yes"
                                              or str(B[i]["tool_attempt"]).lower() == "yes" for i in idx),
    "mention a tool or validator (either reader)": sum(str(A[i]["mentions_tool"]).lower() == "yes"
                                                       or str(B[i]["mentions_tool"]).lower() == "yes"
                                                       for i in idx),
}
out = {"n": n, "readers": "each read in full by two independent readers (Claude Opus agent, "
                          "Claude Sonnet agent) with the fixed rubric",
       "counts": counts, "agreement": agree, "disagreements": dis,
       "rows": [{"id": i, "A": A[i], "B": B[i]} for i in idx]}
(reads / "nocall_readings.json").write_text(json.dumps(out, indent=1))
print(json.dumps(counts, indent=1))
print("agreement", agree)
print("disagreements", json.dumps(dis, indent=1)[:3000])
