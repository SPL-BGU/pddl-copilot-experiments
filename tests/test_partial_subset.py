"""Unit tests for run_experiment._apply_partial_subset.

Run standalone: `python3 tests/test_partial_subset.py`
Or via the shell wrapper: `bash tests/verify.sh`

Pure-Python tests: no MCP, no Ollama, no fixture I/O.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests._helpers import TestResults
from run_experiment import _apply_partial_subset


def _synthetic_domains() -> dict:
    """Synthetic two-domain dict matching pddl_eval.domains.load_domains shape.

    Five positives + five negatives + five-of-each plans per positive: enough
    surface to exercise K-sub-K, K=K, K>K capping behaviour.
    """
    def make_domain(name: str) -> dict:
        return {
            "type": "classical",
            "domain": f"({name}-domain)",
            "problems": {f"p{i:02d}": f"({name}-p{i:02d})" for i in range(1, 6)},
            "negatives": {
                "domain": f"({name}-domain-neg)",
                "problems": [f"({name}-n{i:02d})" for i in range(1, 6)],
                "plans_per_problem": {
                    f"p{i:02d}": {
                        "valid": [f"{name}-p{i:02d}-v{j}" for j in range(1, 6)],
                        "invalid": [f"{name}-p{i:02d}-b{j}" for j in range(1, 6)],
                    }
                    for i in range(1, 6)
                },
            },
        }
    return {"alpha": make_domain("alpha"), "beta": make_domain("beta")}


def test_k_zero_returns_input_unchanged(r: TestResults) -> None:
    """K=0 is the off switch: identity transform. Defends against an
    accidental K=0 wiping the corpus."""
    domains = _synthetic_domains()
    out = _apply_partial_subset(domains, 0)
    r.check("k=0 returns same object", out is domains)


def test_k_two_caps_positives(r: TestResults) -> None:
    domains = _synthetic_domains()
    out = _apply_partial_subset(domains, 2)
    for dname in ("alpha", "beta"):
        kept = list(out[dname]["problems"].keys())
        r.check_eq(f"{dname} positives kept", kept, ["p01", "p02"])


def test_k_two_caps_negatives(r: TestResults) -> None:
    domains = _synthetic_domains()
    out = _apply_partial_subset(domains, 2)
    for dname in ("alpha", "beta"):
        negs = out[dname]["negatives"]["problems"]
        r.check_eq(f"{dname} negatives kept count", len(negs), 2)


def test_k_two_caps_valid_and_invalid_plans(r: TestResults) -> None:
    domains = _synthetic_domains()
    out = _apply_partial_subset(domains, 2)
    for dname in ("alpha", "beta"):
        ppp = out[dname]["negatives"]["plans_per_problem"]
        for pname in ("p01", "p02"):
            r.check_eq(f"{dname}/{pname} valid plans", len(ppp[pname]["valid"]), 2)
            r.check_eq(f"{dname}/{pname} invalid plans", len(ppp[pname]["invalid"]), 2)


def test_dropped_positives_drop_their_plans(r: TestResults) -> None:
    """Plans for p03/p04/p05 must not survive the subset — they belong to
    positive problems we dropped. Set-membership filter on plans_per_problem,
    not parallel slicing.
    """
    domains = _synthetic_domains()
    out = _apply_partial_subset(domains, 2)
    for dname in ("alpha", "beta"):
        ppp_keys = set(out[dname]["negatives"]["plans_per_problem"].keys())
        r.check_eq(f"{dname} plans_per_problem keys", ppp_keys, {"p01", "p02"})


def test_k_larger_than_available_keeps_all(r: TestResults) -> None:
    """K > items: take what's there, no IndexError, no padding."""
    domains = _synthetic_domains()
    out = _apply_partial_subset(domains, 99)
    for dname in ("alpha", "beta"):
        kept = list(out[dname]["problems"].keys())
        r.check_eq(f"{dname} all positives kept under K=99", len(kept), 5)
        ppp = out[dname]["negatives"]["plans_per_problem"]["p01"]
        r.check_eq(f"{dname}/p01 all valid plans under K=99", len(ppp["valid"]), 5)


def test_returned_dict_does_not_share_mutable_substructures(r: TestResults) -> None:
    """Mutating the returned subset must not write through to the caller's
    domains dict. Defends against a future caller that runs partial then
    full sequentially in-process and expects clean separation.
    """
    domains = _synthetic_domains()
    out = _apply_partial_subset(domains, 2)
    out["alpha"]["problems"]["p01"] = "(MUTATED)"
    out["alpha"]["negatives"]["problems"].append("(injected)")
    r.check_eq(
        "original positives untouched",
        domains["alpha"]["problems"]["p01"],
        "(alpha-p01)",
    )
    r.check_eq(
        "original negatives length untouched",
        len(domains["alpha"]["negatives"]["problems"]),
        5,
    )


def test_domain_without_negatives_field_survives(r: TestResults) -> None:
    """Defensive: a domain dict missing the `negatives` key still subsets
    cleanly (load_domains always sets the key today, but the helper should
    not assume)."""
    domains = {
        "gamma": {
            "type": "classical",
            "domain": "(gamma-domain)",
            "problems": {"p01": "x", "p02": "y", "p03": "z"},
        }
    }
    out = _apply_partial_subset(domains, 2)
    r.check_eq("positives capped", list(out["gamma"]["problems"].keys()), ["p01", "p02"])
    r.check("no negatives synthesised", "negatives" not in out["gamma"])


if __name__ == "__main__":
    r = TestResults("test_partial_subset")
    test_k_zero_returns_input_unchanged(r)
    test_k_two_caps_positives(r)
    test_k_two_caps_negatives(r)
    test_k_two_caps_valid_and_invalid_plans(r)
    test_dropped_positives_drop_their_plans(r)
    test_k_larger_than_available_keeps_all(r)
    test_returned_dict_does_not_share_mutable_substructures(r)
    test_domain_without_negatives_field_survives(r)
    r.report_and_exit()
