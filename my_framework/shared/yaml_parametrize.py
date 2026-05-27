from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from my_framework.shared.config_utils import PROJECT_ROOT, load_yaml, read_by_path

DEFAULT_TEST_DATA_FILE = PROJECT_ROOT / "data" / "test_data.yaml"


def _load_yaml_or_raise(path: Path) -> dict[str, Any]:
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
    从 YAML 读取列表数据并转成 pytest 参数化。

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
