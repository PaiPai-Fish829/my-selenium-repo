from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from selenium.common.exceptions import NoSuchWindowException, WebDriverException
from seleniumbase import BaseCase

from my_framework.shared.allure_utils import attach_png, attach_text
from my_framework.shared.config_utils import DATA_DIR, PROJECT_ROOT, coerce_bool, load_yaml, read_by_path
from my_framework.ui.assertions import (
    assert_page_contains,
    assert_page_contains_all,
    assert_page_contains_any,
    assert_page_not_contains,
    assert_url_contains,
)


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
            cls._config_cache = load_yaml(PROJECT_ROOT / "config.yaml")
        if cls._test_data_cache is None:
            cls._test_data_cache = load_yaml(DATA_DIR / "test_data.yaml")

    def get_config(self, key_path: str | None = None, default: Any = None) -> Any:
        return read_by_path(self._config_cache or {}, key_path, default)

    def get_test_data(self, key_path: str | None = None, default: Any = None) -> Any:
        return read_by_path(self._test_data_cache or {}, key_path, default)

    def is_screenshot_on_failure_enabled(self) -> bool:
        """是否开启失败截图（优先读环境变量 SCREENSHOT_ON_FAILURE）。"""
        env_val = os.getenv("SCREENSHOT_ON_FAILURE")
        if env_val is not None:
            return coerce_bool(env_val, default=False)
        return coerce_bool(
            self.get_config("project.screenshot_on_failure", True),
            default=True,
        )

    def _get_screenshot_dir(self) -> Path:
        rel_dir = self.get_config("project.screenshot_dir", "artifacts/screenshots")
        path = Path(str(rel_dir))
        if not path.is_absolute():
            path = PROJECT_ROOT / path
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
            attached = attach_png(saved_path, name=f"{test_name}-failure-screenshot")
            if attached:
                try:
                    attach_text("failure-url", self.get_current_url())
                except Exception:
                    pass
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
