from __future__ import annotations

import logging
from pathlib import Path

from autoedit.align import normalize
from autoedit.config import RetakeConfig
from autoedit.models import (
    Alignment,
    CutDecision,
    DropSegment,
    KeepSegment,
    ScriptToken,
    Word,
)

log = logging.getLogger(__name__)


def detect_drops(
    words: list[Word],
    tokens: list[ScriptToken] | None,
    alignment: Alignment | None,
    cfg: RetakeConfig,
) -> list[DropSegment]:
    """
    Detect NG (retake) drop intervals using the "다시" trigger.

    Strategy (alignment-aware path):
      For each trigger word w_i:
        1. If w_i aligns to a script token whose text is also a trigger,
           it's a legitimate in-script "다시" - skip.
        2. Otherwise, find the restart point k* (next aligned word after i).
           The NG attempt's first word is the first word aligned to the
           script sentence containing k*. NG = [first_attempt_word.start ..
           words[k*].start - snap_margin], capped by context_seconds_before.
      Fallback when alignment is missing: drop from the previous sentence
      boundary (long silence) up to the trigger.
    """
    triggers = {normalize(t) for t in cfg.triggers}
    drops: list[DropSegment] = []
    align_map: dict[int, int | None] = {}
    if alignment is not None:
        align_map = {w_idx: t_idx for w_idx, t_idx in alignment.pairs}

    for i, w in enumerate(words):
        if normalize(w.text) not in triggers:
            continue
        # Rule 1: in-script "다시"
        if tokens is not None and i in align_map and align_map[i] is not None:
            t_idx = align_map[i]
            if t_idx is not None and tokens[t_idx].text in triggers:
                log.debug("Skipping in-script trigger at word %d (%.2fs)", i, w.start)
                continue

        ng_start, ng_end, reason = _decide_drop_window(
            i, w, words, tokens, align_map, cfg
        )
        if ng_end > ng_start:
            drops.append(DropSegment(start=ng_start, end=ng_end, reason=reason))
            log.info("NG drop %.2fs..%.2fs (%s)", ng_start, ng_end, reason)

    return _merge_overlaps(drops)


def _decide_drop_window(
    i: int,
    w: Word,
    words: list[Word],
    tokens: list[ScriptToken] | None,
    align_map: dict[int, int | None],
    cfg: RetakeConfig,
) -> tuple[float, float, str]:
    k_star = _first_aligned_after(i, align_map)

    if tokens is not None and k_star is not None:
        target_token = align_map.get(k_star)
        if target_token is not None:
            sentence_idx = tokens[target_token].sentence_idx
            first_attempt_word_idx = _first_word_for_sentence(
                words, align_map, tokens, sentence_idx, before_idx=i
            )
            if first_attempt_word_idx is not None:
                ng_start = words[first_attempt_word_idx].start - cfg.pre_margin
                ng_end = words[k_star].start - cfg.snap_margin
                hard_min = w.start - cfg.context_seconds_before
                ng_start = max(ng_start, hard_min)
                return ng_start, ng_end, "retake"

    # Fallback A: previous sentence boundary (long silence) ... trigger end
    ng_start = _previous_sentence_boundary(words, i, cfg.sentence_silence)
    ng_end = w.end + cfg.snap_margin
    if k_star is not None:
        ng_end = max(ng_end, words[k_star].start - cfg.snap_margin)
    return ng_start, ng_end, "retake-fallback"


def _first_aligned_after(i: int, align_map: dict[int, int | None]) -> int | None:
    for j in sorted(k for k in align_map if k > i):
        if align_map[j] is not None:
            return j
    return None


def _first_word_for_sentence(
    words: list[Word],
    align_map: dict[int, int | None],
    tokens: list[ScriptToken],
    sentence_idx: int,
    before_idx: int,
) -> int | None:
    """First word index <= before_idx whose aligned token belongs to sentence_idx."""
    candidates = [
        wi for wi in range(before_idx + 1)
        if (t := align_map.get(wi)) is not None
        and tokens[t].sentence_idx == sentence_idx
    ]
    if candidates:
        return min(candidates)
    return None


def _previous_sentence_boundary(words: list[Word], i: int, silence_threshold: float) -> float:
    """Return the start time of the word that begins the current sentence,
    detected via silence gap >= threshold."""
    if i == 0:
        return words[0].start
    for j in range(i, 0, -1):
        gap = words[j].start - words[j - 1].end
        if gap >= silence_threshold:
            return words[j].start
    return words[0].start


def _merge_overlaps(drops: list[DropSegment]) -> list[DropSegment]:
    if not drops:
        return []
    sorted_drops = sorted(drops, key=lambda d: d.start)
    merged: list[DropSegment] = [sorted_drops[0]]
    for d in sorted_drops[1:]:
        last = merged[-1]
        if d.start <= last.end + 0.05:
            merged[-1] = DropSegment(
                start=last.start,
                end=max(last.end, d.end),
                reason=last.reason if last.reason == d.reason else "retake",
            )
        else:
            merged.append(d)
    return merged


def build_keeps(
    source: Path,
    duration: float,
    drops: list[DropSegment],
    *,
    min_keep: float = 0.2,
) -> list[KeepSegment]:
    """Invert drops over [0, duration] to get keep segments."""
    keeps: list[KeepSegment] = []
    cursor = 0.0
    for d in sorted(drops, key=lambda x: x.start):
        if d.start > cursor + min_keep:
            keeps.append(KeepSegment(
                source=source, source_start=cursor, source_end=d.start, reason="main",
            ))
        cursor = max(cursor, d.end)
    if duration > cursor + min_keep:
        keeps.append(KeepSegment(
            source=source, source_start=cursor, source_end=duration, reason="main",
        ))
    return keeps


def build_decision(
    source: Path,
    duration: float,
    words: list[Word],
    tokens: list[ScriptToken] | None,
    alignment: Alignment | None,
    cfg: RetakeConfig,
) -> CutDecision:
    drops = detect_drops(words, tokens, alignment, cfg)
    keeps = build_keeps(source, duration, drops)
    return CutDecision(keeps=keeps, drops=drops)
