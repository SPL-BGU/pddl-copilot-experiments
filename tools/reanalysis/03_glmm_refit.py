#!/usr/bin/env python3
"""Item 3: refit the one mixed model the paper quotes (main.tex near line 564)
with standard, non-variational estimators.

Contrast: Gemma 26B, validate_plan, think=off, with tools, plain (v11-13) vs
steered (v14-16), harness `success` (tool-verified). 1,000 instances x 6 trials.

Original fit: `.local/glmm_feasibility_probe.py` (untracked), statsmodels
`BinomialBayesMixedGLM.fit_vb()` = mean-field variational Bayes with one random
intercept per instance. It printed log-odds 7.532, posterior SD 0.096.

Refits here:
  A. the variational fit again (to confirm the quoted number is reproduced)
  B. marginal maximum likelihood, random intercept on instance, by Gauss-Hermite
     quadrature (the same likelihood lme4::glmer(nAGQ>1) maximises); SE from the
     observed information, plus a profile-likelihood interval and an LR test
  D. conditional (fixed-effects) logistic regression stratified on instance
  E. GEE, exchangeable, clustered on instance and on domain; and the plain
     risk-difference with a domain-clustered interval

Run:  .venv/bin/python tools/reanalysis/03_glmm_refit.py
"""
from __future__ import annotations

import math
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import integrate, optimize, stats
from scipy.special import expit, gammaln
from statsmodels.discrete.conditional_models import ConditionalLogit
from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM

from common import NEUT, OUT, STER, cluster_stat, load_cell

warnings.filterwarnings("ignore")


def load() -> pd.DataFrame:
    rows = [r for r in load_cell("sweep5v2-live", "gemma4_26b-a4b", "off", True)
            if r["task"] == "validate_plan"]
    df = pd.DataFrame(rows)
    df["steered"] = df["variant"].isin(STER).astype(int)
    df["instance"] = df["domain"] + "|" + df["problem"] + "|" + df["plan"]
    df["y"] = df["mech"]
    return df


# ---------------------------------------------------------------- quadrature ML
def cluster_table(df: pd.DataFrame, cluster: str) -> np.ndarray:
    """Per cluster: successes and trials in each arm (sufficient statistics)."""
    g = df.groupby([cluster, "steered"])["y"].agg(["sum", "count"]).unstack("steered")
    return np.column_stack([g[("sum", 0)], g[("count", 0)], g[("sum", 1)], g[("count", 1)]]).astype(float)


def make_nll(tab: np.ndarray, n_nodes: int = 200):
    x, w = np.polynomial.hermite.hermgauss(n_nodes)
    logw = np.log(w) - 0.5 * math.log(math.pi)
    s0, n0, s1, n1 = tab.T
    const = (gammaln(n0 + 1) - gammaln(s0 + 1) - gammaln(n0 - s0 + 1)
             + gammaln(n1 + 1) - gammaln(s1 + 1) - gammaln(n1 - s1 + 1))

    def nll(theta, fix_b1=None):
        if fix_b1 is None:
            b0, b1, ls = theta
        else:
            b0, ls = theta
            b1 = fix_b1
        u = math.sqrt(2.0) * math.exp(ls) * x                     # nodes on the u scale
        e0 = b0 + u[None, :]
        e1 = b0 + b1 + u[None, :]
        ll = (s0[:, None] * e0 - n0[:, None] * np.logaddexp(0, e0)
              + s1[:, None] * e1 - n1[:, None] * np.logaddexp(0, e1)) + logw[None, :]
        m = ll.max(axis=1, keepdims=True)
        return -float((m[:, 0] + np.log(np.exp(ll - m).sum(axis=1)) + const).sum())
    return nll


def num_hessian(f, x, h=1e-4):
    x = np.asarray(x, float)
    k = len(x)
    H = np.zeros((k, k))
    for i in range(k):
        for j in range(i, k):
            ei, ej = np.zeros(k), np.zeros(k)
            ei[i], ej[j] = h, h
            H[i, j] = H[j, i] = (f(x + ei + ej) - f(x + ei - ej) - f(x - ei + ej) + f(x - ei - ej)) / (4 * h * h)
    return H


def fit_ml(tab: np.ndarray, label: str, n_nodes: int = 200) -> dict:
    nll = make_nll(tab, n_nodes)
    best = None
    for start in ([-1.0, 3.0, 0.0], [-3.0, 6.0, 1.0], [-5.0, 9.0, 1.6], [0.0, 1.0, -1.0]):
        r = optimize.minimize(nll, start, method="Nelder-Mead",
                              options=dict(xatol=1e-7, fatol=1e-9, maxiter=20000))
        r = optimize.minimize(nll, r.x, method="BFGS")
        if best is None or r.fun < best.fun:
            best = r
    b0, b1, ls = best.x
    cov = np.linalg.inv(num_hessian(nll, best.x))
    se = np.sqrt(np.diag(cov))
    # LR test and profile-likelihood interval for b1
    null = optimize.minimize(lambda t: nll(t, fix_b1=0.0), [b0, ls], method="Nelder-Mead",
                             options=dict(xatol=1e-7, fatol=1e-9, maxiter=20000))
    lr = 2 * (null.fun - best.fun)

    def prof(b):
        r = optimize.minimize(lambda t: nll(t, fix_b1=b), [b0, ls], method="Nelder-Mead",
                              options=dict(xatol=1e-7, fatol=1e-9, maxiter=20000))
        return 2 * (r.fun - best.fun) - stats.chi2.ppf(0.95, 1)
    plo = optimize.brentq(prof, b1 - 10 * se[1], b1)
    phi = optimize.brentq(prof, b1, b1 + 10 * se[1])
    # node-count stability
    alt = {n: optimize.minimize(make_nll(tab, n), best.x, method="BFGS").x[1] for n in (50, 400)}
    sigma = math.exp(ls)
    # population-averaged rates implied by the fit (integrate the random effect out)
    marg = [integrate.quad(lambda u, e=e: expit(e + u) * stats.norm.pdf(u, scale=sigma),
                           -12 * sigma, 12 * sigma, limit=400)[0] for e in (b0, b0 + b1)]
    return dict(label=label, k=len(tab), b0=b0, b1=b1, se=se[1], wald=(b1 - 1.96 * se[1], b1 + 1.96 * se[1]),
                profile=(plo, phi), sigma=sigma, se_logsigma=se[2], lr=lr,
                p_lr=float(stats.chi2.sf(lr, 1)), loglik=-best.fun, alt=alt, marg=marg)


def selfcheck() -> str:
    """Recover known parameters from simulated data, same shape as the real cell."""
    rng = np.random.default_rng(7)
    k, b0, b1, sig = 1000, -2.0, 4.0, 1.5
    u = rng.normal(0, sig, k)
    s0 = rng.binomial(3, expit(b0 + u))
    s1 = rng.binomial(3, expit(b0 + b1 + u))
    tab = np.column_stack([s0, np.full(k, 3), s1, np.full(k, 3)]).astype(float)
    f = fit_ml(tab, "sim")
    return (f"simulated truth b1=4.00, sigma=1.50 -> estimate b1={f['b1']:.2f} "
            f"(SE {f['se']:.2f}), sigma={f['sigma']:.2f}")


def main() -> None:
    df = load()
    L = []
    p0, p1 = df[df.steered == 0].y.mean(), df[df.steered == 1].y.mean()
    L.append(f"Rows: {len(df)}; instances: {df.instance.nunique()}; domains: {df.domain.nunique()}; "
             f"success plain {p0:.3f} -> steered {p1:.3f}; "
             f"marginal log-odds difference {math.log(p1/(1-p1)) - math.log(p0/(1-p0)):.3f}\n")

    # how the outcome is distributed inside instances
    g = df.groupby(["instance", "steered"])["y"].sum().unstack()
    pat = g.value_counts().sort_index()
    L.append("Instances by (successes of 3 plain, successes of 3 steered): "
             + ", ".join(f"({int(a)},{int(b)}):{n}" for (a, b), n in pat.items()) + "\n")

    rows = []
    # A. the paper's variational fit
    vb = BinomialBayesMixedGLM.from_formula("y ~ steered", {"a": "0 + C(instance)"}, df).fit_vb()
    i = list(vb.model.exog_names).index("steered")
    rows.append(("A. variational Bayes, instance random intercept (the paper's fit)",
                 vb.fe_mean[i], vb.fe_sd[i], (vb.fe_mean[i] - 1.96 * vb.fe_sd[i], vb.fe_mean[i] + 1.96 * vb.fe_sd[i]),
                 f"random-effect SD (posterior mean) {math.exp(vb.vcp_mean[0]):.2f}; subject-specific"))
    # B. quadrature ML (a domain-level random intercept is NOT fitted this way: with 300 trials per
    # domain the integrand is too peaked for fixed-node quadrature; domain clustering is handled in E/E2)
    fits = [fit_ml(cluster_table(df, "instance"),
                   "B. maximum likelihood (Gauss-Hermite, 200 nodes), instance random intercept")]
    for f in fits:
        rows.append((f["label"], f["b1"], f["se"], f["wald"],
                     f"profile 95% [{f['profile'][0]:.2f}, {f['profile'][1]:.2f}]; random-effect SD {f['sigma']:.2f}; "
                     f"LR chi2 {f['lr']:.0f}; implied marginal rates {f['marg'][0]:.3f} -> {f['marg'][1]:.3f}; "
                     f"b1 at 50/400 nodes {f['alt'][50]:.3f}/{f['alt'][400]:.3f}; subject-specific"))

    # D. conditional logit
    keep = df.groupby("instance")["y"].transform(lambda s: 0 < s.sum() < len(s))
    dd = df[keep]
    cl = ConditionalLogit(dd["y"].values, dd[["steered"]].values, groups=dd["instance"].values).fit(disp=0)
    rows.append(("D. conditional logistic, stratified on instance",
                 cl.params[0], cl.bse[0], tuple(cl.conf_int()[0]),
                 f"uses the {dd.instance.nunique()} instances with mixed outcomes; no distribution assumed for the instance effect; subject-specific"))

    # E. GEE
    for cl_name in ("instance", "domain"):
        d2 = df.sort_values(cl_name)
        gee = smf.gee("y ~ steered", cl_name, data=d2, family=sm.families.Binomial(),
                      cov_struct=sm.cov_struct.Exchangeable()).fit()
        ci = gee.conf_int().loc["steered"]
        rows.append((f"E. GEE exchangeable, clustered on {cl_name} (k={d2[cl_name].nunique()})",
                     gee.params["steered"], gee.bse["steered"], (ci[0], ci[1]),
                     "population-averaged; robust SE" + ("; z interval, k=20 is small" if cl_name == "domain" else "")))
    # logistic GLM with domain-cluster-robust SE and t(19) interval
    glm = smf.glm("y ~ steered", data=df, family=sm.families.Binomial()).fit(
        cov_type="cluster", cov_kwds=dict(groups=pd.factorize(df["domain"])[0]))
    b, se = glm.params["steered"], glm.bse["steered"]
    tc = stats.t.ppf(0.975, 19)
    rows.append(("E2. logistic regression, domain-cluster-robust SE, t(19) interval", b, se,
                 (b - tc * se, b + tc * se), "population-averaged"))

    L.append("| fit | log-odds (steered vs plain) | SE (or posterior SD) | 95% interval | z | notes |")
    L.append("|---|---|---|---|---|---|")
    for name, b, se, ci, note in rows:
        L.append(f"| {name} | {b:+.2f} | {se:.2f} | [{ci[0]:.2f}, {ci[1]:.2f}] | {b/se:.1f} | {note} |")
    L.append("")

    # risk difference, paired, clustered
    piv = df.assign(par=df["variant"].map(lambda v: (v - 11) % 3)).pivot_table(
        index=["domain", "problem", "plan", "par"], columns="steered", values="y").reset_index()
    d = (piv[1] - piv[0]).values
    for nm, cl_ in (("domain (k=20)", piv["domain"].values),
                    ("problem (k=100)", (piv["domain"] + "|" + piv["problem"]).values),
                    ("instance (k=1000)", (piv["domain"] + "|" + piv["problem"] + "|" + piv["plan"]).values)):
        c = cluster_stat(d, cl_)
        L.append(f"- paired risk difference, clustered on {nm}: {100*c['est']:+.1f} pp "
                 f"[{100*c['lo']:.1f}, {100*c['hi']:.1f}], SE {100*c['se']:.2f}, p = {c['p']:.1e}")
    L.append("")
    L.append("Self-check of the quadrature code: " + selfcheck())
    text = "\n".join(L)
    OUT.mkdir(exist_ok=True)
    (OUT / "03_glmm.md").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
