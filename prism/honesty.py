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
