from __future__ import annotations

from my_framework.ui.base_page import BasePage


class ShoppingPage(BasePage):
    FLOW_PATH = "/ecshop/flow.php"
    ADD_TO_CART_LINK = "a[href*='javascript:addToCart']"

    def click_product(self, goods_id: str = "141") -> None:
        self.open_path(f"/ecshop/goods.php?id={goods_id}")

    def click_add_to_cart(self) -> None:
        self.click(self.ADD_TO_CART_LINK)

    def go_to_checkout(self) -> None:
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
