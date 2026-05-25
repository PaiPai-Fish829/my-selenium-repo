# Example 演示目录

本目录用于存放可运行的 UI 演示案例，与主框架目录解耦。

- `example/pages/`：演示页面对象
- `example/tests/`：演示测试
- `example/data/`：演示用 YAML 数据

```bash
# 执行演示：
.\.venv\Scripts\python.exe -m pytest example/tests -v --test-env=demo

# 仅收集用例
.\.venv\Scripts\python.exe -m pytest example/tests -v --test-env=demo --collect-only -q
```
