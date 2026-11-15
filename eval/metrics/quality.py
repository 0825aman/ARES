"""quality.py — Research quality and verification metrics."""
from __future__ import annotations
from typing import Any


def citation_completeness_rate(citations: list[dict[str, Any]], claims: list[dict[str, Any]]) -> float:
    """Return proportion of claims that possess at least one citation."""
    if not claims:
        return 0.0
    cited_claim_ids = {c.get("claim_id") for c in citations if c.get("claim_id")}
    covered = sum(1 for claim in claims if claim.get("id") in cited_claim_ids)
    return round(covered / len(claims), 4)


def evidence_linkage_rate(claims: list[dict[str, Any]]) -> float:
    """Return proportion of claims that are linked to supporting evidence."""
    if not claims:
        return 0.0
    linked = sum(1 for c in claims if (c.get("evidence_count", 0) > 0 or bool(c.get("evidence_ids"))))
    return round(linked / len(claims), 4)


def duplicate_source_rate(sources: list[dict[str, Any]]) -> float:
    """Return proportion of duplicated source URLs."""
    if not sources:
        return 0.0
    urls = [s.get("url", "").strip().lower() for s in sources if s.get("url")]
    if not urls:
        return 0.0
    unique_urls = set(urls)
    duplicate_count = len(urls) - len(unique_urls)
    return round(duplicate_count / len(urls), 4)


def empty_report_section_rate(reports: list[dict[str, Any]], min_chars: int = 100) -> float:
    """Return proportion of standard report sections that are empty or below minimum character threshold."""
    if not reports:
        return 0.0
    total_sections = 0
    empty_sections = 0
    section_keys = ["executive_summary", "key_findings", "observations"]

    for rep in reports:
        for k in section_keys:
            total_sections += 1
            content = rep.get(k)
            if not content:
                empty_sections += 1
            elif isinstance(content, str) and len(content.strip()) < min_chars:
                empty_sections += 1
            elif isinstance(content, list) and len(content) == 0:
                empty_sections += 1

    if total_sections == 0:
        return 0.0
    return round(empty_sections / total_sections, 4)
