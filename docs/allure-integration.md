# Allure 集成与使用指南

本文档覆盖以下内容：

1. 已修复问题清单（Environment / Executor / Trends / 单文件 500）
2. Allure 与 Pytest 的结合方式（装饰器、标签、fixture 与附件）
3. `scripts/run_tests.py` 对 Allure 的封装机制（兼容原命令）
4. 本地与 CI 的完整执行流程

## 目录

- [一、已修复问题与原因说明](#一已修复问题与原因说明)
- [二、Allure 与 Pytest 的结合方式](#二allure-与-pytest-的结合方式)
- [三、run_tests.py 对 Allure 的封装](#三run_testspy-对-allure-的封装)
- [四、本地执行（含历史趋势）](#四本地执行含历史趋势)
- [五、CI 与 GitHub Pages 部署](#五ci-与-github-pages-部署)
- [六、常见问题排查](#六常见问题排查)

## 一、已修复问题与原因说明

### 1) `--allure-only` 只生成 JSON，无法直接浏览

- 现象：目录只有 `*-result.json`、`*-container.json`
- 原因：`--allure-only` 设计即为“仅生成原始结果”
- 处理：使用 `--allure` 触发 HTML 生成

### 2) Windows 下 `allure` 命令存在但脚本调用失败

- 现象：终端可执行，脚本 `subprocess` 报 `FileNotFoundError`
- 原因：PowerShell 的 `allure.ps1` 与 Python 子进程解析差异
- 处理：`run_tests.py` 增强命令解析，优先 `allure.cmd` / `npx.cmd`，并支持：
  - 环境变量：`ALLURE_CMD`
  - 配置项：`config.yaml -> project.allure_cmd`

### 3) 单文件报告本地打开出现 500

- 现象：`index.html` 可打开，但资源请求报 500
- 原因：多文件资源在本地预览环境下二次请求失败
- 处理：默认启用 `--single-file` 生成单文件 HTML

### 4) Environment / Executor 在 `example/tests` 场景为空

- 现象：`widgets/environment.json`、`widgets/executors.json` 为 `[]`
- 原因：此前钩子只在 `tests/conftest.py`，运行 `example/tests` 未触发
- 处理：将写入钩子落到仓库根级 `conftest.py`，统一生效

### 5) Environment 键值被错误拆分

- 现象：如 `Test Env=default` 被解析为 `Test -> Env=default`
- 原因：`environment.properties` 键名带空格
- 处理：改为无空格键名（如 `TEST_ENV`、`BASE_URL`）

## 二、Allure 与 Pytest 的结合方式

### 2.1 测试注解：Feature / Story / Severity

```python
import allure
import pytest


@pytest.mark.api
@allure.feature("用户中心")
class TestUserCenter:
    @allure.story("查询用户资料")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_get_profile(self, authenticated_api_client):
        response = authenticated_api_client.get("/profile")
        assert response.status_code == 200
```

参数化场景可动态写入：

```python
allure.dynamic.feature("API 接口测试")
allure.dynamic.story("HTTPBin 冒烟验证")
allure.dynamic.severity(allure.severity_level.NORMAL)
allure.dynamic.title(case.get("title", "default_case"))
```

### 2.2 自定义标签（pytest marker + allure.tag）

```python
import allure
import pytest


@pytest.mark.smoke
@pytest.mark.custom_tag
@allure.tag("smoke", "custom_tag")
def test_smoke_case():
    assert True
```

`pytest.ini` 中已注册：

- `api`
- `ui`
- `demo`
- `smoke`
- `custom_tag`

执行示例：

```bash
.\.venv\Scripts\python.exe -m pytest tests -m smoke -v
```

### 2.3 附件能力（失败截图 / API 请求响应）

- UI：`my_framework/base_test.py` 在失败截图后自动尝试附加 PNG 与失败 URL
- API：`tests/api/conftest.py` 自动附加最后一次请求/响应（JSON）

## 三、run_tests.py 对 Allure 的封装

`scripts/run_tests.py` 已做统一封装，保持现有 CLI 接口不变：

- `--allure-only`：只生成 `allure-results`
- `--allure`：生成 `allure-results` + `allure-report`

### 3.1 环境检测与命令解析

- 检查 `java`
- 自动解析 Allure 可执行命令（支持 Windows）：
  - `allure.cmd`
  - `npx.cmd allure-commandline`
  - `ALLURE_CMD`
  - `project.allure_cmd`

### 3.2 趋势历史继承机制

- 运行前：将 `reports/allure-history` 复制到本次 `allure-results/history`
- 生成后：从 `allure-report-history-cache/history` 回写 `reports/allure-history`

### 3.3 单文件与历史兼容策略

- 为避免本地预览 500，最终报告使用 `--single-file`
- 为保证 Trends 可持续，额外先生成一份 history-cache 报告用于提取 `history`

## 四、本地执行（含历史趋势）

### 4.1 首次执行

```bash
.\.venv\Scripts\python.exe scripts/run_tests.py tests/api --allure
```

产物：

- `reports/<timestamp>/allure-results`
- `reports/<timestamp>/allure-report`
- `reports/allure-history`

### 4.2 第二次执行（验证趋势）

```bash
.\.venv\Scripts\python.exe scripts/run_tests.py tests/api --allure
```

第二次会自动继承上次 `history`，Trends 将展示跨次变化。

## 五、CI 与 GitHub Pages 部署

工作流：`.github/workflows/allure-report.yml`

- 触发：`push(master/main)`、`workflow_dispatch`
- 行为：
  1. 拉取依赖与 Allure CLI
  2. 恢复 `gh-pages` 上一次 `history`
  3. 运行测试并生成报告
  4. 发布到 `gh-pages`

预期地址：

- `https://paipai-fish829.github.io/my-selenium-repo/`

未启用 Pages 时：

1. `Settings -> Pages`
2. `Deploy from a branch`
3. 选择 `gh-pages` + `/ (root)`

## 六、常见问题排查

### 6.1 Environment 为空

- 必须通过 `--alluredir` 执行（`--allure` 或 `--allure-only`）
- 确认运行目标是否在根级 `conftest.py` 覆盖范围（当前已统一）

### 6.2 Executor 为空

- 检查 `allure-results/executor.json` 是否存在
- 检查 `widgets/executors.json` 是否为非空数组

### 6.3 Trends 为空

- 至少连续执行两次
- 确认 `reports/allure-history` 目录存在并有内容

### 6.4 单文件打开仍异常

- 打开最新生成的 `allure-report/index.html`
- 若使用 IDE 内置预览，优先切换系统浏览器验证
