from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path

from autoedit.config import SilenceConfig
from autoedit.models import KeepSegment

log = logging.getLogger(__name__)

_RE_START = re.compile(r"silence_start: (\-?\d+(?:\.\d+)?)")
_RE_END = re.compile(r"silence_end: (\-?\d+(?:\.\d+)?)")


def detect_silences(wav: Path, cfg: SilenceConfig) -> list[tuple[float, float]]:
    """Run FFmpeg's silencedetect filter and parse stderr for silence ranges."""
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not on PATH")
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats",
        "-i", str(wav),
        "-af", f"silencedetect=noise={cfg.threshold_db}dB:d={cfg.max_keep_silence}",
        "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    silences: list[tuple[float, float]] = []
    current_start: float | None = None
    for line in result.stderr.splitlines():
        if (m := _RE_START.search(line)):
            current_start = float(m.group(1))
        elif (m := _RE_END.search(line)) and current_start is not None:
            silences.append((current_start, float(m.group(1))))
            current_start = None
    return silences


def trim_long_silences(
    keeps: list[KeepSegment],
    silences: list[tuple[float, float]],
    cfg: SilenceConfig,
) -> list[KeepSegment]:
    """Cut silence intervals out of keep segments while leaving cfg.max_keep_silence headroom."""
    if not cfg.enable or not silences:
        return keeps
    out: list[KeepSegment] = []
    for k in keeps:
        out.extend(_split_keep(k, silences, cfg.max_keep_silence))
    return out


def _split_keep(
    k: KeepSegment, silences: list[tuple[float, float]], max_silence: float,
) -> list[KeepSegment]:
    cursor = k.source_start
    pieces: list[KeepSegment] = []
    for s_start, s_end in silences:
        if s_end <= k.source_start or s_start >= k.source_end:
            continue
        s_start = max(s_start, k.source_start)
        s_end = min(s_end, k.source_end)
        if s_end - s_start <= max_silence:
            continue
        keep_until = s_start + max_silence / 2
        if keep_until > cursor:
            pieces.append(KeepSegment(
                source=k.source, source_start=cursor,
                source_end=keep_until, reason=k.reason,
            ))
        cursor = max(cursor, s_end - max_silence / 2)
    if cursor < k.source_end:
        pieces.append(KeepSegment(
            source=k.source, source_start=cursor,
            source_end=k.source_end, reason=k.reason,
        ))
    return pieces
