"""Phase 4 Evaluation Metrics — M4.9.

Computes measurable Phase 4 quality metrics on 5 pre-written evaluation
fixtures (deterministic JSON — no LLM calls, no network requests, no DB).

Metrics measured:
  - Evidence coverage      : % of claims that have ≥1 supporting evidence item
  - Citation correctness   : % of citations with is_verified=True
  - Unsupported claim rate : count (and %) of claims with insufficient_evidence status
  - Contradiction detection: % of pre-labeled contradicted claims correctly expected to be 'contradicted'
  - Forced-approval absence: confirms no fixture has forced_approval=True

Targets (from roadmap §M4.9):
  - Evidence coverage ≥ 80% across all fixtures
  - Citation correctness: each fixture must report correctly on its own verified/unverified split
  - Forced-approval absence: 0 occurrences

Evaluation limitations (documented):
  - All evaluation is fixture-based; real-world LLM outputs vary
  - 5 fixtures are not statistically representative of all research domains
  - "Expected" statuses are human-assigned ground truth on a narrow corpus

Test IDs (EM-prefix):
  EM-01: All 5 fixture files load and parse correctly
  EM-02: Evidence coverage ≥ 80% on fixture 1 (fully supported)
  EM-03: Evidence coverage = 50% on fixture 3 (two claims without evidence)
  EM-04: Evidence coverage = 75% on fixture 4 (mixed)
  EM-05: Aggregate evidence coverage ≥ 80% across all 5 fixtures
  EM-06: Citation verified rate = 100% on fixture 1
  EM-07: Citation verified rate = 75% on fixture 5 (one unverified citation)
  EM-08: Citation verified rate = 100% on fixtures 2, 3, 4
  EM-09: Unsupported claim count = 0 on fixture 1 (all supported)
  EM-10: Unsupported claim count = 2 on fixture 3 (insufficient evidence)
  EM-11: Unsupported claim count = 1 on fixture 4 (one insufficient)
  EM-12: Contradiction detection: fixture 2 has 1 labeled contradiction
  EM-13: Contradiction detection: fixture 4 has 1 labeled contradiction
  EM-14: Forced-approval absence: all 5 fixtures have forced_approval=False
  EM-15: claim_verifier VALID_STATUSES covers all expected status values in fixtures
  EM-16: API layer - GET /runs/{run_id}/claims returns correct count via in-memory DB
  EM-17: API layer - GET /runs/{run_id}/citations returns correct count via in-memory DB
  EM-18: format_apa produces non-empty string for well-formed fixture citation data
  EM-19: APA format for fixture-01 source 1 includes title and year
  EM-20: format_ieee produces non-empty string for well-formed fixture citation data
"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio

# ── Fixture loading helpers ────────────────────────────────────────────────────

FIXTURES_DIR = Path(__file__).parent / "evaluation_fixtures"

FIXTURE_FILES = [
    "fixture_01_climate_change.json",
    "fixture_02_contradictions.json",
    "fixture_03_insufficient_evidence.json",
    "fixture_04_mixed.json",
    "fixture_05_citation_validation.json",
]


def load_fixture(filename: str) -> dict[str, Any]:
    path = FIXTURES_DIR / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_all_fixtures() -> list[dict[str, Any]]:
    return [load_fixture(f) for f in FIXTURE_FILES]


# ── Metric computation helpers ─────────────────────────────────────────────────

def compute_evidence_coverage(fixture: dict[str, Any]) -> float:
    """Fraction of claims that have ≥1 associated evidence ID (supporting OR contradicting).

    A contradicted claim with contradicting_evidence_ids counts as 'covered' because
    evidence was collected — the verifier simply found the claim to be incorrect.
    Only claims with no evidence IDs at all (insufficient_evidence) are uncovered.
    """
    claims = fixture["claims"]
    if not claims:
        return 0.0
    covered = sum(
        1 for c in claims
        if c.get("expected_supporting_evidence_ids") or c.get("expected_contradicting_evidence_ids")
    )
    return covered / len(claims)


def compute_citation_verified_rate(fixture: dict[str, Any]) -> float:
    """Fraction of citations with is_verified=True."""
    citations = fixture.get("citations", [])
    if not citations:
        return 1.0  # vacuously 100% if no citations
    verified = sum(1 for c in citations if c.get("is_verified", False))
    return verified / len(citations)


def compute_unsupported_claim_count(fixture: dict[str, Any]) -> int:
    """Count claims whose expected_status is 'insufficient_evidence'."""
    return sum(
        1 for c in fixture["claims"]
        if c.get("expected_status") == "insufficient_evidence"
    )


def compute_contradiction_count(fixture: dict[str, Any]) -> int:
    """Count claims whose expected_status is 'contradicted'."""
    return sum(
        1 for c in fixture["claims"]
        if c.get("expected_status") == "contradicted"
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EM-01: All fixture files load and parse correctly
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_em01_all_fixtures_load():
    """All 5 evaluation fixture files exist and parse as valid JSON."""
    fixtures = load_all_fixtures()
    assert len(fixtures) == 5
    for i, fx in enumerate(fixtures):
        assert "claims" in fx, f"Fixture {i+1} missing 'claims'"
        assert "citations" in fx, f"Fixture {i+1} missing 'citations'"
        assert "evidence" in fx, f"Fixture {i+1} missing 'evidence'"
        assert "expected_metrics" in fx, f"Fixture {i+1} missing 'expected_metrics'"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EM-02 to EM-04: Per-fixture evidence coverage
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_em02_fixture1_evidence_coverage_100():
    """Fixture 1 (climate change): all 4 claims have supporting evidence → 100%."""
    fx = load_fixture("fixture_01_climate_change.json")
    cov = compute_evidence_coverage(fx)
    assert cov == pytest.approx(1.0)
    assert fx["expected_metrics"]["evidence_coverage"] == pytest.approx(cov)


def test_em03_fixture3_evidence_coverage_50():
    """Fixture 3 (remote work): 2 of 4 claims have evidence → 50%."""
    fx = load_fixture("fixture_03_insufficient_evidence.json")
    cov = compute_evidence_coverage(fx)
    assert cov == pytest.approx(0.5)
    assert fx["expected_metrics"]["evidence_coverage"] == pytest.approx(cov)


def test_em04_fixture4_evidence_coverage_75():
    """Fixture 4 (LLM diagnosis): 3 of 4 claims have supporting evidence → 75%."""
    fx = load_fixture("fixture_04_mixed.json")
    cov = compute_evidence_coverage(fx)
    assert cov == pytest.approx(0.75)
    assert fx["expected_metrics"]["evidence_coverage"] == pytest.approx(cov)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EM-05: Aggregate evidence coverage across all fixtures ≥ 80%
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_em05_aggregate_evidence_coverage_gte_80():
    """Aggregate evidence coverage across all 5 fixtures must be ≥ 80%.

    A claim is 'covered' if it has ≥1 supporting OR contradicting evidence ID.
    Claims with insufficient_evidence (no evidence IDs at all) are uncovered.
    """
    fixtures = load_all_fixtures()
    total_claims = sum(len(fx["claims"]) for fx in fixtures)
    covered_claims = sum(
        sum(
            1 for c in fx["claims"]
            if c.get("expected_supporting_evidence_ids")
            or c.get("expected_contradicting_evidence_ids")
        )
        for fx in fixtures
    )
    aggregate = covered_claims / total_claims
    assert aggregate >= 0.80, (
        f"Aggregate evidence coverage {aggregate:.1%} < 80% "
        f"({covered_claims}/{total_claims} claims covered)"
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EM-06 to EM-08: Citation verified rates
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_em06_fixture1_citations_all_verified():
    """Fixture 1: all 4 citations have is_verified=True."""
    fx = load_fixture("fixture_01_climate_change.json")
    rate = compute_citation_verified_rate(fx)
    assert rate == pytest.approx(1.0)
    assert fx["expected_metrics"]["citation_verified_rate"] == pytest.approx(rate)


def test_em07_fixture5_citation_verified_rate_75():
    """Fixture 5 (exercise/CV): 3 of 4 citations verified → 75%."""
    fx = load_fixture("fixture_05_citation_validation.json")
    rate = compute_citation_verified_rate(fx)
    assert rate == pytest.approx(0.75)
    assert fx["expected_metrics"]["citation_verified_rate"] == pytest.approx(rate)


def test_em08_fixtures_2_3_4_citations_all_verified():
    """Fixtures 2, 3, 4: all citations are verified (100% each)."""
    for filename in [
        "fixture_02_contradictions.json",
        "fixture_03_insufficient_evidence.json",
        "fixture_04_mixed.json",
    ]:
        fx = load_fixture(filename)
        rate = compute_citation_verified_rate(fx)
        assert rate == pytest.approx(1.0), (
            f"{filename}: expected 100% citation verification, got {rate:.1%}"
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EM-09 to EM-11: Unsupported claim counts
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_em09_fixture1_no_unsupported_claims():
    """Fixture 1: zero claims have insufficient_evidence status."""
    fx = load_fixture("fixture_01_climate_change.json")
    count = compute_unsupported_claim_count(fx)
    assert count == 0
    assert fx["expected_metrics"]["unsupported_claim_count"] == 0


def test_em10_fixture3_two_unsupported_claims():
    """Fixture 3: exactly 2 claims have insufficient_evidence status."""
    fx = load_fixture("fixture_03_insufficient_evidence.json")
    count = compute_unsupported_claim_count(fx)
    assert count == 2
    assert fx["expected_metrics"]["unsupported_claim_count"] == 2


def test_em11_fixture4_one_unsupported_claim():
    """Fixture 4: exactly 1 claim has insufficient_evidence status."""
    fx = load_fixture("fixture_04_mixed.json")
    count = compute_unsupported_claim_count(fx)
    assert count == 1
    assert fx["expected_metrics"]["unsupported_claim_count"] == 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EM-12 to EM-13: Contradiction detection on labeled fixtures
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_em12_fixture2_one_contradiction():
    """Fixture 2 (IF study): 1 labeled contradiction — overclaiming 'all benefit eliminated'."""
    fx = load_fixture("fixture_02_contradictions.json")
    count = compute_contradiction_count(fx)
    assert count == 1
    assert fx["expected_metrics"]["contradiction_count"] == 1

    contradicted_claims = [
        c["id"] for c in fx["claims"]
        if c.get("expected_status") == "contradicted"
    ]
    expected_labeled = fx["expected_metrics"]["_labeled_contradictions"]
    assert set(contradicted_claims) == set(expected_labeled)


def test_em13_fixture4_one_contradiction():
    """Fixture 4 (LLM diagnosis): 1 labeled contradiction — 'outperform in all specialties'."""
    fx = load_fixture("fixture_04_mixed.json")
    count = compute_contradiction_count(fx)
    assert count == 1
    assert fx["expected_metrics"]["contradiction_count"] == 1

    contradicted_claims = [
        c["id"] for c in fx["claims"]
        if c.get("expected_status") == "contradicted"
    ]
    expected_labeled = fx["expected_metrics"]["_labeled_contradictions"]
    assert set(contradicted_claims) == set(expected_labeled)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EM-14: Forced-approval absence across all fixtures
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_em14_no_forced_approvals_across_all_fixtures():
    """All 5 fixtures have forced_approval=False in expected_metrics.

    Invariant: the Critic cycle limit must NEVER force approval.
    """
    fixtures = load_all_fixtures()
    for i, fx in enumerate(fixtures):
        forced = fx["expected_metrics"].get("forced_approval", True)
        assert forced is False, (
            f"Fixture {i+1} ({fx['run_id']}) has forced_approval={forced!r}. "
            "This violates the Phase 4 invariant: cycle limit must never force approval."
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EM-15: claim_verifier VALID_STATUSES covers all expected statuses in fixtures
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_em15_valid_statuses_cover_all_fixture_statuses():
    """claim_verifier.VALID_STATUSES includes every expected_status found across fixtures."""
    from app.services.claim_verifier import VALID_STATUSES

    fixtures = load_all_fixtures()
    all_expected = {
        c["expected_status"]
        for fx in fixtures
        for c in fx["claims"]
        if "expected_status" in c
    }

    for status in all_expected:
        assert status in VALID_STATUSES, (
            f"Expected status '{status}' from fixtures not in claim_verifier.VALID_STATUSES. "
            f"VALID_STATUSES = {sorted(VALID_STATUSES)}"
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EM-16: API layer — GET /runs/{run_id}/claims
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@pytest.mark.asyncio
async def test_em16_claims_api_returns_correct_count(async_client, db_session):
    """GET /runs/{run_id}/claims returns correct count after inserting 3 Claim rows."""
    from app.models.project import ResearchProject
    from app.models.run import ResearchRun
    from app.models.claim import Claim

    project_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())

    project = ResearchProject(
        id=project_id, title="Eval Test", research_question="Test?", status="in_progress"
    )
    run = ResearchRun(
        id=run_id, project_id=project_id, research_question="Test?",
        status="completed", verification_depth="basic",
    )
    db_session.add_all([project, run])

    for i in range(3):
        db_session.add(Claim(
            run_id=run_id,
            claim_text=f"Evaluation claim {i+1}.",
            claim_type="factual",
            originating_section="key_findings",
            is_high_impact=(i == 0),
        ))
    await db_session.commit()

    response = await async_client.get(
        f"/api/v1/projects/{project_id}/runs/{run_id}/claims"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EM-17: API layer — GET /runs/{run_id}/citations
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@pytest.mark.asyncio
async def test_em17_citations_api_returns_correct_count(async_client, db_session):
    """GET /runs/{run_id}/citations returns correct total and verified_count."""
    from app.models.project import ResearchProject
    from app.models.run import ResearchRun
    from app.models.report import ResearchReport
    from app.models.evidence import EvidenceRecord
    from app.models.citation import Citation

    project_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    report_id = str(uuid.uuid4())

    project = ResearchProject(
        id=project_id, title="Citation Eval", research_question="Cite?", status="completed"
    )
    run = ResearchRun(
        id=run_id, project_id=project_id, research_question="Cite?",
        status="completed", verification_depth="basic",
    )
    report = ResearchReport(
        id=report_id, run_id=run_id,
        research_question="Cite?",
        executive_summary="Summary.",
        key_findings="[]",
        evidence_used="[]",
        limitations="None.",
        sources="[]",
    )
    db_session.add_all([project, run, report])

    # 3 evidence records — assign explicit IDs so they are available before flush
    ev_ids = [str(uuid.uuid4()) for _ in range(3)]
    for i, ev_id in enumerate(ev_ids):
        db_session.add(EvidenceRecord(
            id=ev_id,
            run_id=run_id, source_type="web",
            source_label=f"[SOURCE {i+1}]",
            fetch_status="success",
            relevance_score=0.9,
        ))

    await db_session.flush()

    # 3 citations: 2 verified, 1 unverified
    for i, ev_id in enumerate(ev_ids):
        db_session.add(Citation(
            run_id=run_id,
            report_id=report_id,
            evidence_id=ev_id,
            citation_key=f"[SOURCE {i+1}]",
            is_verified=(i < 2),
            apa_formatted=f"Author {i+1}. (2023). Title {i+1}.",
        ))
    await db_session.commit()

    response = await async_client.get(
        f"/api/v1/projects/{project_id}/runs/{run_id}/citations"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert data["verified_count"] == 2
    assert len(data["citations"]) == 3


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EM-18 to EM-20: Deterministic citation formatting
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_em18_format_apa_nonempty_for_well_formed_input():
    """format_apa produces a non-empty citation string for well-formed input."""
    from app.services.citation_service import format_apa

    result = format_apa(
        title="Capabilities of GPT-4 on Medical Challenge Problems",
        authors=["Nori, H.", "King, N.", "McKinney, S. M."],
        year="2023",
        venue="arXiv preprint",
        publisher=None,
        doi="10.48550/arXiv.2303.13375",
        url=None,
    )
    assert isinstance(result, str)
    assert len(result) > 10
    assert "GPT-4" in result or "Nori" in result


def test_em19_format_apa_includes_title_and_year():
    """format_apa output contains the title year for fixture-01 source data."""
    from app.services.citation_service import format_apa

    result = format_apa(
        title="State of the Global Climate 2020",
        authors=[],
        year="2020",
        venue="WMO",
        publisher=None,
        doi=None,
        url="https://library.wmo.int/doc_num.php?explnum_id=10618",
    )
    assert "2020" in result
    assert "State of the Global Climate" in result


def test_em20_format_ieee_nonempty_for_well_formed_input():
    """format_ieee produces a non-empty citation string for well-formed input."""
    from app.services.citation_service import format_ieee

    result = format_ieee(
        title="Climate Change 2022: Mitigation of Climate Change",
        authors=["IPCC"],
        year="2022",
        venue="IPCC AR6 Working Group III",
        publisher=None,
        doi=None,
        url="https://www.ipcc.ch/report/ar6/wg3/",
    )
    assert isinstance(result, str)
    assert len(result) > 10
