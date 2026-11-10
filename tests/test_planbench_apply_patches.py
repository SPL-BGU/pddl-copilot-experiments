"""planbench/apply_patches.py: per-edit sentinels and an idempotent main() (ISS-025).

Before the fix, patch_init and patch_llm_utils skipped only on the
PATCH_MARKER comment. The laptop's tree carries hand-made versions of those
edits (the same code, other comments, no marker), so main() found neither the
marker nor the original anchor and sys.exit()ed at patch 1.

The trees below are small synthetic files that hold the exact upstream
anchors (karthikv792/LLMs-Planning @ fc638a1, still upstream HEAD on
2026-11-09) and the exact hand-patched forms (SPL-BGU fork commits 6aac3ad and
0378bfe). One extra check runs main() on a COPY of a real tree when one is
found ($PDDL_PLANBENCH_TREE, else <repo>/external/LLMs-Planning); the
original tree is only read.

Standalone: `python3 tests/test_planbench_apply_patches.py`; also under pytest.
"""

import importlib.util
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    "planbench_apply_patches", REPO / "planbench" / "apply_patches.py"
)
AP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(AP)

FILES = (
    "plan-bench/utils/__init__.py",
    "plan-bench/utils/llm_utils.py",
    "plan-bench/response_generation.py",
    "plan-bench/response_evaluation.py",
)

# --- upstream forms (anchors byte-exact; surrounding lines abridged) --------

UP_INIT = (
    "import os\n"
    "import random\n"
    "import openai\n"
    "\n"
    'openai.api_key = os.environ["OPENAI_API_KEY"]\n'
    "random.seed(10)\n"
    "\n"
    "from .llm_utils import *\n"
)

UP_LLM_UTILS = (
    "from transformers import StoppingCriteriaList, StoppingCriteria\n"
    "import openai\n"
    "import os\n"
    'openai.api_key = os.environ["OPENAI_API_KEY"]\n'
    "def generate_from_bloom(model, tokenizer, query, max_tokens):\n"
    "    return ''\n"
    "\n"
    'def send_query(query, engine, max_tokens, model=None, stop="[STATEMENT]"):\n'
    "    max_token_err_flag = False\n"
    "    if engine == 'bloom':\n"
    "        return ''\n"
    "    elif 'gpt-4' in engine:\n"
    "        text_response = ''\n"
    "        return text_response.strip()        \n"
    "    else:\n"
    "        try:\n"
    "            response = openai.Completion.create(\n"
    "                model=engine,\n"
    "                prompt=query,\n"
    "            )\n"
    "        except Exception as e:\n"
    "            max_token_err_flag = True\n"
    "        return ''\n"
)

UP_RESPONSE_GENERATION = (
    "import os\n"
    "import json\n"
    "class ResponseGenerator:\n"
    "    def get_responses(self, task_name, specified_instances = [], run_till_completion=False):\n"
    "        output_dir = f\"responses/{self.data['domain_name']}/{self.engine}/\"\n"
    "        os.makedirs(output_dir, exist_ok=True)\n"
    "        for instance in []:\n"
    "            if True:\n"
    "                if len(specified_instances) > 0:\n"
    "                    if instance['instance_id'] not in specified_instances:\n"
    "                        continue\n"
    "                    else:\n"
    "                        specified_instances.remove(instance['instance_id'])                   \n"
    "                \n"
    "                if self.verbose:\n"
    "                    print(f\"Sending query to LLM: Instance {instance['instance_id']}\")\n"
    "                query = instance[\"query\"]\n"
    "                stop_statement = \"[STATEMENT]\"\n"
)

UP_RESPONSE_EVALUATION = (
    "import os\n"
    "class ResponseEvaluator:\n"
    "    def load_json(self, task_name):\n"
    "        response_dir = 'responses/'\n"
    "        if False:\n"
    "            pass\n"
    "        else:\n"
    "            assert os.path.exists(response_dir+f\"{task_name}.json\")\n"
    "            load_dir = response_dir\n"
    "        return load_dir\n"
    "\n"
    "    def parse_output(self, actions, response):\n"
    "        output_dict = {}\n"
    "        for line in []:\n"
    "            if True:\n"
    "                if True:\n"
    "                    precond_act_flag = False\n"
    "\n"
    "        return output_dict\n"
    "\n"
    "    def evaluate_verification(self, problem, llm_response):\n"
    "        if True:\n"
    "            if True:\n"
    "                parsed_llm_response = self.parse_output(problem.actions, llm_response)\n"
    "        return parsed_llm_response\n"
)

UPSTREAM = dict(zip(FILES, (UP_INIT, UP_LLM_UTILS, UP_RESPONSE_GENERATION,
                            UP_RESPONSE_EVALUATION)))

# --- the hand-patched forms on the laptop tree (fork 6aac3ad + 0378bfe) -----

HAND_INIT = UP_INIT.replace(
    'openai.api_key = os.environ["OPENAI_API_KEY"]\n',
    'openai.api_key = os.environ.get("OPENAI_API_KEY", "")  # tolerate missing key (e.g. local-model runs)\n',
)

HAND_HEADER = (
    "# Tolerant imports: let this module load when only a subset of backends is\n"
    "# installed, and when no OPENAI_API_KEY is set (e.g. when driving a local model).\n"
    "import os\n"
    "try:\n"
    "    from transformers import StoppingCriteriaList, StoppingCriteria  # noqa: F401\n"
    "except ImportError:\n"
    "    StoppingCriteriaList = StoppingCriteria = None\n"
    "try:\n"
    "    import openai\n"
    "\n"
    '    openai.api_key = os.environ.get("OPENAI_API_KEY", "")\n'
    "except ImportError:\n"
    "    openai = None\n"
)
HAND_DISPATCH = (
    "        return text_response.strip()\n"
    "    elif engine.startswith('pddl_copilot__'):\n"
    "        # PDDL_COPILOT_PATCH: route to our local/remote model fleet.\n"
    "        import sys, pathlib\n"
    "        sys.path.insert(\n"
    "            0,\n"
    "            os.environ.get(\n"
    "                'PDDL_COPILOT_EXPERIMENTS_ROOT',\n"
    "                str(pathlib.Path(__file__).resolve().parents[3]),\n"
    "            ),\n"
    "        )\n"
    "        from planbench.engine import pddl_copilot_send_query\n"
    "        return pddl_copilot_send_query(\n"
    "            query, engine, max_tokens, model=model, stop=stop\n"
    "        )\n"
)
_UP_HEADER = (
    "from transformers import StoppingCriteriaList, StoppingCriteria\n"
    "import openai\n"
    "import os\n"
    'openai.api_key = os.environ["OPENAI_API_KEY"]\n'
)
HAND_LLM_UTILS_HEADER_ONLY = UP_LLM_UTILS.replace(_UP_HEADER, HAND_HEADER)  # fork 6aac3ad
HAND_LLM_UTILS = HAND_LLM_UTILS_HEADER_ONLY.replace(  # + 0378bfe
    "        return text_response.strip()        \n", HAND_DISPATCH
)

HAND_RESPONSE_GENERATION = UP_RESPONSE_GENERATION.replace(
    "        output_dir = f\"responses/{self.data['domain_name']}/{self.engine}/\"\n",
    "        # Snapshot to a set so the per-instance filter below doesn't mutate\n"
    "        # state.\n"
    "        _specified_instances_set = set(specified_instances or [])\n"
    "        output_dir = f\"responses/{self.data['domain_name']}/{self.engine}/\"\n",
).replace(
    "                if len(specified_instances) > 0:\n"
    "                    if instance['instance_id'] not in specified_instances:\n"
    "                        continue\n"
    "                    else:\n"
    "                        specified_instances.remove(instance['instance_id'])                   \n",
    "                # Filter against the immutable snapshot (see above).\n"
    "                if _specified_instances_set and instance['instance_id'] not in _specified_instances_set:\n"
    "                    continue\n",
)


@contextmanager
def _tree(files: dict):
    with tempfile.TemporaryDirectory() as d:
        root = Path(d) / "LLMs-Planning"
        for rel, text in files.items():
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        yield root


def _snapshot(root: Path) -> dict:
    return {rel: (root / rel).read_text() for rel in FILES}


def _run_main(root: Path) -> None:
    saved = sys.argv
    sys.argv = ["apply_patches.py", str(root)]
    try:
        AP.main()
    finally:
        sys.argv = saved


def _assert_fully_patched(snap: dict) -> None:
    init, llm, gen, ev = (snap[f] for f in FILES)
    assert AP._INIT_SENTINEL.search(init)
    assert all(s in llm for s in AP._LLM_UTILS_HEADER_SENTINELS)
    assert all(s in llm for s in AP._LLM_UTILS_DISPATCH_SENTINELS)
    assert llm.count("from planbench.engine import pddl_copilot_send_query") == 1
    assert gen.count("_specified_instances_set = set(") == 1
    assert "specified_instances.remove(" not in gen
    assert gen.count("os.environ['PDDL_COPILOT_INSTANCE_ID']") == 1
    assert "output_dict.setdefault('valid', None)" in ev
    assert "parsed_llm_response = {'valid': None}" in ev
    assert "[eval] no response file for" in ev
    for text in snap.values():
        compile(text, "<patched>", "exec")


def test_fresh_upstream_tree_patches_then_is_idempotent():
    with _tree(UPSTREAM) as root:
        _run_main(root)
        first = _snapshot(root)
        _assert_fully_patched(first)
        _run_main(root)
        assert _snapshot(root) == first, "second main() run changed bytes"


def test_hand_patched_tree_runs_end_to_end_without_rewriting():
    """The ISS-025 case: patches 1 to 4 present by hand, no marker."""
    files = dict(UPSTREAM)
    files["plan-bench/utils/__init__.py"] = HAND_INIT
    files["plan-bench/utils/llm_utils.py"] = HAND_LLM_UTILS
    files["plan-bench/response_generation.py"] = HAND_RESPONSE_GENERATION
    with _tree(files) as root:
        # Patch 5 (evaluation) is applied first so only patch 6 is missing,
        # as on the laptop tree before its uncommitted stamp.
        AP.patch_response_evaluation(root)
        before = _snapshot(root)
        _run_main(root)  # used to sys.exit at patch_init
        after = _snapshot(root)
        _assert_fully_patched(after)
        for rel in ("plan-bench/utils/__init__.py", "plan-bench/utils/llm_utils.py",
                    "plan-bench/response_evaluation.py"):
            assert after[rel] == before[rel], f"{rel} rewritten"
        _run_main(root)
        assert _snapshot(root) == after


def test_marker_only_guard_would_have_exited():
    """Pin the failure the fix removes: the hand forms carry no marker."""
    assert AP.PATCH_MARKER not in HAND_INIT
    assert 'openai.api_key = os.environ["OPENAI_API_KEY"]' not in HAND_INIT
    assert AP.PATCH_MARKER not in HAND_LLM_UTILS


def test_partial_llm_utils_gets_only_the_missing_edit():
    """Fork commit 6aac3ad: tolerant header by hand, dispatch missing."""
    files = dict(UPSTREAM)
    files["plan-bench/utils/llm_utils.py"] = HAND_LLM_UTILS_HEADER_ONLY
    with _tree(files) as root:
        AP.patch_llm_utils(root)
        text = (root / "plan-bench/utils/llm_utils.py").read_text()
        assert text.startswith(HAND_HEADER), "hand header was rewritten"
        assert text.count("engine.startswith('pddl_copilot__')") == 1
        assert text.count("import openai\n") == 1


def test_partial_response_generation_gets_only_the_missing_edit():
    half = UP_RESPONSE_GENERATION.replace(
        "        output_dir = f\"responses/{self.data['domain_name']}/{self.engine}/\"\n",
        "        _specified_instances_set = set(specified_instances or [])\n"
        "        output_dir = f\"responses/{self.data['domain_name']}/{self.engine}/\"\n",
    )
    files = dict(UPSTREAM)
    files["plan-bench/response_generation.py"] = half
    with _tree(files) as root:
        AP.patch_response_generation(root)
        text = (root / "plan-bench/response_generation.py").read_text()
        assert text.count("_specified_instances_set = set(") == 1
        assert "specified_instances.remove(" not in text


def test_drifted_upstream_still_exits():
    files = dict(UPSTREAM)
    files["plan-bench/utils/__init__.py"] = "import os\nopenai.api_key = 'x'\n"
    with _tree(files) as root:
        try:
            AP.patch_init(root)
        except SystemExit as exc:
            assert "anchor not found" in str(exc)
        else:
            raise AssertionError("no SystemExit on a drifted anchor")


def _real_tree() -> Path | None:
    import os

    cand = os.environ.get("PDDL_PLANBENCH_TREE")
    p = Path(cand) if cand else REPO / "external" / "LLMs-Planning"
    return p if all((p / rel).is_file() for rel in FILES) else None


def test_real_tree_copy_if_present():
    """main() on a COPY of the real tree: exits 0, then a second run is a no-op."""
    src = _real_tree()
    if src is None:
        print("  (skip: no PlanBench tree; set PDDL_PLANBENCH_TREE to run this check)")
        return
    with tempfile.TemporaryDirectory() as d:
        root = Path(d) / "LLMs-Planning"
        for rel in FILES:
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src / rel, root / rel)
        _run_main(root)
        first = _snapshot(root)
        _assert_fully_patched(first)
        _run_main(root)
        assert _snapshot(root) == first


if __name__ == "__main__":
    _tests = [(n, f) for n, f in sorted(globals().items())
              if n.startswith("test_") and callable(f)]
    _failed = 0
    for _name, _fn in _tests:
        try:
            _fn()
        except (Exception, SystemExit) as exc:  # noqa: BLE001
            _failed += 1
            print(f"  FAIL {_name}: {type(exc).__name__}: {exc}")
    print(f"\ntest_planbench_apply_patches: {len(_tests) - _failed}/{len(_tests)} passed")
    sys.exit(1 if _failed else 0)
