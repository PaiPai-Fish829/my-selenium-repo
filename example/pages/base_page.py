from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from seleniumbase import BaseCase

ROOT_DIR = Path(__file__).resolve().parents[2]


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


class BasePage:
    """演示页面对象的公共基类。"""

    _config_cache: dict[str, Any] | None = None

    def __init__(self, sb: BaseCase) -> None:
        self.sb = sb
        self.base_url = self._get_base_url()

    @classmethod
    def _get_config(cls) -> dict[str, Any]:
        if cls._config_cache is None:
            cls._config_cache = _load_yaml(ROOT_DIR / "config.yaml")
        return cls._config_cache

    def _get_base_url(self) -> str:
        current_config = getattr(self.sb, "current_config", None)
        if isinstance(current_config, dict) and current_config.get("base_url"):
            return str(current_config["base_url"]).rstrip("/")

        config = self._get_config()
        env_name = os.getenv("TEST_ENV", "default")
        env_config = config.get("environments", {}).get(env_name, {})
        return str(env_config.get("base_url", "")).rstrip("/")

    def open_path(self, path: str) -> None:
        if path.startswith("http://") or path.startswith("https://"):
            self.sb.open(path)
            return
        normalized = path if path.startswith("/") else f"/{path}"
        if not self.base_url:
            raise ValueError("base_url 未配置，请检查 config.yaml environments")
        self.sb.open(f"{self.base_url}{normalized}")

    def click(self, selector: str) -> None:
        self.sb.click(selector)

    def type(self, selector: str, text: str) -> None:
        self.sb.type(selector, text)

    def assert_page_contains_any(
        self, *keywords: str, message: str | None = None, check_url: bool = True
    ) -> None:
        from my_framework.assertions_ui import assert_page_contains_any

        assert_page_contains_any(self.sb, *keywords, message=message, check_url=check_url)

    def assert_page_not_contains(
        self, *keywords: str, message: str | None = None, check_url: bool = True
    ) -> None:
        from my_framework.assertions_ui import assert_page_not_contains

        assert_page_not_contains(self.sb, *keywords, message=message, check_url=check_url)

    def assert_url_contains(
        self, *fragments: str, match_all: bool = False, message: str | None = None
    ) -> None:
        from my_framework.assertions_ui import assert_url_contains

        assert_url_contains(self.sb, *fragments, match_all=match_all, message=message)
