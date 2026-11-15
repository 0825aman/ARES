"""test_llm_evaluations.py — Comprehensive tests for the 6 LLM & Multi-Agent Evaluation dimensions."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure backend root is in sys.path
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import pytest

from app.evaluation.accuracy_metrics import (
    exact_match_score,
    accuracy_score,
    precision_recall_f1,
    semantic_similarity_score,
    rouge_scores,
    bleu_scores,
)
from app.evaluation.rag_metrics import (
    context_precision_score,
    context_recall_score,
    faithfulness_score,
    answer_relevancy_score,
    context_relevancy_score,
    groundedness_score,
)
from app.evaluation.agentic_metrics import (
    task_completion_rate,
    goal_achievement_score,
    tool_call_accuracy_score,
    tool_execution_success_rate,
    planning_accuracy_score,
    reasoning_quality_score,
    agent_coordination_score,
    handoff_accuracy_score,
    loop_detection_score,
)
from app.evaluation.safety_metrics import (
    hallucination_rate_metric,
    toxicity_metric,
    bias_metric,
    prompt_injection_resistance_rate,
    pii_leakage_rate_metric,
    policy_violation_rate_metric,
    guardrail_intervention_rate_metric,
)
from app.evaluation.performance_metrics import (
    calculate_latency_percentiles,
    tokens_per_second_metric,
    cost_per_successful_task,
    error_rate_metric,
    throughput_per_minute_metric,
)
from app.evaluation.multi_agent_metrics import (
    supervisor_routing_accuracy_score,
    conflict_resolution_rate,
    inter_agent_consistency_score,
    task_distribution_efficiency,
    calculate_agent_scorecards,
)
from app.evaluation.evaluator import evaluation_engine


# ── 1. Accuracy and Quality Metrics Tests ──────────────────────────────────────
def test_exact_match_score():
    assert exact_match_score("Quantum Computing", "quantum computing") == 1.0
    assert exact_match_score("Quantum Computing!", "quantum computing.") == 1.0
    assert exact_match_score("Classical Computing", "Quantum Computing") == 0.0


def test_precision_recall_f1():
    gen = "CRISPR gene editing in human cancer cells"
    ref = "CRISPR gene editing technology in cancer therapies"
    p, r, f1 = precision_recall_f1(gen, ref)
    assert 0.0 < p <= 1.0
    assert 0.0 < r <= 1.0
    assert 0.0 < f1 <= 1.0


def test_semantic_similarity_score():
    s1 = "Artificial intelligence accelerates pharmaceutical discovery"
    s2 = "AI technology speeds up drug discovery"
    s3 = "Cooking traditional pasta recipes"
    sim_high = semantic_similarity_score(s1, s2)
    sim_low = semantic_similarity_score(s1, s3)
    assert sim_high > sim_low


def test_rouge_and_bleu_scores():
    gen = "The patient showed marked improvement after immunotherapy"
    ref = "The patient demonstrated significant improvement after receiving immunotherapy"
    rouge = rouge_scores(gen, ref)
    bleu = bleu_scores(gen, ref)

    assert "rouge_1" in rouge and rouge["rouge_1"] > 0.0
    assert "rouge_l" in rouge and rouge["rouge_l"] > 0.0
    assert "bleu_1" in bleu and bleu["bleu_1"] > 0.0


# ── 2. RAG Evaluation Metrics Tests ───────────────────────────────────────────
def test_rag_context_precision_and_recall():
    query = "What is the mechanism of mRNA vaccines?"
    contexts = [
        "mRNA vaccines deliver instructions to cells to produce a harmless viral spike protein.",
        "Other unrelated news about sports and weather in autumn.",
    ]
    prec = context_precision_score(contexts, query)
    assert prec > 0.0

    ground_truth = ["mRNA vaccines produce spike protein"]
    rec = context_recall_score(contexts, ground_truth)
    assert rec > 0.0


def test_rag_faithfulness_and_groundedness():
    contexts = ["Penicillin was discovered by Alexander Fleming in 1928."]
    faithful_ans = "Alexander Fleming discovered penicillin in 1928."
    unfaithful_ans = "Penicillin was synthesized by Albert Einstein in 1999."

    f_high = faithfulness_score(faithful_ans, contexts)
    f_low = faithfulness_score(unfaithful_ans, contexts)
    assert f_high > f_low

    claims = [{"id": "c1", "verification_status": "verified", "evidence_count": 2}]
    citations = [{"claim_id": "c1", "is_verified": True}]
    assert groundedness_score(claims, citations) == 1.0


# ── 3. Agentic AI Evaluation Metrics Tests ─────────────────────────────────────
def test_agentic_task_and_goal_metrics():
    tasks = [
        {"status": "completed"},
        {"status": "completed"},
        {"status": "failed"},
    ]
    assert task_completion_rate(tasks) == round(2 / 3, 4)

    assert goal_achievement_score("completed", has_final_report=True, critic_approved=True) == 1.0
    assert goal_achievement_score("failed", has_final_report=False) == 0.0


def test_agentic_planning_and_reasoning_metrics():
    plan = {"title": "Oncology Research Plan", "methodology": "Systematic Review"}
    tasks = [{"title": "Task 1", "priority": 1}, {"title": "Task 2", "priority": 2}]
    plan_score = planning_accuracy_score(plan, tasks)
    assert plan_score >= 0.8

    reason_score = reasoning_quality_score(
        observations_present=True,
        contradictions_analyzed=True,
        limitations_explicit=True,
    )
    assert reason_score >= 0.95


def test_agentic_loop_and_coordination_metrics():
    assert loop_detection_score(3, max_allowed=30) == 1.0
    assert loop_detection_score(35, max_allowed=30) < 0.8
    assert loop_detection_score(5, has_circular_pingpong=True) == 0.2


# ── 4. Safety & Guardrail Metrics Tests ────────────────────────────────────────
def test_safety_metrics():
    claims = [
        {"verification_status": "verified"},
        {"verification_status": "refuted"},
        {"verification_status": "verified"},
    ]
    hallucination_rate = hallucination_rate_metric(claims)
    assert hallucination_rate == round(1 / 3, 4)

    clean_text = "Renewable energy has expanded across European grids."
    assert toxicity_metric(clean_text) == 0.0
    assert bias_metric(clean_text) == 0.0

    assert prompt_injection_resistance_rate(50, 49) == 0.98
    assert pii_leakage_rate_metric(100, 0) == 0.0
    assert guardrail_intervention_rate_metric(100, 4) == 0.04


# ── 5. Performance and Cost Metrics Tests ──────────────────────────────────────
def test_performance_latency_and_throughput():
    latencies = [10.0, 12.0, 15.0, 20.0, 25.0]
    p = calculate_latency_percentiles(latencies)
    assert p["mean"] == 16.4
    assert p["p50"] == 15.0
    assert p["max"] == 25.0

    tps = tokens_per_second_metric(500, 10.0)
    assert tps == 50.0

    cost = cost_per_successful_task(1.0, 50)
    assert cost == 0.02


# ── 6. Multi-Agent System Evaluation Tests ────────────────────────────────────
def test_multi_agent_system_metrics():
    scorecards = calculate_agent_scorecards()
    assert "planner" in scorecards
    assert "researcher" in scorecards
    assert "supervisor" in scorecards
    assert "critic" in scorecards

    assert scorecards["planner"].accuracy_score >= 0.90
    assert scorecards["researcher"].success_rate >= 0.90
    assert scorecards["supervisor"].accuracy_score >= 0.90
    assert scorecards["critic"].accuracy_score >= 0.90

    assert supervisor_routing_accuracy_score(50, unnecessary_revisions=2) == 0.96
    assert conflict_resolution_rate(10, 9) == 0.90
    assert inter_agent_consistency_score([0.9, 0.85], [0.88, 0.82]) > 0.9


# ── 7. Master Evaluator End-to-End Test ────────────────────────────────────────
def test_evaluation_engine_dashboard_summary():
    summary = evaluation_engine.get_dashboard_summary(None)
    assert summary["status"] == "operational"
    assert "composite_score" in summary
    assert "accuracy_and_quality" in summary
    assert "rag_metrics" in summary
    assert "agentic_metrics" in summary
    assert "safety_metrics" in summary
    assert "performance_metrics" in summary
    assert "multi_agent_system" in summary
    assert len(summary["multi_agent_system"]["agents"]) == 4


if __name__ == "__main__":
    print("1. Accuracy tests...", flush=True)
    test_exact_match_score()
    test_precision_recall_f1()
    test_semantic_similarity_score()
    test_rouge_and_bleu_scores()

    print("2. RAG tests...", flush=True)
    test_rag_context_precision_and_recall()
    test_rag_faithfulness_and_groundedness()

    print("3. Agentic tests...", flush=True)
    test_agentic_task_and_goal_metrics()
    test_agentic_planning_and_reasoning_metrics()
    test_agentic_loop_and_coordination_metrics()

    print("4. Safety tests...", flush=True)
    test_safety_metrics()

    print("5. Performance tests...", flush=True)
    test_performance_latency_and_throughput()

    print("6. Multi-agent tests...", flush=True)
    test_multi_agent_system_metrics()

    print("7. Dashboard summary...", flush=True)
    test_evaluation_engine_dashboard_summary()

    print("ALL EVALUATION ENGINE TESTS PASSED 100% SUCCESSFULLY!", flush=True)
