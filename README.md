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
├── docs/
│   ├── api-env-config.md
│   ├── ui-env-config.md
│   └── framework-core.md
├── data/
│   └── scenarios/
│       └── api/
│           └── httpbin_smoke.yaml
├── example/
│   ├── README.md
│   ├── data/
│   │   └── scenarios/
│   │       ├── ecshop_login.yaml
│   │       └── reqres_products.yaml
│   ├── pages/
│   │   ├── base_page.py
│   │   ├── login_page.py
│   │   ├── search.py
│   │   ├── shopping_page.py
│   │   └── shopping_car_page.py
│   └── tests/
│       ├── test_ecshop_flow.py
│       ├── test_ecshop_login_parametrize.py
│       ├── test_reqres_api_demo.py
│       └── test_reqres_session_token_demo.py
├── my_framework/
│   ├── api_client.py
│   ├── assertions_api.py
│   ├── assertions_ui.py
│   ├── assertions.py
│   ├── base_api_test.py
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

API 环境配置的完整字段、优先级与鉴权参数说明见：

- `docs/api-env-config.md`
- `docs/ui-env-config.md`（UI 环境配置说明）

---

## YAML 参数化

使用 `my_framework/yaml_parametrize.py`：

```python
@yaml_parametrize("case", "cases", data_file="data/scenarios/api/httpbin_smoke.yaml")
def test_xxx(case):
    ...
```

它与 UI/API 无耦合，可直接复用。

`BaseTest` 与 `yaml_parametrize` 的轻量说明见：

- `docs/framework-core.md`

### YAML 动态 Marker（API 场景）

API YAML 用例可增加 `markers` 字段，`tests/api/conftest.py` 会在收集阶段动态挂载到用例：

```yaml
cases:
  - id: get_profile
    markers: [api, need_auth, slow]
    request:
      method: GET
      path: /profile
```

可用的 API 相关 marker：

- `api`：标识 API 测试
- `need_auth`：自动触发 Token 鉴权客户端 fixture
- `need_cookies`：自动触发 Cookie 登录态客户端 fixture
- `slow`：标识慢速用例
- `dependency(depends=[...])`：依赖关系标识（建议配合 `pytest-dependency`）

---

## API 封装说明

### 1) ApiClient（`my_framework/api_client.py`）

- 使用 `requests.Session` 复用连接与 Cookie
- 支持 Token / Cookie 鉴权（`auth_mode=token|cookie|both`）
- 支持从 `config.yaml` 自动读取 API 配置（兼容 `api.*` 与 `environments.*`）
- 支持 `get/post/put/patch/delete` 统一调用
- 提供 `get_last_request()` / `get_last_response()`，供 pytest fixture 记录日志
- 自动脱敏敏感字段：`password/token/authorization/secret/api_key`（支持嵌套）

### 2) BaseApiTest（`my_framework/base_api_test.py`）

- `get_token()`：登录获取 Token，内置缓存与过期前 60 秒自动刷新
- `login_and_get_session()`：执行登录并返回带 Cookie 的 Session
- `setup_method/teardown_method`：初始化与释放 `ApiClient`

### 3) API Fixtures（`tests/api/conftest.py`）

- `api_client`：基础客户端（function）
- `auth_token`：会话级 Token（session）
- `authenticated_api_client`：自动注入 Token 的客户端（function）
- `api_session_with_cookies`：带 Cookie 登录态的客户端（function）
- `api_request_log`：自动记录请求/响应；失败时附加脱敏详情

### 4) API 使用示例

```python
import pytest

@pytest.mark.api
@pytest.mark.need_auth
def test_profile(authenticated_api_client):
    response = authenticated_api_client.get("/profile")
    assert response.status_code == 200
```

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
