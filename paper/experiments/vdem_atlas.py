#!/usr/bin/env python3
"""Build a V-Dem atlas in the same (society, state) space, for comparison.

    uv run python paper/experiments/vdem_atlas.py

For each country, plots the expert-coded trajectory at the same period-midpoint
years as the LLM runs, rescaled to the LLM's 0--10 axes:
  society = v2xcs_ccsi * 10      (core civil society index, 0--1 -> 0--10)
  state   = v2svstterr / 10      (state authority over territory, 0--100 -> 0--10)
Writes paper/experiments/results/<country-slug>__vdem.{json,png}. No LLM calls;
needs paper/experiments/external/vdem.csv (see RUNBOOK).
"""

from __future__ import annotations

from analysis import COUNTRY_TO_EXT, REF_MODEL, _load_external, _mid, load_runs
from narrow_corridor.models import NarrowCorridorPath
from narrow_corridor.plot import plot_path
from narrow_corridor.storage import save_path
from run_experiments import COUNTRIES, RUNS_DIR, slug


def main() -> None:
    ext = _load_external()
    if ext is None:
        print("No external/vdem.csv found; see RUNBOOK Step 2.")
        return
    by_country = load_runs()

    for country in COUNTRIES:
        ref = by_country.get(country, {}).get(REF_MODEL)
        if ref is None:
            print(f"(skip {country}: no reference run for period alignment)")
            continue
        vd = ext.get(COUNTRY_TO_EXT.get(country, country), {})
        p = NarrowCorridorPath(country=country, model="V-Dem")
        for per in ref.periods:  # same periods as the LLM atlas
            yr = _mid(per)
            if yr in vd:
                soc, sta = vd[yr]
                p.periods.append(per)
                p.society_power[per] = round(soc * 10, 3)   # 0-1 -> 0-10
                p.state_power[per] = round(sta / 10, 3)      # 0-100 -> 0-10
                p.key_event[per] = ""
                p.reasoning[per] = "V-Dem"
        if not p.periods:
            print(f"(skip {country}: no V-Dem overlap)")
            continue
        stem = f"{slug(country)}__vdem"
        save_path(p, RUNS_DIR / f"{stem}.json")
        plot_path(p, RUNS_DIR / f"{stem}.png", annotate_turns=0)  # no key events
        print(f"{country:16} {len(p.periods)} periods -> {stem}.png")


if __name__ == "__main__":
    main()
