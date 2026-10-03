"""Registered constants of the delivered-rerun prereg, as literal asserts.

Spec: development/reference/delivered_rerun_prereg.md (written 2026-10-02).
Freeze gate 2 (.claude/skills/freeze-protocol/SKILL.md): every quantity the
prereg names appears here as a literal and is asserted by
`assert_registered()`, which the live entry point calls before reading a row.

Two kinds of constant live here:

* statistical constants (margin, seed, resamples, thresholds). These are the
  same in live and fixture mode and are asserted unconditionally at import.
* size constants (rows per cell, per variant, per task, domain count). These
  are bundled in a `Design`. Live mode uses `REGISTERED` and asserts every
  field; the synthetic fixture under tests/fixtures/delivered_rerun/ carries
  its own small `Design` (it cannot have 9,120 rows per cell).
"""
from __future__ import annotations

from dataclasses import dataclass, field

# --------------------------------------------------------------- roster (§2)
# Directory tags (cluster cell names) -> the model id every row must carry.
# Ids checked against results/sweep5v2-live (2026-10-03): same weights and
# quantisations as canonical (§2 "Nothing else differs").
MODEL_IDS: dict[str, str] = {
    "Qwen3_5_9B": "Qwen/Qwen3.5-9B",
    "gemma4_26b-a4b": "cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit",
    "qwen3_6_35b": "cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit",
}
PART_A_MODELS: tuple[str, ...] = ("gemma4_26b-a4b", "Qwen3_5_9B", "qwen3_6_35b")
PART_B_MODEL = "gemma4_26b-a4b"
CONTROL_MODEL = "gemma4_26b-a4b"                    # §3 "Gemma first"
QWEN_MODELS: tuple[str, ...] = ("Qwen3_5_9B", "qwen3_6_35b")
THINK = "off"                                        # §2 thinking off
TOOL_FILTER = "all"                                  # §2 all tools visible
STYLE_A = "minimal"                                  # §2 Part A prompt style
STYLE_B = "neutral"                                  # §2 Part B prompt style
RUN_TAG_A = "delivered-rerun"                        # §2 run tag
RUN_TAG_B = "delivered-rerun-neutral"                # §2 run tag
TASKS: tuple[str, ...] = ("solve", "validate_domain", "validate_problem",
                          "validate_plan", "simulate")
PART_B_TASK = "validate_plan"
PLAIN: tuple[int, ...] = (11, 12, 13)                # §2 plain arm
STEERED: tuple[int, ...] = (14, 15, 16)              # §2 steered arm
VARIANTS: tuple[int, ...] = PLAIN + STEERED
ARMS: dict[str, tuple[int, ...]] = {"plain": PLAIN, "steered": STEERED}
# E3 pairing: the plain wording v is paired with the steered wording v + 3 on
# the same fixture (the same mapping tools/reanalysis/common.py build_pairs
# uses). Prereg §4 says "same pairing"; the variant cannot be literally equal.
STEER_OFFSET = 3

# --------------------------------------------------------------- apparatus (§2)
STORAGE_CAP = 65_536          # §2 delta 1: answers stored up to 65,536 chars
REGISTERED_STORAGE_CUTS = 0   # §2 delta 1: "Registered expectation: zero rows cut"
CONTEXT_WINDOW = 16_384       # §2 delta 2 / §8a: the 16,384-token window
LEAKED_PREFIX = "<|channel>thought\n<channel|>"   # §2 delta 3

# --------------------------------------------------------------- statistics (§3, §4)
MARGIN = 5.0                  # §3 "TOST at ±5 points"; §5 "[−5, +5]"
GROSS = 10.0                  # §3 "no cell of any model has |Δ̂| > 10 points"
QWEN_CELLS_TOTAL = 20         # §3 "at least 18 of the 20 Qwen cells"
QWEN_CELLS_REQUIRED = 18
PARITY_CELLS = 30             # §3 "3 × 5 × 2 = 30 cells"
B_BOOT = 10_000               # §3 "10,000 resamples"
SEED = 20261002               # §3 "seed 20261002"
CI_PARITY = 0.90              # §3 "the 90% confidence interval of Δ"
CI_ENDPOINT = 0.95            # §4 E1/E2/E3 "95% interval"
HOLM_FAMILY = 15              # §4 E2/E3 "Holm across the 15 comparisons"
HOLM_ALPHA = 0.05
UNPAIRED_VOID_FRAC = 0.01     # §3 "more than 1% unpaired rows is VOID"
EXCEPTION_VOID_FRAC = 0.01    # §7 "more than 1% ... infrastructure failures or exceptions"
R4_THRESHOLD = 90.0           # §5 R4 "at least 90% for each model"
R3_MODELS_REQUIRED = 2        # §5 R3 "at least two of the three models"
Z90 = 1.6448536269514722      # two-sided 90% normal quantile (Newcombe secondary)

# failure_reason values that mean "the harness raised" (runner.py except-branch,
# plus the scoring-error path). Counted by the §7 exception VOID rule.
EXCEPTION_REASONS: frozenset[str] = frozenset({"exception", "ollama_parse_error"})


@dataclass(frozen=True)
class Design:
    """Size constants of one corpus layout (live = REGISTERED; fixture = small)."""
    name: str
    n_part_a_cell: int                      # §7 rows per Part A cell (one model)
    n_part_b: int                           # §7 rows of Part B
    per_variant_a: int                      # §7 rows per variant, Part A
    per_variant_b: int                      # §7 rows per variant, Part B
    per_task_variant: dict[str, int] = field(default_factory=dict)
    k_domains: int = 20                     # §3 "the 20 domains"
    n_no_tools_cell: int = 0                # canonical no-tools rows per model (v11-13)
    # Canonical delivered bounds per Part A cell, as (n, delivered ok,
    # censored) counts of the e2e overlay (`e2e_strict`), keyed
    # (model, task, arm). Used ONLY by the readout-time band tripwire.
    canonical_delivered_counts: dict[tuple[str, str, str], tuple[int, int, int]] = \
        field(default_factory=dict)


# Per (task, variant) row counts. Derived from results/sweep5v2-live on
# 2026-10-03 (20 domains: solve 5 problems, validate_domain 5 + 1 negative
# domain, validate_problem 5 + 5 negative problems, validate_plan 5 problems x
# 10 plans, simulate 5 problems). Not a prereg number by itself; it must sum to
# the registered 1,520 per variant, which is asserted.
PER_TASK_VARIANT_REGISTERED: dict[str, int] = {
    "solve": 100, "validate_domain": 120, "validate_problem": 200,
    "validate_plan": 1000, "simulate": 100,
}

# Canonical delivered surface per cell, counted from
# results/derived/e2e_overlay/sweep5v2-live/slurm_vllm_<m>_off_tools_all_minimal.e2e.jsonl
# on 2026-10-03: (n, e2e_strict is True, e2e_strict == "indeterminate").
# tests/test_delivered_rerun_analysis.py re-counts these from the overlay when
# it is on disk.
CANONICAL_DELIVERED_COUNTS: dict[tuple[str, str, str], tuple[int, int, int]] = {
    ("Qwen3_5_9B", "simulate", "plain"): (300, 0, 117),
    ("Qwen3_5_9B", "simulate", "steered"): (300, 0, 76),
    ("Qwen3_5_9B", "solve", "plain"): (300, 78, 98),
    ("Qwen3_5_9B", "solve", "steered"): (300, 83, 113),
    ("Qwen3_5_9B", "validate_domain", "plain"): (360, 359, 1),
    ("Qwen3_5_9B", "validate_domain", "steered"): (360, 360, 0),
    ("Qwen3_5_9B", "validate_plan", "plain"): (3000, 2423, 194),
    ("Qwen3_5_9B", "validate_plan", "steered"): (3000, 2608, 59),
    ("Qwen3_5_9B", "validate_problem", "plain"): (600, 553, 19),
    ("Qwen3_5_9B", "validate_problem", "steered"): (600, 526, 20),
    ("gemma4_26b-a4b", "simulate", "plain"): (300, 0, 82),
    ("gemma4_26b-a4b", "simulate", "steered"): (300, 0, 82),
    ("gemma4_26b-a4b", "solve", "plain"): (300, 43, 63),
    ("gemma4_26b-a4b", "solve", "steered"): (300, 71, 107),
    ("gemma4_26b-a4b", "validate_domain", "plain"): (360, 336, 17),
    ("gemma4_26b-a4b", "validate_domain", "steered"): (360, 341, 13),
    ("gemma4_26b-a4b", "validate_plan", "plain"): (3000, 197, 2790),
    ("gemma4_26b-a4b", "validate_plan", "steered"): (3000, 1665, 1188),
    ("gemma4_26b-a4b", "validate_problem", "plain"): (600, 506, 93),
    ("gemma4_26b-a4b", "validate_problem", "steered"): (600, 550, 50),
    ("qwen3_6_35b", "simulate", "plain"): (300, 0, 117),
    ("qwen3_6_35b", "simulate", "steered"): (300, 0, 81),
    ("qwen3_6_35b", "solve", "plain"): (300, 38, 123),
    ("qwen3_6_35b", "solve", "steered"): (300, 50, 93),
    ("qwen3_6_35b", "validate_domain", "plain"): (360, 331, 26),
    ("qwen3_6_35b", "validate_domain", "steered"): (360, 336, 23),
    ("qwen3_6_35b", "validate_plan", "plain"): (3000, 1650, 1058),
    ("qwen3_6_35b", "validate_plan", "steered"): (3000, 2276, 423),
    ("qwen3_6_35b", "validate_problem", "plain"): (600, 448, 139),
    ("qwen3_6_35b", "validate_problem", "steered"): (600, 493, 89),
}

REGISTERED = Design(
    name="registered",
    n_part_a_cell=9_120,
    n_part_b=6_000,
    per_variant_a=1_520,
    per_variant_b=1_000,
    per_task_variant=PER_TASK_VARIANT_REGISTERED,
    k_domains=20,
    n_no_tools_cell=4_560,
    canonical_delivered_counts=CANONICAL_DELIVERED_COUNTS,
)


def assert_statistical_constants() -> None:
    """Literal asserts on the prereg's statistical quantities (gate 2)."""
    assert MARGIN == 5.0, MARGIN
    assert GROSS == 10.0, GROSS
    assert QWEN_CELLS_TOTAL == 20 and QWEN_CELLS_REQUIRED == 18
    assert PARITY_CELLS == 30 == len(PART_A_MODELS) * len(TASKS) * len(ARMS)
    assert QWEN_CELLS_TOTAL == len(QWEN_MODELS) * len(TASKS) * len(ARMS)
    assert B_BOOT == 10_000, B_BOOT
    assert SEED == 20261002, SEED
    assert CI_PARITY == 0.90 and CI_ENDPOINT == 0.95
    assert HOLM_FAMILY == 15 == len(PART_A_MODELS) * len(TASKS)
    assert UNPAIRED_VOID_FRAC == 0.01 and EXCEPTION_VOID_FRAC == 0.01
    assert R4_THRESHOLD == 90.0 and R3_MODELS_REQUIRED == 2
    assert STORAGE_CAP == 65_536 and REGISTERED_STORAGE_CUTS == 0
    assert CONTEXT_WINDOW == 16_384
    assert THINK == "off" and TOOL_FILTER == "all"
    assert STYLE_A == "minimal" and STYLE_B == "neutral"
    assert PLAIN == (11, 12, 13) and STEERED == (14, 15, 16)
    assert set(PART_A_MODELS) == {"Qwen3_5_9B", "gemma4_26b-a4b", "qwen3_6_35b"}
    assert PART_B_MODEL == CONTROL_MODEL == "gemma4_26b-a4b"
    assert PART_B_TASK == "validate_plan"
    assert LEAKED_PREFIX == "<|channel>thought\n<channel|>"


def assert_registered(design: Design) -> None:
    """Literal asserts on the size constants; live mode calls this (gate 2)."""
    assert design is REGISTERED, "live mode must run on the REGISTERED design"
    assert design.n_part_a_cell == 9_120, design.n_part_a_cell        # §2, §7
    assert design.n_part_b == 6_000, design.n_part_b                  # §2, §7
    assert design.per_variant_a == 1_520, design.per_variant_a        # §7
    assert design.per_variant_b == 1_000, design.per_variant_b        # §7
    assert design.k_domains == 20, design.k_domains                   # §3
    assert design.n_part_a_cell == design.per_variant_a * len(VARIANTS)
    assert design.n_part_b == design.per_variant_b * len(VARIANTS)
    assert sum(design.per_task_variant.values()) == design.per_variant_a
    assert design.per_task_variant[PART_B_TASK] == design.per_variant_b
    # 3,000 trials per cell of the Part B 2 x 2 (§2)
    assert design.per_variant_b * len(PLAIN) == 3_000
    # Part A total (§2): 3 x 9,120 = 27,360
    assert design.n_part_a_cell * len(PART_A_MODELS) == 27_360
    assert design.n_no_tools_cell == design.per_variant_a * len(PLAIN)
    assert set(design.canonical_delivered_counts) == {
        (m, t, a) for m in PART_A_MODELS for t in TASKS for a in ARMS}


assert_statistical_constants()
