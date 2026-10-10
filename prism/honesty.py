"""Honesty contracts for Prism v1.

Two status families, one rule: promote to fact ONLY on a verified
Axiom proof. Everything else stays a graded belief or an inconclusive.
"""

PROVEN = "PROVEN"           # axiom Proved + verified proof
REFUTED = "REFUTED"         # axiom Refuted (closure completed)
IMPOSSIBLE = "IMPOSSIBLE"   # axiom/SAT unsatisfiability with cert
OBSERVED = "OBSERVED"       # nexora FOUND with evidence, no proof
INCONCLUSIVE = "INCONCLUSIVE"  # exhausted/unknown/insufficient/low-confidence/missing-binary

AXIOM_DEFINITE = {"proved": PROVEN, "refuted": REFUTED, "impossible": IMPOSSIBLE}
AXIOM_INCONCLUSIVE = {"exhausted", "unknown", "found"}


class PrismVerdict(dict):
    """A thin dict with a stable key set: verdict/source/detail."""

    def __init__(self, verdict, source, detail=None):
        super().__init__(
            verdict=verdict, source=source, detail=detail or {}
        )


def grade(axiom_status=None, axiom_verified=False, proof_present=False,
          nexora_status=None):
    """Combine one Axiom answer and one Nexora envelope into a verdict.

    Never guesses: an unverified or inconclusive Axiom answer can only
    yield OBSERVED (when Nexora FOUND) or INCONCLUSIVE.
    """
    ax = (axiom_status or "").lower()
    if ax in AXIOM_DEFINITE and proof_present and axiom_verified:
        return PrismVerdict(AXIOM_DEFINITE[ax], "axiom",
                            {"axiom_status": ax, "verified": True})
    if ax in AXIOM_DEFINITE:
        # Definite claim WITHOUT a checked proof backing it: refuse.
        return PrismVerdict(INCONCLUSIVE, "axiom",
                            {"axiom_status": ax,
                             "reason": "proof missing or unverified"})
    if (nexora_status or "").upper() == "FOUND":
        return PrismVerdict(OBSERVED, "nexora",
                            {"axiom_status": ax or "not-asked",
                             "nexora_status": "FOUND"})
    return PrismVerdict(INCONCLUSIVE, "prism",
                        {"axiom_status": ax or "not-asked",
                         "nexora_status": nexora_status or "not-asked"})


def grade_symbiotic(candidate_verdicts, nexora_status=None, anomaly_count=0,
                    clean_agreement=None, determinism=None):
    """Select one verdict from a ranked candidate list. Pure, no I/O.

    candidate_verdicts: list of PrismVerdict (ranked, best first), each
    with detail carrying at least {"next": value}. Selection rule:
      - first PROVEN wins (Axiom proved + verified; repair on veto);
      - else the top candidate's verdict stands (REFUTED stays REFUTED,
        otherwise OBSERVED/INCONCLUSIVE -- never promoted).
    The returned verdict keeps its verdict string and source; only the
    detail is enriched with symbiotic metadata. Empty list degrades to
    grade() with no Axiom answer (honest abstain path).
    """
    cands = list(candidate_verdicts or [])
    if not cands:
        return grade(axiom_status="", nexora_status=nexora_status)
    picked_idx = 0
    for i, v in enumerate(cands):
        try:
            vv = v.get("verdict") if isinstance(v, dict) else None
        except Exception:
            vv = None
        if vv == PROVEN:
            picked_idx = i
            break
    try:
        vetoed = sum(1 for v in cands
                     if isinstance(v, dict) and v.get("verdict") == REFUTED)
    except Exception:
        vetoed = 0
    picked = cands[picked_idx]
    if not isinstance(picked, dict):
        return grade(axiom_status="", nexora_status=nexora_status)
    detail = dict(picked.get("detail", {}) or {})
    detail.update({
        "candidates_tried": len(cands),
        "selected_index": picked_idx,
        "vetoed": vetoed,
        "repaired": bool(picked_idx > 0),
        "anomaly_count": int(anomaly_count or 0),
        "clean_agreement": clean_agreement,
        "determinism": determinism,
    })
    return PrismVerdict(picked.get("verdict", INCONCLUSIVE),
                        picked.get("source", "prism"), detail)
