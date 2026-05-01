"""Optional Claude API helper for low-confidence alignment chunks.

This module is imported lazily by align.py only when
config.llm.enable_alignment_assist is True.
"""

from __future__ import annotations

import json
import logging
import os

from autoedit.models import Word

log = logging.getLogger(__name__)


def align_chunk_with_llm(
    script_window: str,
    transcript_window: list[Word],
    *,
    model: str = "claude-opus-4-7",
    base_word_offset: int = 0,
) -> list[tuple[int, int | None]]:
    """Ask Claude to map transcript words onto script tokens.

    Returns pairs (transcript_word_index, script_token_index | None).
    Falls back to an empty list if the API call fails or output fails validation.
    """
    try:
        from anthropic import Anthropic
    except ImportError:
        log.warning("anthropic SDK not installed; install autoedit[llm] to enable LLM assist.")
        return []

    if not os.environ.get("ANTHROPIC_API_KEY"):
        log.warning("ANTHROPIC_API_KEY not set; skipping LLM assist.")
        return []

    client = Anthropic()
    word_lines = "\n".join(
        f"{i}\t{w.text}\t{w.start:.2f}" for i, w in enumerate(transcript_window)
    )
    prompt = (
        "You align Korean transcript words to script tokens.\n"
        "SCRIPT:\n" + script_window + "\n"
        "TRANSCRIPT (idx<TAB>word<TAB>start_seconds):\n" + word_lines + "\n"
        "Output strict JSON: {\"pairs\": [[transcript_idx, script_token_idx_or_null], ...]}.\n"
        "script_token_idx is the 0-based whitespace token index in SCRIPT. "
        "Use null for transcript words not in the script (filler, retake, NG)."
    )
    try:
        msg = client.messages.create(
            model=model,
            max_tokens=4096,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in msg.content if hasattr(b, "text"))
        data = json.loads(text)
        pairs_raw = data.get("pairs", [])
    except Exception as e:
        log.warning("LLM assist failed: %s", e)
        return []

    out: list[tuple[int, int | None]] = []
    for entry in pairs_raw:
        try:
            wi, ti = entry
            wi_int = int(wi) + base_word_offset
            ti_int = int(ti) if ti is not None else None
            out.append((wi_int, ti_int))
        except Exception:
            continue
    return out
