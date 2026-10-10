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
        return {"prism": "1.5.0",
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

    # ------------------------------------------------ v1.5 symbiotic loop

    def auto_topk(self, data, k=3, current=None, max_steps=1_000_000):
        """Try up to k Nexora candidates; let Axiom veto each one.

        Returns {"observation", "prediction" (top-1, auto-compatible),
        "candidates": [{next, program, legend, proof, reach_proof,
        verdict, pair_observed, encode_reason}], "selected_index",
        "selected", "verdict"}. The verdict is the first PROVEN candidate,
        else the top candidate's verdict -- never promoted. Early-stops
        on the first PROVEN, so clean cycles cost exactly what auto()
        costs (2 proves); only ambiguous traces pay for extra candidates.
        """
        try:
            kk = max(1, int(k))
        except (TypeError, ValueError):
            kk = 3
        kk = min(kk, 5)
        obs = self.notice(data)
        nx_status = obs.get("status", "NONE") if isinstance(obs, dict) else "NONE"
        cur, cands, penv = notice.predict_candidates(data, current, k=kk)
        prediction = {"current": cur, "next": (cands[0] if cands else None),
                      "envelope": penv if isinstance(penv, dict) else {"status": penv}}
        if not cands:
            verdict = honesty.grade(axiom_status="", nexora_status=nx_status)
            return {"observation": obs, "prediction": prediction,
                    "candidates": [], "selected_index": 0, "selected": None,
                    "verdict": verdict}
        ranked = []
        for nxt in cands:
            program, info = encode.auto_program(data, cur, nxt)
            if program is None:
                v = honesty.grade(axiom_status="", nexora_status=nx_status)
                ranked.append({"next": nxt, "program": None, "legend": None,
                               "proof": None, "reach_proof": None, "verdict": v,
                               "pair_observed": False,
                               "encode_reason": info})
                continue
            pf = self.prove(program, query_index=0, max_steps=max_steps)
            reach = self.prove(program, query_index=1, max_steps=max_steps)
            v = honesty.grade(axiom_status=pf.get("status"),
                              axiom_verified=bool(pf.get("verified")),
                              proof_present=bool(pf.get("proof_present")),
                              nexora_status=nx_status)
            ranked.append({"next": nxt, "program": program,
                           "legend": info.get("legend"), "proof": pf,
                           "reach_proof": reach, "verdict": v,
                           "pair_observed": bool(info.get("pair_observed"))})
            try:
                vv = v.get("verdict")
            except Exception:
                vv = None
            if vv == honesty.PROVEN:
                break
        verdict = honesty.grade_symbiotic(
            [r["verdict"] for r in ranked], nexora_status=nx_status)
        try:
            sel_idx = int(verdict.get("detail", {}).get("selected_index", 0))
        except (TypeError, ValueError):
            sel_idx = 0
        sel_idx = max(0, min(sel_idx, len(ranked) - 1))
        return {"observation": obs, "prediction": prediction,
                "candidates": ranked, "selected_index": sel_idx,
                "selected": ranked[sel_idx], "verdict": verdict}

    def auto_symbiotic(self, data, k=3, current=None, max_steps=1_000_000):
        """Full bidirectional loop: Nexora proposes, Axiom disposes.

        1. Nexora proposes up to k candidates (Markov first, then
           context-backoff extras) + anomaly mask.
        2. Axiom proves/vetoes each candidate on the full-trace program.
        3. The first PROVEN candidate wins (repair on veto); else the
           top candidate's honest verdict stands.
        4. Anomaly-aware re-prove: the winner is re-proved on the
           anomaly-cleaned trace; agreement is reported, never used to
           downgrade a full-trace entailment.
        5. Determinism is read off the trace (pure) and attached.
        Returns a superset of auto(): program/legend/proof/reach_proof/
        verdict describe the SELECTED candidate, so on clean cycles the
        output matches auto() plus extras. PROVEN still means a verified
        Axiom proof exists -- the inductive leap stays a confidence.
        """
        top = self.auto_topk(data, k=k, current=current, max_steps=max_steps)
        obs = top["observation"]
        ranked = top["candidates"]
        sel_idx = top["selected_index"]
        sel = top["selected"]
        nx_status = obs.get("status", "NONE") if isinstance(obs, dict) else "NONE"
        anomalies = []
        try:
            anomalies = obs.get("anomalies", []) if isinstance(obs, dict) else []
        except Exception:
            anomalies = []
        try:
            items = list(data)
        except TypeError:
            items = []
        anomaly_idx = encode.anomaly_indices(anomalies, len(items))
        # Determinism (pure, off the full trace).
        det_info = {"deterministic": None, "branching": {}, "current": None}
        try:
            got, _reason = encode.legend_for(items)
            if got is not None:
                symbols, _legend = got
                outgoing, det = encode.determinism_for(symbols)
                cur_sym = None
                if sel is not None and isinstance(sel.get("legend"), dict):
                    try:
                        cur_sym = sel["legend"].get(
                            str(top["prediction"].get("current")))
                    except Exception:
                        cur_sym = None
                if cur_sym is None and got is not None:
                    try:
                        cur_sym = _legend.get(str(top["prediction"].get("current")))
                    except Exception:
                        cur_sym = None
                det_info = {"deterministic": bool(det), "branching": outgoing,
                            "current": cur_sym,
                            "successors": outgoing.get(cur_sym, []) if cur_sym else []}
        except Exception:
            pass
        # Clean-trace re-prove of the winner (bounded: 2 extra proves).
        clean_proof = None
        clean_reach = None
        clean_verdict = None
        agreement = None
        if sel is not None and sel.get("program") is not None and anomaly_idx:
            kept, reason = encode.clean_items(items, anomaly_idx)
            if kept is not None:
                kept_items, _pos = kept
                cprog, cinfo = encode.auto_program(
                    kept_items, top["prediction"].get("current"), sel.get("next"))
                if cprog is not None:
                    clean_proof = self.prove(cprog, query_index=0,
                                             max_steps=max_steps)
                    clean_reach = self.prove(cprog, query_index=1,
                                             max_steps=max_steps)
                    clean_verdict = honesty.grade(
                        axiom_status=clean_proof.get("status"),
                        axiom_verified=bool(clean_proof.get("verified")),
                        proof_present=bool(clean_proof.get("proof_present")),
                        nexora_status=nx_status)
                    try:
                        agreement = (clean_verdict.get("verdict")
                                     == sel["verdict"].get("verdict"))
                    except Exception:
                        agreement = None
                else:
                    agreement = None
            else:
                agreement = None
        verdict = honesty.grade_symbiotic(
            [r["verdict"] for r in ranked] if ranked else [],
            nexora_status=nx_status,
            anomaly_count=len(anomaly_idx),
            clean_agreement=agreement,
            determinism=(det_info.get("deterministic")
                         if isinstance(det_info, dict) else None))
        if sel is None:
            return {"observation": obs, "prediction": top["prediction"],
                    "program": None, "legend": None, "proof": None,
                    "reach_proof": None, "verdict": verdict,
                    "candidates": ranked, "selected_index": 0,
                    "selected": None, "vetoed": 0,
                    "determinism": det_info, "clean_proof": None,
                    "clean_reach": None, "clean_verdict": None,
                    "agreement": agreement,
                    "anomaly_count": len(anomaly_idx),
                    "anomaly_indices": anomaly_idx}
        try:
            vetoed = sum(1 for r in ranked
                         if isinstance(r.get("verdict"), dict)
                         and r["verdict"].get("verdict") == honesty.REFUTED)
        except Exception:
            vetoed = 0
        return {"observation": obs, "prediction": top["prediction"],
                "program": sel.get("program"), "legend": sel.get("legend"),
                "proof": sel.get("proof"), "reach_proof": sel.get("reach_proof"),
                "verdict": verdict, "candidates": ranked,
                "selected_index": sel_idx, "selected": sel,
                "vetoed": vetoed, "determinism": det_info,
                "clean_proof": clean_proof, "clean_reach": clean_reach,
                "clean_verdict": clean_verdict, "agreement": agreement,
                "anomaly_count": len(anomaly_idx),
                "anomaly_indices": anomaly_idx}

    def watch_symbiotic(self, batches, k=3, max_steps=1_000_000):
        """Run auto_symbiotic() per batch; flag prediction/verdict changes.

        Returns {"runs": [...], "changes": [indices],
        "proof_changes": [...], "anomaly_deltas": [...], "repairs": [...] }.
        `changes` uses exactly the watch() rule, so watch() callers can
        switch without re-baselining; the extra fields carry the
        symbiotic signal (proof-status flips, anomaly-count steps,
        batches where Axiom vetoed the top candidate).
        """
        runs = [self.auto_symbiotic(b, k=k, max_steps=max_steps)
                for b in batches]
        changes = []
        proof_changes = []
        anomaly_deltas = []
        repairs = []
        for i in range(1, len(runs)):
            a, b = runs[i - 1], runs[i]
            if (a["prediction"].get("next") != b["prediction"].get("next") or
                    a["verdict"].get("verdict") != b["verdict"].get("verdict")):
                changes.append(i)
            try:
                pa = (a.get("proof") or {}).get("status")
                pb = (b.get("proof") or {}).get("status")
            except Exception:
                pa = pb = None
            if pa != pb:
                proof_changes.append(i)
            try:
                da = int(a.get("anomaly_count", 0) or 0)
                db = int(b.get("anomaly_count", 0) or 0)
            except (TypeError, ValueError):
                da = db = 0
            if db != da:
                anomaly_deltas.append({"batch": i, "from": da, "to": db})
            try:
                if int(b.get("selected_index", 0) or 0) > 0:
                    repairs.append(i)
            except (TypeError, ValueError):
                pass
        return {"runs": runs, "changes": changes,
                "proof_changes": proof_changes,
                "anomaly_deltas": anomaly_deltas, "repairs": repairs}
