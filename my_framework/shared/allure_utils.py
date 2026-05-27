from __future__ import annotations

import json
import os
import platform
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from my_framework.shared.config_utils import read_by_path


def build_environment_map(config: dict[str, Any], test_env: str) -> dict[str, str]:
    """
    封装目的:
    - 为 Allure 环境信息输出构建统一键值映射。

    封装实现:
    - 读取项目名、环境名、Python/OS 版本及基础 URL 配置。
    - 将结果标准化为字符串字典，便于直接写入 properties 文件。

    外部接口:
    - 入参: config（全量配置）、test_env（环境名）。
    - 出参: 环境信息字典。
    """
    env_cfg = read_by_path(config, f"environments.{test_env}", {}) or {}
    project_cfg = config.get("project", {}) if isinstance(config, dict) else {}
    return {
        "PROJECT_NAME": str(project_cfg.get("name", "my-selenium-repo")),
        "TEST_ENV": test_env,
        "PYTHON_VERSION": platform.python_version(),
        "OS": f"{platform.system()} {platform.release()}",
        "BASE_URL": str(env_cfg.get("base_url", "")),
        "API_BASE_URL": str(env_cfg.get("api_base_url", "")),
    }


def write_environment_properties(
    allure_results_dir: Path,
    *,
    config: dict[str, Any],
    test_env: str,
) -> Path:
    """
    封装目的:
    - 生成 Allure `environment.properties` 文件，展示执行环境元信息。

    封装实现:
    - 确保结果目录存在。
    - 调用 build_environment_map 生成键值并按 `key=value` 写入文件。

    外部接口:
    - 入参: allure_results_dir、config、test_env。
    - 出参: 输出文件路径 Path。
    """
    allure_results_dir.mkdir(parents=True, exist_ok=True)
    env_map = build_environment_map(config, test_env)
    output = allure_results_dir / "environment.properties"
    lines = [f"{key}={value}" for key, value in env_map.items()]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def _default_categories() -> list[dict[str, Any]]:
    """
    封装目的:
    - 提供默认 Allure 失败分类规则，便于报告中按问题类型聚合。

    封装实现:
    - 返回内置分类列表，覆盖断言失败、元素定位、窗口与网络异常场景。

    外部接口:
    - 入参: 无。
    - 出参: categories 列表。
    """
    return [
        {
            "name": "断言失败",
            "matchedStatuses": ["failed"],
            "messageRegex": ".*AssertionError.*",
        },
        {
            "name": "元素定位失败",
            "matchedStatuses": ["failed", "broken"],
            "traceRegex": ".*NoSuchElementException.*",
        },
        {
            "name": "浏览器窗口问题",
            "matchedStatuses": ["failed", "broken"],
            "traceRegex": ".*NoSuchWindowException.*",
        },
        {
            "name": "网络请求异常",
            "matchedStatuses": ["broken"],
            "traceRegex": ".*(ConnectionError|Timeout|ReadTimeout|ConnectTimeout).*",
        },
    ]


def write_categories_json(
    allure_results_dir: Path,
    *,
    custom_categories: list[dict[str, Any]] | None = None,
) -> Path:
    """
    封装目的:
    - 生成 Allure `categories.json`，支持默认分类与自定义分类合并。

    封装实现:
    - 先加载默认分类，再追加 custom_categories。
    - 以 UTF-8 和缩进格式输出 JSON 文件。

    外部接口:
    - 入参: allure_results_dir、custom_categories（可选）。
    - 出参: 输出文件路径 Path。
    """
    allure_results_dir.mkdir(parents=True, exist_ok=True)
    categories = _default_categories()
    if custom_categories:
        categories.extend(custom_categories)
    output = allure_results_dir / "categories.json"
    output.write_text(
        json.dumps(categories, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output


def write_executor_json(allure_results_dir: Path) -> Path:
    """
    封装目的:
    - 生成 Allure `executor.json`，描述报告构建来源与执行上下文。

    封装实现:
    - 读取 GitHub Actions 环境变量，区分 CI 与本地运行。
    - 构建标准 executor 结构并写入 JSON 文件。

    外部接口:
    - 入参: allure_results_dir。
    - 出参: 输出文件路径 Path。
    """
    allure_results_dir.mkdir(parents=True, exist_ok=True)
    is_github = os.getenv("GITHUB_ACTIONS", "").lower() == "true"
    repo = os.getenv("GITHUB_REPOSITORY", "")
    run_id = os.getenv("GITHUB_RUN_ID", "")
    run_number = os.getenv("GITHUB_RUN_NUMBER", "")
    build_order = int(run_number) if run_number.isdigit() else int(datetime.now().timestamp())
    run_url = ""
    if repo and run_id:
        run_url = f"https://github.com/{repo}/actions/runs/{run_id}"
    repo_url = f"https://github.com/{repo}" if repo else ""
    payload = {
        "name": "GitHub Actions" if is_github else "Local CLI",
        "type": "github" if is_github else "local",
        "url": repo_url,
        "buildName": os.getenv("GITHUB_WORKFLOW", "local-run"),
        "buildOrder": build_order,
        "buildUrl": run_url,
        "reportName": "Allure Report",
        "reportUrl": "",
    }
    output = allure_results_dir / "executor.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output


def prepare_allure_history(report_root: Path, allure_results_dir: Path) -> bool:
    """
    封装目的:
    - 在生成新报告前恢复历史趋势数据，保持 Allure trend 连续性。

    封装实现:
    - 将 report_root/allure-history 复制到 results/history。
    - 支持目录与文件两类条目复制。

    外部接口:
    - 入参: report_root、allure_results_dir。
    - 出参: bool，是否成功恢复历史数据。
    """
    source = report_root / "allure-history"
    target = allure_results_dir / "history"
    if not source.exists():
        return False
    target.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        destination = target / item.name
        if item.is_dir():
            shutil.copytree(item, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(item, destination)
    return True


def persist_allure_history(report_root: Path, allure_report_dir: Path) -> bool:
    """
    封装目的:
    - 在报告生成后持久化最新 history，供下一次执行复用。

    封装实现:
    - 从 allure_report/history 复制到 report_root/allure-history。
    - 目标存在时先删除再重建，保证数据一致。

    外部接口:
    - 入参: report_root、allure_report_dir。
    - 出参: bool，是否成功持久化历史数据。
    """
    source = allure_report_dir / "history"
    target = report_root / "allure-history"
    if not source.exists():
        return False
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    return True


def attach_text(name: str, content: str) -> None:
    """
    封装目的:
    - 在存在 Allure 依赖时统一附加文本信息，兼容未安装场景。

    封装实现:
    - 运行时延迟导入 allure，导入失败直接静默返回。
    - 导入成功时以 TEXT 类型添加附件。

    外部接口:
    - 入参: name（附件名）、content（文本内容）。
    - 出参: 无。
    """
    try:
        import allure
    except Exception:
        return
    allure.attach(content, name=name, attachment_type=allure.attachment_type.TEXT)


def attach_json(name: str, payload: dict[str, Any]) -> None:
    """
    封装目的:
    - 在报告中附加 JSON 结构化信息，提升调试可读性。

    封装实现:
    - 延迟导入 allure，导入失败时静默退出。
    - 将 payload 序列化为格式化 JSON 后以 JSON 类型附加。

    外部接口:
    - 入参: name、payload。
    - 出参: 无。
    """
    try:
        import allure
    except Exception:
        return
    allure.attach(
        json.dumps(payload, ensure_ascii=False, indent=2),
        name=name,
        attachment_type=allure.attachment_type.JSON,
    )


def attach_png(path: Path, *, name: str = "failure-screenshot") -> bool:
    """
    封装目的:
    - 统一图片附件流程，用于失败截图等二进制证据挂载。

    封装实现:
    - 先校验文件是否存在，再延迟导入 allure。
    - 满足条件时调用 allure.attach.file 以 PNG 类型附加。

    外部接口:
    - 入参: path、name（可选）。
    - 出参: bool，是否成功附加图片。
    """
    if not path.exists():
        return False
    try:
        import allure
    except Exception:
        return False
    allure.attach.file(
        str(path),
        name=name,
        attachment_type=allure.attachment_type.PNG,
    )
    return True
