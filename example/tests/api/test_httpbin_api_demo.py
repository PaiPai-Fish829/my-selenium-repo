from __future__ import annotations

from typing import Any

import allure
import pytest

from my_framework.api_client import ApiClient
from my_framework.assertions_api import assert_json_contains, assert_status_code
from my_framework.yaml_parametrize import yaml_parametrize

PRIORITY_TO_SEVERITY = {
    "P0": allure.severity_level.BLOCKER,
    "P1": allure.severity_level.CRITICAL,
    "P2": allure.severity_level.NORMAL,
    "P3": allure.severity_level.MINOR,
}


def _build_httpbin_client() -> ApiClient:
    return ApiClient(
        base_url="https://httpbin.org",
        timeout=15,
        default_headers={
            "Accept": "application/json",
        },
        enable_token_auth=True,
        enable_cookie_auth=True,
    )


@pytest.mark.demo
@pytest.mark.api
@yaml_parametrize(
    "case",
    "cases",
    data_file="example/data/scenarios/httpbin_token_auth_demo.yaml",
)
def test_httpbin_bearer_token_auth(case: dict[str, Any]) -> None:
    """
    HTTPBin Token 鉴权演示（参数化）：
    - 无 Token 调 /bearer -> 401
    - 带 Bearer Token 调 /bearer -> 200
    """
    request_data = case.get("request", {})
    expected = case.get("expected", {})
    category = str(case.get("category", "auth")).strip()
    priority = str(case.get("priority", "P2")).strip().upper()

    allure.dynamic.title(str(case.get("title", case.get("id", "httpbin_token_case"))))
    allure.dynamic.feature(f"API-{category}")
    allure.dynamic.story("HTTPBin Token 鉴权参数化")
    allure.dynamic.tag("api", "demo", "token-auth", category, priority)
    allure.dynamic.severity(PRIORITY_TO_SEVERITY.get(priority, allure.severity_level.NORMAL))

    client = _build_httpbin_client()
    auth_token = str(request_data.get("auth_token", "")).strip()
    if auth_token:
        client.set_auth_token(auth_token)

    try:
        response = client.request(
            method=str(request_data.get("method", "GET")),
            path=str(request_data.get("path", "/bearer")),
            params=request_data.get("params"),
            headers=request_data.get("headers"),
            use_auth=bool(request_data.get("use_auth", False)),
            auth_mode=str(request_data.get("auth_mode", "token")),
        )
    finally:
        client.close()

    assert_status_code(
        response.status_code,
        int(expected.get("status_code", 200)),
        message=f"HTTPBin Token 鉴权用例失败: {case.get('id', 'unknown_case')}",
    )

    json_contains = expected.get("json_contains")
    if json_contains:
        payload = response.json()
        assert_json_contains(
            payload,
            json_contains,
            message=f"HTTPBin Token JSON 断言失败: {case.get('id', 'unknown_case')}",
        )
