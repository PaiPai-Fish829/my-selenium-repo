from __future__ import annotations

"""
HTTPBin Session(Cookie) 鉴权参数化示例。

本文件目标：
1) 演示会话型鉴权（Cookie）在 API 自动化中的两段式调用方式。
2) 演示如何把正向/负向 session 场景统一纳入 YAML 参数化管理。
3) 演示如何将 case 的类别和优先级映射到 Allure，便于测试报告管理。

文件结构说明：
- `_build_httpbin_client()`：构建 Cookie 场景客户端（关闭 token 自动鉴权，启用 cookie 会话）。
- `PRIORITY_TO_SEVERITY`：业务优先级到 Allure severity 的映射。
- `test_httpbin_cookie_session_auth()`：参数化主入口，负责写 cookie、验 cookie 与断言。

参数化数据约定（YAML）：
- 每个 case 通常包含：
  - `id/title/category/priority`：测试元信息。
  - `request`：写入 cookie 与验证 cookie 两次请求的参数。
  - `expected`：两次状态码断言 + cookie 存在性断言策略。
- 负向场景可通过 `assert_cookie_presence: false` 定义「cookie 不应存在」断言。

Allure 字段说明：
- 优先级定义（severity）：
  - P0 -> BLOCKER
  - P1 -> CRITICAL
  - P2 -> NORMAL
  - P3 -> MINOR
- 类型定义：
  - 建议以 `category` 代表业务类型（session-positive / session-negative 等）。
  - 通过 `feature=API-{category}` 与固定 `story` 形成稳定报表层级。
- 自定义字段：
  - 通过 `allure.dynamic.tag("api", "demo", "session-auth", category, priority)` 写入标签。
  - `category`、`priority` 作为可筛选自定义维度。
"""

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
    """构建 Session/Cookie 场景客户端。

    说明：
    - `enable_token_auth=False`：避免误将 token 注入到 Cookie 场景。
    - `enable_cookie_auth=True`：使用 `requests.Session` 持久化 cookie。
    - 此函数是可复用封装点，后续若要增加代理、超时、统一请求头可在此集中维护。
    """
    return ApiClient(
        base_url="https://httpbin.org",
        timeout=15,
        default_headers={
            "Accept": "application/json",
        },
        enable_token_auth=False,
        enable_cookie_auth=True,
    )


@pytest.mark.demo
@pytest.mark.api
@yaml_parametrize(
    "case",
    "cases",
    data_file="example/data/scenarios/httpbin_session_auth_demo.yaml",
)
def test_httpbin_cookie_session_auth(case: dict[str, Any]) -> None:
    """
    HTTPBin Session(Cookie) 鉴权参数化入口。

    执行流程：
    1) 读取 case 元信息并写入 Allure（title/feature/story/tag/severity）。
    2) 调用 set-cookie 接口写入会话信息。
    3) 调用 verify 接口读取当前会话 cookie。
    4) 按 `expected` 执行状态码断言。
    5) 根据 `assert_cookie_presence` 执行正向或负向 cookie 断言。

    关键参数说明：
    - `set_cookie_path`：写 cookie 的路径模板，支持 `{cookie_name}`/`{cookie_value}`。
    - `verify_path`：会话校验路径，默认 `/cookies`。
    - `assert_cookie_presence`：
      - true（默认）：断言 cookie 存在，且可结合 `json_contains` 进一步精确校验。
      - false：断言 cookie 不存在，常用于负向场景。
    """
    request_data = case.get("request", {})
    expected = case.get("expected", {})
    category = str(case.get("category", "session")).strip()
    priority = str(case.get("priority", "P2")).strip().upper()

    allure.dynamic.title(str(case.get("title", case.get("id", "httpbin_session_case"))))
    allure.dynamic.feature(f"API-{category}")
    allure.dynamic.story("HTTPBin Session/Cookie 鉴权参数化")
    allure.dynamic.tag("api", "demo", "session-auth", category, priority)
    allure.dynamic.severity(PRIORITY_TO_SEVERITY.get(priority, allure.severity_level.NORMAL))

    cookie_name = str(request_data.get("cookie_name", "")).strip()
    cookie_value = str(request_data.get("cookie_value", "")).strip()
    if not cookie_name or not cookie_value:
        raise AssertionError("cookie_name/cookie_value 不能为空")

    set_cookie_path = str(request_data.get("set_cookie_path", "/cookies/set/{cookie_name}/{cookie_value}"))
    verify_path = str(request_data.get("verify_path", "/cookies"))
    formatted_set_cookie_path = set_cookie_path.format(
        cookie_name=cookie_name,
        cookie_value=cookie_value,
    )

    client = _build_httpbin_client()
    try:
        set_cookie_response = client.request(
            method=str(request_data.get("set_cookie_method", "GET")),
            path=formatted_set_cookie_path,
            params=request_data.get("set_cookie_params"),
            use_auth=False,
            auth_mode="cookie",
        )
        verify_response = client.request(
            method=str(request_data.get("verify_method", "GET")),
            path=verify_path,
            params=request_data.get("verify_params"),
            use_auth=False,
            auth_mode="cookie",
        )
    finally:
        client.close()

    assert_status_code(
        set_cookie_response.status_code,
        int(expected.get("set_cookie_status_code", 200)),
        message=f"HTTPBin 设置会话 Cookie 失败: {case.get('id', 'unknown_case')}",
    )
    assert_status_code(
        verify_response.status_code,
        int(expected.get("verify_status_code", 200)),
        message=f"HTTPBin 会话 Cookie 校验失败: {case.get('id', 'unknown_case')}",
    )

    payload = verify_response.json()
    should_exist = bool(expected.get("assert_cookie_presence", True))
    if should_exist:
        expected_json_contains = expected.get(
            "json_contains",
            {"cookies": {cookie_name: cookie_value}},
        )
        assert_json_contains(
            payload,
            expected_json_contains,
            message=f"HTTPBin Session JSON 断言失败: {case.get('id', 'unknown_case')}",
        )
    else:
        cookies = payload.get("cookies", {})
        assert cookie_name not in cookies, (
            f"HTTPBin Session 负向断言失败: {cookie_name} 不应存在, "
            f"当前 cookies={cookies}"
        )
