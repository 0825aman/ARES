# MAAR Evaluation & Benchmarking Framework

The `eval/` framework provides reproducible benchmark datasets and automated metric calculation for the MAAR research engine.

## Structure

```
eval/
├── dataset/
│   └── questions.json    # Standard 10-question evaluation benchmark
├── metrics/
│   ├── structural.py     # Latency, completion rate, cost, collection metrics
│   ├── quality.py        # Evidence linkage, citation completeness, section density
│   └── workflow.py       # Human approvals, export generation success
├── runner.py             # CLI benchmark runner
└── reporter.py           # Markdown and JSON report generator
```

## Running Benchmarks

### 1. Validate Dataset (Dry Run)
```bash
python eval/runner.py --dry-run
```

### 2. Run Single Question
```bash
python eval/runner.py --question-id Q001
```

### 3. Generate Report Summary
```bash
python eval/runner.py --report-only
```
