"""ARES LLM Agent and Performance Evaluation Framework.

Comprehensive evaluation across 6 critical dimensions:
1. Accuracy and Quality Metrics (EM, Accuracy, Precision, Recall, F1, Semantic Similarity, ROUGE, BLEU)
2. RAG Evaluation Metrics (Context Precision, Recall, Faithfulness, Relevancy, Groundedness)
3. Agentic AI Metrics (Task Completion, Goal Achievement, Tool Accuracy, Planning, Reasoning, Loops)
4. Safety and Guardrail Metrics (Hallucinations, Toxicity, Bias, Injection Resistance, PII Leakage)
5. Performance and Cost Metrics (Latency, TTFT, Tokens/sec, Input/Output Tokens, Cost per Task)
6. Multi-Agent System Evaluation (Swarm efficiency, Supervisor accuracy, Conflict resolution, Agent scorecards)
"""
from __future__ import annotations

from app.evaluation.evaluator import evaluation_engine, LLMEvaluationEngine

__all__ = ["evaluation_engine", "LLMEvaluationEngine"]
