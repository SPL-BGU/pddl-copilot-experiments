import re, sys
from pathlib import Path
REPO=Path("/Users/omereliyahu/personal/pddl-copilot-experiments")
def strip_comments(t): return re.sub(r";[^\n]*","",t)
def section(t, kw):
    m=re.search(r"\(\s*:"+kw+r"\b", t, re.I)
    if not m: return ""
    i=m.end(); depth=1
    while depth and i<len(t):
        if t[i]=="(": depth+=1
        elif t[i]==")": depth-=1
        i+=1
    return t[m.end():i-1]
def names(sec):
    toks=sec.split()
    out=[]; skip=False
    for tok in toks:
        if tok=="-": skip=True; continue
        if skip: skip=False; continue
        out.append(tok)
    return out
for tree in ("domains","domains-anon"):
    for f in sorted((REPO/tree).rglob("*.pddl")):
        t=strip_comments(f.read_text())
        found=[]
        for kw in ("objects","constants"):
            found += [n for n in names(section(t,kw)) if any(c.isupper() for c in n)]
        acts=[a for a in re.findall(r"\(:action\s+([^\s()]+)",t,re.I) if any(c.isupper() for c in a)]
        if found or acts:
            print(f.relative_to(REPO), "objs/consts:", sorted(set(found)), "actions:", acts)
    # plan fixtures
    for f in sorted((REPO/tree).rglob("*.plan")):
        t=strip_comments(f.read_text())
        ups=set(w for w in re.findall(r"[A-Za-z][\w\-]*", t) if any(c.isupper() for c in w))
        if ups: print("PLAN", f.relative_to(REPO), sorted(ups)[:8])
