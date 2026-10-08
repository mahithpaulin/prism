# Changelog

## 1.1.0 (2026-10-08)

Prism works with just both engines. `Prism.auto(data)` closes the loop
with no human in the middle: Nexora predicts the next value,
`prism/encode.py` turns the observed transition trace into an Axiom
Datalog program (`trans` facts + `reach` rules, legend `s0...`), Axiom
proves the prediction follows from what was seen (query 0) plus
reachability (query 1). `Prism.watch(batches)` re-runs `auto` per batch
and flags verdict/prediction changes (deterministic, no clocks).

Semantics (kept honest): PROVEN certifies entailment by the encoded
trace, never conformity of the future; unobserved pairs earn Refuted;
abstentions, unencodable data, and missing binaries degrade to
OBSERVED/INCONCLUSIVE. Tests 8 → 15, eval 5 → 9 checks, all green
with zero skips where both engines are present, honest skips elsewhere.

## 1.0.0 (2026-10-08)

Initial Prism: Axiom `v3-slice-1` @ `f8668030cb2d1a02365cfbde8cf6f19906e4ed69`
(PR mahithpaulin/axiom#7 draft) + Nexora `v3.1.0` @
`7131cb1d93e0f332536d20c83fe4c2cafb5e9dc4`
(PR mahithpaulin/nexora#3 draft), pinned as submodules.

- `prism/engine.py`: `Prism` — `notice / prove / prove_sat / route /
  notice_then_prove / health`.
- `prism/notice.py`: lazy Nexora import (`$PRISM_NEXORA_PATH`, `./nexora`,
  `../nexora`, `~/nexora`, installed); missing engine → honest
  `INSUFFICIENT_DATA` envelope, never raises.
- `prism/prove.py`: MCP stdio client (`initialize` + `tools/call`);
  binary search (`$PRISM_AXIOM_MCP`, submodule `target/{debug,release}`,
  sibling, `~/axiom`, PATH); missing binary → honest `inconclusive`.
- `prism/honesty.py`: `grade()` — definite Axiom status + `proof_present`
  + verified ⇒ `PROVEN/REFUTED/IMPOSSIBLE`; definite-without-proof ⇒
  `INCONCLUSIVE`; else Nexora `FOUND` ⇒ `OBSERVED`, else `INCONCLUSIVE`.
- `tests/test_prism.py` (8 tests, all fast, Rust tests skip without binary).
- `examples/demo.py` + `examples/eval_prism.py` (ground-truth gate, CI-required).
- CI (`.github/workflows/ci.yml`): checkout recursive → setup Python →
  setup Rust → `cargo build -p axiom-mcp` → pytest → demo → eval.
