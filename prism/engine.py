"""Prism: the combined engine. Notice with Nexora, prove with Axiom."""
from prism import encode, honesty
from prism import notice, prove


class Prism:
    """One object, two engines.

    - notice(data): Nexora envelope (patterns/anomalies/predictions).
    - prove(program, ...): Axiom MCP verdict dict.
    - prove_sat(dimacs, ...): Axiom SAT verdict dict.
    - route(kind): which engine owns a task ("prove"|"notice"|"both").
    - notice_then_prove(data, program, ...): the Prism loop in one call.
    - auto(data, current=None): the full loop, no human in the middle --
      Nexora predicts, Prism encodes the trace, Axiom proves the prediction
      follows from what was seen.
    - watch(batches): auto() per batch, flagging verdict/prediction changes.
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
        return {"prism": "1.1.0",
                "nexora": {"available": notice.available(), "source": notice.source()},
                "axiom": {"available": prove.available(), "binary": prove.binary_path(),
                          "version": prove.version() if prove.available() else {"present": False}}}

    def auto(self, data, current=None, max_steps=1_000_000):
        """Full loop with just both engines: predict -> encode -> prove.

        Returns {"observation", "prediction", "program", "legend", "proof",
        "reach_proof", "verdict"}. PROVEN certifies the prediction is
        entailed by the encoded trace. Abstentions, unencodable data, and a
        missing binary all degrade to OBSERVED/INCONCLUSIVE -- never PROVEN.
        """
        obs = self.notice(data)
        nx_status = obs.get("status", "NONE") if isinstance(obs, dict) else "NONE"
        cur, nxt, penv = notice.predict_value(data, current)
        prediction = {"current": cur, "next": nxt,
                      "envelope": penv if isinstance(penv, dict) else {"status": penv}}
        if nxt is None:
            verdict = honesty.grade(axiom_status="", nexora_status=nx_status)
            return {"observation": obs, "prediction": prediction, "program": None,
                    "legend": None, "proof": None, "reach_proof": None, "verdict": verdict}
        program, info = encode.auto_program(data, cur, nxt)
        if program is None:
            verdict = honesty.grade(axiom_status="", nexora_status=nx_status)
            return {"observation": obs, "prediction": prediction, "program": None,
                    "legend": None, "proof": None, "reach_proof": None,
                    "verdict": verdict,
                    "encode_reason": info}
        pf = self.prove(program, query_index=0, max_steps=max_steps)
        reach = self.prove(program, query_index=1, max_steps=max_steps)
        verdict = honesty.grade(axiom_status=pf.get("status"),
                                axiom_verified=bool(pf.get("verified")),
                                proof_present=bool(pf.get("proof_present")),
                                nexora_status=nx_status)
        return {"observation": obs, "prediction": prediction, "program": program,
                "legend": info.get("legend"), "proof": pf, "reach_proof": reach,
                "verdict": verdict}

    def watch(self, batches, max_steps=1_000_000):
        """Run auto() per batch; flag batches where prediction/verdict changed.

        Returns {"runs": [...auto results...], "changes": [batch indices]}.
        Deterministic: no clocks, only verdict/prediction comparison.
        """
        runs = [self.auto(b, max_steps=max_steps) for b in batches]
        changes = []
        for i in range(1, len(runs)):
            a, b = runs[i - 1], runs[i]
            if (a["prediction"].get("next") != b["prediction"].get("next") or
                    a["verdict"].get("verdict") != b["verdict"].get("verdict")):
                changes.append(i)
        return {"runs": runs, "changes": changes}
