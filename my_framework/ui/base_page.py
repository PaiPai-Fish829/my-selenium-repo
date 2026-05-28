from __future__ import annotations

import os
from typing import Any

from seleniumbase import BaseCase

from my_framework.shared.config_utils import PROJECT_ROOT, load_yaml
from my_framework.ui.assertions import (
    assert_page_contains_all,
    assert_page_contains_any,
    assert_page_not_contains,
    assert_url_contains,
)


class BasePage:
    """
    封装目的:
    - 提供框架级 UI 页面对象公共基类，沉淀页面导航、基础操作与常用断言。

    封装实现:
    - 持有 SeleniumBase 实例并从测试上下文/配置文件解析 base_url。
    - 封装 open_path/click/type 等页面基础动作。
    - 复用 my_framework.ui.assertions 提供页面内容与 URL 断言能力。

    外部接口:
    - 页面对象通过继承 BasePage 获取通用能力。
    - 对外暴露 open_path、click、type 及 assert_* 断言方法。
    """

    _config_cache: dict[str, Any] | None = None

    def __init__(self, sb: BaseCase) -> None:
        """
        封装目的:
        - 初始化页面对象上下文，绑定浏览器实例并解析基础地址。

        封装实现:
        - 保存 sb 引用。
        - 调用 _get_base_url 计算当前实例可用的 base_url。

        外部接口:
        - 入参: sb（SeleniumBase BaseCase 实例）。
        - 出参: 无。
        """
        self.sb = sb
        self.base_url = self._get_base_url()

    @classmethod
    def _get_config(cls) -> dict[str, Any]:
        """
        封装目的:
        - 懒加载并缓存全局配置，减少重复 I/O。

        封装实现:
        - 首次读取 PROJECT_ROOT/config.yaml 并缓存到类变量。

        外部接口:
        - 入参: 无。
        - 出参: 配置字典。
        """
        if cls._config_cache is None:
            cls._config_cache = load_yaml(PROJECT_ROOT / "config.yaml")
        return cls._config_cache

    def _get_base_url(self) -> str:
        """
        封装目的:
        - 统一解析页面访问基础地址，兼容测试上下文与配置文件来源。

        封装实现:
        - 优先读取 sb.current_config.base_url（由 BaseTest 注入）。
        - 若不存在则回退到 config.yaml 的 environments.<TEST_ENV>.base_url。

        外部接口:
        - 入参: 无。
        - 出参: 去除尾部斜杠后的 base_url 字符串。
        """
        current_config = getattr(self.sb, "current_config", None)
        if isinstance(current_config, dict) and current_config.get("base_url"):
            return str(current_config["base_url"]).rstrip("/")

        config = self._get_config()
        env_name = os.getenv("TEST_ENV", "default")
        env_config = config.get("environments", {}).get(env_name, {})
        return str(env_config.get("base_url", "")).rstrip("/")

    def open_path(self, path: str) -> None:
        """
        封装目的:
        - 提供统一页面打开能力，兼容绝对 URL 与相对路径。

        封装实现:
        - 绝对 URL 直接打开。
        - 相对路径自动拼接 base_url 并访问。
        - 未配置 base_url 时抛错提示配置问题。

        外部接口:
        - 入参: path（绝对 URL 或相对路径）。
        - 出参: 无。
        - 异常: base_url 缺失时抛 ValueError。
        """
        if path.startswith("http://") or path.startswith("https://"):
            self.sb.open(path)
            return
        normalized = path if path.startswith("/") else f"/{path}"
        if not self.base_url:
            raise ValueError("base_url 未配置，请检查 config.yaml environments")
        self.sb.open(f"{self.base_url}{normalized}")

    def click(self, selector: str) -> None:
        """
        封装目的:
        - 统一点击动作入口，保持页面对象调用风格一致。

        封装实现:
        - 直接代理到 SeleniumBase 的 click。

        外部接口:
        - 入参: selector（元素定位表达式）。
        - 出参: 无。
        """
        self.sb.click(selector)

    def type(self, selector: str, text: str) -> None:
        """
        封装目的:
        - 统一输入动作入口，减少页面对象中重复代码。

        封装实现:
        - 直接代理到 SeleniumBase 的 type。

        外部接口:
        - 入参: selector、text。
        - 出参: 无。
        """
        self.sb.type(selector, text)

    def assert_page_contains_any(
        self, *keywords: str, message: str | None = None, check_url: bool = True
    ) -> None:
        """
        封装目的:
        - 提供页面“任一关键词命中”断言的页面对象级快捷调用。

        封装实现:
        - 转调 my_framework.ui.assertions.assert_page_contains_any。

        外部接口:
        - 入参: keywords、message、check_url。
        - 出参: 无；失败抛 AssertionError。
        """
        assert_page_contains_any(self.sb, *keywords, message=message, check_url=check_url)

    def assert_page_contains_all(
        self, *keywords: str, message: str | None = None, check_url: bool = True
    ) -> None:
        """
        封装目的:
        - 提供页面“全部关键词命中”断言快捷调用。

        封装实现:
        - 转调 my_framework.ui.assertions.assert_page_contains_all。

        外部接口:
        - 入参: keywords、message、check_url。
        - 出参: 无；失败抛 AssertionError。
        """
        assert_page_contains_all(self.sb, *keywords, message=message, check_url=check_url)

    def assert_page_not_contains(
        self, *keywords: str, message: str | None = None, check_url: bool = True
    ) -> None:
        """
        封装目的:
        - 提供页面“不应包含关键词”断言快捷调用。

        封装实现:
        - 转调 my_framework.ui.assertions.assert_page_not_contains。

        外部接口:
        - 入参: keywords、message、check_url。
        - 出参: 无；失败抛 AssertionError。
        """
        assert_page_not_contains(self.sb, *keywords, message=message, check_url=check_url)

    def assert_url_contains(
        self, *fragments: str, match_all: bool = False, message: str | None = None
    ) -> None:
        """
        封装目的:
        - 提供 URL 片段断言快捷调用。

        封装实现:
        - 转调 my_framework.ui.assertions.assert_url_contains。

        外部接口:
        - 入参: fragments、match_all、message。
        - 出参: 无；失败抛 AssertionError。
        """
        assert_url_contains(self.sb, *fragments, match_all=match_all, message=message)
