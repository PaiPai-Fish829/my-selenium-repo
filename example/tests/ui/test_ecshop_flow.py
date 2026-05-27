from __future__ import annotations

import pytest

from example.pages import LoginPage, SearchPage, ShoppingPage, ShoppingCarPage
from my_framework.base_test import BaseTest


@pytest.mark.demo
@pytest.mark.ui
class TestEcshopFlow(BaseTest):
    def test_search_product(self) -> None:
        username = "test"
        password = "123456"
        keyword = "钻石"
        goods_id = "141"

        login_page = LoginPage(self)
        login_page.open()
        login_page.login(username, password)
        login_page.assert_login_success()

        search_page = SearchPage(self)
        search_page.search(keyword)
        search_page.assert_search_success()

        shopping_page = ShoppingPage(self)
        shopping_page.click_product(goods_id)
        shopping_page.click_add_to_cart()
        shopping_page.assert_shopping_success()
        shopping_page.go_to_checkout()

        shopping_car_page = ShoppingCarPage(self)
        shopping_car_page.assert_shopping_car_success()
        shopping_car_page.format_order()
        shopping_car_page.submit_order()
        shopping_car_page.assert_submit_order_success()
