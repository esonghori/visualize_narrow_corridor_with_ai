"""Static rendering of a Narrow Corridor path in society-vs-state power space."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from scipy.interpolate import make_interp_spline

from narrow_corridor.models import NarrowCorridorPath

CMAP = "viridis"  # dark (early) -> bright (late), signifying passage of time


def _bounds(x: list[float], y: list[float]) -> tuple[float, float]:
    hi = max(max(x), max(y)) + 1.0
    lo = min(min(x), min(y)) - 1.0
    return lo, hi


def _draw_corridor(ax, lo: float, hi: float) -> None:
    """The book's *widening* corridor around the diagonal.

    In Acemoglu & Robinson the corridor is narrow where state and society are
    both weak (bottom-left) and widens as the two powers grow together
    (top-right): liberty gets easier to sustain once both are strong. We render
    that as a band whose half-width grows linearly along the diagonal, from
    narrow at ``lo`` to wide at ``hi``, so the two dashed boundaries diverge.
    """
    x_line = np.array([lo, hi])
    span = hi - lo
    w = np.array([span * 0.03, span * 0.18])  # narrow at bottom-left, wide at top-right
    ax.plot(x_line, x_line + w, "--", color="green")
    ax.plot(x_line, x_line - w, "--", color="green")


def _gradient_line(ax, x, y, *, smooth: bool = True, clim: tuple[float, float]) -> None:
    """Draw the path as a line whose color ramps with time (via CMAP + clim).

    Optionally B-spline smoothed (the same curve for PNG and GIF). `clim` fixes
    the color scale to absolute period indices so shades are stable frame-to-frame.
    """
    n = len(x)
    if smooth and n > 2:
        t = np.arange(n)
        ts = np.linspace(0, t.max(), 300)
        k = min(3, n - 1)  # cubic needs >=4 points; drop degree for short reveals
        xs, ys, vals = make_interp_spline(t, x, k=k)(ts), make_interp_spline(t, y, k=k)(ts), ts
    else:
        xs, ys, vals = np.asarray(x, float), np.asarray(y, float), np.arange(n, dtype=float)
    if len(xs) < 2:
        return
    pts = np.array([xs, ys]).T.reshape(-1, 1, 2)
    segs = np.concatenate([pts[:-1], pts[1:]], axis=1)
    lc = LineCollection(segs, cmap=CMAP, array=(vals[:-1] + vals[1:]) / 2)
    lc.set_linewidth(2)
    lc.set_clim(*clim)
    ax.add_collection(lc)
    return lc


def _time_points(ax, x, y, *, n_total: int) -> None:
    """Scatter the period points colored by time on the same scale as the line."""
    ax.scatter(
        x, y, c=range(len(x)), cmap=CMAP, vmin=0, vmax=n_total - 1,
        zorder=3, edgecolors="white", linewidths=0.4,
    )


def _year_colorbar(fig, ax, mappable, periods) -> None:
    """Colorbar mapping the time gradient to years (no overlap with the path)."""
    n = len(periods)
    cbar = fig.colorbar(mappable, ax=ax, fraction=0.046, pad=0.04)
    ticks = sorted({int(t) for t in np.linspace(0, n - 1, min(n, 8)).round()})
    cbar.set_ticks(ticks)
    cbar.set_ticklabels([str(periods[t][0]) for t in ticks])
    cbar.set_label("Year")


def _annotate_turns(ax, x, y, periods, key_event, k: int) -> None:
    """Label the k largest moves with 'year: event', offset away from the centroid."""
    if k <= 0 or len(x) < 2:
        return
    moves = sorted(((np.hypot(x[i] - x[i - 1], y[i] - y[i - 1]), i) for i in range(1, len(x))),
                   reverse=True)
    cx, cy = np.mean(x), np.mean(y)
    for rank, (_, i) in enumerate(sorted(moves[:k], key=lambda m: m[1])):
        event = key_event.get(periods[i], "")
        label = f"{periods[i][0]}" + (f": {event[:24]}…" if len(event) > 24 else f": {event}" if event else "")
        # Horizontal offset toward the interior keeps text on-canvas (clear of the
        # colorbar); vertical offset away from center + a per-label stagger keeps
        # nearby callouts from stacking.
        dx = 20 if x[i] < cx else -20
        vsign = 1 if y[i] >= cy else -1
        dy = vsign * (16 + 12 * rank)
        ax.annotate(
            label, (x[i], y[i]), textcoords="offset points", xytext=(dx, dy),
            ha="left" if dx > 0 else "right", va="bottom" if dy > 0 else "top",
            fontsize=8,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="0.7", alpha=0.85),
            arrowprops=dict(arrowstyle="-", color="0.6", lw=0.6),
        )


def plot_path(
    path: NarrowCorridorPath,
    filename: Optional[str | Path] = None,
    *,
    smooth: bool = True,
    annotate_turns: int = 3,
    show: bool = False,
):
    """Plot society power (x) vs state power (y), time-shaded, optionally smoothed.

    A year colorbar labels the time gradient; `annotate_turns` labels that many
    of the largest moves with their year and key event (0 to disable).
    """
    fig, ax = plt.subplots(figsize=(10, 10))

    x = [path.society_power[p] for p in path.periods]
    y = [path.state_power[p] for p in path.periods]
    lo, hi = _bounds(x, y)
    clim = (0, len(x) - 1)

    lc = _gradient_line(ax, x, y, smooth=smooth, clim=clim)
    _time_points(ax, x, y, n_total=len(x))
    _draw_corridor(ax, lo, hi)
    _annotate_turns(ax, x, y, path.periods, path.key_event, annotate_turns)

    ax.set_xlabel("Society Power")
    ax.set_ylabel("State Power")
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_xticks([])
    ax.set_yticks([])
    m = (path.model or "").lower()
    tag = (" (ensemble mean)" if m.startswith("ensemble")
           else " (V-Dem)" if m.startswith(("v-dem", "vdem")) else "")
    ax.set_title(f"State vs Society Power in {path.country}{tag}")
    if lc is not None:
        _year_colorbar(fig, ax, lc, path.periods)

    if filename:
        out = Path(filename)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, bbox_inches="tight")
    if show:
        plt.show()
    return fig
