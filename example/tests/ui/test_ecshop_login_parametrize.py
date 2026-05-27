from __future__ import annotations

import pytest
import allure

from example.pages.login_page import LoginPage
from my_framework.ui.assertions import assert_page_contains_any, assert_page_not_contains
from my_framework.shared.yaml_parametrize import yaml_parametrize

PRIORITY_TO_SEVERITY = {
    "P0": allure.severity_level.BLOCKER,
    "P1": allure.severity_level.CRITICAL,
    "P2": allure.severity_level.NORMAL,
    "P3": allure.severity_level.MINOR,
}

@pytest.mark.demo
@pytest.mark.ui
@yaml_parametrize(
    "case",
    "cases",
    data_file="example/data/scenarios/ecshop_login.yaml",
    id_key="title",
)
def test_login_by_yaml_case(sb, case: dict) -> None:
    allure.dynamic.feature(f"UI-{'ECShop'}")
    allure.dynamic.story("ECShop 登录")
    allure.dynamic.tag("ui", "demo", "ecshop", "login", case.get("priority", "P2"))
    allure.dynamic.severity(PRIORITY_TO_SEVERITY.get(case.get("priority", "P2"), allure.severity_level.NORMAL))

    page = LoginPage(sb)
    page.open()

    user_input = case.get("input", {})
    expected = case.get("expected", {})

    page.login(user_input.get("username", ""), user_input.get("password", ""))

    contains_any = expected.get("contains_any", [])
    case_id = case.get("id", "unknown_case")
    result = expected.get("result")

    if result == "success":
        if contains_any:
            assert_page_contains_any(
                sb,
                *contains_any,
                message=f"【登录成功断言失败】Case={case_id}",
            )
        else:
            assert_page_contains_any(
                sb,
                "欢迎您回来",
                "act=logout",
                message=f"【登录成功断言失败】Case={case_id}",
            )
    else:
        assert_page_not_contains(
            sb,
            "欢迎您回来",
            "act=logout",
            message=f"【登录失败断言失败】Case={case_id}，页面出现成功标识",
        )
