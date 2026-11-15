"""content_sanitizer.py — Input sanitization and prompt injection defense.

Provides:
  - sanitize_research_question: Strip control characters, HTML-encode < and >, length limit.
  - wrap_external_content: Wraps untrusted external data in XML delimiter tags.
  - sanitize_filename: Strips path traversal sequences, null bytes, extracts basename.
"""
from __future__ import annotations

import html
import os
import re


def sanitize_research_question(text: str) -> str:
    """Sanitize research question string.

    - Strips non-printable ASCII control characters (keeping tab, newline)
    - Replaces < and > with HTML entities to prevent tag injection
    - Truncates to max 1000 characters
    - Trims leading/trailing whitespace
    """
    if not text:
        return ""
    # Strip ASCII control characters except \t and \n
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # HTML-encode < and >
    cleaned = html.escape(cleaned, quote=False)
    # Truncate to 1000 chars and trim
    return cleaned[:1000].strip()


def wrap_external_content(content: str, source: str) -> str:
    """Wrap external content in XML delimiter tags to isolate untrusted input for LLMs.

    Agents' system prompts instruct models to treat <external_content> as untrusted.
    """
    safe_source = html.escape(source, quote=True)
    return f'<external_content source="{safe_source}">\n{content}\n</external_content>'


def sanitize_filename(filename: str) -> str:
    """Sanitize uploaded filenames against path traversal attacks.

    - Removes null bytes
    - Extracts basename only (stripping directory components)
    - Strips any remaining '..' sequences
    - Truncates to 255 characters
    - Returns 'unnamed' if empty
    """
    if not filename:
        return "unnamed"
    # Remove null bytes
    clean = filename.replace("\x00", "")
    # Normalize and extract basename across OS boundaries
    clean = clean.replace("\\", "/")
    clean = os.path.basename(clean)
    # Strip any remaining '..'
    clean = clean.replace("..", "")
    clean = clean.strip()
    return clean[:255] if clean else "unnamed"
