from __future__ import annotations

import json
import logging
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path

from autoedit.models import VideoMeta

log = logging.getLogger(__name__)


def _ffmpeg_bin() -> str:
    bin_path = shutil.which("ffmpeg")
    if not bin_path:
        raise RuntimeError("ffmpeg not found on PATH. Install FFmpeg and retry.")
    return bin_path


def _ffprobe_bin() -> str:
    bin_path = shutil.which("ffprobe")
    if not bin_path:
        raise RuntimeError("ffprobe not found on PATH. Install FFmpeg and retry.")
    return bin_path


def probe_video(video: Path) -> VideoMeta:
    """Probe video for fps, duration, resolution, audio presence."""
    cmd = [
        _ffprobe_bin(),
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(video),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    video_stream = next((s for s in streams if s["codec_type"] == "video"), None)
    audio_stream = next((s for s in streams if s["codec_type"] == "audio"), None)
    if not video_stream:
        raise ValueError(f"No video stream in {video}")
    rate_str = video_stream.get("r_frame_rate", "30/1")
    num, den = rate_str.split("/")
    fps = Fraction(int(num), int(den) or 1)
    duration = float(data["format"]["duration"])
    return VideoMeta(
        path=video,
        duration=duration,
        fps=fps,
        width=int(video_stream["width"]),
        height=int(video_stream["height"]),
        has_audio=audio_stream is not None,
    )


def extract_audio(video: Path, out_wav: Path, sr: int = 16000) -> Path:
    """Extract mono PCM WAV at sr Hz. Skips if up-to-date."""
    if out_wav.exists() and out_wav.stat().st_mtime >= video.stat().st_mtime:
        log.info("Reusing cached audio: %s", out_wav)
        return out_wav
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        _ffmpeg_bin(),
        "-y",
        "-i", str(video),
        "-vn",
        "-ac", "1",
        "-ar", str(sr),
        "-c:a", "pcm_s16le",
        str(out_wav),
    ]
    log.info("Extracting audio to %s", out_wav)
    subprocess.run(cmd, check=True, capture_output=True)
    return out_wav
