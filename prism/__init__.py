"""Prism v1.5 — combined symbolic engine.

Nexora (pattern recognition, Python stdlib-only) notices regularities.
Axiom (symbolic reasoning, Rust, zero-dep core) proves or refutes them
via its MCP stdio server. Prism routes each question to the engine that
can answer honestly, and never promotes a confidence into a proof.

v1.1.0: auto() closes the loop with just both engines -- Nexora predicts,
prism/encode.py turns the observed trace into an Axiom program, Axiom
proves the prediction follows from what was seen. watch() re-runs per
batch and flags verdict/prediction changes.
v1.5.0: symbiotic loop -- Nexora proposes up to k candidates, Axiom
vetoes each one (first PROVEN wins, else honest fallback); winners are
re-proved on the anomaly-cleaned trace and annotated with determinism.
auto()/watch()/notice_then_prove()/grade() are byte-compatible with v1.1.
"""
__version__ = "1.5.0"

from prism.engine import Prism
from prism.honesty import grade, PrismVerdict

__all__ = ["Prism", "grade", "PrismVerdict", "__version__"]
