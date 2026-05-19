from __future__ import annotations

from pages.base_page import BasePage


class ShoppingPage(BasePage):
    """商品详情与加购页面对象（通常在搜索结果页进入）。"""

    FLOW_PATH = "/ecshop/flow.php"
    PRODUCT_LINK = "a[href*='goods.php?id=']"
    ADD_TO_CART_LINK = "a[href*='javascript:addToCart']"

    def click_product(self, goods_id: str = "141") -> None:
        """打开商品详情页。"""
        self.open_path(f"/ecshop/goods.php?id={goods_id}")

    def click_add_to_cart(self) -> None:
        self.click(self.ADD_TO_CART_LINK)

    def go_to_checkout(self) -> None:
        """加购后进入购物车/结算流程。"""
        if self.sb.is_element_present("a[href*='flow.php']"):
            self.click("a[href*='flow.php']")
        else:
            self.open_path(self.FLOW_PATH)

    def assert_shopping_success(self) -> None:
        self.assert_page_contains_any(
            "添加成功",
            "继续购物",
            "javascript:addToCart",
            "goods.php",
            message="【加购成功断言失败】未检测到商品页或加购成功标识",
        )
