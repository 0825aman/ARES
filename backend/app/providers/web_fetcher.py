from __future__ import annotations
import ipaddress
import logging
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse

from app.core.retry import async_retry

logger = logging.getLogger(__name__)

BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


BLOCKED_SCHEMES = frozenset({"file", "ftp", "javascript", "data", "gopher", "mailto", "ssh"})


def is_safe_url(url: str) -> bool:
    """Return True only if the URL is a public HTTP/HTTPS URL (SSRF protection)."""
    try:
        parsed = urlparse(url)
        if parsed.scheme.lower() in BLOCKED_SCHEMES:
            return False
        if parsed.scheme.lower() not in ("http", "https"):
            return False
        if not parsed.hostname:
            return False
        # Resolve hostname to IP
        addr = socket.gethostbyname(parsed.hostname)
        ip = ipaddress.ip_address(addr)
        for network in BLOCKED_NETWORKS:
            if ip in network:
                return False
        return True
    except (socket.gaierror, ValueError):
        return False


@async_retry(max_attempts=2, base_delay=0.5)
async def fetch_url(url: str, timeout: int, max_content_kb: int) -> tuple[str | None, str | None]:
    """
    Fetch a URL and extract main content. Returns (title, content) or (None, None) on failure.
    Caller must check is_safe_url() before calling this function.

    Retried up to 2 attempts on timeout/connect errors only.
    HTTP 4xx/5xx errors are not retried (non-transient).
    """
    import httpx
    try:
        import trafilatura
    except ImportError:
        trafilatura = None  # type: ignore

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            max_redirects=5,
        ) as client:
            response = await client.get(
                url,
                headers={"User-Agent": "ARES-Research/0.2 (Autonomous Research & Evidence System)"},
            )
            response.raise_for_status()

            # Re-validate destination URL post-redirects to prevent redirect-based SSRF
            final_url = str(response.url)
            if not is_safe_url(final_url):
                logger.warning("SSRF blocked redirect target: %s -> %s", url, final_url)
                return None, None

            html = response.text

        if trafilatura:
            content = trafilatura.extract(
                html,
                include_tables=False,
                include_comments=False,
                no_fallback=False,
            )
            title = None
            if content:
                try:
                    meta = trafilatura.extract_metadata(html)
                    title = meta.title if meta else None
                except Exception:
                    pass
        else:
            # Basic fallback if trafilatura not available
            from html.parser import HTMLParser

            class _TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text_parts: list[str] = []
                    self._skip = False

                def handle_starttag(self, tag, attrs):
                    if tag in ("script", "style", "nav", "header", "footer"):
                        self._skip = True

                def handle_endtag(self, tag):
                    if tag in ("script", "style", "nav", "header", "footer"):
                        self._skip = False

                def handle_data(self, data):
                    if not self._skip and data.strip():
                        self.text_parts.append(data.strip())

            extractor = _TextExtractor()
            extractor.feed(html)
            content = " ".join(extractor.text_parts) or None
            title = None

        if not content or len(content.strip()) < 100:
            return None, None

        if content and "\x00" in content:
            content = content.replace("\x00", "")
        if title and "\x00" in title:
            title = title.replace("\x00", "")

        max_chars = max_content_kb * 1024
        return title, content[:max_chars]

    except httpx.TimeoutException:
        logger.warning("Timeout fetching %s", url)
        raise
    except httpx.HTTPStatusError as exc:
        logger.warning("HTTP %d fetching %s", exc.response.status_code, url)
        raise
    except Exception as exc:
        logger.warning("Error fetching %s: %s", url, exc)
        raise
