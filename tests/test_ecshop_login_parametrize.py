from __future__ import annotations

from my_framework.assertions import assert_page_contains_any, assert_page_not_contains
from my_framework.yaml_parametrize import yaml_parametrize
from pages.login_page import LoginPage


@yaml_parametrize("case", "cases", data_file="data/scenarios/ecshop_login.yaml")
def test_login_by_yaml_case(sb, case: dict) -> None:
    """
    真实登录参数化测试链路：
    读取 YAML -> 生成用例 -> 执行登录 -> 用 expected 断言结果
    """
    login_page = LoginPage(sb)
    login_page.open()
    login_page.login(
        username=case["input"]["username"],
        password=case["input"]["password"],
    )

    expected = case["expected"]
    case_id = case.get("id", "unknown_case")

    if expected["result"] == "success":
        login_page.assert_login_success()
    else:
        assert_page_not_contains(
            sb,
            "欢迎您回来",
            "act=logout",
            message=f"【{case_id}】失败场景不应出现登录成功标识",
        )

    contains_any = expected.get("contains_any", [])
    if contains_any:
        assert_page_contains_any(
            sb,
            *contains_any,
            message=f"【{case_id}】页面内容与 YAML 预期不一致",
        )
