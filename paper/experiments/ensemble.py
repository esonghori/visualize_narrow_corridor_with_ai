#!/usr/bin/env python3
"""Build the ensemble-mean atlas: per country, average the models' scores.

    uv run python paper/experiments/ensemble.py

For each country it averages society/state power across all available models
(over the periods they share), writes the mean trajectory to
paper/experiments/results/<country-slug>__ensemble-mean.{json,png}, and uses the
reference model's key events for the plot's turn labels. The paper's second
atlas figure includes these panels. No LLM calls.
"""

from __future__ import annotations

from statistics import fmean

from analysis import REF_MODEL, load_runs
from narrow_corridor.models import NarrowCorridorPath
from narrow_corridor.plot import plot_path
from narrow_corridor.storage import save_path
from run_experiments import COUNTRIES, RUNS_DIR, slug


def main() -> None:
    by_country = load_runs()
    if not by_country:
        print(f"No runs in {RUNS_DIR}. Run run_experiments.py first.")
        return

    for country in COUNTRIES:
        models = by_country.get(country, {})
        if len(models) < 2:
            print(f"(skip {country}: need >=2 models, have {len(models)})")
            continue
        common = sorted(set.intersection(*(set(p.periods) for p in models.values())))
        ref = models.get(REF_MODEL)  # key events for the labels, if present

        mean = NarrowCorridorPath(country=country, model=f"ensemble-mean ({len(models)} models)")
        for per in common:
            mean.periods.append(per)
            mean.society_power[per] = round(fmean(p.society_power[per] for p in models.values()), 3)
            mean.state_power[per] = round(fmean(p.state_power[per] for p in models.values()), 3)
            mean.key_event[per] = ref.key_event.get(per, "") if ref else ""
            mean.reasoning[per] = f"mean of {len(models)} models"

        stem = f"{slug(country)}__ensemble-mean"
        save_path(mean, RUNS_DIR / f"{stem}.json")
        plot_path(mean, RUNS_DIR / f"{stem}.png")
        print(f"{country:16} mean over {len(models)} models, {len(common)} periods -> {stem}.png")


if __name__ == "__main__":
    main()
