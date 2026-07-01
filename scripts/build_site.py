#!/usr/bin/env python3
"""Build a static gallery site from a runs directory (for GitHub Pages).

    uv run python scripts/build_site.py                       # from ./runs
    uv run python scripts/build_site.py --runs paper/experiments/runs
    uv run python scripts/build_site.py --runs paper/experiments/runs --out docs

Scans <runs>/*.png (+ matching *.gif) named "<country-slug>__<model-slug>",
copies them into <out>/assets/, and writes a self-contained <out>/index.html.
Each card shows the static plot; clicking it loads the animation (GIFs are big,
so they're fetched on demand). Deploy: enable GitHub Pages on /docs.
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections import defaultdict
from html import escape
from pathlib import Path

# Preferred display order; anything else falls in alphabetically after.
COUNTRY_ORDER = ["Iran (Persia)", "France", "United Kingdom", "United States", "China", "Chile"]
MODEL_ORDER = [
    "gemini/gemini-3.5-flash",
    "anthropic/claude-opus-4-8",
    "openai/gpt-4o",
    "openrouter/qwen/qwen-2.5-72b-instruct",
]


def _order_key(value: str, order: list[str]):
    return (order.index(value), "") if value in order else (len(order), value.lower())


def discover(runs: Path):
    """[(country, model, png_path, gif_path_or_None)], driven off the JSON sidecars.

    Each run saves <stem>.json (with the real country/model) alongside
    <stem>.png/.gif, so we pair by stem and read names from the JSON. This is
    naming-scheme agnostic (works for both 'country__model' and ad-hoc stems).
    """
    items = []
    for j in sorted(runs.glob("*.json")):
        try:
            d = json.loads(j.read_text())
            country, model = d["country"], d["model"]
        except Exception:
            continue
        png = j.with_suffix(".png")
        if not png.exists():
            continue
        gif = j.with_suffix(".gif")
        items.append((country, model, png, gif if gif.exists() else None))
    return items


def build(runs: Path, out: Path) -> int:
    items = discover(runs)
    assets = out / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    by_country: dict[str, list] = defaultdict(list)
    models_seen: set[str] = set()
    for country, model, png, gif in items:
        shutil.copy2(png, assets / png.name)
        gif_name = None
        if gif is not None:
            shutil.copy2(gif, assets / gif.name)
            gif_name = gif.name
        by_country[country].append((model, png.name, gif_name))
        models_seen.add(model)

    countries = sorted(by_country, key=lambda c: _order_key(c, COUNTRY_ORDER))
    models = sorted(models_seen, key=lambda m: _order_key(m, MODEL_ORDER))

    filters = "".join(
        f'<button class="filter" data-model="{escape(m)}">{escape(m)}</button>' for m in models
    )
    sections = []
    for country in countries:
        cards = []
        cards_by_model = sorted(by_country[country], key=lambda t: _order_key(t[0], MODEL_ORDER))
        for model, png_name, gif_name in cards_by_model:
            anim = (
                f' data-gif="assets/{escape(gif_name)}"' if gif_name else ""
            )
            badge = '<span class="badge">▶ animate</span>' if gif_name else ""
            cards.append(
                f'<figure class="card" data-model="{escape(model)}">'
                f'<div class="imgwrap">'
                f'<img loading="lazy" src="assets/{escape(png_name)}" data-png="assets/{escape(png_name)}"{anim} alt="{escape(country)} — {escape(model)}">'
                f"{badge}</div>"
                f"<figcaption>{escape(model)}</figcaption></figure>"
            )
        sections.append(
            f'<section class="country"><h2>{escape(country)}</h2>'
            f'<div class="grid">{"".join(cards)}</div></section>'
        )

    note = "" if items else (
        '<p class="empty">No runs found. Generate them first '
        "(<code>uv run python paper/experiments/run_experiments.py --gif</code>), "
        "then re-run this script.</p>"
    )

    html = _TEMPLATE.format(
        filters=filters,
        sections="\n".join(sections),
        note=note,
        n=len(items),
        n_countries=len(countries),
    )
    (out / "index.html").write_text(html, encoding="utf-8")
    (out / ".nojekyll").write_text("")  # serve files verbatim (keeps '__' names)
    print(f"Wrote {out/'index.html'} — {len(items)} panels across {len(countries)} countries.")
    return len(items)


_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Narrow Corridor — Trajectory Atlas</title>
<style>
  :root {{ --bg:#faf9f6; --fg:#1b1b1b; --muted:#666; --accent:#2b7a4b; --line:#e2e0d8; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font:16px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
          color:var(--fg); background:var(--bg); }}
  header {{ padding:2rem 1.25rem 1rem; max-width:1100px; margin:0 auto; }}
  h1 {{ margin:0 0 .3rem; font-size:1.7rem; }}
  header p {{ margin:.2rem 0; color:var(--muted); }}
  header a {{ color:var(--accent); }}
  .controls {{ position:sticky; top:0; background:var(--bg); border-bottom:1px solid var(--line);
               padding:.6rem 1.25rem; z-index:5; }}
  .controls .inner {{ max-width:1100px; margin:0 auto; display:flex; flex-wrap:wrap; gap:.4rem; align-items:center; }}
  .filter {{ border:1px solid var(--line); background:#fff; color:var(--fg); border-radius:999px;
             padding:.3rem .8rem; cursor:pointer; font-size:.85rem; }}
  .filter.active {{ background:var(--accent); color:#fff; border-color:var(--accent); }}
  main {{ max-width:1100px; margin:0 auto; padding:1rem 1.25rem 4rem; }}
  .country h2 {{ font-size:1.25rem; border-bottom:2px solid var(--accent); padding-bottom:.2rem; margin:2rem 0 1rem; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:1rem; }}
  .card {{ margin:0; border:1px solid var(--line); border-radius:10px; overflow:hidden; background:#fff; }}
  .imgwrap {{ position:relative; cursor:pointer; }}
  .card img {{ width:100%; display:block; }}
  .badge {{ position:absolute; top:.5rem; right:.5rem; background:rgba(0,0,0,.62); color:#fff;
            font-size:.72rem; padding:.15rem .5rem; border-radius:999px; }}
  .imgwrap.playing .badge {{ background:var(--accent); }}
  figcaption {{ padding:.5rem .7rem; font-size:.8rem; color:var(--muted); font-family:ui-monospace,Menlo,monospace; }}
  .empty {{ color:var(--muted); }}
  footer {{ max-width:1100px; margin:0 auto; padding:2rem 1.25rem; color:var(--muted); font-size:.85rem; border-top:1px solid var(--line); }}
</style>
</head>
<body>
<header>
  <h1>The Narrow Corridor — Trajectory Atlas</h1>
  <p>State vs. society power paths, scored by LLMs. {n} panels · {n_countries} countries.</p>
  <p>Method &amp; code: <a href="https://github.com/esonghori/narrow-corridor-llm">GitHub repository</a>.
     Click any plot to play its animation.</p>
</header>
<div class="controls"><div class="inner">
  <button class="filter active" data-model="__all__">All models</button>
  {filters}
</div></div>
<main>
{note}
{sections}
</main>
<footer>
  Generated from committed run outputs. Axes: society power (x) vs. state power (y);
  dashed lines mark the corridor; color ramps dark→bright with time.
</footer>
<script>
  // Click a plot to swap the static PNG for its animated GIF (loaded on demand).
  document.querySelectorAll('.imgwrap').forEach(function (wrap) {{
    var img = wrap.querySelector('img');
    if (!img.dataset.gif) return;
    wrap.addEventListener('click', function () {{
      var playing = wrap.classList.toggle('playing');
      img.src = playing ? img.dataset.gif : img.dataset.png;
      var b = wrap.querySelector('.badge');
      if (b) b.textContent = playing ? '❚❚ static' : '▶ animate';
    }});
  }});
  // Model filter buttons.
  var buttons = document.querySelectorAll('.filter');
  buttons.forEach(function (btn) {{
    btn.addEventListener('click', function () {{
      buttons.forEach(function (b) {{ b.classList.remove('active'); }});
      btn.classList.add('active');
      var m = btn.dataset.model;
      document.querySelectorAll('.card').forEach(function (c) {{
        c.style.display = (m === '__all__' || c.dataset.model === m) ? '' : 'none';
      }});
      document.querySelectorAll('.country').forEach(function (sec) {{
        var any = Array.from(sec.querySelectorAll('.card')).some(function (c) {{ return c.style.display !== 'none'; }});
        sec.style.display = any ? '' : 'none';
      }});
    }});
  }});
</script>
</body>
</html>
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=Path, default=Path("runs"), help="Directory of run outputs.")
    ap.add_argument("--out", type=Path, default=Path("docs"), help="Site output directory.")
    args = ap.parse_args()
    build(args.runs, args.out)


if __name__ == "__main__":
    main()
