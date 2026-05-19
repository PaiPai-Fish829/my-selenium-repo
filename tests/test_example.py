from __future__ import annotations

from my_framework.base_test import BaseTest
from pages.login_page import LoginPage


class TestExample(BaseTest):
    def test_visit_cloudflare_protected_site(self) -> None:
        """
        示例：访问带防检测机制的网站。
        运行时请加 --uc（undetected-chromedriver）：
        pytest tests/test_example.py -k cloudflare --uc
        """
        target_url = self.get_test_data(
            "anti_bot.target_url", "https://www.nowsecure.nl/"
        )
        self.uc_open_with_reconnect(target_url, reconnect_time=6)
        title = self.get_page_title().lower()
        self.assert_true(
            "nowsecure" in title,
            f"【防检测访问断言失败】页面标题未包含 nowsecure，当前标题: {title}",
        )

    def test_login_flow_with_page_object(self) -> None:
        login_data = self.get_test_data("login.valid_user", {})
        username = login_data.get("username", "tomsmith")
        password = login_data.get("password", "SuperSecretPassword!")

        login_page = LoginPage(self)
        login_page.open()
        login_page.login(username=username, password=password)
        login_page.assert_login_success()
