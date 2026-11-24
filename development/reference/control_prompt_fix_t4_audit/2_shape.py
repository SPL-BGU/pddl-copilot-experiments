import pickle, re, json, collections, sys
out = pickle.load(open(sys.argv[1], "rb"))
rows = out[("gemma4_26b-a4b", "B", "simulate")]
FENCE = re.compile(r"```([a-zA-Z0-9_-]*)\n(.*?)```", re.S)
c = collections.Counter(); dom = collections.Counter(); var = collections.Counter()
ex = {}
for r in rows:
    t = r["response"]; blocks = FENCE.findall(t)
    nb = len(blocks); lang = blocks[-1][0] if blocks else "-"
    body = blocks[-1][1].strip() if blocks else ""
    try: v = json.loads(body); kind = type(v).__name__; err = ""
    except Exception as e: kind = "not-json"; err = str(e)[:50]
    ends_fence = t.rstrip().endswith("```")
    prose_before = bool(t[:t.find("```")].strip()) if blocks else True
    top = ""
    if kind == "dict": top = "keys=" + ",".join(sorted(v)[:4])
    if kind == "list": top = "list[%s]" % (type(v[0]).__name__ if v else "")
    sig = (nb, lang, kind, top, "ends-fence" if ends_fence else "text-after", "prose-before" if prose_before else "fence-first", err if kind=="not-json" else "")
    c[sig] += 1; dom[r["domain"]] += 1; var[r["variant"]] += 1; ex.setdefault(sig, r)
for s, n in c.most_common(): print(n, s)
print(dict(dom)); print(dict(var))
for s, r in list(ex.items())[:4]:
    t = r["response"]; print("=" * 30, s, r["domain"], r["problem"], r["variant"], len(t)); print(t[:500]); print("  ...  "); print(t[-700:])
