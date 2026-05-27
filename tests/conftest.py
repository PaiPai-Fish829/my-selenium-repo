from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
import yaml

from my_framework.shared.allure_utils import (
    write_categories_json,
    write_environment_properties,
    write_executor_json,
)

ROOT_DIR = Path(__file__).resolve().parents[1]


def _load_config() -> dict[str, Any]:
    config_path = ROOT_DIR / "config.yaml"
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _resolve_allure_results_dir(config: pytest.Config) -> Path | None:
    try:
        alluredir = config.getoption("--alluredir")
    except Exception:
        return None
    if not alluredir:
        return None
    return Path(str(alluredir))


def pytest_sessionstart(session: pytest.Session) -> None:
    allure_results_dir = _resolve_allure_results_dir(session.config)
    if allure_results_dir is None:
        return

    config = _load_config()
    test_env = os.getenv("TEST_ENV", session.config.getoption("--test-env"))
    custom_categories = config.get("allure", {}).get("categories", []) if isinstance(config, dict) else []
    if not isinstance(custom_categories, list):
        custom_categories = []

    write_environment_properties(
        allure_results_dir,
        config=config,
        test_env=test_env,
    )
    write_categories_json(
        allure_results_dir,
        custom_categories=custom_categories,
    )
    write_executor_json(allure_results_dir)
