from __future__ import annotations

import os
from typing import Any

import pytest

from my_framework.api_client import ApiClient
from my_framework.assertions_api import assert_status_code


def _build_reqres_client() -> ApiClient:
    return ApiClient(
        base_url="https://reqres.in",
        timeout=20,
        default_headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Reqres-Env": "prod",
        },
        # Bearer 场景使用 ApiClient 的 Token 鉴权能力。
        enable_token_auth=True,
        enable_cookie_auth=True,
    )


def _exchange_code_for_session_token(client: ApiClient) -> str:
    """
    通过 ReqRes 登录验证码换取 Session Token。

    需要提前设置：
    - REQRES_LOGIN_EMAIL
    - REQRES_LOGIN_CODE
    """
    email = os.getenv("REQRES_LOGIN_EMAIL", "").strip()
    code = os.getenv("REQRES_LOGIN_CODE", "").strip()
    if not email or not code:
        pytest.skip("缺少 REQRES_LOGIN_EMAIL 或 REQRES_LOGIN_CODE，跳过验证码换 token 场景")

    response = client.post(
        "/api/app-users/verify",
        json={"email": email, "code": code},
        use_auth=False,
        auth_mode="cookie",
    )
    assert_status_code(response.status_code, 200, "验证码换 Session Token 失败")
    payload: dict[str, Any] = response.json()

    session_token = str(payload.get("session_token", "")).strip()
    if not session_token:
        session_token = str(payload.get("token", "")).strip()
    if not session_token:
        raise AssertionError("verify 接口响应中未找到 session_token/token")
    return session_token


@pytest.mark.demo
@pytest.mark.api
def test_reqres_products_with_bearer_from_env() -> None:
    """
    演示1：直接使用 REQRES_SESSION_TOKEN 访问受保护接口。
    """
    session_token = os.getenv("REQRES_SESSION_TOKEN", "").strip()
    if not session_token:
        pytest.skip("缺少 REQRES_SESSION_TOKEN，跳过 Bearer 演示用例")

    client = _build_reqres_client()
    client.set_auth_token(session_token)
    try:
        response = client.get(
            "/api/collections/products/records",
            params={"project_id": "24993"},
            use_auth=True,
            auth_mode="token",
        )
    finally:
        client.close()

    assert_status_code(response.status_code, 200, "Bearer Token 请求 products records 失败")
    payload = response.json()
    assert "records" in payload, "响应中缺少 records 字段"


@pytest.mark.demo
@pytest.mark.api
def test_reqres_exchange_code_then_access_products() -> None:
    """
    演示2：验证码换 Session Token，再带 Bearer 调业务接口。
    """
    client = _build_reqres_client()
    try:
        session_token = _exchange_code_for_session_token(client)
        client.set_auth_token(session_token)
        response = client.get(
            "/api/collections/products/records",
            params={"project_id": "24993"},
            use_auth=True,
            auth_mode="token",
        )
    finally:
        client.close()

    assert_status_code(response.status_code, 200, "换 token 后访问 products records 失败")
    payload = response.json()
    assert "records" in payload, "响应中缺少 records 字段"
