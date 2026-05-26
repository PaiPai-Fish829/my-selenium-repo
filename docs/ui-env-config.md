# UI 环境配置说明

本文档说明当前 UI 自动化测试（SeleniumBase）使用的环境配置来源、字段含义与常见用法。

## 1. 配置入口

- 主配置文件：`config.yaml`
- 运行参数：`--test-env`（在根级 `conftest.py` 中定义）
- 环境变量：`TEST_ENV`（由 `inject_test_env` 自动注入）
- 读取类：`my_framework/base_test.py` 中的 `BaseTest`

## 2. 当前 UI 配置字段（已在项目使用）

基于当前 `BaseTest` 实现，UI 侧主要读取以下配置：

- `environments.<env>.base_url`
  - 当前环境 UI 站点地址。
- `environments.<env>.timeout`
  - 供业务层按需使用的超时配置。
- `project.screenshot_on_failure`
  - 失败是否自动截图（可被环境变量 `SCREENSHOT_ON_FAILURE` 覆盖）。
- `project.screenshot_dir`
  - 失败截图保存目录，支持相对路径和绝对路径。

示例：

```yaml
project:
  screenshot_dir: "artifacts/screenshots"
  screenshot_on_failure: false

environments:
  default:
    base_url: "http://192.168.47.129"
    timeout: 10
  demo:
    base_url: "http://192.168.47.129"
    timeout: 10
```

## 3. 运行时行为

`BaseTest` 的关键流程：

1. `setUp()` 中读取 `TEST_ENV`（默认 `default`）。
2. 加载 `config.yaml` 和 `data/test_data.yaml` 到类缓存。
3. 将 `environments.<env>` 保存为 `self.current_config`。
4. 根据 `project.screenshot_dir` 确保截图目录存在。
5. `tearDown()` 时若用例失败且允许截图，则保存截图后再交给 SeleniumBase 关闭浏览器。

## 4. 配置优先级

### 4.1 环境选择优先级

1. 命令行 `--test-env=<env>`
2. 默认值 `default`

### 4.2 失败截图开关优先级

1. 环境变量 `SCREENSHOT_ON_FAILURE`
2. `project.screenshot_on_failure`
3. 默认值 `true`（代码兜底）

## 5. 常见用法

### 5.1 切换到 demo 环境执行 UI

```bash
.\.venv\Scripts\python.exe -m pytest example/tests -v --test-env=demo
```

### 5.2 临时强制关闭截图

```powershell
$env:SCREENSHOT_ON_FAILURE="false"
.\.venv\Scripts\python.exe -m pytest example/tests -v --test-env=demo
```

## 6. 推荐实践

- UI 站点地址和超时统一放 `environments.<env>`，避免用例硬编码。
- 对于 CI 场景，建议用 `SCREENSHOT_ON_FAILURE=true` 便于失败诊断。
- 用例里优先通过 `self.current_config` 或页面对象基类读取环境配置，不直接写死 URL。
