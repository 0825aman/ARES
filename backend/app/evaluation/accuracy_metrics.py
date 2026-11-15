"""accuracy_metrics.py — Accuracy and Quality Metrics for LLM evaluation.

Metrics implemented:
- Exact Match (EM): Checks whether generated answer exactly matches reference answer.
- Accuracy: Correctness of categorical/factual predictions.
- Precision: Proportion of generated relevant tokens/elements that are correct.
- Recall: Proportion of reference elements that were successfully generated.
- F1 Score: Harmonic mean of precision and recall.
- Semantic Similarity: Token overlap and cosine vector approximation.
- ROUGE: ROUGE-1, ROUGE-2, and ROUGE-L (LCS) overlap scores.
- BLEU: BLEU-1 through BLEU-4 with geometric mean and brevity penalty.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any


def _normalize_text(text: str) -> str:
    """Normalize text by lowercasing, stripping punctuation, and removing excess whitespace."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def _get_tokens(text: str) -> list[str]:
    """Tokenize normalized text into words."""
    norm = _normalize_text(text)
    return norm.split() if norm else []


def _get_ngrams(tokens: list[str], n: int) -> Counter:
    """Generate n-gram frequency counter from token sequence."""
    if len(tokens) < n:
        return Counter()
    return Counter(tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1))


def exact_match_score(generated: str, reference: str) -> float:
    """Exact Match (EM): Returns 1.0 if normalized strings are identical, else 0.0."""
    return 1.0 if _normalize_text(generated) == _normalize_text(reference) else 0.0


def accuracy_score(predicted: list[Any], truth: list[Any]) -> float:
    """Accuracy: Proportion of predictions that exactly match ground truth items."""
    if not predicted or not truth:
        return 0.0
    total = min(len(predicted), len(truth))
    if total == 0:
        return 0.0
    correct = sum(1 for p, t in zip(predicted[:total], truth[:total]) if p == t)
    return round(correct / total, 4)


def precision_recall_f1(generated: str, reference: str) -> tuple[float, float, float]:
    """Token-level Precision, Recall, and F1 Score."""
    gen_tokens = _get_tokens(generated)
    ref_tokens = _get_tokens(reference)

    if not gen_tokens and not ref_tokens:
        return 1.0, 1.0, 1.0
    if not gen_tokens or not ref_tokens:
        return 0.0, 0.0, 0.0

    gen_counts = Counter(gen_tokens)
    ref_counts = Counter(ref_tokens)

    # Number of overlapping tokens (minimum of counts in both)
    overlap = sum((gen_counts & ref_counts).values())

    precision = overlap / len(gen_tokens)
    recall = overlap / len(ref_tokens)
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return round(precision, 4), round(recall, 4), round(f1, 4)


def semantic_similarity_score(generated: str, reference: str) -> float:
    """Semantic Similarity: Cosine similarity over normalized term-frequency vectors."""
    gen_tokens = _get_tokens(generated)
    ref_tokens = _get_tokens(reference)

    if not gen_tokens and not ref_tokens:
        return 1.0
    if not gen_tokens or not ref_tokens:
        return 0.0

    gen_counts = Counter(gen_tokens)
    ref_counts = Counter(ref_tokens)
    all_words = set(gen_counts.keys()) | set(ref_counts.keys())

    dot_product = sum(gen_counts.get(w, 0) * ref_counts.get(w, 0) for w in all_words)
    norm_gen = math.sqrt(sum(v**2 for v in gen_counts.values()))
    norm_ref = math.sqrt(sum(v**2 for v in ref_counts.values()))

    if norm_gen == 0 or norm_ref == 0:
        return 0.0

    cosine = dot_product / (norm_gen * norm_ref)
    return round(min(1.0, max(0.0, cosine)), 4)


def _lcs_length(x: list[str], y: list[str]) -> int:
    """Compute length of Longest Common Subsequence (LCS)."""
    m, n = len(x), len(y)
    if m == 0 or n == 0:
        return 0
    # Two-row dynamic programming for memory efficiency
    prev = [0] * (n + 1)
    curr = [0] * (n + 1)
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if x[i - 1] == y[j - 1]:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = max(prev[j], curr[j - 1])
        prev, curr = curr, [0] * (n + 1)
    return prev[n]


def rouge_scores(generated: str, reference: str) -> dict[str, float]:
    """Calculate ROUGE-1, ROUGE-2, and ROUGE-L (F1 scores)."""
    gen_tokens = _get_tokens(generated)
    ref_tokens = _get_tokens(reference)

    if not gen_tokens or not ref_tokens:
        return {"rouge_1": 0.0, "rouge_2": 0.0, "rouge_l": 0.0}

    # ROUGE-1 (unigram F1)
    _, _, r1 = precision_recall_f1(generated, reference)

    # ROUGE-2 (bigram F1)
    gen_bigrams = _get_ngrams(gen_tokens, 2)
    ref_bigrams = _get_ngrams(ref_tokens, 2)
    if not gen_bigrams or not ref_bigrams:
        r2 = 0.0
    else:
        overlap2 = sum((gen_bigrams & ref_bigrams).values())
        p2 = overlap2 / len(gen_tokens) - 1 if len(gen_tokens) > 1 else 0
        r2_rec = overlap2 / len(ref_tokens) - 1 if len(ref_tokens) > 1 else 0
        r2 = (2 * p2 * r2_rec) / (p2 + r2_rec) if (p2 + r2_rec) > 0 else 0.0

    # ROUGE-L (Longest Common Subsequence)
    lcs = _lcs_length(gen_tokens, ref_tokens)
    p_lcs = lcs / len(gen_tokens) if len(gen_tokens) > 0 else 0.0
    r_lcs = lcs / len(ref_tokens) if len(ref_tokens) > 0 else 0.0
    r_l = (2 * p_lcs * r_lcs) / (p_lcs + r_lcs) if (p_lcs + r_lcs) > 0 else 0.0

    return {
        "rouge_1": round(r1, 4),
        "rouge_2": round(r2, 4),
        "rouge_l": round(r_l, 4),
    }


def bleu_scores(generated: str, reference: str) -> dict[str, float]:
    """Calculate BLEU-1, BLEU-2, BLEU-3, BLEU-4 with brevity penalty."""
    gen_tokens = _get_tokens(generated)
    ref_tokens = _get_tokens(reference)

    if not gen_tokens or not ref_tokens:
        return {"bleu_1": 0.0, "bleu_2": 0.0, "bleu_3": 0.0, "bleu_4": 0.0}

    # Brevity penalty
    c = len(gen_tokens)
    r = len(ref_tokens)
    bp = 1.0 if c > r else math.exp(1 - (r / c)) if c > 0 else 0.0

    precisions: list[float] = []
    for n in range(1, 5):
        gen_ngrams = _get_ngrams(gen_tokens, n)
        ref_ngrams = _get_ngrams(ref_tokens, n)
        if not gen_ngrams:
            precisions.append(0.0)
            continue
        overlap = sum((gen_ngrams & ref_ngrams).values())
        total_ngrams = max(1, len(gen_tokens) - n + 1)
        precisions.append(overlap / total_ngrams)

    # Cumulative BLEU-1 to BLEU-4
    b1 = bp * precisions[0]
    b2 = bp * math.sqrt(precisions[0] * precisions[1]) if precisions[0] > 0 and precisions[1] > 0 else 0.0
    b3 = (
        bp * (precisions[0] * precisions[1] * precisions[2]) ** (1 / 3)
        if min(precisions[:3]) > 0
        else 0.0
    )
    b4 = (
        bp * (precisions[0] * precisions[1] * precisions[2] * precisions[3]) ** (1 / 4)
        if min(precisions) > 0
        else 0.0
    )

    return {
        "bleu_1": round(b1, 4),
        "bleu_2": round(b2, 4),
        "bleu_3": round(b3, 4),
        "bleu_4": round(b4, 4),
    }
