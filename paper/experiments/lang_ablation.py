#!/usr/bin/env python3
"""Prompt-language ablation: does the prompt/response language bias the scores?

    uv run python paper/experiments/lang_ablation.py            # generate + figures
    uv run python paper/experiments/lang_ablation.py --no-run   # figures only (reuse cached runs)

For each showcase country we re-run the whole ensemble (the same MODELS as the
main sweep) with the prompts translated into that country's language, and
compare the resulting ensemble-mean trajectory against the English one:

    French  -> France      Chinese -> China      Persian -> Iran (Persia)

Only the prompt/response *prose* changes; the requested JSON fields stay English
(prompts.py), so the scores are directly comparable. English runs are reused
from paper/experiments/results/; the translated runs land in
paper/experiments/results_lang/ (a separate dir so analysis.load_runs never
counts them as extra raters). Per country we emit a two-path overlay figure
(English vs native, with connectors showing each period's displacement) and a
consistency row in derived/lang_ablation.csv.

This is the "non-English prompting probe" listed as Future Work in RUNBOOK.md.
Only the generation step calls an LLM (and it is cached).
"""

from __future__ import annotations

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor
from statistics import fmean

import matplotlib.pyplot as plt
from scipy.stats import spearmanr

from narrow_corridor.models import NarrowCorridorPath
from narrow_corridor.pipeline import get_narrow_corridor
from narrow_corridor.plot import _bounds, _draw_corridor
from narrow_corridor.storage import load_path, save_path
from run_experiments import COUNTRIES, END, MODELS, RUNS_DIR, STEP, slug

# country <-> its language. The native language is the one whose bias we probe
# for that country (the showcase in the request).
LANG_COUNTRY = {"fr": "France", "zh": "China", "fa": "Iran (Persia)",
                "es": "Chile", "ar": "Lebanon"}
LANG_NAME = {"fr": "French", "zh": "Chinese", "fa": "Persian",
             "es": "Spanish", "ar": "Arabic"}
# Native-language name of the country, used *inside* the translated prompts so the
# whole prompt is one language (the English canonical name stays for storage/slugs).
NATIVE_NAME = {"France": "la France", "China": "中国", "Iran (Persia)": "ایران",
               "Chile": "Chile", "Lebanon": "لبنان"}

LANG_DIR = RUNS_DIR.parent / "results_lang"     # kept out of results/ on purpose
DERIVED = RUNS_DIR.parent / "derived"
EN_COLOR, XX_COLOR = "#1f77b4", "#d62728"       # English blue vs native red


def _generate_one(lang: str, country: str, model: str) -> None:
    """Generate one (country, language, model) run and save it (cached).

    Periods inside a run stay sequential (in-context anchoring), but each run is
    independent, so the caller fans these out across threads.
    """
    stem = f"{slug(country)}__{slug(model)}__{lang}"
    print(f"=== {country} | {lang} | {model} -> {stem} ===", flush=True)
    try:
        path = get_narrow_corridor(
            model=model, country=country,
            start_year=COUNTRIES[country], end_year=END, step_years=STEP, lang=lang,
            prompt_country=NATIVE_NAME[country],
        )
    except Exception as e:  # keep going; a missing key/model just drops a rater
        print(f"  SKIPPED {country}|{lang}|{model} ({type(e).__name__}: {e})", flush=True)
        return
    save_path(path, LANG_DIR / f"{stem}.json")
    print(f"=== DONE {country} | {lang} | {model} ===", flush=True)


def _generate_all(workers: int) -> None:
    """Fan every (language, country, model) run out across a thread pool.

    Runs are network-bound (LLM calls), so threads overlap the waits. Concurrent
    runs write distinct cache files (the key includes model+prompt, which differ),
    so no two threads touch the same cache entry.
    """
    LANG_DIR.mkdir(parents=True, exist_ok=True)
    tasks = [(lang, country, model)
             for lang, country in LANG_COUNTRY.items() for model in MODELS]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(lambda t: _generate_one(*t), tasks))


def _load_models(country: str, lang: str | None) -> dict[str, NarrowCorridorPath]:
    """model -> path for one country. lang=None loads the English runs in results/."""
    out: dict[str, NarrowCorridorPath] = {}
    for model in MODELS:
        stem = f"{slug(country)}__{slug(model)}" + (f"__{lang}" if lang else "")
        f = (LANG_DIR if lang else RUNS_DIR) / f"{stem}.json"
        if f.exists():
            out[model] = load_path(f)
    return out


def _mean_path(country: str, models: dict[str, NarrowCorridorPath], periods, tag: str):
    mean = NarrowCorridorPath(country=country, model=f"ensemble-mean ({tag})")
    for per in periods:
        mean.periods.append(per)
        mean.society_power[per] = round(fmean(p.society_power[per] for p in models.values()), 3)
        mean.state_power[per] = round(fmean(p.state_power[per] for p in models.values()), 3)
    return mean


def _diff(seq):
    return [b - a for a, b in zip(seq, seq[1:])]


def _draw_path(ax, path, color, label):
    x = [path.society_power[p] for p in path.periods]
    y = [path.state_power[p] for p in path.periods]
    ax.plot(x, y, "-", color=color, lw=2, label=label, zorder=3)
    ax.scatter(x, y, color=color, s=28, zorder=4, edgecolors="white", linewidths=0.5)
    ax.scatter([x[0]], [y[0]], color=color, s=110, marker="o", zorder=5,
               edgecolors="black", linewidths=0.8)   # start (hollow-ish)
    ax.scatter([x[-1]], [y[-1]], color=color, s=150, marker="*", zorder=5,
               edgecolors="black", linewidths=0.8)    # end
    return x, y


def _panel(ax, country, lang, en_mean, xx_mean):
    """Overlay English vs native ensemble paths on one axis; return metrics."""
    ex, ey = _draw_path(ax, en_mean, EN_COLOR, "English prompts")
    xx, xy = _draw_path(ax, xx_mean, XX_COLOR, f"{LANG_NAME[lang]} prompts")
    # connectors: how far each period moves when the language changes
    for i in range(len(ex)):
        ax.plot([ex[i], xx[i]], [ey[i], xy[i]], "-", color="0.6", lw=0.7, zorder=2)

    lo, hi = _bounds(ex + xx, ey + xy)
    _draw_corridor(ax, lo, hi)
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_xlabel("Society Power"); ax.set_ylabel("State Power")
    ax.set_title(f"{country}: English vs {LANG_NAME[lang]} prompts")
    ax.legend(loc="best", fontsize=8, framealpha=0.9)

    # ---- consistency metrics ------------------------------------------------
    d_soc = [a - b for a, b in zip(ex, xx)]
    d_sta = [a - b for a, b in zip(ey, xy)]
    rmsd = (fmean([s * s + t * t for s, t in zip(d_soc, d_sta)])) ** 0.5
    end_shift = ((ex[-1] - xx[-1]) ** 2 + (ey[-1] - xy[-1]) ** 2) ** 0.5

    def _rho(a, b):  # Spearman on first differences: is the shape/timing preserved?
        if len(a) < 3 or len(set(a)) < 2 or len(set(b)) < 2:
            return None
        return spearmanr(a, b).statistic

    return {
        "country": country,
        "language": LANG_NAME[lang],
        "n_models": None,  # filled by caller
        "n_periods": len(ex),
        "mad_society": round(fmean(abs(v) for v in d_soc), 3),
        "mad_state": round(fmean(abs(v) for v in d_sta), 3),
        "rmsd": round(rmsd, 3),
        "endpoint_shift": round(end_shift, 3),
        "rho_dsociety": _rho(_diff(ex), _diff(xx)),
        "rho_dstate": _rho(_diff(ey), _diff(xy)),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-run", action="store_true",
                    help="Skip LLM generation; build figures from cached runs only.")
    ap.add_argument("--workers", type=int, default=6,
                    help="Concurrent runs (country×model×lang) during generation.")
    args = ap.parse_args()

    if not args.no_run:
        _generate_all(args.workers)

    LANG_DIR.mkdir(parents=True, exist_ok=True)
    DERIVED.mkdir(parents=True, exist_ok=True)

    rows = []
    n = len(LANG_COUNTRY)
    ncols = min(3, n)
    nrows = -(-n // ncols)  # ceil
    combined, axgrid = plt.subplots(nrows, ncols, figsize=(7 * ncols, 7 * nrows),
                                    squeeze=False)
    axes = axgrid.ravel()
    for ax in axes[n:]:  # hide unused cells (e.g. the 6th when there are 5 countries)
        ax.set_visible(False)
    for ax, (lang, country) in zip(axes, LANG_COUNTRY.items()):
        en = _load_models(country, None)
        xx = _load_models(country, lang)
        shared_models = sorted(set(en) & set(xx))
        if len(shared_models) < 2:
            print(f"(skip {country}/{lang}: need >=2 models in both languages, "
                  f"have {len(shared_models)})")
            ax.set_visible(False)
            continue
        en = {m: en[m] for m in shared_models}
        xx = {m: xx[m] for m in shared_models}
        periods = sorted(set.intersection(*(set(p.periods) for p in {**en, **xx}.values())))

        en_mean = _mean_path(country, en, periods, "English")
        xx_mean = _mean_path(country, xx, periods, LANG_NAME[lang])
        save_path(en_mean, LANG_DIR / f"{slug(country)}__ensemble-mean__en.json")
        save_path(xx_mean, LANG_DIR / f"{slug(country)}__ensemble-mean__{lang}.json")

        row = _panel(ax, country, lang, en_mean, xx_mean)
        row["n_models"] = len(shared_models)
        rows.append(row)

        # also a standalone single-country figure
        single, sax = plt.subplots(figsize=(8, 8))
        _panel(sax, country, lang, en_mean, xx_mean)
        single_out = LANG_DIR / f"{slug(country)}__lang-compare-{lang}.png"
        single.savefig(single_out, bbox_inches="tight"); plt.close(single)
        print(f"{country:16} {LANG_NAME[lang]:8} {len(shared_models)} models, "
              f"{row['n_periods']} periods, RMSD={row['rmsd']}, "
              f"endpoint_shift={row['endpoint_shift']} -> {single_out.name}")

    combined.savefig(LANG_DIR / "lang-ablation.png", bbox_inches="tight")
    print(f"wrote {LANG_DIR / 'lang-ablation.png'}")

    if rows:
        cols = list(rows[0].keys())
        with (DERIVED / "lang_ablation.csv").open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader(); w.writerows(rows)
        print(f"wrote {DERIVED / 'lang_ablation.csv'}")


if __name__ == "__main__":
    main()
