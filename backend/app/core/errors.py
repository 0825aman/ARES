from __future__ import annotations
import re


def safe_error_message(exc: Exception) -> str:
    """Convert an exception to a safe, non-leaking error message.

    Strips file system paths and truncates to 500 characters.
    Used by all workflow and agent error handlers to avoid leaking
    internal paths or sensitive context in persisted error messages.
    """
    msg = str(exc)
    # Strip Windows-style paths (e.g. C:\Users\...)
    msg = re.sub(r"[A-Za-z]:\\[\w\\.\-]+", "<path>", msg)
    # Strip Unix-style paths (e.g. /home/user/...)
    msg = re.sub(r"/[\w/.\-]+", "<path>", msg)
    return msg[:500]
