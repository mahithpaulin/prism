"""Prism: the combined engine. Notice with Nexora, prove with Axiom."""
from prism import honesty
from prism import notice, prove


class Prism:
    """One object, two engines.

    - notice(data): Nexora envelope (patterns/anomalies/predictions).
    - prove(program, ...): Axiom MCP verdict dict.
    - prove_sat(dimacs, ...): Axiom SAT verdict dict.
    - route(kind): which engine owns a task ("prove"|"notice"|"both").
    - notice_then_prove(data, program, ...): the Prism loop in one call.
    """

    def notice(self, data):
        return notice.observe(data)

    def prove(self, program, query_index=0, max_steps=1_000_000):
        return prove.prove(program, query_index=query_index, max_steps=max_steps)

    def prove_sat(self, dimacs, max_steps=1_000_000):
        return prove.prove_sat(dimacs, max_steps=max_steps)

    def route(self, kind):
        k = (kind or "").lower()
        if k in ("prove", "proof", "verify", "sat", "plan", "constraint", "game"):
            return "axiom"
        if k in ("notice", "pattern", "anomaly", "predict", "forecast",
                 "correlation", "seasonality", "drift"):
            return "nexora"
        if k in ("both", "combined", "prism"):
            return "both"
        return "both"

    def notice_then_prove(self, data, program, query_index=0, max_steps=1_000_000):
        """Run Nexora observation + Axiom proof, combine with honesty grading.

        Returns {"observation": ..., "proof": ..., "verdict": PrismVerdict}.
        The verdict is PROVEN/REFUTED/IMPOSSIBLE only when Axiom returns a
        definite status WITH proof_present; otherwise OBSERVED (Nexora FOUND)
        or INCONCLUSIVE. Never promotes a confidence into a proof.
        """
        obs = self.notice(data)
        pf = self.prove(program, query_index=query_index, max_steps=max_steps)
        nx_status = obs.get("status", "NONE") if isinstance(obs, dict) else "NONE"
        verdict = honesty.grade(axiom_status=pf.get("status"),
                                axiom_verified=bool(pf.get("verified")),
                                proof_present=bool(pf.get("proof_present")),
                                nexora_status=nx_status)
        return {"observation": obs, "proof": pf, "verdict": verdict}

    def health(self):
        return {"prism": "1.0.0",
                "nexora": {"available": notice.available(), "source": notice.source()},
                "axiom": {"available": prove.available(), "binary": prove.binary_path(),
                          "version": prove.version() if prove.available() else {"present": False}}}
