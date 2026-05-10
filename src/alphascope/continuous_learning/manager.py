from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pandas as pd

from alphascope.alerts import AlertDispatcher
from alphascope.config.settings import settings
from alphascope.continuous_learning.model_lifecycle import ModelLifecycleManager
from alphascope.ml.train_market_model import MarketModelTrainer
from alphascope.storage.repositories import StorageRepository


class ContinuousLearningManager:
    def __init__(
        self,
        repository: StorageRepository | None = None,
        alert_dispatcher: AlertDispatcher | None = None,
    ) -> None:
        self.repository = repository or StorageRepository()
        self.alert_dispatcher = alert_dispatcher or AlertDispatcher()
        self.model_lifecycle = ModelLifecycleManager(repository=self.repository)
        self.model_trainer = MarketModelTrainer(registry=None)

    def record_cycle_state(
        self,
        *,
        symbols: list[str],
        interval: str,
        ranking: pd.DataFrame,
        latest_prices: dict[str, float],
        snapshot: dict[str, Any] | None,
    ) -> None:
        if not settings.continuous_learning_enabled:
            return
        timestamp = datetime.now(UTC)
        ranking_rows: list[dict[str, object]] = []
        signal_rows: list[dict[str, object]] = []
        prediction_rows: list[dict[str, object]] = []
        market_snapshots: list[dict[str, object]] = []
        feature_snapshots: list[dict[str, object]] = []
        cycle_id = f"{interval}:{timestamp.isoformat()}:{uuid4().hex[:8]}"
        account_snapshot = self.repository.get_latest_account_snapshot() or {}
        total_equity = float((snapshot or {}).get("equity") or account_snapshot.get("total_balance") or 0.0)
        available_balance = float((snapshot or {}).get("cash") or account_snapshot.get("free_balance") or 0.0)
        open_positions_frame = self.repository.get_open_positions()
        for symbol in symbols:
            features = self.repository.get_features(symbol=symbol, interval=interval)
            latest_feature = features.sort_values("timestamp").iloc[-1].to_dict() if not features.empty else {}
            ranking_row = (
                ranking.loc[ranking["symbol"] == symbol].iloc[-1].to_dict()
                if not ranking.empty and "symbol" in ranking.columns and (ranking["symbol"] == symbol).any()
                else {}
            )
            current_price = float(latest_prices.get(symbol) or latest_feature.get("close") or 0.0)
            prev_close = float(latest_feature.get("ma_short") or current_price or 0.0)
            price_change_1h = ((current_price / prev_close) - 1.0) if current_price > 0 and prev_close > 0 else 0.0
            market_snapshots.append(
                {
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "timeframe": interval,
                    "current_price": current_price,
                    "price_change_1h": price_change_1h,
                    "price_change_24h": float(latest_feature.get("return_pct", 0.0)),
                    "volume": float(latest_feature.get("avg_volume", 0.0)),
                    "relative_volume": float(latest_feature.get("relative_volume", 0.0)),
                    "volatility": float(latest_feature.get("volatility", 0.0)),
                    "rsi": float(latest_feature.get("rsi", 0.0)),
                    "macd": 0.0,
                    "bollinger_upper": 0.0,
                    "bollinger_lower": 0.0,
                    "sma20": float(latest_feature.get("ma_short", 0.0)),
                    "sma50": float(latest_feature.get("ma_long", 0.0)),
                    "ema9": float(latest_feature.get("ma_short", 0.0)),
                    "ema21": float(latest_feature.get("ma_long", 0.0)),
                    "atr": float(latest_feature.get("volatility", 0.0)),
                    "news_score": float(ranking_row.get("news_score", 0.0)),
                    "fear_greed_score": 0.0,
                    "ranking_score": float(ranking_row.get("score", 0.0)),
                    "ml_score": float(ranking_row.get("ml_probability", 0.0)),
                    "heuristic_score": float(ranking_row.get("heuristic_score", ranking_row.get("score", 0.0))),
                    "confidence_score": self._confidence_from_scores(ranking_row),
                    "current_position": float(
                        open_positions_frame.loc[open_positions_frame["symbol"] == symbol, "quantity"].sum()
                    ) if not open_positions_frame.empty and "symbol" in open_positions_frame.columns else 0.0,
                    "available_balance": available_balance,
                    "total_equity": total_equity,
                    "market_cap": 0.0,
                    "btc_dominance": 0.0,
                    "sentiment_score": float(ranking_row.get("news_score", 0.0)),
                    "snapshot_json": {"feature": latest_feature, "ranking": ranking_row},
                }
            )
            if latest_feature:
                feature_snapshots.append(
                    {
                        "timestamp": timestamp,
                        "symbol": symbol,
                        "timeframe": interval,
                        "feature_version": "v1",
                        "features_json": latest_feature,
                    }
                )
            if ranking_row:
                ranking_rows.append(
                    {
                        "cycle_id": cycle_id,
                        "timestamp": timestamp,
                        "symbol": symbol,
                        "timeframe": interval,
                        "rank": int(ranking_row.get("rank", 0) or 0),
                        "ranking_score": float(ranking_row.get("score", 0.0)),
                        "heuristic_score": float(ranking_row.get("heuristic_score", ranking_row.get("score", 0.0))),
                        "ml_score": float(ranking_row.get("ml_probability", 0.0)),
                        "news_score": float(ranking_row.get("news_score", 0.0)),
                        "confidence_score": self._confidence_from_scores(ranking_row),
                        "payload_json": ranking_row,
                    }
                )
                signal_type = "hold_candidate"
                score = float(ranking_row.get("score", 0.0))
                if score >= settings.rank_buy_threshold:
                    signal_type = "buy_candidate"
                elif score <= settings.rank_sell_threshold:
                    signal_type = "sell_candidate"
                signal_rows.append(
                    {
                        "timestamp": timestamp,
                        "symbol": symbol,
                        "timeframe": interval,
                        "signal_type": signal_type,
                        "signal_strength": score,
                        "confidence_score": self._confidence_from_scores(ranking_row),
                        "ranking_score": score,
                        "payload_json": ranking_row,
                    }
                )
                ml_score = float(ranking_row.get("ml_probability", 0.0))
                hold_probability = max(0.0, 1.0 - abs((ml_score * 2.0) - 1.0))
                prediction_rows.append(
                    {
                        "timestamp": timestamp,
                        "symbol": symbol,
                        "timeframe": interval,
                        "model_name": "market_model",
                        "model_version": self._current_model_version(),
                        "prediction_score": ml_score,
                        "confidence_score": self._confidence_from_scores(ranking_row),
                        "buy_probability": ml_score,
                        "sell_probability": max(0.0, 1.0 - ml_score),
                        "hold_probability": hold_probability,
                        "predicted_label": "buy" if ml_score >= 0.5 else "sell",
                        "ranking_score": score,
                        "heuristic_score": float(ranking_row.get("heuristic_score", score)),
                        "news_score": float(ranking_row.get("news_score", 0.0)),
                        "features_json": latest_feature,
                    }
                )
        self.repository.save_market_snapshots(market_snapshots)
        self.repository.save_feature_snapshots(feature_snapshots)
        self.repository.save_ranking_history(ranking_rows)
        self.repository.save_signal_history(signal_rows)
        self.repository.save_model_predictions(prediction_rows)
        self.repository.save_portfolio_analytics_snapshot(self._build_portfolio_analytics_snapshot(snapshot))

    def maybe_run_retraining(self, *, symbols: list[str], interval: str, cycle_count: int) -> dict[str, Any] | None:
        if not settings.auto_retrain_enabled:
            return None
        recent_trades = self.repository.get_trade_history(status="CLOSED", limit=max(settings.auto_retrain_min_trades, 100))
        retraining_runs = self.repository.get_retraining_runs(limit=1)
        latest_run_time = None if retraining_runs.empty else pd.to_datetime(retraining_runs.iloc[0]["started_at"], utc=True)
        hours_since_last = 10**6 if latest_run_time is None else (pd.Timestamp.now(tz="UTC") - latest_run_time).total_seconds() / 3600.0
        win_rate = float(recent_trades["was_successful"].mean()) if not recent_trades.empty and "was_successful" in recent_trades.columns else 1.0
        drawdown = abs(float(recent_trades["max_drawdown_during_trade"].min())) if not recent_trades.empty and "max_drawdown_during_trade" in recent_trades.columns else 0.0
        model_versions = self.repository.get_model_versions(stage="production", limit=1)
        current_score = float(model_versions.iloc[0]["average_score"]) if not model_versions.empty else 1.0
        should_retrain = (
            len(recent_trades) >= settings.auto_retrain_min_trades
            and (
                hours_since_last >= settings.auto_retrain_interval_hours
                or win_rate < settings.auto_retrain_min_win_rate
                or drawdown > settings.auto_retrain_max_drawdown
                or current_score < settings.auto_retrain_min_model_score
            )
        )
        if not should_retrain:
            return None
        trigger_reason = "trade_count"
        if win_rate < settings.auto_retrain_min_win_rate:
            trigger_reason = "win_rate_drop"
        elif drawdown > settings.auto_retrain_max_drawdown:
            trigger_reason = "drawdown_spike"
        elif current_score < settings.auto_retrain_min_model_score:
            trigger_reason = "model_score_drop"
        elif hours_since_last >= settings.auto_retrain_interval_hours:
            trigger_reason = "time_interval"
        run_id = f"retrain_{uuid4().hex}"
        self.repository.save_retraining_run(
            {
                "run_id": run_id,
                "started_at": datetime.now(UTC),
                "finished_at": None,
                "status": "started",
                "trigger_reason": trigger_reason,
                "cycle_count": cycle_count,
                "trade_count": len(recent_trades),
                "win_rate_before": win_rate,
                "drawdown_before": drawdown,
                "model_score_before": current_score,
                "selected_model_name": None,
                "selected_model_version": None,
                "candidate_count": 0,
                "promoted": False,
                "rollback_triggered": False,
                "metrics_json": {},
                "notes_json": {"symbols": symbols, "interval": interval},
            }
        )
        self.alert_dispatcher.dispatch_raw("retraining_started", "Retraining started", f"Retraining iniciado | motivo={trigger_reason}", {"run_id": run_id})
        result = self.model_trainer.train(symbols=symbols, interval=interval)
        lifecycle = self.model_lifecycle.register_candidate(
            model_name=str(result["best_model_name"]),
            metrics=dict(result["best_metrics"]),
            artifact_path=str(result["artifact_path"]),
            metadata_path=str(result["metadata_path"]),
            feature_columns=list(result.get("feature_columns", [])) or [],
            dataset_used=f"market_dataset:{interval}",
            params={},
            trade_count=len(recent_trades),
            candle_count=0,
        )
        self.repository.update_retraining_run(
            run_id,
            {
                "finished_at": datetime.now(UTC),
                "status": "completed",
                "selected_model_name": str(result["best_model_name"]),
                "selected_model_version": lifecycle["version"],
                "candidate_count": int(len(result["leaderboard"])),
                "promoted": bool(lifecycle["promoted"]),
                "rollback_triggered": bool(lifecycle["rollback_triggered"]),
                "metrics_json": {
                    "best_metrics": result["best_metrics"],
                    "leaderboard": result["leaderboard"].to_dict(orient="records"),
                },
                "notes_json": lifecycle,
            },
        )
        if lifecycle["promoted"]:
            self.alert_dispatcher.dispatch_raw(
                "model_promoted",
                "New production model",
                f"Novo modelo promovido | {result['best_model_name']} {lifecycle['version']}",
                lifecycle,
            )
        elif lifecycle["rollback_triggered"]:
            self.alert_dispatcher.dispatch_raw(
                "model_rollback",
                "Model rollback",
                f"Rollback automático preservado | candidato {result['best_model_name']} rejeitado",
                lifecycle,
            )
        self.alert_dispatcher.dispatch_raw(
            "retraining_completed",
            "Retraining completed",
            f"Retraining concluído | melhor={result['best_model_name']} | promovido={lifecycle['promoted']}",
            {"run_id": run_id, **lifecycle},
        )
        return {"run_id": run_id, **lifecycle}

    def apply_dynamic_thresholds(self) -> dict[str, float] | None:
        if not settings.dynamic_thresholds_enabled:
            return None
        snapshots = self.repository.get_market_snapshots(limit=50)
        recent_trades = self.repository.get_trade_history(status="CLOSED", limit=20)
        avg_volatility = float(snapshots["volatility"].mean()) if not snapshots.empty and "volatility" in snapshots.columns else 0.0
        recent_win_rate = float(recent_trades["was_successful"].mean()) if not recent_trades.empty and "was_successful" in recent_trades.columns else 0.5
        buy_threshold = min(0.9, max(0.35, settings.rank_buy_threshold + (0.05 if avg_volatility > 0.04 else -0.02 if recent_win_rate > 0.6 else 0.0)))
        sell_threshold = min(0.5, max(0.05, settings.rank_sell_threshold + (0.02 if avg_volatility > 0.04 else 0.0)))
        confidence = min(0.95, max(0.35, settings.min_confidence_score + (0.05 if avg_volatility > 0.04 else -0.02 if recent_win_rate > 0.6 else 0.0)))
        stop_loss = min(0.08, max(0.01, settings.stop_loss_pct + (0.005 if avg_volatility > 0.04 else -0.002)))
        trailing = min(0.06, max(0.005, settings.trailing_stop_pct + (0.004 if avg_volatility > 0.04 else -0.001)))
        take_profit = min(0.15, max(0.01, settings.take_profit_pct + (0.005 if recent_win_rate > 0.6 else 0.0)))
        object.__setattr__(settings, "rank_buy_threshold", buy_threshold)
        object.__setattr__(settings, "rank_sell_threshold", sell_threshold)
        object.__setattr__(settings, "min_confidence_score", confidence)
        object.__setattr__(settings, "stop_loss_pct", stop_loss)
        object.__setattr__(settings, "trailing_stop_pct", trailing)
        object.__setattr__(settings, "take_profit_pct", take_profit)
        payload = {
            "rank_buy_threshold": buy_threshold,
            "rank_sell_threshold": sell_threshold,
            "min_confidence_score": confidence,
            "stop_loss_pct": stop_loss,
            "trailing_stop_pct": trailing,
            "take_profit_pct": take_profit,
        }
        self.repository.save_audit_event(
            {
                "timestamp": datetime.now(UTC),
                "action": "dynamic_threshold_update",
                "actor": "continuous_learning",
                "source": "runtime",
                "target": "trading_thresholds",
                "payload_json": payload,
            }
        )
        return payload

    @staticmethod
    def _confidence_from_scores(row: dict[str, Any]) -> float:
        ml_score = float(row.get("ml_probability", row.get("score", 0.0)) or 0.0)
        heuristic = float(row.get("heuristic_score", row.get("score", 0.0)) or 0.0)
        return max(0.0, min(1.0, (abs(ml_score - 0.5) * 2 * 0.6) + (heuristic * 0.4)))

    def _build_portfolio_analytics_snapshot(self, snapshot: dict[str, Any] | None) -> dict[str, Any]:
        trade_history = self.repository.get_trade_history(status="CLOSED", limit=200)
        pnl = trade_history["pnl"].astype(float) if not trade_history.empty and "pnl" in trade_history.columns else pd.Series(dtype=float)
        wins = pnl[pnl > 0].sum() if not pnl.empty else 0.0
        losses = abs(pnl[pnl < 0].sum()) if not pnl.empty else 0.0
        profit_factor = float(wins / losses) if losses > 0 else float(wins) if wins > 0 else 0.0
        win_rate = float((trade_history["was_successful"].astype(float).mean())) if not trade_history.empty and "was_successful" in trade_history.columns else 0.0
        sharpe = 0.0
        if not pnl.empty and pnl.std(ddof=0) > 0:
            sharpe = float((pnl.mean() / pnl.std(ddof=0)) * (len(pnl) ** 0.5))
        drawdown = abs(float(trade_history["max_drawdown_during_trade"].min())) if not trade_history.empty and "max_drawdown_during_trade" in trade_history.columns else 0.0
        open_trades = len(self.repository.get_trade_history(status="OPEN", limit=500))
        closed_trades = len(trade_history)
        snapshot = snapshot or {}
        return {
            "timestamp": datetime.now(UTC),
            "mode": settings.live_trading_mode if settings.live_trading_enabled else "paper",
            "total_equity": float(snapshot.get("equity") or snapshot.get("total_balance") or 0.0),
            "available_balance": float(snapshot.get("cash") or snapshot.get("free_balance") or 0.0),
            "drawdown": drawdown,
            "sharpe_ratio": sharpe,
            "profit_factor": profit_factor,
            "win_rate": win_rate,
            "open_trades": open_trades,
            "closed_trades": closed_trades,
            "payload_json": {
                "snapshot": snapshot,
                "computed_at": datetime.now(UTC).isoformat(),
            },
        }

    def _current_model_version(self) -> str:
        versions = self.repository.get_model_versions(stage="production", limit=1)
        if versions.empty:
            return "unknown"
        return str(versions.iloc[0]["version"])
