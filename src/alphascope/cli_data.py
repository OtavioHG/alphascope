"""Dataset, ML, news and optimization CLI commands for AlphaScope."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

try:  # pragma: no cover - optional import for lightweight CLI bootstrap
    import pandas as pd
except Exception:  # pragma: no cover - allows parser/help usage without pandas installed
    pd = None  # type: ignore[assignment]

from alphascope.cli_registry import dispatch_command
from alphascope.config.settings import settings
from alphascope.ui import print_kv_panel, print_success, print_table_from_dataframe, print_warning
from alphascope.utils.io import list_dataset_files, parse_csv_argument


def add_data_ml_subparsers(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    dataset_parser = subparsers.add_parser("build-training-dataset", help="Build a supervised market training dataset")
    dataset_parser.add_argument("--symbols", default=",".join(settings.symbol_list))
    dataset_parser.add_argument("--interval", default=settings.default_interval)
    dataset_parser.add_argument("--horizon-bars", type=int, default=settings.target_horizon_bars)
    dataset_parser.add_argument("--threshold-pct", type=float, default=settings.target_threshold_pct)
    dataset_parser.add_argument("--external-dataset-paths", default=None)

    build_market_parser = subparsers.add_parser("build-market-dataset", help="Build a market dataset from local and external sources")
    build_market_parser.add_argument("--symbols", default=",".join(settings.symbol_list))
    build_market_parser.add_argument("--interval", default=settings.default_interval)
    build_market_parser.add_argument("--horizon-bars", type=int, default=settings.target_horizon_bars)
    build_market_parser.add_argument("--threshold-pct", type=float, default=settings.target_threshold_pct)
    build_market_parser.add_argument("--external-dataset-paths", default=None)
    build_market_parser.add_argument("--chunk-size", type=int, default=100000)

    import_market_parser = subparsers.add_parser("import-market-dataset", help="Import and normalize a large external market dataset")
    import_market_parser.add_argument("--input-path", required=True)
    import_market_parser.add_argument("--output-path", default=None)
    import_market_parser.add_argument("--chunk-size", type=int, default=100000)

    train_model_parser = subparsers.add_parser("train-market-model", help="Train and persist market ML models")
    train_model_parser.add_argument("--symbols", default=",".join(settings.symbol_list))
    train_model_parser.add_argument("--interval", default=settings.default_interval)

    eval_model_parser = subparsers.add_parser("evaluate-market-model", help="Evaluate the saved market ML model")
    eval_model_parser.add_argument("--symbols", default=",".join(settings.symbol_list))
    eval_model_parser.add_argument("--interval", default=settings.default_interval)
    eval_model_parser.add_argument("--artifact-path", default=str(settings.market_model_path))

    predict_parser = subparsers.add_parser("predict-market", help="Generate market probabilities with the saved model")
    predict_parser.add_argument("--symbols", default=",".join(settings.symbol_list))
    predict_parser.add_argument("--interval", default=settings.default_interval)

    ingest_news_parser = subparsers.add_parser("ingest-news", help="Fetch news from GDELT and store locally")
    ingest_news_parser.add_argument("--query", default="crypto OR bitcoin OR ethereum")
    ingest_news_parser.add_argument("--days", type=int, default=1)
    ingest_news_parser.add_argument("--limit", type=int, default=50)

    build_news_parser = subparsers.add_parser("build-news-dataset", help="Build a consolidated news dataset from multiple sources")
    build_news_parser.add_argument("--query", default="crypto OR bitcoin OR ethereum")
    build_news_parser.add_argument("--days", type=int, default=1)
    build_news_parser.add_argument("--limit", type=int, default=50)
    build_news_parser.add_argument("--include-hf", action="store_true")
    build_news_parser.add_argument("--hf-export-path", default=None)
    build_news_parser.add_argument("--kaggle-export-path", default=None)
    build_news_parser.add_argument("--filename", default=settings.news_dataset_path.name)

    train_news_parser = subparsers.add_parser("train-news-model", help="Train a supervised news sentiment model")
    train_news_parser.add_argument("--input-path", default=str(settings.news_data_dir / "news_training_dataset.csv"))
    train_news_parser.add_argument("--text-column", default=None)
    train_news_parser.add_argument("--label-column", default="label")

    import_news_parser = subparsers.add_parser("import-news-dataset", help="Import and normalize an external news dataset")
    import_news_parser.add_argument("--input-path", required=True)
    import_news_parser.add_argument("--output-path", default=None)

    list_external_parser = subparsers.add_parser("list-external-datasets", help="List external market/news datasets available locally")
    list_external_parser.add_argument("--type", choices=["market", "news", "all"], default="all")

    show_news_parser = subparsers.add_parser("show-news-signals", help="Show aggregated news signals by asset")
    show_news_parser.add_argument("--symbols", default=None)
    show_news_parser.add_argument("--limit", type=int, default=20)

    score_news_parser = subparsers.add_parser("score-news", help="Score news sentiment and topics")
    score_news_parser.add_argument("--input-path", default=str(settings.news_data_dir / "gdelt_news_latest.csv"))

    optimize_parser = subparsers.add_parser("optimize-strategy", help="Optimize strategy parameters with Optuna")
    optimize_parser.add_argument("--symbol", default=settings.symbol_list[0])
    optimize_parser.add_argument("--interval", default=settings.default_interval)
    optimize_parser.add_argument("--trials", type=int, default=settings.optuna_trials)

    train_prod_parser = subparsers.add_parser("train-production-ai", help="Build dataset, train the market model and warm the production AI stack")
    train_prod_parser.add_argument("--symbols", default=",".join(settings.symbol_list))
    train_prod_parser.add_argument("--interval", default=settings.default_interval)
    train_prod_parser.add_argument("--horizon-bars", type=int, default=settings.target_horizon_bars)
    train_prod_parser.add_argument("--threshold-pct", type=float, default=settings.target_threshold_pct)


def handle_data_ml_command(args: argparse.Namespace, *, repository: StorageRepository, pipeline: AlphaScopePipeline) -> bool:
    return dispatch_command(args.command, DATA_ML_COMMAND_HANDLERS, args=args, repository=repository, pipeline=pipeline)


def _handle_build_training_dataset(args: argparse.Namespace, repository: StorageRepository, **_: Any) -> None:
    from alphascope.datasets.market_dataset_builder import MarketDatasetBuilder

    builder = MarketDatasetBuilder(repository=repository)
    dataset = builder.build(
        symbols=parse_csv_argument(args.symbols),
        interval=args.interval,
        horizon_bars=args.horizon_bars,
        threshold_pct=args.threshold_pct,
        external_dataset_paths=_parse_optional_paths(args.external_dataset_paths),
        export=True,
    )
    print_success(f"Dataset de treino gerado com {len(dataset)} linhas.")
    preview_columns = ["timestamp", "symbol", "future_return_target", "up_move_target", "binary_breakout_target"]
    print_table_from_dataframe(dataset.loc[:, preview_columns], title="Market Training Dataset", max_rows=20)


def _handle_build_market_dataset(args: argparse.Namespace, repository: StorageRepository, **_: Any) -> None:
    from alphascope.datasets.market_dataset_builder import MarketDatasetBuilder

    dataset = MarketDatasetBuilder(repository=repository).build(
        symbols=parse_csv_argument(args.symbols),
        interval=args.interval,
        horizon_bars=args.horizon_bars,
        threshold_pct=args.threshold_pct,
        external_dataset_paths=_parse_optional_paths(args.external_dataset_paths),
        chunk_size=args.chunk_size,
        export=True,
    )
    print_success(f"Dataset de mercado gerado com {len(dataset)} linhas.")
    print_kv_panel("Market Dataset", {"path": str(settings.market_dataset_path), "rows": len(dataset)})
    columns = ["timestamp", "symbol", "market_cap", "market_rank", "is_exchange_source", "is_external_source", "btc_correlation_24"]
    print_table_from_dataframe(dataset.loc[:, [column for column in columns if column in dataset.columns]], title="Market Dataset Preview", max_rows=20)


def _handle_import_market_dataset(args: argparse.Namespace, repository: StorageRepository, **_: Any) -> None:
    from alphascope.datasets.market_dataset_builder import MarketDatasetBuilder
    from alphascope.datasets.parquet_utils import validate_dataset_file

    output_path = MarketDatasetBuilder(repository=repository).import_external_market_data(
        input_path=args.input_path,
        output_path=args.output_path,
        chunk_size=args.chunk_size,
    )
    validation = validate_dataset_file(output_path, dataset_type="market")
    print_success("Dataset externo de mercado importado.")
    print_kv_panel("Market Dataset Import", {"output_path": str(output_path), "rows": validation.row_count, "duplicates": validation.duplicate_count, "valid": validation.valid})


def _handle_train_market_model(args: argparse.Namespace, repository: StorageRepository, **_: Any) -> None:
    from alphascope.ml.train_market_model import MarketModelTrainer

    result = MarketModelTrainer().train(symbols=parse_csv_argument(args.symbols), interval=args.interval)
    print_success(f"Melhor modelo salvo: {result['best_model_name']}")
    print_kv_panel("Best Market Model", result["best_metrics"])  # type: ignore[arg-type]
    print_table_from_dataframe(result["leaderboard"], title="Model Leaderboard")  # type: ignore[arg-type]


def _handle_evaluate_market_model(args: argparse.Namespace, repository: StorageRepository, **_: Any) -> None:
    from alphascope.datasets.market_dataset_builder import MarketDatasetBuilder
    from alphascope.ml.evaluate_market_model import MarketModelEvaluator

    builder = MarketDatasetBuilder(repository=repository)
    dataset = builder.build(symbols=parse_csv_argument(args.symbols), interval=args.interval, export=False)
    evaluation = MarketModelEvaluator(dataset_builder=builder).evaluate(dataset=dataset, artifact_path=args.artifact_path)
    print_success("Modelo de mercado avaliado.")
    print_kv_panel("Market Model Metrics", evaluation["metrics"])  # type: ignore[arg-type]
    print_table_from_dataframe(evaluation["predictions"], title="Market Predictions", max_rows=20)  # type: ignore[arg-type]


def _handle_predict_market(args: argparse.Namespace, repository: StorageRepository, **_: Any) -> None:
    from alphascope.ml.inference import MarketModelInference

    predictions = MarketModelInference(repository=repository).predict_latest(symbols=parse_csv_argument(args.symbols), interval=args.interval)
    print_success(f"{len(predictions)} ativos pontuados pelo modelo.")
    columns = ["timestamp", "symbol", "ml_probability", "score", "rsi", "momentum", "trend_strength"]
    visible = [column for column in columns if column in predictions.columns]
    print_table_from_dataframe(predictions.loc[:, visible], title="Market ML Predictions")


def _handle_ingest_news(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.datasets.news_dataset_builder import NewsDatasetBuilder

    builder = NewsDatasetBuilder()
    dataset = builder.fetch_gdelt(query=args.query, max_records=args.limit, days=args.days)
    path = builder.save_dataset(dataset, "gdelt_news_latest.csv")
    print_success(f"Noticias ingeridas: {len(dataset)}")
    print_kv_panel("News Dataset", {"path": str(path), "rows": len(dataset), "query": args.query})
    if not dataset.empty:
        preview_columns = [column for column in ["title", "source", "timestamp"] if column in dataset.columns]
        print_table_from_dataframe(dataset.loc[:, preview_columns], title="Fetched News", max_rows=20)


def _handle_build_news_dataset(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.datasets.news_dataset_builder import NewsDatasetBuilder

    builder = NewsDatasetBuilder()
    dataset = builder.build(
        gdelt_query=args.query,
        gdelt_days=args.days,
        gdelt_limit=args.limit,
        include_huggingface_financial_phrasebank=args.include_hf,
        huggingface_export_path=args.hf_export_path,
        kaggle_export_path=args.kaggle_export_path,
        export=True,
        filename=args.filename,
    )
    print_success(f"Dataset consolidado de noticias gerado com {len(dataset)} linhas.")
    print_kv_panel("News Dataset Builder", {"output_path": str(settings.news_data_dir / args.filename), "rows": len(dataset), "hf_enabled": args.include_hf})
    preview_columns = [column for column in ["timestamp", "dataset_source", "title", "source", "clean_text"] if column in dataset.columns]
    print_table_from_dataframe(dataset.loc[:, preview_columns], title="News Training Dataset", max_rows=20)


def _handle_import_news_dataset(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.datasets.news_dataset_builder import NewsDatasetBuilder
    from alphascope.datasets.parquet_utils import validate_dataset_file

    output_path = NewsDatasetBuilder().import_external_news_data(input_path=args.input_path, output_path=args.output_path)
    validation = validate_dataset_file(output_path, dataset_type="news")
    print_success("Dataset externo de noticias importado.")
    print_kv_panel("News Dataset Import", {"output_path": str(output_path), "rows": validation.row_count, "duplicates": validation.duplicate_count, "valid": validation.valid})


def _handle_train_news_model(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.datasets.news_dataset_builder import NewsDatasetBuilder
    from alphascope.ml.news_model_training import NewsModelTrainer

    dataset = NewsDatasetBuilder().load_local_dataset(args.input_path)
    result = NewsModelTrainer().train(dataset, text_column=args.text_column, label_column=args.label_column)
    print_success("Modelo supervisionado de noticias treinado.")
    print_kv_panel("News Model Metrics", result)


def _handle_show_news_signals(args: argparse.Namespace, pipeline: AlphaScopePipeline, **_: Any) -> None:
    symbols = parse_csv_argument(args.symbols) if args.symbols else None
    summary = pipeline.show_news_signals(symbols=symbols)
    if summary.empty:
        print_warning("Nenhum sinal de noticias disponivel.")
        return
    print_success(f"{len(summary)} ativos com sinais de noticias agregados.")
    columns = ["related_asset", "news_score", "avg_sentiment_score", "avg_impact_score", "news_count", "last_news_at"]
    print_table_from_dataframe(summary.loc[:, columns], title="News Signals", max_rows=args.limit)


def _handle_list_external_datasets(args: argparse.Namespace, **_: Any) -> None:
    if pd is None:
        raise RuntimeError("pandas is required to listar datasets externos. Instale as dependências completas do projeto.")
    rows: list[dict[str, str]] = []
    if args.type in {"market", "all"}:
        for path in list_dataset_files(settings.kaggle_data_dir):
            rows.append({"type": "market", "location": "kaggle", "path": str(path)})
        for path in list_dataset_files(settings.hf_datasets_dir):
            rows.append({"type": "market", "location": "huggingface", "path": str(path)})
    if args.type in {"news", "all"}:
        for path in list_dataset_files(settings.kaggle_data_dir):
            rows.append({"type": "news", "location": "kaggle", "path": str(path)})
        for path in list_dataset_files(settings.hf_datasets_dir):
            rows.append({"type": "news", "location": "huggingface", "path": str(path)})
    frame = pd.DataFrame(rows)
    if frame.empty:
        print_warning("Nenhum dataset externo encontrado.")
        return
    print_success(f"{len(frame)} arquivos externos encontrados.")
    print_table_from_dataframe(frame, title="External Datasets", max_rows=100)


def _handle_score_news(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.datasets.news_dataset_builder import NewsDatasetBuilder
    from alphascope.nlp.inference import NewsInferenceEngine

    builder = NewsDatasetBuilder()
    news_frame = builder.load_local_dataset(args.input_path)
    scored = NewsInferenceEngine().score_frame(news_frame)
    output_path = settings.processed_data_dir / "scored_news_latest.csv"
    scored.to_csv(output_path, index=False)
    print_success(f"Noticias pontuadas: {len(scored)}")
    print_kv_panel("News Scoring", {"input_path": args.input_path, "output_path": str(output_path), "rows": len(scored)})
    preview_columns = [column for column in ["title", "sentiment_label", "sentiment_score", "topic_label", "related_asset", "impact_score"] if column in scored.columns]
    print_table_from_dataframe(scored.loc[:, preview_columns], title="Scored News", max_rows=20)


def _handle_optimize_strategy(args: argparse.Namespace, repository: StorageRepository, **_: Any) -> None:
    from alphascope.optimization.tuner import StrategyTuner

    result = StrategyTuner(repository=repository).optimize(symbol=args.symbol.upper(), interval=args.interval, n_trials=args.trials)
    print_success("Otimizacao concluida.")
    print_kv_panel("Optimization", result)


def _handle_train_production_ai(args: argparse.Namespace, repository: StorageRepository, **_: Any) -> None:
    from alphascope.datasets.market_dataset_builder import MarketDatasetBuilder
    from alphascope.ml.evaluate_market_model import MarketModelEvaluator
    from alphascope.ml.train_market_model import MarketModelTrainer

    symbols = parse_csv_argument(args.symbols)
    builder = MarketDatasetBuilder(repository=repository)
    dataset = builder.build(
        symbols=symbols,
        interval=args.interval,
        horizon_bars=args.horizon_bars,
        threshold_pct=args.threshold_pct,
        export=True,
    )
    result = MarketModelTrainer(dataset_builder=builder).train(symbols=symbols, interval=args.interval, dataset=dataset)
    evaluation = MarketModelEvaluator(dataset_builder=builder).evaluate(dataset=dataset, artifact_path=result["artifact_path"])
    print_success("Treino inicial de IA para produção concluído.")
    print_kv_panel(
        "Production AI Warm Start",
        {
            "dataset_rows": len(dataset),
            "best_model": result["best_model_name"],
            "artifact_path": result["artifact_path"],
            "roc_auc": evaluation["metrics"].get("roc_auc"),
            "accuracy": evaluation["metrics"].get("accuracy"),
        },
    )
    print_table_from_dataframe(result["leaderboard"], title="Production AI Leaderboard")


def _parse_optional_paths(value: str | None) -> list[Path] | None:
    if not value:
        return None
    return [Path(item.strip()) for item in value.split(",") if item.strip()]


DATA_ML_COMMAND_HANDLERS = {
    "build-training-dataset": _handle_build_training_dataset,
    "build-market-dataset": _handle_build_market_dataset,
    "import-market-dataset": _handle_import_market_dataset,
    "train-market-model": _handle_train_market_model,
    "evaluate-market-model": _handle_evaluate_market_model,
    "predict-market": _handle_predict_market,
    "ingest-news": _handle_ingest_news,
    "build-news-dataset": _handle_build_news_dataset,
    "import-news-dataset": _handle_import_news_dataset,
    "train-news-model": _handle_train_news_model,
    "list-external-datasets": _handle_list_external_datasets,
    "show-news-signals": _handle_show_news_signals,
    "score-news": _handle_score_news,
    "optimize-strategy": _handle_optimize_strategy,
    "train-production-ai": _handle_train_production_ai,
}
