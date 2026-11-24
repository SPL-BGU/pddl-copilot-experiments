import pickle, re, json, collections, sys
out = pickle.load(open(sys.argv[1], "rb"))
rows = out[("gemma4_26b-a4b", "B", "simulate")]
FENCE = re.compile(r"```([a-zA-Z0-9_-]*)\n(.*?)```", re.S)
ctx = collections.Counter(); bal = collections.Counter()
for r in rows:
    t = r["response"]; body = FENCE.findall(t)[-1][1].strip()
    try:
        v = json.loads(body)
        print("VALID", r["domain"], r["problem"], r["variant"], "prose braces:", t[:t.find("```")].count("{"), "| traj len", len(v.get("trajectory", [])), "| step0 keys", sorted(v["trajectory"][0]) if v.get("trajectory") else None, "| body head:", body[:150].replace("\n"," "))
    except json.JSONDecodeError as e:
        bal[(body.count("{") - body.count("}"), body.count("[") - body.count("]"))] += 1
        ctx[(e.msg, body[max(0,e.pos-6):e.pos+3])] += 1
print("brace/bracket imbalance (open minus close):", dict(bal))
for k, n in ctx.most_common(12): print(n, k)
