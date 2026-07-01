"""Command-line interface: generate / plot / animate / models."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(
    add_completion=False,
    help="Visualize a country's Narrow Corridor (state vs society power) trajectory with LLMs.",
)


@app.command()
def generate(
    country: str = typer.Option("Iran (Persia)", help="Country/region to analyze."),
    model: str = typer.Option(
        "gemini/gemini-3.5-flash", help="LiteLLM model string (see `ncorridor models`)."
    ),
    start: int = typer.Option(1880, help="First year."),
    end: int = typer.Option(2025, help="Last year."),
    step: int = typer.Option(5, help="Years per period."),
    out: Path = typer.Option(Path("runs/path.json"), help="Where to save the JSON result."),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass the on-disk response cache."),
):
    """Run the LLM pipeline and save the trajectory as JSON. This makes one or two
    model calls per period and can be expensive — results are cached by default."""
    from narrow_corridor.pipeline import get_narrow_corridor
    from narrow_corridor.storage import save_path

    path = get_narrow_corridor(
        model=model,
        country=country,
        start_year=start,
        end_year=end,
        step_years=step,
        use_cache=not no_cache,
    )
    saved = save_path(path, out)
    typer.echo(f"Saved {len(path.periods)} periods to {saved}")


@app.command()
def plot(
    run: Path = typer.Argument(..., help="Path JSON produced by `generate`."),
    out: Optional[Path] = typer.Option(None, help="Output image (e.g. runs/path.png)."),
    no_smooth: bool = typer.Option(False, "--no-smooth", help="Disable B-spline smoothing."),
    annotate_turns: int = typer.Option(
        3, help="Label this many of the biggest moves with year + event (0 to disable)."
    ),
    show: bool = typer.Option(False, help="Open an interactive window."),
):
    """Render the static society-vs-state plot with the corridor boundaries."""
    from narrow_corridor.plot import plot_path
    from narrow_corridor.storage import load_path

    path = load_path(run)
    plot_path(path, out, smooth=not no_smooth, annotate_turns=annotate_turns, show=show)
    if out:
        typer.echo(f"Wrote {out}")


@app.command()
def animate(
    run: Path = typer.Argument(..., help="Path JSON produced by `generate`."),
    out: Path = typer.Option(Path("runs/trajectory.gif"), help="Output GIF."),
    fps: float = typer.Option(0.5, help="Periods per second (0.5 = 2s per period)."),
):
    """Render an animated GIF tracing the trajectory with per-period event callouts."""
    from narrow_corridor.animate import animate_path
    from narrow_corridor.storage import load_path

    path = load_path(run)
    saved = animate_path(path, out, fps=fps)
    typer.echo(f"Wrote {saved}")


@app.command()
def models():
    """List suggested LiteLLM model strings and which API key each one needs."""
    from narrow_corridor.llm import env_status, known_models

    status = env_status()
    typer.echo("Suggested models (model string  ->  required env var):\n")
    for model, var in known_models():
        mark = "✓" if status.get(var) else "✗"
        typer.echo(f"  [{mark} {var:<18}] {model}")
    typer.echo("\n✓ = key found in environment/.env, ✗ = not set.")


if __name__ == "__main__":
    app()
