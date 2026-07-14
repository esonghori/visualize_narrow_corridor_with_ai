# Experiment runbook

How to run every experiment in the paper, process the data, produce the figures
and tables, and interpret the results. All commands run from the **repo root**.

## What the paper claims, and which script produces it

| Paper element | Script | Output |
|---|---|---|
| §Setup generation (8 countries × 4 models) | `paper/experiments/run_experiments.py` | `paper/experiments/results/<country>__<model>.{json,png,gif}` |
| Fig. 1 Trajectory atlas (reference model) | (above) + `\atlas{}` in `main.tex` | PNG panels, assembled by LaTeX |
| Fig. 2 Ensemble atlas (mean across models) | `paper/experiments/ensemble.py` | `results/<country>__ensemble-mean.{json,png}` |
| Fig. 3 One-map combined atlas | `paper/experiments/atlas_combined.py` | `results/all-countries__ensemble-mean.png` |
| §Consistency with V-Dem (Table 2) | `paper/experiments/analysis.py` | `paper/tables/validation.tex` |
| §Model comparison & reliability (Table 1) | `paper/experiments/analysis.py` | `paper/tables/intermodel.tex` |
| §Cross-country patterns (prose) | `paper/experiments/summarize.py` | `paper/experiments/derived/summary.csv` + stdout |
| §Qualitative case studies (prose) | `paper/experiments/summarize.py` | `paper/experiments/derived/<country>.csv` |
| Interactive gallery (contribution) | `scripts/build_site.py` | `docs/` static site |
| Fig. §Prompt-language sensitivity | `paper/experiments/lang_ablation.py` | `results_lang/lang-ablation.png` + `derived/lang_ablation.csv` |

> The remaining Future Work items (human expert-coder baseline, prompt/period
> granularity ablations, additional indices) are **intentionally not scripted** —
> they are out of scope for this paper. The non-English prompting probe *is* now
> scripted (`lang_ablation.py`, Step 3b).

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
- **Cost**: ~1,200 LLM calls per full sweep (1–2 per period × ~156 country-periods ×
  4 models). With each provider's strongest model the estimate is **≈ $10, range
  $6–18** — dominated by `claude-opus-4-8`, `gpt-5`, and `gemini-3.5-pro`; the
  open-weight Qwen is cents. Reasoning-tier models (`gpt-5`, Gemini Pro) emit
  hidden reasoning tokens, so their output cost and wall-clock (≈ 1–2 h,
  sequential) are the least predictable part. Responses are cached under
  `runs/.cache/`, so re-runs and interrupted sweeps are free/resumable. Outputs
  land in `paper/experiments/results/` (committed, not gitignored).

## Step 1 — Generate the trajectories

```bash
uv run python paper/experiments/run_experiments.py --gif
```

Produces `paper/experiments/results/<country-slug>__<model-slug>.{json,png,gif}`.
Country/model set, period length (decade), and end year (2020) are the constants
at the top of `run_experiments.py`. To generate only the atlas reference model
first (cheapest, needs only the Anthropic key):

```bash
uv run python paper/experiments/run_experiments.py --models anthropic/claude-opus-4-8 --gif
```

## Step 2 — Build the tables

Get the V-Dem **Country-Year: Full+Others** dataset from
<https://www.v-dem.org/data/the-v-dem-dataset/> (the full CSV is ~406 MB and
~4,600 columns). Slim it to the four columns we need for the eight countries into
`paper/experiments/external/vdem.csv` (gitignored — V-Dem is a third-party input,
not our data). If the zip is at `runs/V-Dem-CY-FullOthers-v16_csv.zip`:

```bash
uv run python - <<'PY'
import zipfile, csv, io
KEEP = {"Iran","France","United Kingdom","United States of America","China","Chile","Colombia","Democratic Republic of the Congo","Lebanon","Zambia","Somalia","India"}
COLS = ["country_name","year","v2xcs_ccsi","v2svstterr"]
zf = zipfile.ZipFile("runs/V-Dem-CY-FullOthers-v16_csv.zip")
with zf.open("V-Dem-CY-Full+Others-v16.csv") as f:
    r = csv.reader(io.TextIOWrapper(f, "utf-8")); h = next(r); i = {c: h.index(c) for c in COLS}
    rows = [[row[i[c]] for c in COLS] for row in r if row[i["country_name"]] in KEEP]
import os; os.makedirs("paper/experiments/external", exist_ok=True)
csv.writer(open("paper/experiments/external/vdem.csv","w",newline="")).writerows([COLS]+rows)
print("wrote", len(rows), "rows")
PY
```

Indicator columns and the country-name map are configured at the top of
`analysis.py` (society ← `v2xcs_ccsi`; state ← `v2svstterr` = state authority
over territory; swap to `v2clrspct` for an administration-quality proxy).

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

Then build the **ensemble (mean-across-models) atlas** — Figure 2 in the paper:

```bash
uv run python paper/experiments/ensemble.py --gif   # --gif also renders the animations for the gallery
```

Writes `paper/experiments/results/<country>__ensemble-mean.{json,png,gif}`, averaging
society/state power across all available models per period (reference-model key
events supply the turn labels). This is the paper's headline reading; the
single-model atlas (Fig. 1) stays for legibility.

Then build the **one-map combined atlas** — Figure 3 — which overlays every
country's ensemble-mean path in a single shared (society, state) space (the
book's single-plane view; the shared rubric is what makes the cross-country
numbers comparable):

```bash
uv run python paper/experiments/atlas_combined.py
```

Writes `paper/experiments/results/all-countries__ensemble-mean.png`. Needs the
ensemble runs above, so run `ensemble.py` first.

### Step 3b — Prompt-language ablation (Fig. §Prompt-language sensitivity)

Re-runs the full four-model ensemble with the prompts (country name included)
translated into each showcase country's own language (French→France,
Chinese→China, Persian→Iran, Spanish→Chile, Arabic→Lebanon) and overlays each
result against the English trajectory:

```bash
uv run python paper/experiments/lang_ablation.py            # generate + figures
uv run python paper/experiments/lang_ablation.py --no-run   # figures only, from cache
```

Translated runs land in `paper/experiments/results_lang/` (kept out of
`results/` so `analysis.py` never counts them as extra raters). Only the prompt
*prose* is translated; the rubric and the requested (English) JSON fields are
held fixed (`prompts.py`), so scores stay comparable. Cost is ~one extra ensemble
per country (~$3–6, cached/resumable). Outputs: `results_lang/lang-ablation.png`
(combined 3-panel), per-country `results_lang/<country>__lang-compare-<lang>.png`,
and `derived/lang_ablation.csv` (per-period displacement, RMSD, endpoint shift,
first-difference ρ between the two languages). Fill the `\ph{}` numbers in
§Prompt-language sensitivity from that CSV.

## Step 4 — Build the gallery

```bash
uv run python scripts/build_site.py --runs paper/experiments/results --out docs
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
model — cross-model spread is in Table 1. (4) Eight countries, short series → no
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
