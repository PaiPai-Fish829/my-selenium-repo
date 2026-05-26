# Example 演示目录

本目录用于存放可运行的 UI 演示案例，与主框架目录解耦。

- `example/pages/`：演示页面对象
- `example/tests/`：演示测试
- `example/data/`：演示用 YAML 数据
- `example/tests/test_reqres_api_demo.py`：ReqRes API 演示（401 + x-api-key 鉴权）

```bash
# 执行演示：
.\.venv\Scripts\python.exe -m pytest example/tests -v --test-env=demo

# 仅收集用例
.\.venv\Scripts\python.exe -m pytest example/tests -v --test-env=demo --collect-only -q

# 仅执行 ReqRes API 演示（默认含 1 条 401 用例）
.\.venv\Scripts\python.exe -m pytest example/tests/test_reqres_api_demo.py -v

# 执行需要 API Key 的演示用例（Windows PowerShell）
$env:REQRES_API_KEY="你的ReqRes项目Key"
.\.venv\Scripts\python.exe -m pytest example/tests/test_reqres_api_demo.py -v -k with_api_key
```
