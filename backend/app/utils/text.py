"""
Text utilities for parsing and cleaning LLM output.

The agents are instructed to wrap their structured response inside a
``<structured_response>`` XML tag containing JSON. These helpers extract
and validate that payload robustly.
"""

from __future__ import annotations

import json
import re
import textwrap
from typing import Any

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

_STRUCTURED_TAG_RE = re.compile(
    r"<structured_response\s*>(.*?)</structured_response>",
    re.DOTALL | re.IGNORECASE,
)

_JSON_FENCE_RE = re.compile(
    r"```(?:json)?\s*([\[{].*?)\s*```",
    re.DOTALL | re.IGNORECASE,
)

_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def extract_json_block(text: str) -> dict[str, Any] | list[Any] | None:
    """
    Try to extract a JSON object or array from *text*.

    Strategy (in order):
    1. Parse ``<structured_response>…</structured_response>`` tag.
    2. Parse a fenced ```json … ``` block.
    3. Parse the entire text as JSON.
    4. Return ``None`` on failure.
    """
    # 1. structured tag
    match = _STRUCTURED_TAG_RE.search(text)
    if match:
        candidate = match.group(1).strip()
        parsed = _try_parse(candidate)
        if parsed is not None:
            return parsed

    # 2. fenced code block
    match = _JSON_FENCE_RE.search(text)
    if match:
        candidate = match.group(1).strip()
        parsed = _try_parse(candidate)
        if parsed is not None:
            return parsed

    # 3. raw text
    return _try_parse(text.strip())


def parse_structured_response(raw: str) -> list[dict[str, Any]]:
    """
    Parse the agent's raw text output into a list of structured blocks.

    Expected shape inside the structured tag::

        {
          "intent": "rti_inquiry",
          "blocks": [
            {"type": "header",   "title": "...", "content": "..."},
            {"type": "section",  "title": "...", "content": "..."},
            {"type": "steps",    "title": "...", "content": "...", "metadata": {}},
            {"type": "draft",    "title": "...", "content": "...", "metadata": {}},
            {"type": "disclaimer","title": "...", "content": "..."}
          ]
        }

    Returns the blocks list, or a single plain-text block as fallback.
    """
    parsed = extract_json_block(raw)

    if isinstance(parsed, dict):
        blocks = parsed.get("blocks")
        if isinstance(blocks, list) and blocks:
            return _validate_blocks(blocks)

    if isinstance(parsed, list) and parsed:
        return _validate_blocks(parsed)

    # Fallback — wrap the raw text in a plain section block.
    return [
        {
            "type": "section",
            "title": "Response",
            "content": clean_llm_output(raw),
            "metadata": {},
        }
    ]


def clean_llm_output(text: str) -> str:
    """
    Strip common LLM artefacts from *text*.

    - Removes leading / trailing whitespace.
    - Collapses runs of 3+ blank lines to 2.
    - Strips stray ``<structured_response>`` tags if the caller wants raw text.
    """
    text = _STRUCTURED_TAG_RE.sub("", text)
    text = _JSON_FENCE_RE.sub("", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def truncate(text: str, max_chars: int = 500, suffix: str = "…") -> str:
    """Truncate *text* to *max_chars*, appending *suffix* if truncated."""
    if len(text) <= max_chars:
        return text
    return textwrap.shorten(text, width=max_chars, placeholder=suffix)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _try_parse(text: str) -> dict[str, Any] | list[Any] | None:
    """Attempt JSON parsing, with a trailing-comma repair pass."""
    for candidate in (text, _TRAILING_COMMA_RE.sub(r"\1", text)):
        try:
            return json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
    return None


_VALID_BLOCK_TYPES = {
    "header",
    "section",
    "steps",
    "draft",
    "disclaimer",
    "clarification",
    "info",
    "warning",
}


def _validate_blocks(blocks: list[Any]) -> list[dict[str, Any]]:
    """Normalise each block, dropping malformed entries."""
    result: list[dict[str, Any]] = []
    for item in blocks:
        if not isinstance(item, dict):
            continue
        block_type = str(item.get("type", "section"))
        if block_type not in _VALID_BLOCK_TYPES:
            block_type = "section"
        result.append(
            {
                "type": block_type,
                "title": str(item.get("title", "")),
                "content": str(item.get("content", "")),
                "metadata": item.get("metadata") or {},
            }
        )
    return result or [
        {
            "type": "section",
            "title": "Response",
            "content": "",
            "metadata": {},
        }
    ]
