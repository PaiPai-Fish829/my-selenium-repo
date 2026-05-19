from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from seleniumbase import BaseCase

ROOT_DIR = Path(__file__).resolve().parents[1]


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


class BasePage:
    """所有页面对象的公共基类。"""

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
        # 优先复用 BaseTest 注入的当前环境配置
        current_config = getattr(self.sb, "current_config", None)
        if isinstance(current_config, dict) and current_config.get("base_url"):
            return str(current_config["base_url"]).rstrip("/")

        config = self._get_config()
        env_name = os.getenv("TEST_ENV", "default")
        env_config = config.get("environments", {}).get(env_name, {})
        return str(env_config.get("base_url", "")).rstrip("/")

    def open(self, url: str) -> None:
        self.sb.open(url)

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

    def wait_visible(self, selector: str, timeout: int = 10) -> None:
        self.sb.wait_for_element_visible(selector, timeout=timeout)

    def assert_page_contains(
        self,
        *keywords: str,
        match_all: bool = False,
        message: str | None = None,
        check_url: bool = True,
    ) -> None:
        """断言当前页面包含关键词（match_all=False 为 OR，True 为 AND）。"""
        from my_framework.assertions import assert_page_contains

        assert_page_contains(
            self.sb,
            *keywords,
            match_all=match_all,
            message=message,
            check_url=check_url,
        )

    def assert_page_contains_any(
        self, *keywords: str, message: str | None = None, check_url: bool = True
    ) -> None:
        self.assert_page_contains(
            *keywords, match_all=False, message=message, check_url=check_url
        )

    def assert_page_contains_all(
        self, *keywords: str, message: str | None = None, check_url: bool = True
    ) -> None:
        self.assert_page_contains(
            *keywords, match_all=True, message=message, check_url=check_url
        )

    def assert_page_not_contains(
        self, *keywords: str, message: str | None = None, check_url: bool = True
    ) -> None:
        from my_framework.assertions import assert_page_not_contains

        assert_page_not_contains(
            self.sb, *keywords, message=message, check_url=check_url
        )

    def assert_url_contains(
        self, *fragments: str, match_all: bool = False, message: str | None = None
    ) -> None:
        from my_framework.assertions import assert_url_contains

        assert_url_contains(self.sb, *fragments, match_all=match_all, message=message)
