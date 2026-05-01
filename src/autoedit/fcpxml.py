from __future__ import annotations

import logging
from pathlib import Path

from autoedit.timeline import Timeline

log = logging.getLogger(__name__)


def write_fcpxml(timeline: Timeline, output: Path) -> Path:
    """Write the timeline to an FCPXML file via OpenTimelineIO.

    Premiere Pro CC 2018+ supports FCPXML import (File → Import).
    """
    import opentimelineio as otio

    rate = timeline.fps
    rate_float = float(rate)
    tl = otio.schema.Timeline(name=output.stem)
    track = otio.schema.Track(name="V1", kind=otio.schema.TrackKind.Video)
    tl.tracks.append(track)
    audio_track = otio.schema.Track(name="A1", kind=otio.schema.TrackKind.Audio)
    tl.tracks.append(audio_track)

    for keep, meta in timeline.clips:
        media_ref = otio.schema.ExternalReference(
            target_url=keep.source.resolve().as_uri(),
            available_range=otio.opentime.TimeRange(
                start_time=otio.opentime.RationalTime(0, rate_float),
                duration=otio.opentime.RationalTime.from_seconds(meta.duration, rate_float),
            ),
        )
        source_range = otio.opentime.TimeRange(
            start_time=otio.opentime.RationalTime.from_seconds(keep.source_start, rate_float),
            duration=otio.opentime.RationalTime.from_seconds(
                keep.source_end - keep.source_start, rate_float
            ),
        )
        clip = otio.schema.Clip(
            name=f"{keep.source.stem}_{keep.reason}",
            media_reference=media_ref,
            source_range=source_range,
        )
        track.append(clip)
        if meta.has_audio:
            audio_clip = otio.schema.Clip(
                name=f"{keep.source.stem}_{keep.reason}_audio",
                media_reference=media_ref.deepcopy(),
                source_range=source_range,
            )
            audio_track.append(audio_clip)

    output.parent.mkdir(parents=True, exist_ok=True)
    adapter = _pick_fcpxml_adapter()
    log.info("Writing FCPXML via adapter '%s' -> %s", adapter, output)
    otio.adapters.write_to_file(tl, str(output), adapter_name=adapter)
    return output


def _pick_fcpxml_adapter() -> str:
    """Prefer the modern fcpx_xml adapter; fall back to fcp_xml (FCP7 XML/XMEML)."""
    import opentimelineio as otio
    available = set(otio.adapters.available_adapter_names())
    for name in ("fcpx_xml", "fcp_xml"):
        if name in available:
            return name
    raise RuntimeError(
        "No FCPXML adapter available in OpenTimelineIO. "
        "Install opentimelineio with FCPXML support."
    )
