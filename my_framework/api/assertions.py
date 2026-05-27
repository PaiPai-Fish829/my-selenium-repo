from __future__ import annotations

from typing import Any


def _raise_assertion(message: str) -> None:
    raise AssertionError(message)


def _read_by_path(data: Any, key_path: str) -> Any:
    value = data
    for key in key_path.split("."):
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            raise KeyError(f"JSON 路径不存在: {key_path}")
    return value


def assert_status_code(actual: int, expected: int, message: str | None = None) -> None:
    if actual == expected:
        return
    _raise_assertion(
        message or f"【接口断言失败】状态码不匹配，期望: {expected}，实际: {actual}"
    )


def assert_json_path_equals(
    payload: dict[str, Any],
    key_path: str,
    expected: Any,
    message: str | None = None,
) -> None:
    actual = _read_by_path(payload, key_path)
    if actual == expected:
        return
    _raise_assertion(
        message
        or f"【接口断言失败】JSON 字段不匹配，路径: {key_path}，期望: {expected}，实际: {actual}"
    )


def assert_json_contains(
    payload: dict[str, Any],
    expected_items: dict[str, Any],
    message: str | None = None,
) -> None:
    for key_path, expected in expected_items.items():
        try:
            actual = _read_by_path(payload, key_path)
        except KeyError:
            _raise_assertion(message or f"【接口断言失败】缺少字段: {key_path}")
        if actual != expected:
            _raise_assertion(
                message
                or f"【接口断言失败】字段值不匹配，路径: {key_path}，期望: {expected}，实际: {actual}"
            )
