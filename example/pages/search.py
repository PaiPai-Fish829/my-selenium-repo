from __future__ import annotations

from my_framework.ui.base_page import BasePage


class SearchPage(BasePage):
    PATH = "/ecshop/index.php"
    SEARCH_INPUT = "input[name='keywords'], #keyword"
    SEARCH_BUTTON = "input[name='imageField'], .fm_hd_btm_shbx_bttn"

    def open(self) -> None:
        self.open_path(self.PATH)

    def search(self, keywords: str) -> None:
        self.type(self.SEARCH_INPUT, keywords)
        self.click(self.SEARCH_BUTTON)

    def assert_search_success(self) -> None:
        self.assert_page_contains_any(
            "search.php",
            "搜索结果",
            message="【搜索成功断言失败】未进入搜索结果页",
        )
