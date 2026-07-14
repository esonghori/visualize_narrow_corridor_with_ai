"""Provider-agnostic LLM access via LiteLLM, with structured output and caching.

`complete_text` returns free text (used for the events/trends step).
`complete_structured` returns a validated `PeriodScore`, with a one-shot retry
and a regex fallback ported from the original notebook before giving up.

Responses are cached on disk keyed by (model, prompt[, schema]) so re-runs and
iteration are free — `get_narrow_corridor` is otherwise expensive.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from narrow_corridor.models import PeriodScore

load_dotenv()

DEFAULT_CACHE_DIR = Path("runs/.cache")

_FLOAT = r"[-+]?\d*\.?\d+"


def _cache_key(model: str, prompt: str, tag: str) -> str:
    h = hashlib.sha256(f"{model}\0{tag}\0{prompt}".encode("utf-8")).hexdigest()
    return h


def _cache_get(cache_dir: Path, key: str) -> Optional[str]:
    f = cache_dir / f"{key}.txt"
    if f.exists():
        return f.read_text(encoding="utf-8")
    return None


def _cache_put(cache_dir: Path, key: str, value: str) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"{key}.txt").write_text(value, encoding="utf-8")


def _raw_completion(model: str, prompt: str, response_format=None, *, max_attempts: int = 3) -> str:
    """One LiteLLM call, retried up to `max_attempts` times on transient errors.

    Providers (esp. OpenRouter's multi-backend routing) intermittently return
    rate-limit (429), provider-routing (400), timeout, or 5xx errors. Retrying
    with backoff lets a momentary blip clear or reroute instead of aborting the
    whole country run. litellm is imported lazily so `--help`/`models` stay fast.
    """
    import time

    import litellm

    kwargs: dict = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        # Our outputs are tiny (a short JSON object or two bulleted lists), so cap
        # the completion well below providers' 16k default. This also keeps the
        # (prompt+max_tokens) cost under credit-limited accounts' per-request
        # ceiling (OpenRouter rejects oversized max_tokens with HTTP 402).
        "max_tokens": 8192,
    }
    if response_format is not None:
        kwargs["response_format"] = response_format
    if model.startswith("openrouter/"):
        # OpenRouter multiplexes several backends per model. Its default order can
        # land on a rate-limited backend (DeepInfra 429) and then fall through to
        # one that can't serve the model the requested way (Novita -> 400). Steer
        # it to any healthy chat backend and let it fall back among them; this is
        # the difference between qwen dropping out and staying in the ensemble.
        kwargs["extra_body"] = {
            "provider": {"sort": "throughput", "allow_fallbacks": True,
                         "ignore": ["Novita"]}
        }

    last_error: Exception | None = None
    for attempt in range(max_attempts):
        try:
            resp = litellm.completion(**kwargs)
            return resp.choices[0].message.content or ""
        except Exception as e:  # noqa: BLE001 - retry any provider/transport error
            last_error = e
            if attempt + 1 < max_attempts:
                time.sleep(3 * (attempt + 1))  # 3s, then 6s backoff
    raise last_error


def complete_text(
    model: str, prompt: str, *, cache_dir: Path = DEFAULT_CACHE_DIR, use_cache: bool = True
) -> str:
    key = _cache_key(model, prompt, tag="text")
    if use_cache and (hit := _cache_get(cache_dir, key)) is not None:
        return hit
    out = _raw_completion(model, prompt)
    if use_cache:
        _cache_put(cache_dir, key, out)
    return out


def _regex_fallback(text: str, prev_society: float, prev_state: float) -> Optional[PeriodScore]:
    """Last-resort extraction of numbers from free text (ported from the notebook).

    Accepts a 4-tuple <society_change, state_change, society_power, state_power>
    or a 2-tuple <society_power, state_power>. Returns None if no match.
    """
    m4 = re.search(
        rf"<\s*({_FLOAT})\s*,\s*({_FLOAT})\s*,\s*({_FLOAT})\s*,\s*({_FLOAT})\s*>", text
    )
    if m4:
        sc, st, sp, stp = (float(m4.group(i)) for i in range(1, 5))
        return PeriodScore(
            society_power=sp,
            state_power=stp,
            society_change=sc,
            state_change=st,
            key_event="",
            reasoning=text.strip()[:300],
        )
    m2 = re.search(rf"<\s*({_FLOAT})\s*,\s*({_FLOAT})\s*>", text)
    if m2:
        sp, stp = float(m2.group(1)), float(m2.group(2))
        return PeriodScore(
            society_power=sp,
            state_power=stp,
            society_change=sp - prev_society,
            state_change=stp - prev_state,
            key_event="",
            reasoning=text.strip()[:300],
        )
    return None


def complete_structured(
    model: str,
    prompt: str,
    *,
    prev_society: float = 0.0,
    prev_state: float = 0.0,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    use_cache: bool = True,
) -> tuple[PeriodScore, str]:
    """Return a validated `PeriodScore` and the raw response text.

    Strategy: request JSON via LiteLLM `response_format`; validate with pydantic;
    on failure retry once with an explicit reminder; then try the regex fallback;
    then raise ValueError.
    """
    key = _cache_key(model, prompt, tag="PeriodScore")
    if use_cache and (hit := _cache_get(cache_dir, key)) is not None:
        score = _parse(hit, prev_society, prev_state)
        if score is not None:
            return score, hit

    raw = _raw_completion(model, prompt, response_format=PeriodScore)
    score = _parse(raw, prev_society, prev_state)

    if score is None:
        reminder = (
            prompt
            + "\n\nIMPORTANT: Respond with ONLY a single valid JSON object matching "
            "the requested fields. No prose, no markdown fences."
        )
        raw = _raw_completion(model, reminder, response_format=PeriodScore)
        score = _parse(raw, prev_society, prev_state)

    if score is None:
        raise ValueError(f"Could not parse a PeriodScore from response:\n{raw}")

    if use_cache:
        _cache_put(cache_dir, key, raw)
    return score, raw


def _parse(raw: str, prev_society: float, prev_state: float) -> Optional[PeriodScore]:
    text = raw.strip()
    try:
        return PeriodScore.model_validate_json(text)
    except Exception:
        pass
    # Locate the JSON object anywhere in the text (also handles ```json fences).
    obj = re.search(r"\{.*\}", text, re.DOTALL)
    if obj:
        try:
            return PeriodScore.model_validate_json(obj.group(0))
        except Exception:
            pass
    return _regex_fallback(text, prev_society, prev_state)


def known_models() -> list[tuple[str, str]]:
    """Suggested LiteLLM model strings and the env var each one needs."""
    return [
        ("gemini/gemini-2.5-pro", "GEMINI_API_KEY"),
        ("anthropic/claude-opus-4-8", "ANTHROPIC_API_KEY"),
        ("openai/gpt-5.5", "OPENAI_API_KEY"),
        ("openrouter/qwen/qwen-2.5-72b-instruct", "OPENROUTER_API_KEY"),
    ]


def env_status() -> dict[str, bool]:
    """Which provider keys are currently set in the environment."""
    return {
        var: bool(os.getenv(var))
        for var in {"GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY"}
    }
