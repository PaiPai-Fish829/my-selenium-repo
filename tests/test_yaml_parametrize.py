from __future__ import annotations

from my_framework.yaml_parametrize import yaml_parametrize


@yaml_parametrize("case", "cases", data_file="data/scenarios/ecshop_login.yaml")
def test_yaml_parametrize_login_cases(case: dict) -> None:
    """
    验证 YAML 参数化是否生效：
    - 每条 case 会被单独展开成一个测试用例
    - case 结构包含 input / expected 字段
    """
    assert "title" in case
    assert "input" in case
    assert "expected" in case

    assert "username" in case["input"]
    assert "password" in case["input"]
    assert case["expected"]["result"] in {"success", "fail"}
