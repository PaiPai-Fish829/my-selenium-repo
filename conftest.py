from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--test-env",
        action="store",
        default="default",
        help="选择运行环境（映射到 config.yaml 的 environments 节点）",
    )


@pytest.fixture(autouse=True)
def inject_test_env(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    env_name = request.config.getoption("--test-env")
    monkeypatch.setenv("TEST_ENV", env_name)
    yield


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)
