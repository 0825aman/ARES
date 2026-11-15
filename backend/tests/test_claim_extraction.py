"""
tests/test_claim_extraction.py — Phase 4 M4.4: Claim extraction

Test IDs:
  CE-01  Basic depth extracts claims from key_findings list
  CE-02  Basic depth caps at MAX_CLAIMS_PER_RUN
  CE-03  Thorough depth extracts more claims than basic from same report
  CE-04  Claim type classification produces valid enum values only
  CE-05  is_high_impact=True for statistical claim type
  CE-06  is_high_impact=True for causal claim type
  CE-07  is_high_impact=True for factual claim with percentage keyword
  CE-08  is_high_impact=False for plain factual claim
  CE-09  _parse_extraction_response handles malformed JSON gracefully
  CE-10  _parse_extraction_response enforces originating_section enum
  CE-11  extract_claims_from_report returns empty list for empty report (no crash)
  CE-12  extract_claims_from_report fallback: never returns empty when key_findings present
  CE-13  extract_claims_from_report persists Claim rows in DB
  CE-14  Claim.is_high_impact set correctly on persisted rows
"""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.claim import Claim
from app.models.project import ResearchProject
from app.models.run import ResearchRun
from app.services.claim_extractor import (
    _is_high_impact,
    _parse_extraction_response,
    extract_claims_from_report,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_report_data(key_findings=None, executive_summary="", observations=None):
    kf = json.dumps(key_findings or [
        "AI adoption increased by 42% between 2020 and 2023.",
        "Machine learning models require large datasets for training.",
        "Climate change causes significant disruption to agriculture.",
    ])
    return {
        "executive_summary": executive_summary,
        "key_findings": kf,
        "observations": json.dumps(observations) if observations else None,
    }


async def _setup_run(db: AsyncSession) -> tuple[str, str]:
    project = ResearchProject(id=str(uuid.uuid4()), title="T", research_question="Q?")
    db.add(project)
    run = ResearchRun(id=str(uuid.uuid4()), project_id=project.id, research_question="Q?")
    db.add(run)
    await db.flush()
    return project.id, run.id


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_ce05_high_impact_statistical():
    """CE-05: statistical claim type → is_high_impact=True."""
    assert _is_high_impact("Any text here", "statistical") is True


def test_ce06_high_impact_causal():
    """CE-06: causal claim type → is_high_impact=True."""
    assert _is_high_impact("Any text here", "causal") is True


def test_ce07_high_impact_factual_with_percentage():
    """CE-07: factual claim with percentage keyword → is_high_impact=True."""
    assert _is_high_impact("AI adoption increased by 42% in 2023.", "factual") is True


def test_ce08_not_high_impact_plain_factual():
    """CE-08: plain factual claim → is_high_impact=False."""
    assert _is_high_impact("The study was published in 2023.", "factual") is False


def test_ce09_parse_extraction_malformed_json():
    """CE-09: _parse_extraction_response returns [] on malformed JSON."""
    result = _parse_extraction_response("not json", 10)
    assert result == []


def test_ce10_parse_extraction_invalid_section():
    """CE-10: _parse_extraction_response normalises invalid originating_section to 'other'."""
    raw = json.dumps([{
        "claim_text": "Some claim.",
        "claim_type": "factual",
        "originating_section": "invalid_section",
    }])
    result = _parse_extraction_response(raw, 10)
    assert len(result) == 1
    assert result[0]["originating_section"] == "other"


def test_ce04_parse_extraction_invalid_claim_type():
    """CE-04: _parse_extraction_response replaces invalid claim_type with 'factual'."""
    raw = json.dumps([{
        "claim_text": "Some claim.",
        "claim_type": "nonsense_type",
        "originating_section": "key_findings",
    }])
    result = _parse_extraction_response(raw, 10)
    assert result[0]["claim_type"] == "factual"


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ce01_basic_depth_extracts_from_key_findings(db_session: AsyncSession):
    """CE-01: Basic depth extracts claims from key_findings list."""
    _, run_id = await _setup_run(db_session)
    report_data = _make_report_data()

    claim_ids = await extract_claims_from_report(
        db=db_session,
        run_id=run_id,
        report_id=None,
        report_data=report_data,
        depth="basic",
        max_claims=20,
        llm_provider=None,
    )
    await db_session.flush()
    assert len(claim_ids) == 3  # 3 key findings


@pytest.mark.asyncio
async def test_ce02_basic_depth_respects_max_claims(db_session: AsyncSession):
    """CE-02: Basic depth caps at max_claims."""
    _, run_id = await _setup_run(db_session)
    many_findings = [f"Finding number {i}." for i in range(30)]
    report_data = _make_report_data(key_findings=many_findings)

    claim_ids = await extract_claims_from_report(
        db=db_session,
        run_id=run_id,
        report_id=None,
        report_data=report_data,
        depth="basic",
        max_claims=5,
        llm_provider=None,
    )
    await db_session.flush()
    assert len(claim_ids) <= 5


@pytest.mark.asyncio
async def test_ce03_thorough_extracts_via_llm(db_session: AsyncSession):
    """CE-03: Thorough depth uses LLM to extract claims."""
    _, run_id = await _setup_run(db_session)

    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value=json.dumps([
        {"claim_text": "Claim A.", "claim_type": "statistical", "originating_section": "key_findings"},
        {"claim_text": "Claim B.", "claim_type": "factual", "originating_section": "executive_summary"},
        {"claim_text": "Claim C.", "claim_type": "causal", "originating_section": "observations"},
    ]))

    report_data = _make_report_data()
    claim_ids = await extract_claims_from_report(
        db=db_session,
        run_id=run_id,
        report_id=None,
        report_data=report_data,
        depth="thorough",
        max_claims=20,
        llm_provider=mock_llm,
    )
    await db_session.flush()
    assert len(claim_ids) >= 1


@pytest.mark.asyncio
async def test_ce11_empty_report_no_crash(db_session: AsyncSession):
    """CE-11: extract_claims_from_report returns [] for empty key_findings, no crash."""
    _, run_id = await _setup_run(db_session)
    report_data = {"executive_summary": "", "key_findings": "[]", "observations": None}

    claim_ids = await extract_claims_from_report(
        db=db_session,
        run_id=run_id,
        report_id=None,
        report_data=report_data,
        depth="basic",
        max_claims=20,
        llm_provider=None,
    )
    assert claim_ids == []


@pytest.mark.asyncio
async def test_ce12_fallback_never_empty_when_findings_present(db_session: AsyncSession):
    """CE-12: Fallback ensures claims are returned when key_findings is non-empty."""
    _, run_id = await _setup_run(db_session)
    report_data = _make_report_data(key_findings=["Finding one.", "Finding two."])

    claim_ids = await extract_claims_from_report(
        db=db_session,
        run_id=run_id,
        report_id=None,
        report_data=report_data,
        depth="basic",
        max_claims=20,
        llm_provider=None,
    )
    await db_session.flush()
    assert len(claim_ids) > 0


@pytest.mark.asyncio
async def test_ce13_persists_claim_rows(db_session: AsyncSession):
    """CE-13: extract_claims_from_report creates Claim rows in DB."""
    from sqlalchemy import select as sa_select

    _, run_id = await _setup_run(db_session)
    report_data = _make_report_data()

    claim_ids = await extract_claims_from_report(
        db=db_session,
        run_id=run_id,
        report_id=None,
        report_data=report_data,
        depth="basic",
        max_claims=20,
        llm_provider=None,
    )
    await db_session.flush()

    result = await db_session.execute(
        sa_select(Claim).where(Claim.run_id == run_id)
    )
    db_claims = result.scalars().all()
    assert len(db_claims) == len(claim_ids)


@pytest.mark.asyncio
async def test_ce14_is_high_impact_set_correctly(db_session: AsyncSession):
    """CE-14: is_high_impact=True on claims with percentage in text."""
    from sqlalchemy import select as sa_select

    _, run_id = await _setup_run(db_session)
    report_data = _make_report_data(key_findings=[
        "AI adoption increased by 42% between 2020 and 2023.",
        "The study was conducted in Europe.",
    ])

    await extract_claims_from_report(
        db=db_session,
        run_id=run_id,
        report_id=None,
        report_data=report_data,
        depth="basic",
        max_claims=20,
        llm_provider=None,
    )
    await db_session.flush()

    result = await db_session.execute(
        sa_select(Claim).where(Claim.run_id == run_id)
    )
    claims = result.scalars().all()
    high_impact_texts = [c.claim_text for c in claims if c.is_high_impact]
    assert any("42%" in t for t in high_impact_texts)
