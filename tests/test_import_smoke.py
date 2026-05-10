from __future__ import annotations

import importlib


def test_official_modules_import() -> None:
    modules = [
        "alphascope.cli",
        "alphascope.core.pipeline",
        "alphascope.config.settings",
        "alphascope.storage.database",
        "alphascope.storage.repositories",
        "alphascope.execution.paper_trader",
        "alphascope.execution.live_trader",
        "alphascope.dashboard.app",
        "alphascope.monitoring.runtime_status",
        "alphascope.api.platform_api",
    ]
    for module_name in modules:
        module = importlib.import_module(module_name)
        assert module is not None, module_name
