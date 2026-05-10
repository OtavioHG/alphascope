from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from alphascope.config.settings import settings


@dataclass(slots=True)
class RuntimeCheck:
    name: str
    ok: bool
    detail: str
    severity: str = "error"


class RuntimeValidator:
    """Run non-destructive environment and runtime readiness checks."""

    def checks(self) -> list[RuntimeCheck]:
        checks: list[RuntimeCheck] = [
            RuntimeCheck("sqlite_path", settings.sqlite_path.parent.exists(), f"sqlite_path={settings.sqlite_path}"),
            RuntimeCheck("logs_dir", settings.log_dir.exists(), f"log_dir={settings.log_dir}"),
            RuntimeCheck("api_key_secret", settings.api_key_secret not in {"", "change-me-before-production", "local-dev-secret-change-me"}, "API_KEY_SECRET definido", severity="warning"),
            RuntimeCheck("jwt_secret", settings.jwt_secret not in {"", "change-me-before-production", "local-dev-secret-change-me"}, "JWT_SECRET definido", severity="warning"),
            RuntimeCheck("dockerfile", Path("Dockerfile").exists(), "Dockerfile presente", severity="warning"),
            RuntimeCheck("docker_compose", Path("docker-compose.yml").exists(), "docker-compose.yml presente", severity="warning"),
            RuntimeCheck("multi_agent_learning", settings.continuous_learning_enabled and settings.multi_agent_train_on_runtime_cycle, "Treino multiagente contínuo habilitado no runtime", severity="warning"),
            RuntimeCheck("multi_agent_thresholds", settings.dynamic_thresholds_enabled and settings.multi_agent_apply_dynamic_thresholds_on_runtime_cycle, "Ajuste dinâmico de thresholds habilitado no runtime", severity="warning"),
            RuntimeCheck("multi_agent_models", all(bool(config.get("active")) for config in settings.multi_agent_model_registry.values()), f"modelos={json.dumps(settings.multi_agent_model_registry, ensure_ascii=False)}", severity="warning"),
        ]
        if settings.llm_enable_external:
            openrouter_present = bool(settings.openrouter_api_key)
            checks.append(
                RuntimeCheck(
                    "openrouter_api_key",
                    openrouter_present,
                    "OPENROUTER_API_KEY presente para uso dos modelos externos"
                    if openrouter_present
                    else "OPENROUTER_API_KEY ausente; runtime ficará em fallback local até a chave ser configurada",
                    severity="warning",
                )
            )
        if settings.live_trading_mode == "live":
            checks.append(
                RuntimeCheck(
                    "live_guard",
                    settings.live_allow_live_mode and settings.live_kill_switch_enabled,
                    "Live mode requer LIVE_ALLOW_LIVE_MODE=true e kill switch habilitado",
                )
            )
        if settings.live_trading_enabled:
            checks.append(
                RuntimeCheck(
                    "binance_credentials",
                    bool(settings.binance_api_key and settings.binance_api_secret),
                    "Credenciais Binance presentes para live/testnet",
                )
            )
        return checks

    def run(self) -> dict[str, Any]:
        checks = self.checks()
        failures = [check for check in checks if not check.ok and check.severity == "error"]
        warnings = [check for check in checks if not check.ok and check.severity == "warning"]
        return {
            "ok": not failures,
            "failures": [asdict(check) for check in failures],
            "warnings": [asdict(check) for check in warnings],
            "checks": [asdict(check) for check in checks],
        }


class BackupService:
    def __init__(self, database_path: Path | None = None, backup_dir: Path | None = None) -> None:
        self.database_path = database_path or settings.sqlite_path
        self.backup_dir = backup_dir or Path("artifacts/backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self) -> Path:
        if not self.database_path.exists():
            raise FileNotFoundError(f"Database not found: {self.database_path}")
        timestamp = settings.daemon_status_file.parent.name  # deterministic enough for tests? no
        del timestamp
        from datetime import UTC, datetime
        backup_path = self.backup_dir / f"{self.database_path.stem}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}{self.database_path.suffix}"
        shutil.copy2(self.database_path, backup_path)
        return backup_path

    def metadata(self) -> str:
        return json.dumps({"database_path": str(self.database_path), "backup_dir": str(self.backup_dir)}, ensure_ascii=False)
