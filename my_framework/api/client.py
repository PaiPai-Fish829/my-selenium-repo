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
        self.session.close()

    def set_auth_token(self, token: str | None) -> None:
        self.auth_token = token

    def configure_auth(
        self,
        *,
        token: str | None = None,
        enable_token_auth: bool | None = None,
        enable_cookie_auth: bool | None = None,
    ) -> None:
        if token is not None:
            self.auth_token = token
        if enable_token_auth is not None:
            self.enable_token_auth = enable_token_auth
        if enable_cookie_auth is not None:
            self.enable_cookie_auth = enable_cookie_auth

    def _build_url(self, path: str) -> str:
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
        return copy.deepcopy(self._last_request)

    def get_last_response(self) -> dict[str, Any] | None:
        return copy.deepcopy(self._last_response)

    def _sanitize(self, payload: Any) -> Any:
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
