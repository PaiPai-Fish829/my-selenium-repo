from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from my_framework.api_client import ApiClient

ROOT_DIR = Path(__file__).resolve().parents[2]


def _load_project_config() -> dict[str, Any]:
    with (ROOT_DIR / "config.yaml").open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@pytest.fixture(scope="session")
def api_settings(request: pytest.FixtureRequest) -> dict[str, Any]:
    config = _load_project_config()
    env_name = request.config.getoption("--test-env")
    envs = config.get("environments", {})
    selected = envs.get(env_name, {})
    return {
        "base_url": selected.get("api_base_url", "https://httpbin.org"),
        "timeout": int(selected.get("api_timeout", 10)),
    }


@pytest.fixture
def api_client(api_settings: dict[str, Any]) -> ApiClient:
    return ApiClient(
        base_url=str(api_settings["base_url"]),
        timeout=int(api_settings["timeout"]),
        default_headers={"Content-Type": "application/json"},
    )
