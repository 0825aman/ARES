"""Tool functions available to the Research Agent.

These are plain async Python functions — NOT LangChain Tool objects.
The Research Agent calls them directly; LangGraph does not manage them.

All three functions return lists of NormalizedEvidence, matching the
same type used by the Phase 2 workflow (research_workflow.py).

SSRF protection:
  - web_search(): delegates to TavilySearchProvider which only returns
    external URLs by design.
  - fetch_web_content(): calls is_safe_url() before fetching; returns None
    if the URL is blocked.
  - get_document_chunks(): reads local DB and local file system only;
    no network calls.
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.providers.web_search import WebSearchProvider
from app.providers.web_fetcher import is_safe_url, fetch_url
from app.services.evidence_normalizer import (
    NormalizedEvidence,
    normalize_web_result,
    normalize_document_chunk,
    chunk_text,
)
from app.guardrails.service import guardrails_service

logger = logging.getLogger(__name__)


async def web_search(
    query: str,
    search_provider: WebSearchProvider,
    num_results: int = 8,
) -> list[NormalizedEvidence]:
    """Execute a web search and return normalised evidence.

    For each result:
    - If Tavily already supplied full content (≥100 chars), use it directly.
    - Otherwise call fetch_web_content() to retrieve the page.

    On provider failure the exception propagates to the caller (research_node),
    which decides whether to continue or fail the task.
    """
    from app.core.config import settings

    # Enforce Tool Execution Guardrail
    policy = guardrails_service.authorize_tool(
        "researcher", "web_search", {"query": query, "num_results": num_results}
    )
    if not policy.is_allowed:
        logger.warning("Guardrail blocked web_search: %s", policy.reason)
        return []

    results = await search_provider.search(query, num_results=num_results)
    evidence: list[NormalizedEvidence] = []
    seen_urls: set[str] = set()

    for result in results:
        url = result.url.strip().rstrip("/")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        # Use raw_content when Tavily supplied it
        if result.content and len(result.content.strip()) >= 100:
            evidence.append(normalize_web_result(url, result.title, result.content))
            continue

        # Try to fetch the full page
        fetched = await fetch_web_content(url, settings)
        if fetched is not None:
            if not fetched.page_title and result.title:
                fetched.page_title = result.title
            evidence.append(fetched)
            continue

        # Last resort: use the Tavily snippet even if short — better than nothing
        if result.snippet and len(result.snippet.strip()) >= 30:
            evidence.append(normalize_web_result(url, result.title, result.snippet))

    return evidence


async def fetch_web_content(
    url: str,
    settings,  # app.core.config.Settings — typed loosely to avoid circular import
) -> NormalizedEvidence | None:
    """Fetch a single URL and return normalised evidence, or None if blocked/failed.

    Returns None when:
    - SSRF guard blocks the URL (private/local address)
    - Fetch times out or returns no content
    """
    # Enforce Tool Execution Guardrail
    policy = guardrails_service.authorize_tool(
        "researcher", "fetch_web_content", {"url": url}
    )
    if not policy.is_allowed:
        logger.warning("Guardrail blocked fetch_web_content: %s", policy.reason)
        return None

    if not is_safe_url(url):
        logger.info("SSRF: blocked URL %s", url)
        return None

    try:
        title, content = await fetch_url(
            url,
            timeout=settings.WEB_FETCH_TIMEOUT_SECONDS,
            max_content_kb=settings.WEB_FETCH_MAX_CONTENT_KB,
        )
    except Exception as exc:
        logger.warning("fetch_web_content: failed to fetch %s: %s", url, exc)
        return None

    if not content:
        return None

    return normalize_web_result(url, title, content)


async def get_document_chunks(
    run_id: str,
    db: AsyncSession,
) -> list[NormalizedEvidence]:
    """Load all uploaded documents for a run and return chunked evidence.

    Reuses the same extraction logic as Phase 2's _extract_documents(),
    but does not check run.use_documents — the Research Agent does that
    before calling this function.

    On per-document extraction failure, the document is skipped with a
    warning (non-fatal); the other documents are still processed.
    """
    from io import BytesIO

    from sqlalchemy import select

    from app.models.document import UploadedDocument

    result = await db.execute(
        select(UploadedDocument).where(UploadedDocument.run_id == run_id)
    )
    documents = result.scalars().all()
    evidence: list[NormalizedEvidence] = []

    for doc in documents:
        try:
            with open(doc.storage_path, "rb") as fh:
                file_data = fh.read()

            ext = doc.original_filename.rsplit(".", 1)[-1].lower()

            if ext == "pdf":
                from pypdf import PdfReader
                from pypdf.errors import FileNotDecryptedError
                try:
                    reader = PdfReader(BytesIO(file_data))
                    pages_text = [
                        page.extract_text() or ""
                        for page in reader.pages
                    ]
                    full_text = "\n\n".join(t.strip() for t in pages_text if t.strip())
                except FileNotDecryptedError:
                    logger.warning("get_document_chunks: encrypted PDF %s", doc.id)
                    continue

            elif ext == "docx":
                from docx import Document as DocxDocument
                docx_doc = DocxDocument(BytesIO(file_data))
                paragraphs = [p.text.strip() for p in docx_doc.paragraphs if p.text.strip()]
                full_text = "\n".join(paragraphs)

            elif ext == "txt":
                full_text = file_data.decode("utf-8", errors="replace")

            else:
                logger.warning("get_document_chunks: unsupported format %s for doc %s", ext, doc.id)
                continue

            if not full_text.strip():
                logger.warning("get_document_chunks: no text in doc %s", doc.id)
                continue

            chunks = chunk_text(full_text)
            for chunk_idx, chunk in enumerate(chunks):
                evidence.append(
                    normalize_document_chunk(
                        document_id=doc.id,
                        filename=doc.original_filename,
                        chunk_text=chunk,
                        chunk_index=chunk_idx,
                        page_number=None,
                    )
                )

        except Exception as exc:
            logger.warning("get_document_chunks: failed for doc %s: %s", doc.id, exc)

    return evidence
