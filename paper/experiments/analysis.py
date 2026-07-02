#!/usr/bin/env python3
"""Turn the runs into the paper's LaTeX tables.

    uv run python paper/experiments/analysis.py

Writes paper/tables/intermodel.tex and paper/tables/validation.tex, which
main.tex \\input{}s. Tables are always (re)written so the paper compiles; rows
fall back to placeholders when data is missing.

Inter-model agreement uses only the runs in paper/experiments/results/ and is
reported as Krippendorff's alpha (interval) on the period-to-period *changes*
(agreement on moves, not on the shared secular trend).

The V-Dem consistency check additionally needs an expert-index CSV at
paper/experiments/external/vdem.csv (see EXTERNAL config below and paper/README.md);
it reports Spearman correlations on both levels and first differences. Without
the CSV, that table is written with placeholder values.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from scipy.stats import spearmanr

from narrow_corridor.storage import load_path
from run_experiments import COUNTRIES, END  # reuse the sweep config

HERE = Path(__file__).parent
RUNS_DIR = HERE / "results"
TABLES_DIR = HERE.parent / "tables"
REF_MODEL = "anthropic/claude-opus-4-8"  # reference model for the V-Dem check

# ----- external index config (edit to match your downloaded dataset) ---------
EXTERNAL_CSV = HERE / "external" / "vdem.csv"
EXT_COUNTRY_COL = "country_name"
EXT_YEAR_COL = "year"
EXT_SOCIETY_COL = "v2xcs_ccsi"   # V-Dem core civil society index (0-1)
# State power -> V-Dem state authority over territory (v2svstterr).
# Alternatives worth trying: v2clrspct (rigorous/impartial public administration),
# or an external state-capacity dataset (Hanson-Sigman).
EXT_STATE_COL = "v2svstterr"
# Short display names for the LaTeX tables (full names blow the column width).
# Only affects table cells; prompts, filenames, slugs, and V-Dem lookup keep the
# full country name.
DISPLAY_NAME = {
    "Democratic Republic of the Congo": "DR Congo",
}

# LLM country name -> external-dataset country name
COUNTRY_TO_EXT = {
    "Iran (Persia)": "Iran",
    "United States": "United States of America",
    "United Kingdom": "United Kingdom",
    "France": "France",
    "China": "China",
    "Chile": "Chile",
    "Colombia": "Colombia",
    "Democratic Republic of the Congo": "Democratic Republic of the Congo",
}


def _mid(period) -> int:
    return (period[0] + period[1]) // 2


def _diff(seq):
    return [b - a for a, b in zip(seq, seq[1:])]


def _spearman(a, b):
    """Spearman rho over paired values; None if too few points or no variance."""
    if len(a) < 3 or len(set(a)) < 2 or len(set(b)) < 2:
        return None
    return spearmanr(a, b).statistic


def krippendorff_alpha_interval(units) -> float | None:
    """Krippendorff's alpha (interval metric).

    `units` is a list of per-unit value lists (one value per rater; raters that
    did not rate a unit are simply omitted). Uses the coincidence-matrix
    identity alpha = 1 - (n-1) * Do_num / De_num, which is exact for the interval
    metric delta(a,b) = (a-b)^2. Returns None if there is nothing to compare or
    no variance in the pooled values.
    """
    pool, do_num = [], 0.0
    for vals in units:
        m = len(vals)
        if m < 2:
            continue
        pool.extend(vals)
        do_num += sum(
            (vals[i] - vals[j]) ** 2 for i in range(m) for j in range(i + 1, m)
        ) / (m - 1)
    n = len(pool)
    if n < 2:
        return None
    de_num = sum(
        (pool[i] - pool[j]) ** 2 for i in range(n) for j in range(i + 1, n)
    )
    if de_num == 0:
        return None
    return 1.0 - (n - 1) * do_num / de_num


def _fmt(r) -> str:
    return f"{r:.2f}" if r is not None else r"\ph{--}"


def _pair(a, b) -> str:
    return f"{_fmt(a)}\\,/\\,{_fmt(b)}"


def load_runs() -> dict[str, dict[str, object]]:
    """country -> {model -> NarrowCorridorPath} for every real model run on disk.

    Ensemble-mean runs are excluded: they are derived from the model runs, so
    counting them as a rater would double-count and inflate inter-model agreement.
    """
    by_country: dict[str, dict[str, object]] = defaultdict(dict)
    for f in sorted(RUNS_DIR.glob("*.json")):
        path = load_path(f)
        if path.model.lower().startswith(("ensemble", "v-dem", "vdem")):
            continue  # derived atlases, not model runs
        by_country[path.country][path.model] = path
    return by_country


# ----------------------------------------------------------------------------
def _change_units(models: dict, attr: str):
    """Per-change-index list of [each model's period-to-period change], over the
    periods common to all models. attr is 'society_power' or 'state_power'."""
    common = sorted(set.intersection(*(set(p.periods) for p in models.values())))
    series = {m: _diff([getattr(p, attr)[per] for per in common]) for m, p in models.items()}
    return [[series[m][k] for m in models] for k in range(max(0, len(common) - 1))]


def inter_model_table(by_country) -> None:
    rows, pooled_soc, pooled_sta = [], [], []
    for country in COUNTRIES:
        models = by_country.get(country, {})
        if len(models) < 2:
            rows.append((country, len(models), None, None))
            continue
        soc_units = _change_units(models, "society_power")
        sta_units = _change_units(models, "state_power")
        pooled_soc += soc_units
        pooled_sta += sta_units
        rows.append((
            country, len(models),
            krippendorff_alpha_interval(soc_units),
            krippendorff_alpha_interval(sta_units),
        ))
    overall_soc = krippendorff_alpha_interval(pooled_soc)
    overall_sta = krippendorff_alpha_interval(pooled_sta)

    lines = [
        r"\begin{table}[t]", r"\centering", r"\small",
        r"\caption{Inter-model reliability: Krippendorff's $\alpha$ (interval) on "
        r"period-to-period \emph{changes} across models, per country. Higher $=$ "
        r"models see the same moves.}",
        r"\label{tab:intermodel}",
        r"\begin{tabular}{lccc}", r"\toprule",
        r"Country & \#models & Society $\alpha$ & State $\alpha$ \\", r"\midrule",
    ]
    for country, k, soc, sta in rows:
        lines.append(f"{DISPLAY_NAME.get(country, country)} & {k} & {_fmt(soc)} & {_fmt(sta)} \\\\")
    lines += [
        r"\midrule",
        f"\\textbf{{Overall}} & -- & \\textbf{{{_fmt(overall_soc)}}} & \\textbf{{{_fmt(overall_sta)}}} \\\\",
        r"\bottomrule", r"\end{tabular}", r"\end{table}",
    ]
    (TABLES_DIR / "intermodel.tex").write_text("\n".join(lines) + "\n")
    print(f"wrote intermodel.tex (overall society alpha={_fmt(overall_soc)}, state={_fmt(overall_sta)})")


# ----------------------------------------------------------------------------
def _load_external():
    """(country -> {year -> (society_val, state_val)}) or None if CSV absent."""
    if not EXTERNAL_CSV.exists():
        return None
    table: dict[str, dict[int, tuple]] = defaultdict(dict)
    with EXTERNAL_CSV.open() as fh:
        for row in csv.DictReader(fh):
            try:
                yr = int(float(row[EXT_YEAR_COL]))
                soc = float(row[EXT_SOCIETY_COL])
                sta = float(row[EXT_STATE_COL])
            except (KeyError, ValueError):
                continue
            table[row[EXT_COUNTRY_COL]][yr] = (soc, sta)
    return table


def validation_table(by_country) -> None:
    ext = _load_external()
    lines = [
        r"\begin{table*}[t]", r"\centering", r"\small",
        r"\caption{Consistency with V-Dem (\texttt{claude-opus-4-8}): Spearman "
        r"$\rho$ at period-midpoint years, reported as level\,/\,$\Delta$ (levels "
        r"vs.\ first differences). Society vs.\ \texttt{v2xcs\_ccsi}; state vs.\ "
        r"\texttt{v2svstterr}. First differences are the more honest signal.}",
        r"\label{tab:validation}",
        r"\begin{tabular}{lcccc}", r"\toprule",
        r"Country & Window & $N$ & Society $\rho$ & State $\rho$ \\", r"\midrule",
    ]
    for country, start in COUNTRIES.items():
        window = f"{start}--{END}"
        soc_l = soc_d = sta_l = sta_d = None
        n = 0
        path = by_country.get(country, {}).get(REF_MODEL)
        if path is not None and ext is not None:
            ext_years = ext.get(COUNTRY_TO_EXT.get(country, country), {})
            ls, es, lt, et = [], [], [], []
            for per in sorted(path.periods):  # year order for first differences
                yr = _mid(per)
                if yr in ext_years:
                    e_soc, e_sta = ext_years[yr]
                    ls.append(path.society_power[per]); es.append(e_soc)
                    lt.append(path.state_power[per]); et.append(e_sta)
            n = len(ls)
            soc_l, sta_l = _spearman(ls, es), _spearman(lt, et)
            soc_d = _spearman(_diff(ls), _diff(es))
            sta_d = _spearman(_diff(lt), _diff(et))
        n_cell = n if n else r"\ph{--}"
        disp = DISPLAY_NAME.get(country, country)
        lines.append(f"{disp} & {window} & {n_cell} & {_pair(soc_l, soc_d)} & {_pair(sta_l, sta_d)} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}"]
    (TABLES_DIR / "validation.tex").write_text("\n".join(lines) + "\n")
    status = "computed" if ext is not None else "placeholder (no external CSV)"
    print(f"wrote validation.tex ({status})")


def main() -> None:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    by_country = load_runs()
    if not by_country:
        print(f"No runs found in {RUNS_DIR}. Run run_experiments.py first; "
              "writing placeholder tables so the paper still compiles.")
    inter_model_table(by_country)
    validation_table(by_country)


if __name__ == "__main__":
    main()
