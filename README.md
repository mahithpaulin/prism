# Prism v1 — combined symbolic engine

**Nexora notices. Axiom proves. Prism routes honestly.**

Prism v1 pins two proven engines and wires them into one loop:

- **Axiom `v3-slice-1`** (`f866803`, PR `mahithpaulin/axiom#7` draft) —
  Rust symbolic reasoning, zero-dep core, exposed here via its
  `axiom-mcp` stdio server (`axiom_prove` / `axiom_sat` / `axiom_version`).
- **Nexora `v3.1.0`** (`7131cb1`, PR `mahithpaulin/nexora#3` draft) —
  stdlib-only Python pattern recognition (`discover / find_anomalies /
  predict / update / ...`, 100-iteration v3 loop).

Checked out as submodules (`axiom/`, `nexora/`), pinned to those exact
commits. The `prism/` package itself is stdlib-only (`>=3.10`).

```python
from prism import Prism
p = Prism()
obs = p.notice(list("ABCABCABC"))          # Nexora envelope
pf = p.prove("edge(a,b).\nedge(b,c).\n"
             "path(X,Y) :- edge(X,Y).\n"
             "path(X,Z) :- path(X,Y), edge(Y,Z).\n"
             "?- path(a,c).\n")             # Axiom verdict (needs built axiom-mcp)
combo = p.notice_then_prove(list("ABCABCABC"), "edge(a,b).\n?- edge(a,b).\n")
print(combo["verdict"]["verdict"])          # PROVEN / OBSERVED / INCONCLUSIVE — never guessed
print(p.health())
```

## Honesty rule

Promote to fact **only** on Axiom `proved/refuted/impossible` **with**
`proof_present` + verified. Everything else stays `OBSERVED` (Nexora
`FOUND` with evidence) or `INCONCLUSIVE` (`exhausted/unknown/insufficient/
low-confidence`, or `axiom-mcp` not built). Missing binaries never fail —
they return honest `INCONCLUSIVE` envelopes, so `pytest` is green with or
without the Rust build; CI builds `axiom-mcp` and runs the full gate.

## Layout

- `prism/` — `engine.py` (Prism loop) · `notice.py` (lazy Nexora import) ·
  `prove.py` (MCP stdio client) · `honesty.py` (grading, the load-bearing rule)
- `axiom/` · `nexora/` — pinned submodules (exact SHAs in `.gitmodules` + CHANGELOG)
- `tests/test_prism.py` — fast unit + integration (Rust tests skip cleanly without binary)
- `examples/demo.py` — the story end to end · `examples/eval_prism.py` — ground-truth gate (CI-required)
- `docs/ARCHITECTURE.md` · `docs/LIMITS.md` · `CHANGELOG.md`

```bash
pip install -e .                  # or run from repo root (stdlib only)
python -m pytest tests/ -q
python examples/demo.py
python examples/eval_prism.py
# full proof path (needs Rust):
cargo build -p axiom-mcp --manifest-path axiom/Cargo.toml
export PRISM_AXIOM_MCP=$PWD/axiom/target/debug/axiom-mcp
python examples/eval_prism.py     # proof checks now run for real
```

Public repo → GitHub Actions minutes are free. License: MIT.
