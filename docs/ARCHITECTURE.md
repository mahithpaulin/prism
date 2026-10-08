# Architecture

```text
WORLD ──▶ NEXORA (nexora/) ──▶ candidate regularity ──▶ AXIOM (axiom/) ──▶ verdict + proof
  ▲              │                                                      │
  └──────────────┴──────── drift / regimes (re-prove on change) ────────┘
```

`prism/` is the only new code (stdlib-only): `engine.py` owns the loop,
`notice.py` lazily imports Nexora, `prove.py` speaks MCP stdio to a built
`axiom-mcp`, `honesty.py` grades the pair. Neither engine was forked:
both are pinned submodules, so upstream fixes flow via SHA bumps.

## Why this shape

- Axiom's core must stay zero-dep Rust; Nexora must stay stdlib-only
  Python. A Python bridge that shells out over line-delimited JSON-RPC
  respects both without adding dependencies to either.
- Missing pieces degrade honestly: no `nexora` checkout →
  `INSUFFICIENT_DATA`; no `axiom-mcp` binary → `inconclusive`. Tests skip
  instead of failing, so the repo is green on a bare clone and fully
  proven once CI builds the binary.
- The load-bearing invariant lives in `honesty.grade()`: one function,
  four pure unit tests, no I/O. Everything else is transport.

## Data flow

1. `notice(data)`: `Nexora.discover` + `find_anomalies` + `predict` in one
   envelope (status, explanation, patterns, anomalies, predictions).
2. `prove(program)`: `initialize` + `tools/call axiom_prove` over stdin/
   stdout; parse verdict (`status/summary/steps/proof_present`), mark
   `verified` when a definite status arrives with a proof.
3. `notice_then_prove`: runs both, grades with `honesty.grade`.
4. Monitor (v1 manual, v2 watchlist): `Nexora.update()` streams new
   observations; on drift, re-encode and re-prove.
