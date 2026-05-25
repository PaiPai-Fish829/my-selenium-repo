from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def ui_runtime_settings() -> dict[str, bool]:
    return {
        "screenshot_on_failure": True,
    }
