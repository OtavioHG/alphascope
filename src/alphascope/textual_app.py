from __future__ import annotations

from alphascope.config.settings import settings
from alphascope.platform.service import AlphaPlatformService
from alphascope.storage.repositories import StorageRepository


class _FallbackControlCenterApp:
    def run(self) -> None:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        repository = StorageRepository()
        snapshot = repository.get_latest_account_snapshot() or {}
        daily = repository.get_daily_performance() or {}
        ranking = repository.get_latest_ranking(settings.default_interval)

        table = Table(title="AlphaScope Control Center")
        table.add_column("Metric")
        table.add_column("Value")
        table.add_row("Portfolio Value", str(snapshot.get("total_balance", 0.0)))
        table.add_row("Available Cash", str(snapshot.get("free_balance", 0.0)))
        table.add_row("Open Positions", str(snapshot.get("open_positions", 0)))
        table.add_row("Daily PnL", str(daily.get("realized_pnl_pct", 0.0)))
        table.add_row("Win Rate", str(daily.get("win_rate", 0.0)))
        table.add_row("Market Regime", str(ranking.iloc[0]["market_regime"]) if not ranking.empty else "unknown")
        table.add_row("Bot Status", "RUNNING" if not daily.get("paused", False) else "PAUSED")
        console.print(table)


def create_control_center_app():
    try:
        from textual.app import App, ComposeResult
        from textual.containers import Container
        from textual.widgets import Footer, Header, Static
    except Exception:
        return _FallbackControlCenterApp()

    class AlphaScopeControlCenter(App[None]):
        CSS = """
        Screen {
            background: #0f172a;
            color: #e2e8f0;
        }
        #hero {
            background: #111827;
            border: heavy #22c55e;
            padding: 1 2;
            margin: 1;
        }
        .card {
            background: #172033;
            border: round #38bdf8;
            padding: 1;
            margin: 1;
            height: auto;
        }
        """

        BINDINGS = [("q", "quit", "Exit")]

        def compose(self) -> ComposeResult:
            repository = StorageRepository()
            service = AlphaPlatformService()
            snapshot = repository.get_latest_account_snapshot() or {}
            daily = repository.get_daily_performance() or {}
            ranking = repository.get_latest_ranking(settings.default_interval)
            top_regime = str(ranking.iloc[0]["market_regime"]) if not ranking.empty else "unknown"
            yield Header(show_clock=True)
            with Container(id="hero"):
                yield Static("AlphaScope Control Center\nQuantitative Crypto Terminal v2")
            with Container(classes="card"):
                yield Static(
                    "\n".join(
                        [
                            f"Portfolio Value : ${snapshot.get('total_balance', 0.0):.2f}",
                            f"Available Cash : ${snapshot.get('free_balance', 0.0):.2f}",
                            f"Open Positions : {snapshot.get('open_positions', 0)}",
                            f"Daily PnL : {daily.get('realized_pnl_pct', 0.0):+.2%}",
                            f"Win Rate : {daily.get('win_rate', 0.0):.2%}",
                            f"Market Regime : {top_regime}",
                            f"Bot Status : {'RUNNING' if not daily.get('paused', False) else 'PAUSED'}",
                        ]
                    )
                )
            with Container(classes="card"):
                yield Static(
                    "\n".join(
                        [
                            "[1] Dashboard",
                            "[2] Open Positions",
                            "[3] Rankings",
                            "[4] Trading History",
                            "[5] Risk Management",
                            "[6] Strategy Settings",
                            "[7] Telegram Settings",
                            "[8] API Management",
                            "[9] Logs and Errors",
                            "[10] Backtesting",
                            "[11] Model Training",
                            "[12] Market Scanner",
                            "[13] Start Bot",
                            "[14] Stop Bot",
                            "[15] Emergency Sell All",
                            "[16] Exit",
                        ]
                    )
                )
            with Container(classes="card"):
                yield Static(f"Loaded risk profile: {service.config.risk.profile.value}")
            yield Footer()

    return AlphaScopeControlCenter()
