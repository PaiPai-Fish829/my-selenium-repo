from __future__ import annotations

from typing import Any

import requests


class ApiClient:
    """轻量 API 客户端，统一 base_url / timeout / headers 行为。"""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: int = 10,
        default_headers: dict[str, str] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        if default_headers:
            self.session.headers.update(default_headers)

    def _build_url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        normalized = path if path.startswith("/") else f"/{path}"
        return f"{self.base_url}{normalized}"

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        timeout: int | None = None,
    ) -> requests.Response:
        url = self._build_url(path)
        return self.session.request(
            method=method.upper(),
            url=url,
            params=params,
            headers=headers,
            json=json,
            data=data,
            timeout=timeout or self.timeout,
        )
