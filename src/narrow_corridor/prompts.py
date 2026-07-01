"""Prompt templates for the Narrow Corridor scoring pipeline.

Two improvements over the original notebook prompts:

* An explicit, anchored 0-10 rubric for both axes, so scores are comparable
  across countries and across models instead of free-floating.
* Neutral, non-leading framing: the model is asked to weigh evidence both ways,
  avoid presentism, and not assume the country drifts toward any corner.

The Chain-of-Thought (events/trends first) and In-Context Learning (prior scores
fed forward) structure of the original methodology is preserved.
"""

from __future__ import annotations

from narrow_corridor.models import Period, period_to_text

# Shared rubric + neutrality guidance injected into every scoring prompt.
RUBRIC = """\
Use this fixed 0-10 rubric so values are comparable across periods and countries.

STATE POWER — the capacity of the state to enforce its will, administer
territory, collect taxes, and project authority:
  0-2  collapsed / nonexistent: no effective central authority.
  3-4  weak: limited reach, contested control, depends on local powerbrokers.
  5-6  moderate: functioning bureaucracy and military with real but bounded reach.
  7-8  strong: pervasive administration, effective coercion and revenue capacity.
  9-10 overwhelming: near-total penetration of society; little it cannot enforce.

SOCIETY POWER — the capacity of civil society to organize, mobilize, hold the
state accountable, and resist domination (norms, associations, press, protest,
independent institutions):
  0-2  atomized: no autonomous organization; collective action near-impossible.
  3-4  weak: sporadic, easily suppressed mobilization.
  5-6  moderate: real associational life and periodic effective mobilization.
  7-8  strong: dense civic institutions routinely constraining the state.
  9-10 dominant: society pervasively shapes and checks state action.

Guidance for objectivity:
- Judge each period on its own terms; do not assume the country trends toward
  liberty, autocracy, or any particular corner of the space.
- Weigh evidence both for and against a shift before settling on a number.
- Avoid presentism: score by the standards and information of the period, not
  by how things turned out later.
- These two axes are independent: a strong state can coexist with a strong or a
  weak society. Score them separately."""


def events_trends_prompt(country: str, period: Period) -> str:
    period_text = period_to_text(period)
    return f"""\
Considering Daron Acemoğlu and James A. Robinson's framework in *The Narrow
Corridor: States, Societies, and the Fate of Liberty*, identify the major
historical events and trends in {country} during {period_text} that materially
affected EITHER the power of the state OR the power of civil society.

Be concrete and specific to {period_text}. Distinguish slow-moving trends
(institutional, economic, demographic) from discrete events. For each item, note
briefly whether it strengthened or weakened the state, society, or both.

Respond with two short bulleted lists:

Trends:
- ...

Events:
- ..."""


def _common_score_framing(country: str, start_year: int, end_year: int) -> str:
    return f"""\
You are placing the country of {country} in the 2D space of Acemoğlu and
Robinson's *The Narrow Corridor*: the x-axis is the power of civil society and
the y-axis is the power of the state. We are tracing the path from {start_year}
to {end_year}.

{RUBRIC}"""


def bootstrap_score_prompt(country: str, start_year: int, end_year: int, period: Period) -> str:
    """First-period prompt: emit absolute <society, state> with changes = 0."""
    period_text = period_to_text(period)
    return f"""\
{_common_score_framing(country, start_year, end_year)}

This is the FIRST period of the trajectory: {period_text}. Establish the
starting point. Estimate the absolute power of civil society and of the state in
{country} during {period_text} using the rubric above. Since there is no prior
period, report both change values as 0.0.

Return a JSON object with exactly these fields:
- society_power (float, 0-10)
- state_power (float, 0-10)
- society_change (float, 0.0)
- state_change (float, 0.0)
- key_event (string, <= ~10 words: the single most defining feature of this period)
- reasoning (string, 1-2 sentences justifying the two power values)"""


def score_prompt(
    country: str,
    start_year: int,
    end_year: int,
    period: Period,
    previous_period: Period,
    events_trends_text: str,
    previous_scores_text: str,
) -> str:
    """Subsequent-period prompt: condition on this period's events + prior path."""
    period_text = period_to_text(period)
    previous_period_text = period_to_text(previous_period)
    return f"""\
{_common_score_framing(country, start_year, end_year)}

Score the period {period_text}, building on the established trajectory. Start
from where {country} stood at the end of {previous_period_text}, then apply the
changes implied by the events and trends below. Report both the per-axis change
and the resulting absolute values (anchored to the rubric, not just to the prior
point). A period with little real change should show changes near 0.0.

Historical events and trends in {period_text}:
{events_trends_text}

Trajectory so far (period: <society_power, state_power>):
{previous_scores_text}

Return a JSON object with exactly these fields:
- society_power (float, 0-10): absolute society power at the end of {period_text}
- state_power (float, 0-10): absolute state power at the end of {period_text}
- society_change (float): society_power change vs. {previous_period_text}
- state_change (float): state_power change vs. {previous_period_text}
- key_event (string, <= ~10 words: the defining event/trend driving the change)
- reasoning (string, 1-2 sentences justifying the values)"""
