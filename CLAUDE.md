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

## Conventions

- Standard **4-space** Python indentation (the old notebook used 2-space Google style).
- The two-axis methodology is the core value: keep the Chain-of-Thought (events first) and In-Context Learning (prior scores fed forward) structure when editing prompts or the pipeline.
- `PeriodScore` is the contract between the prompt and the parser — if you change requested output fields in `prompts.py`, update the pydantic model (and the regex fallback in `llm.py` if the `<...>` shape changes).
- `example/` holds a committed sample run for Iran (Persia) 1880–2025 (full transcript + output PNG).
