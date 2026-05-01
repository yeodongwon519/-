from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path

from autoedit.config import STTConfig
from autoedit.models import TranscriptSegment, Word

log = logging.getLogger(__name__)


def transcribe(wav: Path, cache_path: Path, cfg: STTConfig) -> list[TranscriptSegment]:
    """Run faster-whisper with word timestamps. Caches result as JSON."""
    cache_key = {
        "model": cfg.model,
        "language": cfg.language,
        "vad": cfg.vad,
        "beam_size": cfg.beam_size,
        "compute_type": cfg.compute_type,
    }
    if cache_path.exists():
        with open(cache_path, encoding="utf-8") as f:
            cached = json.load(f)
        if cached.get("_key") == cache_key:
            log.info("Using cached transcript: %s", cache_path)
            return _deserialize(cached["segments"])
        log.info("Cache key mismatch; re-transcribing.")

    from faster_whisper import WhisperModel

    device, compute_type = _resolve_device(cfg)
    log.info("Loading faster-whisper model=%s device=%s compute_type=%s",
             cfg.model, device, compute_type)
    model = WhisperModel(cfg.model, device=device, compute_type=compute_type)

    log.info("Transcribing (this can take several minutes)...")
    segments_iter, info = model.transcribe(
        str(wav),
        language=cfg.language,
        beam_size=cfg.beam_size,
        vad_filter=cfg.vad,
        word_timestamps=True,
    )

    segments: list[TranscriptSegment] = []
    for s in segments_iter:
        words = tuple(
            Word(text=w.word.strip(), start=float(w.start), end=float(w.end),
                 probability=float(w.probability))
            for w in (s.words or [])
            if w.word.strip()
        )
        segments.append(TranscriptSegment(
            start=float(s.start),
            end=float(s.end),
            text=s.text.strip(),
            words=words,
        ))

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(
            {"_key": cache_key, "segments": _serialize(segments), "language": info.language},
            f, ensure_ascii=False, indent=2,
        )
    log.info("Wrote transcript to %s (%d segments)", cache_path, len(segments))
    return segments


def _resolve_device(cfg: STTConfig) -> tuple[str, str]:
    device = cfg.device
    compute_type = cfg.compute_type
    if device == "auto":
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            device = "cpu"
    if compute_type == "auto":
        compute_type = "int8_float16" if device == "cuda" else "int8"
    return device, compute_type


def _serialize(segments: list[TranscriptSegment]) -> list[dict]:
    return [
        {
            "start": s.start, "end": s.end, "text": s.text,
            "words": [asdict(w) for w in s.words],
        }
        for s in segments
    ]


def _deserialize(raw: list[dict]) -> list[TranscriptSegment]:
    return [
        TranscriptSegment(
            start=s["start"], end=s["end"], text=s["text"],
            words=tuple(Word(**w) for w in s["words"]),
        )
        for s in raw
    ]


def all_words(segments: list[TranscriptSegment]) -> list[Word]:
    out: list[Word] = []
    for s in segments:
        out.extend(s.words)
    return out
