"""rag_metrics.py — Retrieval-Augmented Generation (RAG) Evaluation Metrics.

Metrics implemented:
- Context Precision: Measures whether retrieved documents are relevant to query.
- Context Recall: Measures whether relevant ground-truth information is retrieved.
- Faithfulness: Checks whether the generated answer is strictly supported by retrieved context.
- Answer Relevancy: Measures how relevant the generated answer is to the user query.
- Context Relevancy: Measures signal-to-noise ratio in retrieved context.
- Groundedness: Measures claim-level verbatim and semantic grounding in source evidence.
"""
from __future__ import annotations

import re
from typing import Any
from app.evaluation.accuracy_metrics import semantic_similarity_score, _get_tokens


def context_precision_score(
    retrieved_contexts: list[str],
    query: str,
    relevant_contexts: list[str] | None = None,
) -> float:
    """Context Precision: Evaluates whether top retrieved chunks are actually relevant.

    If relevant_contexts is provided, computes precision @ K.
    Otherwise, computes semantic relevance score of retrieved chunks to the query.
    """
    if not retrieved_contexts:
        return 0.0

    if relevant_contexts:
        # Match based on token overlap or inclusion
        hits = 0
        precisions = []
        for i, ctx in enumerate(retrieved_contexts):
            is_hit = any(semantic_similarity_score(ctx, rel) > 0.4 for rel in relevant_contexts)
            if is_hit:
                hits += 1
                precisions.append(hits / (i + 1))
        return round(sum(precisions) / len(precisions), 4) if precisions else 0.0

    # Fallback heuristic: query token presence in retrieved contexts
    query_tokens = set(_get_tokens(query))
    if not query_tokens:
        return 1.0

    scores = []
    for ctx in retrieved_contexts:
        ctx_tokens = set(_get_tokens(ctx))
        overlap = len(query_tokens & ctx_tokens) / len(query_tokens)
        scores.append(overlap)

    return round(sum(scores) / len(scores), 4) if scores else 0.0


def context_recall_score(
    retrieved_contexts: list[str],
    ground_truth_statements: list[str],
) -> float:
    """Context Recall: Measures fraction of ground-truth statements found in retrieved context."""
    if not ground_truth_statements:
        return 1.0
    if not retrieved_contexts:
        return 0.0

    combined_context = " ".join(retrieved_contexts)
    recalled = 0

    for stmt in ground_truth_statements:
        sim = semantic_similarity_score(stmt, combined_context)
        if sim > 0.25:  # Ground truth statement is present in context
            recalled += 1

    return round(recalled / len(ground_truth_statements), 4)


STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "because", "as", "what",
    "which", "this", "that", "these", "those", "then", "just", "so", "than",
    "such", "both", "through", "about", "for", "is", "of", "while", "during",
    "to", "from", "in", "out", "on", "off", "again", "further", "then", "once",
    "here", "there", "when", "where", "why", "how", "all", "any", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "can", "will", "just",
    "don", "should", "now", "was", "were", "been", "being", "have", "has",
    "had", "do", "does", "did", "doing", "by", "at", "with"
}


def faithfulness_score(
    answer: str,
    retrieved_contexts: list[str],
    claims: list[dict[str, Any]] | None = None,
) -> float:
    """Faithfulness: Proportion of statements in generated answer supported by context.

    If verified claims are supplied, calculates ratio of verified claims to total claims.
    Otherwise, evaluates informative token overlap between answer statements and context.
    """
    if not answer or not retrieved_contexts:
        return 0.0

    if claims:
        total = len(claims)
        if total == 0:
            return 1.0
        supported = sum(1 for c in claims if c.get("verification_status") == "verified")
        return round(supported / total, 4)

    # Informative token grounding heuristic
    combined_context = " ".join(retrieved_contexts).lower()
    ctx_tokens = set(_get_tokens(combined_context)) - STOPWORDS
    if not ctx_tokens:
        return 0.5

    ans_tokens = set(_get_tokens(answer.lower())) - STOPWORDS
    if not ans_tokens:
        return 1.0

    overlap = len(ans_tokens & ctx_tokens)
    return round(overlap / len(ans_tokens), 4)


def answer_relevancy_score(query: str, answer: str) -> float:
    """Answer Relevancy: Evaluates how directly the answer addresses the query."""
    if not query or not answer:
        return 0.0
    return semantic_similarity_score(query, answer)


def context_relevancy_score(query: str, retrieved_contexts: list[str]) -> float:
    """Context Relevancy: Proportion of retrieved context sentences that are relevant to query."""
    if not retrieved_contexts or not query:
        return 0.0

    total_sentences = 0
    relevant_sentences = 0

    for ctx in retrieved_contexts:
        sentences = [s.strip() for s in re.split(r"[.!?]+", ctx) if len(s.strip()) > 10]
        for s in sentences:
            total_sentences += 1
            if semantic_similarity_score(query, s) > 0.15:
                relevant_sentences += 1

    if total_sentences == 0:
        return 0.0
    return round(relevant_sentences / total_sentences, 4)


def groundedness_score(
    claims: list[dict[str, Any]],
    citations: list[dict[str, Any]],
) -> float:
    """Groundedness: Ratio of claims with verified evidence citations to total claims."""
    if not claims:
        return 1.0

    cited_claim_ids = {c.get("claim_id") for c in citations if c.get("claim_id") and c.get("is_verified", True)}
    grounded = sum(1 for c in claims if c.get("id") in cited_claim_ids or c.get("evidence_count", 0) > 0)
    return round(grounded / len(claims), 4)
