from __future__ import annotations

import copy
import json as jsonlib
import os
from pathlib import Path
from time import time
from typing import Any, Iterable, Mapping

import requests

from my_framework.shared.config_utils import PROJECT_ROOT, load_yaml, read_by_path

DEFAULT_SENSITIVE_FIELDS = {
    "password",
    "token",
    "authorization",
    "secret",
    "api_key",
}


class ApiClient:
    """
    封装目的:
    - 统一 API 调用入口，屏蔽 requests 的重复样板代码。
    - 在框架层提供鉴权、日志脱敏、请求追踪等测试所需能力。

    封装实现:
    - 基于 requests.Session 实现连接复用和可选 Cookie 会话。
    - 通过配置中心读取环境参数，构建基础 URL、超时和默认请求头。
    - 在 request 主流程中记录最近一次请求/响应并执行敏感字段脱敏。

    外部接口:
    - 构造函数支持 base_url、timeout、headers、auth 和脱敏字段定制。
    - 提供 from_config/read_api_runtime_settings 快速初始化能力。
    - 提供 request/get/post/put/patch/delete 与调试辅助接口。
    """
    def __init__(
        self,
        base_url: str,
        *,
        timeout: int = 10,
        default_headers: Mapping[str, str] | None = None,
        session: requests.Session | None = None,
        auth_token: str | None = None,
        enable_token_auth: bool = True,
        enable_cookie_auth: bool = True,
        sensitive_fields: Iterable[str] | None = None,
    ) -> None:
        """
        封装目的:
        - 初始化 API 客户端运行状态，建立后续请求所需上下文。

        封装实现:
        - 标准化 base_url 并初始化 requests.Session。
        - 合并默认请求头，设置 Token/Cookie 鉴权开关。
        - 构建脱敏字段集合并准备请求追踪缓存。

        外部接口:
        - 入参: 基础地址、超时、默认头、Session、鉴权参数及脱敏字段。
        - 出参: 无显式返回，实例化完成后可直接发起请求。
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        if default_headers:
            self.session.headers.update(dict(default_headers))

        self.auth_token = auth_token or os.getenv("API_TOKEN")
        self.enable_token_auth = enable_token_auth
        self.enable_cookie_auth = enable_cookie_auth
        self.sensitive_fields = {
            field.lower()
            for field in (set(sensitive_fields) if sensitive_fields else DEFAULT_SENSITIVE_FIELDS)
        }

        self._last_request: dict[str, Any] | None = None
        self._last_response: dict[str, Any] | None = None

    @classmethod
    def from_config(
        cls,
        *,
        config_path: str | Path | None = None,
        env_name: str | None = None,
        auth_token: str | None = None,
        sensitive_fields: Iterable[str] | None = None,
    ) -> "ApiClient":
        """
        封装目的:
        - 通过配置文件与环境变量快速创建可用客户端，减少测试样板代码。

        封装实现:
        - 调用 read_api_runtime_settings 解析配置。
        - 按显式参数 > 配置 > 环境变量优先级解析 Token。
        - 返回带完整运行参数的 ApiClient 实例。

        外部接口:
        - 入参: 可选配置文件路径、环境名、Token、脱敏字段。
        - 出参: ApiClient 实例。
        """
        settings = cls.read_api_runtime_settings(config_path=config_path, env_name=env_name)
        token = auth_token or settings["token"] or os.getenv(settings["token_env"]) or os.getenv("API_TOKEN")
        return cls(
            base_url=str(settings["base_url"]),
            timeout=int(settings["timeout"]),
            default_headers=settings["default_headers"],
            auth_token=token,
            enable_token_auth=bool(settings["enable_token_auth"]),
            enable_cookie_auth=bool(settings["enable_cookie_auth"]),
            sensitive_fields=sensitive_fields or settings["sensitive_fields"],
        )

    @classmethod
    def read_api_runtime_settings(
        cls,
        *,
        config_path: str | Path | None = None,
        env_name: str | None = None,
    ) -> dict[str, Any]:
        """
        封装目的:
        - 统一读取并归并 API 运行配置，避免调用方重复处理多层配置结构。

        封装实现:
        - 解析全局 api 节点与 environments 下环境专属节点。
        - 以分层兜底策略提取 base_url、timeout、auth 和 headers。
        - 标准化输出字段，保证上层调用读取稳定。

        外部接口:
        - 入参: 可选配置路径、环境名称。
        - 出参: 运行配置字典（含 base_url/timeout/auth/token 等字段）。
        """
        config_file = Path(config_path) if config_path else PROJECT_ROOT / "config.yaml"
        config = load_yaml(config_file)
        selected_env = env_name or os.getenv("TEST_ENV", "default")

        api_node = read_by_path(config, "api", {}) or {}
        env_node = read_by_path(config, f"environments.{selected_env}", {}) or {}
        env_api_node = read_by_path(config, f"environments.{selected_env}.api", {}) or {}

        auth_node = (
            read_by_path(env_node, "api_auth", None)
            or read_by_path(env_node, "auth", None)
            or read_by_path(env_api_node, "auth", None)
            or read_by_path(api_node, "auth", {})
            or {}
        )

        base_url = (
            read_by_path(env_api_node, "base_url", None)
            or read_by_path(env_node, "api_base_url", None)
            or read_by_path(api_node, "base_url", None)
            or read_by_path(config, "api_base_url", None)
            or "https://httpbin.org"
        )
        timeout = (
            read_by_path(env_api_node, "timeout", None)
            or read_by_path(env_node, "api_timeout", None)
            or read_by_path(api_node, "timeout", None)
            or 10
        )
        default_headers = read_by_path(api_node, "headers", {}) or {}

        configured_sensitive = read_by_path(api_node, "sensitive_fields", None)
        if isinstance(configured_sensitive, list) and configured_sensitive:
            sensitive_fields = [str(field) for field in configured_sensitive]
        else:
            sensitive_fields = list(DEFAULT_SENSITIVE_FIELDS)

        return {
            "base_url": str(base_url),
            "timeout": int(timeout),
            "default_headers": dict(default_headers) if isinstance(default_headers, Mapping) else {},
            "auth": auth_node if isinstance(auth_node, Mapping) else {},
            "token": read_by_path(auth_node, "token", None),
            "token_env": str(read_by_path(auth_node, "token_env", "API_TOKEN")),
            "enable_token_auth": bool(read_by_path(auth_node, "enable_token_auth", True)),
            "enable_cookie_auth": bool(read_by_path(auth_node, "enable_cookie_auth", True)),
            "sensitive_fields": sensitive_fields,
        }

    def close(self) -> None:
        """
        封装目的:
        - 显式释放底层 Session 资源。

        封装实现:
        - 调用 requests.Session.close() 关闭连接池。

        外部接口:
        - 入参: 无。
        - 出参: 无。
        """
        self.session.close()

    def set_auth_token(self, token: str | None) -> None:
        """
        封装目的:
        - 在运行时更新 Bearer Token，支持动态鉴权切换。

        封装实现:
        - 直接替换实例内保存的 auth_token。

        外部接口:
        - 入参: token，可传 None 清空。
        - 出参: 无。
        """
        self.auth_token = token

    def configure_auth(
        self,
        *,
        token: str | None = None,
        enable_token_auth: bool | None = None,
        enable_cookie_auth: bool | None = None,
    ) -> None:
        """
        封装目的:
        - 统一修改客户端鉴权策略，避免分散修改实例属性。

        封装实现:
        - 根据非 None 参数分别更新 token、token 鉴权开关、cookie 鉴权开关。

        外部接口:
        - 入参: token、enable_token_auth、enable_cookie_auth（均可选）。
        - 出参: 无。
        """
        if token is not None:
            self.auth_token = token
        if enable_token_auth is not None:
            self.enable_token_auth = enable_token_auth
        if enable_cookie_auth is not None:
            self.enable_cookie_auth = enable_cookie_auth

    def _build_url(self, path: str) -> str:
        """
        封装目的:
        - 将相对路径与 base_url 统一拼装为最终请求地址。

        封装实现:
        - 已是绝对 URL 时直接返回。
        - 相对路径自动补齐前导斜杠并拼接 base_url。

        外部接口:
        - 入参: path，请求路径或完整 URL。
        - 出参: 可直接请求的完整 URL 字符串。
        """
        if path.startswith("http://") or path.startswith("https://"):
            return path
        normalized = path if path.startswith("/") else f"/{path}"
        return f"{self.base_url}{normalized}"

    def _build_headers(
        self,
        headers: Mapping[str, str] | None,
        *,
        use_auth: bool,
        use_token_auth: bool,
    ) -> dict[str, str]:
        """
        封装目的:
        - 统一构建请求头，集中处理默认头合并与 Token 注入逻辑。

        封装实现:
        - 以 Session 头为基准合并调用方传入头。
        - 当允许鉴权且未显式传 Authorization 时自动注入 Bearer Token。

        外部接口:
        - 入参: headers、use_auth、use_token_auth。
        - 出参: 合并后的请求头字典。
        """
        merged = dict(self.session.headers)
        if headers:
            merged.update(dict(headers))
        if use_auth and use_token_auth and self.auth_token and "Authorization" not in merged:
            merged["Authorization"] = f"Bearer {self.auth_token}"
        return merged

    def request(
        self,
        method: str,
        url: str | None = None,
        *,
        path: str | None = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        json: Any | None = None,
        data: Any | None = None,
        timeout: int | None = None,
        use_auth: bool = True,
        auth_mode: str = "token",
    ) -> requests.Response:
        """
        封装目的:
        - 提供统一底层请求执行入口，承载鉴权、超时、追踪和响应采集。

        封装实现:
        - 解析 url/path、鉴权模式和最终请求头。
        - 在发送前记录脱敏后的请求快照，发送后记录响应快照。
        - 按 auth_mode 决定使用 Session（Cookie）或 requests（无会话）发送。

        外部接口:
        - 入参: method、url/path、params/json/data/headers/timeout 等。
        - 出参: requests.Response。
        - 异常: 缺少 url/path 时抛 ValueError，请求异常由 requests 抛出。
        """
        target = url if url is not None else path
        if not target:
            raise ValueError("request() 需要提供 url 或 path")
        final_url = self._build_url(target)
        resolved_timeout = timeout if timeout is not None else self.timeout
        normalized_auth_mode = auth_mode.lower().strip()
        use_token_auth = normalized_auth_mode in {"token", "both"}
        use_cookie_auth = normalized_auth_mode in {"cookie", "both"}
        if normalized_auth_mode not in {"token", "cookie", "both"}:
            use_token_auth = True
            use_cookie_auth = False

        request_headers = self._build_headers(
            headers,
            use_auth=use_auth and self.enable_token_auth,
            use_token_auth=use_token_auth,
        )

        self._last_request = self._sanitize(
            {
                "method": method.upper(),
                "url": final_url,
                "params": dict(params) if isinstance(params, Mapping) else params,
                "headers": request_headers,
                "json": json,
                "data": data,
                "timeout": resolved_timeout,
                "use_auth": use_auth,
                "auth_mode": normalized_auth_mode,
                "cookie_count": len(self.session.cookies),
            }
        )

        sender = self.session if (use_cookie_auth and self.enable_cookie_auth) else requests
        started_at = time()
        response = sender.request(
            method=method.upper(),
            url=final_url,
            params=params,
            headers=request_headers,
            json=json,
            data=data,
            timeout=resolved_timeout,
        )
        elapsed_ms = int((time() - started_at) * 1000)

        self._last_response = self._sanitize(
            {
                "status_code": response.status_code,
                "reason": response.reason,
                "url": response.url,
                "elapsed_ms": elapsed_ms,
                "headers": dict(response.headers),
                "cookies": response.cookies.get_dict(),
                "body": self._response_payload(response),
            }
        )
        return response

    def get(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: int | None = None,
        use_auth: bool = True,
        auth_mode: str = "token",
    ) -> requests.Response:
        """
        封装目的:
        - 提供 GET 语义化快捷接口，减少重复 method 传参。

        封装实现:
        - 内部转调 request("GET", ...)。

        外部接口:
        - 入参: url、params、headers、timeout、鉴权参数。
        - 出参: requests.Response。
        """
        return self.request(
            "GET",
            url,
            params=params,
            headers=headers,
            timeout=timeout,
            use_auth=use_auth,
            auth_mode=auth_mode,
        )

    def post(
        self,
        url: str,
        *,
        json: Any | None = None,
        data: Any | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: int | None = None,
        use_auth: bool = True,
        auth_mode: str = "token",
    ) -> requests.Response:
        """
        封装目的:
        - 提供 POST 语义化快捷接口。

        封装实现:
        - 内部转调 request("POST", ...)，透传 json/data 等参数。

        外部接口:
        - 入参: url、json/data、headers、timeout、鉴权参数。
        - 出参: requests.Response。
        """
        return self.request(
            "POST",
            url,
            json=json,
            data=data,
            headers=headers,
            timeout=timeout,
            use_auth=use_auth,
            auth_mode=auth_mode,
        )

    def put(
        self,
        url: str,
        *,
        json: Any | None = None,
        data: Any | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: int | None = None,
        use_auth: bool = True,
        auth_mode: str = "token",
    ) -> requests.Response:
        """
        封装目的:
        - 提供 PUT 语义化快捷接口。

        封装实现:
        - 内部转调 request("PUT", ...)，透传更新请求参数。

        外部接口:
        - 入参: url、json/data、headers、timeout、鉴权参数。
        - 出参: requests.Response。
        """
        return self.request(
            "PUT",
            url,
            json=json,
            data=data,
            headers=headers,
            timeout=timeout,
            use_auth=use_auth,
            auth_mode=auth_mode,
        )

    def patch(
        self,
        url: str,
        *,
        json: Any | None = None,
        data: Any | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: int | None = None,
        use_auth: bool = True,
        auth_mode: str = "token",
    ) -> requests.Response:
        """
        封装目的:
        - 提供 PATCH 语义化快捷接口。

        封装实现:
        - 内部转调 request("PATCH", ...)，透传局部更新参数。

        外部接口:
        - 入参: url、json/data、headers、timeout、鉴权参数。
        - 出参: requests.Response。
        """
        return self.request(
            "PATCH",
            url,
            json=json,
            data=data,
            headers=headers,
            timeout=timeout,
            use_auth=use_auth,
            auth_mode=auth_mode,
        )

    def delete(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: int | None = None,
        use_auth: bool = True,
        auth_mode: str = "token",
    ) -> requests.Response:
        """
        封装目的:
        - 提供 DELETE 语义化快捷接口。

        封装实现:
        - 内部转调 request("DELETE", ...)，透传查询及鉴权参数。

        外部接口:
        - 入参: url、params、headers、timeout、鉴权参数。
        - 出参: requests.Response。
        """
        return self.request(
            "DELETE",
            url,
            params=params,
            headers=headers,
            timeout=timeout,
            use_auth=use_auth,
            auth_mode=auth_mode,
        )

    def get_last_request(self) -> dict[str, Any] | None:
        """
        封装目的:
        - 暴露最近一次请求快照，便于调试和断言。

        封装实现:
        - 返回内部缓存的深拷贝，避免外部修改原始数据。

        外部接口:
        - 入参: 无。
        - 出参: 脱敏后的请求快照或 None。
        """
        return copy.deepcopy(self._last_request)

    def get_last_response(self) -> dict[str, Any] | None:
        """
        封装目的:
        - 暴露最近一次响应快照，便于排障与报告输出。

        封装实现:
        - 返回内部缓存响应数据的深拷贝。

        外部接口:
        - 入参: 无。
        - 出参: 脱敏后的响应快照或 None。
        """
        return copy.deepcopy(self._last_response)

    def _sanitize(self, payload: Any) -> Any:
        """
        封装目的:
        - 对日志/快照中的敏感字段做统一脱敏，避免泄露凭证。

        封装实现:
        - 递归遍历 Mapping、list、tuple。
        - 命中 sensitive_fields 的键统一替换为 ***REDACTED***。

        外部接口:
        - 入参: 任意层级 payload。
        - 出参: 脱敏后的结构化数据。
        """
        if isinstance(payload, Mapping):
            sanitized: dict[str, Any] = {}
            for key, value in payload.items():
                key_text = str(key)
                if key_text.lower() in self.sensitive_fields:
                    sanitized[key_text] = "***REDACTED***"
                else:
                    sanitized[key_text] = self._sanitize(value)
            return sanitized
        if isinstance(payload, list):
            return [self._sanitize(item) for item in payload]
        if isinstance(payload, tuple):
            return [self._sanitize(item) for item in payload]
        return payload

    @staticmethod
    def _response_payload(response: requests.Response) -> Any:
        """
        封装目的:
        - 统一提取响应体，兼容 JSON 与文本场景。

        封装实现:
        - Content-Type 为 JSON 时优先 response.json()。
        - 非 JSON 返回文本，超长文本截断至 5000 字符。

        外部接口:
        - 入参: requests.Response。
        - 出参: dict/list/str 等可序列化内容。
        """
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type.lower():
            try:
                return response.json()
            except ValueError:
                return response.text
        text = response.text
        if len(text) > 5000:
            return f"{text[:5000]}...<truncated>"
        return text

    @staticmethod
    def parse_body_as_json(body: Any) -> Any:
        """
        封装目的:
        - 将多形态响应体尽量转换为 JSON 结构，简化断言代码。

        封装实现:
        - dict/list 直接返回，bytes 先解码，str 尝试 json.loads。
        - 解析失败时保留原始字符串。

        外部接口:
        - 入参: body（dict/list/bytes/str/其他）。
        - 出参: JSON 结构或原值。
        """
        if isinstance(body, (dict, list)):
            return body
        if isinstance(body, bytes):
            body = body.decode("utf-8", errors="replace")
        if isinstance(body, str):
            try:
                return jsonlib.loads(body)
            except ValueError:
                return body
        return body
