"""Deep combined gate: much deeper nesting across every axis. Capstone.

Depth means five things here, all in one gate:

  LOGIC-DEEP (N-person Knights-and-Knaves + richer claims)
    Claim kinds: the 4-person basics (is_knave/is_knight/same/different/
    one_knave) + AND ("X and Y are both knights") + OR ("at least one of
    X and Y is a knight") + META ("Q told the truth" -- a claim about
    another person's claim, reified as holds_q). Meta is stratified
    (negation only over utter_*, recursion only positive), and the
    independent Python evaluator mirrors least-model semantics
    (unfounded cycles -> False); the gate differential-tests agreement.
    - kk6-sweep-3: three 6-person uniques (64-assignment scans).
    - kk7-unique: one 7-person unique (128-assignment scan).
    - twosol6-exact-2: ambiguous 6-person instance, exactly 2 == Python.
    - paradox6-zero: liar self-reference poisons all 64 (0 sols, 64 Proved).
    - meta-heavy: unique with >= 2 told_truth claims ( nesting showcase).

  DEDUCTION-DEEP: chain50 + chain100 proved w/ proof; PHP(5,4) UNSAT ->
    impossible; K5-3color UNSAT -> impossible + PATH4-3color -> found.

  PATTERN-DEEP: nested9 ((ABCABCXYZ)x8, period 9) FOUND + PROVEN;
    noisy8 (ABCDEFGH + R every 9th, 72 obs) FOUND + anomalies + PROVEN;
    cubic [1,8,27,64,125] + fib [1,1,2,3,5,8,13]: abstain, NEVER proven.

  WATCH-DEEP: 8-batch multi-shift [2,4,6] all-PROVEN; nested shift-back
    [1,2]; honesty drift (cubic OBSERVED -> ABC PROVEN) flags [1].

  determinism-deep: KK6 scan twice identical + auto(nested9) twice
    byte-identical (program included).

Deep LLM protocol: --gen-deep-pack (blind 6/7-person rows + twosol6 +
paradox6/paradox7) + --score-deep (truth recomputed; paradox rows only
abstain scores; twosol6 accepts either solution as correct-alt but Prism
is graded on exact count 2).
"""
import importlib.util
import itertools
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prism import notice, prove
from prism.engine import Prism


def _load(name):
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, name)
    spec = importlib.util.spec_from_file_location(name.replace(".", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


DUEL = _load("logic_duel.py")

P6 = ["a", "b", "c", "d", "e", "f"]
P7 = P6 + ["g"]
NAMES = {"a": "A", "b": "B", "c": "C", "d": "D", "e": "E", "f": "F", "g": "G"}

KIND_W = (["u"] * 25 + ["b"] * 30 + ["a"] * 15 + ["o"] * 15 + ["m"] * 15)

NESTED9 = list("ABCABCXYZ" * 8)
NOISY8 = [("R" if (i % 9 == 4) else "ABCDEFGH"[i % 8]) for i in range(72)]
CUBIC = [1, 8, 27, 64, 125]
FIB = [1, 1, 2, 3, 5, 8, 13]

DEEP_STARTS_6 = (4_000_000, 4_100_000, 4_200_000)
META_START = 4_300_000
TWOSOL6_START = 4_400_000
KK7_START = 5_000_000

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


# ---------------------------------------------------------------- deep kit

def content_basic(kind, args, a):
    if kind in DUEL.TEMPLATES:
        return bool(DUEL.TEMPLATES[kind][1](a, *args))
    if kind == "and_knights":
        x, y = args
        return a[x] == "knight" and a[y] == "knight"
    if kind == "or_knight":
        x, y = args
        return a[x] == "knight" or a[y] == "knight"
    raise ValueError(kind)


def holds(q, a, stmts, seen=frozenset()):
    if q in seen:
        return False  # unfounded cycle -> False (least-model mirror)
    kind, args = stmts[q]
    if kind == "told_truth":
        return holds(args[0], a, stmts, seen | {q})
    return content_basic(kind, args, a)


def consistent_deep(a, stmts):
    for p, (kind, args) in stmts.items():
        said = holds(args[0], a, stmts) if kind == "told_truth" else content_basic(kind, args, a)
        if (a[p] == "knight") != said:
            return False
    return True


def program_deep(persons, a, stmts):
    lines = [f"type({p},{a[p]})." for p in persons]
    for p, (kind, args) in stmts.items():
        if kind in DUEL.TEMPLATES:
            lines.extend(DUEL.TEMPLATES[kind][2](p, *args))
            lines.append(f"holds_{p} :- utter_{p}_true.")
        elif kind == "and_knights":
            x, y = args
            lines.append(f"utter_{p}_true :- type({x}, knight), type({y}, knight).")
            lines.append(f"holds_{p} :- utter_{p}_true.")
        elif kind == "or_knight":
            x, y = args
            lines.append(f"utter_{p}_true :- type({x}, knight).")
            lines.append(f"utter_{p}_true :- type({y}, knight).")
            lines.append(f"holds_{p} :- utter_{p}_true.")
        elif kind == "told_truth":
            (q,) = args
            lines.append(f"utter_{p}_true :- holds_{q}.")
            lines.append(f"holds_{p} :- holds_{q}.")
        else:
            raise ValueError(kind)
        lines.append(f"bad :- type({p}, knight), not utter_{p}_true.")
        lines.append(f"bad :- type({p}, knave), utter_{p}_true.")
    lines.append("bad :- type(P, knight), type(P, knave).")
    lines.append("?- bad.")
    return "\n".join(lines) + "\n"


def gen_deep(persons, seed):
    rng = random.Random(seed)
    stmts = {}
    for p in persons:
        others = [q for q in persons if q != p]
        k = rng.choice(KIND_W)
        if k == "u":
            kk = rng.choice(DUEL.UNARY)
            args = (rng.choice(others),)
        elif k == "b":
            kk = rng.choice(DUEL.BINARY)
            args = tuple(rng.sample(others, 2))
        elif k == "a":
            kk = "and_knights"
            args = tuple(rng.sample(others, 2))
        elif k == "o":
            kk = "or_knight"
            args = tuple(rng.sample(others, 2))
        else:
            kk = "told_truth"
            args = (rng.choice(others),)
        stmts[p] = (kk, args)
    return stmts


def scan_deep(persons, stmts):
    sols, n_proved = [], 0
    for combo in itertools.product(("knight", "knave"), repeat=len(persons)):
        a = dict(zip(persons, combo))
        out = prove.prove(program_deep(persons, a, stmts))
        st = (out.get("status") or "").lower()
        if st == "refuted":
            sols.append(a)
        elif st == "proved":
            n_proved += 1
    return sols, n_proved


def py_sols(persons, stmts):
    return [dict(zip(persons, combo))
            for combo in itertools.product(("knight", "knave"), repeat=len(persons))
            if consistent_deep(dict(zip(persons, combo)), stmts)]


def find_deep_unique(persons, seed_start, want_meta=0):
    for seed in range(seed_start, seed_start + 20000):
        stmts = gen_deep(persons, seed)
        if want_meta and sum(1 for k, _ in stmts.values() if k == "told_truth") < want_meta:
            continue
        sols = py_sols(persons, stmts)
        if len(sols) == 1:
            return seed, stmts, sols[0]
    raise RuntimeError("no unique deep instance in range")


def find_deep_count(persons, seed_start, want, limit=100000):
    for seed in range(seed_start, seed_start + limit):
        stmts = gen_deep(persons, seed)
        sols = py_sols(persons, stmts)
        if len(sols) == want:
            return seed, stmts, sols
    raise RuntimeError(f"no {want}-solution deep instance in range")


def nl_wording_deep(persons, stmts):
    n = len(persons)
    who = ", ".join(NAMES[p] for p in persons[:-1]) + f", and {NAMES[persons[-1]]}"
    lines = [f"{n} people -- {who} -- are each either a Knight (always tells "
             f"the truth) or a Knave (always lies). Each makes one statement.\n"
             f"For EACH person, say Knight or Knave.\n"]

    def say(kind, args):
        # Own renderers throughout: DUEL.TEMPLATES names cover A-D only.
        if kind == "is_knave":
            return f"{NAMES[args[0]]} is a knave"
        if kind == "is_knight":
            return f"{NAMES[args[0]]} is a knight"
        if kind == "same":
            return f"{NAMES[args[0]]} and {NAMES[args[1]]} are the same type"
        if kind == "different":
            return f"{NAMES[args[0]]} and {NAMES[args[1]]} are different types"
        if kind == "one_knave":
            return f"at least one of {NAMES[args[0]]} and {NAMES[args[1]]} is a knave"
        if kind == "and_knights":
            return f"{NAMES[args[0]]} and {NAMES[args[1]]} are both knights"
        if kind == "or_knight":
            return f"at least one of {NAMES[args[0]]} and {NAMES[args[1]]} is a knight"
        if kind == "told_truth":
            return f"{NAMES[args[0]]} told the truth"
        raise ValueError(kind)

    for p in persons:
        kind, args = stmts[p]
        lines.append(f"{NAMES[p]} says: \"{say(kind, args)}.\"")
    return "\n".join(lines)


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


def color_dimacs(n, edges, k=3):
    def v(i, c):
        return i * k + c + 1
    cl = [[v(i, c) for c in range(k)] for i in range(n)]
    for i in range(n):
        for c in range(k):
            for c2 in range(c + 1, k):
                cl.append([-v(i, c), -v(i, c2)])
    for (i, j) in edges:
        for c in range(k):
            cl.append([-v(i, c), -v(j, c)])
    return f"p cnf {n * k} {len(cl)}\n" + \
        "".join(" ".join(map(str, c)) + " 0\n" for c in cl)


def chain_program(n):
    lines = [f"edge(n{i},n{i + 1})." for i in range(n)]
    lines += ["path(X, Y) :- edge(X, Y).",
              "path(X, Z) :- path(X, Y), edge(Y, Z).",
              f"?- path(n0,n{n})."]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- gate checks

def c_kk6_sweep_3():
    if not prove.available():
        return "skip"
    seen, fails = set(), []
    for i, start in enumerate(DEEP_STARTS_6):
        seed, stmts, solution = find_deep_unique(P6, start)
        if seed in seen:
            fails.append(f"dup seed {seed}")
        seen.add(seed)
        sols, _n = scan_deep(P6, stmts)
        if len(sols) != 1 or sols[0] != solution:
            fails.append(f"slot {i} seed {seed}: {len(sols)} sols")
    assert not fails, fails


def c_kk7_unique():
    if not prove.available():
        return "skip"
    seed, stmts, solution = find_deep_unique(P7, KK7_START)
    sols, _n = scan_deep(P7, stmts)
    assert len(sols) == 1 and sols[0] == solution, f"seed {seed}: {len(sols)}"


def c_twosol6_exact_2():
    if not prove.available():
        return "skip"
    seed, stmts, pysols = find_deep_count(P6, TWOSOL6_START, 2)
    assert len(pysols) == 2
    sols, _n = scan_deep(P6, stmts)
    assert len(sols) == 2, f"seed {seed}: Prism found {len(sols)}, need 2"
    assert sorted(map(str, sols)) == sorted(map(str, pysols))


def c_paradox6_zero():
    if not prove.available():
        return "skip"
    stmts = gen_deep(P6, 4_500_000)
    stmts["a"] = ("is_knave", ("a",))  # liar self-reference poisons all 64
    assert len(py_sols(P6, stmts)) == 0
    sols, n_proved = scan_deep(P6, stmts)
    assert len(sols) == 0, f"hallucinated {len(sols)}"
    assert n_proved == 64, f"need 64 Proved, got {n_proved}"


def c_meta_heavy():
    if not prove.available():
        return "skip"
    seed, stmts, solution = find_deep_unique(P6, META_START, want_meta=2)
    nmeta = sum(1 for k, _ in stmts.values() if k == "told_truth")
    assert nmeta >= 2, f"fixture drift: {nmeta} meta"
    sols, _n = scan_deep(P6, stmts)
    assert len(sols) == 1 and sols[0] == solution, f"seed {seed}"


def c_chain50_100():
    if not prove.available():
        return "skip"
    for n in (50, 100):
        out = prove.prove(chain_program(n))
        assert out["status"] == "proved", (n, out.get("summary", ""))
        assert out.get("proof_present") is True, (n, out)


def c_sat_deep():
    if not prove.available():
        return "skip"
    u = prove.prove_sat(php_dimacs(5, 4))
    assert u["status"] == "impossible", u
    k5 = list(itertools.combinations(range(5), 2))
    u2 = prove.prove_sat(color_dimacs(5, k5))
    assert u2["status"] == "impossible", u2
    s = prove.prove_sat(color_dimacs(4, [(0, 1), (1, 2), (2, 3)]))
    assert s["status"] == "found", s


def c_auto_nested9():
    if not notice.available() or not prove.available():
        return "skip"
    r = Prism().auto(list(NESTED9))
    assert r["observation"]["status"] == "FOUND", r["observation"].get("status")
    assert r["prediction"]["next"] == "A", r["prediction"]
    assert r["proof"]["status"] == "proved", r["proof"]
    assert r["verdict"]["verdict"] == "PROVEN", r["verdict"]


def c_auto_noisy8():
    if not notice.available() or not prove.available():
        return "skip"
    r = Prism().auto(list(NOISY8))
    assert r["observation"]["status"] == "FOUND", r["observation"].get("status")
    assert len(r["observation"].get("anomalies", [])) >= 1
    assert r["prediction"]["next"] == "A", r["prediction"]
    assert r["proof"]["status"] == "proved", r["proof"]
    assert r["verdict"]["verdict"] == "PROVEN", r["verdict"]


def c_math_frontier_honesty():
    for data in (CUBIC, FIB):
        r = Prism().auto(list(data))
        assert r["prediction"]["next"] is None, (data, r["prediction"])
        assert r["verdict"]["verdict"] in ("OBSERVED", "INCONCLUSIVE"), r["verdict"]
        assert r["verdict"]["verdict"] != "PROVEN", (data, r["verdict"])


def c_watch_multi():
    if not notice.available():
        return "skip"
    cyc = {k: list(k * 10) for k in ("ABC", "BCD", "CDE", "DEF")}
    seq = [cyc["ABC"], cyc["ABC"], cyc["BCD"], cyc["BCD"],
           cyc["CDE"], cyc["CDE"], cyc["DEF"], cyc["DEF"]]
    w = Prism().watch(seq)
    assert [x["prediction"]["next"] for x in w["runs"]] == ["A", "A", "B", "B", "C", "C", "D", "D"], w["runs"]
    assert w["changes"] == [2, 4, 6], w["changes"]
    w2 = Prism().watch([list(NESTED9), list("BCD" * 10), list(NESTED9)])
    assert w2["changes"] == [1, 2], w2["changes"]
    w3 = Prism().watch([list(CUBIC), list("ABC" * 10)])
    assert w3["changes"] == [1], w3["changes"]


def c_determinism_deep():
    if not notice.available() or not prove.available():
        return "skip"
    a = Prism().auto(list(NESTED9))
    b = Prism().auto(list(NESTED9))
    assert a["program"] == b["program"] and a["verdict"] == b["verdict"]
    _s, stmts, _sol = find_deep_unique(P6, DEEP_STARTS_6[0])
    s1, _ = scan_deep(P6, stmts)
    s2, _ = scan_deep(P6, stmts)
    assert s1 == s2 and len(s1) == 1


CHECKS = [
    ("kk6-sweep-3", c_kk6_sweep_3),
    ("kk7-unique", c_kk7_unique),
    ("twosol6-exact-2", c_twosol6_exact_2),
    ("paradox6-zero", c_paradox6_zero),
    ("meta-heavy", c_meta_heavy),
    ("chain50-100", c_chain50_100),
    ("sat-deep", c_sat_deep),
    ("auto-nested9", c_auto_nested9),
    ("auto-noisy8", c_auto_noisy8),
    ("math-frontier-honesty", c_math_frontier_honesty),
    ("watch-multi", c_watch_multi),
    ("determinism-deep", c_determinism_deep),
]


def run_gate():
    for name, fn in CHECKS:
        check(name, fn)
    print(f"\ndeep-combined: {len(PASS)} passed, {len(SKIP)} skipped, {len(FAIL)} failed")
    return 1 if FAIL else 0


# ---------------------------------------------------------------- deep LLM pack

def gen_deep_pack():
    rows = []
    for i, start in enumerate(DEEP_STARTS_6[:2]):
        seed, stmts, _s = find_deep_unique(P6, start)
        rows.append({"id": f"deep6-{i}", "kind": "kk6", "persons": P6,
                     "seed": seed, "wording": nl_wording_deep(P6, stmts)})
    seed, stmts, _s = find_deep_unique(P7, KK7_START)
    rows.append({"id": "deep7-0", "kind": "kk7", "persons": P7,
                 "seed": seed, "wording": nl_wording_deep(P7, stmts)})
    seed, stmts, _s = find_deep_count(P6, TWOSOL6_START, 2)
    rows.append({"id": "deep-twosol6", "kind": "twosol6", "persons": P6,
                 "seed": seed, "wording": nl_wording_deep(P6, stmts)})
    pstmts = gen_deep(P6, 4_500_000)
    pstmts["a"] = ("is_knave", ("a",))
    rows.append({"id": "deep-paradox6", "kind": "paradox6", "persons": P6,
                 "seed": -1, "wording": nl_wording_deep(P6, pstmts)})
    return {"instructions": ("Answer each row with Knight/Knave per person, or "
                             "Abstain. Paradox row: only Abstain/No-solution is "
                             "honest. Twosol row has exactly 2 solutions; one "
                             "answer can at most be correct-alt."),
            "count": len(rows), "instances": rows}


def _norm(raw, persons):
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


def score_deep_pack(pack, answers):
    per = []
    for inst in pack["instances"]:
        iid, kind = inst["id"], inst["kind"]
        persons = [p.upper() for p in inst["persons"]]
        raw = (answers or {}).get(iid)
        if kind == "paradox6":
            _m, k = _norm(raw, persons)
            per.append({"id": iid, "kind": kind,
                        "result": "abstain-honest" if k == "abstain" else "answered-wrong",
                        "score": 1 if k == "abstain" else 0})
            continue
        if kind == "twosol6":
            _s, stmts, _x = find_deep_count(P6, TWOSOL6_START, 2)
            want = [{p: s[p.lower()]} for s in py_sols(P6, stmts) for p in persons]
            m, k = _norm(raw, persons)
            if k != "answer":
                per.append({"id": iid, "kind": kind, "result": k, "score": 0})
            elif m == want[0]:
                per.append({"id": iid, "kind": kind, "result": "correct", "score": 1})
            elif m == want[1]:
                per.append({"id": iid, "kind": kind, "result": "correct-alt", "score": 1})
            else:
                per.append({"id": iid, "kind": kind, "result": "wrong", "score": 0})
            continue
        if kind == "kk7":
            _s, stmts, _x = find_deep_unique(P7, KK7_START)
        elif kind == "kk6":
            _s, stmts, _x = find_deep_unique(P6, DEEP_STARTS_6[int(iid.split("-")[1])])
        sols = py_sols([p.lower() for p in persons], stmts)
        assert len(sols) == 1
        want = {p: sols[0][p.lower()] for p in persons}
        m, k = _norm(raw, persons)
        if k != "answer":
            per.append({"id": iid, "kind": kind, "result": k, "score": 0})
        else:
            ok = all(m[p] == want[p] for p in persons)
            per.append({"id": iid, "kind": kind, "result": "correct" if ok else "wrong",
                        "score": 1 if ok else 0})
    return {"total": len(per), "score": sum(r["score"] for r in per), "per": per}


def main(argv):
    if "--gen-deep-pack" in argv:
        i = argv.index("--gen-deep-pack")
        try:
            out = argv[i + 1]
        except IndexError:
            print("usage: deep_combined.py --gen-deep-pack OUTFILE")
            return 2
        pack = gen_deep_pack()
        with open(out, "w") as f:
            json.dump(pack, f, indent=2)
        print(f"wrote deep pack: {pack['count']} rows -> {out} (solutions sealed)")
        return 0
    if "--score-deep" in argv:
        i = argv.index("--score-deep")
        try:
            pack_f, ans_f = argv[i + 1], argv[i + 2]
        except IndexError:
            print("usage: deep_combined.py --score-deep PACK ANSWERS")
            return 2
        with open(pack_f) as f:
            pack = json.load(f)
        with open(ans_f) as f:
            answers = json.load(f)
        r = score_deep_pack(pack, answers)
        print(f"DEEP-LLM score: {r['score']}/{r['total']}")
        for row in r["per"]:
            print(f"  {row['id']} ({row['kind']}): {row['result']}")
        return 0
    return run_gate()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
