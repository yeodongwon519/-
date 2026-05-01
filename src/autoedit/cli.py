from __future__ import annotations

import logging
from pathlib import Path

import typer

from autoedit.config import load_config
from autoedit.logging_setup import setup_logging
from autoedit import pipeline

app = typer.Typer(add_completion=False, help="Auto-edit Korean one-take videos into FCPXML for Premiere Pro.")

log = logging.getLogger(__name__)


def _config_option() -> typer.Option:
    return typer.Option(None, "--config", "-c", help="Path to config.toml")


@app.callback()
def _root(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    setup_logging(verbose=verbose)


@app.command()
def run(
    video: Path = typer.Option(..., exists=True, dir_okay=False, readable=True),
    script: Path = typer.Option(..., exists=True, dir_okay=False, readable=True),
    output: Path = typer.Option(..., help="Output .fcpxml path"),
    intro: Path = typer.Option(None, exists=True, dir_okay=False),
    outro: Path = typer.Option(None, exists=True, dir_okay=False),
    config: Path = typer.Option(None, "--config", "-c"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate inputs and exit"),
) -> None:
    """Run the full pipeline: transcribe -> align -> cuts -> export FCPXML."""
    cfg = load_config(config)
    if dry_run:
        from autoedit.audio import probe_video
        meta = probe_video(video)
        typer.echo(f"video: {video} ({meta.duration:.1f}s, {meta.width}x{meta.height} @ {meta.fps})")
        typer.echo(f"script: {script} ({script.stat().st_size} bytes)")
        typer.echo(f"output: {output}")
        if intro: typer.echo(f"intro: {intro}")
        if outro: typer.echo(f"outro: {outro}")
        return
    pipeline.run_full(video, script, output, cfg, intro, outro)
    typer.echo(f"Wrote {output}")


@app.command()
def transcribe(
    video: Path = typer.Option(..., exists=True, dir_okay=False),
    config: Path = typer.Option(None, "--config", "-c"),
) -> None:
    """Run STT only and cache the transcript."""
    cfg = load_config(config)
    path = pipeline.stage_transcribe(video, cfg)
    typer.echo(str(path))


@app.command()
def align(
    video: Path = typer.Option(..., exists=True, dir_okay=False),
    script: Path = typer.Option(..., exists=True, dir_okay=False),
    config: Path = typer.Option(None, "--config", "-c"),
) -> None:
    """Run STT (cached) and alignment."""
    cfg = load_config(config)
    tokens_path, align_path = pipeline.stage_align(video, script, cfg)
    typer.echo(f"tokens: {tokens_path}")
    typer.echo(f"alignment: {align_path}")


@app.command()
def cuts(
    video: Path = typer.Option(..., exists=True, dir_okay=False),
    script: Path = typer.Option(..., exists=True, dir_okay=False),
    config: Path = typer.Option(None, "--config", "-c"),
) -> None:
    """Run pipeline up to cut decision and emit cuts.json."""
    cfg = load_config(config)
    path = pipeline.stage_cuts(video, script, cfg)
    typer.echo(str(path))


@app.command()
def export(
    video: Path = typer.Option(..., exists=True, dir_okay=False),
    cuts: Path = typer.Option(..., exists=True, dir_okay=False),
    output: Path = typer.Option(...),
    intro: Path = typer.Option(None, exists=True, dir_okay=False),
    outro: Path = typer.Option(None, exists=True, dir_okay=False),
    config: Path = typer.Option(None, "--config", "-c"),
) -> None:
    """Export an FCPXML from an existing cuts.json."""
    cfg = load_config(config)
    path = pipeline.stage_export(video, cuts, output, cfg, intro, outro)
    typer.echo(str(path))


if __name__ == "__main__":
    app()
