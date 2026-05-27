from __future__ import annotations

import os
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Mapping

from requests import Session

from my_framework.api.client import ApiClient
from my_framework.shared.config_utils import read_by_path


class BaseApiTest:
    """
    封装目的:
    - 提供 API 用例公共基类，统一管理登录、Token 缓存与客户端生命周期。

    封装实现:
    - 通过类级缓存与锁控制 Token 刷新，避免并发场景重复登录。
    - 从配置读取认证策略，支持 token/cookie 两类登录流程。
    - 提供 setup/teardown 与客户端创建的标准入口。

    外部接口:
    - 供测试类继承使用，核心能力为 get_token、login_and_get_session。
    - 实例属性 api_client 在 setup_method 中可直接使用。
    """
    _token_lock = Lock()
    _cached_token: str | None = None
    _token_expire_at: float = 0.0
    _refresh_buffer_seconds = 60

    def __init__(self) -> None:
        """
        封装目的:
        - 初始化测试实例所需的 API 客户端。

        封装实现:
        - 调用 ApiClient.from_config 按当前环境创建客户端实例。

        外部接口:
        - 入参: 无。
        - 出参: 无（初始化 self.api_client）。
        """
        self.api_client = ApiClient.from_config()

    @classmethod
    def _runtime_settings(cls) -> dict[str, Any]:
        """
        封装目的:
        - 统一整理运行期鉴权配置，避免后续方法重复读取与判空。

        封装实现:
        - 调用 ApiClient.read_api_runtime_settings。
        - 归并并标准化 base_url、timeout、token_env、auth 字段。

        外部接口:
        - 入参: 无。
        - 出参: 运行设置字典。
        """
        settings = ApiClient.read_api_runtime_settings()
        auth_node = settings.get("auth", {}) if isinstance(settings.get("auth"), Mapping) else {}
        return {
            "base_url": settings.get("base_url"),
            "timeout": settings.get("timeout", 10),
            "token_env": settings.get("token_env", "API_TOKEN"),
            "auth": dict(auth_node),
        }

    @staticmethod
    def _read_by_path(source: Mapping[str, Any], key_path: str, default: Any = None) -> Any:
        """
        封装目的:
        - 在基类内部提供统一路径读取能力，保持调用风格一致。

        封装实现:
        - 直接复用 shared.config_utils.read_by_path。

        外部接口:
        - 入参: source、key_path、default。
        - 出参: 读取结果或默认值。
        """
        return read_by_path(source, key_path, default)

    @staticmethod
    def _to_expire_at(value: Any) -> float | None:
        """
        封装目的:
        - 将不同格式的过期时间统一转换为 Unix 时间戳。

        封装实现:
        - 支持秒/毫秒数字、数字字符串、ISO8601 字符串。
        - 无法解析时返回 None，由上层执行兜底逻辑。

        外部接口:
        - 入参: 任意类型过期时间值。
        - 出参: 过期时间戳（秒）或 None。
        """
        if value is None:
            return None
        if isinstance(value, (int, float)):
            number = float(value)
            if number > 10_000_000_000:
                return number / 1000.0
            return number
        if isinstance(value, str):
            try:
                number = float(value)
                if number > 10_000_000_000:
                    return number / 1000.0
                return number
            except ValueError:
                pass
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
            except ValueError:
                return None
        return None

    @classmethod
    def _should_refresh_token(cls) -> bool:
        """
        封装目的:
        - 判断当前缓存 Token 是否接近过期，决定是否刷新。

        封装实现:
        - 使用当前 UTC 时间与 token_expire_at - buffer 进行比较。

        外部接口:
        - 入参: 无。
        - 出参: True 表示应刷新；False 表示可继续复用。
        """
        return datetime.now(tz=timezone.utc).timestamp() >= (
            cls._token_expire_at - cls._refresh_buffer_seconds
        )

    @classmethod
    def _extract_token_from_response(cls, payload: Mapping[str, Any], auth_cfg: Mapping[str, Any]) -> str:
        """
        封装目的:
        - 从登录响应中提取 Token，统一错误处理方式。

        封装实现:
        - 按配置 token_path 读取字段。
        - 字段缺失时抛 RuntimeError，避免静默失败。

        外部接口:
        - 入参: 登录响应 payload、auth 配置。
        - 出参: token 字符串。
        - 异常: 未找到 token 时抛 RuntimeError。
        """
        token_path = str(auth_cfg.get("token_path", "token"))
        token = cls._read_by_path(payload, token_path, None)
        if token is None:
            raise RuntimeError(f"登录响应中未找到 token，路径: {token_path}")
        return str(token)

    @classmethod
    def _extract_expire_at_from_response(cls, payload: Mapping[str, Any], auth_cfg: Mapping[str, Any]) -> float:
        """
        封装目的:
        - 从登录响应中解析 Token 过期时间，支持多种接口返回约定。

        封装实现:
        - 优先读取 expires_at_path，并转时间戳。
        - 其次读取 expires_in_path 并叠加当前时间。
        - 都不可用时回退 default_expire_seconds。

        外部接口:
        - 入参: 登录响应 payload、auth 配置。
        - 出参: 过期时间戳（秒）。
        """
        expires_at_path = auth_cfg.get("expires_at_path")
        expires_in_path = auth_cfg.get("expires_in_path", "expires_in")
        default_expire_seconds = int(auth_cfg.get("default_expire_seconds", 3600))

        if isinstance(expires_at_path, str):
            expire_at = cls._to_expire_at(cls._read_by_path(payload, expires_at_path, None))
            if expire_at:
                return expire_at

        if isinstance(expires_in_path, str):
            expires_in = cls._read_by_path(payload, expires_in_path, None)
            if isinstance(expires_in, str) and expires_in.isdigit():
                expires_in = int(expires_in)
            if isinstance(expires_in, (int, float)):
                return datetime.now(tz=timezone.utc).timestamp() + float(expires_in)

        return datetime.now(tz=timezone.utc).timestamp() + float(default_expire_seconds)

    @classmethod
    def _build_login_payload(cls, auth_cfg: Mapping[str, Any]) -> dict[str, Any]:
        """
        封装目的:
        - 统一构建登录请求体，兼容环境变量与配置两套来源。

        封装实现:
        - 读取 username/password 字段名及默认值。
        - 若配置了 payload 模板则合并并补齐账号密码字段。

        外部接口:
        - 入参: auth 配置。
        - 出参: 可直接发送的登录 payload 字典。
        """
        username_field = str(auth_cfg.get("username_field", "username"))
        password_field = str(auth_cfg.get("password_field", "password"))
        username = os.getenv("API_USERNAME", str(auth_cfg.get("username", "")))
        password = os.getenv("API_PASSWORD", str(auth_cfg.get("password", "")))

        custom_payload = auth_cfg.get("payload", None)
        if isinstance(custom_payload, Mapping):
            payload = dict(custom_payload)
            if username_field not in payload:
                payload[username_field] = username
            if password_field not in payload:
                payload[password_field] = password
            return payload
        return {username_field: username, password_field: password}

    @classmethod
    def get_token(cls, *, force_refresh: bool = False) -> str:
        """
        封装目的:
        - 获取可用 Token，集中处理静态 Token、环境变量与动态登录刷新策略。

        封装实现:
        - 按优先级返回 env token、静态 token、缓存 token。
        - 在锁内执行登录请求，解析 token 与过期时间并写入缓存。
        - 支持 force_refresh 强制跳过缓存重新登录。

        外部接口:
        - 入参: force_refresh（是否强制刷新）。
        - 出参: token 字符串。
        - 异常: 登录失败、响应格式异常时抛 RuntimeError。
        """
        settings = cls._runtime_settings()
        auth_cfg = settings["auth"]
        token_env = str(settings.get("token_env", "API_TOKEN"))
        env_token = os.getenv(token_env) or os.getenv("API_TOKEN")
        static_token = str(auth_cfg.get("token", "")).strip()

        if env_token:
            return env_token
        if static_token and not force_refresh:
            return static_token

        with cls._token_lock:
            if (
                not force_refresh
                and cls._cached_token
                and cls._token_expire_at > 0
                and not cls._should_refresh_token()
            ):
                return cls._cached_token

            login_path = str(auth_cfg.get("login_path", "/login"))
            login_method = str(auth_cfg.get("login_method", "POST")).upper()
            payload_type = str(auth_cfg.get("payload_type", "json")).lower()
            headers = auth_cfg.get("headers", None)
            timeout = int(auth_cfg.get("login_timeout", settings.get("timeout", 10)))
            login_payload = cls._build_login_payload(auth_cfg)

            client = ApiClient.from_config()
            try:
                if payload_type == "data":
                    response = client.request(
                        method=login_method,
                        url=login_path,
                        data=login_payload,
                        headers=headers if isinstance(headers, Mapping) else None,
                        timeout=timeout,
                        use_auth=False,
                        auth_mode="cookie",
                    )
                else:
                    response = client.request(
                        method=login_method,
                        url=login_path,
                        json=login_payload,
                        headers=headers if isinstance(headers, Mapping) else None,
                        timeout=timeout,
                        use_auth=False,
                        auth_mode="cookie",
                    )
                if response.status_code >= 400:
                    raise RuntimeError(
                        f"获取 Token 失败: status={response.status_code}, url={response.url}"
                    )
                payload = response.json()
                if not isinstance(payload, Mapping):
                    raise RuntimeError("获取 Token 失败：登录响应不是 JSON 对象")
                token = cls._extract_token_from_response(payload, auth_cfg)
                expire_at = cls._extract_expire_at_from_response(payload, auth_cfg)

                cls._cached_token = token
                cls._token_expire_at = expire_at
                return token
            finally:
                client.close()

    @classmethod
    def login_and_get_session(cls, *, client: ApiClient | None = None) -> Session:
        """
        封装目的:
        - 执行 Cookie 登录并返回带会话状态的 Session。

        封装实现:
        - 从配置读取 cookie_login_* 参数，复用统一 payload 构建逻辑。
        - 调用 ApiClient.request(auth_mode="cookie") 完成登录。

        外部接口:
        - 入参: 可选 ApiClient；未传入时内部创建。
        - 出参: requests.Session（含登录 Cookie）。
        - 异常: 登录状态码 >=400 时抛 RuntimeError。
        """
        settings = cls._runtime_settings()
        auth_cfg = settings["auth"]
        login_path = str(auth_cfg.get("cookie_login_path", auth_cfg.get("login_path", "/login")))
        login_method = str(auth_cfg.get("cookie_login_method", auth_cfg.get("login_method", "POST"))).upper()
        payload_type = str(auth_cfg.get("cookie_payload_type", auth_cfg.get("payload_type", "json"))).lower()
        timeout = int(auth_cfg.get("cookie_login_timeout", auth_cfg.get("login_timeout", settings.get("timeout", 10))))
        headers = auth_cfg.get("cookie_headers", auth_cfg.get("headers", None))
        payload = cls._build_login_payload(auth_cfg)

        managed_client = client or ApiClient.from_config()
        if payload_type == "data":
            response = managed_client.request(
                method=login_method,
                url=login_path,
                data=payload,
                headers=headers if isinstance(headers, Mapping) else None,
                timeout=timeout,
                use_auth=False,
                auth_mode="cookie",
            )
        else:
            response = managed_client.request(
                method=login_method,
                url=login_path,
                json=payload,
                headers=headers if isinstance(headers, Mapping) else None,
                timeout=timeout,
                use_auth=False,
                auth_mode="cookie",
            )

        if response.status_code >= 400:
            raise RuntimeError(f"Cookie 登录失败: status={response.status_code}, url={response.url}")
        return managed_client.session

    def setup_method(self) -> None:
        """
        封装目的:
        - 为每个测试方法准备独立的 API 客户端。

        封装实现:
        - 每次调用均重新创建 ApiClient，减少跨用例状态污染。

        外部接口:
        - 入参: 无。
        - 出参: 无。
        """
        self.api_client = ApiClient.from_config()

    def teardown_method(self) -> None:
        """
        封装目的:
        - 回收测试方法使用的客户端资源，避免连接泄漏。

        封装实现:
        - 检查 api_client 类型后调用 close()。

        外部接口:
        - 入参: 无。
        - 出参: 无。
        """
        if hasattr(self, "api_client") and isinstance(self.api_client, ApiClient):
            self.api_client.close()
