from __future__ import annotations

from pages.base_page import BasePage


class SearchPage(BasePage):
    """ECShop 搜索页对象。"""

    PATH = "/ecshop/index.php"
    SEARCH_INPUT = "input[name='keywords'], #keyword"
    SEARCH_BUTTON = "input[name='imageField'], .fm_hd_btm_shbx_bttn"

    def open(self) -> None:
        self.open_path(self.PATH)

    def search(self, keywords: str) -> None:
        self.type(self.SEARCH_INPUT, keywords)
        self.click(self.SEARCH_BUTTON)

    def assert_search_success(self) -> None:
        """断言已进入搜索结果页。"""
        self.assert_page_contains_any(
            "search.php",
            "搜索结果",
            message="【搜索成功断言失败】未进入搜索结果页",
        )

    def assert_search_failed(self, expected_error: str = "未找到"):
        """断言搜索失败时的提示。"""
        self.assert_page_contains(
            expected_error,
            message=f"【搜索失败断言】期望出现提示: {expected_error}",
            check_url=False,
        )
