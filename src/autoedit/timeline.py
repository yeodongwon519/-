from __future__ import annotations

import logging
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from autoedit.audio import probe_video
from autoedit.models import KeepSegment, VideoMeta

log = logging.getLogger(__name__)


@dataclass
class Timeline:
    fps: Fraction
    width: int
    height: int
    clips: list[tuple[KeepSegment, VideoMeta]]

    @property
    def total_duration(self) -> float:
        return sum(c.duration for c, _ in self.clips)


def assemble(
    keeps: list[KeepSegment],
    intro: Path | None,
    outro: Path | None,
    fps_override: Fraction | None = None,
) -> Timeline:
    """Combine intro + keeps + outro into a Timeline. fps/dimensions come from main clip."""
    if not keeps:
        raise ValueError("No keep segments to assemble.")

    main_meta = probe_video(keeps[0].source)
    fps = fps_override or main_meta.fps

    clips: list[tuple[KeepSegment, VideoMeta]] = []

    if intro is not None:
        intro_meta = probe_video(intro)
        _warn_mismatch("intro", intro_meta, main_meta)
        clips.append((
            KeepSegment(source=intro, source_start=0.0,
                        source_end=intro_meta.duration, reason="intro"),
            intro_meta,
        ))

    keeps_snapped = _snap_to_frame(keeps, fps)
    keeps_snapped = _merge_adjacent(keeps_snapped)
    for k in keeps_snapped:
        clips.append((k, main_meta))

    if outro is not None:
        outro_meta = probe_video(outro)
        _warn_mismatch("outro", outro_meta, main_meta)
        clips.append((
            KeepSegment(source=outro, source_start=0.0,
                        source_end=outro_meta.duration, reason="outro"),
            outro_meta,
        ))

    return Timeline(fps=fps, width=main_meta.width, height=main_meta.height, clips=clips)


def _warn_mismatch(label: str, meta: VideoMeta, ref: VideoMeta) -> None:
    if meta.fps != ref.fps:
        log.warning("%s fps %s != main fps %s (Premiere may conform)", label, meta.fps, ref.fps)
    if (meta.width, meta.height) != (ref.width, ref.height):
        log.warning(
            "%s resolution %dx%d != main %dx%d (Premiere may scale)",
            label, meta.width, meta.height, ref.width, ref.height,
        )


def _snap_to_frame(keeps: list[KeepSegment], fps: Fraction) -> list[KeepSegment]:
    """Snap each keep boundary to the nearest frame so Premiere doesn't round it."""
    fps_f = float(fps)
    out: list[KeepSegment] = []
    for k in keeps:
        start = round(k.source_start * fps_f) / fps_f
        end = round(k.source_end * fps_f) / fps_f
        if end - start < 1.0 / fps_f:
            continue
        out.append(KeepSegment(
            source=k.source, source_start=start, source_end=end, reason=k.reason,
        ))
    return out


def _merge_adjacent(keeps: list[KeepSegment]) -> list[KeepSegment]:
    if not keeps:
        return []
    out = [keeps[0]]
    for k in keeps[1:]:
        last = out[-1]
        if (k.source == last.source and k.reason == last.reason
                and abs(k.source_start - last.source_end) < 1e-6):
            out[-1] = KeepSegment(
                source=last.source,
                source_start=last.source_start,
                source_end=k.source_end,
                reason=last.reason,
            )
        else:
            out.append(k)
    return out
