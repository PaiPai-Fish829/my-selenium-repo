from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"


def load_yaml(path: Path) -> dict[str, Any]:
    """
    封装目的:
    - 提供 YAML 文件读取基础能力，屏蔽文件不存在与空内容细节。

    封装实现:
    - 文件不存在返回空字典。
    - 文件存在时以 utf-8 读取并使用 yaml.safe_load 解析。

    外部接口:
    - 入参: path，YAML 文件路径。
    - 出参: dict；不存在或空内容时返回 {}。
    """
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def read_by_path(source: Mapping[str, Any] | None, key_path: str | None, default: Any = None) -> Any:
    """
    封装目的:
    - 提供通用点路径读取能力，统一配置/测试数据访问方式。

    封装实现:
    - source 为空时返回默认值。
    - key_path 为空时返回源对象本身。
    - 逐层读取 Mapping，任一层缺失时返回默认值。

    外部接口:
    - 入参: source、key_path、default。
    - 出参: 读取值或 default。
    """
    if source is None:
        return default
    if not key_path:
        return source
    value: Any = source
    for key in key_path.split("."):
        if isinstance(value, Mapping) and key in value:
            value = value[key]
        else:
            return default
    return value


def coerce_bool(value: Any, default: bool = True) -> bool:
    """
    封装目的:
    - 将多类型配置值规范化为布尔值，减少调用方类型判断。

    封装实现:
    - 支持 bool/int/float/str 常见输入。
    - 字符串按 1/true/yes/on 识别为 True，其余回退默认值。

    外部接口:
    - 入参: value、default。
    - 出参: 归一化后的 bool。
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return default
