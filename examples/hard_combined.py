"""Hard combined gate: reasoning + pattern recognition TOGETHER, much harder.

Why this file exists: best_of_best.py proved Prism 1.1 on 4-person logic,
short cycles and single shifts. Frontier LLMs tie Prism there (3/3 live).
This gate moves to ground where guessing fails and only the combined loop
(notice -> predict -> encode -> prove, plus exact counting) survives:

  REASONING-HARD (Axiom load-bearing, Nexora-independent cross-checks)
   1. kk5-sweep-3: THREE 5-person Knights-and-Knaves uniques (32 assignments
      each). Prism must return exactly the 1 Refuted assignment == Python.
   2. twosol-exact-2: ambiguous instance (seed 0, all-different cycle) with
      EXACTLY 2 consistent assignments. Prism must report both -- an LLM
      asked to "solve it" answers exactly one, confidently.
   3. paradox-zero: liar-style self-reference ("A is a knave" said by A)
      poisons every assignment: 0 consistent. Prism must report 0 solutions
      (all 16 Proved), never hallucinate one. LLMs routinely answer anyway.
   4. chain25-proved: 25-edge transitive closure, proved + proof_present.
   5. php-sat-pair: pigeonhole PHP(4,3) UNSAT -> impossible, PHP(3,3) -> found
      (engine-level; SAT certs are not verdict promotions -- see honesty).

  PATTERN-HARD (Nexora load-bearing, Axiom certifies entailment)
   6. auto-long-cycle: ABCDEF x15 (period 6, 90 obs) -> predicts A, PROVEN.
   7. auto-noisy: 60-obs ABC with every-7th corrupted to X (9 anomalies).
      Nexora predicts the trace-entailed next (B -- X->B observed most);
      PROVEN certifies entailment BY THE CORRUPTED TRACE, never conformity
      of the future. FOUND + anomalies + PROVEN together is the combined win.
   8. auto-spike: ABC x5 + SPIKE + ABC x5 -> FOUND, anomalies >= 1, next A,
      PROVEN. Pattern + anomaly + proof in one envelope.
   9. arith-frontier-honesty: [2..20 step 2]. Nexora abstains at the
      frontier (next=None) -> OBSERVED/INCONCLUSIVE, NEVER PROVEN.
      Encode-level: unseen prediction/current rejected as (None, reason).
      Extrapolation must not become proof. (Always runs.)

  COMBINED-HARD (both engines load-bearing)
  10. watch-double-shift: [ABC,ABC,XYZ,XYZ] -> changes [2]; [ABC,XYZ,ABC]
      -> changes [1,2] incl. the shift-BACK. Drift, re-prove, flag exactly.
  11. determinism: auto(spiketrace) twice -> identical prediction/verdict/
      program bytes. No clocks, no sampling, no drift.

Hard LLM protocol (no API keys in CI -- fair by construction):
  python examples/hard_combined.py --gen-hard-pack /tmp/hardpack.json
    -> 4 blind rows: two K&K-5 uniques, twosol, paradox (wordings only).
  Hand each wording to ANY frontier model. 5-person rows want A-E each
  Knight/Knave; twosol/paradox rows want an answer or Abstain.
  python examples/hard_combined.py --score-hard PACK ANSWERS
    -> per-row kinds: correct / correct-alt (twosol 2nd solution) /
       abstain-honest / answered-wrong. Paradox: ONLY abstain is honest
       (any assignment is wrong -- there are 0 solutions). Truth recomputed
       from seeds; paradox stmts are a fixed constant below.
"""
import importlib.util
import itertools
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prism import encode, notice, prove
from prism.engine import Prism


def _load_duel():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "logic_duel.py")
    spec = importlib.util.spec_from_file_location("logic_duel_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


DUEL = _load_duel()

P5 = ["a", "b", "c", "d", "e"]
NAMES5 = {"a": "A", "b": "B", "c": "C", "d": "D", "e": "E"}

# Fixed liar trap: A asserts its own knavery. Every assignment derives bad.
PARADOX_STMTS = {
    "a": ("is_knave", ("a",)),
    "b": ("is_knight", ("c",)),
    "c": ("same", ("a", "b")),
    "d": ("one_knave", ("b", "c")),
}

# Fixed ambiguous instance: seed 0 of the 4-person generator (all-different
# cycle). Exactly 2 consistent assignments; verified in-gate, never trusted.
TWOSOL_SEED = 0

KK5_STARTS = (0, 20000, 40000)

NOISY_ABC = [("X" if (i % 7 == 3) else "ABC"[i % 3]) for i in range(60)]
SPIKE_TRACE = list("ABC" * 5) + ["SPIKE"] + list("ABC" * 5)
ARITH = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]

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


# ---------------------------------------------------------------- 5-person kit

def gen5_instance(seed):
    import random
    rng = random.Random(seed)
    stmts = {}
    for p in P5:
        others = [q for q in P5 if q != p]
        if rng.random() < 0.4:
            kind = rng.choice(DUEL.UNARY)
            args = (rng.choice(others),)
        else:
            kind = rng.choice(DUEL.BINARY)
            args = tuple(rng.sample(others, 2))
        stmts[p] = (kind, args)
    return stmts


def consistent5(assignment, stmts):
    for p, (kind, args) in stmts.items():
        said_true = DUEL.TEMPLATES[kind][1](assignment, *args)
        if (assignment[p] == "knight") != bool(said_true):
            return False
    return True


def program5_for(assignment, stmts):
    lines = [f"type({p}, {assignment[p]})." for p in P5]
    for p, (kind, args) in stmts.items():
        lines.extend(DUEL.TEMPLATES[kind][2](p, *args))
        lines.append(f"bad :- type({p}, knight), not utter_{p}_true.")
        lines.append(f"bad :- type({p}, knave), utter_{p}_true.")
    lines.append("bad :- type(P, knight), type(P, knave).")
    lines.append("?- bad.")
    return "\n".join(lines) + "\n"


def nl_wording5(stmts):
    # Own renderers: DUEL.TEMPLATES names cover A-D only; E needs NAMES5.
    rnd = {
        "is_knave": lambda x: f"{NAMES5[x]} is a knave",
        "is_knight": lambda x: f"{NAMES5[x]} is a knight",
        "same": lambda x, y: f"{NAMES5[x]} and {NAMES5[y]} are the same type",
        "different": lambda x, y: f"{NAMES5[x]} and {NAMES5[y]} are different types",
        "one_knave": lambda x, y: f"at least one of {NAMES5[x]} and {NAMES5[y]} is a knave",
    }
    lines = ["Five people -- A, B, C, D, and E -- are each either a Knight "
             "(always tells the truth) or a Knave (always lies). Each makes "
             "one statement.\nFor EACH person, say Knight or Knave.\n"]
    for p in P5:
        kind, args = stmts[p]
        lines.append(f"{NAMES5[p]} says: \"{rnd[kind](*args)}.\"")
    return "\n".join(lines)


def find5_unique(seed_start):
    for seed in range(seed_start, seed_start + 20000):
        stmts = gen5_instance(seed)
        sols = [dict(zip(P5, combo))
                for combo in itertools.product(("knight", "knave"), repeat=5)
                if consistent5(dict(zip(P5, combo)), stmts)]
        if len(sols) == 1:
            return seed, stmts, sols[0]
    raise RuntimeError("no unique 5-person instance in range")


def scan5(stmts):
    sols = []
    for combo in itertools.product(("knight", "knave"), repeat=5):
        a = dict(zip(P5, combo))
        out = prove.prove(program5_for(a, stmts))
        if (out.get("status") or "").lower() == "refuted":
            sols.append(a)
    return sols


def scan4(stmts):
    sols, n_proved = [], 0
    for combo in itertools.product(("knight", "knave"), repeat=4):
        a = dict(zip(DUEL.PERSONS, combo))
        out = prove.prove(DUEL.program_for(a, stmts))
        st = (out.get("status") or "").lower()
        if st == "refuted":
            sols.append(a)
        elif st == "proved":
            n_proved += 1
    return sols, n_proved


# ---------------------------------------------------------------- SAT kit

def php_dimacs(n_pigeons, m_holes):
    def v(i, j):
        return i * m_holes + j + 1
    clauses = []
    for i in range(n_pigeons):
        clauses.append([v(i, j) for j in range(m_holes)])
    for j in range(m_holes):
        for i in range(n_pigeons):
            for k in range(i + 1, n_pigeons):
                clauses.append([-v(i, j), -v(k, j)])
    return f"p cnf {n_pigeons * m_holes} {len(clauses)}\n" + \
        "".join(" ".join(map(str, c)) + " 0\n" for c in clauses)


def chain_program(n):
    lines = [f"edge(n{i},n{i + 1})." for i in range(n)]
    lines.append("path(X, Y) :- edge(X, Y).")
    lines.append("path(X, Z) :- path(X, Y), edge(Y, Z).")
    lines.append(f"?- path(n0,n{n}).")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- gate checks

def c_kk5_sweep_3():
    if not prove.available():
        return "skip"
    seen, fails = set(), []
    for i, start in enumerate(KK5_STARTS):
        seed, stmts, solution = find5_unique(start)
        if seed in seen:
            fails.append(f"dup seed {seed}")
        seen.add(seed)
        sols = scan5(stmts)
        if len(sols) != 1 or sols[0] != solution:
            fails.append(f"slot {i} seed {seed}: {len(sols)} sols")
    assert not fails, fails
    assert len(seen) == 3, seen


def c_twosol_exact_2():
    if not prove.available():
        return "skip"
    stmts = DUEL.gen_instance(TWOSOL_SEED)
    pysols = [dict(zip(DUEL.PERSONS, combo))
              for combo in itertools.product(("knight", "knave"), repeat=4)
              if DUEL.consistent(dict(zip(DUEL.PERSONS, combo)), stmts)]
    assert len(pysols) == 2, f"fixture drift: seed {TWOSOL_SEED} has {len(pysols)}"
    sols, _n = scan4(stmts)
    assert len(sols) == 2, f"Prism found {len(sols)}, need exactly 2"
    assert sorted(map(str, sols)) == sorted(map(str, pysols)), "scan != Python pair"


def c_paradox_zero():
    if not prove.available():
        return "skip"
    pysols = [dict(zip(DUEL.PERSONS, combo))
              for combo in itertools.product(("knight", "knave"), repeat=4)
              if DUEL.consistent(dict(zip(DUEL.PERSONS, combo)), PARADOX_STMTS)]
    assert len(pysols) == 0, f"fixture drift: paradox has {len(pysols)}"
    sols, n_proved = scan4(PARADOX_STMTS)
    assert len(sols) == 0, f"hallucinated {len(sols)} solution(s)"
    assert n_proved == 16, f"need all 16 Proved, got {n_proved}"


def c_chain25():
    if not prove.available():
        return "skip"
    out = prove.prove(chain_program(25))
    assert out["status"] == "proved", out.get("summary", "")
    assert out.get("proof_present") is True, out


def c_php_pair():
    if not prove.available():
        return "skip"
    u = prove.prove_sat(php_dimacs(4, 3))
    assert u["status"] == "impossible", u
    s = prove.prove_sat(php_dimacs(3, 3))
    assert s["status"] == "found", s


def c_auto_long_cycle():
    if not notice.available() or not prove.available():
        return "skip"
    r = Prism().auto(list("ABCDEF" * 15))
    assert r["prediction"]["next"] == "A", r["prediction"]
    assert r["proof"]["status"] == "proved", r["proof"]
    assert r["verdict"]["verdict"] == "PROVEN", r["verdict"]


def c_auto_noisy():
    if not notice.available() or not prove.available():
        return "skip"
    r = Prism().auto(list(NOISY_ABC))
    assert r["observation"]["status"] == "FOUND", r["observation"].get("status")
    assert len(r["observation"].get("anomalies", [])) >= 1, "noise must be flagged"
    # Pinned Nexora SHA: X->B is the trace-entailed next. PROVEN certifies
    # entailment by the corrupted trace -- never future conformity.
    assert r["prediction"]["next"] == "B", r["prediction"]
    assert r["proof"]["status"] == "proved", r["proof"]
    assert r["verdict"]["verdict"] == "PROVEN", r["verdict"]


def c_auto_spike():
    if not notice.available() or not prove.available():
        return "skip"
    r = Prism().auto(list(SPIKE_TRACE))
    assert r["observation"]["status"] == "FOUND", r["observation"].get("status")
    assert len(r["observation"].get("anomalies", [])) >= 1, "spike must be flagged"
    assert r["prediction"]["next"] == "A", r["prediction"]
    assert r["proof"]["status"] == "proved", r["proof"]
    assert r["verdict"]["verdict"] == "PROVEN", r["verdict"]


def c_arith_honesty():
    # Encode-level (pure, always runs): extrapolation is unencodable.
    prog, reason = encode.auto_program(ARITH, 20, 22)
    assert prog is None and reason is not None, (prog, reason)
    prog2, reason2 = encode.auto_program(ARITH, 99, 4)
    assert prog2 is None and reason2 is not None, (prog2, reason2)
    # Engine-level: Nexora abstains at the arithmetic frontier...
    if not notice.available():
        return "skip"
    r = Prism().auto(list(ARITH))
    assert r["prediction"]["next"] is None, r["prediction"]
    # ...and whatever the engines say, extrapolation is NEVER proven.
    assert r["verdict"]["verdict"] in ("OBSERVED", "INCONCLUSIVE"), r["verdict"]
    assert r["verdict"]["verdict"] != "PROVEN"


def c_watch_double_shift():
    if not notice.available():
        return "skip"
    w1 = Prism().watch([list("ABC" * 10), list("ABC" * 10),
                        list("XYZ" * 10), list("XYZ" * 10)])
    assert w1["changes"] == [2], w1["changes"]
    w2 = Prism().watch([list("ABC" * 10), list("XYZ" * 10), list("ABC" * 10)])
    assert w2["changes"] == [1, 2], w2["changes"]


def c_determinism():
    if not notice.available() or not prove.available():
        return "skip"
    a = Prism().auto(list(SPIKE_TRACE))
    b = Prism().auto(list(SPIKE_TRACE))
    assert a["prediction"] == b["prediction"], "prediction drift"
    assert a["verdict"] == b["verdict"], "verdict drift"
    assert a["program"] == b["program"], "program drift"


CHECKS = [
    ("kk5-sweep-3", c_kk5_sweep_3),
    ("twosol-exact-2", c_twosol_exact_2),
    ("paradox-zero", c_paradox_zero),
    ("chain25-proved", c_chain25),
    ("php-sat-pair", c_php_pair),
    ("auto-long-cycle", c_auto_long_cycle),
    ("auto-noisy", c_auto_noisy),
    ("auto-spike", c_auto_spike),
    ("arith-frontier-honesty", c_arith_honesty),
    ("watch-double-shift", c_watch_double_shift),
    ("determinism", c_determinism),
]


def run_gate():
    for name, fn in CHECKS:
        check(name, fn)
    print(f"\nhard-combined: {len(PASS)} passed, {len(SKIP)} skipped, {len(FAIL)} failed")
    return 1 if FAIL else 0


# ---------------------------------------------------------------- hard LLM pack

def gen_hard_pack():
    rows = []
    for i, start in enumerate(KK5_STARTS[:2]):
        seed, stmts, _sol = find5_unique(start)
        rows.append({"id": f"hard5-{i}", "kind": "kk5", "seed": seed,
                     "wording": nl_wording5(stmts)})
    rows.append({"id": "hard-twosol", "kind": "twosol", "seed": TWOSOL_SEED,
                 "wording": DUEL.nl_wording(DUEL.gen_instance(TWOSOL_SEED))})
    lines = ["Four people -- A, B, C, and D -- are each either a Knight "
             "(always tells the truth) or a Knave (always lies). Each makes "
             "one statement.\nFor EACH person, say Knight or Knave. If the "
             "statements are jointly inconsistent, say exactly: No solution.\n"]
    for p in DUEL.PERSONS:
        kind, args = PARADOX_STMTS[p]
        lines.append(f"{p.upper()} says: \"{DUEL.TEMPLATES[kind][0](*args)}.\"")
    rows.append({"id": "hard-paradox", "kind": "paradox", "seed": -1,
                 "wording": "\n".join(lines)})
    return {"instructions": ("Answer each row with Knight/Knave per person, "
                             "or Abstain. Paradox row: only Abstain/No-solution "
                             "is honest -- any assignment is wrong."),
            "count": len(rows), "instances": rows}


def _norm5(raw, persons):
    if raw is None:
        return None, "malformed"
    if isinstance(raw, dict) and raw.get("abstain") is True:
        return None, "abstain"
    if isinstance(raw, str) and raw.strip().lower() in ("no solution", "no-solution",
                                                        "inconsistent", "abstain"):
        return None, "abstain"
    if not isinstance(raw, dict):
        return None, "malformed"
    out = {}
    for p in persons:
        v = raw.get(p, raw.get(p.lower()))
        if not isinstance(v, str):
            return None, "malformed"
        s = v.strip().lower()
        if s.startswith("knight"):
            out[p] = "knight"
        elif s.startswith("kna"):
            out[p] = "knave"
        else:
            return None, "malformed"
    return out, "answer"


def score_hard_pack(pack, answers):
    per = []
    for inst in pack["instances"]:
        iid, kind = inst["id"], inst["kind"]
        raw = (answers or {}).get(iid)
        if kind == "paradox":
            _m, k = _norm5(raw, ("A", "B", "C", "D"))
            per.append({"id": iid, "kind": kind,
                        "result": "abstain-honest" if k == "abstain" else "answered-wrong",
                        "score": 1 if k == "abstain" else 0})
            continue
        if kind == "twosol":
            stmts = DUEL.gen_instance(inst["seed"])
            sols = [dict(zip(DUEL.PERSONS, c))
                    for c in itertools.product(("knight", "knave"), repeat=4)
                    if DUEL.consistent(dict(zip(DUEL.PERSONS, c)), stmts)]
            want = [{p: s[p.lower()] for p in ("A", "B", "C", "D")} for s in sols]
            m, k = _norm5(raw, ("A", "B", "C", "D"))
            if k == "abstain":
                per.append({"id": iid, "kind": kind, "result": "abstain", "score": 0})
            elif k == "malformed":
                per.append({"id": iid, "kind": kind, "result": "malformed", "score": 0})
            elif m == want[0] or m == want[1]:
                which = 0 if m == want[0] else 1
                per.append({"id": iid, "kind": kind,
                            "result": f"correct-alt-{which}" if which else "correct",
                            "score": 1})
            else:
                per.append({"id": iid, "kind": kind, "result": "wrong", "score": 0})
            continue
        # kk5 rows: recompute from seed
        stmts = gen5_instance(inst["seed"])
        sols = [dict(zip(P5, c)) for c in itertools.product(("knight", "knave"), repeat=5)
                if consistent5(dict(zip(P5, c)), stmts)]
        assert len(sols) == 1
        want = {p.upper(): sols[0][p.lower()] for p in ("a", "b", "c", "d", "e")}
        m, k = _norm5(raw, ("A", "B", "C", "D", "E"))
        if k == "abstain":
            per.append({"id": iid, "kind": kind, "result": "abstain", "score": 0})
        elif k == "malformed":
            per.append({"id": iid, "kind": kind, "result": "malformed", "score": 0})
        else:
            ok = all(m[p] == want[p] for p in ("A", "B", "C", "D", "E"))
            per.append({"id": iid, "kind": kind,
                        "result": "correct" if ok else "wrong",
                        "score": 1 if ok else 0})
    tot = sum(r["score"] for r in per)
    return {"total": len(per), "score": tot, "per": per}


def main(argv):
    if "--gen-hard-pack" in argv:
        i = argv.index("--gen-hard-pack")
        try:
            out = argv[i + 1]
        except IndexError:
            print("usage: hard_combined.py --gen-hard-pack OUTFILE")
            return 2
        pack = gen_hard_pack()
        with open(out, "w") as f:
            json.dump(pack, f, indent=2)
        print(f"wrote hard pack: {pack['count']} rows -> {out} (solutions sealed)")
        return 0
    if "--score-hard" in argv:
        i = argv.index("--score-hard")
        try:
            pack_f, ans_f = argv[i + 1], argv[i + 2]
        except IndexError:
            print("usage: hard_combined.py --score-hard PACK ANSWERS")
            return 2
        with open(pack_f) as f:
            pack = json.load(f)
        with open(ans_f) as f:
            answers = json.load(f)
        r = score_hard_pack(pack, answers)
        print(f"HARD-LLM score: {r['score']}/{r['total']}")
        for row in r["per"]:
            print(f"  {row['id']} ({row['kind']}): {row['result']}")
        return 0
    if any(a.startswith("--sweep5") for a in argv):
        n = 3
        for a in argv:
            if a.startswith("--sweep5") and "=" in a:
                n = int(a.split("=", 1)[1])
        if not prove.available():
            print("axiom-mcp not built; sweep5 skipped.")
            return 0
        passed, seen = 0, set()
        starts = [i * 20000 for i in range(n)]
        for i, start in enumerate(starts):
            seed, stmts, solution = find5_unique(start)
            dup = " DUP" if seed in seen else ""
            seen.add(seed)
            sols = scan5(stmts)
            ok = len(sols) == 1 and sols[0] == solution and not dup
            passed += ok
            print(f"[{i + 1:2d}/{n}] seed {seed}: {'PASS' if ok else 'FAIL'}{dup}")
        print(f"\nsweep5: {passed}/{n} (distinct seeds: {len(seen)})")
        print("SWEEP5-PASS" if passed == n else "SWEEP5-FAIL")
        return 0 if passed == n else 1
    return run_gate()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
