# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A research tool that uses an LLM to place a country's historical trajectory in the two-dimensional "state power vs. society power" space from Acemoglu & Robinson's *The Narrow Corridor*. The LLM assigns numerical state/society power values per time period; the result is plotted as a path and as an animated GIF. See `README.md` for the conceptual background and citation.

It is a **uv-managed Python package** (`src/narrow_corridor/`) with a `typer` CLI. It is **provider-agnostic via LiteLLM** — any model (Gemini, Claude, OpenAI, Qwen via OpenRouter, …) works by changing the model string. There is no notebook and no Colab/Drive dependency anymore (the old `main.ipynb` was replaced by this package).

## Commands

- `uv sync` — install (Python ≥ 3.10).
- `uv run ncorridor models` — list suggested LiteLLM model strings and which API key each needs (no network).
- `uv run ncorridor generate --country ... --model ... --start ... --end ... --step ... --out runs/x.json` — run the pipeline.
- `uv run ncorridor plot runs/x.json --out runs/x.png` / `uv run ncorridor animate runs/x.json --out runs/x.gif`.
- `uv run pytest` — no-network parsing/round-trip tests.
- API keys come from a `.env` file (gitignored; see `.env.example`). Never commit real keys.
- **`generate` makes one or two LLM calls per period and is expensive.** Responses are cached on disk under `runs/.cache/` keyed by `(model, prompt)`, so re-runs and plot/animation iteration are free. Prefer `load_path` on a saved `.json` when iterating on visualization.

## Architecture

Module map under `src/narrow_corridor/`:

- `models.py` — `PeriodScore` (pydantic schema the LLM fills) and `NarrowCorridorPath` (`@dataclass`, the result object: `periods` plus per-period dicts keyed by the `(start, end)` tuple). `NarrowCorridorPath.to_dict`/`from_dict` handle JSON (tuple keys are encoded as `"start-end"` strings); the saved JSON keeps each period's prompts and raw responses as a transcript.
- `prompts.py` — the prompt templates. `events_trends_prompt` (CoT step 1), `bootstrap_score_prompt` (first period, absolute values), `score_prompt` (later periods, change + absolute). All scoring prompts embed the shared `RUBRIC` (anchored 0–10 scale + neutrality guidance).
- `llm.py` — provider-agnostic access via `litellm.completion`. `complete_text` (free text) and `complete_structured` (returns a validated `PeriodScore`). Robustness ladder: structured `response_format` → one retry with a JSON reminder → `_regex_fallback` (ported from the original notebook; accepts a 2- or 4-tuple `<...>`) → raise. On-disk cache + `known_models`/`env_status` helpers.
- `pipeline.py` — `get_narrow_corridor(...)`: the two-call-per-period loop. First period bootstraps absolute values; each later period calls events→score, accumulating prior `<society, state>` scores (In-Context Learning) into the next scoring prompt.
- `plot.py` — `plot_path`: society (x) vs state (y), optional B-spline smoothing (`scipy.interpolate.make_interp_spline`), two dashed-green corridor boundary lines. `_bounds`/`_draw_corridor` are shared with the animator.
- `animate.py` — `animate_path`: `matplotlib.animation.FuncAnimation` + `PillowWriter`. Each frame reveals the path up to one more period, highlights the new point, draws a crimson arrow for the move that period's event caused, and captions it with `period` + `key_event`.
- `storage.py` — `save_path`/`load_path` as JSON (replaces the old pickle-to-Drive).
- `cli.py` — the `ncorridor` entry point (`generate` / `plot` / `animate` / `models`). Heavy imports are deferred into each command so `--help` and `models` stay fast.

## Paper, experiments & gallery

The `src/` package is the reusable library; the reproducible research around it lives in `paper/` and `scripts/`. **`paper/RUNBOOK.md` is the authoritative end-to-end guide** (commands, cost, and how to interpret each result) — read it before touching the experiment pipeline.

- `paper/experiments/run_experiments.py` — the sweep config *and* the config source for every other script: `COUNTRIES`, `MODELS`, `END`, `STEP`, `slug()`, `RUNS_DIR` live here, and `analysis.py` / `ensemble.py` / `summarize.py` / `vdem_atlas.py` all `import from run_experiments`. Change the country/model set here, in one place. It writes `paper/experiments/results/<country-slug>__<model-slug>.{json,png,gif}` (**committed**, not gitignored — note some docs still say `runs/`; the code uses `results/`). Slugs match the `\includegraphics` names in `main.tex`.
- `analysis.py` → `paper/tables/{intermodel,validation}.tex` (Krippendorff's α across models on first differences; Spearman ρ vs. V-Dem). `ensemble.py` → `<country>__ensemble-mean.{json,png}` (mean across models). `atlas_combined.py` → `all-countries__ensemble-mean.png` (every country's ensemble path overlaid in one shared space; the shared rubric is the common scale). `summarize.py` → `paper/experiments/derived/*.csv` for the prose. `vdem_atlas.py` → `<country>__vdem.{json,png}`. Only `run_experiments.py` calls an LLM; the rest are pure post-processing.
- V-Dem is a third-party input you provide at `paper/experiments/external/vdem.csv` (gitignored); indicator columns are configured at the top of `analysis.py`. Without it, tables still write with placeholders and the paper still compiles.
- `paper/main.tex` compiles standalone (twocolumn, no external `.sty`); unfilled items are red `\ph{...}` macros — grep for `\ph` to find open items.
- `scripts/build_site.py --runs <dir> --out docs` — turns a results dir into the committed static gallery in `docs/` (GitHub Pages). Discovery is driven off each run's `.json` sidecar (real country/model names), not the slug. GIFs are committed under `docs/assets/` (copied there by this script), not under `results/`.
- `thread/` — a draft X/Twitter thread (`THREAD.md`) plus its attached images/GIF for promoting the project; not part of the code or research pipeline.

## Conventions

- Standard **4-space** Python indentation (the old notebook used 2-space Google style).
- The two-axis methodology is the core value: keep the Chain-of-Thought (events first) and In-Context Learning (prior scores fed forward) structure when editing prompts or the pipeline.
- `PeriodScore` is the contract between the prompt and the parser — if you change requested output fields in `prompts.py`, update the pydantic model (and the regex fallback in `llm.py` if the `<...>` shape changes).
- There is no separate `example/` dir; the committed sample runs are the paper sweep under `paper/experiments/results/` (full transcripts + PNGs). The README's worked example points at the USA reference-model run there.
