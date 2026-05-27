from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def read_by_path(source: Mapping[str, Any] | None, key_path: str | None, default: Any = None) -> Any:
    if source is None:
        return default
    if not key_path:
        return source
    value: Any = source
    for key in key_path.split("."):
        if isinstance(value, Mapping) and key in value:
            value = value[key]
        else:
            return default
    return value


def coerce_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return default
