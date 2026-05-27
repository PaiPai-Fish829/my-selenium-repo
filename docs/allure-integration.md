# Allure 集成与使用指南

本文档说明如何在当前 pytest 自动化框架中使用 Allure，并补齐 Environment / Behaviors / Categories / Trends 四个模块。

## 1. 在测试代码中使用 Allure 装饰器

常用装饰器：

- `@allure.feature`：功能模块
- `@allure.story`：业务场景/用户故事
- `@allure.severity`：严重级别（`blocker` / `critical` / `normal` / `minor` / `trivial`）

示例（类级别 + 方法级别）：

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

参数化用例中也可以用动态方式：

```python
allure.dynamic.feature("API 接口测试")
allure.dynamic.story("HTTPBin 冒烟验证")
allure.dynamic.severity(allure.severity_level.NORMAL)
allure.dynamic.title(case.get("title", "default_case"))
```

## 2. 添加自定义标签（标记）

### 2.1 pytest marker + allure.tag 组合

```python
import allure
import pytest

@pytest.mark.smoke
@pytest.mark.custom_tag
@allure.tag("smoke", "custom_tag")
def test_smoke_case():
    assert True
```

### 2.2 在 pytest.ini 注册 marker

当前项目已在 `pytest.ini` 注册：

- `smoke`
- `custom_tag`
- `api`
- `ui`
- `demo`

可以按 marker 执行：

```bash
.\.venv\Scripts\python.exe -m pytest tests -m smoke -v
```

## 3. 本地生成带历史趋势的 Allure 报告

### 3.1 首次运行

```bash
.\.venv\Scripts\python.exe scripts/run_tests.py tests/api --allure
```

首次会生成：

- `reports/<timestamp>/allure-results`
- `reports/<timestamp>/allure-report`
- `reports/allure-history`（历史缓存）

### 3.2 第二次运行（继承历史）

```bash
.\.venv\Scripts\python.exe scripts/run_tests.py tests/api --allure
```

第二次执行前脚本会自动把 `reports/allure-history` 复制到新的 `allure-results/history`，生成后再回写最新历史，因此 Trends 模块会显示跨运行趋势。

### 3.3 完整流程说明

1. pytest 通过 `--alluredir` 产出原始结果
2. `tests/conftest.py` 自动写入 `environment.properties` / `categories.json` / `executor.json`
3. `scripts/run_tests.py` 自动继承历史缓存
4. Allure CLI 生成报告并更新历史缓存

## 4. CI 环境中的报告部署地址

本项目已提供工作流：`.github/workflows/allure-report.yml`。

- 触发：`push(master/main)` 或 `workflow_dispatch`
- 部署分支：`gh-pages`
- 预期访问地址：
  - `https://paipai-fish829.github.io/my-selenium-repo/`

如果仓库尚未开启 GitHub Pages：

1. 打开仓库 `Settings` -> `Pages`
2. `Source` 选择 `Deploy from a branch`
3. 分支选择 `gh-pages`，目录选择 `/ (root)`
4. 保存后等待工作流下一次部署

---

## 常见问题

### 1) Allure 报告 Environment 为空

确认是否通过 `scripts/run_tests.py ... --allure` 或 `pytest --alluredir=...` 执行；`tests/conftest.py` 只会在存在 `alluredir` 时写环境文件。

### 2) Trends 为空

确认不是第一次执行，并检查 `reports/allure-history` 是否存在。

### 3) 报告页面 500（本地直接打开）

项目已默认启用 `--single-file` 生成，若仍有问题请优先打开新生成的 `allure-report/index.html`。
