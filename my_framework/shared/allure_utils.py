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
    allure_results_dir.mkdir(parents=True, exist_ok=True)
    env_map = build_environment_map(config, test_env)
    output = allure_results_dir / "environment.properties"
    lines = [f"{key}={value}" for key, value in env_map.items()]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def _default_categories() -> list[dict[str, Any]]:
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
    source = allure_report_dir / "history"
    target = report_root / "allure-history"
    if not source.exists():
        return False
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    return True


def attach_text(name: str, content: str) -> None:
    try:
        import allure
    except Exception:
        return
    allure.attach(content, name=name, attachment_type=allure.attachment_type.TEXT)


def attach_json(name: str, payload: dict[str, Any]) -> None:
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
