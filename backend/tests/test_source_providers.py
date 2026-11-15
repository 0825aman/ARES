"""
tests/test_source_providers.py — Phase 4 M4.2: Multi-Provider Source Collection

Test IDs:
  SP-01  ArXivSearchProvider parses valid Atom XML into SearchResult objects
  SP-02  arXiv results always have is_peer_reviewed=False
  SP-03  arXiv results include doi when <arxiv:doi> present in XML
  SP-04  arXiv results include authors list
  SP-05  arXiv results include venue when <arxiv:journal_ref> present
  SP-06  ArXivSearchProvider returns [] on HTTP error (graceful degradation)
  SP-07  ArXivSearchProvider returns [] on malformed XML
  SP-08  SemanticScholarProvider returns [] when rate-limited (429)
  SP-09  SemanticScholarProvider parses valid JSON response into SearchResult objects
  SP-10  SemanticScholarProvider returns [] on connection error (graceful degradation)
  SP-11  MultiProviderSearch deduplicates by URL across providers
  SP-12  MultiProviderSearch deduplicates by DOI across providers
  SP-13  MultiProviderSearch returns combined results when no duplicates
  SP-14  source_service creates Source row for a SearchResult
  SP-15  source_service deduplicates by URL within same run
  SP-16  source_service deduplicates by DOI within same run
  SP-17  source_service creates separate Source rows for different runs
  SP-18  GET /runs/{run_id}/sources → 200 with correct total
  SP-19  GET /runs/{run_id}/sources → 200 with empty list when no sources
  SP-20  GET /runs/{run_id}/sources → 404 for non-existent run
  SP-21  SourceResponse deserializes authors JSON TEXT → list[str]
  SP-22  get_search_provider returns MultiProviderSearch when ARXIV_ENABLED=True
  SP-23  get_search_provider returns single TavilySearchProvider when only Tavily configured
"""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.providers.web_search import (
    ArXivSearchProvider,
    MultiProviderSearch,
    SearchResult,
    SemanticScholarProvider,
    TavilySearchProvider,
    _dedup_key,
)
from app.services.source_service import create_source_from_result, get_sources_for_run


# ---------------------------------------------------------------------------
# Sample arXiv Atom XML fixture
# ---------------------------------------------------------------------------

_ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2301.00001v1</id>
    <title>  A Test Paper on Transformers  </title>
    <summary>This paper studies transformer architectures for NLP tasks.</summary>
    <published>2023-01-01T00:00:00Z</published>
    <author><name>Alice Smith</name></author>
    <author><name>Bob Jones</name></author>
    <arxiv:doi>10.1234/example.doi</arxiv:doi>
    <arxiv:journal_ref>Nature Machine Intelligence 2023</arxiv:journal_ref>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2302.00002v1</id>
    <title>Another Paper</title>
    <summary>Abstract of another paper.</summary>
    <published>2023-02-01T00:00:00Z</published>
    <author><name>Carol White</name></author>
  </entry>
</feed>"""

_ARXIV_XML_NO_TEXT = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
</feed>"""

_SEMANTIC_SCHOLAR_JSON = {
    "data": [
        {
            "paperId": "abc123",
            "title": "Attention Is All You Need",
            "abstract": "We propose a new network architecture based solely on attention mechanisms.",
            "authors": [{"name": "Ashish Vaswani"}, {"name": "Noam Shazeer"}],
            "year": 2017,
            "venue": "NeurIPS",
            "publicationDate": "2017-06-12",
            "externalIds": {"DOI": "10.5555/3295222.3295349", "ArXiv": "1706.03762"},
        },
        {
            "paperId": "def456",
            "title": "BERT: Pre-training of Deep Bidirectional Transformers",
            "abstract": "BERT pre-trains deep bidirectional representations.",
            "authors": [{"name": "Jacob Devlin"}],
            "year": 2019,
            "venue": "NAACL",
            "publicationDate": "2019-05-11",
            "externalIds": {"DOI": "10.18653/v1/N19-1423"},
        },
    ]
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_project_and_run(client: AsyncClient) -> tuple[str, str]:
    proj_resp = await client.post(
        "/api/v1/projects/",
        json={"title": "Source Test", "research_question": "What are transformers?"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    run_resp = await client.post(
        f"/api/v1/projects/{project_id}/runs",
        json={"research_question": "What are transformers?", "workflow_mode": "sequential"},
    )
    assert run_resp.status_code == 201
    run_id = run_resp.json()["id"]
    return project_id, run_id


# ---------------------------------------------------------------------------
# arXiv provider unit tests
# ---------------------------------------------------------------------------

def test_sp01_arxiv_parses_atom_xml():
    """SP-01: ArXivSearchProvider parses valid Atom XML → SearchResult objects."""
    provider = ArXivSearchProvider()
    results = provider._parse_atom(_ARXIV_XML)
    assert len(results) == 2
    assert results[0].title == "A Test Paper on Transformers"
    assert "arxiv.org" in results[0].url


def test_sp02_arxiv_is_not_peer_reviewed():
    """SP-02: All arXiv results have is_peer_reviewed=False."""
    provider = ArXivSearchProvider()
    results = provider._parse_atom(_ARXIV_XML)
    for r in results:
        assert r.is_peer_reviewed is False


def test_sp03_arxiv_doi_parsed():
    """SP-03: arXiv DOI extracted from <arxiv:doi> element."""
    provider = ArXivSearchProvider()
    results = provider._parse_atom(_ARXIV_XML)
    assert results[0].doi == "10.1234/example.doi"
    assert results[1].doi is None  # second entry has no DOI


def test_sp04_arxiv_authors_parsed():
    """SP-04: arXiv authors list extracted from <author><name> elements."""
    provider = ArXivSearchProvider()
    results = provider._parse_atom(_ARXIV_XML)
    assert results[0].authors == ["Alice Smith", "Bob Jones"]
    assert results[1].authors == ["Carol White"]


def test_sp05_arxiv_venue_parsed():
    """SP-05: arXiv venue extracted from <arxiv:journal_ref> when present."""
    provider = ArXivSearchProvider()
    results = provider._parse_atom(_ARXIV_XML)
    assert results[0].venue == "Nature Machine Intelligence 2023"
    assert results[1].venue is None


def test_sp06_arxiv_http_error_returns_empty():
    """SP-06: ArXivSearchProvider returns [] on HTTP error (graceful degradation)."""
    import asyncio

    async def _run():
        provider = ArXivSearchProvider()
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get.side_effect = Exception("Connection refused")
            results = await provider.search("test query", 5)
        return results

    results = asyncio.get_event_loop().run_until_complete(_run())
    assert results == []


def test_sp07_arxiv_malformed_xml_returns_empty():
    """SP-07: ArXivSearchProvider returns [] on malformed XML."""
    provider = ArXivSearchProvider()
    results = provider._parse_atom("not xml at all <<<")
    assert results == []


# ---------------------------------------------------------------------------
# Semantic Scholar provider unit tests
# ---------------------------------------------------------------------------

def test_sp08_semantic_scholar_rate_limit_returns_empty():
    """SP-08: SemanticScholarProvider returns [] on 429 (rate limited)."""
    import asyncio

    async def _run():
        provider = SemanticScholarProvider(api_key="test_key")
        mock_response = MagicMock()
        mock_response.status_code = 429

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get.return_value = mock_response
            results = await provider.search("test", 5)
        return results

    results = asyncio.get_event_loop().run_until_complete(_run())
    assert results == []


def test_sp09_semantic_scholar_parses_json():
    """SP-09: SemanticScholarProvider._parse_response → correct SearchResult objects."""
    provider = SemanticScholarProvider()
    results = provider._parse_response(_SEMANTIC_SCHOLAR_JSON)
    assert len(results) == 2
    assert results[0].title == "Attention Is All You Need"
    assert results[0].doi == "10.5555/3295222.3295349"
    assert results[0].authors == ["Ashish Vaswani", "Noam Shazeer"]
    assert results[0].venue == "NeurIPS"
    assert results[0].is_peer_reviewed is False
    assert "doi.org" in results[0].url


def test_sp10_semantic_scholar_connection_error_returns_empty():
    """SP-10: SemanticScholarProvider returns [] on connection error."""
    import asyncio

    async def _run():
        provider = SemanticScholarProvider()
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get.side_effect = Exception("Network error")
            results = await provider.search("test", 5)
        return results

    results = asyncio.get_event_loop().run_until_complete(_run())
    assert results == []


# ---------------------------------------------------------------------------
# MultiProviderSearch deduplication tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sp11_multi_provider_dedup_by_url():
    """SP-11: MultiProviderSearch deduplicates results sharing the same URL."""
    shared_url = "https://example.com/same-paper"
    provider_a = MagicMock(spec=["search"])
    provider_a.search = AsyncMock(return_value=[
        SearchResult(url=shared_url, title="Paper A", snippet="A"),
    ])
    provider_b = MagicMock(spec=["search"])
    provider_b.search = AsyncMock(return_value=[
        SearchResult(url=shared_url, title="Paper A Duplicate", snippet="B"),
        SearchResult(url="https://example.com/different", title="Different", snippet="D"),
    ])
    multi = MultiProviderSearch([provider_a, provider_b])
    results = await multi.search("test", 10)
    urls = [r.url for r in results]
    assert urls.count(shared_url) == 1  # deduplicated
    assert len(results) == 2  # shared_url + different


@pytest.mark.asyncio
async def test_sp12_multi_provider_dedup_by_doi():
    """SP-12: MultiProviderSearch deduplicates results sharing the same DOI."""
    shared_doi = "10.1234/shared-doi"
    provider_a = MagicMock(spec=["search"])
    provider_a.search = AsyncMock(return_value=[
        SearchResult(url="https://arxiv.org/abs/1234", title="Paper", snippet="X", doi=shared_doi),
    ])
    provider_b = MagicMock(spec=["search"])
    provider_b.search = AsyncMock(return_value=[
        SearchResult(url="https://doi.org/10.1234/shared-doi", title="Same Paper", snippet="Y", doi=shared_doi),
    ])
    multi = MultiProviderSearch([provider_a, provider_b])
    results = await multi.search("test", 10)
    assert len(results) == 1  # deduplicated by DOI


@pytest.mark.asyncio
async def test_sp13_multi_provider_combined_no_dupes():
    """SP-13: MultiProviderSearch returns combined results when no duplicates."""
    provider_a = MagicMock(spec=["search"])
    provider_a.search = AsyncMock(return_value=[
        SearchResult(url="https://a.com/1", title="A1", snippet="A1"),
        SearchResult(url="https://a.com/2", title="A2", snippet="A2"),
    ])
    provider_b = MagicMock(spec=["search"])
    provider_b.search = AsyncMock(return_value=[
        SearchResult(url="https://b.com/1", title="B1", snippet="B1"),
    ])
    multi = MultiProviderSearch([provider_a, provider_b])
    results = await multi.search("test", 10)
    assert len(results) == 3


# ---------------------------------------------------------------------------
# source_service tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sp14_source_service_creates_source(db_session: AsyncSession):
    """SP-14: source_service creates a Source row from a SearchResult."""
    from app.models.run import ResearchRun
    from app.models.project import ResearchProject

    # Minimal project + run setup
    project = ResearchProject(
        id=str(uuid.uuid4()),
        title="Test",
        research_question="Q?",
    )
    db_session.add(project)
    run = ResearchRun(
        id=str(uuid.uuid4()),
        project_id=project.id,
        research_question="Q?",
    )
    db_session.add(run)
    await db_session.flush()

    result = SearchResult(
        url="https://example.com/paper",
        title="Test Paper",
        snippet="A test.",
        doi="10.1/test",
        authors=["Alice"],
        venue="ICML 2023",
        is_peer_reviewed=False,
    )
    source = await create_source_from_result(db_session, run.id, result, "tavily")
    await db_session.flush()

    assert source.id is not None
    assert source.run_id == run.id
    assert source.doi == "10.1/test"
    assert source.venue == "ICML 2023"
    assert source.is_peer_reviewed is False
    assert source.retrieval_provider == "tavily"


@pytest.mark.asyncio
async def test_sp15_source_service_dedup_by_url(db_session: AsyncSession):
    """SP-15: source_service returns existing Source for duplicate URL in same run."""
    from app.models.run import ResearchRun
    from app.models.project import ResearchProject

    project = ResearchProject(id=str(uuid.uuid4()), title="T", research_question="Q?")
    db_session.add(project)
    run = ResearchRun(id=str(uuid.uuid4()), project_id=project.id, research_question="Q?")
    db_session.add(run)
    await db_session.flush()

    result = SearchResult(url="https://example.com/paper-url", title="Paper", snippet="S")
    src1 = await create_source_from_result(db_session, run.id, result, "tavily")
    await db_session.flush()
    src2 = await create_source_from_result(db_session, run.id, result, "tavily")
    await db_session.flush()

    assert src1.id == src2.id


@pytest.mark.asyncio
async def test_sp16_source_service_dedup_by_doi(db_session: AsyncSession):
    """SP-16: source_service deduplicates by DOI even if URLs differ."""
    from app.models.run import ResearchRun
    from app.models.project import ResearchProject

    project = ResearchProject(id=str(uuid.uuid4()), title="T", research_question="Q?")
    db_session.add(project)
    run = ResearchRun(id=str(uuid.uuid4()), project_id=project.id, research_question="Q?")
    db_session.add(run)
    await db_session.flush()

    r1 = SearchResult(url="https://arxiv.org/abs/1234", title="P", snippet="S", doi="10.1/doi")
    r2 = SearchResult(url="https://doi.org/10.1/doi", title="P2", snippet="S2", doi="10.1/doi")
    src1 = await create_source_from_result(db_session, run.id, r1, "arxiv")
    await db_session.flush()
    src2 = await create_source_from_result(db_session, run.id, r2, "semantic_scholar")
    await db_session.flush()

    assert src1.id == src2.id


@pytest.mark.asyncio
async def test_sp17_source_service_separate_runs(db_session: AsyncSession):
    """SP-17: Same URL creates separate Source rows for different runs."""
    from app.models.run import ResearchRun
    from app.models.project import ResearchProject

    project = ResearchProject(id=str(uuid.uuid4()), title="T", research_question="Q?")
    db_session.add(project)
    run1 = ResearchRun(id=str(uuid.uuid4()), project_id=project.id, research_question="Q?")
    run2 = ResearchRun(id=str(uuid.uuid4()), project_id=project.id, research_question="Q?")
    db_session.add(run1)
    db_session.add(run2)
    await db_session.flush()

    result = SearchResult(url="https://example.com/shared-paper", title="P", snippet="S")
    src1 = await create_source_from_result(db_session, run1.id, result, "tavily")
    src2 = await create_source_from_result(db_session, run2.id, result, "tavily")
    await db_session.flush()

    assert src1.id != src2.id  # separate rows for separate runs


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sp18_get_sources_200(async_client: AsyncClient):
    """SP-18: GET /runs/{run_id}/sources → 200 with correct structure."""
    project_id, run_id = await _create_project_and_run(async_client)
    resp = await async_client.get(f"/api/v1/projects/{project_id}/runs/{run_id}/sources")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["run_id"] == run_id
    assert isinstance(body["total"], int)


@pytest.mark.asyncio
async def test_sp19_get_sources_empty(async_client: AsyncClient):
    """SP-19: GET sources for new run → empty list."""
    project_id, run_id = await _create_project_and_run(async_client)
    resp = await async_client.get(f"/api/v1/projects/{project_id}/runs/{run_id}/sources")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_sp20_get_sources_nonexistent_run(async_client: AsyncClient):
    """SP-20: GET sources for non-existent run → 404."""
    project_id, _ = await _create_project_and_run(async_client)
    fake_run_id = str(uuid.uuid4())
    resp = await async_client.get(f"/api/v1/projects/{project_id}/runs/{fake_run_id}/sources")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# SourceResponse serialization tests
# ---------------------------------------------------------------------------

def test_sp21_source_response_deserializes_authors():
    """SP-21: SourceResponse deserializes authors JSON TEXT to list[str]."""
    from app.schemas.source import SourceResponse
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    data = {
        "id": str(uuid.uuid4()),
        "run_id": str(uuid.uuid4()),
        "source_type": "academic",
        "title": "Test Paper",
        "url": "https://example.com",
        "doi": None,
        "authors": '["Alice Smith", "Bob Jones"]',  # JSON TEXT as stored in DB
        "publisher": None,
        "venue": None,
        "publication_date": None,
        "is_peer_reviewed": False,
        "retrieval_provider": "arxiv",
        "retrieved_at": now,
        "is_accessible": True,
        "credibility_notes": None,
        "created_at": now,
    }
    response = SourceResponse.model_validate(data)
    assert response.authors == ["Alice Smith", "Bob Jones"]


# ---------------------------------------------------------------------------
# Provider factory tests
# ---------------------------------------------------------------------------

def test_sp22_get_search_provider_multi_when_arxiv_enabled():
    """SP-22: get_search_provider returns MultiProviderSearch when ARXIV_ENABLED=True."""
    from app.providers.web_search import get_search_provider, MultiProviderSearch
    import app.core.config as _config_mod

    original = _config_mod.settings
    try:
        mock_settings = MagicMock()
        mock_settings.SEARCH_PROVIDER = "tavily"
        mock_settings.SEARCH_API_KEY = "test_key"
        mock_settings.ARXIV_ENABLED = True
        mock_settings.SEMANTIC_SCHOLAR_API_KEY = ""
        _config_mod.settings = mock_settings
        provider = get_search_provider()
    finally:
        _config_mod.settings = original

    assert isinstance(provider, MultiProviderSearch)


def test_sp23_get_search_provider_tavily_only():
    """SP-23: get_search_provider returns single TavilySearchProvider by default."""
    from app.providers.web_search import get_search_provider, TavilySearchProvider
    import app.core.config as _config_mod

    original = _config_mod.settings
    try:
        mock_settings = MagicMock()
        mock_settings.SEARCH_PROVIDER = "tavily"
        mock_settings.SEARCH_API_KEY = "test_key"
        mock_settings.ARXIV_ENABLED = False
        mock_settings.SEMANTIC_SCHOLAR_API_KEY = ""
        _config_mod.settings = mock_settings
        provider = get_search_provider()
    finally:
        _config_mod.settings = original

    assert isinstance(provider, TavilySearchProvider)
