"""Unit tests for the core '다시' retake algorithm.

We construct synthetic Word/Token sequences with explicit alignments to
exercise the five canonical scenarios from the plan.
"""

from pathlib import Path

import pytest

from autoedit.config import RetakeConfig
from autoedit.models import Alignment, ScriptToken, Word
from autoedit.retake import build_keeps, detect_drops


def W(text: str, start: float, end: float) -> Word:
    return Word(text=text, start=start, end=end, probability=1.0)


def T(text: str, sentence_idx: int) -> ScriptToken:
    return ScriptToken(text=text, raw=text, sentence_idx=sentence_idx, char_offset=0)


CFG = RetakeConfig(
    triggers=["다시"],
    pre_margin=0.1,
    snap_margin=0.05,
    context_seconds_before=8.0,
    sentence_silence=0.6,
)


def test_simple_one_retake_drops_only_ng_attempt():
    # Script: "안녕하세요. 오늘 비트코인은 5만 달러입니다."
    tokens = [
        T("안녕하세요", 0),  # 0
        T("오늘", 1),         # 1
        T("비트코인은", 1),    # 2
        T("5만", 1),          # 3
        T("달러입니다", 1),    # 4
    ]
    # Spoken: "안녕하세요" / NG: "오늘 비트코인은 4만" "다시" / "오늘 비트코인은 5만 달러입니다"
    words = [
        W("안녕하세요", 0.0, 1.0),     # 0  -> 0
        W("오늘", 2.0, 2.3),            # 1  -> 1 (NG)
        W("비트코인은", 2.4, 3.0),      # 2  -> 2 (NG)
        W("4만", 3.1, 3.5),             # 3  -> None (NG)
        W("다시", 3.6, 3.9),            # 4  trigger
        W("오늘", 5.0, 5.3),            # 5  -> 1 (restart)
        W("비트코인은", 5.4, 6.0),      # 6  -> 2
        W("5만", 6.1, 6.5),             # 7  -> 3
        W("달러입니다", 6.6, 7.5),      # 8  -> 4
    ]
    alignment = Alignment(pairs=(
        (0, 0), (1, 1), (2, 2), (3, None), (4, None),
        (5, 1), (6, 2), (7, 3), (8, 4),
    ), confidence=0.78)

    drops = detect_drops(words, tokens, alignment, CFG)
    assert len(drops) == 1
    d = drops[0]
    # NG attempt starts at the first word aligned to sentence 1 (word index 1, t=2.0)
    # minus pre_margin (0.1) -> 1.9
    assert d.start == pytest.approx(1.9, abs=1e-6)
    # NG ends just before the restart word (idx 5, t=5.0) minus snap_margin (0.05) -> 4.95
    assert d.end == pytest.approx(4.95, abs=1e-6)


def test_in_script_dasi_is_not_dropped():
    tokens = [T("다시", 0), T("강조하지만", 0)]
    words = [
        W("다시", 0.0, 0.4),
        W("강조하지만", 0.5, 1.5),
    ]
    alignment = Alignment(pairs=((0, 0), (1, 1)), confidence=1.0)
    drops = detect_drops(words, tokens, alignment, CFG)
    assert drops == []


def test_two_consecutive_retakes_merge_into_one_drop():
    tokens = [T("오늘", 0), T("비트코인은", 0), T("5만", 0), T("달러", 0)]
    words = [
        W("오늘", 0.0, 0.3),       # 0 -> 0 attempt 1
        W("3만", 0.4, 0.7),        # 1 -> None
        W("다시", 0.8, 1.0),       # 2 trigger 1
        W("오늘", 1.5, 1.8),       # 3 -> 0 attempt 2
        W("4만", 1.9, 2.2),        # 4 -> None
        W("다시", 2.3, 2.5),       # 5 trigger 2
        W("오늘", 3.5, 3.8),       # 6 -> 0 final
        W("비트코인은", 3.9, 4.5),  # 7 -> 1
        W("5만", 4.6, 4.9),        # 8 -> 2
        W("달러", 5.0, 5.4),       # 9 -> 3
    ]
    alignment = Alignment(pairs=(
        (0, 0), (1, None), (2, None),
        (3, 0), (4, None), (5, None),
        (6, 0), (7, 1), (8, 2), (9, 3),
    ), confidence=0.6)
    drops = detect_drops(words, tokens, alignment, CFG)
    assert len(drops) == 1, f"expected merged drop, got {drops}"
    d = drops[0]
    assert d.start == pytest.approx(-0.1, abs=1e-6)  # word 0 start (0.0) - pre_margin
    assert d.end == pytest.approx(3.45, abs=1e-6)    # word 6 start (3.5) - snap_margin


def test_retake_at_video_start_uses_fallback():
    tokens = [T("오늘", 0), T("비트코인은", 0)]
    # No aligned word before "다시" at index 1.
    words = [
        W("3만", 0.0, 0.3),
        W("다시", 0.4, 0.7),
        W("오늘", 1.5, 1.8),
        W("비트코인은", 1.9, 2.5),
    ]
    alignment = Alignment(pairs=(
        (0, None), (1, None), (2, 0), (3, 1),
    ), confidence=0.5)
    drops = detect_drops(words, tokens, alignment, CFG)
    assert len(drops) == 1
    d = drops[0]
    # Fallback: drop covers from before the trigger up through it.
    assert d.start <= words[0].start
    assert d.end >= words[1].end - 1e-6


def test_keep_segments_invert_drops_correctly():
    src = Path("/tmp/fake.mp4")
    duration = 100.0
    drops = [
        type("D", (), {"start": 10.0, "end": 20.0, "reason": "retake"})(),
        type("D", (), {"start": 50.0, "end": 60.0, "reason": "retake"})(),
    ]
    keeps = build_keeps(src, duration, drops)  # type: ignore[arg-type]
    assert len(keeps) == 3
    assert keeps[0].source_start == 0.0 and keeps[0].source_end == 10.0
    assert keeps[1].source_start == 20.0 and keeps[1].source_end == 50.0
    assert keeps[2].source_start == 60.0 and keeps[2].source_end == 100.0


def test_no_triggers_returns_empty_drops():
    tokens = [T("안녕하세요", 0), T("오늘", 0)]
    words = [W("안녕하세요", 0.0, 1.0), W("오늘", 1.5, 2.0)]
    alignment = Alignment(pairs=((0, 0), (1, 1)), confidence=1.0)
    assert detect_drops(words, tokens, alignment, CFG) == []
