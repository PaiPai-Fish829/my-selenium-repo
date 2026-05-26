# API 环境配置说明

本文档说明当前框架中 API 测试相关配置的来源、优先级、字段含义与常见用法。

## 1. 配置入口与加载链路

- 配置文件：`config.yaml`
- 运行环境切换参数：`--test-env`（定义在根级 `conftest.py`）
- 环境变量注入：`TEST_ENV`（由 `inject_test_env` 自动注入）
- 读取入口：
  - `ApiClient.read_api_runtime_settings()`
  - `ApiClient.from_config()`
  - `BaseApiTest.get_token()` / `BaseApiTest.login_and_get_session()`

## 2. 建议配置结构

```yaml
api:
  base_url: "https://httpbin.org"
  timeout: 10
  headers:
    Content-Type: "application/json"
  sensitive_fields:
    - password
    - token
    - authorization
    - secret
    - api_key
  auth:
    token_env: "API_TOKEN"
    enable_token_auth: true
    enable_cookie_auth: true
    login_path: "/login"
    login_method: "POST"
    payload_type: "json"
    username_field: "username"
    password_field: "password"
    token_path: "token"
    expires_in_path: "expires_in"
    default_expire_seconds: 3600

environments:
  default:
    api_base_url: "https://httpbin.org"
    api_timeout: 10
    # 可选：按环境覆盖 auth
    api_auth:
      login_path: "/auth/login"
```

## 3. 字段与作用

### 3.1 `api` 节点（全局 API 默认配置）

- `api.base_url`
  - 全局 API 默认地址。
- `api.timeout`
  - 全局 API 默认超时时间（秒）。
- `api.headers`
  - 全局默认请求头（会与单次请求 header 合并）。
- `api.sensitive_fields`
  - 日志脱敏字段列表（支持嵌套 JSON 脱敏）。
- `api.auth.*`
  - 全局鉴权配置（Token/Cookie 登录参数、token 提取路径等）。

### 3.2 `environments.<env>` 节点（环境级覆盖）

- `api_base_url`
  - 覆盖 `api.base_url`。
- `api_timeout`
  - 覆盖 `api.timeout`。
- `api_auth` / `auth`
  - 覆盖全局 `api.auth`。

### 3.3 `environments.<env>.api` 节点（更高优先级覆盖）

- `environments.<env>.api.base_url`
- `environments.<env>.api.timeout`
- `environments.<env>.api.auth`

该节点用于更规范地集中放置“某环境下 API 专属配置”。

## 4. 配置优先级（从高到低）

### 4.1 `base_url`

1. `environments.<env>.api.base_url`
2. `environments.<env>.api_base_url`
3. `api.base_url`
4. `api_base_url`（根节点兼容写法）
5. 默认值：`https://httpbin.org`

### 4.2 `timeout`

1. `environments.<env>.api.timeout`
2. `environments.<env>.api_timeout`
3. `api.timeout`
4. 默认值：`10`

### 4.3 `auth` 配置

1. `environments.<env>.api_auth`
2. `environments.<env>.auth`
3. `environments.<env>.api.auth`
4. `api.auth`
5. 默认空对象

### 4.4 Token 取值

`ApiClient.from_config()` / `BaseApiTest.get_token()` 的 Token 来源优先级：

1. 显式传参（仅 `from_config(auth_token=...)`）
2. 配置中的静态 token（`auth.token`）
3. `auth.token_env` 指定的环境变量（默认 `API_TOKEN`）
4. 兜底环境变量 `API_TOKEN`
5. `BaseApiTest` 登录换 token（当未命中前几项时）

## 5. 与 pytest 的关系

- `--test-env=staging` 会决定读取 `environments.staging`。
- `tests/api/conftest.py` 的 `api_client` / `authenticated_api_client` / `api_session_with_cookies`
  都通过 `ApiClient.from_config()` 使用上述配置。
- `@pytest.mark.need_auth` 会自动注入 Token 客户端 fixture。
- `@pytest.mark.need_cookies` 会自动注入 Cookie 登录态客户端 fixture。

## 6. 常见场景

### 6.1 仅切换 API 地址

在 `environments.<env>` 配置 `api_base_url` 即可。

### 6.2 登录接口字段不是 `username/password`

在 `api.auth` 中改：

- `username_field`
- `password_field`
- `payload`（可选，完全自定义登录 payload）

### 6.3 token 不在响应根节点

配置 `token_path`，例如：

- `token_path: "data.access_token"`

### 6.4 token 过期时间字段不同

可配置：

- `expires_at_path`（绝对时间，支持 ISO 时间或时间戳）
- `expires_in_path`（相对秒数）
- `default_expire_seconds`（兜底）

## 7. 推荐实践

- 生产/测试账号密码尽量走环境变量（`API_USERNAME` / `API_PASSWORD`）。
- 不建议把长期有效 token 明文写入仓库。
- 如需跨环境复用，优先在 `api` 放默认值，在 `environments.<env>` 做覆盖。
