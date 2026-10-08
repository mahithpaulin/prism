"""Prism v1 — combined symbolic engine (v1.0.0).

Nexora (pattern recognition, Python stdlib-only) notices regularities.
Axiom (symbolic reasoning, Rust, zero-dep core) proves or refutes them
via its MCP stdio server. Prism routes each question to the engine that
can answer honestly, and never promotes a confidence into a proof.
"""
__version__ = "1.0.0"

from prism.engine import Prism
from prism.honesty import grade, PrismVerdict

__all__ = ["Prism", "grade", "PrismVerdict", "__version__"]
