from __future__ import annotations

from typing import Any


def _raise_assertion(message: str) -> None:
    """
    封装目的:
    - 统一 API 断言失败异常抛出方式。

    封装实现:
    - 直接抛出 AssertionError，并由上层传入业务语义文案。

    外部接口:
    - 入参: message，失败提示信息。
    - 出参: 无；恒抛异常。
    """
    raise AssertionError(message)


def _read_by_path(data: Any, key_path: str) -> Any:
    """
    封装目的:
    - 支持通过点路径读取 JSON 对象中的嵌套字段。

    封装实现:
    - 以 "." 分割路径并逐层向下读取 dict 节点。
    - 任一层缺失时抛 KeyError，避免断言误判。

    外部接口:
    - 入参: data（响应 JSON）、key_path（如 data.user.id）。
    - 出参: 路径对应值。
    - 异常: 路径不存在时抛 KeyError。
    """
    value = data
    for key in key_path.split("."):
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            raise KeyError(f"JSON 路径不存在: {key_path}")
    return value


def assert_status_code(actual: int, expected: int, message: str | None = None) -> None:
    """
    封装目的:
    - 统一状态码断言逻辑，提升失败信息可读性。

    封装实现:
    - 相等时直接返回，不相等时输出标准化失败文案。

    外部接口:
    - 入参: actual、expected、可选自定义 message。
    - 出参: 无；失败抛 AssertionError。
    """
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
    """
    封装目的:
    - 断言 JSON 指定路径字段值与预期一致。

    封装实现:
    - 先用 _read_by_path 读取实际值，再与 expected 比较。
    - 不一致时抛出携带路径信息的断言错误。

    外部接口:
    - 入参: payload、key_path、expected、可选 message。
    - 出参: 无；失败抛 AssertionError/KeyError。
    """
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
    """
    封装目的:
    - 批量断言 JSON 中多个路径字段是否同时满足期望值。

    封装实现:
    - 遍历 expected_items，逐项读取并比较。
    - 缺失字段或值不匹配时立即抛 AssertionError。

    外部接口:
    - 入参: payload、expected_items、可选 message。
    - 出参: 无；失败抛 AssertionError。
    """
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
