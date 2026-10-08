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
