# SeleniumBase 自动化测试框架（ECShop）

基于 `SeleniumBase + Pytest + YAML` 的 UI 自动化测试项目，支持：

- Page Object 模式
- YAML 参数化测试
- 自定义断言封装
- 失败自动截图
- 可选测试报告（HTML / Markdown / Allure）

---

## 3 分钟上手

### 1) 安装依赖

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2) 直接跑一个测试（原生 pytest）

```bash
.\.venv\Scripts\python.exe -m pytest tests/ecshoplogin.py -v
```

### 3) 用脚本跑并按需生成报告

```bash
# 默认：是否产报告由 config.yaml 的 project.report_enabled 控制
.\.venv\Scripts\python.exe scripts/run_tests.py tests/ecshoplogin.py -v

# 显式生成报告（HTML + Markdown）
.\.venv\Scripts\python.exe scripts/run_tests.py tests/ecshoplogin.py -v --report
```

---

## 项目结构

```text
my-selenium-repo/
├── config.yaml
├── data/
│   ├── test_data.yaml
│   └── scenarios/
│       └── ecshop_login.yaml
├── my_framework/
│   ├── base_test.py
│   ├── assertions.py
│   └── yaml_parametrize.py
├── pages/
│   ├── base_page.py
│   ├── login_page.py
│   ├── search.py
│   ├── shopping_page.py
│   └── shopping_car_page.py
├── scripts/
│   └── run_tests.py
├── tests/
│   ├── ecshoplogin.py
│   ├── test_ecshop_login_parametrize.py
│   ├── test_yaml_parametrize.py
│   └── test_example.py
├── pytest.ini
└── Makefile
```

### 分层职责

- `config.yaml`：框架配置（环境、截图、报告开关）
- `data/`：测试数据
- `pages/`：页面对象（只配路径和定位器，不写 IP）
- `my_framework/`：框架能力（基类、断言、参数化）
- `tests/`：业务测试与参数化用例
- `scripts/`：测试执行脚本

---

## 配置说明（config.yaml）

### 1) 环境配置（生效）

`BaseTest` 会读取当前环境，`BasePage.open_path()` 会自动拼接 `base_url`。

```yaml
environments:
  default:
    base_url: "http://192.168.47.129"
    timeout: 10
  staging:
    base_url: "http://192.168.47.129"
    timeout: 15
```

切换环境：

```bash
.\.venv\Scripts\python.exe -m pytest tests --test-env=staging -v
```

### 2) 失败截图开关

```yaml
project:
  screenshot_on_failure: false
  screenshot_dir: "artifacts/screenshots"
```

临时覆盖：

```bash
set SCREENSHOT_ON_FAILURE=true
```

### 3) 报告默认开关

```yaml
project:
  report_enabled: false
  report_dir: "reports"
```

- `false`：脚本默认只跑测试，不产报告
- 可用 CLI `--report` 临时开启

---

## 测试数据设计

### 通用数据（`data/test_data.yaml`）

用于常规流程测试的默认值（例如账号、关键字、商品 ID）。

### 参数化数据（`data/scenarios/*.yaml`）

用于一条测试生成多条 case。

示例：`data/scenarios/ecshop_login.yaml`

```yaml
cases:
  - id: "login_success_valid_user"
    input:
      username: "test"
      password: "123456"
    expected:
      result: "success"
      contains_any: ["登录成功"]
```

---

## YAML 参数化用法

装饰器（`my_framework/yaml_parametrize.py`）：

```python
@yaml_parametrize("case", "cases", data_file="data/scenarios/ecshop_login.yaml")
def test_login_by_yaml_case(sb, case):
    ...
```

执行链路：

1. 读取 YAML
2. 生成 pytest 参数化 case
3. 逐条执行真实 UI 流程
4. 按 `expected` 调用断言封装校验

---

## 断言与输出策略

项目使用 `my_framework/assertions.py`，支持：

- `assert_page_contains_any(...)`
- `assert_page_contains_all(...)`
- `assert_page_not_contains(...)`
- `assert_url_contains(...)`

断言失败信息包含：业务提示、期望关键词、当前 URL、失败原因。  
同时项目已禁用 `pytest-markdown-report` 的终端接管，保留原生 pytest 输出风格。

---

## 报告管理（scripts/run_tests.py）

### 支持报告类型

1. `pytest-html`（HTML）
2. Markdown（由 junitxml 转换生成，AI 友好）
3. Allure（可选）

### 常用命令

```bash
# 默认（是否产报告由 config.yaml 控制）
.\.venv\Scripts\python.exe scripts/run_tests.py tests/ecshoplogin.py -v

# 强制生成 HTML + Markdown 报告
.\.venv\Scripts\python.exe scripts/run_tests.py tests/ecshoplogin.py -v --report

# 强制关闭 HTML + Markdown 报告
.\.venv\Scripts\python.exe scripts/run_tests.py tests/ecshoplogin.py -v --no-report

# 指定报告目录
.\.venv\Scripts\python.exe scripts/run_tests.py tests/ecshoplogin.py -v --report --report-dir reports

# 生成 Allure（会检查 java / allure 是否可用）
.\.venv\Scripts\python.exe scripts/run_tests.py tests/ecshoplogin.py --allure

# 仅生成 Allure 原始结果
.\.venv\Scripts\python.exe scripts/run_tests.py tests/ecshoplogin.py --allure-only
```

### 报告目录结构

```text
reports/
└── 20260519_173932/
    ├── report.html
    ├── report.md
    ├── report.xml
    ├── allure-results/   # 仅 --allure / --allure-only
    └── allure-report/    # 仅 --allure
```

### Makefile（可选）

```bash
make test
make test-allure
make test-allure-only
```

---

## 常见问题

### 为什么直接 `python tests/xxx.py` 会报模块导入错误？

因为 pytest 项目应通过 pytest 入口运行，不要直接执行测试文件。

正确方式：

```bash
.\.venv\Scripts\python.exe -m pytest tests/xxx.py -v
```

### 为什么脚本跑出来和原生 pytest 终端输出不一样？

项目已在 `pytest.ini` 和脚本中禁用了 `pytest-markdown-report` 的终端接管。  
如果你仍看到 markdown 风格输出，请确认没有手动启用该插件参数。
