from __future__ import annotations

from example.pages.base_page import BasePage


class ShoppingCarPage(BasePage):
    PATH = "/ecshop/flow.php"
    CHECKOUT_LINK = "a[href*='step=checkout']"
    SHIPPING_METHOD = "input[name='shipping']"
    PAYMENT_METHOD = "input[name='payment']"
    SUBMIT_ORDER_BUTTON = "input[src*='bnt_subOrder.gif']"

    def proceed_to_checkout(self) -> None:
        if self.sb.is_element_present(self.CHECKOUT_LINK):
            self.click(self.CHECKOUT_LINK)
            self.sb.sleep(1)

    def format_order(self) -> None:
        self.proceed_to_checkout()
        self.click(self.SHIPPING_METHOD)
        self.click(self.PAYMENT_METHOD)

    def submit_order(self) -> None:
        self.click(self.SUBMIT_ORDER_BUTTON)

    def assert_shopping_car_success(self) -> None:
        self.assert_url_contains("flow.php", message="【购物车断言失败】URL 不在结算流程中")
        self.assert_page_contains_any(
            "购物车",
            "配送",
            "支付方式",
            "商品列表",
            message="【购物车断言失败】页面缺少购物车/结算关键内容",
            check_url=False,
        )

    def assert_submit_order_success(self) -> None:
        self.assert_page_contains_any(
            "订单已提交成功",
            "请记住您的订单号",
            message="【订单提交成功断言失败】页面未出现成功提示",
        )
