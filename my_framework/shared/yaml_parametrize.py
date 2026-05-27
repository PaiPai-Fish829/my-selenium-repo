from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from my_framework.shared.config_utils import PROJECT_ROOT, load_yaml, read_by_path

DEFAULT_TEST_DATA_FILE = PROJECT_ROOT / "data" / "test_data.yaml"


def _load_yaml_or_raise(path: Path) -> dict[str, Any]:
    """
    封装目的:
    - 为参数化装饰器提供严格 YAML 读取能力，避免数据源缺失被忽略。

    封装实现:
    - 文件不存在时直接抛 FileNotFoundError。
    - 文件存在时复用 load_yaml 返回解析结果。

    外部接口:
    - 入参: path，YAML 文件路径。
    - 出参: YAML 解析后的字典。
    - 异常: 文件不存在时抛 FileNotFoundError。
    """
    if not path.exists():
        raise FileNotFoundError(f"YAML 文件不存在: {path}")
    return load_yaml(path)


def yaml_parametrize(
    arg_name: str,
    key_path: str,
    *,
    data_file: str = "data/test_data.yaml",
    id_key: str = "id",
):
    """
    封装目的:
    - 将 YAML 中的用例列表转换为 pytest 参数化装饰器，统一数据驱动测试写法。

    封装实现:
    - 读取目标 YAML 文件并按 key_path 提取列表。
    - 校验路径存在且类型为 list。
    - 自动生成参数化 ids（优先 id_key，其次 title，最后按序号兜底）。

    外部接口:
    - 入参: arg_name、key_path、data_file、id_key。
    - 出参: pytest.mark.parametrize 装饰器对象。
    - 异常: 文件缺失、路径不存在或类型错误时抛相应异常。

    示例:
    @yaml_parametrize("case", "scenarios.login")
    def test_xxx(case): ...
    """
    yaml_path = PROJECT_ROOT / data_file
    content = _load_yaml_or_raise(yaml_path)
    cases = read_by_path(content, key_path, None)
    if cases is None:
        raise KeyError(f"YAML 路径不存在: {key_path}")
    if not isinstance(cases, list):
        raise TypeError(f"{key_path} 必须是列表(list)，当前类型: {type(cases).__name__}")

    ids: list[str] = []
    for index, case in enumerate(cases):
        if isinstance(case, dict):
            case_id = case.get(id_key) or case.get("title") or f"case_{index + 1}"
        else:
            case_id = f"case_{index + 1}"
        ids.append(str(case_id))

    return pytest.mark.parametrize(arg_name, cases, ids=ids)
