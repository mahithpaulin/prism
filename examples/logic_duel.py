"""Logic duel: Knights-and-Knaves through Prism 1.1 vs. a large language model.

A seeded random 4-person Knights-and-Knaves instance. Each person makes one
statement; knights tell the truth, knaves lie. The instance is accepted only
if exactly one of the 16 type-assignments is consistent (checked by an
independent Python evaluator that shares no code with Axiom).

Prism side: for each assignment, encode types as facts + statements as
rules deriving `bad` on contradiction, and ask Axiom `?- bad.` The unique
Refuted assignment (absent from the completed least model) IS the solution;
the other 15 must come back Proved (contradiction derived + checked).

Modes:
  --gen-only   print the NL wording + consistency count, NOT the solution
               (blind protocol for the LLM contestant)
  (default)    full run: Prism scan + Python cross-check + solution reveal

CI gate: exactly-one-Refuted AND Axiom-scan agrees with Python evaluator.
"""
import itertools
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prism import honesty, prove

PERSONS = ["a", "b", "c", "d"]
NAMES = {"a": "A", "b": "B", "c": "C", "d": "D"}

# template -> (NL renderer, python truth fn, datalog utter-rules)
TEMPLATES = {
    "is_knave": (
        lambda x: f"{NAMES[x]} is a knave",
        lambda t, x: t[x] == "knave",
        lambda p, x: [f"utter_{p}_true :- type({x}, knave)."],
    ),
    "is_knight": (
        lambda x: f"{NAMES[x]} is a knight",
        lambda t, x: t[x] == "knight",
        lambda p, x: [f"utter_{p}_true :- type({x}, knight)."],
    ),
    "same": (
        lambda x, y: f"{NAMES[x]} and {NAMES[y]} are the same type",
        lambda t, x, y: t[x] == t[y],
        lambda p, x, y: [f"utter_{p}_true :- type({x}, T), type({y}, T)."],
    ),
    "different": (
        lambda x, y: f"{NAMES[x]} and {NAMES[y]} are different types",
        lambda t, x, y: t[x] != t[y],
        lambda p, x, y: [f"utter_{p}_true :- type({x}, knight), type({y}, knave).",
                          f"utter_{p}_true :- type({x}, knave), type({y}, knight)."],
    ),
    "one_knave": (
        lambda x, y: f"at least one of {NAMES[x]} and {NAMES[y]} is a knave",
        lambda t, x, y: t[x] == "knave" or t[y] == "knave",
        lambda p, x, y: [f"utter_{p}_true :- type({x}, knave).",
                          f"utter_{p}_true :- type({y}, knave)."],
    ),
}
UNARY = ("is_knave", "is_knight")
BINARY = ("same", "different", "one_knave")

WORDING = ("Four people -- A, B, C, and D -- are each either a Knight "
           "(always tells the truth) or a Knave (always lies). Each makes "
           "one statement.\nFor EACH person, say Knight or Knave.\n")


def gen_instance(seed):
    rng = random.Random(seed)
    stmts = {}
    for p in PERSONS:
        others = [q for q in PERSONS if q != p]
        if rng.random() < 0.4:
            kind = rng.choice(UNARY)
            args = (rng.choice(others),)
        else:
            kind = rng.choice(BINARY)
            args = tuple(rng.sample(others, 2))
        stmts[p] = (kind, args)
    return stmts


def consistent(assignment, stmts):
    """Python-side evaluator: True iff no contradiction under assignment."""
    for p, (kind, args) in stmts.items():
        said_true = TEMPLATES[kind][1](assignment, *args)
        is_knight = assignment[p] == "knight"
        if is_knight != said_true:
            return False
    return True


def find_unique(seed_start=0):
    for seed in range(seed_start, seed_start + 10000):
        stmts = gen_instance(seed)
        sols = [dict(zip(PERSONS, combo))
                for combo in itertools.product(("knight", "knave"), repeat=4)
                if consistent(dict(zip(PERSONS, combo)), stmts)]
        if len(sols) == 1:
            return seed, stmts, sols[0]
    raise RuntimeError("no unique instance in range")


def nl_wording(stmts):
    lines = [WORDING]
    for p in PERSONS:
        kind, args = stmts[p]
        lines.append(f"{NAMES[p]} says: \"{TEMPLATES[kind][0](*args)}.\"")
    return "\n".join(lines)


def program_for(assignment, stmts):
    lines = [f"type({p}, {assignment[p]})." for p in PERSONS]
    for p, (kind, args) in stmts.items():
        lines.extend(TEMPLATES[kind][2](p, *args))
        lines.append(f"bad :- type({p}, knight), not utter_{p}_true.")
        lines.append(f"bad :- type({p}, knave), utter_{p}_true.")
    lines.append("bad :- type(P, knight), type(P, knave).")
    lines.append("?- bad.")
    return "\n".join(lines) + "\n"


def prism_scan(stmts):
    """Returns {solution_assignments, details}. Solution = Refuted (no `bad`)."""
    sols, details = [], []
    for combo in itertools.product(("knight", "knave"), repeat=4):
        a = dict(zip(PERSONS, combo))
        out = prove.prove(program_for(a, stmts))
        st = (out.get("status") or "").lower()
        verdict = honesty.grade(axiom_status=st,
                                axiom_verified=bool(out.get("verified")),
                                proof_present=bool(out.get("proof_present")),
                                nexora_status="NONE")
        details.append((a, st, verdict["verdict"]))
        if st == "refuted":
            sols.append(a)
    return sols, details


def run_one(seed_start):
    """One duel instance. Returns (seed, passed, note). No solution printed."""
    seed, stmts, solution = find_unique(seed_start)
    sols, _ = prism_scan(stmts)
    ok = len(sols) == 1 and sols[0] == solution
    short = "".join(s[0].upper() if v == "knight" else s[0].lower()
                    for s, v in sorted(solution.items()))
    return seed, ok, f"solution {short}"


def main():
    gen_only = "--gen-only" in sys.argv
    sweep = [a for a in sys.argv if a.startswith("--sweep")]
    if sweep:
        n = int(sweep[0].split("=", 1)[1]) if "=" in sweep[0] else 24
        if not prove.available():
            print("axiom-mcp not built; sweep skipped.")
            sys.exit(0)
        passed, seen = 0, set()
        for i in range(n):
            seed, ok, note = run_one(i * 10000)
            dup = " DUP" if seed in seen else ""
            seen.add(seed)
            passed += ok and not dup
            print(f"[{i + 1:2d}/{n}] seed {seed}: {'PASS' if ok else 'FAIL'} ({note}){dup}")
        print(f"\nsweep: {passed}/{n} (distinct seeds: {len(seen)})")
        print("SWEEP-PASS" if passed == n else "SWEEP-FAIL")
        sys.exit(0 if passed == n else 1)
    seed, stmts, solution = find_unique()
    print(f"seed: {seed}")
    print(nl_wording(stmts))
    n = sum(1 for combo in itertools.product(("knight", "knave"), repeat=4)
            if consistent(dict(zip(PERSONS, combo)), stmts))
    print(f"\nconsistent assignments (independent Python count): {n}")
    if gen_only:
        print("(solution sealed -- answer blind, then re-run without --gen-only)")
        return
    if not prove.available():
        print("axiom-mcp not built; Prism scan skipped.")
        return
    sols, details = prism_scan(stmts)
    for a, st, v in details:
        tag = " <== SOLUTION (Refuted: no contradiction)" if st == "refuted" else ""
        print(f"{{A:{a['a']}, B:{a['b']}, C:{a['c']}, D:{a['d']}}} -> axiom:{st} prism:{v}{tag}")
    ok_unique = len(sols) == 1
    ok_agree = ok_unique and sols[0] == solution
    print(f"\nprism solutions: {len(sols)} (need 1); agrees with Python: {ok_agree}")
    print("DUEL-PASS" if (ok_unique and ok_agree) else "DUEL-FAIL")
    sys.exit(0 if (ok_unique and ok_agree) else 1)


if __name__ == "__main__":
    main()
