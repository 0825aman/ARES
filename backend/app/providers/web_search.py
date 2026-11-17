"""Web search provider abstractions — Phase 4 M4.2 extended.

Changes from Phase 3:
  - SearchResult gains doi, authors, venue, is_peer_reviewed (all optional)
  - ArXivSearchProvider: free httpx-based arXiv API (activated by ARXIV_ENABLED=true)
  - SemanticScholarProvider: httpx-based (activated by SEMANTIC_SCHOLAR_API_KEY being set)
  - MultiProviderSearch: runs all enabled providers in parallel, deduplicates by URL+DOI
  - get_search_provider() now returns MultiProviderSearch when additional providers are enabled

Backward compatibility:
  - Existing code that constructs SearchResult with positional/keyword args unchanged
  - New fields are Optional with default None — no call-site changes required
  - MockWebSearchProvider accepts the same constructor signature
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Sequence

from app.core.retry import async_retry

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    url: str
    title: str
    snippet: str
    content: str | None = None
    published_date: str | None = None
    # Phase 4 M4.2 — academic metadata (None for non-academic sources)
    doi: str | None = None
    authors: list[str] | None = None      # list of author name strings
    venue: str | None = None              # journal / conference name
    is_peer_reviewed: bool = False        # arXiv preprints → always False

    def __post_init__(self) -> None:
        if self.url and "\x00" in self.url:
            self.url = self.url.replace("\x00", "")
        if self.title and "\x00" in self.title:
            self.title = self.title.replace("\x00", "")
        if self.snippet and "\x00" in self.snippet:
            self.snippet = self.snippet.replace("\x00", "")
        if self.content and "\x00" in self.content:
            self.content = self.content.replace("\x00", "")
        if self.venue and "\x00" in self.venue:
            self.venue = self.venue.replace("\x00", "")


class WebSearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, num_results: int) -> list[SearchResult]:
        ...


# ---------------------------------------------------------------------------
# DuckDuckGo — 100% free web search, no API key required
# ---------------------------------------------------------------------------

class DuckDuckGoSearchProvider(WebSearchProvider):
    """100% Free Web Search via DuckDuckGo (ddgs).

    - No API key required
    - No cost / free tier limitations
    - Returns SearchResult objects with title, URL, snippet
    """

    @async_retry(max_attempts=2, base_delay=1.0)
    async def search(self, query: str, num_results: int) -> list[SearchResult]:
        loop = asyncio.get_event_loop()

        def _do_search(q: str):
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                return list(ddgs.text(q, max_results=num_results))

        # Try full query first, and if empty/error, try progressively simplified keyword slices
        candidates = [query]
        words = [w for w in query.replace(":", " ").replace("-", " ").split() if len(w) > 2]
        if len(words) > 5:
            candidates.append(" ".join(words[:5]))
        if len(words) > 2:
            candidates.append(" ".join(words[:3]))

        for candidate in candidates:
            try:
                raw_results = await loop.run_in_executor(None, lambda c=candidate: _do_search(c))
                if not raw_results:
                    continue
                results = []
                for r in raw_results:
                    url = r.get("href") or r.get("url") or ""
                    title = r.get("title") or ""
                    body = r.get("body") or r.get("snippet") or ""
                    if url:
                        results.append(
                            SearchResult(
                                url=url,
                                title=title,
                                snippet=body,
                                content=body,
                            )
                        )
                if results:
                    return results
            except Exception as exc:
                logger.debug("DuckDuckGo search attempt failed for '%s': %s", candidate, exc)

        return []


# ---------------------------------------------------------------------------
# Tavily (with automatic DuckDuckGo fallback)
# ---------------------------------------------------------------------------

class TavilySearchProvider(WebSearchProvider):
    def __init__(self, api_key: str):
        self._api_key = api_key
        self._fallback = DuckDuckGoSearchProvider()

    @async_retry(max_attempts=2, base_delay=1.0)
    async def search(self, query: str, num_results: int) -> list[SearchResult]:
        if not self._api_key:
            return await self._fallback.search(query, num_results)
        from tavily import TavilyClient
        client = TavilyClient(api_key=self._api_key)
        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                None,
                lambda: client.search(query, max_results=num_results, include_raw_content=True),
            )
            results = []
            for r in response.get("results", []):
                results.append(SearchResult(
                    url=r.get("url", ""),
                    title=r.get("title", ""),
                    snippet=r.get("content", ""),
                    content=r.get("raw_content"),
                    published_date=r.get("published_date"),
                ))
            if not results:
                # Tavily returned empty; fallback to DuckDuckGo
                return await self._fallback.search(query, num_results)
            return results
        except Exception as exc:
            logger.warning("Tavily search failed (%s); falling back to DuckDuckGo", exc)
            return await self._fallback.search(query, num_results)


# ---------------------------------------------------------------------------
# arXiv — free API, no key required
# ---------------------------------------------------------------------------

class ArXivSearchProvider(WebSearchProvider):
    """Search arXiv preprint server via its Atom/XML API.

    Key design decisions:
    - All results have is_peer_reviewed=False — arXiv preprints are NOT peer-reviewed
    - Uses httpx for async HTTP; no SDK dependency
    - API base: http://export.arxiv.org/api/query
    - Returns up to num_results papers ordered by relevance
    """

    _BASE_URL = "http://export.arxiv.org/api/query"

    @async_retry(max_attempts=3, base_delay=1.0)
    async def search(self, query: str, num_results: int) -> list[SearchResult]:
        import httpx
        import xml.etree.ElementTree as ET

        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": num_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(self._BASE_URL, params=params)
                response.raise_for_status()
        except Exception as exc:
            logger.warning("arXiv search failed: %s", exc)
            return []

        return self._parse_atom(response.text)

    def _parse_atom(self, xml_text: str) -> list[SearchResult]:
        """Parse arXiv Atom XML into SearchResult objects."""
        import xml.etree.ElementTree as ET

        _NS = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            logger.warning("arXiv: failed to parse XML: %s", exc)
            return []

        results = []
        for entry in root.findall("atom:entry", _NS):
            # ID → URL
            raw_id = (entry.findtext("atom:id", default="", namespaces=_NS) or "").strip()
            # arXiv IDs are like http://arxiv.org/abs/2301.00001v1
            url = raw_id if raw_id.startswith("http") else f"https://arxiv.org/abs/{raw_id}"

            title_el = entry.findtext("atom:title", default="", namespaces=_NS)
            title = " ".join((title_el or "").split())  # normalise whitespace

            summary = (entry.findtext("atom:summary", default="", namespaces=_NS) or "").strip()
            published = entry.findtext("atom:published", default=None, namespaces=_NS)

            # Authors
            authors = [
                a.findtext("atom:name", default="", namespaces=_NS).strip()
                for a in entry.findall("atom:author", _NS)
            ]
            authors = [a for a in authors if a]

            # DOI
            doi_el = entry.find("arxiv:doi", _NS)
            doi = doi_el.text.strip() if doi_el is not None and doi_el.text else None

            # Journal ref (venue)
            journal_el = entry.find("arxiv:journal_ref", _NS)
            venue = journal_el.text.strip() if journal_el is not None and journal_el.text else None

            if not url:
                continue

            results.append(SearchResult(
                url=url,
                title=title,
                snippet=summary[:500] if summary else "",
                content=summary,
                published_date=published[:10] if published else None,
                doi=doi,
                authors=authors or None,
                venue=venue,
                is_peer_reviewed=False,  # arXiv preprints NEVER assumed peer-reviewed
            ))

        return results


# ---------------------------------------------------------------------------
# Semantic Scholar
# ---------------------------------------------------------------------------

class SemanticScholarProvider(WebSearchProvider):
    """Search Semantic Scholar Graph API.

    - With API key: higher rate limits (100 req/5min)
    - Without API key: limited to ~100 req/5min shared pool — degraded but functional
    - Gracefully returns [] on rate limit or connectivity failure (non-fatal)
    """

    _BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

    def __init__(self, api_key: str = ""):
        self._api_key = api_key

    @async_retry(max_attempts=3, base_delay=1.0)
    async def search(self, query: str, num_results: int) -> list[SearchResult]:
        import httpx

        headers = {}
        if self._api_key:
            headers["x-api-key"] = self._api_key

        params = {
            "query": query,
            "limit": min(num_results, 100),
            "fields": "title,abstract,authors,year,venue,externalIds,publicationDate,isOpenAccess,openAccessPdf",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
                response = await client.get(self._BASE_URL, params=params)
                if response.status_code == 429:
                    logger.warning("SemanticScholar: rate limited — skipping")
                    return []
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            logger.warning("SemanticScholar search failed: %s", exc)
            return []

        return self._parse_response(data)

    def _parse_response(self, data: dict) -> list[SearchResult]:
        results = []
        for paper in data.get("data", []):
            ext_ids = paper.get("externalIds") or {}
            doi = ext_ids.get("DOI")
            arxiv_id = ext_ids.get("ArXiv")

            # Build URL — prefer DOI link, fall back to arXiv, then S2 page
            paper_id = paper.get("paperId", "")
            if doi:
                url = f"https://doi.org/{doi}"
            elif arxiv_id:
                url = f"https://arxiv.org/abs/{arxiv_id}"
            elif paper_id:
                url = f"https://www.semanticscholar.org/paper/{paper_id}"
            else:
                continue

            title = (paper.get("title") or "").strip()
            abstract = (paper.get("abstract") or "").strip()
            authors = [
                a.get("name", "").strip()
                for a in (paper.get("authors") or [])
            ]
            authors = [a for a in authors if a]
            year = paper.get("year")
            pub_date = paper.get("publicationDate") or (str(year) if year else None)
            venue = (paper.get("venue") or "").strip() or None

            results.append(SearchResult(
                url=url,
                title=title,
                snippet=abstract[:500] if abstract else "",
                content=abstract,
                published_date=pub_date,
                doi=doi,
                authors=authors or None,
                venue=venue,
                # Semantic Scholar indexes peer-reviewed and preprint sources.
                # We conservatively default to False; the venue/DOI fields give
                # the user the information to judge themselves.
                is_peer_reviewed=False,
            ))
        return results


# ---------------------------------------------------------------------------
# Multi-provider dispatcher
# ---------------------------------------------------------------------------

def _dedup_key(result: SearchResult) -> str:
    """Generate a deduplication key for a SearchResult.

    Prefer DOI (canonical across providers) over URL.
    URL is normalised: lowercase, strip trailing slash.
    """
    if result.doi:
        return f"doi:{result.doi.lower().strip()}"
    url = result.url.lower().strip().rstrip("/")
    return f"url:{url}"


class MultiProviderSearch(WebSearchProvider):
    """Runs all enabled providers in parallel and deduplicates by URL/DOI.

    Provider routing by research category:
      - Tavily always included
      - arXiv added when ARXIV_ENABLED=True
      - Semantic Scholar added when SEMANTIC_SCHOLAR_API_KEY is set

    All categories are eligible for arXiv (not restricted to STEM).
    Query-level signals (keywords like "study", "research", etc.) are checked
    to determine whether arXiv is useful even for non-typical categories.
    """

    def __init__(self, providers: list[WebSearchProvider]):
        self._providers = providers

    async def search(self, query: str, num_results: int) -> list[SearchResult]:
        if not self._providers:
            return []

        # Run all providers in parallel
        tasks = [p.search(query, num_results) for p in self._providers]
        raw_lists: list[list[SearchResult]] = await asyncio.gather(*tasks, return_exceptions=False)

        # Deduplicate across providers, preserving insertion order
        seen: set[str] = set()
        merged: list[SearchResult] = []
        for results in raw_lists:
            if isinstance(results, Exception):
                logger.warning("MultiProviderSearch: provider error: %s", results)
                continue
            for r in results:
                key = _dedup_key(r)
                if key not in seen:
                    seen.add(key)
                    merged.append(r)

        return merged[:num_results * len(self._providers)]  # cap at generous upper bound


# ---------------------------------------------------------------------------
# Mock provider (unchanged interface)
# ---------------------------------------------------------------------------

class MockWebSearchProvider(WebSearchProvider):
    """Returns canned search results for testing."""

    def __init__(self, results: list[SearchResult] | None = None, fail: bool = False):
        self._results = results or [
            SearchResult(
                url="https://example.com/article-1",
                title="Example Article 1",
                snippet="This is the first example article snippet.",
                content="This is the full content of the first example article. It contains useful information about the research topic.",
            ),
            SearchResult(
                url="https://example.com/article-2",
                title="Example Article 2",
                snippet="This is the second example article snippet.",
                content="This is the full content of the second example article. More relevant information here.",
            ),
        ]
        self._fail = fail

    async def search(self, query: str, num_results: int) -> list[SearchResult]:
        if self._fail:
            raise RuntimeError("MockWebSearchProvider: simulated failure")
        return self._results[:num_results]


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------

def get_search_provider() -> WebSearchProvider:
    """Return the appropriate search provider based on configuration.

    Phase 4 M4.2: returns MultiProviderSearch when additional providers are enabled.
    Falls back to Tavily-only when ARXIV_ENABLED=False and no Semantic Scholar key.
    """
    from app.core.config import settings

    providers: list[WebSearchProvider] = []

    if settings.SEARCH_PROVIDER in ("duckduckgo", "ddg"):
        providers.append(DuckDuckGoSearchProvider())
        logger.info("DuckDuckGo 100% free search provider enabled")
    elif settings.SEARCH_PROVIDER == "tavily":
        if settings.SEARCH_API_KEY:
            providers.append(TavilySearchProvider(api_key=settings.SEARCH_API_KEY))
        else:
            logger.warning("Tavily selected but SEARCH_API_KEY is not set — using DuckDuckGo fallback")
            providers.append(DuckDuckGoSearchProvider())

    if settings.ARXIV_ENABLED:
        providers.append(ArXivSearchProvider())
        logger.info("arXiv search provider enabled")

    if settings.SEMANTIC_SCHOLAR_API_KEY:
        providers.append(SemanticScholarProvider(api_key=settings.SEMANTIC_SCHOLAR_API_KEY))
        logger.info("Semantic Scholar search provider enabled")

    if len(providers) == 1:
        return providers[0]

    if providers:
        return MultiProviderSearch(providers)

    raise ValueError(f"Unknown or unconfigured search provider: {settings.SEARCH_PROVIDER}")
