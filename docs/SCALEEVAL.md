# PrismScale: reasoning x pattern recognition at 10k scale

## Why another eval system

No existing benchmark combines all four of Prism's load-bearing axes:

| System | Scale | What it covers | What it misses for Prism |
|---|---|---|---|
| ARC-AGI-1/2/3 | 100s tasks / 25 games | Pattern induction + reasoning; ARC-3 adds efficiency scoring; human-calibrated | Visual/game modality, API keys, 8h caps; no proofs, no honesty axis |
| Bongard-LOGO | 12,000 procedural + ground-truth programs | Rule induction at scale; symbolic inputs unlock reasoning (2026) | Visual-only; accuracy-only scoring |
| PBEBench (ACL'26) | Unlimited, difficulty-graded | Programmatic generation + contamination resistance; hard <5% | Inductive-only; no streaming/anomaly, no proofs |
| Time-RA / RATs40K (ACL'26) | ~40,000 x 10 domains | Series + text + plots + reasoning labels; detection->diagnosis | LLM-judge flavor; no machine-checked certs |
| NAB / Yahoo / SMD / NASA | 10s-100s series | Streaming anomaly, time-tolerant scoring | Small; "flawed benchmarks create illusion of progress" (Wu & Keogh) |
| LiveBench | 1,270, monthly refresh, objective truth | Freshness-as-contamination-defense | Still static per release; reasoning-only slices (Zebra etc.) |
| miniF2F -> PutnamBench -> FATE (Lean) | 488 -> 672 -> PhD | Proof-carrying verdicts, machine-checked; ALF mutations vs contamination | Heavy stack, math-only, saturating (100% miniF2F); no pattern axis |
| RAVEN/I-RAVEN, MM-IQ | 1k-42k | Procedural analogical reasoning | Shortcut/distractor defects (rsbench); accuracy-only |

PrismScale's position: **programmatic infinity (PBEBench) + freshness doctrine
(LiveBench, taken further: never-static) + proof culture (miniF2F, stdlib-weight)
+ streaming anomalies (NAB, time-tolerant spirit) + adversarial honesty
(RAVEN's lesson)** -- in one stdlib-only harness that runs on free CI minutes.

## The four axes

1. **Accuracy** -- exact-match vs independently recomputed truth. Traps
   (twosol/zero/paradox) grade exact *counts*, the way I-RAVEN grades
   distractor impartiality: answering one of two is a fail here.
2. **Honesty** -- hallucination count must be **0**: PROVEN on unprovable
   (arithmetic frontiers, junk), wrong solution counts, proved-unobserved
   pairs. Any hallucination fails the shard. This is the axis frontier LLMs
   have no equivalent of.
3. **Proof** -- verified-cert rate on provable items (floor 0.97). A proved
   status without `proof_present` never promotes (see Honesty rule).
4. **Efficiency** -- items/sec + proves/sec, reported not gated (ARC-3 spirit:
   skill-acquisition efficiency matters, but v1 only instruments it).

## Families (10,000/shard-set, 2,500 x 4 shards)

- shard0: kk4 uniques/twosol/zero (2,500, L1)
- shard1: kk5-7 + meta-heavy + paradox7 + chains + SAT (2,500, L2-L3)
- shard2: clean cycles + noisy + spikes (2,500, L2)
- shard3: noisy/spike overflow + arithmetic frontiers + watch + long cycles
  + encode/honesty units (2,500, mixed)

`python examples/scale_foundry.py --count` prints the table (no engines).
Grades L1/L2/L3 scale persons, chain length, noise rate, shift count.

## Freshness protocol

Every instance derives from `(shard, family, index, seed_base)` in
non-overlapping seed blocks (>= 10M, far above all prior rounds).
`--seed S` regenerates a fully fresh, equally-valid 10k; the manifest logs
seed + prism/axiom/nexora versions. Default `--seed 1` is the CI gate.
Contamination is impossible by construction: there is no static test set.

## Cost (measured, CI ubuntu-latest)

~115k axiom-mcp proves + ~5k Nexora analyses per 10k run; shards run
~2-8 min each in parallel on free public-repo minutes. Phone rule holds:
only `--selftest` (~30 items, ~20s) and `--count` run on-device.

## LLM lane

`--gen-pack kk4|kk6 --limit N --seed S` emits blind wordings (solutions
sealed, truth recomputed from seeds at score time); `--score-pack` grades
any frontier model on the same items Prism ran. Packets scale to any N.

## Future (not v1)

- MiniF2F-ALF-style mutation sensitivity: paraphrase/mutate instances,
  require stable verdicts.
- Real-data lane: NAB-subset vendor for ecological validity alongside
  synthetic scale (cf. RATs40K's real-world grounding).
- Efficiency gating once baselines stabilize across runners.
