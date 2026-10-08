"""Prism v1 — combined symbolic engine (v1.1.0).

Nexora (pattern recognition, Python stdlib-only) notices regularities.
Axiom (symbolic reasoning, Rust, zero-dep core) proves or refutes them
via its MCP stdio server. Prism routes each question to the engine that
can answer honestly, and never promotes a confidence into a proof.

v1.1.0: auto() closes the loop with just both engines -- Nexora predicts,
prism/encode.py turns the observed trace into an Axiom program, Axiom
proves the prediction follows from what was seen. watch() re-runs per
batch and flags verdict/prediction changes.
"""
__version__ = "1.1.0"

from prism.engine import Prism
from prism.honesty import grade, PrismVerdict

__all__ = ["Prism", "grade", "PrismVerdict", "__version__"]
