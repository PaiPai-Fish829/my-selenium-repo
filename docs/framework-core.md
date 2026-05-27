# 框架核心模块简述

本文档对两个核心模块做轻量说明：

- `my_framework/base_test.py`
- `my_framework/yaml_parametrize.py`

## 1. `BaseTest`（UI 测试基类）

文件：`my_framework/base_test.py`

### 1.1 主要职责

- 继承 `SeleniumBase` 的 `BaseCase`，作为 UI 用例公共父类。
- 统一读取配置与测试数据（`config.yaml` / `data/test_data.yaml`）。
- 提供失败截图能力（含开关与目录管理）。
- 提供统一 UI 断言包装方法（`assert_page_contains_*`、`assert_url_contains`）。

### 1.2 生命周期

- `setUp()`
  - 调用 SeleniumBase 原始初始化。
  - 根据 `TEST_ENV` 选环境并加载 `self.current_config`。
  - 初始化截图目录。
- `tearDown()`
  - 若当前用例失败且启用截图，先保存失败截图。
  - 然后调用 SeleniumBase 的 `tearDown()` 释放浏览器资源。

### 1.3 常用能力

- `get_config(key_path, default)`：读取配置。
- `get_test_data(key_path, default)`：读取测试数据。
- `save_failure_artifacts(test_name)`：保存失败截图。

## 2. `yaml_parametrize`（YAML 参数化装饰器）

文件：`my_framework/yaml_parametrize.py`

### 2.1 主要职责

- 从 YAML 文件按路径读取用例列表。
- 自动转换为 `pytest.mark.parametrize(...)`。
- 自动生成可读用例 ID（默认优先 `id`，其次 `title`）。

### 2.2 使用方式

```python
from my_framework.shared.yaml_parametrize import yaml_parametrize

@yaml_parametrize("case", "cases", data_file="data/scenarios/api/httpbin_smoke.yaml")
def test_httpbin(case):
    assert "request" in case
```

参数说明：

- `arg_name`：测试函数参数名（例如 `case`）。
- `key_path`：YAML 中列表路径（例如 `cases`、`scenarios.login`）。
- `data_file`：相对项目根目录的 YAML 文件路径。
- `id_key`：生成参数 ID 时优先读取的字段名，默认 `id`。

### 2.3 异常行为（便于排错）

- YAML 文件不存在：抛出 `FileNotFoundError`。
- `key_path` 不存在：抛出 `KeyError`。
- `key_path` 对应值不是列表：抛出 `TypeError`。

## 3. 推荐配合方式

- UI 场景：测试类继承 `BaseTest`，用页面对象封装交互。
- API/UI 数据驱动场景：统一用 `yaml_parametrize` 管理用例数据。
- 复杂项目中，可在 YAML 增加 `markers` 字段并在 `conftest.py` 动态挂载 marker。
