"""Prism v1 tests: fast, honest, no heavy builds on the authoring machine.

- Pure unit tests (honesty grading, routing) always run.
- Nexora tests run when a checkout is importable, else skip.
- Axiom tests run when axiom-mcp is built, else skip.
CI builds axiom-mcp, so the full gate runs there.
"""
import pytest

from prism import encode, honesty
from prism import notice, prove
from prism.engine import Prism


CLOSURE_PROGRAM = (
    "edge(a, b).\n"
    "edge(b, c).\n"
    "path(X, Y) :- edge(X, Y).\n"
    "path(X, Z) :- path(X, Y), edge(Y, Z).\n"
    "?- path(a, c).\n"
)


def test_grade_proven_only_with_verified_proof():
    v = honesty.grade(axiom_status="proved", axiom_verified=True,
                      proof_present=True, nexora_status="FOUND")
    assert v["verdict"] == "PROVEN" and v["source"] == "axiom"


def test_grade_definite_without_proof_is_inconclusive():
    v = honesty.grade(axiom_status="proved", axiom_verified=False,
                      proof_present=False, nexora_status="FOUND")
    assert v["verdict"] == "INCONCLUSIVE"


def test_grade_observed_when_axiom_silent_and_nexora_found():
    v = honesty.grade(axiom_status="exhausted", axiom_verified=False,
                      proof_present=False, nexora_status="FOUND")
    assert v["verdict"] == "OBSERVED" and v["source"] == "nexora"


def test_grade_inconclusive_when_both_silent():
    v = honesty.grade(axiom_status="unknown", axiom_verified=False,
                      proof_present=False, nexora_status="NONE")
    assert v["verdict"] == "INCONCLUSIVE"


def test_route():
    p = Prism()
    assert p.route("prove") == "axiom"
    assert p.route("sat") == "axiom"
    assert p.route("anomaly") == "nexora"
    assert p.route("forecast") == "nexora"
    assert p.route("both") == "both"


def test_notice_cycle_or_skip():
    if not notice.available():
        pytest.skip(f"nexora not checked out ({notice.source()})")
    obs = notice.observe(list("ABC" * 10))
    assert obs["status"] in ("FOUND", "NONE", "INSUFFICIENT_DATA", "LOW_CONFIDENCE")
    # ABCx10 cycle must be FOUND with patterns, not silent.
    assert obs["status"] == "FOUND", obs.get("explanation", "")
    assert len(obs["patterns"]) >= 1


def test_prove_closure_or_skip():
    if not prove.available():
        pytest.skip("axiom-mcp not built (honest skip)")
    out = prove.prove(CLOSURE_PROGRAM)
    assert out["status"] == "proved", out.get("summary", "")
    assert out.get("proof_present") is True


def test_notice_then_prove_never_fabricates():
    p = Prism()
    combo = p.notice_then_prove(list("ABC" * 10), CLOSURE_PROGRAM)
    assert combo["verdict"]["verdict"] in ("PROVEN", "OBSERVED", "INCONCLUSIVE",
                                           "REFUTED", "IMPOSSIBLE")
    if not prove.available():
        # Without the binary, PROVEN is unreachable by construction.
        assert combo["verdict"]["verdict"] in ("OBSERVED", "INCONCLUSIVE")


def test_encoder_legend_stable_and_round_trips():
    (got, reason) = encode.legend_for(list("ABCABC"))
    assert reason is None
    symbols, legend = got
    assert symbols == ["s0", "s1", "s2", "s0", "s1", "s2"]
    assert legend == {"A": "s0", "B": "s1", "C": "s2"}


def test_encoder_rejects_unencodable():
    assert encode.legend_for([])[0] is None
    assert encode.legend_for(["only"])[0] is None
    assert encode.legend_for([["nested"], ["lists"]])[0] is None
    assert encode.auto_program([], None, None)[0] is None


def test_encoder_program_shape():
    program, info = encode.auto_program(list("ABCABC"), "C", "A")
    assert program is not None and info["pair_observed"] is True
    assert "?- trans(s2, s0)." in program
    assert "?- reach(s0, s0)." in program
    assert program.count("trans(s") >= 3


def test_auto_cycle_proven_or_skip():
    if not notice.available() or not prove.available():
        pytest.skip("needs both engines (honest skip)")
    r = Prism().auto(list("ABC" * 10))
    assert r["prediction"]["next"] == "A", r["prediction"]
    assert r["proof"]["status"] == "proved", r["proof"]
    assert r["proof"].get("proof_present") is True
    assert r["verdict"]["verdict"] == "PROVEN", r["verdict"]


def test_auto_negative_earns_refuted_or_skip():
    if not prove.available():
        pytest.skip("axiom-mcp not built (honest skip)")
    # Query a transition never observed: must be Refuted, never Proved.
    (got, _reason) = encode.legend_for(list("ABCABC"))
    symbols = got[0]
    program = encode.program_for_trace(symbols, "s0", "s0")  # A->A unseen
    out = prove.prove(program, query_index=0)
    assert out["status"] == "refuted", out


def test_auto_junk_never_proven():
    r = Prism().auto([f"tok{i:04d}x" for i in range(25)])
    assert r["verdict"]["verdict"] in ("OBSERVED", "INCONCLUSIVE")
    assert r["verdict"]["verdict"] != "PROVEN"


def test_watch_flags_change_or_skip():
    if not notice.available():
        pytest.skip(f"nexora not checked out ({notice.source()})")
    w = Prism().watch([list("ABC" * 10), [f"tok{i:04d}x" for i in range(25)]])
    assert len(w["runs"]) == 2
    assert w["changes"] == [1]


# ------------------------------------------------ v1.5 symbiotic (pure first)


def test_anomaly_indices_pure():
    anoms = [{"index": 2}, {"index": 2}, {"index": 99}, {"index": -1},
             {"nope": 1}, "junk", {"index": "3"}]
    assert encode.anomaly_indices(anoms, 5) == [2, 3]
    assert encode.anomaly_indices([], 10) == []
    assert encode.anomaly_indices([{"index": 0}], 0) == []


def test_clean_items_pure():
    (kept, _reason) = encode.clean_items(list("ABCDE"), [1, 3])
    items, pos = kept
    assert items == ["A", "C", "E"] and pos == [0, 2, 4]
    assert encode.clean_items(list("ABC"), [0, 1, 2])[0] is None
    assert encode.clean_items("ABC", [])[0] is not None


def test_determinism_pure():
    out, det = encode.determinism_for(["s0", "s1", "s2", "s0", "s1", "s2"])
    assert det is True
    assert out["s0"] == ["s1"]
    out2, det2 = encode.determinism_for(["s0", "s1", "s0", "s2"])
    assert det2 is False
    assert sorted(out2["s0"]) == ["s1", "s2"]


def test_grade_symbiotic_selects_proven_pure():
    a = honesty.grade("refuted", True, True, "FOUND")
    b = honesty.grade("proved", True, True, "FOUND")
    v = honesty.grade_symbiotic([a, b], nexora_status="FOUND")
    assert v["verdict"] == "PROVEN"
    assert v["detail"]["selected_index"] == 1
    assert v["detail"]["repaired"] is True
    assert v["detail"]["vetoed"] == 1


def test_grade_symbiotic_falls_back_honestly_pure():
    o = honesty.grade("exhausted", False, False, "FOUND")
    assert honesty.grade_symbiotic([], nexora_status="FOUND")["verdict"] == "OBSERVED"
    v = honesty.grade_symbiotic([o], nexora_status="FOUND")
    assert v["verdict"] == "OBSERVED"


def test_predict_candidates_or_skip():
    if not notice.available():
        pytest.skip(f"nexora not checked out ({notice.source()})")
    cur, cands, _env = notice.predict_candidates(list("ABC" * 10), k=3)
    assert cur == "C"
    assert cands and cands[0] == "A"
    assert len(cands) <= 3


def test_auto_topk_matches_auto_on_cycle_or_skip():
    if not notice.available() or not prove.available():
        pytest.skip("needs both engines (honest skip)")
    p = Prism()
    a = p.auto(list("ABC" * 10))
    t = p.auto_topk(list("ABC" * 10), k=3)
    assert t["prediction"]["next"] == a["prediction"]["next"] == "A"
    assert t["verdict"]["verdict"] == "PROVEN"
    assert t["selected"]["program"] == a["program"]
    assert t["selected_index"] == 0


def test_auto_symbiotic_superset_or_skip():
    if not notice.available() or not prove.available():
        pytest.skip("needs both engines (honest skip)")
    p = Prism()
    r = p.auto_symbiotic(list("ABC" * 10), k=3)
    assert r["verdict"]["verdict"] == "PROVEN"
    assert r["program"] is not None and r["proof"]["status"] == "proved"
    assert r["determinism"]["deterministic"] is True
    assert r["anomaly_count"] == 0
    assert r["selected_index"] == 0


def test_auto_symbiotic_junk_never_proven():
    r = Prism().auto_symbiotic([f"tok{i:04d}x" for i in range(25)], k=3)
    assert r["verdict"]["verdict"] in ("OBSERVED", "INCONCLUSIVE")
    assert r["verdict"]["verdict"] != "PROVEN"


def test_watch_symbiotic_matches_watch_or_skip():
    if not notice.available():
        pytest.skip(f"nexora not checked out ({notice.source()})")
    p = Prism()
    seq = [list("ABC" * 10), [f"tok{i:04d}x" for i in range(25)]]
    assert p.watch_symbiotic(seq)["changes"] == p.watch(seq)["changes"] == [1]
