from fractions import Fraction
from pathlib import Path

import pytest

from autoedit.fcpxml import _quantize_rate, write_fcpxml
from autoedit.models import KeepSegment, VideoMeta
from autoedit.timeline import Timeline


def test_quantize_canonical_rates_match_adapter_table():
    assert _quantize_rate(Fraction(30000, 1001)) == 29.97
    assert _quantize_rate(Fraction(60000, 1001)) == 59.94
    assert _quantize_rate(Fraction(30, 1)) == 30.0
    assert _quantize_rate(Fraction(24, 1)) == 24.0


def test_write_fcpxml_produces_valid_structure(tmp_path: Path):
    src = tmp_path / "fake.mp4"
    src.write_bytes(b"\0" * 32)
    meta = VideoMeta(
        path=src, duration=120.0, fps=Fraction(30000, 1001),
        width=1920, height=1080, has_audio=True,
    )
    keeps = [
        (KeepSegment(source=src, source_start=5.0, source_end=15.0, reason="main"), meta),
        (KeepSegment(source=src, source_start=30.0, source_end=45.0, reason="main"), meta),
    ]
    tl = Timeline(fps=Fraction(30000, 1001), width=1920, height=1080, clips=keeps)
    out = tmp_path / "result.fcpxml"
    write_fcpxml(tl, out)

    text = out.read_text()
    # Frame duration must match the canonical 29.97 rational.
    assert 'frameDuration="1001/30000s"' in text
    # The asset must reference the actual source file.
    assert src.resolve().as_uri() in text
    # Sequence duration is the sum of keep durations (10 + 15 = 25).
    assert 'duration="25/1s"' in text
    # The two keeps appear in the spine.
    assert text.count("<clip ") >= 2


def test_write_fcpxml_dedupes_media_references_per_source(tmp_path: Path):
    src = tmp_path / "video.mp4"
    src.write_bytes(b"\0" * 32)
    meta = VideoMeta(
        path=src, duration=60.0, fps=Fraction(30, 1),
        width=1280, height=720, has_audio=True,
    )
    keeps = [
        (KeepSegment(source=src, source_start=0.0, source_end=5.0, reason="main"), meta),
        (KeepSegment(source=src, source_start=10.0, source_end=15.0, reason="main"), meta),
        (KeepSegment(source=src, source_start=20.0, source_end=25.0, reason="main"), meta),
    ]
    tl = Timeline(fps=Fraction(30, 1), width=1280, height=720, clips=keeps)
    out = tmp_path / "out.fcpxml"
    write_fcpxml(tl, out)
    text = out.read_text()
    # Only one <asset> entry should be created for the single source.
    assert text.count("<asset ") == 1
