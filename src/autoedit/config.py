from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclass
class STTConfig:
    model: str = "large-v3"
    language: str = "ko"
    device: str = "auto"
    compute_type: str = "auto"
    vad: bool = True
    beam_size: int = 5


@dataclass
class RetakeConfig:
    triggers: list[str] = field(default_factory=lambda: ["다시"])
    pre_margin: float = 0.15
    snap_margin: float = 0.05
    context_seconds_before: float = 8.0
    sentence_silence: float = 0.6


@dataclass
class SilenceConfig:
    enable: bool = False
    threshold_db: float = -35.0
    max_keep_silence: float = 0.6


@dataclass
class LLMConfig:
    enable_alignment_assist: bool = False
    model: str = "claude-opus-4-7"
    chunk_seconds: int = 60


@dataclass
class OutputConfig:
    fcpxml_version: str = "1.10"
    fps: str = "auto"


@dataclass
class Config:
    stt: STTConfig = field(default_factory=STTConfig)
    retake: RetakeConfig = field(default_factory=RetakeConfig)
    silence: SilenceConfig = field(default_factory=SilenceConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    output: OutputConfig = field(default_factory=OutputConfig)


def load_config(path: Path | None) -> Config:
    if path is None:
        return Config()
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    cfg = Config()
    if "stt" in raw:
        cfg.stt = STTConfig(**raw["stt"])
    if "retake" in raw:
        cfg.retake = RetakeConfig(**raw["retake"])
    if "silence" in raw:
        cfg.silence = SilenceConfig(**raw["silence"])
    if "llm" in raw:
        cfg.llm = LLMConfig(**raw["llm"])
    if "output" in raw:
        cfg.output = OutputConfig(**raw["output"])
    return cfg
