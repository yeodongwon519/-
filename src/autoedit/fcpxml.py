from __future__ import annotations

import logging
from fractions import Fraction
from pathlib import Path

from autoedit.timeline import Timeline

log = logging.getLogger(__name__)

# The otio-fcpx-xml-adapter looks up frameDuration in a dict keyed by
# rounded float fps values. Pass the canonical float so the lookup hits.
_CANONICAL_RATE: dict[Fraction, float] = {
    Fraction(24000, 1001): 23.98,
    Fraction(24, 1): 24.0,
    Fraction(25, 1): 25.0,
    Fraction(30000, 1001): 29.97,
    Fraction(30, 1): 30.0,
    Fraction(50, 1): 50.0,
    Fraction(60000, 1001): 59.94,
    Fraction(60, 1): 60.0,
}


def _quantize_rate(rate: Fraction) -> float:
    if rate in _CANONICAL_RATE:
        return _CANONICAL_RATE[rate]
    log.warning("Non-canonical fps %s; FCPXML may need manual format fix.", rate)
    return float(rate)


def write_fcpxml(timeline: Timeline, output: Path) -> Path:
    """Write the timeline to an FCPXML file via OpenTimelineIO.

    Premiere Pro CC 2018+ supports FCPXML import (File → Import).
    """
    import opentimelineio as otio

    rate = timeline.fps
    rate_float = _quantize_rate(rate)
    tl = otio.schema.Timeline(name=output.stem)
    track = otio.schema.Track(name="V1", kind=otio.schema.TrackKind.Video)
    tl.tracks.append(track)

    # Reuse the same media reference per source path so FCPXML resources stay deduped.
    refs: dict[Path, "otio.schema.ExternalReference"] = {}
    for keep, meta in timeline.clips:
        if keep.source not in refs:
            refs[keep.source] = otio.schema.ExternalReference(
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
            media_reference=refs[keep.source],
            source_range=source_range,
        )
        track.append(clip)

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
