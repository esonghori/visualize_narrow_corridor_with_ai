"""The two-call-per-period Chain-of-Thought + In-Context Learning loop."""

from __future__ import annotations

from pathlib import Path

from narrow_corridor import prompts
from narrow_corridor.llm import DEFAULT_CACHE_DIR, complete_structured, complete_text
from narrow_corridor.models import NarrowCorridorPath, Period, period_to_text


def get_narrow_corridor(
    model: str = "gemini/gemini-3.5-flash",
    country: str = "Iran (Persia)",
    start_year: int = 1870,
    end_year: int = 2025,
    step_years: int = 5,
    *,
    lang: str = "en",
    prompt_country: str | None = None,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    use_cache: bool = True,
) -> NarrowCorridorPath:
    """Score a country's trajectory period by period.

    For each period (except the first) we first ask the model to list events and
    trends (Chain-of-Thought), then feed that narrative plus all prior periods'
    scores (In-Context Learning) into a structured scoring call.

    ``lang`` selects the prompt language ("en"/"fr"/"zh"/"fa"); only the prose is
    translated, the returned scores are language-neutral (see prompts.py).
    ``prompt_country`` is the name used *inside* the prompts (default: ``country``);
    the language ablation passes the country's native-language name here so the
    prompt is fully in one language, while ``country`` stays the English canonical
    name used for storage, slugs, and figures.
    """
    prompt_country = prompt_country or country
    path = NarrowCorridorPath(country=country, model=model)

    def record(period: Period, score, raw: str, et_prompt: str, et_resp: str, sc_prompt: str):
        path.periods.append(period)
        path.society_power[period] = score.society_power
        path.state_power[period] = score.state_power
        path.key_event[period] = score.key_event
        path.reasoning[period] = score.reasoning
        path.events_trends_prompt[period] = et_prompt
        path.events_trends_response[period] = et_resp
        path.score_prompt[period] = sc_prompt
        path.score_response[period] = raw
        print(
            f"{period_to_text(period)}  society={score.society_power:.1f} "
            f"state={score.state_power:.1f}  | {score.key_event}"
        )

    # ----- first period (bootstrap, absolute values) ------------------------
    initial: Period = (start_year, start_year + step_years - 1)
    sc_prompt = prompts.bootstrap_score_prompt(prompt_country, start_year, end_year, initial, lang)
    score, raw = complete_structured(
        model, sc_prompt, cache_dir=cache_dir, use_cache=use_cache
    )
    record(initial, score, raw, "", "", sc_prompt)

    previous_scores_text = (
        f"{period_to_text(initial)}: <{score.society_power}, {score.state_power}>"
    )
    previous_period = initial

    # ----- subsequent periods (events -> score, with accumulated context) ---
    for year in range(start_year + step_years, end_year, step_years):
        period: Period = (year, year + step_years - 1)

        et_prompt = prompts.events_trends_prompt(prompt_country, period, lang)
        et_resp = complete_text(model, et_prompt, cache_dir=cache_dir, use_cache=use_cache)

        sc_prompt = prompts.score_prompt(
            country=prompt_country,
            start_year=start_year,
            end_year=end_year,
            period=period,
            previous_period=previous_period,
            events_trends_text=et_resp,
            previous_scores_text=previous_scores_text,
            lang=lang,
        )
        score, raw = complete_structured(
            model,
            sc_prompt,
            prev_society=path.society_power[previous_period],
            prev_state=path.state_power[previous_period],
            cache_dir=cache_dir,
            use_cache=use_cache,
        )
        record(period, score, raw, et_prompt, et_resp, sc_prompt)

        previous_scores_text += (
            f"\n{period_to_text(period)}: <{score.society_power}, {score.state_power}>"
        )
        previous_period = period

    return path
