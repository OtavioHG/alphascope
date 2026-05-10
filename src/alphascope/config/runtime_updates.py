from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from alphascope.config.settings import ROOT_DIR, settings


@dataclass(frozen=True, slots=True)
class RiskProfile:
    max_position_size_pct: float
    max_account_exposure_pct: float
    max_daily_loss_pct: float
    stop_loss_pct: float
    take_profit_pct: float
    trailing_stop_pct: float


RISK_PROFILES: dict[str, RiskProfile] = {
    "conservative": RiskProfile(0.01, 0.05, 0.01, 0.01, 0.02, 0.0075),
    "moderate": RiskProfile(0.02, 0.10, 0.02, 0.015, 0.03, 0.01),
    "aggressive": RiskProfile(0.05, 0.25, 0.05, 0.03, 0.06, 0.02),
}

MODE_ALIASES = {
    "paper": {"live_trading_enabled": False, "live_trading_mode": "paper"},
    "live": {"live_trading_enabled": True, "live_trading_mode": "live"},
    "simulation": {"live_trading_enabled": True, "live_trading_mode": "testnet"},
}


class RuntimeSettingsManager:
    def __init__(self, env_path: Path | None = None) -> None:
        self.env_path = env_path or (ROOT_DIR / ".env")

    def update(self, key: str, value: str, *, persist: bool = True) -> None:
        os.environ[key] = value
        self._apply_runtime_value(key, value)
        if persist:
            self._write_env_key(key, value)

    def set_alerts_enabled(self, enabled: bool, *, persist: bool = False) -> None:
        value = "true" if enabled else "false"
        self.update("TELEGRAM_ENABLED", value, persist=persist)
        self.update("ENABLE_TELEGRAM_ALERTS", value, persist=persist)

    def set_symbols(self, symbols: list[str], *, persist: bool = True) -> list[str]:
        normalized = [symbol.strip().upper() for symbol in symbols if symbol and symbol.strip()]
        self.update("SYMBOLS", ",".join(normalized), persist=persist)
        return normalized

    def add_symbol(self, symbol: str, *, persist: bool = True) -> list[str]:
        normalized = symbol.strip().upper()
        symbols = list(dict.fromkeys([*settings.symbol_list, normalized]))
        return self.set_symbols(symbols, persist=persist)

    def remove_symbol(self, symbol: str, *, persist: bool = True) -> list[str]:
        normalized = symbol.strip().upper()
        symbols = [item for item in settings.symbol_list if item != normalized]
        return self.set_symbols(symbols, persist=persist)

    def set_max_open_trades(self, value: int, *, persist: bool = True) -> int:
        if value <= 0:
            raise ValueError("MAX_OPEN_TRADES must be greater than zero.")
        self.update("MAX_OPEN_TRADES", str(value), persist=persist)
        return value

    def set_mode(self, mode: str, *, persist: bool = True) -> str:
        normalized = mode.strip().lower()
        if normalized not in MODE_ALIASES:
            raise ValueError("Modo invalido. Use live, paper ou simulation.")
        for key, value in MODE_ALIASES[normalized].items():
            env_key = "LIVE_TRADING_ENABLED" if key == "live_trading_enabled" else "LIVE_TRADING_MODE"
            self.update(env_key, str(value).lower() if isinstance(value, bool) else str(value), persist=persist)
        return normalized

    def set_risk_profile(self, profile_name: str, *, persist: bool = True) -> RiskProfile:
        normalized = profile_name.strip().lower()
        if normalized not in RISK_PROFILES:
            raise ValueError("Perfil invalido. Use conservative, moderate ou aggressive.")
        profile = RISK_PROFILES[normalized]
        self.update("MAX_POSITION_SIZE_PCT", str(profile.max_position_size_pct), persist=persist)
        self.update("MAX_ACCOUNT_EXPOSURE_PCT", str(profile.max_account_exposure_pct), persist=persist)
        self.update("MAX_DAILY_LOSS_PCT", str(profile.max_daily_loss_pct), persist=persist)
        self.update("STOP_LOSS_PCT", str(profile.stop_loss_pct), persist=persist)
        self.update("TAKE_PROFIT_PCT", str(profile.take_profit_pct), persist=persist)
        self.update("TRAILING_STOP_PCT", str(profile.trailing_stop_pct), persist=persist)
        self.update("RISK_PROFILE", normalized, persist=persist)
        return profile

    def current_mode_label(self) -> str:
        if not settings.live_trading_enabled or settings.live_trading_mode == "paper":
            return "paper"
        if settings.live_trading_mode == "live":
            return "live"
        return "simulation"

    def _apply_runtime_value(self, key: str, value: str) -> None:
        key_upper = key.upper()
        if key_upper in {"TELEGRAM_ENABLED", "ENABLE_TELEGRAM_ALERTS", "LIVE_TRADING_ENABLED"}:
            parsed: Any = value.strip().lower() in {"1", "true", "yes", "on"}
        elif key_upper in {"MAX_OPEN_TRADES"}:
            parsed = int(value)
        elif key_upper in {
            "MAX_POSITION_SIZE_PCT",
            "MAX_ACCOUNT_EXPOSURE_PCT",
            "MAX_DAILY_LOSS_PCT",
            "STOP_LOSS_PCT",
            "TAKE_PROFIT_PCT",
            "TRAILING_STOP_PCT",
        }:
            parsed = float(value)
        else:
            parsed = value
        attr_map = {
            "TELEGRAM_ENABLED": "telegram_enabled",
            "ENABLE_TELEGRAM_ALERTS": "enable_telegram_alerts",
            "LIVE_TRADING_ENABLED": "live_trading_enabled",
            "LIVE_TRADING_MODE": "live_trading_mode",
            "SYMBOLS": "symbols",
            "MAX_OPEN_TRADES": "max_open_trades",
            "MAX_POSITION_SIZE_PCT": "max_position_size_pct",
            "MAX_ACCOUNT_EXPOSURE_PCT": "max_account_exposure_pct",
            "MAX_DAILY_LOSS_PCT": "max_daily_loss_pct",
            "STOP_LOSS_PCT": "stop_loss_pct",
            "TAKE_PROFIT_PCT": "take_profit_pct",
            "TRAILING_STOP_PCT": "trailing_stop_pct",
            "RISK_PROFILE": "risk_profile",
        }
        attr_name = attr_map.get(key_upper)
        if attr_name is not None:
            object.__setattr__(settings, attr_name, parsed)

    def _write_env_key(self, key: str, value: str) -> None:
        lines = []
        if self.env_path.exists():
            lines = self.env_path.read_text(encoding="utf-8").splitlines()
        updated = False
        new_lines: list[str] = []
        for line in lines:
            if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
                new_lines.append(line)
                continue
            current_key, _ = line.split("=", 1)
            if current_key.strip() != key:
                new_lines.append(line)
                continue
            new_lines.append(f"{key}={value}")
            updated = True
        if not updated:
            new_lines.append(f"{key}={value}")
        self.env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
