# Limits

Prism inherits its parents' limits and adds one of its own.

- Axiom: no V2 text language for new reps yet, no full Simplex, no table
  constraints, no go scoring, no IR serialisation (Stage A/B work), no
  GPU/neural path (deliberate). `Exhausted`/`Unknown` carry no proof.
- Nexora: confidences, never proofs. Flat series stay silent; univariate
  never trips the multivariate detector; `predict_next` abstains below
  threshold. See `nexora/docs/LIMITATIONS.md`.
- Prism v1: the Nexora→Axiom encoder is manual (you write the program
  string). The monitor loop is manual (you call `update`, then re-prove).
  An automatic encoder library + watchlist is Prism v2 work.
- Missing `axiom-mcp` binary or `nexora` checkout is NOT an error: every
  entry point returns a labelled inconclusive envelope.
