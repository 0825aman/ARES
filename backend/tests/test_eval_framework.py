"""test_eval_framework.py — Tests for evaluation metrics and benchmark reporting."""
import json
import sys
from pathlib import Path

# Ensure project root is in sys.path so eval package can be imported
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from eval.metrics.structural import (
    task_completion_rate,
    mean_run_latency_seconds,
    mean_llm_cost_usd,
    source_collection_rate,
)
from eval.metrics.quality import (
    citation_completeness_rate,
    evidence_linkage_rate,
    duplicate_source_rate,
    empty_report_section_rate,
)
from eval.metrics.workflow import (
    approval_success_rate,
    export_success_rate,
)
from eval.reporter import generate_json_report, generate_markdown_report
from eval.runner import load_dataset


def test_dataset_contains_at_least_10_questions():
    questions = load_dataset()
    assert len(questions) >= 10
    categories = {q["category"] for q in questions}
    assert len(categories) >= 4
    for q in questions:
        assert "id" in q
        assert "question" in q
        assert "difficulty" in q


def test_structural_metrics():
    runs = [
        {"status": "completed", "duration_seconds": 30.0, "estimated_cost_usd": 0.02, "source_count": 5},
        {"status": "completed", "duration_seconds": 40.0, "estimated_cost_usd": 0.04, "source_count": 4},
        {"status": "failed", "duration_seconds": 10.0, "estimated_cost_usd": 0.01, "source_count": 1},
    ]
    assert task_completion_rate(runs) == round(2 / 3, 4)
    assert mean_run_latency_seconds(runs) == 26.67
    assert mean_llm_cost_usd(runs) == round((0.02 + 0.04 + 0.01) / 3, 4)
    assert source_collection_rate(runs, min_expected=3) == round(2 / 3, 4)


def test_quality_metrics():
    claims = [
        {"id": "c1", "evidence_count": 2},
        {"id": "c2", "evidence_count": 0, "evidence_ids": []},
        {"id": "c3", "evidence_count": 1},
    ]
    citations = [
        {"claim_id": "c1", "url": "https://example.com/1"},
        {"claim_id": "c3", "url": "https://example.com/3"},
    ]
    assert citation_completeness_rate(citations, claims) == round(2 / 3, 4)
    assert evidence_linkage_rate(claims) == round(2 / 3, 4)

    sources = [
        {"url": "https://example.com/page1"},
        {"url": "https://example.com/page2"},
        {"url": "https://example.com/page1"},
    ]
    assert duplicate_source_rate(sources) == round(1 / 3, 4)

    reports = [
        {
            "executive_summary": "A" * 150,
            "key_findings": ["Finding A", "Finding B"],
            "observations": "Short",  # < 100 chars
        }
    ]
    assert empty_report_section_rate(reports, min_chars=100) == round(1 / 3, 4)


def test_workflow_metrics():
    approvals = [
        {"decision": "approved"},
        {"decision": "rejected"},
        {"decision": "approved"},
    ]
    assert approval_success_rate(approvals) == round(2 / 3, 4)

    exports = [
        {"status": "ready"},
        {"status": "failed"},
        {"status": "ready"},
    ]
    assert export_success_rate(exports) == round(2 / 3, 4)


def test_reporter_generation():
    dummy_metrics = {"task_completion_rate": 0.95, "citation_completeness_rate": 0.88}
    json_rep = generate_json_report(dummy_metrics)
    parsed = json.loads(json_rep)
    assert "summary" in parsed
    assert parsed["summary"]["task_completion_rate"] == 0.95

    md_rep = generate_markdown_report(dummy_metrics)
    assert "# MAAR Evaluation & Benchmark Report" in md_rep
    assert "| `task_completion_rate` |" in md_rep
