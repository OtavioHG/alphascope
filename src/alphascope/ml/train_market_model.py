"""Training pipeline for supervised market models."""

from __future__ import annotations

import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier, VotingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from alphascope.config.settings import settings
from alphascope.core.logger import get_logger
from alphascope.datasets.market_dataset_builder import MARKET_FEATURE_COLUMNS
from alphascope.ml.dataset_builder import MarketDatasetBuilder
from alphascope.ml.evaluate_market_model import evaluate_market_classifier
from alphascope.ml.model_registry import ModelRegistry
from alphascope.ml.schemas import MarketModelMetadata

logger = get_logger(__name__)

try:
    from xgboost import XGBClassifier
except ModuleNotFoundError:  # pragma: no cover
    XGBClassifier = None

try:
    from lightgbm import LGBMClassifier
except ModuleNotFoundError:  # pragma: no cover
    LGBMClassifier = None

try:
    from catboost import CatBoostClassifier
except ModuleNotFoundError:  # pragma: no cover
    CatBoostClassifier = None


class MarketModelTrainer:
    """Train, compare and persist market direction classifiers."""

    def __init__(self, dataset_builder: MarketDatasetBuilder | None = None, registry: ModelRegistry | None = None) -> None:
        self.dataset_builder = dataset_builder or MarketDatasetBuilder()
        self.registry = registry or ModelRegistry()

    def train(
        self,
        *,
        symbols: list[str],
        interval: str,
        dataset: pd.DataFrame | None = None,
    ) -> dict[str, object]:
        training_dataset = dataset if dataset is not None else self.dataset_builder.build(symbols=symbols, interval=interval, export=True)
        if training_dataset.empty:
            raise RuntimeError("Market training dataset is empty.")

        train_frame, test_frame = self.dataset_builder.train_test_split(training_dataset)
        if train_frame.empty or test_frame.empty:
            raise RuntimeError("Insufficient data for temporal train/test split.")

        x_train = train_frame.loc[:, MARKET_FEATURE_COLUMNS]
        y_train = train_frame["up_move_target"].astype(int)
        x_test = test_frame.loc[:, MARKET_FEATURE_COLUMNS]
        y_test = test_frame["up_move_target"].astype(int)

        candidates = self._build_candidates()
        results: list[dict[str, object]] = []
        best_model = None
        best_result: dict[str, object] | None = None

        for model_name, model in candidates.items():
            model.fit(x_train, y_train)
            y_pred = model.predict(x_test)
            y_proba = model.predict_proba(x_test)[:, 1]
            metrics = evaluate_market_classifier(y_true=y_test, y_pred=y_pred, y_proba=y_proba)
            result = {"model_name": model_name, "model": model, "metrics": metrics}
            results.append(result)
            logger.info("Trained market model %s with metrics %s", model_name, metrics)
            if best_result is None or metrics["roc_auc"] > best_result["metrics"]["roc_auc"]:
                best_result = result
                best_model = model

        assert best_result is not None and best_model is not None
        artifact_path = settings.market_model_dir / "best_market_model.joblib"
        metadata = MarketModelMetadata(
            model_name=str(best_result["model_name"]),
            target_name=settings.market_target_name,
            feature_columns=MARKET_FEATURE_COLUMNS,
            symbols=symbols,
            train_rows=len(train_frame),
            test_rows=len(test_frame),
            metrics=best_result["metrics"],  # type: ignore[arg-type]
            artifact_path=str(artifact_path),
            extra_metadata={"interval": interval},
        )
        self.registry.save_market_model(best_model, metadata)
        leaderboard = pd.DataFrame(
            [{"model_name": item["model_name"], **item["metrics"]} for item in results]
        ).sort_values("roc_auc", ascending=False).reset_index(drop=True)
        return {
            "leaderboard": leaderboard,
            "best_model_name": best_result["model_name"],
            "best_metrics": best_result["metrics"],
            "artifact_path": str(artifact_path),
            "metadata_path": str(artifact_path.with_suffix(".json")),
            "feature_columns": MARKET_FEATURE_COLUMNS,
        }

    @staticmethod
    def _build_candidates() -> dict[str, Pipeline]:
        candidates: dict[str, Pipeline] = {
            "logistic_regression": Pipeline(
                steps=[
                    ("imputer", SimpleImputer(strategy="median")),
                    ("model", LogisticRegression(max_iter=1000)),
                ]
            ),
            "random_forest": Pipeline(
                steps=[
                    ("imputer", SimpleImputer(strategy="median")),
                    ("model", RandomForestClassifier(n_estimators=200, random_state=42)),
                ]
            ),
            "gradient_boosting": Pipeline(
                steps=[
                    ("imputer", SimpleImputer(strategy="median")),
                    ("model", GradientBoostingClassifier(random_state=42)),
                ]
            ),
        }
        if XGBClassifier is not None:
            candidates["xgboost"] = Pipeline(
                steps=[
                    ("imputer", SimpleImputer(strategy="median")),
                    ("model", XGBClassifier(n_estimators=250, max_depth=4, learning_rate=0.05, subsample=0.9, eval_metric="logloss")),
                ]
            )
        if LGBMClassifier is not None:
            candidates["lightgbm"] = Pipeline(
                steps=[
                    ("imputer", SimpleImputer(strategy="median")),
                    ("model", LGBMClassifier(n_estimators=250, learning_rate=0.05)),
                ]
            )
        if CatBoostClassifier is not None:
            candidates["catboost"] = Pipeline(
                steps=[
                    ("imputer", SimpleImputer(strategy="median")),
                    ("model", CatBoostClassifier(verbose=False, iterations=250, learning_rate=0.05)),
                ]
            )
        candidates["ensemble_model"] = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    VotingClassifier(
                        estimators=[
                            ("logistic_regression", LogisticRegression(max_iter=1000)),
                            ("random_forest", RandomForestClassifier(n_estimators=200, random_state=42)),
                            ("gradient_boosting", GradientBoostingClassifier(random_state=42)),
                        ],
                        voting="soft",
                    ),
                ),
            ]
        )
        return candidates
