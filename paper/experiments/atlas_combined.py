#!/usr/bin/env python3
"""All countries on one map: each country's final (2020) position, over the
book's labeled Leviathan regions.

    uv run python paper/experiments/atlas_combined.py

The book plots countries in a single (society, state) plane divided into regions
(Despotic / Shackled / Absent Leviathan) by a widening corridor. Because every
run is scored against the *same* fixed 0--10 rubric (prompts.RUBRIC), the numbers
are already on a common scale, so we can drop each country's end-of-trajectory
(2020) point into that shared plane directly and read off which region it lands
in. This is the test of whether the shared rubric yields sensible *relative*
cross-country placement. Needs the ensemble-mean runs (run ensemble.py first).
No LLM calls.
"""

from __future__ import annotations

import matplotlib.pyplot as plt

from narrow_corridor.plot import _draw_corridor
from narrow_corridor.storage import load_path
from run_experiments import COUNTRIES, RUNS_DIR, slug

LO, HI = 0.0, 10.0  # fixed rubric quadrant, origin-anchored like the book's figure

# Region labels at the same positions as the conceptual schematic
# (corridor_schematic.py), so the two figures line up: Despotic above the
# corridor, Shackled inside it, Absent in the weak-state region below.
REGIONS = [
    ("Despotic\nLeviathan", 2.0, 8.3, "center"),
    ("Shackled\nLeviathan", 8.0, 8.0, "center"),
    ("Absent\nLeviathan", 7.2, 1.6, "center"),
]


def main() -> None:
    paths = []
    for country in COUNTRIES:
        f = RUNS_DIR / f"{slug(country)}__ensemble-mean.json"
        if f.exists():
            paths.append(load_path(f))
        else:
            print(f"(skip {country}: no ensemble-mean run; run ensemble.py first)")
    if not paths:
        print(f"No ensemble-mean runs in {RUNS_DIR}. Run ensemble.py first.")
        return

    fig, ax = plt.subplots(figsize=(10, 10))
    _draw_corridor(ax, LO, HI)

    # region labels (light, like the book's hand annotations)
    for text, x, y, ha in REGIONS:
        ax.text(x, y, text, fontsize=13, style="italic", color="0.35",
                ha=ha, va="center", zorder=1)

    # one point per country: its final (2020) position, labeled
    colors = plt.get_cmap("tab20").colors  # >10 distinct colors for 11+ countries
    for i, p in enumerate(paths):
        per = p.periods[-1]
        x, y = p.society_power[per], p.state_power[per]
        c = colors[i % len(colors)]
        ax.scatter(x, y, color=c, s=90, zorder=3, edgecolors="white", linewidths=0.6)
        ax.annotate(p.country, (x, y), textcoords="offset points", xytext=(10, 0),
                    color=c, fontsize=10, va="center", ha="left",
                    fontweight="bold", zorder=4)

    ax.set_xlim(LO, HI)
    ax.set_ylim(LO, HI)
    ax.set_xlabel("Power of Society")
    ax.set_ylabel("Power of the State")
    ax.set_title("Where each country sits in 2020 (ensemble mean, shared rubric)")

    out = RUNS_DIR / "all-countries__ensemble-mean.png"
    fig.savefig(out, bbox_inches="tight")
    print(f"{len(paths)} countries -> {out.name}")


if __name__ == "__main__":
    main()
