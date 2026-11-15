from __future__ import annotations
import asyncio
import json
import logging
import re

from app.services.evidence_normalizer import NormalizedEvidence
from app.providers.llm import LLMProvider
from app.guardrails.service import guardrails_service

logger = logging.getLogger(__name__)


def _parse_llm_response(raw: str) -> dict:
    """Parse LLM JSON response. Falls back to minimal structure on failure."""
    # Try direct JSON parse
    try:
        parsed = json.loads(raw)
        if _is_template_echo(parsed):
            raise ValueError("LLM returned unfilled template placeholders")
        return parsed
    except (json.JSONDecodeError, ValueError):
        pass

    # Try to extract JSON from code fence
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(1))
            if not _is_template_echo(parsed):
                return parsed
        except json.JSONDecodeError:
            pass

    # Try to find a raw JSON object in the response (LLM may have added preamble)
    obj_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if obj_match:
        try:
            parsed = json.loads(obj_match.group(0))
            if not _is_template_echo(parsed):
                return parsed
        except json.JSONDecodeError:
            pass

    # Fallback: return raw as summary if it looks like real content
    logger.warning("Could not parse LLM response as JSON; using raw text as summary")
    summary = raw.strip()
    # Strip any leading JSON template echo — take only the first 2000 chars
    if summary.startswith("{") or "<write" in summary[:100]:
        summary = "The research report could not be structured. Please review the raw findings."
    return {
        "executive_summary": summary[:2000] if summary else "Research complete.",
        "key_findings": [],
        "observations": None,
        "contradictions": None,
        "limitations": "Report generation produced an unstructured response.",
        "sources_used": [],
    }


def _is_template_echo(parsed: dict) -> bool:
    """Return True if the LLM returned the unfilled template placeholders."""
    summary = parsed.get("executive_summary", "")
    # Detect angle-bracket placeholders like "<write 2-4 sentences..."
    if isinstance(summary, str) and summary.strip().startswith("<"):
        return True
    # Detect the literal schema description text
    if isinstance(summary, str) and "2-4 sentence" in summary:
        return True
    return False


def _build_sources_list(evidence_list: list[NormalizedEvidence]) -> list[dict]:
    sources = []
    for ev in evidence_list:
        if ev.source_type == "web":
            sources.append({
                "type": "web",
                "source_label": ev.source_label,
                "url": ev.url,
                "title": ev.page_title,
                "retrieved_at": ev.retrieved_at.isoformat() if ev.retrieved_at else None,
            })
        else:
            sources.append({
                "type": "document",
                "source_label": ev.source_label,
                "filename": ev.filename,
                "chunk_index": ev.chunk_index,
                "page_number": ev.page_number,
            })
    return sources


def _build_evidence_used(parsed: dict, evidence_list: list[NormalizedEvidence]) -> list[dict]:
    label_map = {ev.source_label: ev for ev in evidence_list}
    used = []
    for label in parsed.get("sources_used", []):
        ev = label_map.get(label)
        if ev:
            entry: dict = {
                "source_label": label,
                "source_type": ev.source_type,
            }
            if ev.source_type == "web":
                entry["url"] = ev.url
                entry["title"] = ev.page_title
                entry["excerpt"] = (ev.content or "")[:200]
            else:
                entry["filename"] = ev.filename
                entry["chunk_index"] = ev.chunk_index
                entry["page_number"] = ev.page_number
                entry["excerpt"] = (ev.content or "")[:200]
            used.append(entry)
    return used


async def generate_report(
    llm: LLMProvider,
    research_question: str,
    evidence_list: list[NormalizedEvidence],
    user_prompt: str,
    system_prompt: str,
    max_retries: int = 1,
) -> tuple[dict, str]:
    """
    Call LLM and build report dict. Returns (report_dict, raw_llm_response).
    Retries once on failure.
    """
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            raw = await llm.complete(system_prompt, user_prompt)
            # Output Guardrails: redact leaked credentials/secrets before parsing
            sanitized_raw, _ = guardrails_service.output.redact_secrets(raw)
            parsed = _parse_llm_response(sanitized_raw)

            exec_summary = parsed.get("executive_summary", "")
            if isinstance(exec_summary, str):
                exec_summary, _ = guardrails_service.output.redact_secrets(exec_summary)

            limitations = parsed.get("limitations", "")
            if isinstance(limitations, str):
                limitations, _ = guardrails_service.output.redact_secrets(limitations)

            report = {
                "research_question": research_question,
                "executive_summary": exec_summary,
                "key_findings": json.dumps(parsed.get("key_findings", [])),
                "evidence_used": json.dumps(_build_evidence_used(parsed, evidence_list)),
                "observations": parsed.get("observations"),
                "contradictions": parsed.get("contradictions"),
                "limitations": limitations,
                "sources": json.dumps(_build_sources_list(evidence_list)),
            }
            return report, sanitized_raw
        except Exception as exc:
            last_error = exc
            logger.warning("LLM call attempt %d failed: %s", attempt + 1, exc)
            if attempt < max_retries:
                await asyncio.sleep(5)

    raise RuntimeError(f"LLM synthesis failed after {max_retries + 1} attempts: {last_error}") from last_error
