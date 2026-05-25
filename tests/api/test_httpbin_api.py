from __future__ import annotations

import pytest

from my_framework.assertions_api import assert_json_contains, assert_status_code
from my_framework.yaml_parametrize import yaml_parametrize


@pytest.mark.api
@yaml_parametrize("case", "cases", data_file="data/scenarios/api/httpbin_smoke.yaml")
def test_httpbin_case(api_client, case: dict) -> None:
    request_data = case["request"]
    expected = case["expected"]

    response = api_client.request(
        method=request_data.get("method", "GET"),
        path=request_data.get("path", "/"),
        params=request_data.get("params"),
        headers=request_data.get("headers"),
        json=request_data.get("json"),
        data=request_data.get("data"),
    )

    assert_status_code(
        response.status_code,
        int(expected.get("status_code", 200)),
        message=f"【接口用例失败】{case.get('title', case.get('id', 'unknown'))}",
    )

    if "json_contains" in expected:
        payload = response.json()
        assert_json_contains(
            payload,
            expected["json_contains"],
            message=f"【接口用例失败】JSON 断言失败: {case.get('id', 'unknown')}",
        )
