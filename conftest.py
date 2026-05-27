from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
import yaml

from my_framework.allure_utils import (
    write_categories_json,
    write_environment_properties,
    write_executor_json,
)

ROOT_DIR = Path(__file__).resolve().parent


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


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--test-env",
        action="store",
        default="default",
        help="选择运行环境（映射到 config.yaml 的 environments 节点）",
    )


@pytest.fixture(autouse=True)
def inject_test_env(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    env_name = request.config.getoption("--test-env")
    monkeypatch.setenv("TEST_ENV", env_name)
    yield


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


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
