# MAAR AI Evaluation & Benchmarking Guide

This document describes the evaluation framework for benchmarking MAAR's multi-agent research performance, quality, and workflow reliability.

---

## 1. Overview & Principles

Evaluation in MAAR is designed to be **reproducible, automated, and free from mandatory paid evaluation platforms**.

The framework measures:
1. **Structural Metrics:** Completion rate, latency, token costs, and source collection depth.
2. **Quality & Verification Metrics:** Evidence coverage, citation completeness, section density, duplicate URL rates.
3. **Workflow Metrics:** Human approval outcomes and export format success rates.

---

## 2. Benchmark Dataset

The standard evaluation dataset is located at `eval/dataset/questions.json`. It contains ≥10 calibrated research questions covering diverse domains:
- **Technology:** Transformer architectures, Post-quantum cryptography.
- **Science:** Ambient superconductors, JWST early universe cosmological data.
- **Healthcare:** GLP-1 agonists vs bariatric surgery, mRNA vs viral vector T-cell immunity.
- **Economics:** Universal Basic Income vs CCTs, CBDCs and commercial bank liquidity.
- **History:** 1915 Gallipoli campaign supply logistics.
- **Society:** Algorithmic content moderation and freedom of expression.

---

## 3. Running Evaluations

### Validate Dataset Schema
```bash
python eval/runner.py --dry-run
```

### Inspect a Single Benchmark Query
```bash
python eval/runner.py --question-id Q001
```

### Generate Quality Report
```bash
python eval/runner.py --report-only
```

---

## 4. Key Metrics Reference

| Metric | Target | Formula |
|--------|--------|---------|
| `task_completion_rate` | $\ge 90\%$ | $\frac{\text{completed runs}}{\text{total runs}}$ |
| `evidence_linkage_rate` | $\ge 85\%$ | $\frac{\text{claims with evidence}}{\text{total claims}}$ |
| `citation_completeness_rate` | $\ge 80\%$ | $\frac{\text{claims with citations}}{\text{total claims}}$ |
| `duplicate_source_rate` | $\le 5\%$ | $\frac{\text{duplicate URLs}}{\text{total URLs}}$ |
| `export_success_rate` | $\ge 95\%$ | $\frac{\text{ready exports}}{\text{total exports}}$ |
