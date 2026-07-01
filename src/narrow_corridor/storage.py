"""Persist a NarrowCorridorPath as JSON (portable, diff-able; replaces pickle)."""

from __future__ import annotations

import json
from pathlib import Path

from narrow_corridor.models import NarrowCorridorPath


def save_path(path: NarrowCorridorPath, filename: str | Path) -> Path:
    out = Path(filename)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(path.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def load_path(filename: str | Path) -> NarrowCorridorPath:
    data = json.loads(Path(filename).read_text(encoding="utf-8"))
    return NarrowCorridorPath.from_dict(data)
