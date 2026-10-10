"""Encoder: observed sequences -> Axiom Datalog programs. No human in the loop.

Honest, narrow semantics: the program encodes the OBSERVED transition
trace as facts. Query 0 asks the Nexora-predicted transition; query 1 asks
reachability from the trace start to the predicted value. A Proved verdict
certifies the prediction is entailed by the encoded trace (machine-checked
consistency over what was seen). A Refuted verdict is earned (absent from
the completed least model). Nothing here claims the future will conform --
the inductive leap stays a Nexora confidence, never a proof.
"""
import re

_ATOM = re.compile(r"^[a-z][a-z0-9_]*$")


def legend_for(data):
    """Map each distinct value to s0, s1, ... in first-seen order.

    Returns (symbols, legend) where symbols[i] names data[i] and
    legend maps str(value) -> symbol. Returns (None, reason) when the
    data cannot be encoded (empty, unhashable items).
    """
    try:
        items = list(data)
    except TypeError:
        return None, "not a sequence"
    if len(items) < 2:
        return None, "fewer than 2 observations (no transitions)"
    legend = {}
    symbols = []
    try:
        for v in items:
            hash(v)
            key = str(v)
            if key not in legend:
                legend[key] = f"s{len(legend)}"
            symbols.append(legend[key])
    except TypeError:
        return None, "unhashable observation (cannot name it)"
    return (symbols, legend), None


def program_for_trace(symbols, current_sym, predicted_sym):
    """Build the verification program. Pure function of symbols."""
    pairs = sorted({(a, b) for a, b in zip(symbols, symbols[1:])})
    lines = [f"trans({a}, {b})." for a, b in pairs]
    lines.append("reach(X, Y) :- trans(X, Y).")
    lines.append("reach(X, Z) :- reach(X, Y), trans(Y, Z).")
    lines.append(f"?- trans({current_sym}, {predicted_sym}).")
    lines.append(f"?- reach({symbols[0]}, {predicted_sym}).")
    return "\n".join(lines) + "\n"


def auto_program(data, current, predicted):
    """Encode data + a (current -> predicted) claim.

    Returns (program, info) or (None, reason). info carries the legend,
    the queried pair, and whether the pair was observed (a prediction
    Nexora derived from the trace always is; anything else earns Refuted).
    """
    got, reason = legend_for(data)
    if got is None:
        return None, reason
    symbols, legend = got
    try:
        cur_sym = legend[str(current)]
    except KeyError:
        return None, "current value never observed"
    pred_sym = legend.get(str(predicted))
    if pred_sym is None:
        return None, "predicted value never observed"
    observed = (cur_sym, pred_sym) in {(a, b) for a, b in zip(symbols, symbols[1:])}
    program = program_for_trace(symbols, cur_sym, pred_sym)
    return program, {"legend": legend, "current": cur_sym,
                     "predicted": pred_sym, "pair_observed": observed}


def anomaly_indices(anomalies, n):
    """Extract valid anomaly positions. Pure function of the envelope.

    Returns a sorted list of int indices i with 0 <= i < n.
    Anything malformed is ignored, never raises.
    """
    out = set()
    try:
        count = int(n)
    except (TypeError, ValueError):
        return []
    if count <= 0 or not isinstance(anomalies, list):
        return []
    for a in anomalies:
        if not isinstance(a, dict):
            continue
        try:
            i = int(a.get("index", -1))
        except (TypeError, ValueError):
            continue
        if 0 <= i < count:
            out.add(i)
    return sorted(out)


def clean_items(data_items, drop_indices):
    """Filter observations at dropped positions. Pure, never raises.

    Returns (kept_list, kept_positions) or (None, reason) when fewer
    than 2 observations would remain (no transitions to encode).
    """
    try:
        items = list(data_items)
    except TypeError:
        return None, "not a sequence"
    try:
        drop = set(int(i) for i in (drop_indices or []))
    except (TypeError, ValueError):
        drop = set()
    kept = [v for i, v in enumerate(items) if i not in drop]
    kept_pos = [i for i in range(len(items)) if i not in drop]
    if len(kept) < 2:
        return None, "fewer than 2 observations remain after cleaning"
    return (kept, kept_pos), None


def determinism_for(symbols):
    """Map each state to its observed successors. Pure function.

    Returns (outgoing, is_deterministic) where outgoing maps symbol
    -> sorted list of successor symbols. Deterministic means every
    observed state has exactly one observed successor.
    """
    outgoing = {}
    try:
        pairs = list(zip(symbols, symbols[1:]))
    except TypeError:
        return {}, True
    for a, b in pairs:
        outgoing.setdefault(a, set()).add(b)
    det = all(len(v) == 1 for v in outgoing.values())
    return ({k: sorted(v) for k, v in outgoing.items()}, det)
