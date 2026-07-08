#!/usr/bin/env python3
"""Conceptual schematic of the Narrow Corridor: the widening corridor and the
four Leviathan regions, drawn in the same (society, state) style as our atlases.

    uv run python paper/experiments/corridor_schematic.py

A framework diagram (no data, no LLM calls) for the paper's Method section and
the README. Writes paper/experiments/results/corridor-schematic.png.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from narrow_corridor.plot import _draw_corridor
from run_experiments import RUNS_DIR

LO, HI = 0.0, 10.0

# Region labels placed as in Acemoglu & Robinson: Despotic above the corridor,
# Shackled inside it near the top, Paper a weak state near the origin, Absent
# below the corridor. (x, y, ha) in society/state units.
REGIONS = [
    ("Despotic\nLeviathan", 2.0, 8.3, "center"),
    ("Shackled\nLeviathan", 8.0, 8.0, "center"),  # on the x=y diagonal, inside the corridor
    ("Paper\nLeviathan", 1.4, 1.7, "left"),
    ("Absent\nLeviathan", 7.4, 1.5, "center"),
]

# Curved guide arrows (start -> end, arc curvature) pointing into a region.
ARROWS = [
    ((3.6, 5.6), (2.5, 7.4), 0.35),   # up-left, toward Despotic
    ((5.4, 4.0), (6.7, 2.4), -0.35),  # down-right, toward Absent (mirrored)
]
# A country's path climbing the corridor: a wavy S (two curves) up the diagonal.
PATH = ((3.0, 2.8), (6.9, 7.0), 0.4, 2)  # start, end, wave amplitude, half-periods


def main() -> None:
    fig, ax = plt.subplots(figsize=(10, 10))
    _draw_corridor(ax, LO, HI)

    for text, x, y, ha in REGIONS:
        ax.text(x, y, text, fontsize=16, style="italic", color="0.2",
                ha=ha, va="center", zorder=3)

    for (x0, y0), (x1, y1), rad in ARROWS:
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="-|>", color="0.35", lw=1.4,
                                    connectionstyle=f"arc3,rad={rad}"), zorder=2)

    # wavy S-shaped path climbing the corridor: base diagonal + perpendicular sine
    (px0, py0), (px1, py1), amp, halfp = PATH
    t = np.linspace(0, 1, 200)
    bx, by = px0 + t * (px1 - px0), py0 + t * (py1 - py0)
    dx, dy = px1 - px0, py1 - py0
    L = np.hypot(dx, dy)
    nx, ny = -dy / L, dx / L                     # unit perpendicular
    off = amp * np.sin(halfp * np.pi * t)        # halfp half-periods -> two curves
    wx, wy = bx + nx * off, by + ny * off
    ax.plot(wx[:-1], wy[:-1], color="0.35", lw=1.4, zorder=2)
    ax.annotate("", xy=(wx[-1], wy[-1]), xytext=(wx[-3], wy[-3]),
                arrowprops=dict(arrowstyle="-|>", color="0.35", lw=1.4), zorder=2)

    ax.set_xlim(LO, HI)
    ax.set_ylim(LO, HI)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("Power of Society", fontsize=14)
    ax.set_ylabel("Power of the State", fontsize=14)

    out = RUNS_DIR / "corridor-schematic.png"
    fig.savefig(out, bbox_inches="tight", dpi=150)
    print(f"-> {out}")


if __name__ == "__main__":
    main()
