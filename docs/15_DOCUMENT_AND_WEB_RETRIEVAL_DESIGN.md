# 15 — Document and Web Retrieval Design

**Project**: Multi-Agent Autonomous Researcher (MAAR)
**Phase**: 2 — First End-to-End Research Workflow
**Status**: Planning

---

## 1. Document Upload and Storage

### 1.1 Upload Flow

1. User selects files in the browser (via `<input type="file">` or drag-and-drop).
2. Browser sends `multipart/form-data` POST to `POST /api/v1/projects/{project_id}/documents`.
3. FastAPI receives files as `list[UploadFile]`.
4. For each file, the service validates (see section 1.2) before touching disk.
5. Accepted files are written to `{UPLOAD_DIR}/{project_id}/{uuid4()}_{safe_filename}`.
6. An `UploadedDocument` record is created in the database.
7. Rejected files are collected in a `rejected` array and returned to the caller — they do not abort the accepted files.

### 1.2 File Validation

**Extension check**: Filename must end with `.pdf`, `.docx`, or `.txt` (case-insensitive).

**MIME type check**: The first 4KB of the file is read to detect the actual MIME type using `python-magic` (libmagic). The detected type must match the declared extension:

| Extension | Accepted MIME types |
|---|---|
| `.pdf` | `application/pdf` |
| `.docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| `.txt` | `text/plain` |

**Size check**: File size must not exceed `MAX_UPLOAD_SIZE_MB` (default 20 MB). Checked against `UploadFile.size` before writing to disk.

**Why `python-magic`?** File extension alone is trivially spoofed. A user could rename `malicious.exe` to `report.pdf`. Libmagic reads the file's magic bytes to determine the true type. This is the standard approach for file type validation in production applications.

**Note on Windows**: `python-magic` requires `libmagic` binary. On Windows, use `python-magic-bin` which bundles the DLL. This is documented in `requirements.txt` as a Windows-specific note.

### 1.3 Safe File Storage

- The `UPLOAD_DIR` setting controls the base directory (default `./uploads/`). It must be created on startup if it does not exist.
- Files are stored as `{UPLOAD_DIR}/{project_id}/{doc_uuid}_{sanitized_original_name}`.
- `sanitized_original_name` is produced by: lowercasing, replacing spaces and special characters with underscores, and preserving the extension. Maximum 100 characters.
- The `project_id` subdirectory ensures files are scoped to projects and simplifies bulk deletion.
- File paths are never constructed from unsanitized user input. The `doc_uuid` prefix ensures uniqueness and prevents collisions.
- The `UPLOAD_DIR` must be outside the Next.js `public/` directory and must not be served statically.

### 1.4 Content Deduplication

Before writing a new file to disk, compute its SHA-256 hash. If an `UploadedDocument` with the same `content_hash` already exists for this project, skip the disk write and reuse the existing stored file. A new `UploadedDocument` record is still created (pointing to the existing `storage_path`) so the document is correctly associated with the new run.

---

## 2. Text Extraction

### 2.1 PDF Extraction (`pypdf`)

```python
from pypdf import PdfReader

reader = PdfReader(file_path)
pages = []
for i, page in enumerate(reader.pages):
    text = page.extract_text()
    if text:
        pages.append((i + 1, text.strip()))
```

- `pypdf` is pure Python — no system dependencies.
- Encrypted/password-protected PDFs raise `pypdf.errors.FileNotDecryptedError` — catch and mark extraction as failed.
- Scanned PDFs (image-only) return empty strings from `extract_text()`. If all pages return empty strings, mark extraction as failed with a descriptive message: `"PDF appears to be image-only. OCR is not supported in Phase 2."`.
- The page number from `enumerate` is stored in `EvidenceRecord.page_number`.

### 2.2 DOCX Extraction (`python-docx`)

```python
from docx import Document

doc = Document(file_path)
paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
full_text = "\n".join(paragraphs)
```

- Tables are not extracted in Phase 2 (deferred).
- Headers and footers are not extracted.
- Page numbers are not available from `python-docx` at the paragraph level; `chunk_index` is used instead.

### 2.3 TXT Extraction

```python
with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
    full_text = f.read()
```

- `errors='replace'` handles non-UTF-8 bytes without crashing.
- No page number information is available.

### 2.4 Text Chunking

After extraction, text is split into chunks:

```
chunk_size = 8000 characters (≈ 2000 tokens at 4 chars/token)
overlap = 400 characters (5% overlap to preserve sentence context across chunks)
```

Each chunk becomes one `EvidenceRecord` with:
- `source_type = "document"`
- `document_id` = the `UploadedDocument.id`
- `chunk_index` = sequential 0-based index
- `page_number` = the PDF page number from which this chunk originated (NULL for DOCX/TXT)
- `content` = the chunk text

---

## 3. Web Search Provider

### 3.1 Provider Selection

**Recommended: Tavily Search API**

Tavily is purpose-built for LLM-augmented research. Key characteristics:
- Returns pre-extracted, clean text content alongside URLs (avoids the need to fetch and parse HTML for many results).
- Has a free tier (1,000 searches/month as of 2026).
- Python SDK available (`tavily-python`).
- Designed specifically for RAG and research workflows.

**Alternative: SerpAPI**

- Wraps Google Search results.
- Free tier limited to 100 searches/month.
- Returns search result snippets; content must be fetched separately.
- Requires separate URL fetching for full content.

**Alternative: DuckDuckGo (unofficial)**

- No API key required.
- Uses the `duckduckgo-search` package (unofficial wrapper).
- Returns snippets only — no clean content extraction.
- Rate limits may be enforced without notice.
- **Not recommended** for production use due to instability.

**Decision for Phase 2**: Tavily as default. SerpAPI as alternative. Both are configured via the provider abstraction. The choice is set by `SEARCH_PROVIDER` env var.

### 3.2 Provider Interface

```python
# app/providers/web_search.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

@dataclass
class SearchResult:
    url: str
    title: str
    snippet: str
    content: str | None        # Pre-extracted content (Tavily provides this)
    published_date: str | None

class WebSearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, num_results: int) -> list[SearchResult]: ...
```

### 3.3 Tavily Implementation

```python
class TavilySearchProvider(WebSearchProvider):
    def __init__(self, api_key: str):
        self._client = TavilyClient(api_key=api_key)

    async def search(self, query: str, num_results: int) -> list[SearchResult]:
        # Tavily's SDK is synchronous — run in thread pool
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._client.search(query, max_results=num_results, include_raw_content=True)
        )
        return [SearchResult(...) for r in response["results"]]
```

When Tavily returns `include_raw_content=True`, the content is already extracted — the web fetcher is only invoked for results where `content` is `None` or empty.

---

## 4. Web Content Fetching

### 4.1 SSRF Protection

Before fetching any URL, it must pass the SSRF validation gate:

```python
import ipaddress
import socket

BLOCKED_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),   # link-local
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 private
]

def is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    try:
        addr = socket.gethostbyname(parsed.hostname)
        ip = ipaddress.ip_address(addr)
        return not any(ip in net for net in BLOCKED_RANGES)
    except socket.gaierror:
        return False  # DNS resolution failure
```

URLs failing this check are recorded as `fetch_status=failed` with `fetch_error="URL blocked by SSRF policy"`.

### 4.2 Content Fetching

```python
import httpx
import trafilatura

async def fetch_url(url: str, timeout: int) -> tuple[str | None, str | None]:
    """Returns (title, content) or (None, None) on failure."""
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True,
                                  max_redirects=5) as client:
        response = await client.get(url, headers={"User-Agent": "MAAR-Research/0.2"})
        response.raise_for_status()
        html = response.text

    content = trafilatura.extract(html, include_tables=False, include_comments=False)
    title = trafilatura.extract_metadata(html).title if content else None

    if not content or len(content.strip()) < 100:
        return None, None  # Page yielded no usable content

    # Truncate to configured limit
    max_chars = settings.WEB_FETCH_MAX_CONTENT_KB * 1024
    return title, content[:max_chars]
```

**`trafilatura`** is the recommended HTML-to-text library. It:
- Removes navigation, ads, and boilerplate.
- Extracts main article content.
- Is significantly better than `BeautifulSoup` for news/article pages.
- Is pure Python with no system dependencies.

### 4.3 Fetch Failure Handling

| Failure type | Handling |
|---|---|
| `httpx.TimeoutException` | Record `fetch_status=failed`, `fetch_error="Request timed out"` |
| HTTP 4xx | Record as failed, include status code in error |
| HTTP 5xx | Record as failed, include status code in error |
| `trafilatura` returns empty | Record as failed, `fetch_error="No extractable content"` |
| `UnicodeDecodeError` | Record as failed |
| Any other exception | Record as failed, log WARNING |

---

## 5. Evidence Normalization

All evidence — from both documents and web — is stored as `EvidenceRecord` rows with a common schema. This is the single interface that the synthesis stage consumes.

### 5.1 Web Evidence → EvidenceRecord

```
SearchResult {
    url         →  evidence.url
    title       →  evidence.page_title
    content     →  evidence.content
}
EvidenceRecord {
    source_type    = "web"
    source_label   = "[SOURCE N]"    # assigned sequentially
    content        = truncated content
    url            = url
    page_title     = title
    retrieved_at   = utcnow()
    document_id    = NULL
    chunk_index    = NULL
    page_number    = NULL
}
```

### 5.2 Document Evidence → EvidenceRecord

```
ExtractedChunk {
    text        →  evidence.content
    chunk_idx   →  evidence.chunk_index
    page_num    →  evidence.page_number
}
EvidenceRecord {
    source_type    = "document"
    source_label   = "[SOURCE N]"    # assigned sequentially
    content        = chunk text
    url            = NULL
    page_title     = NULL
    retrieved_at   = NULL
    document_id    = UploadedDocument.id
    chunk_index    = chunk index
    page_number    = page number (PDF) or NULL
}
```

Source labels (`[SOURCE 1]`, `[SOURCE 2]`) are assigned after all evidence is collected, sorted by relevance score descending, so the highest-relevance sources get the lowest numbers (most likely to appear first in the LLM prompt).

---

## 6. Citation Provenance

The synthesis stage passes numbered source labels to the LLM:

```
Evidence passage [SOURCE 1]:
Source: https://example.com/article — "Environmental Impact of Lithium"
Retrieved: 2026-01-01

Lithium extraction in the Atacama Desert requires approximately 2 million liters 
of water per tonne of lithium produced...

---

Evidence passage [SOURCE 2]:
Source: report.pdf (page 3)

The environmental review commissioned by the Chilean government found that...
```

The LLM is instructed to cite sources using `[SOURCE N]` inline. The report generator then resolves `[SOURCE N]` back to the actual `EvidenceRecord` data and builds the `evidence_used` array in the report.

**Anti-hallucination instruction**: The system prompt explicitly states that citing a source number not present in the evidence list is prohibited. The report generator validates that all cited source numbers exist in the provided evidence set.

---

## 7. Supported File Format Summary

| Format | Library | Phase 2 | Deferred |
|---|---|---|---|
| PDF (text-based) | pypdf | ✅ | — |
| PDF (scanned/image) | tesseract OCR | — | Phase 3 |
| DOCX | python-docx | ✅ | — |
| TXT (UTF-8) | built-in | ✅ | — |
| XLSX / CSV | openpyxl / csv | — | Phase 3 |
| PPTX | python-pptx | — | Phase 3 |
| HTML | — | — | Phase 3 |
| Markdown | — | — | Phase 3 |
| Images (JPG/PNG) | — | — | Phase 3+ |
