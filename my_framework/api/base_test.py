from __future__ import annotations

import os
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Mapping

from requests import Session

from my_framework.api.client import ApiClient
from my_framework.shared.config_utils import read_by_path


class BaseApiTest:
    _token_lock = Lock()
    _cached_token: str | None = None
    _token_expire_at: float = 0.0
    _refresh_buffer_seconds = 60

    def __init__(self) -> None:
        self.api_client = ApiClient.from_config()

    @classmethod
    def _runtime_settings(cls) -> dict[str, Any]:
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
        return read_by_path(source, key_path, default)

    @staticmethod
    def _to_expire_at(value: Any) -> float | None:
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
        return datetime.now(tz=timezone.utc).timestamp() >= (
            cls._token_expire_at - cls._refresh_buffer_seconds
        )

    @classmethod
    def _extract_token_from_response(cls, payload: Mapping[str, Any], auth_cfg: Mapping[str, Any]) -> str:
        token_path = str(auth_cfg.get("token_path", "token"))
        token = cls._read_by_path(payload, token_path, None)
        if token is None:
            raise RuntimeError(f"登录响应中未找到 token，路径: {token_path}")
        return str(token)

    @classmethod
    def _extract_expire_at_from_response(cls, payload: Mapping[str, Any], auth_cfg: Mapping[str, Any]) -> float:
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
        self.api_client = ApiClient.from_config()

    def teardown_method(self) -> None:
        if hasattr(self, "api_client") and isinstance(self.api_client, ApiClient):
            self.api_client.close()
