#!/usr/bin/env python3
"""Process the runs into per-country data dumps + a cross-country summary.

    uv run python paper/experiments/summarize.py

Supports the paper's two qualitative subsections (Cross-country patterns, and
Qualitative case studies). For the reference model it writes, under
paper/experiments/derived/:
  * <country-slug>.csv  — one row per period: scores, changes, corridor position,
    key event, and reasoning (the raw material for case studies).
  * summary.csv         — one row per country: start/end corridor position, net
    drift on each axis, and the single largest period-to-period move.
and prints the summary table to stdout. Nothing here calls an LLM.
"""

from __future__ import annotations

import csv
from math import hypot
from pathlib import Path

from analysis import REF_MODEL, load_runs
from run_experiments import COUNTRIES, slug

HERE = Path(__file__).parent
DERIVED = HERE / "derived"

# Corridor half-width on the 0-10 scale for the (illustrative) in/above/below
# label. The paper reads positions qualitatively; this threshold only labels the
# dumps and is not a fitted cutoff.
BAND = 1.5


def _position(society: float, state: float) -> str:
    gap = state - society
    if abs(gap) <= BAND:
        return "in-corridor"
    return "state-dominated" if gap > 0 else "society-dominated"


def _rows(path):
    rows = []
    prev = None
    for per in sorted(path.periods):
        soc, sta = path.society_power[per], path.state_power[per]
        d_soc = "" if prev is None else round(soc - prev[0], 2)
        d_sta = "" if prev is None else round(sta - prev[1], 2)
        rows.append({
            "start": per[0], "end": per[1], "midyear": (per[0] + per[1]) // 2,
            "society": soc, "state": sta, "d_society": d_soc, "d_state": d_sta,
            "gap_state_minus_society": round(sta - soc, 2),
            "position": _position(soc, sta),
            "key_event": path.key_event.get(per, ""),
            "reasoning": path.reasoning.get(per, ""),
        })
        prev = (soc, sta)
    return rows


def _largest_move(rows):
    """(period_label, key_event, magnitude) for the biggest single-period move."""
    best = (None, "", 0.0)
    for r in rows[1:]:
        mag = hypot(r["d_society"] or 0.0, r["d_state"] or 0.0)
        if mag > best[2]:
            best = (f"{r['start']}-{r['end']}", r["key_event"], round(mag, 2))
    return best


def main() -> None:
    DERIVED.mkdir(parents=True, exist_ok=True)
    by_country = load_runs()
    summary = []

    for country in COUNTRIES:
        path = by_country.get(country, {}).get(REF_MODEL)
        if path is None:
            print(f"(skip {country}: no {REF_MODEL} run)")
            continue
        rows = _rows(path)
        with (DERIVED / f"{slug(country)}.csv").open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

        first, last = rows[0], rows[-1]
        move_period, move_event, move_mag = _largest_move(rows)
        summary.append({
            "country": country,
            "start_position": first["position"],
            "end_position": last["position"],
            "drift_society": round(last["society"] - first["society"], 2),
            "drift_state": round(last["state"] - first["state"], 2),
            "largest_move_period": move_period,
            "largest_move_mag": move_mag,
            "largest_move_event": move_event,
        })

    if not summary:
        print("No reference-model runs found. Run run_experiments.py first.")
        return

    with (DERIVED / "summary.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)

    # Readable cross-country overview.
    print(f"\nCross-country summary ({REF_MODEL}):\n")
    hdr = f"{'country':16} {'start':18} {'end':18} {'Δsoc':>6} {'Δsta':>6}  largest move"
    print(hdr); print("-" * len(hdr))
    for s in summary:
        print(f"{s['country']:16} {s['start_position']:18} {s['end_position']:18} "
              f"{s['drift_society']:>6} {s['drift_state']:>6}  "
              f"{s['largest_move_period']} ({s['largest_move_event']})")
    print(f"\nPer-country period-level dumps + summary.csv written to {DERIVED}/")


if __name__ == "__main__":
    main()
