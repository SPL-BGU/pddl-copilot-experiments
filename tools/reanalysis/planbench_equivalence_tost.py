"""Q1 re-analysis: the PlanBench clean-vs-Mystery with-tools equivalence sentence.

Recomputes the paired equivalence test (TOST) for |clean_WT - mystery_WT| from
the committed per-instance graded data, for both readings of the clean-WT cell
(first-draw, last-attempt), both margins named in the prereg (7.5 and 10
points) and several interval methods.

Read-only. Imports the data loaders from the pinned
planbench/analysis/verify_promotion.py (never modifies it). stdlib + pyyaml.

Usage (repo root):
  python3 tools/reanalysis/planbench_equivalence_tost.py [--json OUT.json]

Sign convention: delta = clean_WT - mystery_WT (negative = Mystery higher).
  b = solved on clean only, c = solved on Mystery only, delta = (b - c) / n.
TOST at alpha = 0.05 per side  <=>  the 90% two-sided CI lies inside the margin.
"""
import argparse
import importlib.util
import json
import math
import random
from pathlib import Path

R = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "verify_promotion", R / "planbench/analysis/verify_promotion.py")
vp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vp)

Z90 = 1.6448536269514722  # one-sided 0.05


def phi(x):
    return 0.5 * math.erfc(-x / math.sqrt(2))


def phi_inv(p):
    lo, hi = -40.0, 40.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if phi(mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ---------- data ----------
def load_tables():
    """Return {reading: (a, b, c, d)} with rows clean, cols mystery, n = 600."""
    clean_last = vp.arm(vp.TOOLS, vp.ARMS["clean"])
    myst = vp.arm(vp.TOOLS, vp.ARMS["mystery"])
    recs = [json.loads(ln) for ln in open(vp.D / "sidelogs/blocksworld__anthropic-tools.jsonl")]
    ids = [int(r["instance_id"]) for r in recs]
    dups = sorted(i for i in set(ids) if ids.count(i) > 1)
    clean_first = dict(clean_last)
    for i in dups:
        clean_first[("blocksworld", i)] = False  # first draw delivered nothing
    out = {}
    for name, clean in (("first-draw", clean_first), ("last-attempt", clean_last)):
        assert set(clean) == set(myst) and len(clean) == 600
        a = sum(clean[k] and myst[k] for k in clean)
        b = sum(clean[k] and not myst[k] for k in clean)
        c = sum((not clean[k]) and myst[k] for k in clean)
        d = sum((not clean[k]) and (not myst[k]) for k in clean)
        out[name] = (a, b, c, d)
    return out, len(dups)


# ---------- methods ----------
def wald(a, b, c, d, margin):
    n = a + b + c + d
    est = (b - c) / n
    se = math.sqrt((b + c) - (b - c) ** 2 / n) / n
    ci = (est - Z90 * se, est + Z90 * se)
    p_low = 1 - phi((est + margin) / se)   # H0: delta <= -margin
    p_up = phi((est - margin) / se)        # H0: delta >= +margin
    return ci, max(p_low, p_up)


def tango_T(b, c, n, delta0):
    """Tango (1998) score statistic for H0: p12 - p21 = delta0."""
    A = 2 * n
    B = -b - c + (2 * n - b + c) * delta0
    C = -c * delta0 * (1 - delta0)
    q21 = (math.sqrt(B * B - 4 * A * C) - B) / (2 * A)
    den = math.sqrt(n * (2 * q21 + delta0 * (1 - delta0)))
    return (b - c - n * delta0) / den


def tango(a, b, c, d, margin):
    n = a + b + c + d
    est = (b - c) / n

    def root(target, lo, hi):  # T is decreasing in delta0
        for _ in range(200):
            mid = (lo + hi) / 2
            if tango_T(b, c, n, mid) > target:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2
    ci = (root(Z90, -0.999, est), root(-Z90, est, 0.999))
    p_low = 1 - phi(tango_T(b, c, n, -margin))
    p_up = phi(tango_T(b, c, n, margin))
    return ci, max(p_low, p_up)


def _wilson(k, n, z):
    p = k / n
    den = 1 + z * z / n
    cen = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (cen - h) / den, (cen + h) / den


def _newcombe_ci(a, b, c, d, z):
    """Newcombe (1998) paired method 10 (Wilson limits + corrected phi)."""
    n = a + b + c + d
    p1, p2 = (a + b) / n, (a + c) / n
    l1, u1 = _wilson(a + b, n, z)
    l2, u2 = _wilson(a + c, n, z)
    prod = (a + b) * (c + d) * (a + c) * (b + d)
    if prod == 0:
        ph = 0.0
    else:
        num = a * d - b * c
        if num > n / 2:
            num -= n / 2
        elif num >= 0:
            num = 0.0
        ph = num / math.sqrt(prod)
    est = p1 - p2
    lo = est - math.sqrt((p1 - l1) ** 2 - 2 * ph * (p1 - l1) * (u2 - p2) + (u2 - p2) ** 2)
    hi = est + math.sqrt((u1 - p1) ** 2 - 2 * ph * (u1 - p1) * (p2 - l2) + (p2 - l2) ** 2)
    return lo, hi


def _p_by_inversion(ci_at_z, margin):
    """Smallest one-sided alpha whose (1-2alpha) CI lies inside +-margin."""
    lo_z, hi_z = 1e-9, 12.0
    l, u = ci_at_z(lo_z)
    if not (-margin < l and u < margin):
        return 1.0  # point estimate itself outside
    for _ in range(200):
        mid = (lo_z + hi_z) / 2
        l, u = ci_at_z(mid)
        if -margin < l and u < margin:
            lo_z = mid
        else:
            hi_z = mid
    return 1 - phi(lo_z)


def newcombe(a, b, c, d, margin):
    return (_newcombe_ci(a, b, c, d, Z90),
            _p_by_inversion(lambda z: _newcombe_ci(a, b, c, d, z), margin))


def _bp_ci(a, b, c, d, z):
    """Bonett & Price (2012) adjusted Wald for paired proportions."""
    n = a + b + c + d
    p12, p21 = (b + 1) / (n + 2), (c + 1) / (n + 2)
    est = p12 - p21
    se = math.sqrt((p12 + p21 - (p12 - p21) ** 2) / (n + 2))
    return est - z * se, est + z * se


def bonett_price(a, b, c, d, margin):
    return (_bp_ci(a, b, c, d, Z90),
            _p_by_inversion(lambda z: _bp_ci(a, b, c, d, z), margin))


def bootstrap(a, b, c, d, margin, reps=20000, seed=20261002):
    """Percentile bootstrap over instances (pairs resampled together)."""
    n = a + b + c + d
    rng = random.Random(seed)
    pb, pc = b / n, c / n
    vals = []
    for _ in range(reps):
        nb = nc = 0
        for _ in range(n):
            u = rng.random()
            if u < pb:
                nb += 1
            elif u < pb + pc:
                nc += 1
        vals.append((nb - nc) / n)
    vals.sort()
    ci = (vals[int(0.05 * reps)], vals[int(0.95 * reps) - 1])
    p_low = sum(v <= -margin for v in vals) / reps
    p_up = sum(v >= margin for v in vals) / reps
    return ci, max(p_low, p_up)


METHODS = [("Wald paired", wald), ("Tango score", tango),
           ("Newcombe paired (method 10)", newcombe),
           ("Bonett-Price adjusted Wald", bonett_price),
           ("bootstrap percentile (20k)", bootstrap)]


def mcnemar_exact(b, c):
    n, k = b + c, min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) * 0.5 ** n)


def certifiable_psi(n, margin, alpha=0.05, power=0.80):
    """Largest total discordance psi at which a Wald paired TOST has the stated
    power when the true difference is zero: margin >= (z_a + z_{b/2}) sqrt(psi/n)."""
    za, zb = phi_inv(1 - alpha), phi_inv(1 - (1 - power) / 2)
    return n * (margin / (za + zb)) ** 2


def tost_power(n, psi, margin, alpha=0.05):
    """Wald TOST power at true difference 0 with total discordance psi."""
    se = math.sqrt(psi / n)
    za = phi_inv(1 - alpha)
    return max(0.0, 2 * phi(margin / se - za) - 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    args = ap.parse_args()
    tables, ndups = load_tables()
    out = {"rows": [], "tables": {}}
    print(f"clean-WT re-drawn ids (first draw counted as failure): {ndups}\n")
    for reading, (a, b, c, d) in tables.items():
        n = a + b + c + d
        est = 100 * (b - c) / n
        print(f"== {reading}: a={a} b={b} c={c} d={d} n={n}  "
              f"clean {a+b}/{n}  mystery {a+c}/{n}")
        print(f"   delta (clean - mystery) = {est:+.2f} pts   exact McNemar p = "
              f"{mcnemar_exact(b, c):.3f}   total discordance psi = {(b+c)/n:.3f}")
        out["tables"][reading] = dict(a=a, b=b, c=c, d=d, n=n, delta_pts=est,
                                      mcnemar_p=mcnemar_exact(b, c), psi=(b + c) / n)
        for margin in (0.075, 0.10):
            for name, fn in METHODS:
                (lo, hi), p = fn(a, b, c, d, margin)
                met = (-margin < lo) and (hi < margin)
                verdict = "criterion met" if met else "criterion not met"
                print(f"   margin +-{100*margin:4.1f}  {name:30s} 90% CI "
                      f"[{100*lo:+.2f}, {100*hi:+.2f}]  TOST p = {p:.4f}  {verdict}")
                out["rows"].append(dict(reading=reading, margin_pts=100 * margin,
                                        method=name, ci90=[100 * lo, 100 * hi],
                                        tost_p=p, met=met))
        print()
    print("== what the prereg's own power sentence implies ==")
    for n in (500, 600):
        for m in (0.075, 0.10):
            print(f"   n={n} margin +-{100*m:.1f}: certifiable (80% power, true diff 0) "
                  f"up to psi = {certifiable_psi(n, m):.3f}")
    for reading, (a, b, c, d) in tables.items():
        n = a + b + c + d
        psi = (b + c) / n
        print(f"   {reading}: observed psi = {psi:.3f}; TOST power at true diff 0: "
              f"+-7.5 -> {tost_power(n, psi, 0.075):.2f}, +-10 -> {tost_power(n, psi, 0.10):.2f}")
    print(f"   planned psi = 0.18 at n=600: power +-7.5 -> {tost_power(600, 0.18, 0.075):.3f}")
    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
