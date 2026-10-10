"""Prism v1.5 symbiotic gate (CI-required): exits nonzero on failure.

Checks (all must hold; engine checks skip honestly without binaries):
  1. grade_symbiotic picks first PROVEN, flags repair (pure unit).
  2. grade_symbiotic falls back honestly on empty/single OBSERVED (pure).
  3. anomaly_indices + clean_items + determinism pure units.
  4. predict_candidates top-1 is A on ABCx10 (needs nexora).
  5. auto_topk on ABCx10: top-1 A, PROVEN, program == auto() program.
  6. auto_symbiotic on ABCx10: PROVEN + deterministic + superset keys.
  7. auto_symbiotic on noisy trace: FOUND + anomalies + PROVEN or honest
     fallback, agreement reported, never hallucinated PROVEN on unobserved.
  8. auto_symbiotic on junk: never PROVEN.
  9. watch_symbiotic changes == watch changes on shift pair.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prism import encode, honesty, notice, prove
from prism.engine import Prism

NOISY_ABC = [("X" if (i % 7 == 3) else "ABC"[i % 3]) for i in range(60)]
JUNK = [f"tok{i:04d}x" for i in range(25)]

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
    except Exception as exc:
        FAIL.append(f"{name}: FAIL (error {type(exc).__name__}: {exc})")
        print(f"FAIL {name}: error {type(exc).__name__}: {exc}")
        return
    if r == "skip":
        SKIP.append(name)
        print(f"SKIP {name}")
    else:
        PASS.append(name)
        print(f"PASS {name}")


def c_repair_unit():
    a = honesty.grade("refuted", True, True, "FOUND")
    b = honesty.grade("proved", True, True, "FOUND")
    v = honesty.grade_symbiotic([a, b], nexora_status="FOUND")
    assert v["verdict"] == "PROVEN", v
    assert v["detail"]["selected_index"] == 1, v["detail"]
    assert v["detail"]["repaired"] is True


def c_fallback_unit():
    o = honesty.grade("exhausted", False, False, "FOUND")
    assert honesty.grade_symbiotic([], nexora_status="FOUND")["verdict"] == "OBSERVED"
    assert honesty.grade_symbiotic([o], nexora_status="FOUND")["verdict"] == "OBSERVED"


def c_pure_units():
    assert encode.anomaly_indices([{"index": 1}, {"index": 1}], 4) == [1]
    (kept, _r) = encode.clean_items(list("ABCDE"), [1, 3])
    assert kept[0] == ["A", "C", "E"]
    _out, det = encode.determinism_for(["s0", "s1", "s0", "s1"])
    assert det is True
    _o2, det2 = encode.determinism_for(["s0", "s1", "s0", "s2"])
    assert det2 is False


def c_candidates():
    if not notice.available():
        return "skip"
    cur, cands, _env = notice.predict_candidates(list("ABC" * 10), k=3)
    assert cur == "C", cur
    assert cands and cands[0] == "A", cands


def c_topk_matches_auto():
    if not notice.available() or not prove.available():
        return "skip"
    p = Prism()
    a = p.auto(list("ABC" * 10))
    t = p.auto_topk(list("ABC" * 10), k=3)
    assert t["prediction"]["next"] == "A", t["prediction"]
    assert t["verdict"]["verdict"] == "PROVEN", t["verdict"]
    assert t["selected"]["program"] == a["program"]


def c_symbiotic_cycle():
    if not notice.available() or not prove.available():
        return "skip"
    r = Prism().auto_symbiotic(list("ABC" * 10), k=3)
    assert r["verdict"]["verdict"] == "PROVEN", r["verdict"]
    assert r["proof"]["status"] == "proved", r["proof"]
    assert r["determinism"]["deterministic"] is True, r["determinism"]
    for key in ("program", "legend", "proof", "reach_proof", "verdict",
                "candidates", "selected", "vetoed", "agreement"):
        assert key in r, key


def c_symbiotic_noisy():
    if not notice.available() or not prove.available():
        return "skip"
    r = Prism().auto_symbiotic(list(NOISY_ABC), k=3)
    assert r["observation"]["status"] == "FOUND", r["observation"].get("status")
    assert len(r["observation"].get("anomalies", [])) >= 1
    assert r["verdict"]["verdict"] in ("PROVEN", "OBSERVED", "INCONCLUSIVE",
                                       "REFUTED"), r["verdict"]
    if r["verdict"]["verdict"] == "PROVEN":
        assert r["selected"]["pair_observed"] is True, r["selected"]


def c_symbiotic_junk():
    r = Prism().auto_symbiotic(list(JUNK), k=3)
    assert r["verdict"]["verdict"] in ("OBSERVED", "INCONCLUSIVE"), r["verdict"]
    assert r["verdict"]["verdict"] != "PROVEN"


def c_watch_symbiotic():
    if not notice.available():
        return "skip"
    p = Prism()
    seq = [list("ABC" * 10), list(JUNK)]
    assert p.watch_symbiotic(seq)["changes"] == p.watch(seq)["changes"] == [1]


for name, fn in [("repair-unit", c_repair_unit),
                 ("fallback-unit", c_fallback_unit),
                 ("pure-units", c_pure_units),
                 ("candidates", c_candidates),
                 ("topk-matches-auto", c_topk_matches_auto),
                 ("symbiotic-cycle", c_symbiotic_cycle),
                 ("symbiotic-noisy", c_symbiotic_noisy),
                 ("symbiotic-junk", c_symbiotic_junk),
                 ("watch-symbiotic", c_watch_symbiotic)]:
    check(name, fn)

print(f"\nprism-symbiotic-eval: {len(PASS)} passed, {len(SKIP)} skipped, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
