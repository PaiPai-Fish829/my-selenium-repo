from __future__ import annotations

"""
HTTPBin Token 鉴权参数化示例。

本文件目标：
1) 演示如何使用 `ApiClient` 发送 Bearer Token 相关请求。
2) 演示如何通过 `yaml_parametrize` 把 YAML 场景映射为 pytest 参数化用例。
3) 演示如何把业务侧的「优先级」「类型」映射到 Allure 字段，便于报告筛选与分层查看。

文件结构说明：
- `_build_httpbin_client()`：统一构建 API 客户端，避免每个 case 重复初始化逻辑。
- `PRIORITY_TO_SEVERITY`：把业务优先级 P0~P3 映射到 Allure severity。
- `test_httpbin_bearer_token_auth()`：参数化主测试函数，读取 case 并执行请求、断言、报告打标。

参数化数据约定（YAML）：
- 顶层：`cases` 列表。
- 每个 case 建议字段：
  - `id`：用例唯一标识（用于 pytest 参数化 id）。
  - `title`：报告展示标题。
  - `category`：业务类别（例如 auth-positive / auth-negative / error-code）。
  - `priority`：业务优先级（P0/P1/P2/P3）。
  - `request`：请求参数（method/path/use_auth/auth_mode/auth_token/...）。
  - `expected`：断言参数（status_code/json_contains）。

Allure 字段说明：
- 优先级定义（severity）：
  - P0 -> BLOCKER（核心链路阻断）
  - P1 -> CRITICAL（关键功能不可用）
  - P2 -> NORMAL（一般功能问题）
  - P3 -> MINOR（低风险问题）
- 类型定义（本文件建议）：
  - 通过 `category` 表示业务类型，例如鉴权正向、鉴权负向、错误码场景等。
  - 通过 `feature=API-{category}`、`story=HTTPBin Token 鉴权参数化` 分层展示。
- 自定义字段：
  - 使用 `allure.dynamic.tag("api", "demo", "token-auth", category, priority)` 添加标签。
  - `category`、`priority` 即为自定义业务维度，可在 Allure 中按 tag 过滤。
"""

from typing import Any

import allure
import pytest

from my_framework.api.client import ApiClient
from my_framework.api.assertions import assert_json_contains, assert_status_code
from my_framework.shared.yaml_parametrize import yaml_parametrize

PRIORITY_TO_SEVERITY = {
    "P0": allure.severity_level.BLOCKER,
    "P1": allure.severity_level.CRITICAL,
    "P2": allure.severity_level.NORMAL,
    "P3": allure.severity_level.MINOR,
}


def _build_httpbin_client() -> ApiClient:
    """构建 Token 场景通用客户端。

    说明：
    - `enable_token_auth=True`：允许 `use_auth=True` 时自动注入 Bearer Token。
    - `enable_cookie_auth=True`：保持开启，便于同一客户端兼容需要会话能力的扩展场景。
    - 如需切换目标环境，可把 `base_url` 改成配置读取模式（例如 `ApiClient.from_config()`）。
    """
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
    HTTPBin Token 鉴权参数化入口。

    执行流程：
    1) 从 YAML case 读取请求与期望。
    2) 读取 `category/priority` 并写入 Allure 的 feature/tag/severity。
    3) 若 case 提供 `auth_token`，通过 `client.set_auth_token()` 注入。
    4) 调用 `client.request()` 发送请求。
    5) 对状态码和可选 JSON 字段做断言。

    关键参数说明：
    - `use_auth`：是否启用客户端鉴权注入。
    - `auth_mode`：鉴权模式（token/cookie/both），当前文件主要使用 token。
    - `json_contains`：若提供，则执行结构化包含断言，适合做关键字段校验。
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
