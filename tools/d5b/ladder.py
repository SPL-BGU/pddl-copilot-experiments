"""D5b size ladder: which IPC 2023 learning-track problems we generate, and how.

Standard library only, so the tests run in the repo venv.

Source: https://github.com/ipc2023-learning/benchmarks at the pinned commit
below. The repo has no licence file, so nothing from it is committed here: only
the commit, the generator commands and parameters, the seeds, and a sha256
manifest (tools/d5b/manifest.json). The clone and the generated PDDL live in
gitignored folders (external/ by default).

Tiers. Each of our tiers copies one IPC 2023 *testing* tier (easy, medium,
hard): the same start and end parameters as that domain's generate_all.py, the
same linear interpolation formula (copied below, including the rovers quirk
where the objectives step is computed from starting_cameras), but 10 instances
per tier instead of 30 and fresh seeds. The 10 instances run from the tier's
smallest parameters towards its largest, so the 30 problems of a domain form a
size ladder across the whole easy-to-hard test range. `ipc_testing_commands`
rebuilds IPC's own 30-instance testing commands (seed 1007), which the tests use
to check that our command builder reproduces their committed testing files byte
for byte.

Seeds. IPC 2023 used 42.. (training) and 1007..1036 (testing). Ours are
5001..5010 (easy), 5101..5110 (medium), 5201..5210 (hard), one per instance,
the same for every domain (IPC also reuses one seed base across domains).
"""
from __future__ import annotations

from dataclasses import dataclass

IPC_REPO = "https://github.com/ipc2023-learning/benchmarks"
IPC_COMMIT = "19d6a8ad4b354328154a2cc1f1a95f7c09fa9db6"

DOMAINS = ("blocksworld", "miconic", "rovers", "satellite")
TIERS = ("easy", "medium", "hard")
N_PER_TIER = 10
SEED_BASE = {"easy": 5001, "medium": 5101, "hard": 5201}
IPC_TEST_SEED = 1007
IPC_TEST_N = 30

# Start/end parameters of IPC 2023's testing tiers, copied from each domain's
# generate_all.py at IPC_COMMIT (list index 1 = testing/easy, 2 = medium,
# 3 = hard). Keys are the generator's parameter names.
IPC_TEST_RANGES: dict[str, dict[str, dict[str, tuple[int, int]]]] = {
    "blocksworld": {
        "easy": {"blocks": (5, 30)},
        "medium": {"blocks": (35, 150)},
        "hard": {"blocks": (160, 500)},
    },
    "miconic": {
        "easy": {"passengers": (1, 10), "floors": (4, 20)},
        "medium": {"passengers": (20, 80), "floors": (30, 60)},
        "hard": {"passengers": (50, 500), "floors": (80, 200)},
    },
    "rovers": {
        "easy": {"rovers": (1, 4), "waypoints": (4, 10), "cameras": (1, 4), "objectives": (1, 10)},
        "medium": {"rovers": (5, 10), "waypoints": (15, 90), "cameras": (5, 50), "objectives": (15, 80)},
        "hard": {"rovers": (15, 30), "waypoints": (100, 200), "cameras": (60, 100), "objectives": (100, 200)},
    },
    "satellite": {
        "easy": {"satellites": (3, 10), "instruments": (3, 20), "modes": (1, 3), "directions": (4, 10)},
        "medium": {"satellites": (15, 40), "instruments": (15, 80), "modes": (3, 5), "directions": (15, 30)},
        "hard": {"satellites": (50, 100), "instruments": (50, 200), "modes": (5, 10), "directions": (40, 100)},
    },
}

# Generator command-line flags, in the order generate_all.py writes them.
_FLAGS = {
    "blocksworld": [("blocks", "-b")],
    "miconic": [("passengers", "-p"), ("floors", "-f")],
    "rovers": [("rovers", "-r"), ("waypoints", "-w"), ("cameras", "-c"), ("objectives", "-o")],
    "satellite": [("satellites", "-s"), ("instruments", "-i"), ("modes", "-m"), ("directions", "-d")],
}
_OUT_FLAG = {"blocksworld": "-out", "miconic": "-o", "rovers": "-out", "satellite": "-o"}
_ID_FLAG = {"blocksworld": "-id", "miconic": "-i", "rovers": "-id", "satellite": "-id"}
# generate_all.py prefixes PYTHONHASHSEED=0 for these three, not for blocksworld.
_HASHSEED = {"blocksworld": None, "miconic": "0", "rovers": "0", "satellite": "0"}


@dataclass(frozen=True)
class GenSpec:
    domain: str
    tier: str
    instance_id: int
    seed: int
    params: dict
    argv: tuple  # relative to the domain folder of the clone, e.g. ("blocksworld.py", "-b", "5", ...)
    env: dict  # extra environment (PYTHONHASHSEED)

    @property
    def problem_name(self) -> str:
        return f"p{self.instance_id:02}.pddl"

    def shell_command(self, out_folder: str) -> str:
        env = "".join(f"{k}={v} " for k, v in sorted(self.env.items()))
        args = " ".join(a if a != "{OUT}" else out_folder for a in self.argv)
        return f"{env}python {args}"


def _params(domain: str, ranges: dict, n: int, step_index: int) -> dict:
    """One instance's parameters, by generate_all.py's own formula."""
    if domain == "blocksworld":
        start, end = ranges["blocks"]
        step = float(end - start) / float(n)  # (max-start)/(1+max_id-start_id)
        return {"blocks": int(start + step * step_index)}
    num = float(n)
    out = {}
    for name, (start, end) in ranges.items():
        lo = start
        if domain == "rovers" and name == "objectives":
            # rovers/generate_all.py: step_objectives = (1 + max_objectives - starting_cameras) / n
            lo = ranges["cameras"][0]
        step = float(1 + end - lo) / num
        out[name] = int(step * step_index + start)
    return out


def _spec(domain: str, tier: str, n: int, seed_base: int, i: int) -> GenSpec:
    params = _params(domain, IPC_TEST_RANGES[domain][tier], n, i)
    instance_id = i + 1
    seed = seed_base + i
    argv = [f"{domain}.py"]
    for name, flag in _FLAGS[domain]:
        argv += [flag, str(params[name])]
    argv += [_OUT_FLAG[domain], "{OUT}", _ID_FLAG[domain], str(instance_id), "--seed", str(seed)]
    env = {"PYTHONHASHSEED": _HASHSEED[domain]} if _HASHSEED[domain] else {}
    return GenSpec(domain, tier, instance_id, seed, params, tuple(argv), env)


def ladder(domains=DOMAINS, tiers=TIERS) -> list[GenSpec]:
    """Our D5b problems: N_PER_TIER per (domain, tier), fresh seeds."""
    return [
        _spec(d, t, N_PER_TIER, SEED_BASE[t], i)
        for d in domains
        for t in tiers
        for i in range(N_PER_TIER)
    ]


def ipc_testing_commands(domain: str, tier: str) -> list[GenSpec]:
    """IPC 2023's own testing/<tier> commands (30 instances, seed 1007..1036)."""
    return [_spec(domain, tier, IPC_TEST_N, IPC_TEST_SEED, i) for i in range(IPC_TEST_N)]


def spec_record() -> dict:
    """Everything needed to regenerate the ladder, as committed in manifest.json."""
    return {
        "source_repo": IPC_REPO,
        "source_commit": IPC_COMMIT,
        "domains": list(DOMAINS),
        "tiers": list(TIERS),
        "n_per_tier": N_PER_TIER,
        "seed_base": dict(SEED_BASE),
        "ipc_test_ranges": {d: {t: {k: list(v) for k, v in r.items()} for t, r in tr.items()}
                            for d, tr in IPC_TEST_RANGES.items()},
        "how_run": "python <clone>/<domain>/<command>, cwd=<work>/problems/<domain>, PYTHONPATH=<clone>, output folder = the tier name",
    }
