# neurosymbolic-curriculum

**Curriculum-trained neural policy over a formal symbolic core.**

A neural model learns to navigate Lean 4 + Mathlib by proposing proof tactics, staged by import-depth complexity. Facts live in the symbolic layer (verified, executable, never hallucinated). The model is a librarian-and-translator: it learns *where things live, how to compose them, and which tactic to try next* — not what is true.

## Thesis

Most attempts to teach neural networks mathematics treat the network as the knowledge substrate. We argue this is the wrong split. Mathematical content is structural; symbolic systems already encode it perfectly. The neural component should learn **search policy**, not facts.

```
Neural shell:   proposes tactics, navigates search, translates NL ↔ formal
Symbolic core:  axioms + inference rules + proof checker (Lean 4 / Mathlib)
Curriculum:     on the neural shell only — staged by formal depth, 
                gated on proof-success rate (not token accuracy)
```

This avoids three failure modes of pure-neural approaches:
1. **Surface pattern-matching:** examples of a rule are not the rule. SFT on `2+3=5` does not yield commutativity.
2. **Cascading error:** layer N at 99% accuracy becomes layer 20 at ~82%. Stacking neural inferences erodes correctness multiplicatively. Stacking *verified proofs* does not.
3. **Hallucination under composition:** the model cannot fabricate a theorem the symbolic core rejects.

## Architecture

```
NL goal ──► [Neural Policy: tactic proposal] ──► [Lean 4 / Mathlib: verifier] ──► verified step
                       ▲                                       │
                       └───────── proof state feedback ◄────────┘
```

## Phase plan

| Phase | Scope | Signal of success |
|---|---|---|
| 1 | SFT on Mathlib tier 0, single-tactic proposal | >20% tactic success on held-out tier-0 goals |
| 2 | Curriculum: stage tiers 0→4, mastery gate before advancement | Tier-N model beats tier-0 model on tier-N goals |
| 3 | Best-first proof search over tactic proposals | Close non-trivial held-out theorems end-to-end |
| 4 | Expert iteration / self-play on Lean | Improve without new human data |
| 5 | Empirical-axiom schema; physics layer (classical mechanics in Lean) | Verify a textbook derivation formally |

## Week 1 scope (this repo, this week)

End state: Phase 1 working end-to-end on Main (RTX 5090). Single GPU, single model, single Mathlib tier.

| Evening | Goal |
|---|---|
| 1 | Repo scaffolding, Lean 4 + Mathlib install, LeanDojo smoke test on `Mathlib.Algebra.Group.Basic` |
| 2 | Extraction pipeline: `(goal_state, tactic, next_goal_state)` tuples from Mathlib subset |
| 3 | Depth stratification: parse Mathlib import DAG, bucket into 5 tiers, save tier-0 JSONL |
| 4 | SFT pipeline: Qwen2.5-Coder-1.5B + LoRA on tier-0 `(goal → tactic)` pairs, MLflow tracking |
| 5 | Eval harness: LeanDojo round-trip — model proposes tactic, Lean applies, measure success rate |

**Non-goals this week:** RL, multi-tier curriculum, proof search, physics, distributed training.

## Stack

- **Formal core:** Lean 4, Mathlib (pinned commit)
- **Bridge:** [LeanDojo](https://leandojo.org/) for extraction and runtime interaction
- **Base model:** Qwen2.5-Coder-1.5B (LoRA fine-tunes)
- **Training:** HuggingFace transformers, TRL, PEFT
- **Tracking:** MLflow (server on Olares, port 5000)
- **Compute:** Main (Ryzen 9950X3D, RTX 5090 32GB)

## Layout

```
neurosymbolic-curriculum/
├── README.md
├── LICENSE                      # MIT
├── pyproject.toml
├── .gitignore                   # CLAUDE.md, data/, experiments/, .venv/, etc.
├── data/
│   ├── extract_mathlib.py       # LeanDojo → (goal, tactic, next_goal) tuples
│   ├── depth_stratify.py        # bucket by import depth in Mathlib DAG
│   └── splits/                  # tier_0/, tier_1/, ... train/val/test (gitignored)
├── src/
│   ├── model.py                 # base model + LoRA wrapper
│   ├── curriculum.py            # tier progression + mastery gate
│   ├── train.py                 # SFT per tier
│   ├── eval.py                  # proof success rate via LeanDojo
│   └── interact.py              # CLI: goal → tactic → verify
├── configs/
│   └── tier_0.yaml
├── experiments/
│   └── runs/                    # MLflow artifacts (gitignored)
└── notebooks/
    └── 00_data_exploration.ipynb
```

## Risks & open questions

- **LeanDojo extraction is brittle on Mathlib HEAD.** Pin a known-working Mathlib commit (LeanDojo repo lists compatible versions). Document the pin in `data/extract_mathlib.py`.
- **Tier-0 may saturate too fast.** If Qwen2.5-Coder-1.5B already crushes tier 0 zero-shot, the curriculum payoff only shows at tier 2+. Still useful data, but adjust expectations.
- **Tactic vocabulary mismatch.** Mathlib uses Lean 4 tactic syntax; the base model was pretrained mostly on Lean 3 and other proof assistants. Tokenizer behavior on Lean 4 syntax is an empirical question for Evening 4.
- **Proof success rate vs. token accuracy.** The harness must measure whether the proposed tactic *closes the goal*, not whether the tokens match the ground-truth proof. Multiple valid tactics exist for any goal.

## License

MIT. See [LICENSE](LICENSE).
