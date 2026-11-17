"""Source service — Phase 4 M4.2.

Creates and queries Source records for a research run.
Implements run-level deduplication by URL and DOI so the same paper
appearing in multiple provider results or research tasks is only stored once.
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source import Source
from app.providers.web_search import SearchResult

logger = logging.getLogger(__name__)


def _content_hash(url: str | None, doi: str | None) -> str:
    """Build a deterministic hash for deduplication.

    Prefer DOI as canonical identifier; fall back to normalised URL.
    """
    if doi:
        key = f"doi:{doi.lower().strip()}"
    elif url:
        key = f"url:{url.lower().strip().rstrip('/')}"
    else:
        key = f"uuid:{uuid.uuid4()}"
    return hashlib.sha256(key.encode()).hexdigest()


async def create_source_from_result(
    db: AsyncSession,
    run_id: str,
    result: SearchResult,
    retrieval_provider: str,
) -> Source:
    """Persist a SearchResult as a Source record.

    Deduplicates within the run: if a Source with the same content_hash already
    exists for this run, the existing record is returned without creating a duplicate.
    """
    content_hash = _content_hash(result.url, result.doi)

    # Run-level dedup check
    existing_result = await db.execute(
        select(Source)
        .where(Source.run_id == run_id)
        .where(Source.content_hash == content_hash)
        .limit(1)
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        return existing

    # Determine source_type
    if retrieval_provider in ("arxiv", "semantic_scholar"):
        source_type = "academic"
    else:
        source_type = "web"

    clean_title = (result.title.replace("\x00", "") if result.title else None)
    clean_url = (result.url.replace("\x00", "") if result.url else None)
    clean_venue = (result.venue.replace("\x00", "") if result.venue else None)
    source = Source(
        id=str(uuid.uuid4()),
        run_id=run_id,
        source_type=source_type,
        title=clean_title,
        url=clean_url,
        doi=result.doi,
        authors=json.dumps(result.authors) if result.authors else None,
        publisher=None,
        venue=clean_venue,
        publication_date=result.published_date,
        is_peer_reviewed=result.is_peer_reviewed,
        retrieval_provider=retrieval_provider,
        retrieved_at=datetime.now(timezone.utc),
        content_hash=content_hash,
        is_accessible=True,
        credibility_notes=None,
        metadata_json=None,
        created_at=datetime.now(timezone.utc),
    )
    db.add(source)
    return source


async def get_sources_for_run(
    db: AsyncSession,
    run_id: str,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[Source], int]:
    """Return paginated list of sources for a run, ordered by creation time."""
    count_result = await db.execute(
        select(func.count(Source.id)).where(Source.run_id == run_id)
    )
    total = count_result.scalar_one()

    items_result = await db.execute(
        select(Source)
        .where(Source.run_id == run_id)
        .order_by(Source.created_at)
        .offset(offset)
        .limit(limit)
    )
    return list(items_result.scalars().all()), total


async def get_source(db: AsyncSession, source_id: str) -> Source | None:
    result = await db.execute(select(Source).where(Source.id == source_id))
    return result.scalar_one_or_none()


async def publish_source_added(source: Source) -> None:
    """Publish a source_added event to all active SSE subscribers for this run.

    Call this AFTER ``db.commit()`` so the record is visible in the DB.
    """
    from app.services.sse_manager import sse_manager

    data = {
        "id": source.id,
        "run_id": source.run_id,
        "source_type": source.source_type,
        "title": source.title,
        "url": source.url,
        "doi": source.doi,
        "authors": source.authors,
        "publisher": source.publisher,
        "venue": source.venue,
        "publication_date": source.publication_date,
        "is_peer_reviewed": source.is_peer_reviewed,
        "retrieval_provider": source.retrieval_provider,
        "created_at": source.created_at.isoformat() if source.created_at else None,
    }
    await sse_manager.publish(source.run_id, "source_added", data)
