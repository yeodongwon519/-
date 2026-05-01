from __future__ import annotations

import json
import logging
from dataclasses import asdict
from fractions import Fraction
from pathlib import Path

from autoedit.align import align, load_alignment, load_tokens, save_alignment, save_tokens, tokenize_script
from autoedit.audio import extract_audio, probe_video
from autoedit.config import Config
from autoedit.fcpxml import write_fcpxml
from autoedit.hashing import cache_dir_for
from autoedit.models import CutDecision, DropSegment, KeepSegment
from autoedit.retake import build_decision
from autoedit.silence import detect_silences, trim_long_silences
from autoedit.timeline import assemble
from autoedit.transcribe import all_words, transcribe

log = logging.getLogger(__name__)


def stage_audio(video: Path) -> tuple[Path, Path]:
    cache = cache_dir_for(video)
    wav = cache / "audio.wav"
    extract_audio(video, wav)
    return wav, cache


def stage_transcribe(video: Path, cfg: Config) -> Path:
    wav, cache = stage_audio(video)
    transcript_path = cache / "transcript.json"
    transcribe(wav, transcript_path, cfg.stt)
    return transcript_path


def stage_align(video: Path, script: Path, cfg: Config) -> tuple[Path, Path]:
    cache = cache_dir_for(video)
    transcript_path = stage_transcribe(video, cfg)
    from autoedit.transcribe import _deserialize  # type: ignore
    with open(transcript_path, encoding="utf-8") as f:
        segments = _deserialize(json.load(f)["segments"])
    words = all_words(segments)
    script_text = script.read_text(encoding="utf-8")
    tokens = tokenize_script(script_text)
    alignment = align(words, tokens)
    tokens_path = cache / "tokens.json"
    align_path = cache / "alignment.json"
    save_tokens(tokens, tokens_path)
    save_alignment(alignment, align_path)
    return tokens_path, align_path


def stage_cuts(video: Path, script: Path, cfg: Config) -> Path:
    cache = cache_dir_for(video)
    tokens_path, align_path = stage_align(video, script, cfg)
    transcript_path = cache / "transcript.json"
    from autoedit.transcribe import _deserialize  # type: ignore
    with open(transcript_path, encoding="utf-8") as f:
        segments = _deserialize(json.load(f)["segments"])
    words = all_words(segments)
    tokens = load_tokens(tokens_path)
    alignment = load_alignment(align_path)

    meta = probe_video(video)
    decision = build_decision(
        source=video.resolve(), duration=meta.duration,
        words=words, tokens=tokens, alignment=alignment, cfg=cfg.retake,
    )

    if cfg.silence.enable:
        wav = cache / "audio.wav"
        silences = detect_silences(wav, cfg.silence)
        decision.keeps = trim_long_silences(decision.keeps, silences, cfg.silence)

    cuts_path = cache / "cuts.json"
    _save_decision(decision, cuts_path)
    log.info("Wrote cuts: %d keeps, %d drops -> %s",
             len(decision.keeps), len(decision.drops), cuts_path)
    return cuts_path


def stage_export(
    video: Path,
    cuts: Path,
    output: Path,
    cfg: Config,
    intro: Path | None,
    outro: Path | None,
) -> Path:
    decision = _load_decision(cuts)
    fps_override = _parse_fps(cfg.output.fps)
    timeline = assemble(decision.keeps, intro, outro, fps_override=fps_override)
    return write_fcpxml(timeline, output)


def run_full(
    video: Path,
    script: Path,
    output: Path,
    cfg: Config,
    intro: Path | None,
    outro: Path | None,
) -> Path:
    cuts_path = stage_cuts(video, script, cfg)
    return stage_export(video, cuts_path, output, cfg, intro, outro)


def _parse_fps(value: str) -> Fraction | None:
    if value == "auto":
        return None
    if "/" in value:
        n, d = value.split("/")
        return Fraction(int(n), int(d))
    return Fraction(value)


def _save_decision(decision: CutDecision, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "keeps": [
                {
                    "source": str(k.source),
                    "source_start": k.source_start,
                    "source_end": k.source_end,
                    "reason": k.reason,
                }
                for k in decision.keeps
            ],
            "drops": [asdict(d) for d in decision.drops],
        }, f, ensure_ascii=False, indent=2)


def _load_decision(path: Path) -> CutDecision:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    keeps = [
        KeepSegment(
            source=Path(k["source"]),
            source_start=k["source_start"],
            source_end=k["source_end"],
            reason=k["reason"],
        )
        for k in raw["keeps"]
    ]
    drops = [DropSegment(**d) for d in raw["drops"]]
    return CutDecision(keeps=keeps, drops=drops)
