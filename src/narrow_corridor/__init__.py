"""Visualize a country's Narrow Corridor trajectory using LLMs.

See Acemoglu & Robinson, *The Narrow Corridor: States, Societies, and the Fate
of Liberty* (2019). This package places a country's history in the 2D space of
state power vs. society power, scored by an LLM (any provider, via LiteLLM).
"""

from narrow_corridor.models import NarrowCorridorPath, PeriodScore
from narrow_corridor.pipeline import get_narrow_corridor
from narrow_corridor.storage import load_path, save_path

__all__ = [
    "NarrowCorridorPath",
    "PeriodScore",
    "get_narrow_corridor",
    "load_path",
    "save_path",
]
