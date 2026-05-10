from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from alphascope.core.logger import JsonLogFormatter, PlainLogFormatter
from alphascope.config.settings import settings


class BraceStyleAdapter(logging.LoggerAdapter):
    def log(self, level: int, msg: object, *args: Any, **kwargs: Any) -> None:
        if not self.isEnabledFor(level):
            return
        if args:
            try:
                msg = str(msg).format(*args)
                args = ()
            except Exception:
                pass
        super().log(level, msg, *args, **kwargs)



def build_component_logger(component: str, log_path: Path) -> BraceStyleAdapter:
    logger = logging.getLogger(f"alphascope.{component}")
    formatter = JsonLogFormatter() if settings.log_format == "json" else PlainLogFormatter()
    sink_id = f"{component}:{log_path}"
    configured = getattr(build_component_logger, "_configured", set())
    if sink_id not in configured:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(settings.log_level)
        logger.propagate = True
        configured.add(sink_id)
        setattr(build_component_logger, "_configured", configured)
    return BraceStyleAdapter(logger, {"component": component})
