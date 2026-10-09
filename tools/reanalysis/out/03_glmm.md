Rows: 6000; instances: 1000; domains: 20; success plain 0.206 -> steered 0.926; marginal log-odds difference 3.873

Instances by (successes of 3 plain, successes of 3 steered): (0,0):45, (0,1):24, (0,2):24, (0,3):571, (1,0):1, (1,1):1, (1,2):1, (1,3):93, (2,0):1, (2,1):1, (2,2):5, (2,3):192, (3,3):41

| fit | log-odds (steered vs plain) | SE (or posterior SD) | 95% interval | z | notes |
|---|---|---|---|---|---|
| A. variational Bayes, instance random intercept (the paper's fit) | +7.53 | 0.10 | [7.34, 7.72] | 78.1 | random-effect SD (posterior mean) 2.74; subject-specific |
| B. maximum likelihood (Gauss-Hermite, 200 nodes), instance random intercept | +7.80 | 0.29 | [7.23, 8.37] | 26.8 | profile 95% [7.25, 8.40]; random-effect SD 2.86; LR chi2 4410; implied marginal rates 0.204 -> 0.931; b1 at 50/400 nodes 7.799/7.798; subject-specific |
| D. conditional logistic, stratified on instance | +6.15 | 0.29 | [5.59, 6.72] | 21.2 | uses the 914 instances with mixed outcomes; no distribution assumed for the instance effect; subject-specific |
| E. GEE exchangeable, clustered on instance (k=1000) | +3.87 | 0.12 | [3.65, 4.10] | 33.5 | population-averaged; robust SE |
| E. GEE exchangeable, clustered on domain (k=20) | +3.87 | 0.64 | [2.63, 5.12] | 6.1 | population-averaged; robust SE; z interval, k=20 is small |
| E2. logistic regression, domain-cluster-robust SE, t(19) interval | +3.87 | 0.65 | [2.51, 5.24] | 5.9 | population-averaged |

- paired risk difference, clustered on domain (k=20): +72.0 pp [57.5, 86.5], SE 6.92, p = 2.8e-09
- paired risk difference, clustered on problem (k=100): +72.0 pp [65.4, 78.6], SE 3.35, p = 4.2e-39
- paired risk difference, clustered on instance (k=1000): +72.0 pp [69.8, 74.2], SE 1.14, p = 0.0e+00

Self-check of the quadrature code: simulated truth b1=4.00, sigma=1.50 -> estimate b1=3.89 (SE 0.11), sigma=1.35
