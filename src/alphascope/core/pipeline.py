"""End-to-end AlphaScope V1 pipeline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from alphascope.external_data.normalizers import canonicalize_asset_symbol, split_binance_symbol

from alphascope.backtest.engine import BacktestEngine
from alphascope.backtest.strategy import ThresholdStrategy
from alphascope.config.settings import settings
from alphascope.continuous_learning import ContinuousLearningManager
from alphascope.core.logger import get_logger
from alphascope.execution import build_trader, log_trader_startup
from alphascope.execution.live_trader import LiveTrader
from alphascope.execution.paper_trader import PaperTrader
from alphascope.features.feature_pipeline import FeaturePipeline
from alphascope.ingestion.market_ingestor import MarketIngestor
from alphascope.ranking.ranker import AssetRanker
from alphascope.ranking.scorer import ensure_score_column, score_assets, score_timeseries
from alphascope.storage.repositories import StorageRepository
from alphascope.universe.builder import BinanceUniverseBuilder

logger = get_logger(__name__)


class AlphaScopePipeline:
    """Orchestrates ingestion, feature generation, ranking, backtesting and trading execution."""

    def __init__(self, repository: StorageRepository | None = None) -> None:
        self.repository = repository or StorageRepository()
        self.ingestor = MarketIngestor(repository=self.repository)
        self.feature_pipeline = FeaturePipeline(repository=self.repository)
        self.ranker = AssetRanker()
        self.universe_builder = BinanceUniverseBuilder()
        self.continuous_learning = ContinuousLearningManager(repository=self.repository)

    def ingest_market(self, symbols: list[str], intervals: list[str], limit: int) -> list[dict[str, object]]:
        results = self.ingestor.ingest(symbols=symbols, intervals=intervals, limit=limit)
        return [{"symbol": result.symbol, "interval": result.interval, "rows": result.rows} for result in results]

    def build_features(self, symbols: list[str], interval: str) -> pd.DataFrame:
        frames = [self.feature_pipeline.build_for_symbol(symbol=symbol, interval=interval) for symbol in symbols]
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    def rank_assets(self, symbols: list[str], interval: str) -> pd.DataFrame:
        cross_section = self._build_rank_cross_section(symbols=symbols, interval=interval)
        ranking = self.ranker.rank(cross_section)
        self.repository.save_ranking(ranking, interval=interval)
        return ranking

    def explain_ranking(self, symbols: list[str], interval: str) -> pd.DataFrame:
        """Return the ranking dataset with intermediate components and weighted contributions."""
        cross_section = self._build_rank_cross_section(symbols=symbols, interval=interval)
        if cross_section.empty:
            return cross_section
        if settings.ranking_mode in {"hybrid", "hybrid_with_news"} and "news_score" not in cross_section.columns:
            cross_section = self._attach_news_scores(cross_section)
        explained = ensure_score_column(score_assets(cross_section))
        if "heuristic_score" not in explained.columns:
            explained["heuristic_score"] = explained["score"]
        explained["heuristic_contribution"] = explained["heuristic_score"].astype(float) * settings.ranking_heuristic_weight
        if "ml_probability" in explained.columns:
            explained["ml_contribution"] = explained["ml_probability"].astype(float) * settings.ranking_ml_weight
        if "news_score" in explained.columns:
            explained["news_contribution"] = explained["news_score"].astype(float) * settings.ranking_news_weight
        explained = explained.sort_values(["score", "momentum"], ascending=[False, False]).reset_index(drop=True)
        explained["rank"] = range(1, len(explained) + 1)
        return explained

    def _build_rank_cross_section(self, symbols: list[str], interval: str) -> pd.DataFrame:
        latest_rows = []
        for symbol in symbols:
            features = self.repository.get_features(symbol=symbol, interval=interval)
            if features.empty:
                features = self.feature_pipeline.build_for_symbol(symbol=symbol, interval=interval)
            if not features.empty:
                latest_rows.append(features.sort_values("timestamp").iloc[[-1]])
        cross_section = pd.concat(latest_rows, ignore_index=True) if latest_rows else pd.DataFrame()
        if not cross_section.empty and settings.ranking_mode in {"ml", "hybrid", "hybrid_with_news"} and settings.market_model_path.exists():
            from alphascope.ml.inference import MarketModelInference

            ml_scored = MarketModelInference(repository=self.repository).predict_frame(cross_section)
            if not ml_scored.empty and "ml_probability" in ml_scored.columns:
                cross_section["ml_probability"] = ml_scored["ml_probability"].values
        if not cross_section.empty and settings.ranking_mode in {"hybrid", "hybrid_with_news"}:
            cross_section = self._attach_news_scores(cross_section)
        return cross_section

    def backtest(self, symbol: str, interval: str) -> dict[str, pd.DataFrame | dict[str, float]]:
        candles = self.repository.get_candles(symbol=symbol, interval=interval)
        features = self.repository.get_features(symbol=symbol, interval=interval)
        if features.empty:
            features = self.feature_pipeline.build_for_symbol(symbol=symbol, interval=interval)
        scored = ensure_score_column(score_timeseries(features))
        dataset = candles.merge(scored[["timestamp", "symbol", "score"]], on=["timestamp", "symbol"], how="inner")
        signal_frame = ThresholdStrategy(
            buy_threshold=settings.rank_buy_threshold,
            sell_threshold=settings.rank_sell_threshold,
        ).generate_signals(dataset)
        return BacktestEngine(
            initial_cash=settings.backtest_initial_cash,
            fee_rate=settings.backtest_fee_rate,
        ).run(signal_frame)

    def paper_trade(self, symbols: list[str], interval: str) -> dict[str, object]:
        ranking = self.rank_assets(symbols=symbols, interval=interval)
        return self.execute_trading_cycle(ranking=ranking, symbols=symbols, interval=interval, force_paper=True)

    def execute_trading_cycle(
        self,
        *,
        ranking: pd.DataFrame,
        symbols: list[str],
        interval: str,
        force_paper: bool = False,
    ) -> dict[str, object]:
        latest_prices: dict[str, float] = {}
        for symbol in symbols:
            candles = self.repository.get_candles(symbol=symbol, interval=interval)
            if not candles.empty:
                latest_prices[symbol] = float(candles.sort_values("timestamp").iloc[-1]["close"])
        trader = PaperTrader(repository=self.repository, initial_cash=settings.paper_initial_cash) if force_paper else build_trader(repository=self.repository)
        log_trader_startup(logger, trader)
        self.continuous_learning.apply_dynamic_thresholds()
        if isinstance(trader, LiveTrader):
            closed = trader.monitor_positions(latest_prices)
            ranking_frame = ranking.copy()
            if not ranking_frame.empty:
                ranking_frame["price"] = ranking_frame["symbol"].map(latest_prices)
                ranking_frame = ranking_frame.loc[ranking_frame["price"].notna()].reset_index(drop=True)
            opened_or_blocked = trader.process_live_signals(ranking_frame)
            snapshot = trader.sync_account()
            opened = [item for item in opened_or_blocked if item.get("status") == "opened"]
            blocked = [item for item in opened_or_blocked if item.get("status") == "blocked"]
            self.continuous_learning.record_cycle_state(
                symbols=symbols,
                interval=interval,
                ranking=ranking_frame if not ranking_frame.empty else ranking,
                latest_prices=latest_prices,
                snapshot=snapshot,
            )
            return {
                "trader": trader.__class__.__name__,
                "mode": settings.live_trading_mode,
                "opened": opened,
                "closed": closed,
                "blocked": blocked,
                "trades": opened + closed,
                "snapshot": snapshot,
            }
        paper_result = trader.run_cycle(ranking=ranking, latest_prices=latest_prices)
        trades = list(paper_result.get("trades", []))
        self.continuous_learning.record_cycle_state(
            symbols=symbols,
            interval=interval,
            ranking=ranking,
            latest_prices=latest_prices,
            snapshot=paper_result.get("snapshot") if isinstance(paper_result.get("snapshot"), dict) else None,
        )
        return {
            "trader": trader.__class__.__name__,
            "mode": "paper",
            "opened": [trade for trade in trades if trade.get("side") == "BUY"],
            "closed": [trade for trade in trades if trade.get("side") == "SELL"],
            "blocked": [],
            "trades": trades,
            "snapshot": paper_result.get("snapshot"),
        }

    def run_pipeline(
        self,
        symbols: list[str] | None,
        interval: str,
        limit: int,
        *,
        use_auto_universe: bool = False,
        universe_path: Path | None = None,
    ) -> dict[str, object]:
        resolved_symbols = self.resolve_symbols(symbols=symbols, use_auto_universe=use_auto_universe, universe_path=universe_path)
        if not resolved_symbols:
            raise ValueError("No symbols available to run the pipeline.")
        ingestion = self.ingest_market(symbols=resolved_symbols, intervals=[interval], limit=limit)
        features = self.build_features(symbols=resolved_symbols, interval=interval)
        ranking = self.rank_assets(symbols=resolved_symbols, interval=interval)
        trading = self.execute_trading_cycle(ranking=ranking, symbols=resolved_symbols, interval=interval)
        self.continuous_learning.maybe_run_retraining(
            symbols=resolved_symbols,
            interval=interval,
            cycle_count=len(self.repository.get_ranking_cycles(interval=interval)),
        )
        logger.info("Pipeline run completed for %s", resolved_symbols)
        return {
            "ingestion": ingestion,
            "feature_rows": int(len(features)),
            "ranking_rows": int(len(ranking)),
            "trades_executed": len(trading["trades"]),
            "selected_trader": trading["trader"],
            "symbols": resolved_symbols,
        }

    def show_news_signals(self, symbols: list[str] | None = None) -> pd.DataFrame:
        """Return aggregated news signals by asset using the same logic as hybrid ranking."""
        return self._load_news_signal_summary(symbols=symbols)

    def resolve_symbols(
        self,
        *,
        symbols: list[str] | None,
        use_auto_universe: bool = False,
        universe_path: Path | None = None,
    ) -> list[str]:
        """Resolve the symbol universe for pipeline execution."""
        if use_auto_universe:
            universe = self.universe_builder.load(path=universe_path)
            if universe.empty or "symbol" not in universe.columns:
                raise ValueError("Automatic universe file is empty or unavailable. Run build-universe first.")
            if "selected" in universe.columns:
                selected = universe.loc[universe["selected"]].copy()
                if not selected.empty:
                    universe = selected
            resolved = [str(symbol).upper() for symbol in universe["symbol"].tolist() if str(symbol).strip()]
            if resolved:
                return resolved
            raise ValueError("Automatic universe did not contain any symbols.")
        return [str(symbol).upper() for symbol in (symbols or []) if str(symbol).strip()]

    def _attach_news_scores(self, cross_section: pd.DataFrame) -> pd.DataFrame:
        summary = self._load_news_signal_summary()
        enriched = cross_section.copy()
        
        # Ensure news_score exists even if summary is empty
        if summary.empty:
            enriched["news_score"] = 0.0
            return enriched

        enriched["canonical_symbol"] = enriched["symbol"].apply(self._canonical_symbol_from_market_symbol)
        enriched = enriched.merge(
            summary.loc[:, ["related_asset", "news_score"]],
            left_on="canonical_symbol",
            right_on="related_asset",
            how="left",
        )
        # Fill missing news scores with 0.0 as requested for "neutral/fail" state
        if "news_score" in enriched.columns:
            enriched["news_score"] = enriched["news_score"].fillna(0.0)
        else:
            enriched["news_score"] = 0.0
            
        enriched = enriched.drop(columns=["related_asset", "canonical_symbol"], errors="ignore")
        return enriched

    def _load_news_signal_summary(self, symbols: list[str] | None = None) -> pd.DataFrame:
        if not settings.scored_news_path.exists():
            return pd.DataFrame()

        try:
            news_frame = pd.read_csv(settings.scored_news_path)
        except Exception as exc:
            logger.warning("Failed to load scored news from %s: %s", settings.scored_news_path, exc)
            return pd.DataFrame()
        
        if news_frame.empty or "related_asset" not in news_frame.columns:
            return pd.DataFrame()

        # Validate columns
        required_cols = ["sentiment_score", "impact_score"]
        for col in required_cols:
            if col not in news_frame.columns:
                news_frame[col] = 0.5 if "sentiment" in col else 0.0

        if "timestamp" in news_frame.columns:
            news_frame["timestamp"] = pd.to_datetime(news_frame["timestamp"], errors="coerce", utc=True)
            if news_frame["timestamp"].notna().any():
                cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=settings.ranking_news_lookback_hours)
                news_frame = news_frame.loc[news_frame["timestamp"].isna() | (news_frame["timestamp"] >= cutoff)].reset_index(drop=True)

        asset_news = news_frame.loc[news_frame["related_asset"].notna()].copy()
        if asset_news.empty:
            return pd.DataFrame()

        asset_news["related_asset"] = asset_news["related_asset"].astype(str).str.upper()
        if symbols:
            allowed_assets = {self._canonical_symbol_from_market_symbol(symbol) for symbol in symbols}
            asset_news = asset_news.loc[asset_news["related_asset"].isin(allowed_assets)].reset_index(drop=True)
        
        if asset_news.empty:
            return pd.DataFrame()

        # Robust numeric conversion
        asset_news["sentiment_score"] = pd.to_numeric(asset_news["sentiment_score"], errors="coerce").fillna(0.5)
        asset_news["impact_score"] = pd.to_numeric(asset_news["impact_score"], errors="coerce").fillna(0.0)
        
        summary = asset_news.groupby("related_asset", as_index=False).agg(
            news_count=("related_asset", "size"),
            avg_sentiment_score=("sentiment_score", "mean"),
            avg_impact_score=("impact_score", "mean"),
            last_news_at=("timestamp", "max"),
        )
        summary["impact_norm"] = summary["avg_impact_score"].clip(lower=0.0, upper=1.0)
        summary["news_score"] = 0.5 + ((summary["avg_sentiment_score"] - 0.5) * summary["impact_norm"])
        return summary.sort_values(["news_score", "news_count"], ascending=[False, False]).reset_index(drop=True)

    @staticmethod
    def _canonical_symbol_from_market_symbol(symbol: str) -> str:
        base_asset, _ = split_binance_symbol(str(symbol).upper())
        return canonicalize_asset_symbol(base_asset)
