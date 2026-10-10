"""Notice side: Nexora pattern recognition behind a lazy, honest import.

Resolution order for the Nexora checkout:
  1. $PRISM_NEXORA_PATH
  2. ./nexora (submodule checkout inside the prism repo)
  3. ../nexora (sibling checkout, e.g. ~/nexora on the dev phone)
  4. installed `nexora` package

If none is found, every call returns an INSUFFICIENT-style envelope
instead of raising — the Prism honesty rule.
"""
import importlib.util
import os
import sys

_CANDIDATES = [
    os.environ.get("PRISM_NEXORA_PATH", ""),
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nexora"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "nexora"),
    os.path.expanduser("~/nexora"),
]

_engine_cls = None
_engine_error = None
_engine_source = None


def _load():
    global _engine_cls, _engine_error, _engine_source
    if _engine_cls is not None or _engine_error is not None:
        return
    for cand in [c for c in _CANDIDATES if c]:
        init = os.path.join(cand, "nexora", "api", "engine.py")
        if os.path.isfile(init):
            try:
                if cand not in sys.path:
                    sys.path.insert(0, cand)
                mod = importlib.import_module("nexora.api.engine")
                _engine_cls = mod.Nexora
                _engine_source = cand
                return
            except Exception as exc:  # keep looking
                _engine_error = f"{cand}: {exc}"
                continue
    try:
        from nexora.api.engine import Nexora
        _engine_cls = Nexora
        _engine_source = "<installed>"
        return
    except Exception as exc:
        _engine_error = str(exc)


def available():
    _load()
    return _engine_cls is not None


def source():
    _load()
    return _engine_source or f"missing ({_engine_error})"


def _missing(op):
    return {"status": "INSUFFICIENT_DATA",
            "explanation": f"nexora not available for {op}: {_engine_error}",
            "patterns": [], "anomalies": [], "prism_source": source()}


def observe(data):
    """Run discover + anomalies + prediction; always an envelope, never raises."""
    _load()
    if _engine_cls is None:
        return _missing("observe")
    nx = _engine_cls()
    try:
        disc = nx.discover(data)
    except Exception as exc:
        return {"status": "INSUFFICIENT_DATA",
                "explanation": f"discover failed honestly: {exc}",
                "patterns": [], "anomalies": [], "prism_source": source()}
    try:
        anom = nx.find_anomalies(data)
    except Exception:
        anom = {"anomalies": []}
    try:
        pred = nx.predict(data)
    except Exception:
        pred = {"predictions": []}
    status = disc.get("status", "NONE") if isinstance(disc, dict) else "NONE"
    return {"status": status,
            "explanation": disc.get("explanation", "") if isinstance(disc, dict) else "",
            "patterns": disc.get("patterns", []) if isinstance(disc, dict) else [],
            "anomalies": anom.get("anomalies", []) if isinstance(anom, dict) else [],
            "predictions": pred.get("predictions", []) if isinstance(pred, dict) else [],
            "prism_source": source()}


def predict_candidates(data, current=None, k=3):
    """Ask Nexora for up to k next-value candidates after `current`.

    Returns (current_used, [next values in ranked order], envelope).
    Markov predictions come first, then unseen context-backoff extras --
    but only when Markov has at least one candidate. When Markov is
    empty Nexora is abstaining (no recorded outgoing transition, e.g.
    junk or arithmetic frontiers) and the context order-0 unigram
    fallback must not override that abstention, so the list stays empty.
    This keeps the top-1 identical to predict_value() in every case:
    v1.1 abstains exactly where v1.5 abstains. Empty list means Nexora
    abstained or is unavailable -- never a fabricated guess. Pure
    ranking, no Axiom contact (the veto happens in engine.py).
    """
    _load()
    try:
        kk = max(1, int(k))
    except (TypeError, ValueError):
        kk = 3
    if _engine_cls is None:
        return None, [], {"status": "INSUFFICIENT_DATA",
                           "reason": f"nexora unavailable: {_engine_error}"}
    try:
        items = list(data)
    except TypeError:
        return None, [], {"status": "INSUFFICIENT_DATA",
                           "reason": "data is not a sequence"}
    if current is None:
        if not items:
            return None, [], {"status": "INSUFFICIENT_DATA",
                               "reason": "empty data, no current value"}
        current = items[-1]
    nx = _engine_cls()
    try:
        res = nx.predict(items, current=current, top_k=kk)
    except TypeError:
        # Older Nexora without top_k kwarg: fall back to default call.
        try:
            res = nx.predict(items, current=current)
        except Exception as exc:
            return current, [], {"status": "INSUFFICIENT_DATA",
                                  "reason": f"predict failed honestly: {exc}"}
    except Exception as exc:
        return current, [], {"status": "INSUFFICIENT_DATA",
                              "reason": f"predict failed honestly: {exc}"}
    if not isinstance(res, dict):
        return current, [], {"status": "NONE",
                              "reason": "nexora returned non-dict envelope"}
    markov = res.get("predictions", []) if isinstance(res.get("predictions"), list) else []
    if not markov:
        # Markov abstains: no recorded outgoing transition. Keep the
        # abstention (v1.1 predict_value returns None here too); the
        # context order-0 fallback is not a real prediction.
        return current, [], res
    seen = []
    seen_set = set()
    for field in ("predictions", "context"):
        preds = res.get(field, []) if isinstance(res.get(field), list) else []
        for p in preds:
            nxt = p.get("next") if isinstance(p, dict) else None
            try:
                key = repr(nxt)
            except Exception:
                continue
            if nxt is None or key in seen_set:
                continue
            try:
                hash(nxt)
            except TypeError:
                continue
            seen.append(nxt)
            seen_set.add(key)
            if len(seen) >= kk:
                break
        if len(seen) >= kk:
            break
    return current, seen, res


def predict_value(data, current=None):
    """Ask Nexora for the next value after `current` (default: last element).

    Returns (current_used, value_or_None, envelope). None means Nexora
    abstained or is unavailable -- never a fabricated guess.
    """
    _load()
    if _engine_cls is None:
        return None, None, {"status": "INSUFFICIENT_DATA",
                            "reason": f"nexora unavailable: {_engine_error}"}
    try:
        items = list(data)
    except TypeError:
        return None, None, {"status": "INSUFFICIENT_DATA",
                            "reason": "data is not a sequence"}
    if current is None:
        if not items:
            return None, None, {"status": "INSUFFICIENT_DATA",
                                "reason": "empty data, no current value"}
        current = items[-1]
    nx = _engine_cls()
    try:
        res = nx.predict(items, current=current)
    except Exception as exc:
        return current, None, {"status": "INSUFFICIENT_DATA",
                               "reason": f"predict failed honestly: {exc}"}
    preds = res.get("predictions", []) if isinstance(res, dict) else []
    if not preds:
        return current, None, {"status": res.get("status", "NONE") if isinstance(res, dict) else "NONE",
                               "reason": "nexora abstained (no candidates)"}
    nxt = preds[0].get("next") if isinstance(preds[0], dict) else None
    return current, nxt, res
