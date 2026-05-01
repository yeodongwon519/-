from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path


@dataclass(frozen=True)
class Word:
    text: str
    start: float
    end: float
    probability: float = 1.0


@dataclass(frozen=True)
class TranscriptSegment:
    start: float
    end: float
    text: str
    words: tuple[Word, ...]


@dataclass(frozen=True)
class ScriptToken:
    text: str
    raw: str
    sentence_idx: int
    char_offset: int


@dataclass(frozen=True)
class Alignment:
    pairs: tuple[tuple[int, int | None], ...]
    confidence: float = 1.0


@dataclass(frozen=True)
class KeepSegment:
    source: Path
    source_start: float
    source_end: float
    reason: str = "main"

    @property
    def duration(self) -> float:
        return self.source_end - self.source_start


@dataclass(frozen=True)
class DropSegment:
    start: float
    end: float
    reason: str


@dataclass
class CutDecision:
    keeps: list[KeepSegment] = field(default_factory=list)
    drops: list[DropSegment] = field(default_factory=list)


@dataclass(frozen=True)
class VideoMeta:
    path: Path
    duration: float
    fps: Fraction
    width: int
    height: int
    has_audio: bool
