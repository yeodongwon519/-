from fractions import Fraction
from pathlib import Path

from autoedit.models import KeepSegment
from autoedit.timeline import _merge_adjacent, _snap_to_frame


def test_snap_to_frame_rounds_to_29_97_grid():
    fps = Fraction(30000, 1001)  # 29.97
    src = Path("/tmp/x.mp4")
    keeps = [
        KeepSegment(source=src, source_start=1.001, source_end=2.002),
    ]
    snapped = _snap_to_frame(keeps, fps)
    assert len(snapped) == 1
    # 1.001s @ 29.97 fps == frame 30 exactly.
    assert abs(snapped[0].source_start - 30 / float(fps)) < 1e-9


def test_merge_adjacent_combines_touching_keeps():
    src = Path("/tmp/x.mp4")
    keeps = [
        KeepSegment(source=src, source_start=0.0, source_end=1.0),
        KeepSegment(source=src, source_start=1.0, source_end=2.0),
        KeepSegment(source=src, source_start=3.0, source_end=4.0),
    ]
    merged = _merge_adjacent(keeps)
    assert len(merged) == 2
    assert merged[0].source_start == 0.0 and merged[0].source_end == 2.0
    assert merged[1].source_start == 3.0 and merged[1].source_end == 4.0


def test_drops_under_one_frame_are_discarded():
    fps = Fraction(30, 1)
    src = Path("/tmp/x.mp4")
    keeps = [KeepSegment(source=src, source_start=0.0, source_end=0.001)]
    assert _snap_to_frame(keeps, fps) == []
