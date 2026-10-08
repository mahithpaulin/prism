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
