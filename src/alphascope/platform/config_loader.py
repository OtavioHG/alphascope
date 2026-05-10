from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from alphascope.config.settings import settings
from alphascope.platform.config_models import PlatformConfig, RiskProfile


class PlatformConfigLoader:
    """Load layered platform configuration from repo-local JSON files."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path.cwd()

    def load(self, *, risk_profile: RiskProfile | str | None = None, strategy_name: str | None = None) -> PlatformConfig:
        base = PlatformConfig()
        config_root = self.root / base.paths.config_root
        resolved_profile = risk_profile or settings.risk_profile

        merged = base.model_dump()
        for relative_path in self._candidate_files(config_root=config_root, risk_profile=resolved_profile, strategy_name=strategy_name):
            payload = self._read_json(relative_path)
            if payload:
                merged = self._deep_merge(merged, payload)
        return PlatformConfig.model_validate(merged)

    def _candidate_files(
        self,
        *,
        config_root: Path,
        risk_profile: RiskProfile | str | None,
        strategy_name: str | None,
    ) -> list[Path]:
        candidates = [
            config_root / "risk" / "risk_limits.json",
            config_root / "risk" / "position_sizing.json",
            config_root / "risk" / "daily_limits.json",
            config_root / "telegram" / "alerts.json",
            config_root / "telegram" / "commands.json",
            config_root / "telegram" / "permissions.json",
        ]
        if strategy_name:
            candidates.append(config_root / "strategies" / f"{strategy_name}.json")
        if risk_profile:
            candidates.append(config_root / "strategies" / f"{str(risk_profile)}.json")
        return candidates

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @classmethod
    def _deep_merge(cls, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        merged = dict(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = cls._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged
