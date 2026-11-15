from __future__ import annotations
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class NormalizedEvidence:
    source_type: str           # "web" or "document"
    content: str
    source_label: str = ""     # assigned later
    relevance_score: float = 0.0
    # Web
    url: str | None = None
    page_title: str | None = None
    retrieved_at: datetime | None = None
    # Document
    document_id: str | None = None
    filename: str | None = None
    chunk_index: int | None = None
    page_number: int | None = None
    # Phase 4 M4.3 — enrichment fields (populated by EvidenceExtractor)
    source_id: str | None = None        # FK to Source record
    chunk_id: str | None = None         # FK to DocumentChunk record
    evidence_type: str = "other"        # statistical/experimental/observational/etc.
    evidence_relationship: str = "neutral"  # supports/contradicts/qualifies/contextualizes/neutral
    section_name: str | None = None     # document section this evidence came from
    extraction_method: str | None = None
    extraction_confidence: float | None = None


def score_relevance(content: str, research_question: str) -> float:
    """Simple token overlap relevance score between 0.0 and 1.0."""
    def tokenize(text: str) -> set[str]:
        return set(re.findall(r"\b\w{4,}\b", text.lower()))

    q_tokens = tokenize(research_question)
    if not q_tokens:
        return 0.0
    c_tokens = tokenize(content)
    overlap = q_tokens & c_tokens
    return min(len(overlap) / len(q_tokens), 1.0)


def normalize_web_result(url: str, title: str | None, content: str) -> NormalizedEvidence:
    return NormalizedEvidence(
        source_type="web",
        content=content,
        url=url,
        page_title=title,
        retrieved_at=datetime.now(timezone.utc),
    )


def normalize_document_chunk(
    document_id: str,
    filename: str,
    chunk_text: str,
    chunk_index: int,
    page_number: int | None = None,
) -> NormalizedEvidence:
    return NormalizedEvidence(
        source_type="document",
        content=chunk_text,
        document_id=document_id,
        filename=filename,
        chunk_index=chunk_index,
        page_number=page_number,
    )


def chunk_text(text: str, chunk_size: int = 8000, overlap: int = 400) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
        if start >= len(text):
            break
    return chunks
