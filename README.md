# 自动化测试框架（UI + API）

本仓库基于 `Pytest + SeleniumBase + Requests + YAML`，支持：

- UI 自动化测试（SeleniumBase）
- API 接口测试（Requests）
- YAML 参数化用例
- UI/API 断言分层
- 可选报告（HTML / Markdown / Allure）
- 演示项目隔离（`example/`）

---

## 快速开始

### 1) 安装依赖

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2) 运行 API 测试（默认入口）

```bash
.\.venv\Scripts\python.exe -m pytest tests/api -v
```

### 3) 运行演示 UI 测试（独立目录）

```bash
.\.venv\Scripts\python.exe -m pytest example/tests -v --test-env=demo
```

---

## 目录结构（重构后）

```text
my-selenium-repo/
├── config.yaml
├── data/
│   └── scenarios/
│       └── api/
│           └── httpbin_smoke.yaml
├── example/
│   ├── data/
│   │   └── scenarios/
│   │       └── ecshop_login.yaml
│   ├── pages/
│   │   ├── base_page.py
│   │   ├── login_page.py
│   │   ├── search.py
│   │   ├── shopping_page.py
│   │   └── shopping_car_page.py
│   └── tests/
│       ├── test_ecshop_flow.py
│       └── test_ecshop_login_parametrize.py
├── my_framework/
│   ├── api_client.py
│   ├── assertions_api.py
│   ├── assertions_ui.py
│   ├── assertions.py
│   ├── base_test.py
│   └── yaml_parametrize.py
├── tests/
│   ├── conftest.py
│   ├── api/
│   │   ├── conftest.py
│   │   └── test_httpbin_api.py
│   └── ui/
│       └── conftest.py
├── scripts/
│   └── run_tests.py
├── pytest.ini
└── Makefile
```

---

## 分层与解耦策略

- `my_framework/`：框架能力层（参数化、断言、API 客户端、UI 基类）
- `tests/`：正式测试入口（API/UI 可长期演进）
- `example/`：演示工程（可删可换，不影响框架主逻辑）
- `tests/conftest.py`：全局通用能力（如 `--test-env`）
- `tests/api/conftest.py`：API 专属 fixture（如 `api_client`）
- `tests/ui/conftest.py`：UI 专属 fixture（可继续扩展浏览器策略）

---

## 配置说明（config.yaml）

环境配置现在支持 UI 与 API 双域：

```yaml
environments:
  default:
    base_url: "http://192.168.47.129"
    timeout: 10
    api_base_url: "https://httpbin.org"
    api_timeout: 10
```

切换环境：

```bash
.\.venv\Scripts\python.exe -m pytest tests -v --test-env=staging
```

---

## YAML 参数化

使用 `my_framework/yaml_parametrize.py`：

```python
@yaml_parametrize("case", "cases", data_file="data/scenarios/api/httpbin_smoke.yaml")
def test_xxx(case):
    ...
```

它与 UI/API 无耦合，可直接复用。

---

## 断言拆分

- UI 断言：`my_framework/assertions_ui.py`
  - `assert_page_contains_any(...)`
  - `assert_page_not_contains(...)`
  - `assert_url_contains(...)`
- API 断言：`my_framework/assertions_api.py`
  - `assert_status_code(...)`
  - `assert_json_path_equals(...)`
  - `assert_json_contains(...)`

`my_framework/assertions.py` 保留为兼容导出层，避免旧代码立即失效。

---

## 运行命令

### 原生 pytest

```bash
# API
.\.venv\Scripts\python.exe -m pytest tests/api -v

# 演示 UI
.\.venv\Scripts\python.exe -m pytest example/tests -v --test-env=demo

# 按 marker 运行
.\.venv\Scripts\python.exe -m pytest tests -m api -v
.\.venv\Scripts\python.exe -m pytest example/tests -m "ui and demo" -v
```

### 统一脚本（报告管理）

```bash
# 默认：是否产报告由 config.yaml 的 project.report_enabled 控制
.\.venv\Scripts\python.exe scripts/run_tests.py tests/api -v

# 强制启用 HTML + Markdown
.\.venv\Scripts\python.exe scripts/run_tests.py tests/api -v --report

# 仅导出 Allure 原始数据
.\.venv\Scripts\python.exe scripts/run_tests.py tests/api --allure-only

# 生成 Allure HTML（需要 java + allure 命令可用）
.\.venv\Scripts\python.exe scripts/run_tests.py tests/api --allure
```

---

## 报告输出结构

```text
reports/
└── 20260525_190000/
    ├── report.html
    ├── report.md
    ├── report.xml
    ├── allure-results/
    └── allure-report/
```

---

## 迁移后的维护建议

- 正式项目用例写在 `tests/`，演示仅放在 `example/`
- 新增 API fixture 时优先写入 `tests/api/conftest.py`
- UI/API 断言不要混用，避免后期维护成本上升
- 若要引入业务 UI 测试，可新增 `tests/ui/test_*.py`，不影响 `example/`
