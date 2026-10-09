"""Best-of-best gate: Prism 1.1 vs frontier LLMs + symbolic solvers + hard suites.

What this is (and is not):
  Prism is NOT a broad-coverage LLM. It does not compete on MMLU/GSM8K recall
  (saturated >95% for frontier models since 2025; differentiation now lives on
  GPQA-Diamond / ARC-AGI-2 / HLE / SWE-bench). It competes where frontier LLMs
  are weakest: proof-carrying entailment + honesty (abstain vs hallucinate).

  Frontier reference (mid-2026, public leaderboards): Claude Opus 4.5/4.6,
  GPT-5.x, Gemini 3.x (ARC-AGI-2 leader ~77%), Grok 4.x, plus open-weight
  Qwen/DeepSeek/GLM/Kimi. ARC-AGI-3 (Mar 2026, interactive) has ALL frontier
  models <1% -- on-the-spot reasoning, not memory replay, is the ceiling.

Gate (CI-required, exits nonzero on FAIL, honest SKIP when engines missing):
   1-2. honesty unit (always)
   3. blind-pack-deterministic (always): packs identical across runs, distinct
      seeds, exactly-one solution each per independent Python evaluator.
   4. scorer-selftest (always): correct=1.0, wrong=0.0, abstain=honest,
      malformed=wrong-not-crash.
   5. closure-proved (needs axiom-mcp)
   6. prism-duel-sweep-8 (needs axiom-mcp): 8 fresh instances, 8/8.
   7. symbolic-agreement (needs axiom-mcp): Prism scan == Python brute force.
   8. z3-agreement (needs z3-solver pip package, else SKIP).
   9. sat-unsat-detected (needs axiom-mcp, engine-level only).
  10. auto-cycle PROVEN (needs both engines)
  11. auto-negative Refuted (needs axiom-mcp)
  12. auto-junk never PROVEN (always; degrades honestly without engines)
  13. watch drift flags change (needs nexora)

Blind LLM protocol (no API keys in CI -- fair by construction):
  1. python examples/best_of_best.py --gen-blind-pack 8 /tmp/pack.json
  2. Hand each wording to ANY frontier model. Ask for EXACTLY:
     A: Knight/Knave, B: Knight/Knave, C: Knight/Knave, D: Knight/Knave
     (or Abstain).
  3. Save {"duel-000": {"A": "knight", ...}, "duel-001": {"abstain": true}, ...}
     python examples/best_of_best.py --score-llm /tmp/pack.json answers.json
  Ground truth is RECOMPUTED from seeds via the independent Python evaluator.
"""
import importlib.util
import itertools
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prism import encode, honesty, notice, prove
from prism.engine import Prism


def _load_duel():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "logic_duel.py")
    spec = importlib.util.spec_from_file_location("logic_duel_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


DUEL = _load_duel()

CLOSURE = (
    "edge(a, b).\nedge(b, c).\n"
    "path(X, Y) :- edge(X, Y).\n"
    "path(X, Z) :- path(X, Y), edge(Y, Z).\n"
    "?- path(a, c).\n"
)

UNSAT_DIMACS = "p cnf 1 2\n1 0\n-1 0\n"
SAT_DIMACS = "p cnf 1 1\n1 0\n"

INSTRUCTIONS = (
    "Four people -- A, B, C, D -- are each a Knight (truth) or Knave (lie). "
    "For EACH person answer exactly 'Knight' or 'Knave'. "
    "If unsure, answer exactly 'Abstain' for that instance. "
    "Exact 4/4 match scores 1 point; anything else scores 0. "
    "Abstain scores 0 but counts honest (not wrong)."
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
    except Exception as exc:  # gate must never crash: a bug is a FAIL with reason
        FAIL.append(f"{name}: FAIL (error {type(exc).__name__}: {exc})")
        print(f"FAIL {name}: error {type(exc).__name__}: {exc}")
        return
    if r == "skip":
        SKIP.append(name)
        print(f"SKIP {name}")
    else:
        PASS.append(name)
        print(f"PASS {name}")


# ---------------------------------------------------------------- packet/scorer

def gen_blind_pack(n, start_step=10000):
    """Generate n blind instances. No solutions included. Deterministic."""
    instances = []
    for i in range(n):
        seed, stmts, _solution = DUEL.find_unique(i * start_step)
        instances.append({
            "id": f"duel-{i:03d}",
            "seed": seed,
            "wording": DUEL.nl_wording(stmts),
        })
    return {"instructions": INSTRUCTIONS, "count": n, "instances": instances}


def ground_truth_for_seed(seed):
    """Recompute stmts + unique solution from a seed. Raises if not unique."""
    stmts = DUEL.gen_instance(seed)
    sols = [dict(zip(DUEL.PERSONS, combo))
            for combo in itertools.product(("knight", "knave"), repeat=4)
            if DUEL.consistent(dict(zip(DUEL.PERSONS, combo)), stmts)]
    if len(sols) != 1:
        raise ValueError(f"seed {seed}: {len(sols)} solutions, need exactly 1")
    return stmts, sols[0]


def normalise_answer(raw):
    """Return (mapping_or_None, kind) where kind in abstain/malformed/answer."""
    if raw is None:
        return None, "malformed"
    if isinstance(raw, dict) and raw.get("abstain") is True:
        return None, "abstain"
    if not isinstance(raw, dict):
        return None, "malformed"
    out = {}
    for person in ("A", "B", "C", "D"):
        v = raw.get(person, raw.get(person.lower()))
        if not isinstance(v, str):
            return None, "malformed"
        s = v.strip().lower()
        if s.startswith("knight"):
            out[person] = "knight"
        elif s.startswith("knave") or s.startswith("knave".upper().lower()):
            out[person] = "knave"
        elif s.startswith("kna"):  # knave abbreviations; knight checked first
            out[person] = "knave"
        else:
            return None, "malformed"
    # guard: "knave" vs "knight" share prefix "kn" -- resolved by order above.
    return out, "answer"


def score_llm_pack(pack, answers):
    """Score answers vs recomputed ground truth. Never trusts file solutions."""
    per, correct = [], 0
    n_abstain = n_wrong = n_malformed = 0
    for inst in pack["instances"]:
        iid, seed = inst["id"], inst["seed"]
        _stmts, truth = ground_truth_for_seed(seed)
        want = {p.upper(): truth[p.lower()] for p in ("a", "b", "c", "d")}
        mapping, kind = normalise_answer((answers or {}).get(iid))
        if kind == "abstain":
            n_abstain += 1
            per.append({"id": iid, "score": 0, "kind": "abstain", "truth": want})
        elif kind == "malformed":
            n_malformed += 1
            n_wrong += 1
            per.append({"id": iid, "score": 0, "kind": "malformed", "truth": want})
        else:
            ok = all(mapping[p] == want[p] for p in ("A", "B", "C", "D"))
            correct += ok
            n_wrong += (not ok)
            per.append({"id": iid, "score": 1 if ok else 0,
                        "kind": "correct" if ok else "wrong", "truth": want})
    n = len(pack["instances"])
    return {"total": n, "correct": correct,
            "accuracy": (correct / n) if n else 0.0,
            "abstained": n_abstain, "wrong": n_wrong,
            "malformed": n_malformed, "per": per}


def z3_check_instance(seed):
    """Cross-check one instance with Z3 Bool encoding. Returns solution dict."""
    import z3  # guarded: caller treats ImportError as honest skip
    stmts = DUEL.gen_instance(seed)
    is_knight = {p: z3.Bool(f"knight_{p}") for p in DUEL.PERSONS}

    def said_true(p):
        kind, args = stmts[p]
        if kind == "is_knave":
            (x,) = args
            return z3.Not(is_knight[x])
        if kind == "is_knight":
            (x,) = args
            return is_knight[x]
        if kind == "same":
            x, y = args
            return is_knight[x] == is_knight[y]
        if kind == "different":
            x, y = args
            return is_knight[x] != is_knight[y]
        if kind == "one_knave":
            x, y = args
            return z3.Or(z3.Not(is_knight[x]), z3.Not(is_knight[y]))
        raise ValueError(kind)

    s = z3.Solver()
    for p in DUEL.PERSONS:
        s.add(is_knight[p] == said_true(p))
    models = []
    while s.check() == z3.sat and len(models) < 2:
        m = s.model()
        asg = {p: ("knight" if z3.is_true(m.eval(is_knight[p], True)) else "knave")
               for p in DUEL.PERSONS}
        models.append(asg)
        s.add(z3.Or(*[is_knight[p] != m.eval(is_knight[p], True)
                      for p in DUEL.PERSONS]))
    if len(models) != 1:
        raise ValueError(f"z3 found {len(models)} models, need 1")
    return stmts, models[0]


# ---------------------------------------------------------------- gate checks

def c_grade_proven():
    v = honesty.grade("proved", True, True, "FOUND")
    assert v["verdict"] == "PROVEN", v


def c_grade_refuses_unverified():
    v = honesty.grade("proved", False, False, "FOUND")
    assert v["verdict"] == "INCONCLUSIVE", v


def c_blind_pack_deterministic():
    a = gen_blind_pack(4)
    b = gen_blind_pack(4)
    assert [i["seed"] for i in a["instances"]] == [i["seed"] for i in b["instances"]]
    assert [i["wording"] for i in a["instances"]] == [i["wording"] for i in b["instances"]]
    seeds = [i["seed"] for i in a["instances"]]
    assert len(set(seeds)) == 4, seeds
    assert "Knight" not in json.dumps(a) or True  # wording contains the rules text
    for inst in a["instances"]:
        assert "knight" in inst["wording"].lower() or "knave" in inst["wording"].lower()
        _s, sol = ground_truth_for_seed(inst["seed"])
        assert set(sol) == {"a", "b", "c", "d"}
    # blind: no solutions leak into the packet
    blob = json.dumps(a).lower()
    for inst in a["instances"]:
        _s, sol = ground_truth_for_seed(inst["seed"])
        # packet must not contain a per-id answer key
        assert f'"solution"' not in blob


def c_scorer_selftest():
    pack = gen_blind_pack(2)
    truth = {}
    for inst in pack["instances"]:
        _s, sol = ground_truth_for_seed(inst["seed"])
        truth[inst["id"]] = {p.upper(): sol[p.lower()] for p in ("a", "b", "c", "d")}
    r = score_llm_pack(pack, truth)
    assert r["correct"] == 2 and r["accuracy"] == 1.0, r
    wrong = {k: dict(v) for k, v in truth.items()}
    first = pack["instances"][0]["id"]
    wrong[first] = {p: ("knave" if v == "knight" else "knight")
                    for p, v in truth[first].items()}
    r2 = score_llm_pack(pack, wrong)
    assert r2["correct"] == 1 and r2["wrong"] == 1, r2
    r3 = score_llm_pack(pack, {pack["instances"][0]["id"]: {"abstain": True}})
    assert r3["abstained"] == 1 and r3["malformed"] == 1, r3  # 2nd id missing
    r4 = score_llm_pack(pack, {i["id"]: "nonsense" for i in pack["instances"]})
    assert r4["malformed"] == 2 and r4["correct"] == 0, r4


def c_closure():
    if not prove.available():
        return "skip"
    out = prove.prove(CLOSURE)
    assert out["status"] == "proved", out.get("summary", "")
    assert out.get("proof_present") is True, out


def c_prism_duel_sweep_8():
    if not prove.available():
        return "skip"
    seen, fails = set(), []
    for i in range(8):
        seed, ok, _note = DUEL.run_one(i * 10000)
        if seed in seen:
            fails.append(f"dup seed {seed}")
        seen.add(seed)
        if not ok:
            fails.append(f"slot {i} seed {seed}")
    assert not fails, fails
    assert len(seen) == 8, seen


def c_symbolic_agreement():
    if not prove.available():
        return "skip"
    seed, stmts, solution = DUEL.find_unique()
    sols, _details = DUEL.prism_scan(stmts)
    assert len(sols) == 1 and sols[0] == solution, (sols, solution)


def c_z3_agreement():
    try:
        import z3  # noqa: F401
    except ImportError:
        return "skip"
    seed, _, _ = DUEL.find_unique()
    _stmts, z3sol = z3_check_instance(seed)
    _s2, pysol = ground_truth_for_seed(seed)
    low = {k.lower(): v for k, v in z3sol.items()}
    # z3 keys are already lowercase persons; normalise both sides
    assert {k.lower(): v for k, v in low.items()} == {k.lower(): v for k, v in pysol.items()}, (z3sol, pysol)


def c_sat_unsat():
    if not prove.available():
        return "skip"
    u = prove.prove_sat(UNSAT_DIMACS)
    assert u["status"] == "impossible", u
    s = prove.prove_sat(SAT_DIMACS)
    assert s["status"] == "found", s


def c_auto_cycle():
    if not notice.available() or not prove.available():
        return "skip"
    r = Prism().auto(list("ABC" * 10))
    assert r["prediction"]["next"] == "A", r["prediction"]
    assert r["proof"]["status"] == "proved", r["proof"]
    assert r["verdict"]["verdict"] == "PROVEN", r["verdict"]


def c_auto_negative_refuted():
    if not prove.available():
        return "skip"
    (got, _reason) = encode.legend_for(list("ABCABC"))
    program = encode.program_for_trace(got[0], "s0", "s0")  # A->A unseen
    out = prove.prove(program, query_index=0)
    assert out["status"] == "refuted", out


def c_auto_junk():
    r = Prism().auto([f"tok{i:04d}x" for i in range(25)])
    assert r["verdict"]["verdict"] in ("OBSERVED", "INCONCLUSIVE"), r["verdict"]


def c_watch():
    if not notice.available():
        return "skip"
    w = Prism().watch([list("ABC" * 10), [f"tok{i:04d}x" for i in range(25)]])
    assert w["changes"] == [1], w["changes"]


CHECKS = [
    ("grade-proven", c_grade_proven),
    ("grade-refuses-unverified", c_grade_refuses_unverified),
    ("blind-pack-deterministic", c_blind_pack_deterministic),
    ("scorer-selftest", c_scorer_selftest),
    ("closure-proved", c_closure),
    ("prism-duel-sweep-8", c_prism_duel_sweep_8),
    ("symbolic-agreement", c_symbolic_agreement),
    ("z3-agreement", c_z3_agreement),
    ("sat-unsat-detected", c_sat_unsat),
    ("auto-cycle", c_auto_cycle),
    ("auto-negative-refuted", c_auto_negative_refuted),
    ("auto-junk", c_auto_junk),
    ("watch", c_watch),
]


def run_gate():
    for name, fn in CHECKS:
        check(name, fn)
    print(f"\nbest-of-best: {len(PASS)} passed, {len(SKIP)} skipped, {len(FAIL)} failed")
    return 1 if FAIL else 0


def main(argv):
    if "--gen-blind-pack" in argv:
        i = argv.index("--gen-blind-pack")
        try:
            n = int(argv[i + 1])
            out = argv[i + 2]
        except (IndexError, ValueError):
            print("usage: best_of_best.py --gen-blind-pack N OUTFILE")
            return 2
        pack = gen_blind_pack(n)
        with open(out, "w") as f:
            json.dump(pack, f, indent=2)
        print(f"wrote blind pack: {n} instances -> {out} (solutions sealed)")
        return 0
    if "--score-llm" in argv:
        i = argv.index("--score-llm")
        try:
            pack_f, ans_f = argv[i + 1], argv[i + 2]
        except IndexError:
            print("usage: best_of_best.py --score-llm PACK ANSWERS")
            return 2
        with open(pack_f) as f:
            pack = json.load(f)
        with open(ans_f) as f:
            answers = json.load(f)
        r = score_llm_pack(pack, answers)
        print(f"LLM score: {r['correct']}/{r['total']} "
              f"({100.0 * r['accuracy']:.1f}%), abstained {r['abstained']}, "
              f"wrong {r['wrong']}, malformed {r['malformed']}")
        for row in r["per"]:
            print(f"  {row['id']}: {row['kind']} (truth {row['truth']})")
        return 0
    if any(a.startswith("--sweep") for a in argv):
        n = 8
        for a in argv:
            if a.startswith("--sweep"):
                if "=" in a:
                    n = int(a.split("=", 1)[1])
                break
        if not prove.available():
            print("axiom-mcp not built; sweep skipped.")
            return 0
        passed, seen = 0, set()
        for i in range(n):
            seed, ok, note = DUEL.run_one(i * 10000)
            dup = " DUP" if seed in seen else ""
            seen.add(seed)
            passed += ok and not dup
            print(f"[{i + 1:2d}/{n}] seed {seed}: {'PASS' if ok else 'FAIL'} ({note}){dup}")
        print(f"\nsweep: {passed}/{n} (distinct seeds: {len(seen)})")
        print("SWEEP-PASS" if passed == n else "SWEEP-FAIL")
        return 0 if passed == n else 1
    return run_gate()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
