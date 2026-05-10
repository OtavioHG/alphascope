from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from alphascope.analysis.asset_behavior import AssetBehaviorAnalyzer
from alphascope.analysis.cross_asset_analysis import CrossAssetAnalyzer
from alphascope.analysis.sector_rotation import SectorRotationAnalyzer
from alphascope.data_management.data_lineage import DataLineageTracker
from alphascope.data_management.dataset_versioning import DatasetVersionManager
from alphascope.data_management.validation import DataValidator
from alphascope.discovery.alpha_ranker import AlphaRanker
from alphascope.discovery.anomaly_detection import AnomalyDetector
from alphascope.discovery.regime_detection import RegimeDetector
from alphascope.discovery.signal_mining import SignalMiner
from alphascope.discovery.strategy_generator import StrategyGenerator
from alphascope.experiments.experiment_manager import ExperimentManager
from alphascope.meta_learning.feature_selector import FeatureSelector
from alphascope.meta_learning.meta_features import MetaFeatureBuilder
from alphascope.meta_learning.strategy_meta_model import StrategyMetaModel
from alphascope.reports.alpha_reports import AlphaReportBuilder
from alphascope.reports.strategy_reports import StrategyReportBuilder
from alphascope.research.experiment_tracker import ExperimentTracker
from alphascope.research.hypothesis_engine import HypothesisEngine
from alphascope.storage.database import StorageSessionLocal
from alphascope.storage.migrations.manager import MigrationManager
from alphascope.storage.models.production import (
    AlphaReportRecord,
    AnomalyDetectionRecord,
    DiscoveryRankingRecord,
    ExperimentRunRecord,
    MinedSignalRecord,
    RegimeDetectionRecord,
    StrategyCandidateRecord,
)
from alphascope.models.model_registry_store import ModelRegistryStore


class ResearchPipeline:
    def __init__(
        self,
        dataset_path: str = "data/processed/dataset.csv",
        research_dir: str = "data/processed/research",
        discovery_dir: str = "data/processed/discovery",
        experiments_dir: str = "data/processed/experiments",
        reports_dir: str = "data/processed/reports",
    ):
        self.dataset_path = Path(dataset_path)
        self.research_dir = Path(research_dir)
        self.discovery_dir = Path(discovery_dir)
        self.experiments_dir = Path(experiments_dir)
        self.reports_dir = Path(reports_dir)
        for directory in [self.research_dir, self.discovery_dir, self.experiments_dir, self.reports_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        MigrationManager().upgrade()

        self.regime_detector = RegimeDetector()
        self.anomaly_detector = AnomalyDetector()
        self.signal_miner = SignalMiner()
        self.strategy_generator = StrategyGenerator()
        self.alpha_ranker = AlphaRanker()
        self.feature_selector = FeatureSelector()
        self.meta_builder = MetaFeatureBuilder()
        self.meta_model = StrategyMetaModel()
        self.experiment_manager = ExperimentManager(output_dir=str(self.experiments_dir))
        self.experiment_tracker = ExperimentTracker(output_dir=str(self.experiments_dir))
        self.hypothesis_engine = HypothesisEngine()
        self.asset_behavior = AssetBehaviorAnalyzer()
        self.cross_asset = CrossAssetAnalyzer()
        self.sector_rotation = SectorRotationAnalyzer()
        self.alpha_report = AlphaReportBuilder(output_dir=str(self.reports_dir))
        self.strategy_report = StrategyReportBuilder(output_dir=str(self.reports_dir))
        self.dataset_versions = DatasetVersionManager()
        self.lineage = DataLineageTracker()
        self.validator = DataValidator()
        self.model_registry = ModelRegistryStore()

    def load_dataset(self) -> pd.DataFrame:
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Dataset not found: {self.dataset_path}")
        dataset = pd.read_csv(self.dataset_path)
        if "timestamp" in dataset.columns:
            dataset["timestamp"] = pd.to_datetime(dataset["timestamp"], errors="coerce", utc=True)
        return dataset.sort_values(["symbol", "timestamp"]).reset_index(drop=True)

    def detect_regimes(self, dataset: pd.DataFrame | None = None) -> pd.DataFrame:
        frame = dataset if dataset is not None else self.load_dataset()
        regimes = self.regime_detector.detect(frame)
        regimes.to_csv(self.discovery_dir / "regimes_detected.csv", index=False)
        return regimes

    def detect_anomalies(self, dataset: pd.DataFrame | None = None) -> pd.DataFrame:
        frame = dataset if dataset is not None else self.load_dataset()
        anomalies = self.anomaly_detector.detect(frame)
        anomalies.to_csv(self.discovery_dir / "anomalies_detected.csv", index=False)
        return anomalies

    def mine_signals(self, dataset: pd.DataFrame | None = None) -> pd.DataFrame:
        frame = dataset if dataset is not None else self.load_dataset()
        signals = self.signal_miner.mine(frame)
        signals.to_csv(self.discovery_dir / "mined_signals.csv", index=False)
        return signals

    def generate_strategies(
        self,
        mined_signals: pd.DataFrame | None = None,
        regimes: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        local_signals = mined_signals if mined_signals is not None else self.mine_signals()
        local_regimes = regimes if regimes is not None else self.detect_regimes()
        strategies = self.strategy_generator.generate(local_signals, local_regimes)
        strategies.to_json(self.discovery_dir / "strategy_candidates.json", orient="records", indent=2)
        return strategies

    def rank_alpha(
        self,
        strategies: pd.DataFrame | None = None,
        mined_signals: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        local_strategies = strategies if strategies is not None else self.generate_strategies()
        local_signals = mined_signals if mined_signals is not None else self.mine_signals()
        ranking = self.alpha_ranker.rank(local_strategies, local_signals)
        ranking.to_csv(self.discovery_dir / "discovery_rankings.csv", index=False)
        return ranking

    def run(self) -> dict[str, Any]:
        dataset = self.load_dataset()
        validation = self.validator.validate(dataset)
        dataset_version = self.dataset_versions.register(
            dataset=dataset,
            dataset_name="research_dataset",
            features_used=[column for column in dataset.columns if column not in {"timestamp", "symbol"}],
            temporal_window={
                "start": str(dataset["timestamp"].min()) if "timestamp" in dataset.columns else None,
                "end": str(dataset["timestamp"].max()) if "timestamp" in dataset.columns else None,
            },
        )
        regimes = self.detect_regimes(dataset)
        anomalies = self.detect_anomalies(dataset)
        mined_signals = self.mine_signals(dataset)
        strategies = self.generate_strategies(mined_signals, regimes)
        ranking = self.rank_alpha(strategies, mined_signals)

        candidate_columns = [
            "rsi",
            "macd",
            "macd_signal",
            "bb_upper",
            "bb_lower",
            "sma_20",
            "sma_50",
            "pct_return",
            "volatility",
            "relative_volume",
            "sentiment_score",
            "news_count_window",
            "avg_sentiment_window",
        ]
        selected_features = self.feature_selector.select(dataset, candidate_columns, top_k=5)
        meta_features = self.meta_builder.build(dataset, regimes, anomalies)
        experiment_batch = self.experiment_manager.run_batch(selected_features, regimes, mined_signals)

        for _, row in ranking.head(5).iterrows():
            self.experiment_tracker.track(
                strategy_id=str(row["strategy_id"]),
                feature_set=selected_features,
                target_definition={"future_horizon": 4, "return_threshold": 0.015},
                metrics={
                    "alpha_discovery_score": float(row["alpha_discovery_score"]),
                    "win_rate": float(row["win_rate"]),
                    "sharpe": float(row["sharpe"]),
                },
                promotion_status=str(row["promotion_status"]),
                dataset_hash=str(dataset_version["dataset_hash"]),
                dataset_window=dataset_version["temporal_window"],
                model_name="research_ranker",
                hyperparameters={"top_features": len(selected_features)},
                backtest_summary={},
                experiment_type="alpha_discovery",
            )
            self.lineage.record(
                dataset_hash=str(dataset_version["dataset_hash"]),
                features_used=selected_features,
                model_version="research_ranker_v1",
                strategy_id=str(row["strategy_id"]),
                source="research_pipeline",
            )

        self.model_registry.register(
            model_name="research_ranker",
            model_version="v1",
            hyperparameters={"selected_features": selected_features},
            dataset_hash=str(dataset_version["dataset_hash"]),
            metrics={"ranking_rows": int(len(ranking)), "validation_rows": int(validation["rows"])},
            artifact_path=None,
        )

        asset_behavior = self.asset_behavior.analyze(dataset)
        cross_asset = self.cross_asset.analyze(dataset)
        sector_rotation = self.sector_rotation.analyze(dataset)
        hypotheses = self.hypothesis_engine.generate(regimes, anomalies, ranking, sector_rotation)
        meta_recommendations = self.meta_model.recommend(ranking, regimes)

        self._persist_frame(asset_behavior, self.research_dir / "asset_behavior.csv")
        self._persist_frame(cross_asset.get("correlation", pd.DataFrame()), self.research_dir / "cross_asset_correlation.csv")
        self._persist_frame(cross_asset.get("leaders_followers", pd.DataFrame()), self.research_dir / "leaders_followers.csv")
        self._persist_frame(sector_rotation, self.research_dir / "sector_rotation.csv")
        self._persist_frame(meta_features, self.research_dir / "meta_features.csv")
        self._persist_frame(meta_recommendations, self.research_dir / "strategy_meta_recommendations.csv")
        self._persist_frame(hypotheses, self.research_dir / "hypotheses.csv")
        self._persist_frame(experiment_batch, self.experiments_dir / "experiment_runs.csv")

        alpha_report_paths = self.alpha_report.build(ranking, anomalies, hypotheses)
        strategy_report_paths = self.strategy_report.build(strategies, mined_signals)
        self._persist_relational_outputs(
            regimes=regimes,
            anomalies=anomalies,
            mined_signals=mined_signals,
            strategies=strategies,
            ranking=ranking,
            report_paths={**alpha_report_paths, **strategy_report_paths},
        )
        summary = {
            "regimes_rows": len(regimes),
            "anomalies_rows": len(anomalies),
            "signals_rows": len(mined_signals),
            "strategies_rows": len(strategies),
            "ranking_rows": len(ranking),
            "selected_features": selected_features,
            "dataset_hash": dataset_version["dataset_hash"],
            "validation": validation,
            "reports": {
                **{key: str(value) for key, value in alpha_report_paths.items()},
                **{key: str(value) for key, value in strategy_report_paths.items()},
            },
        }
        (self.reports_dir / "research_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return {
            "dataset": dataset,
            "regimes": regimes,
            "anomalies": anomalies,
            "mined_signals": mined_signals,
            "strategies": strategies,
            "ranking": ranking,
            "selected_features": selected_features,
            "hypotheses": hypotheses,
            "summary": summary,
        }

    @staticmethod
    def _persist_frame(frame: pd.DataFrame, path: Path) -> None:
        if frame.empty:
            pd.DataFrame().to_csv(path, index=False)
            return
        frame.to_csv(path, index=False)

    def _persist_relational_outputs(
        self,
        regimes: pd.DataFrame,
        anomalies: pd.DataFrame,
        mined_signals: pd.DataFrame,
        strategies: pd.DataFrame,
        ranking: pd.DataFrame,
        report_paths: dict[str, Path],
    ) -> None:
        session = StorageSessionLocal()
        try:
            session.query(RegimeDetectionRecord).delete(synchronize_session=False)
            session.query(AnomalyDetectionRecord).delete(synchronize_session=False)
            session.query(MinedSignalRecord).delete(synchronize_session=False)
            session.query(StrategyCandidateRecord).delete(synchronize_session=False)
            session.query(DiscoveryRankingRecord).delete(synchronize_session=False)
            session.query(AlphaReportRecord).delete(synchronize_session=False)

            for row in regimes.to_dict(orient="records"):
                session.add(
                    RegimeDetectionRecord(
                        symbol=str(row["symbol"]),
                        timestamp=pd.to_datetime(row["timestamp"], utc=True, errors="coerce").to_pydatetime(),
                        regime_label=str(row["regime_label"]),
                        regime_confidence=float(row["regime_confidence"]),
                    )
                )
            for row in anomalies.to_dict(orient="records"):
                session.add(
                    AnomalyDetectionRecord(
                        symbol=str(row["symbol"]),
                        timestamp=pd.to_datetime(row["timestamp"], utc=True, errors="coerce").to_pydatetime(),
                        anomaly_score=float(row["anomaly_score"]),
                        anomaly_type=str(row["anomaly_type"]),
                        anomaly_window=int(row["anomaly_window"]),
                    )
                )
            for row in mined_signals.to_dict(orient="records"):
                session.add(
                    MinedSignalRecord(
                        signal_definition=str(row["signal_definition"]),
                        sample_count=int(row["sample_count"]),
                        win_rate=float(row["win_rate"]),
                        avg_return=float(row["avg_return"]),
                        sharpe=float(row["sharpe"]),
                        max_drawdown=float(row["max_drawdown"]),
                        stability_score=float(row["stability_score"]),
                    )
                )
            for row in strategies.to_dict(orient="records"):
                session.add(
                    StrategyCandidateRecord(
                        strategy_id=str(row["strategy_id"]),
                        signal_definition=str(row["signal_definition"]),
                        promotion_status=str(row["promotion_status"]),
                        evaluation_metrics=json.dumps(row["evaluation_metrics"], default=str),
                    )
                )
            for row in ranking.to_dict(orient="records"):
                session.add(
                    DiscoveryRankingRecord(
                        strategy_id=str(row["strategy_id"]),
                        alpha_discovery_score=float(row["alpha_discovery_score"]),
                        promotion_status=str(row["promotion_status"]),
                    )
                )
            tracked = self.experiment_tracker.load()
            for row in tracked.tail(20).to_dict(orient="records"):
                existing = session.query(ExperimentRunRecord).filter(ExperimentRunRecord.experiment_id == str(row["experiment_id"])).first()
                if existing:
                    continue
                session.add(
                    ExperimentRunRecord(
                        experiment_id=str(row["experiment_id"]),
                        strategy_id=str(row["strategy_id"]),
                        feature_set=json.dumps(row["feature_set"], default=str),
                        target_definition=json.dumps(row["target_definition"], default=str),
                        metrics=json.dumps(row["metrics"], default=str),
                        promotion_status=str(row["promotion_status"]),
                    )
                )
            for name, path in report_paths.items():
                session.add(AlphaReportRecord(report_name=str(name), report_path=str(path)))
            session.commit()
        finally:
            session.close()
