"""Chunk service — Phase 4 M4.1.

CRUD operations for DocumentChunk records.
"""
from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import DocumentChunk

logger = logging.getLogger(__name__)


async def get_chunks_for_document(
    db: AsyncSession,
    document_id: str,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[DocumentChunk], int]:
    """Return a paginated list of chunks for a document, ordered by chunk_index.

    Returns (items, total_count).
    """
    count_result = await db.execute(
        select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == document_id)
    )
    total = count_result.scalar_one()

    items_result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
        .offset(offset)
        .limit(limit)
    )
    return list(items_result.scalars().all()), total


async def get_chunk(db: AsyncSession, chunk_id: str) -> DocumentChunk | None:
    """Return a single chunk by its ID."""
    result = await db.execute(
        select(DocumentChunk).where(DocumentChunk.id == chunk_id)
    )
    return result.scalar_one_or_none()


async def get_chunks_by_document_ids(
    db: AsyncSession,
    document_ids: list[str],
) -> list[DocumentChunk]:
    """Return all chunks for a list of document IDs, ordered by document then index."""
    if not document_ids:
        return []
    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id.in_(document_ids))
        .order_by(DocumentChunk.document_id, DocumentChunk.chunk_index)
    )
    return list(result.scalars().all())
