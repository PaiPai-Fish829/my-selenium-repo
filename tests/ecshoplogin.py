from __future__ import annotations

from my_framework.base_test import BaseTest
from pages import LoginPage, SearchPage, ShoppingPage, ShoppingCarPage


class TestEcshopLogin(BaseTest):
    # 测试ecshop流程
    def test_search_product(self) -> None:
        """登录后搜索商品"""
        user_data = self.get_test_data("ecshop.default_user", {})
        search_data = self.get_test_data("ecshop.default_search", {})
        username = user_data.get("username", "test")
        password = user_data.get("password", "123456")
        keyword = search_data.get("keyword", "钻石")
        goods_id = search_data.get("goods_id", "141")

        # 1. 登录
        login_page = LoginPage(self)
        login_page.open()
        login_page.login(username, password)
        login_page.assert_login_success()


        self.sleep(5)
        # 2. 搜索（同一个浏览器，同一个 session）
        search_page = SearchPage(self)
        search_page.search(keyword)
        search_page.assert_search_success()

        # 3. 加入购物车
        shopping_page = ShoppingPage(self)
        shopping_page.click_product(goods_id)
        shopping_page.click_add_to_cart()
        shopping_page.assert_shopping_success()
        shopping_page.go_to_checkout()

        # 4. 结算并提交订单
        shopping_car_page = ShoppingCarPage(self)
        shopping_car_page.assert_shopping_car_success()
        shopping_car_page.format_order()
        shopping_car_page.submit_order()
        shopping_car_page.assert_submit_order_success()