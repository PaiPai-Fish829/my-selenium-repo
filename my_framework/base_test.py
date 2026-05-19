from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from seleniumbase import BaseCase
from selenium.common.exceptions import NoSuchWindowException, WebDriverException

from my_framework.assertions import (
    assert_page_contains,
    assert_page_contains_all,
    assert_page_contains_any,
    assert_page_not_contains,
    assert_url_contains,
)

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"


def _load_yaml(file_path: Path) -> dict[str, Any]:
    if not file_path.exists():
        return {}
    with file_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _coerce_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return default


class BaseTest(BaseCase):
    """项目测试基类：负责配置、数据读取和通用能力。"""

    _config_cache: dict[str, Any] | None = None
    _test_data_cache: dict[str, Any] | None = None

    def setUp(self) -> None:
        super().setUp()
        self._ensure_data_loaded()
        self.env = os.getenv("TEST_ENV", "default")
        self.current_config = self.get_config(f"environments.{self.env}", {})
        self._get_screenshot_dir()

    @classmethod
    def _ensure_data_loaded(cls) -> None:
        if cls._config_cache is None:
            cls._config_cache = _load_yaml(ROOT_DIR / "config.yaml")
        if cls._test_data_cache is None:
            cls._test_data_cache = _load_yaml(DATA_DIR / "test_data.yaml")

    def get_config(self, key_path: str | None = None, default: Any = None) -> Any:
        return self._read_by_path(self._config_cache or {}, key_path, default)

    def get_test_data(self, key_path: str | None = None, default: Any = None) -> Any:
        return self._read_by_path(self._test_data_cache or {}, key_path, default)

    @staticmethod
    def _read_by_path(source: dict[str, Any], key_path: str | None, default: Any) -> Any:
        if not key_path:
            return source
        value: Any = source
        for key in key_path.split("."):
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def is_screenshot_on_failure_enabled(self) -> bool:
        """是否开启失败截图（优先读环境变量 SCREENSHOT_ON_FAILURE）。"""
        env_val = os.getenv("SCREENSHOT_ON_FAILURE")
        if env_val is not None:
            return _coerce_bool(env_val, default=False)
        return _coerce_bool(
            self.get_config("project.screenshot_on_failure", True),
            default=True,
        )

    def _get_screenshot_dir(self) -> Path:
        rel_dir = self.get_config("project.screenshot_dir", "artifacts/screenshots")
        path = Path(str(rel_dir))
        if not path.is_absolute():
            path = ROOT_DIR / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_failure_artifacts(self, test_name: str) -> bool:
        """失败时保存截图。须在 tearDown 关闭浏览器之前调用。"""
        if not self.is_screenshot_on_failure_enabled():
            print("[截图] 已跳过：project.screenshot_on_failure=false")
            return False

        screenshot_dir = self._get_screenshot_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_name = f"{test_name}_{timestamp}"
        try:
            self.save_screenshot(name=screenshot_name, folder=str(screenshot_dir))
            saved_path = screenshot_dir / f"{screenshot_name}.png"
            print(f"[截图] 失败截图已保存: {saved_path}")
            return True
        except (NoSuchWindowException, WebDriverException) as exc:
            print(f"[截图] 保存失败（浏览器不可用）: {exc}")
            return False
        except Exception as exc:
            print(f"[截图] 保存失败: {exc}")
            return False

    def tearDown(self) -> None:
        """在 SeleniumBase 关闭浏览器之前保存失败截图。"""
        if self.is_screenshot_on_failure_enabled() and self.has_exception():
            test_name = getattr(self, "_testMethodName", "unknown_test")
            self.save_failure_artifacts(test_name)
        super().tearDown()

    def assert_page_contains(
        self,
        *keywords: str,
        match_all: bool = False,
        message: str | None = None,
        check_url: bool = True,
    ) -> None:
        """断言当前页面包含关键词（match_all=False 为 OR，True 为 AND）。"""
        assert_page_contains(
            self,
            *keywords,
            match_all=match_all,
            message=message,
            check_url=check_url,
        )

    def assert_page_contains_any(
        self, *keywords: str, message: str | None = None, check_url: bool = True
    ) -> None:
        assert_page_contains_any(self, *keywords, message=message, check_url=check_url)

    def assert_page_contains_all(
        self, *keywords: str, message: str | None = None, check_url: bool = True
    ) -> None:
        assert_page_contains_all(self, *keywords, message=message, check_url=check_url)

    def assert_page_not_contains(
        self, *keywords: str, message: str | None = None, check_url: bool = True
    ) -> None:
        assert_page_not_contains(self, *keywords, message=message, check_url=check_url)

    def assert_url_contains(
        self, *fragments: str, match_all: bool = False, message: str | None = None
    ) -> None:
        assert_url_contains(self, *fragments, match_all=match_all, message=message)
