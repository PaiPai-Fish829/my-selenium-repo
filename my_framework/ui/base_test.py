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
    """
    封装目的:
    - 为 UI 自动化测试提供统一基类，沉淀配置读取、断言增强和失败留证能力。

    封装实现:
    - 继承 SeleniumBase.BaseCase 并在 setUp/tearDown 中接入框架逻辑。
    - 通过类级缓存加载配置与测试数据，减少重复文件读取。
    - 封装页面内容/URL 断言与失败截图附件能力。

    外部接口:
    - 供 UI 测试类直接继承。
    - 对外提供 get_config/get_test_data/断言方法及失败工件保存方法。
    """

    _config_cache: dict[str, Any] | None = None
    _test_data_cache: dict[str, Any] | None = None

    def setUp(self) -> None:
        """
        封装目的:
        - 在每个 UI 用例开始前统一完成运行环境初始化。

        封装实现:
        - 调用父类 setUp 启动浏览器上下文。
        - 加载配置缓存并绑定当前环境配置。
        - 预创建截图目录，保证失败时可直接落盘。

        外部接口:
        - 入参: 无。
        - 出参: 无。
        """
        super().setUp()
        self._ensure_data_loaded()
        self.env = os.getenv("TEST_ENV", "default")
        self.current_config = self.get_config(f"environments.{self.env}", {})
        self._get_screenshot_dir()

    @classmethod
    def _ensure_data_loaded(cls) -> None:
        """
        封装目的:
        - 懒加载并缓存配置与测试数据，提升执行效率。

        封装实现:
        - 首次调用时读取 config.yaml 与 test_data.yaml。
        - 结果写入类变量缓存，后续用例复用。

        外部接口:
        - 入参: 无。
        - 出参: 无。
        """
        if cls._config_cache is None:
            cls._config_cache = load_yaml(PROJECT_ROOT / "config.yaml")
        if cls._test_data_cache is None:
            cls._test_data_cache = load_yaml(DATA_DIR / "test_data.yaml")

    def get_config(self, key_path: str | None = None, default: Any = None) -> Any:
        """
        封装目的:
        - 提供统一配置读取入口，支持点路径访问。

        封装实现:
        - 从已缓存配置中调用 read_by_path 获取目标值。

        外部接口:
        - 入参: key_path（可空）、default。
        - 出参: 配置值或默认值。
        """
        return read_by_path(self._config_cache or {}, key_path, default)

    def get_test_data(self, key_path: str | None = None, default: Any = None) -> Any:
        """
        封装目的:
        - 提供统一测试数据读取入口，减少用例中的 YAML 访问细节。

        封装实现:
        - 从测试数据缓存中按路径提取内容，不存在时返回默认值。

        外部接口:
        - 入参: key_path（可空）、default。
        - 出参: 测试数据值或默认值。
        """
        return read_by_path(self._test_data_cache or {}, key_path, default)

    def is_screenshot_on_failure_enabled(self) -> bool:
        """
        封装目的:
        - 统一判断是否启用失败截图策略。

        封装实现:
        - 优先读取环境变量 SCREENSHOT_ON_FAILURE。
        - 未设置时读取项目配置 project.screenshot_on_failure。
        - 使用 coerce_bool 兼容多类型布尔值。

        外部接口:
        - 入参: 无。
        - 出参: bool，True 表示启用失败截图。
        """
        env_val = os.getenv("SCREENSHOT_ON_FAILURE")
        if env_val is not None:
            return coerce_bool(env_val, default=False)
        return coerce_bool(
            self.get_config("project.screenshot_on_failure", True),
            default=True,
        )

    def _get_screenshot_dir(self) -> Path:
        """
        封装目的:
        - 解析并确保失败截图目录存在。

        封装实现:
        - 读取 project.screenshot_dir，支持相对路径转项目绝对路径。
        - 自动创建目录（含父目录）。

        外部接口:
        - 入参: 无。
        - 出参: 截图目录 Path。
        """
        rel_dir = self.get_config("project.screenshot_dir", "artifacts/screenshots")
        path = Path(str(rel_dir))
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_failure_artifacts(self, test_name: str) -> bool:
        """
        封装目的:
        - 在失败场景统一保存截图并附加到 Allure，提升问题定位效率。

        封装实现:
        - 根据配置开关决定是否执行。
        - 按测试名+时间戳生成截图文件，调用 SeleniumBase 保存截图。
        - 尝试向 Allure 附加图片与失败 URL。

        外部接口:
        - 入参: test_name（通常为测试方法名）。
        - 出参: bool，表示是否成功保存截图。
        """
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
        """
        封装目的:
        - 在用例结束时统一处理失败留证并完成资源回收。

        封装实现:
        - 检测失败且开关开启时先保存失败工件。
        - 最后调用父类 tearDown 关闭浏览器。

        外部接口:
        - 入参: 无。
        - 出参: 无。
        """
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
        """
        封装目的:
        - 为测试类提供实例化页面包含断言，简化用例调用。

        封装实现:
        - 透传参数到 ui.assertions.assert_page_contains。

        外部接口:
        - 入参: keywords、match_all、message、check_url。
        - 出参: 无；断言失败抛 AssertionError。
        """
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
        """
        封装目的:
        - 提供“任一关键词命中”页面断言快捷方法。

        封装实现:
        - 调用 ui.assertions.assert_page_contains_any 完成断言。

        外部接口:
        - 入参: keywords、message、check_url。
        - 出参: 无；断言失败抛 AssertionError。
        """
        assert_page_contains_any(self, *keywords, message=message, check_url=check_url)

    def assert_page_contains_all(
        self, *keywords: str, message: str | None = None, check_url: bool = True
    ) -> None:
        """
        封装目的:
        - 提供“全部关键词命中”页面断言快捷方法。

        封装实现:
        - 调用 ui.assertions.assert_page_contains_all 完成断言。

        外部接口:
        - 入参: keywords、message、check_url。
        - 出参: 无；断言失败抛 AssertionError。
        """
        assert_page_contains_all(self, *keywords, message=message, check_url=check_url)

    def assert_page_not_contains(
        self, *keywords: str, message: str | None = None, check_url: bool = True
    ) -> None:
        """
        封装目的:
        - 提供页面不包含关键词的负向断言快捷方法。

        封装实现:
        - 调用 ui.assertions.assert_page_not_contains 完成断言。

        外部接口:
        - 入参: keywords、message、check_url。
        - 出参: 无；断言失败抛 AssertionError。
        """
        assert_page_not_contains(self, *keywords, message=message, check_url=check_url)

    def assert_url_contains(
        self, *fragments: str, match_all: bool = False, message: str | None = None
    ) -> None:
        """
        封装目的:
        - 提供 URL 片段断言实例方法，减少测试代码重复。

        封装实现:
        - 调用 ui.assertions.assert_url_contains 并透传匹配模式。

        外部接口:
        - 入参: fragments、match_all、message。
        - 出参: 无；断言失败抛 AssertionError。
        """
        assert_url_contains(self, *fragments, match_all=match_all, message=message)
