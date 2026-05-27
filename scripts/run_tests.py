from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET
import yaml

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from my_framework.allure_utils import prepare_allure_history, persist_allure_history

def load_config() -> dict:
    config_path = ROOT_DIR / "config.yaml"
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def to_bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return default


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="运行 pytest 并统一管理测试报告输出。"
    )
    parser.add_argument(
        "targets",
        nargs="*",
        default=["tests"],
        help="可选测试路径，默认运行 tests 目录。",
    )
    parser.add_argument(
        "--report-dir",
        default=None,
        help="报告根目录（默认读取 config.yaml 的 project.report_dir）。",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="启用 HTML + Markdown 报告（可覆盖 config.yaml 默认值）。",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="关闭 HTML + Markdown 报告（可覆盖 config.yaml 默认值）。",
    )
    parser.add_argument(
        "--allure",
        action="store_true",
        help="在默认 HTML+Markdown 基础上，额外生成 Allure 报告。",
    )
    parser.add_argument(
        "--allure-only",
        action="store_true",
        help="仅生成 Allure 原始结果（allure-results）。",
    )
    parser.add_argument(
        "--pytest-arg",
        action="append",
        default=[],
        help="附加 pytest 参数（可重复）。例如 --pytest-arg=-k=login",
    )
    return parser


def check_command_available(command: str) -> bool:
    return shutil.which(command) is not None


def _command_exists(command: str) -> bool:
    # 支持绝对路径可执行文件 / bat / cmd
    if os.path.sep in command or (os.path.altsep and os.path.altsep in command):
        return Path(command).exists()
    return check_command_available(command)


def _parse_command(raw: str) -> list[str]:
    return shlex.split(raw, posix=False)


def _is_command_runnable(command_parts: list[str]) -> bool:
    try:
        result = subprocess.run(
            [*command_parts, "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode == 0
    except OSError:
        return False


def resolve_allure_command(project_cfg: dict) -> list[str] | None:
    # 优先级：环境变量 ALLURE_CMD > config.yaml(project.allure_cmd) > PATH 中 allure > npx 兜底
    raw_cmd = os.getenv("ALLURE_CMD") or str(project_cfg.get("allure_cmd", "")).strip()
    if raw_cmd:
        parsed = _parse_command(raw_cmd)
        if parsed and _command_exists(parsed[0]) and _is_command_runnable(parsed):
            return parsed

    if os.name == "nt":
        if check_command_available("allure.cmd") and _is_command_runnable(["allure.cmd"]):
            return ["allure.cmd"]
        if check_command_available("npx.cmd") and _is_command_runnable(
            ["npx.cmd", "allure-commandline"]
        ):
            return ["npx.cmd", "allure-commandline"]

    if check_command_available("allure") and _is_command_runnable(["allure"]):
        return ["allure"]
    if check_command_available("npx") and _is_command_runnable(["npx", "allure-commandline"]):
        return ["npx", "allure-commandline"]
    return None


def check_allure_environment(allure_exec: list[str] | None) -> tuple[bool, str]:
    missing: list[str] = []
    if not check_command_available("java"):
        missing.append("Java")
    if not allure_exec:
        missing.append("allure")

    if missing:
        tips = (
            "、".join(missing)
            + " 不可用。请先安装并确保命令在 PATH 中。\n"
            + "你也可以先不加 --allure，仅生成 HTML + Markdown 报告。\n"
            + "可选方案：设置环境变量 ALLURE_CMD 或 config.yaml 的 project.allure_cmd。"
        )
        return False, tips
    return True, ""


def run_command(cmd: list[str]) -> int:
    process = subprocess.run(cmd, check=False)
    return process.returncode


def generate_markdown_from_junit(junit_path: Path, markdown_path: Path) -> None:
    if not junit_path.exists():
        markdown_path.write_text(
            "# Test Report\n\n未找到 junit xml，无法生成 Markdown 报告。\n",
            encoding="utf-8",
        )
        return

    tree = ET.parse(junit_path)
    root = tree.getroot()
    testsuite = root if root.tag == "testsuite" else root.find("testsuite")
    if testsuite is None:
        markdown_path.write_text(
            "# Test Report\n\njunit xml 结构异常，无法生成 Markdown 报告。\n",
            encoding="utf-8",
        )
        return

    total = int(testsuite.attrib.get("tests", "0"))
    failures = int(testsuite.attrib.get("failures", "0"))
    errors = int(testsuite.attrib.get("errors", "0"))
    skipped = int(testsuite.attrib.get("skipped", "0"))
    passed = total - failures - errors - skipped

    lines: list[str] = ["# Test Report", ""]
    summary_parts = [f"{passed}/{total} passed"]
    if failures:
        summary_parts.append(f"{failures} failed")
    if errors:
        summary_parts.append(f"{errors} errors")
    if skipped:
        summary_parts.append(f"{skipped} skipped")
    lines.append(f"**Summary:** {', '.join(summary_parts)}")
    lines.append("")

    failed_cases: list[tuple[str, str]] = []
    passed_cases: list[str] = []
    skipped_cases: list[str] = []

    for testcase in testsuite.iter("testcase"):
        nodeid = f"{testcase.attrib.get('classname', '')}::{testcase.attrib.get('name', '')}"
        failure_node = testcase.find("failure")
        error_node = testcase.find("error")
        skipped_node = testcase.find("skipped")

        if failure_node is not None or error_node is not None:
            detail = ""
            picked = failure_node if failure_node is not None else error_node
            if picked is not None:
                detail = (picked.text or "").strip()
            failed_cases.append((nodeid, detail))
        elif skipped_node is not None:
            skipped_cases.append(nodeid)
        else:
            passed_cases.append(nodeid)

    if failed_cases:
        lines.extend(["## Failures", ""])
        for nodeid, detail in failed_cases:
            lines.append(f"### {nodeid}")
            lines.append("")
            if detail:
                lines.append("```python")
                lines.append(detail)
                lines.append("```")
                lines.append("")

    if passed_cases:
        lines.extend(["## Passes", ""])
        for nodeid in passed_cases:
            lines.append(f"- {nodeid}")
        lines.append("")

    if skipped_cases:
        lines.extend(["## Skipped", ""])
        for nodeid in skipped_cases:
            lines.append(f"- {nodeid}")
        lines.append("")

    markdown_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = build_parser()
    args, passthrough_pytest_args = parser.parse_known_args()
    config = load_config()
    project_cfg = config.get("project", {}) if isinstance(config, dict) else {}
    allure_exec = resolve_allure_command(project_cfg)

    if args.allure and args.allure_only:
        parser.error("--allure 与 --allure-only 不能同时使用。")
    if args.report and args.no_report:
        parser.error("--report 与 --no-report 不能同时使用。")

    report_enabled = to_bool(project_cfg.get("report_enabled"), default=False)
    if args.report:
        report_enabled = True
    if args.no_report:
        report_enabled = False
    if args.allure_only:
        report_enabled = False

    report_dir_from_config = str(project_cfg.get("report_dir", "reports"))
    report_root = Path(args.report_dir or report_dir_from_config)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    need_artifacts_dir = report_enabled or args.allure or args.allure_only
    run_dir = report_root / timestamp if need_artifacts_dir else None
    if run_dir:
        run_dir.mkdir(parents=True, exist_ok=True)

    html_report = run_dir / "report.html" if run_dir else None
    markdown_report = run_dir / "report.md" if run_dir else None
    junit_report = run_dir / "report.xml" if run_dir else None
    allure_results = run_dir / "allure-results" if run_dir else None
    allure_report = run_dir / "allure-report" if run_dir else None

    pytest_args: list[str] = ["-v", "-p", "no:markdown_report"]
    pytest_args.extend(args.pytest_arg)
    pytest_args.extend(passthrough_pytest_args)

    if report_enabled and not args.allure_only:
        pytest_args.extend(
            [
                f"--html={html_report}",
                "--self-contained-html",
                f"--junitxml={junit_report}",
            ]
        )

    if args.allure or args.allure_only:
        pytest_args.append(f"--alluredir={allure_results}")
        if run_dir and allure_results:
            inherited = prepare_allure_history(report_root, allure_results)
            if inherited:
                print(f"[报告] 已继承历史趋势数据: {report_root / 'allure-history'}")

    if args.allure:
        ok, msg = check_allure_environment(allure_exec)
        if not ok:
            print(f"[报告] Allure 环境检查失败：{msg}")
            return 2

    cmd = [sys.executable, "-m", "pytest", *args.targets, *pytest_args]
    print(f"[运行] {' '.join(cmd)}")
    pytest_code = run_command(cmd)

    if report_enabled and not args.allure_only:
        generate_markdown_from_junit(junit_report, markdown_report)

    if run_dir:
        print(f"[报告] 输出目录: {run_dir}")
    if report_enabled and not args.allure_only:
        print(f"[报告] HTML: {html_report}")
        print(f"[报告] Markdown: {markdown_report}")
    if args.allure or args.allure_only:
        print(f"[报告] Allure results: {allure_results}")

    if args.allure and pytest_code == 0:
        allure_single_file = to_bool(project_cfg.get("allure_single_file"), default=True)
        executable = allure_exec or ["allure"]

        history_report_dir = allure_report
        if allure_single_file and run_dir:
            history_report_dir = run_dir / "allure-report-history-cache"

        history_cmd = [
            *executable,
            "generate",
            str(allure_results),
            "-o",
            str(history_report_dir),
            "--clean",
        ]
        print(f"[运行] {' '.join(history_cmd)}")
        history_code = run_command(history_cmd)
        if history_code != 0:
            print("[报告] Allure 报告生成失败，请检查 Java/Allure 安装。")
            return history_code

        persisted = persist_allure_history(report_root, history_report_dir)
        if persisted:
            print(f"[报告] 已更新趋势历史缓存: {report_root / 'allure-history'}")

        if allure_single_file:
            single_file_cmd = [
                *executable,
                "generate",
                str(allure_results),
                "-o",
                str(allure_report),
                "--clean",
                "--single-file",
            ]
            print(f"[运行] {' '.join(single_file_cmd)}")
            single_file_code = run_command(single_file_cmd)
            if single_file_code != 0:
                print("[报告] Allure 单文件报告生成失败，请检查 Allure CLI 版本。")
                return single_file_code

        print(f"[报告] Allure HTML: {allure_report}")

    return pytest_code


if __name__ == "__main__":
    raise SystemExit(main())
