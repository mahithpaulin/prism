# Changelog

## 1.5.0 (2026-10-10)

Symbiotic loop: Nexora proposes, Axiom disposes. v1.1 was one-way
(predict -> encode -> prove, single candidate). v1.5 is bidirectional
with no new dependencies and no engine forks:

- `notice.predict_candidates(data, k)`: up to k ranked next-values
  (Markov first, then unseen context-backoff extras), honestly empty
  on abstain. `predict_value()` kept byte-identical.
- `Prism.auto_topk(k)`: proves every candidate (query 0 + reachability),
  first PROVEN wins (repair on veto), else the top candidate's honest
  verdict stands. Early-stops on first PROVEN: clean cycles cost what
  `auto()` costs (2 proves); only ambiguous traces pay more (max 5
  candidates, 2 proves each, plus 2 for the clean re-prove).
- `Prism.auto_symbiotic(k)`: superset of `auto()` (same program/legend/
  proof/reach_proof/verdict for the winner on clean cycles) plus
  anomaly-aware re-prove on the cleaned trace (agreement reported, never
  used to downgrade entailment), pure determinism readout, veto counts,
  candidate table. PROVEN still requires a verified Axiom proof.
- `Prism.watch_symbiotic()`: `changes` uses exactly the `watch()` rule;
  adds `proof_changes`, `anomaly_deltas`, `repairs`.
- `honesty.grade_symbiotic()`: pure selection over ranked verdicts;
  `grade()` untouched. `encode.anomaly_indices/clean_items/
  determinism_for()`: pure helpers, fully unit-tested.
- All v1.1 entry points unchanged: pytest 15 -> 25, eval 9 checks
  untouched, new `eval_symbiotic.py` gate (9 checks) runs in CI.

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
