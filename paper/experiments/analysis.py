#!/usr/bin/env python3
"""Turn the runs into the paper's LaTeX tables.

    uv run python paper/experiments/analysis.py

Writes paper/tables/intermodel.tex and paper/tables/validation.tex, which
main.tex \\input{}s. Tables are always (re)written so the paper compiles; rows
fall back to placeholders when data is missing.

Inter-model agreement needs only the runs in paper/experiments/runs/.
External validation additionally needs an expert-index CSV at
paper/experiments/external/vdem.csv (see EXTERNAL config below and paper/README.md);
without it, the validation table is written with placeholder correlations.
"""

from __future__ import annotations

import csv
import itertools
from collections import defaultdict
from pathlib import Path

from scipy.stats import pearsonr

from narrow_corridor.storage import load_path
from run_experiments import COUNTRIES, END, STEP, slug  # reuse the sweep config

HERE = Path(__file__).parent
RUNS_DIR = HERE / "runs"
TABLES_DIR = HERE.parent / "tables"

# ----- external index config (edit to match your downloaded dataset) ---------
EXTERNAL_CSV = HERE / "external" / "vdem.csv"
EXT_COUNTRY_COL = "country_name"
EXT_YEAR_COL = "year"
EXT_SOCIETY_COL = "v2xcs_ccsi"   # V-Dem core civil society index (0-1)
EXT_STATE_COL = "v2x_rule"       # V-Dem rule-of-law index as a state-capacity proxy
# LLM country name -> external-dataset country name
COUNTRY_TO_EXT = {
    "Iran (Persia)": "Iran",
    "United States": "United States of America",
    "United Kingdom": "United Kingdom",
    "France": "France",
    "China": "China",
    "Chile": "Chile",
}


def _mid(period) -> int:
    return (period[0] + period[1]) // 2


def _corr(a, b):
    """Pearson r over paired values; None if too few points or no variance."""
    if len(a) < 3 or len(set(a)) < 2 or len(set(b)) < 2:
        return None
    return pearsonr(a, b)[0]


def _fmt(r) -> str:
    return f"{r:.2f}" if r is not None else r"\ph{--}"


def load_runs() -> dict[str, dict[str, object]]:
    """country -> {model -> NarrowCorridorPath} for every run on disk."""
    by_country: dict[str, dict[str, object]] = defaultdict(dict)
    for f in sorted(RUNS_DIR.glob("*.json")):
        path = load_path(f)
        by_country[path.country][path.model] = path
    return by_country


# ----------------------------------------------------------------------------
def inter_model_table(by_country) -> None:
    rows = []
    all_soc, all_sta = [], []
    for country in COUNTRIES:
        models = by_country.get(country, {})
        if len(models) < 2:
            rows.append((country, len(models), None, None))
            continue
        # common periods across the models we have for this country
        common = set.intersection(*(set(p.periods) for p in models.values()))
        common = sorted(common)
        soc_series = {m: [p.society_power[per] for per in common] for m, p in models.items()}
        sta_series = {m: [p.state_power[per] for per in common] for m, p in models.items()}
        soc_pairs, sta_pairs = [], []
        for m1, m2 in itertools.combinations(models, 2):
            if (r := _corr(soc_series[m1], soc_series[m2])) is not None:
                soc_pairs.append(r)
            if (r := _corr(sta_series[m1], sta_series[m2])) is not None:
                sta_pairs.append(r)
        soc_mean = sum(soc_pairs) / len(soc_pairs) if soc_pairs else None
        sta_mean = sum(sta_pairs) / len(sta_pairs) if sta_pairs else None
        rows.append((country, len(models), soc_mean, sta_mean))
        all_soc += soc_pairs
        all_sta += sta_pairs

    overall_soc = sum(all_soc) / len(all_soc) if all_soc else None
    overall_sta = sum(all_sta) / len(all_sta) if all_sta else None

    lines = [
        r"\begin{table}[t]", r"\centering", r"\small",
        r"\caption{Inter-model agreement: mean pairwise Pearson $r$ between models "
        r"on the same country, over shared periods. Higher $=$ more reliable.}",
        r"\label{tab:intermodel}",
        r"\begin{tabular}{lccc}", r"\toprule",
        r"Country & \#models & Society $r$ & State $r$ \\", r"\midrule",
    ]
    for country, k, soc, sta in rows:
        lines.append(f"{country} & {k} & {_fmt(soc)} & {_fmt(sta)} \\\\")
    lines += [
        r"\midrule",
        f"\\textbf{{Overall}} & -- & \\textbf{{{_fmt(overall_soc)}}} & \\textbf{{{_fmt(overall_sta)}}} \\\\",
        r"\bottomrule", r"\end{tabular}", r"\end{table}",
    ]
    (TABLES_DIR / "intermodel.tex").write_text("\n".join(lines) + "\n")
    print(f"wrote intermodel.tex (society overall={_fmt(overall_soc)}, state={_fmt(overall_sta)})")


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
    # Use one model as the reference series for external validation.
    ref_model = "anthropic/claude-opus-4-8"

    lines = [
        r"\begin{table}[t]", r"\centering", r"\small",
        r"\caption{External validation: correlation of LLM scores "
        r"(\texttt{claude-opus-4-8}) with expert indices at period-midpoint years. "
        r"Society vs.\ V-Dem core civil society; State vs.\ V-Dem rule-of-law proxy.}",
        r"\label{tab:validation}",
        r"\begin{tabular}{lcccc}", r"\toprule",
        r"Country & Window & $N$ & Society $r$ & State $r$ \\", r"\midrule",
    ]
    for country, start in COUNTRIES.items():
        window = f"{start}--{END}"
        soc_r = sta_r = None
        n = 0
        path = by_country.get(country, {}).get(ref_model)
        if path is not None and ext is not None:
            ext_name = COUNTRY_TO_EXT.get(country, country)
            ext_years = ext.get(ext_name, {})
            ls, es, lt, et = [], [], [], []
            for per in path.periods:
                yr = _mid(per)
                if yr in ext_years:
                    e_soc, e_sta = ext_years[yr]
                    ls.append(path.society_power[per]); es.append(e_soc)
                    lt.append(path.state_power[per]); et.append(e_sta)
            n = len(ls)
            soc_r, sta_r = _corr(ls, es), _corr(lt, et)
        lines.append(f"{country} & {window} & {n or r'\ph{--}'} & {_fmt(soc_r)} & {_fmt(sta_r)} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
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
