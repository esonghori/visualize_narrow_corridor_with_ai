# Experiment runbook

How to run every experiment in the paper, process the data, produce the figures
and tables, and interpret the results. All commands run from the **repo root**.

## What the paper claims, and which script produces it

| Paper element | Script | Output |
|---|---|---|
| §Setup generation (6 countries × 4 models) | `paper/experiments/run_experiments.py` | `paper/experiments/runs/<country>__<model>.{json,png,gif}` |
| Fig. 1 Trajectory atlas (reference model) | (above) + `\atlas{}` in `main.tex` | PNG panels, assembled by LaTeX |
| §Consistency with V-Dem (Table 2) | `paper/experiments/analysis.py` | `paper/tables/validation.tex` |
| §Model comparison & reliability (Table 1) | `paper/experiments/analysis.py` | `paper/tables/intermodel.tex` |
| §Cross-country patterns (prose) | `paper/experiments/summarize.py` | `paper/experiments/derived/summary.csv` + stdout |
| §Qualitative case studies (prose) | `paper/experiments/summarize.py` | `paper/experiments/derived/<country>.csv` |
| Interactive gallery (contribution) | `scripts/build_site.py` | `docs/` static site |

> The paper's Future Work items (human expert-coder baseline, prompt/period
> ablations, non-English prompting probe, additional indices, ensemble atlas)
> are **intentionally not scripted** — they are out of scope for this paper.

## Prerequisites

```bash
uv sync
cp .env.example .env      # add keys for the providers you want
```

- **API keys** (`.env`): `ANTHROPIC_API_KEY` is enough for the atlas + case
  studies (the reference model is `claude-opus-4-8`). For the full 4-model
  reliability table you also need `GEMINI_API_KEY`, `OPENAI_API_KEY`,
  `OPENROUTER_API_KEY`. Missing a key → that model is skipped, not fatal.
- **V-Dem CSV** (for Table 2 only): download the V-Dem dataset CSV to
  `paper/experiments/external/vdem.csv`. See §Step 2. Without it, Table 2 is
  written with placeholders and the paper still compiles.
- **Cost**: generation is 1–2 LLM calls per period, ~15 periods × 6 countries ×
  4 models ≈ a few hundred calls per full sweep. Responses are cached under
  `runs/.cache/`, so re-runs and interrupted sweeps are free/resumable.

## Step 1 — Generate the trajectories

```bash
uv run python paper/experiments/run_experiments.py --gif
```

Produces `paper/experiments/runs/<country-slug>__<model-slug>.{json,png,gif}`.
Country/model set, period length (decade), and end year (2020) are the constants
at the top of `run_experiments.py`. To generate only the atlas reference model
first (cheapest, needs only the Anthropic key):

```bash
uv run python paper/experiments/run_experiments.py --models anthropic/claude-opus-4-8 --gif
```

## Step 2 — Build the tables

Download the V-Dem dataset CSV (Country-Year, Full+Others) from
<https://www.v-dem.org/data/the-v-dem-dataset/> to
`paper/experiments/external/vdem.csv`. It already has `country_name` and `year`
columns. The indicator columns and country-name mapping are configured at the
top of `analysis.py` (society ← `v2xcs_ccsi`; state ← `v2terr`; see that file to
swap in a different state-capacity indicator such as `v2clrspct`).

```bash
uv run python paper/experiments/analysis.py
```

Writes `paper/tables/intermodel.tex` (Krippendorff's α on first differences,
across models) and `paper/tables/validation.tex` (Spearman ρ vs. V-Dem, on
levels and first differences). Re-run it whenever the runs or the CSV change.

## Step 3 — Process the data for the qualitative sections

```bash
uv run python paper/experiments/summarize.py
```

Writes `paper/experiments/derived/<country>.csv` (per-period scores, changes,
corridor position, key event, reasoning) and `derived/summary.csv` (start/end
position, net drift per axis, largest single-period move), and prints a
cross-country overview. Use these to write the Cross-country patterns and Case
studies subsections.

## Step 4 — Build the gallery

```bash
uv run python scripts/build_site.py --runs paper/experiments/runs --out docs
```

## Step 5 — Compile the paper

```bash
cd paper && tectonic main.tex          # or: pdflatex main && bibtex main && pdflatex main x2
```

Figures and tables are pulled in automatically. Then replace every remaining red
`\ph{...}` (see §Filling placeholders).

---

## How to interpret the results

**Trajectory atlas (Fig. 1).** Read each path against the diagonal band: near the
diagonal = *in corridor* (state and society balanced); clearly above =
state-dominated; clearly below = society-dominated. Long diagonal runs indicate
the two powers co-growing; tight loops indicate oscillation (contested periods);
a large single-period jump marks a sharp transition (revolution, coup). `summary.csv`
gives the start/end position and largest move per country to anchor the prose.

**Consistency with V-Dem (Table 2).** Expect **high level ρ** almost trivially —
both the LLM path and V-Dem share a secular upward trend. The **first-difference
ρ** is the honest signal: it tests whether the model gets the *timing and
direction of change* right, not just the trend. Report both; lead with Δ.
Interpret a high Δ ρ as *consistency with expert consensus*, **not accuracy** —
V-Dem is almost certainly in the models' training data (state this caveat when
you cite the number). Low or negative Δ ρ localizes where the LLM and experts
disagree.

**Inter-model reliability (Table 1).** Krippendorff's α on period-to-period
changes, over the four models as raters. Rules of thumb (Krippendorff): α ≥ 0.80
= strong agreement, 0.67–0.80 = tentative, < 0.67 = weak, ≤ 0 = systematic
disagreement / no shared signal. Compare the Society vs. State columns (which
axis do models agree on more?) and note whether the open-weight model (Qwen)
drags the α down relative to the three closed models. High α + high V-Dem Δ ρ =
a score reflects a shared, expert-consistent signal; high α + low V-Dem ρ = the
models agree with each other but not with experts (shared bias); low α = the
case is contested — exactly where a human panel would also disagree.

**Case studies.** Open the per-country `derived/*.csv`, find the rows with the
largest `d_state`/`d_society`, and check the `key_event`/`reasoning` against
documented history (e.g., Iran ~1979 sharp state consolidation; Chile 1973 coup
then 1990 redemocratization). Note both matches (consensus captured) and misses
(anachronism, or a contested episode flattened toward consensus).

**Caveats to state whenever you report a number.** (1) V-Dem overlap → concurrent
consistency, not accuracy. (2) Coverage/language bias is worst for Iran, China,
Chile (English prompts, sparser training data). (3) The atlas is one reference
model — cross-model spread is in Table 1. (4) Six countries, short series → no
significance/generalization claims.

## Filling the paper's `\ph{...}` placeholders

Grep `main.tex` for `\ph`. Each maps to an output above:

| Placeholder location | Filled from |
|---|---|
| §Atlas reading | `derived/summary.csv` + Fig. 1 |
| §Cross-country patterns | `derived/summary.csv` + `derived/*.csv` |
| §Consistency (Table 2 summary) | `tables/validation.tex` values |
| §Reliability (Table 1 summary) | `tables/intermodel.tex` values |
| §Case studies | `derived/<country>.csv` |
| Fig. 1 caption "Regenerate with…" | delete once the panels exist |

When done, no red `\ph` should remain in the compiled PDF.
