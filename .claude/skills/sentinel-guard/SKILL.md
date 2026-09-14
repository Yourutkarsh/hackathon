---
name: sentinel-guard
description: Enforce Sentinel Shift V5.1 invariants, zero-leakage causal rules, and verification gates.
---

# Sentinel Shift Architectural Guard & Verification Skill

When invoked via `/sentinel-guard`, strictly enforce all Sentinel Shift V5.1 invariants and verification gates before and after file changes.

## 1. Non-Negotiable Invariants
1. **Engine Immutability:** `risk_engine_v5_1.py` is strictly READ-ONLY. Never alter or patch it.
2. **Zero Temporal Leakage:** Baseline windows must strictly use `[t - window, t)`. Never count the current event in its own baseline.
3. **Read-Only LLM Separation:** The LLM layer is strictly an evidence summarizer. It must never calculate risk scores, alter severities, or label users as malicious.
4. **Deterministic Reproducibility:** Lock `seed=42` across generators and Isolation Forest models. MongoDB demo reset must run under 50 ms.

## 2. Post-Execution Verification Gate
Always run the test suite after any code modification:
```bash
python test_v51_fixes.py