# Example 演示目录

本目录用于存放可运行的 UI/API 演示案例，与主框架目录解耦。

- `example/pages/`：演示页面对象
- `example/tests/api/`：演示 API 测试
- `example/tests/ui/`：演示 UI 测试
- `example/data/`：演示用 YAML 数据
- `example/tests/api/test_httpbin_api_demo.py`：HTTPBin Token 鉴权演示（/bearer）
- `example/tests/api/test_httpbin_session_token_demo.py`：HTTPBin Session/Cookie 鉴权演示（/cookies）

```bash
# 使用项目启动脚本执行测试并用allure生成静态报告
.\.venv\Scripts\python.exe scripts/run_tests.py example/tests --allure --test-env=demo

# 使用原生pytest模块执行测试
.\.venv\Scripts\python.exe -m pytest example/tests -v --test-env=demo

# 仅收集用例
.\.venv\Scripts\python.exe scripts/run_tests.py example/tests -v --test-env=demo --collect-only -q

# 仅执行 HTTPBin Token 鉴权演示（参数化）
.\.venv\Scripts\python.exe scripts/run_tests.py example/tests/api/test_httpbin_api_demo.py -v

# 仅执行 HTTPBin Session/Cookie 鉴权演示（参数化）
.\.venv\Scripts\python.exe scripts/run_tests.py example/tests/api/test_httpbin_session_token_demo.py -v

# 仅执行演示 UI 用例
.\.venv\Scripts\python.exe scripts/run_tests.py example/tests/ui -v --test-env=demo

# 仅执行演示 API 用例
.\.venv\Scripts\python.exe scripts/run_tests.py example/tests/api -v
```
