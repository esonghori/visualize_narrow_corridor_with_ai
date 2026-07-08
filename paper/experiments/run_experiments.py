#!/usr/bin/env python3
"""Generate every (country, model) run for the paper.

Run from the repo root (needs provider API keys in .env):

    uv run python paper/experiments/run_experiments.py            # JSON + PNG
    uv run python paper/experiments/run_experiments.py --gif      # also animations
    uv run python paper/experiments/run_experiments.py --models anthropic/claude-opus-4-8

Outputs land in paper/experiments/results/ as <country-slug>__<model-slug>.{json,png,gif}
(the slug matches the \\includegraphics names in main.tex). Responses are cached,
so re-running is free and interrupted runs resume.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from narrow_corridor.pipeline import get_narrow_corridor
from narrow_corridor.plot import plot_path
from narrow_corridor.storage import save_path

# country -> first year to score; all run through END in STEP-year periods.
# Chosen to put several countries in each of the book's four Leviathan types:
# Despotic (Iran, China), Shackled/in-corridor (UK, France, US, India),
# Paper (Colombia, Zambia), Absent (DR Congo, Lebanon, Somalia); Chile re-enters.
COUNTRIES: dict[str, int] = {
    "Iran (Persia)": 1880,
    "France": 1789,
    "United Kingdom": 1789,
    "United States": 1789,
    "China": 1880,
    "Chile": 1818,
    "Colombia": 1819,                    # Paper Leviathan
    "Democratic Republic of the Congo": 1885,  # Absent Leviathan (Congo Free State on)
    "Lebanon": 1918,                     # Absent Leviathan (mandate -> confessional state)
    "Zambia (Northern Rhodesia)": 1911,  # Paper Leviathan (colonial -> post-colonial)
    "Somalia": 1900,                     # Absent Leviathan (colonial -> 1991 collapse)
    "India": 1885,                       # Shackled Leviathan under a "cage of norms"
}
END = 2020
STEP = 10  # decade periods keep the sweep affordable; lower for finer paths.

# Each provider's strongest current model. For Alibaba we use the strongest
# *open-weight* Qwen (not the proprietary qwen-max) to keep an open/closed
# contrast. Verify these ids resolve in your LiteLLM version before a full run;
# an unresolved id just skips that model (the sweep continues, no cost).
MODELS = [
    "gemini/gemini-2.5-pro",                  # gemini-3.1-pro unavailable -> previous version
    "anthropic/claude-opus-4-8",
    "openai/gpt-5.5",
    # Fell back from Qwen3-235B-A22B: its plain endpoint returns non-JSON and its
    # :nitro endpoint degenerates into repetition on the longer scoring prompts.
    # qwen-2.5-72b-instruct is the stable open-weight fallback (honors response_format).
    "openrouter/qwen/qwen-2.5-72b-instruct",
]

RUNS_DIR = Path(__file__).parent / "results"  # committed (not gitignored) for reproducibility


def slug(s: str) -> str:
    """Filename-safe slug. Replaces '/' (model ids) and parens; must match the
    <country-slug>__<model-slug> names used by \\atlas{} in paper/main.tex, e.g.
    'anthropic/claude-opus-4-8' -> 'anthropic-claude-opus-4-8'."""
    for ch in "()":
        s = s.replace(ch, "")
    return "-".join(s.lower().replace("/", " ").replace(":", " ").split())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", default=MODELS, help="Override model list.")
    ap.add_argument("--gif", action="store_true", help="Also render animations.")
    args = ap.parse_args()

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    for country, start in COUNTRIES.items():
        for model in args.models:
            stem = f"{slug(country)}__{slug(model)}"
            print(f"\n=== {country} | {model} -> {stem} ===")
            try:
                path = get_narrow_corridor(
                    model=model, country=country,
                    start_year=start, end_year=END, step_years=STEP,
                )
            except Exception as e:  # keep the sweep going; note the gap
                print(f"  SKIPPED ({type(e).__name__}: {e})")
                continue
            save_path(path, RUNS_DIR / f"{stem}.json")
            plot_path(path, RUNS_DIR / f"{stem}.png")
            if args.gif:
                from narrow_corridor.animate import animate_path
                animate_path(path, RUNS_DIR / f"{stem}.gif")


if __name__ == "__main__":
    main()
