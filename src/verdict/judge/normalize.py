"""Format normalization: strip Markdown so *style* differences don't sway a judge.

Recent work finds **style/format bias is the dominant judge bias** (judges prefer
Markdown-formatted text even when content is identical). Normalizing formatting
before judging is a direct, cheap mitigation.
"""

from __future__ import annotations

import re

_PATTERNS: list[tuple[str, str]] = [
    (r"```.*?```", " "),          # fenced code blocks
    (r"`([^`]*)`", r"\1"),         # inline code
    (r"^\s{0,3}#{1,6}\s*", ""),    # ATX headers
    (r"\*\*([^*]+)\*\*", r"\1"),   # bold **
    (r"__([^_]+)__", r"\1"),       # bold __
    (r"\*([^*]+)\*", r"\1"),       # italic *
    (r"_([^_]+)_", r"\1"),         # italic _
    (r"^\s{0,3}[-*+]\s+", "", ),   # bullet list markers
    (r"^\s{0,3}\d+\.\s+", ""),     # ordered list markers
    (r"^\s{0,3}>\s?", ""),         # blockquotes
    (r"\[([^\]]+)\]\([^)]+\)", r"\1"),  # links -> link text
]


def strip_formatting(text: str) -> str:
    """Return ``text`` with common Markdown formatting removed and whitespace collapsed."""
    out = text
    for pattern, repl in _PATTERNS:
        flags = re.MULTILINE | re.DOTALL if "```" in pattern else re.MULTILINE
        out = re.sub(pattern, repl, out, flags=flags)
    out = re.sub(r"[ \t]+", " ", out)
    out = re.sub(r"\n{2,}", "\n", out)
    return out.strip()
