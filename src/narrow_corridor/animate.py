"""Animated GIF of a Narrow Corridor trajectory with per-period event callouts.

Each frame reveals the path up to one more period, highlights the new point,
draws an arrow showing the move that period's key event caused, and captions it.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import fill

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

from narrow_corridor.models import NarrowCorridorPath, period_to_text
from narrow_corridor.plot import (
    CMAP,
    _bounds,
    _draw_corridor,
    _gradient_line,
    _time_points,
    _year_colorbar,
)


def animate_path(
    path: NarrowCorridorPath,
    filename: str | Path = "trajectory.gif",
    *,
    fps: float = 0.5,
) -> Path:
    """Render the trajectory to an animated GIF (fps = periods per second).

    Default 0.5 fps = two seconds per period, giving the viewer time to read
    each period's event caption before the path advances.
    """
    periods = path.periods
    x = [path.society_power[p] for p in periods]
    y = [path.state_power[p] for p in periods]
    lo, hi = _bounds(x, y)

    fig, ax = plt.subplots(figsize=(10, 10))
    n = len(periods)
    frames = list(range(n)) + [n - 1] * 3  # hold the finished path briefly before looping

    # Static year colorbar (same every frame; ax.clear() in draw() leaves it intact).
    sm = plt.cm.ScalarMappable(cmap=CMAP, norm=plt.Normalize(0, n - 1))
    sm.set_array([])
    _year_colorbar(fig, ax, sm, periods)

    def draw(i: int) -> None:
        ax.clear()
        ax.set_xlim(lo, hi)
        ax.set_ylim(lo, hi)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlabel("Society Power")
        ax.set_ylabel("State Power")
        ax.set_title(f"State vs Society Power in {path.country}")
        _draw_corridor(ax, lo, hi)

        # path revealed so far: same smoothed curve as the PNG, time-shaded.
        # clim/n_total span the full run so shades stay stable across frames.
        _gradient_line(ax, x[: i + 1], y[: i + 1], smooth=True, clim=(0, n - 1))
        _time_points(ax, x[: i + 1], y[: i + 1], n_total=n)

        # arrow showing the move the current period's event caused
        if i > 0:
            ax.annotate(
                "",
                xy=(x[i], y[i]),
                xytext=(x[i - 1], y[i - 1]),
                arrowprops=dict(arrowstyle="-|>", color="crimson", lw=2),
            )

        # current point highlighted
        ax.plot([x[i]], [y[i]], "o", color="crimson", markersize=12)

        # caption: period + key event
        period = periods[i]
        event = path.key_event.get(period, "")
        caption = f"{period_to_text(period)}"
        if event:
            caption += f"\n{fill(event, width=46)}"
        ax.text(
            0.5,
            0.02,
            caption,
            transform=ax.transAxes,
            ha="center",
            va="bottom",
            fontsize=12,
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.85),
        )

    anim = FuncAnimation(fig, draw, frames=frames, interval=1000 / max(fps, 0.01))

    out = Path(filename)
    out.parent.mkdir(parents=True, exist_ok=True)
    anim.save(out, writer=PillowWriter(fps=fps))
    plt.close(fig)
    return out
