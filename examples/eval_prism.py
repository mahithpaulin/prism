"""Prism ground-truth gate (CI-required): exits nonzero on failure.

Checks (all must hold):
  1. honesty.grade promotes only verified proofs (pure unit).
  2. honesty.grade refuses definite-without-proof (pure unit).
  3. Nexora cycle ABCx3 is FOUND (skipped honestly if nexora missing).
  4. Axiom transitive closure proves (skipped honestly if binary missing).
  5. notice_then_prove never returns PROVEN without a built binary.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prism import honesty, notice, prove
from prism.engine import Prism

CLOSURE = (
    "edge(a, b).\nedge(b, c).\n"
    "path(X, Y) :- edge(X, Y).\n"
    "path(X, Z) :- path(X, Y), edge(Y, Z).\n"
    "?- path(a, c).\n"
)

PASS = []
SKIP = []
FAIL = []


def check(name, fn):
    try:
        r = fn()
    except AssertionError as exc:
        FAIL.append(f"{name}: FAIL ({exc})")
        print(f"FAIL {name}: {exc}")
        return
    if r == "skip":
        SKIP.append(name)
        print(f"SKIP {name}")
    else:
        PASS.append(name)
        print(f"PASS {name}")


def c_grade_proven():
    v = honesty.grade("proved", True, True, "FOUND")
    assert v["verdict"] == "PROVEN", v


def c_grade_refuses_unverified():
    v = honesty.grade("proved", False, False, "FOUND")
    assert v["verdict"] == "INCONCLUSIVE", v


def c_cycle():
    if not notice.available():
        return "skip"
    obs = notice.observe(list("ABC" * 10))
    assert obs["status"] == "FOUND", obs.get("explanation", "")


def c_closure():
    if not prove.available():
        return "skip"
    out = prove.prove(CLOSURE)
    assert out["status"] == "proved", out.get("summary", "")
    assert out.get("proof_present") is True, out


def c_never_fabricates():
    p = Prism()
    combo = p.notice_then_prove(list("ABC" * 10), CLOSURE)
    assert combo["verdict"]["verdict"] in ("PROVEN", "OBSERVED", "INCONCLUSIVE",
                                           "REFUTED", "IMPOSSIBLE"), combo["verdict"]
    if not prove.available():
        assert combo["verdict"]["verdict"] in ("OBSERVED", "INCONCLUSIVE"), combo["verdict"]


for name, fn in [("grade-proven", c_grade_proven),
                 ("grade-refuses-unverified", c_grade_refuses_unverified),
                 ("cycle-found", c_cycle),
                 ("closure-proved", c_closure),
                 ("never-fabricates", c_never_fabricates)]:
    check(name, fn)

print(f"\nprism-eval: {len(PASS)} passed, {len(SKIP)} skipped, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
