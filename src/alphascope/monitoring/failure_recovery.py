"""Simple operational failure detection and recovery guidance."""

from __future__ import annotations

import os
from dataclasses import asdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from alphascope.config.settings import settings


@dataclass(slots=True)
class RecoveryIssue:
    """Detected operational issue that may require intervention."""

    code: str
    message: str
    severity: str


class FailureRecoveryService:
    """Detect stale runtime artifacts and suggest or apply simple recovery actions."""

    def __init__(
        self,
        *,
        pid_file: Path | None = None,
        heartbeat_file: Path | None = None,
        max_consecutive_errors: int = settings.max_consecutive_errors,
        heartbeat_stale_seconds: int = settings.heartbeat_interval_seconds * 3,
    ) -> None:
        self.pid_file = pid_file or settings.daemon_pid_file
        self.heartbeat_file = heartbeat_file or settings.heartbeat_file
        self.max_consecutive_errors = max_consecutive_errors
        self.heartbeat_stale_seconds = heartbeat_stale_seconds

    def inspect(self, status_payload: dict[str, Any]) -> dict[str, Any]:
        """Inspect runtime status and return issues plus recovery hints."""
        issues: list[RecoveryIssue] = []
        daemon = status_payload.get("daemon", {})
        continuous = status_payload.get("continuous_pipeline", {})
        heartbeat = status_payload.get("heartbeat", {})

        if self.pid_file.exists():
            pid_text = self.pid_file.read_text(encoding="utf-8").strip()
            if not pid_text.isdigit():
                issues.append(
                    RecoveryIssue(
                        code="invalid_pid",
                        message="Pid file is present but does not contain a valid process id.",
                        severity="warning",
                    )
                )
            elif not self._pid_exists(int(pid_text)):
                issues.append(
                    RecoveryIssue(
                        code="stale_pid",
                        message=f"Pid file exists but process {pid_text} is not running.",
                        severity="warning",
                    )
                )

        heartbeat_timestamp = heartbeat.get("timestamp")
        if heartbeat_timestamp:
            try:
                heartbeat_at = datetime.fromisoformat(str(heartbeat_timestamp).replace("Z", "+00:00"))
                if datetime.now(UTC) - heartbeat_at > timedelta(seconds=self.heartbeat_stale_seconds):
                    issues.append(
                        RecoveryIssue(
                            code="stale_heartbeat",
                            message="Heartbeat file is stale and may indicate a stuck daemon.",
                            severity="warning",
                        )
                    )
            except ValueError:
                issues.append(
                    RecoveryIssue(
                        code="invalid_heartbeat",
                        message="Heartbeat timestamp could not be parsed.",
                        severity="warning",
                    )
                )

        consecutive_errors = int(daemon.get("consecutive_errors", 0) or 0)
        continuous_errors = int(continuous.get("errors", 0) or 0)
        if consecutive_errors >= self.max_consecutive_errors or continuous_errors >= self.max_consecutive_errors:
            issues.append(
                RecoveryIssue(
                    code="excessive_errors",
                    message="Runtime exceeded the configured error threshold.",
                    severity="critical",
                )
            )

        if daemon.get("status") == "error":
            issues.append(
                RecoveryIssue(
                    code="daemon_error",
                    message=str(daemon.get("last_error") or "Daemon reported an error state."),
                    severity="critical",
                )
            )

        return {
            "healthy": len(issues) == 0,
            "issues": [asdict(issue) for issue in issues],
            "recommended_actions": self._recommended_actions(issues),
        }

    def recover_stale_pid(self) -> bool:
        """Remove a stale pid file when the referenced process no longer exists."""
        if not self.pid_file.exists():
            return False
        pid_text = self.pid_file.read_text(encoding="utf-8").strip()
        if not pid_text.isdigit():
            self.pid_file.unlink()
            return True
        if self._pid_exists(int(pid_text)):
            return False
        self.pid_file.unlink()
        return True

    @staticmethod
    def _pid_exists(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    @staticmethod
    def _recommended_actions(issues: list[RecoveryIssue]) -> list[str]:
        actions: list[str] = []
        for issue in issues:
            if issue.code == "stale_pid":
                actions.append("Remove the stale pid file or run automated stale pid recovery.")
            elif issue.code == "invalid_pid":
                actions.append("Remove the invalid pid file before restarting the daemon.")
            elif issue.code == "stale_heartbeat":
                actions.append("Inspect daemon responsiveness and restart the daemon if needed.")
            elif issue.code == "excessive_errors":
                actions.append("Review recent logs and reduce runtime load before restarting services.")
            elif issue.code == "daemon_error":
                actions.append("Check daemon status file and restart after fixing the root cause.")
            elif issue.code == "invalid_heartbeat":
                actions.append("Rewrite the heartbeat by restarting the daemon cleanly.")
        return actions
