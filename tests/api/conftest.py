from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

import pytest

from my_framework.api_client import ApiClient
from my_framework.allure_utils import attach_json, attach_text
from my_framework.base_api_test import BaseApiTest

LOGGER = logging.getLogger("tests.api")
_ACTIVE_API_CLIENT_KEY = "_active_api_client"


def _normalize_yaml_markers(markers: Any) -> list[str]:
    if isinstance(markers, str):
        return [markers.strip()] if markers.strip() else []
    if isinstance(markers, Iterable):
        result: list[str] = []
        for marker in markers:
            if isinstance(marker, str) and marker.strip():
                result.append(marker.strip())
        return result
    return []


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "api: 标识 API 测试")
    config.addinivalue_line("markers", "need_auth: 当前用例需要 Token 鉴权")
    config.addinivalue_line("markers", "need_cookies: 当前用例需要 Cookie 登录态")
    config.addinivalue_line("markers", "slow: 标记慢速 API 用例")
    config.addinivalue_line(
        "markers",
        "dependency(depends=[...]): 用例依赖关系（建议配合 pytest-dependency 插件）",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        callspec = getattr(item, "callspec", None)
        if callspec:
            for param in callspec.params.values():
                if isinstance(param, dict):
                    for marker_name in _normalize_yaml_markers(param.get("markers", [])):
                        item.add_marker(getattr(pytest.mark, marker_name))

        if item.get_closest_marker("need_auth"):
            item.add_marker(pytest.mark.usefixtures("authenticated_api_client"))
        if item.get_closest_marker("need_cookies"):
            item.add_marker(pytest.mark.usefixtures("api_session_with_cookies"))
        if item.get_closest_marker("api"):
            item.add_marker(pytest.mark.usefixtures("api_request_log"))


@pytest.fixture(scope="session")
def api_settings() -> dict[str, Any]:
    return ApiClient.read_api_runtime_settings()


@pytest.fixture(scope="function")
def api_client(request: pytest.FixtureRequest) -> ApiClient:
    client = ApiClient.from_config()
    setattr(request.node, _ACTIVE_API_CLIENT_KEY, client)
    yield client
    client.close()


@pytest.fixture(scope="session")
def auth_token() -> str:
    return BaseApiTest.get_token(force_refresh=False)


@pytest.fixture(scope="function")
def authenticated_api_client(request: pytest.FixtureRequest) -> ApiClient:
    client = ApiClient.from_config()
    token = BaseApiTest.get_token(force_refresh=False)
    client.configure_auth(token=token, enable_token_auth=True)
    setattr(request.node, _ACTIVE_API_CLIENT_KEY, client)
    yield client
    client.close()


@pytest.fixture(scope="function")
def api_session_with_cookies(request: pytest.FixtureRequest) -> ApiClient:
    client = ApiClient.from_config()
    BaseApiTest.login_and_get_session(client=client)
    client.configure_auth(enable_cookie_auth=True)
    setattr(request.node, _ACTIVE_API_CLIENT_KEY, client)
    yield client
    client.close()


@pytest.fixture(autouse=True, scope="function")
def api_request_log(request: pytest.FixtureRequest) -> None:
    yield

    node = request.node
    if not node.get_closest_marker("api"):
        return

    client = getattr(node, _ACTIVE_API_CLIENT_KEY, None)
    if not isinstance(client, ApiClient):
        return

    last_request = client.get_last_request()
    last_response = client.get_last_response()
    if last_request:
        LOGGER.info("API Request: %s", last_request)
        attach_json("api-last-request", last_request)
    if last_response:
        LOGGER.info("API Response: %s", last_response)
        attach_json("api-last-response", last_response)

    rep_call = getattr(node, "rep_call", None)
    if rep_call is not None and rep_call.failed:
        LOGGER.error("API test failed: %s", node.nodeid)
        LOGGER.error("Failure request details: %s", last_request)
        LOGGER.error("Failure response details: %s", last_response)
        attach_text("api-failure-nodeid", node.nodeid)
