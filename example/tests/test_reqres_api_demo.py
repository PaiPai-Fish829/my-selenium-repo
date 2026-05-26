from __future__ import annotations

import os
from typing import Any

import pytest

from my_framework.api_client import ApiClient
from my_framework.assertions_api import assert_status_code
from my_framework.yaml_parametrize import yaml_parametrize


def _build_reqres_client() -> ApiClient:
    return ApiClient(
        base_url="https://reqres.in",
        timeout=15,
        default_headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        # ReqRes 演示场景下不依赖 Bearer Token，由测试按需显式传 Header。
        enable_token_auth=False,
        enable_cookie_auth=True,
    )


@pytest.mark.demo
@pytest.mark.api
@yaml_parametrize(
    "case",
    "cases",
    data_file="example/data/scenarios/reqres_products.yaml",
)
def test_reqres_products_api(case: dict[str, Any]) -> None:
    """
    ReqRes products records 演示：
    - case1: 无鉴权 -> 401
    - case2: x-api-key + X-Reqres-Env -> 200
    """
    request_data = case.get("request", {})
    expected = case.get("expected", {})

    headers = dict(request_data.get("headers", {}) or {})
    if request_data.get("use_api_key_header"):
        api_key = os.getenv("REQRES_API_KEY", "").strip()
        if not api_key:
            pytest.skip("缺少 REQRES_API_KEY，跳过需要 x-api-key 的演示用例")
        headers["x-api-key"] = api_key

    client = _build_reqres_client()
    try:
        response = client.request(
            method=str(request_data.get("method", "GET")),
            path=str(request_data.get("path", "/")),
            params=request_data.get("params"),
            headers=headers,
            use_auth=bool(request_data.get("use_auth", False)),
            auth_mode=str(request_data.get("auth_mode", "token")),
        )
    finally:
        client.close()

    assert_status_code(
        response.status_code,
        int(expected.get("status_code", 200)),
        message=f"ReqRes 演示用例失败: {case.get('id', 'unknown_case')}",
    )

    required_keys = expected.get("require_json_keys", [])
    if required_keys:
        payload = response.json()
        for key in required_keys:
            assert key in payload, f"响应缺少关键字段: {key}"
