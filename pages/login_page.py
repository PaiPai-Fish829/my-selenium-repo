from __future__ import annotations

from pages.base_page import BasePage


class LoginPage(BasePage):
    """ECShop 登录页对象。"""

    PATH = "/ecshop/user.php"
    USERNAME_INPUT = "input[name='username'], #username"
    PASSWORD_INPUT = "input[name='password'], #password"
    SUBMIT_BUTTON = "input[name='submit'], button[type='submit']"
    SUCCESS_BANNER = "#flash.success"

    def open(self) -> None:
        self.open_path(self.PATH)

    def login(self, username: str, password: str) -> None:
        self.type(self.USERNAME_INPUT, username)
        self.type(self.PASSWORD_INPUT, password)
        self.click(self.SUBMIT_BUTTON)

    def assert_login_success(self) -> None:
        """兼容 ECShop / Heroku 示例站的登录成功断言。"""
        if self.sb.is_element_present(self.SUCCESS_BANNER):
            self.sb.assert_text("You logged into a secure area!", self.SUCCESS_BANNER)
            return

        self.assert_page_contains_any(
            "登录成功",
            message="【登录成功断言失败】未检测到登录成功标识",
        )

    def assert_login_failed(self, expected_error: str = "Your username is invalid!"):
        """断言登录失败并显示特定错误信息。"""
        self.sb.assert_text(expected_error, "#flash.error")
        self.sb.assert_element("#flash.error")
