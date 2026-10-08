"""Prism v1 tests: fast, honest, no heavy builds on the authoring machine.

- Pure unit tests (honesty grading, routing) always run.
- Nexora tests run when a checkout is importable, else skip.
- Axiom tests run when axiom-mcp is built, else skip.
CI builds axiom-mcp, so the full gate runs there.
"""
import pytest

from prism import honesty
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
