"""Data models for a Narrow Corridor trajectory."""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, Field

Period = tuple[int, int]


class PeriodScore(BaseModel):
    """Structured score the LLM returns for a single period.

    The same schema serves the bootstrap (first) period and all later periods;
    for the first period the model is told to report ``*_change`` as 0.0.
    """

    society_power: float = Field(
        description="Absolute power of civil society this period, on the 0-10 rubric."
    )
    state_power: float = Field(
        description="Absolute power of the state this period, on the 0-10 rubric."
    )
    society_change: float = Field(
        default=0.0,
        description="Change in society power vs. the previous period (0.0 for the first).",
    )
    state_change: float = Field(
        default=0.0,
        description="Change in state power vs. the previous period (0.0 for the first).",
    )
    key_event: str = Field(
        description="The single most defining event/trend of this period (<= ~10 words)."
    )
    reasoning: str = Field(
        description="One or two sentences justifying the two power values."
    )


def period_to_text(period: Period) -> str:
    return f"{period[0]}-{period[1]}"


@dataclass
class NarrowCorridorPath:
    """The full result object for one country/model run.

    Per-period data is keyed by the ``(start, end)`` tuple. Keeping the prompts
    and raw responses lets ``debug_path`` reconstruct exactly what was asked and
    answered.
    """

    country: str
    model: str
    periods: list[Period] = field(default_factory=list)
    society_power: dict[Period, float] = field(default_factory=dict)
    state_power: dict[Period, float] = field(default_factory=dict)
    key_event: dict[Period, str] = field(default_factory=dict)
    reasoning: dict[Period, str] = field(default_factory=dict)
    events_trends_prompt: dict[Period, str] = field(default_factory=dict)
    events_trends_response: dict[Period, str] = field(default_factory=dict)
    score_prompt: dict[Period, str] = field(default_factory=dict)
    score_response: dict[Period, str] = field(default_factory=dict)

    # ----- JSON (de)serialization -------------------------------------------
    # JSON object keys must be strings, so period tuples are encoded as "start-end".

    def to_dict(self) -> dict:
        def keyed(d: dict[Period, object]) -> dict[str, object]:
            return {period_to_text(p): v for p, v in d.items()}

        return {
            "country": self.country,
            "model": self.model,
            "periods": [list(p) for p in self.periods],
            "society_power": keyed(self.society_power),
            "state_power": keyed(self.state_power),
            "key_event": keyed(self.key_event),
            "reasoning": keyed(self.reasoning),
            "events_trends_prompt": keyed(self.events_trends_prompt),
            "events_trends_response": keyed(self.events_trends_response),
            "score_prompt": keyed(self.score_prompt),
            "score_response": keyed(self.score_response),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NarrowCorridorPath":
        periods: list[Period] = [tuple(p) for p in data["periods"]]
        by_text: dict[str, Period] = {period_to_text(p): p for p in periods}

        def unkeyed(d: dict[str, object]) -> dict[Period, object]:
            return {by_text[k]: v for k, v in d.items()}

        return cls(
            country=data["country"],
            model=data["model"],
            periods=periods,
            society_power=unkeyed(data.get("society_power", {})),
            state_power=unkeyed(data.get("state_power", {})),
            key_event=unkeyed(data.get("key_event", {})),
            reasoning=unkeyed(data.get("reasoning", {})),
            events_trends_prompt=unkeyed(data.get("events_trends_prompt", {})),
            events_trends_response=unkeyed(data.get("events_trends_response", {})),
            score_prompt=unkeyed(data.get("score_prompt", {})),
            score_response=unkeyed(data.get("score_response", {})),
        )
