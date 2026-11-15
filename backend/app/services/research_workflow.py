from __future__ import annotations
import logging
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.run import ResearchRun
from app.models.document import UploadedDocument
from app.models.evidence import EvidenceRecord
from app.models.report import ResearchReport
from app.providers.llm import LLMProvider, get_llm_provider
from app.providers.web_search import WebSearchProvider, get_search_provider
from app.providers.web_fetcher import is_safe_url, fetch_url
from app.services.evidence_normalizer import (
    NormalizedEvidence, normalize_web_result, normalize_document_chunk, chunk_text
)
from app.services.context_builder import build_evidence_context, build_prompt, SYSTEM_PROMPT
from app.services.report_generator import generate_report

logger = logging.getLogger(__name__)


def _safe_error(exc: Exception) -> str:
    """Convert exception to a safe, non-leaking error message."""
    msg = str(exc)
    # Strip file paths
    msg = re.sub(r"[A-Za-z]:\\[\w\\.\-]+", "<path>", msg)
    msg = re.sub(r"/[\w/.\-]+", "<path>", msg)
    return msg[:500]


async def _extract_documents(
    db: AsyncSession,
    run: ResearchRun,
    research_question: str,
) -> list[NormalizedEvidence]:
    """Stage 2: Process uploaded documents → evidence records."""
    from sqlalchemy import select
    from pypdf import PdfReader
    from pypdf.errors import FileNotDecryptedError
    from docx import Document as DocxDocument
    from io import BytesIO

    docs_result = await db.execute(
        select(UploadedDocument).where(UploadedDocument.run_id == run.id)
    )
    documents = docs_result.scalars().all()
    evidence = []

    for doc in documents:
        try:
            with open(doc.storage_path, "rb") as f:
                file_data = f.read()

            ext = doc.original_filename.rsplit(".", 1)[-1].lower()

            if ext == "pdf":
                try:
                    reader = PdfReader(BytesIO(file_data))
                    pages_text = []
                    for i, page in enumerate(reader.pages):
                        text = page.extract_text() or ""
                        if text.strip():
                            pages_text.append((i + 1, text.strip()))

                    if not pages_text:
                        doc.extraction_status = "failed"
                        doc.extraction_error = "PDF appears to be image-only (no extractable text)."
                        await db.commit()
                        continue

                    full_text = "\n\n".join(t for _, t in pages_text)

                except FileNotDecryptedError:
                    doc.extraction_status = "failed"
                    doc.extraction_error = "PDF is encrypted or password-protected."
                    await db.commit()
                    continue

            elif ext == "docx":
                docx_doc = DocxDocument(BytesIO(file_data))
                paragraphs = [p.text.strip() for p in docx_doc.paragraphs if p.text.strip()]
                full_text = "\n".join(paragraphs)
                if not full_text.strip():
                    doc.extraction_status = "failed"
                    doc.extraction_error = "DOCX contains no extractable text."
                    await db.commit()
                    continue

            elif ext == "txt":
                try:
                    full_text = file_data.decode("utf-8", errors="replace")
                except Exception:
                    doc.extraction_status = "failed"
                    doc.extraction_error = "Could not decode text file."
                    await db.commit()
                    continue
            else:
                doc.extraction_status = "failed"
                doc.extraction_error = f"Unsupported format: {ext}"
                await db.commit()
                continue

            # Chunk the text
            chunks = chunk_text(full_text)
            for chunk_idx, chunk in enumerate(chunks):
                norm = normalize_document_chunk(
                    document_id=doc.id,
                    filename=doc.original_filename,
                    chunk_text=chunk,
                    chunk_index=chunk_idx,
                    page_number=None,
                )
                evidence.append(norm)

            doc.extraction_status = "success"
            await db.commit()

        except Exception as exc:
            logger.warning("Document extraction failed for %s: %s", doc.id, exc)
            doc.extraction_status = "failed"
            doc.extraction_error = _safe_error(exc)
            await db.commit()

    return evidence


async def _web_research(
    run: ResearchRun,
    search_provider: WebSearchProvider,
    research_question: str,
) -> list[NormalizedEvidence]:
    """Stage 3: Web search + URL fetching → evidence records."""
    from app.core.config import settings

    evidence = []
    try:
        results = await search_provider.search(research_question, num_results=settings.SEARCH_MAX_RESULTS)
    except Exception as exc:
        logger.warning("Web search failed: %s", exc)
        return []

    seen_urls: set[str] = set()
    for result in results:
        url = result.url.strip().rstrip("/")
        if url in seen_urls:
            continue
        seen_urls.add(url)

        # If Tavily already provided content, use it directly
        if result.content and len(result.content.strip()) >= 100:
            norm = normalize_web_result(url, result.title, result.content)
            evidence.append(norm)
            continue

        # Otherwise fetch the page
        if not is_safe_url(url):
            logger.info("SSRF: skipping blocked URL %s", url)
        else:
            try:
                title, content = await fetch_url(
                    url,
                    timeout=settings.WEB_FETCH_TIMEOUT_SECONDS,
                    max_content_kb=settings.WEB_FETCH_MAX_CONTENT_KB,
                )
                if content:
                    norm = normalize_web_result(url, title or result.title, content)
                    evidence.append(norm)
                    continue
            except Exception as exc:
                logger.warning("Failed to fetch %s: %s", url, exc)

        # Last resort: use the Tavily snippet — better than dropping the source
        if result.snippet and len(result.snippet.strip()) >= 30:
            norm = normalize_web_result(url, result.title, result.snippet)
            evidence.append(norm)

    return evidence


async def _persist_evidence(
    db: AsyncSession,
    run_id: str,
    evidence_list: list[NormalizedEvidence],
) -> list[str]:
    """Save evidence records to DB. Returns list of persisted IDs."""
    ids: list[str] = []
    for ev in evidence_list:
        record = EvidenceRecord(
            id=str(uuid.uuid4()),
            run_id=run_id,
            source_type=ev.source_type,
            source_label=ev.source_label,
            content=ev.content,
            relevance_score=ev.relevance_score,
            fetch_status="success",
            url=ev.url,
            page_title=ev.page_title,
            retrieved_at=ev.retrieved_at,
            document_id=ev.document_id,
            chunk_index=ev.chunk_index,
            page_number=ev.page_number,
            # Phase 4 M4.3 fields (defaults; enriched after commit)
            evidence_type=ev.evidence_type,
            evidence_relationship=ev.evidence_relationship,
            section_name=ev.section_name,
            extraction_method=ev.extraction_method,
            extraction_confidence=ev.extraction_confidence,
        )
        db.add(record)
        ids.append(record.id)
    await db.commit()
    return ids


async def run_research_workflow(
    run_id: str,
    llm_provider: LLMProvider | None = None,
    search_provider: WebSearchProvider | None = None,
) -> None:
    """
    Top-level research workflow coroutine.
    Providers can be injected for testing; defaults to real providers from settings.
    All exceptions are caught and written to the run record.
    """
    from app.core.config import settings as _settings
    from app.providers.tracked_llm import TrackedLLMProvider

    base_llm = llm_provider or get_llm_provider()
    # Wrap with TrackedLLMProvider for usage tracking (observability only)
    if _settings.ENABLE_LLM_USAGE_TRACKING and not isinstance(base_llm, TrackedLLMProvider):
        llm: LLMProvider = TrackedLLMProvider(
            base_llm, cost_per_1k_tokens=_settings.LLM_COST_PER_1K_TOKENS
        )
    else:
        llm = base_llm

    search = search_provider or get_search_provider()

    async with AsyncSessionLocal() as db:
        try:
            # Stage 1: Initialize
            from sqlalchemy import select
            result = await db.execute(select(ResearchRun).where(ResearchRun.id == run_id))
            run = result.scalar_one_or_none()

            if run is None:
                logger.error("Workflow: run %s not found", run_id)
                return
            if run.status != "pending":
                logger.warning("Workflow: run %s is not pending (status=%s), skipping", run_id, run.status)
                return

            run.status = "running"
            run.current_stage = "Initializing"
            run.started_at = datetime.now(timezone.utc)
            await db.commit()

            all_evidence: list[NormalizedEvidence] = []

            # Stage 2: Document Processing
            if run.use_documents:
                run.current_stage = "Processing documents"
                await db.commit()
                doc_evidence = await _extract_documents(db, run, run.research_question)
                all_evidence.extend(doc_evidence)

                if not doc_evidence and not run.use_web:
                    raise RuntimeError(
                        "All documents failed text extraction and no web search was requested."
                    )

            # Stage 3: Web Research
            web_evidence: list[NormalizedEvidence] = []
            if run.use_web:
                run.current_stage = "Searching the web"
                await db.commit()
                web_evidence = await _web_research(run, search, run.research_question)
                all_evidence.extend(web_evidence)

            # Check: do we have any evidence at all?
            if not all_evidence:
                raise RuntimeError(
                    "No evidence could be collected from any source. "
                    "Web search may have failed and no documents were provided."
                )

            # Stage 4: Collect and score evidence
            run.current_stage = "Collecting evidence"
            await db.commit()

            from app.core.config import settings
            selected_evidence = build_evidence_context(
                all_evidence,
                run.research_question,
                budget_chars=settings.LLM_CONTEXT_BUDGET_CHARS,
            )

            # Persist evidence records
            await _persist_evidence(db, run_id, selected_evidence)

            # Stage 5: Synthesis
            run.current_stage = "Synthesizing findings"
            await db.commit()

            user_prompt = build_prompt(selected_evidence, run.research_question)

            # Stage 6: Generate Report
            run.current_stage = "Generating report"
            await db.commit()

            report_data, raw_llm_response = await generate_report(
                llm=llm,
                research_question=run.research_question,
                evidence_list=selected_evidence,
                user_prompt=user_prompt,
                system_prompt=SYSTEM_PROMPT,
                max_retries=1,
            )

            # Stage 7: Persist and complete
            run.current_stage = "Complete"
            await db.commit()

            report = ResearchReport(
                id=str(uuid.uuid4()),
                run_id=run_id,
                raw_llm_response=raw_llm_response[:10000] if raw_llm_response else None,
                generated_at=datetime.now(timezone.utc),
                **report_data,
            )
            db.add(report)

            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            # Phase 4 M4.7 — write LLM usage totals
            if isinstance(llm, TrackedLLMProvider):
                run.llm_call_count = llm.call_count
                run.total_tokens_used = llm.total_tokens
                run.estimated_cost_usd = llm.estimated_cost_usd
            await db.commit()

            # Phase 4 M4.4 — Claim verification (best-effort; non-fatal)
            try:
                from app.services.claim_verifier import verify_claims_for_run
                from app.core.config import settings

                depth = run.verification_depth or settings.VERIFICATION_DEPTH
                v_summary = await verify_claims_for_run(
                    db=db,
                    run_id=run_id,
                    report_id=report.id,
                    depth=depth,
                    max_claims=settings.MAX_CLAIMS_PER_RUN,
                    llm_provider=llm,
                )
                await db.commit()
                logger.info(
                    "Workflow: claim verification completed — %d claims (run %s)",
                    v_summary.get("total_claims", 0), run_id
                )
            except Exception as verif_exc:
                logger.warning(
                    "Workflow: claim verification failed for run %s: %s", run_id, verif_exc
                )

            # Phase 4 M4.6 — Citation management (best-effort; non-fatal)
            try:
                from app.services.citation_service import create_citations_for_run
                from app.services.citation_validator import validate_citations_for_run

                await create_citations_for_run(db=db, run_id=run_id, report_id=report.id)
                await db.commit()

                val_summary = await validate_citations_for_run(
                    db=db, run_id=run_id, report_id=report.id
                )
                await db.commit()
                logger.info(
                    "Workflow: citation validation completed — %d/%d verified (run %s)",
                    val_summary.get("verified_count", 0),
                    val_summary.get("total_citations", 0),
                    run_id,
                )
            except Exception as cit_exc:
                logger.warning(
                    "Workflow: citation management failed for run %s: %s", run_id, cit_exc
                )

            logger.info("Workflow: run %s completed successfully", run_id)

        except Exception as exc:
            logger.error("Workflow: run %s failed: %s", run_id, exc)
            try:
                run.status = "failed"
                run.error_message = _safe_error(exc)
                run.completed_at = datetime.now(timezone.utc)
                await db.commit()
            except Exception as inner_exc:
                logger.error("Workflow: could not write failure state for run %s: %s", run_id, inner_exc)
