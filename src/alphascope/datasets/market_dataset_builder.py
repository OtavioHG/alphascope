"""Build supervised market datasets using multiple data sources and large files."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from alphascope.config.constants import MARKET_CANDLE_COLUMNS
from alphascope.config.settings import settings
from alphascope.core.logger import get_logger
from alphascope.data_sources.coingecko_client import CoinGeckoDataClient
from alphascope.data_sources.coinmarketcap_client import CoinMarketCapDataClient
from alphascope.data_sources.cryptocompare_client import CryptoCompareMarketDataClient
from alphascope.data_sources.fear_greed_client import FearGreedIndexClient
from alphascope.datasets.parquet_utils import convert_csv_to_parquet, export_dataset, read_dataset
from alphascope.datasets.validators import validate_market_dataframe
from alphascope.external_data.normalizers import canonicalize_asset_symbol, split_binance_symbol
from alphascope.features.feature_pipeline import FeaturePipeline
from alphascope.features.technical import compute_technical_features
from alphascope.ml.targets import binary_breakout_target, future_return_target, up_move_target
from alphascope.storage.repositories import StorageRepository

logger = get_logger(__name__)

MARKET_FEATURE_COLUMNS = [
    "return_pct",
    "ma_short",
    "ma_long",
    "rsi",
    "volatility",
    "avg_volume",
    "relative_volume",
    "momentum",
    "trend_strength",
    "market_cap",
    "market_rank",
    "cryptocompare_market_cap",
    "cryptocompare_supply",
    "fear_greed_value",
    "is_exchange_source",
    "is_external_source",
    "btc_correlation_24",
]


class MarketDatasetBuilder:
    """Build market datasets combining technical, metadata and large external files."""

    def __init__(
        self,
        repository: StorageRepository | None = None,
        cryptocompare_client: CryptoCompareMarketDataClient | None = None,
        coingecko_client: CoinGeckoDataClient | None = None,
        coinmarketcap_client: CoinMarketCapDataClient | None = None,
        fear_greed_client: FearGreedIndexClient | None = None,
    ) -> None:
        self.repository = repository or StorageRepository()
        self.feature_pipeline = FeaturePipeline(repository=self.repository)
        self.cryptocompare_client = cryptocompare_client or CryptoCompareMarketDataClient()
        self.coingecko_client = coingecko_client or CoinGeckoDataClient()
        self.coinmarketcap_client = coinmarketcap_client or CoinMarketCapDataClient()
        self.fear_greed_client = fear_greed_client or FearGreedIndexClient()

    @staticmethod
    def _normalize_timestamp(series: pd.Series) -> pd.Series:
        timestamps = pd.to_datetime(series, errors="coerce", utc=True)
        return timestamps.dt.tz_convert(None).astype("datetime64[ns]")

    def build(
        self,
        *,
        symbols: list[str],
        interval: str,
        horizon_bars: int | None = None,
        threshold_pct: float | None = None,
        external_dataset_paths: list[str | Path] | None = None,
        chunk_size: int = 100_000,
        export: bool = True,
    ) -> pd.DataFrame:
        """Build a merged supervised dataset with technical and market metadata."""
        horizon = horizon_bars or settings.target_horizon_bars
        threshold = threshold_pct if threshold_pct is not None else settings.target_threshold_pct
        market_metadata = self._load_market_metadata()
        fear_greed_frame = self._load_fear_greed_index()
        frames = []

        for symbol in symbols:
            candles = self._load_symbol_candles(
                symbol=symbol,
                interval=interval,
                external_dataset_paths=external_dataset_paths,
                chunk_size=chunk_size,
            )
            if candles.empty:
                continue
            features = self._load_or_compute_features(symbol=symbol, interval=interval, candles=candles)
            if features.empty:
                continue
            symbol_dataset = self._merge_symbol_dataset(
                symbol=symbol,
                features=features,
                candles=candles,
                market_metadata=market_metadata,
                fear_greed_frame=fear_greed_frame,
                horizon_bars=horizon,
                threshold_pct=threshold,
            )
            if not symbol_dataset.empty:
                frames.append(symbol_dataset)

        dataset = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        if not dataset.empty:
            dataset = self._attach_btc_correlation(dataset)
            optional_defaults = {
                "cryptocompare_market_cap": 0.0,
                "cryptocompare_supply": 0.0,
                "fear_greed_value": 50.0,
            }
            for column, default in optional_defaults.items():
                if column in dataset.columns:
                    dataset[column] = pd.to_numeric(dataset[column], errors="coerce").fillna(default)
            if "fear_greed_label" in dataset.columns:
                dataset["fear_greed_label"] = dataset["fear_greed_label"].fillna("Neutral")
            dataset = dataset.dropna(
                subset=[column for column in MARKET_FEATURE_COLUMNS if column in dataset.columns]
            ).reset_index(drop=True)
        if export and not dataset.empty:
            export_dataset(dataset, settings.market_dataset_path, include_csv=True)
        return dataset

    def import_external_market_data(
        self,
        input_path: str | Path,
        *,
        output_path: str | Path | None = None,
        chunk_size: int = 100_000,
        schema_map: dict[str, str] | None = None,
    ) -> Path:
        """Normalize a large external market dataset and persist it as Parquet."""
        source_path = Path(input_path)
        target_path = Path(output_path) if output_path else settings.external_data_dir / f"{source_path.stem}.parquet"
        if source_path.suffix.lower() == ".csv":
            parquet_path = convert_csv_to_parquet(
                source_path,
                target_path,
                columns=None,
                chunk_size=chunk_size,
                schema_map=schema_map,
            )
            validation = validate_market_dataframe(pd.concat(list(read_dataset(parquet_path)), ignore_index=True))
            if not validation.valid:
                raise RuntimeError(f"Invalid imported market dataset: {validation}")
            return parquet_path
        frames = list(read_dataset(source_path, chunk_size=chunk_size, schema_map=schema_map))
        if not frames:
            raise RuntimeError(f"No rows found in {source_path}")
        combined = pd.concat(frames, ignore_index=True)
        validation = validate_market_dataframe(combined)
        if not validation.valid:
            raise RuntimeError(f"Invalid imported market dataset: {validation}")
        export_dataset(combined, target_path)
        return target_path

    def train_test_split(
        self,
        dataset: pd.DataFrame,
        train_fraction: float | None = None,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Split the dataset chronologically without shuffling."""
        if dataset.empty:
            return pd.DataFrame(), pd.DataFrame()
        fraction = train_fraction or settings.training_train_fraction
        ordered = dataset.sort_values(["timestamp", "symbol"]).reset_index(drop=True)
        split_index = max(1, int(len(ordered) * fraction))
        train = ordered.iloc[:split_index].reset_index(drop=True)
        test = ordered.iloc[split_index:].reset_index(drop=True)
        return train, test

    def _load_symbol_candles(
        self,
        *,
        symbol: str,
        interval: str,
        external_dataset_paths: list[str | Path] | None,
        chunk_size: int,
    ) -> pd.DataFrame:
        candles = self.repository.get_candles(symbol=symbol, interval=interval)
        frames = [candles] if not candles.empty else []
        if external_dataset_paths:
            for dataset_path in external_dataset_paths:
                external = self._load_external_symbol_candles(
                    dataset_path,
                    symbol=symbol,
                    interval=interval,
                    chunk_size=chunk_size,
                )
                if not external.empty:
                    frames.append(external)
        if settings.cryptocompare_api_enabled:
            cryptocompare = self._load_cryptocompare_symbol_candles(symbol=symbol, interval=interval)
            if not cryptocompare.empty:
                frames.append(cryptocompare)
        if not frames:
            return pd.DataFrame(columns=MARKET_CANDLE_COLUMNS)
        combined = pd.concat(frames, ignore_index=True)
        combined["timestamp"] = self._normalize_timestamp(combined["timestamp"])
        combined = combined.dropna(subset=["timestamp", "open", "high", "low", "close", "volume"])
        combined = combined.drop_duplicates(subset=["timestamp", "symbol", "interval"], keep="last")
        return combined.sort_values("timestamp").reset_index(drop=True)

    def _load_external_symbol_candles(
        self,
        dataset_path: str | Path,
        *,
        symbol: str,
        interval: str,
        chunk_size: int,
    ) -> pd.DataFrame:
        columns = ["timestamp", "open", "high", "low", "close", "volume", "symbol", "interval", "source"]
        frames = []
        for chunk in read_dataset(dataset_path, columns=None, chunk_size=chunk_size):
            normalized = self._normalize_external_candles(chunk, interval=interval)
            if normalized.empty:
                continue
            filtered = normalized.loc[normalized["symbol"] == symbol.upper()].reset_index(drop=True)
            if not filtered.empty:
                frames.append(filtered.loc[:, [column for column in columns if column in filtered.columns]])
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=columns)

    def _load_or_compute_features(self, *, symbol: str, interval: str, candles: pd.DataFrame) -> pd.DataFrame:
        features = self.repository.get_features(symbol=symbol, interval=interval)
        if not features.empty:
            features = features.copy()
            features["timestamp"] = self._normalize_timestamp(features["timestamp"])
            return features.sort_values("timestamp").reset_index(drop=True)
        if candles.empty:
            return pd.DataFrame()
        if {"symbol", "interval"}.issubset(candles.columns):
            computed = compute_technical_features(
                candles=candles.loc[:, MARKET_CANDLE_COLUMNS],
                short_window=settings.short_window,
                long_window=settings.long_window,
                rsi_window=settings.rsi_window,
                volatility_window=settings.volatility_window,
                volume_window=settings.volume_window,
                momentum_window=settings.momentum_window,
            )
            computed["timestamp"] = self._normalize_timestamp(computed["timestamp"])
            return computed.sort_values("timestamp").reset_index(drop=True)
        computed = self.feature_pipeline.build_for_symbol(symbol=symbol, interval=interval)
        if not computed.empty:
            computed = computed.copy()
            computed["timestamp"] = self._normalize_timestamp(computed["timestamp"])
        return computed.sort_values("timestamp").reset_index(drop=True)

    def _load_market_metadata(self) -> pd.DataFrame:
        frames = []
        try:
            coingecko = self.coingecko_client.fetch_market_metrics(limit=500)
            if not coingecko.empty:
                frames.append(coingecko)
        except Exception as exc:
            logger.warning("CoinGecko metadata unavailable: %s", exc)

        try:
            if settings.cryptocompare_api_enabled:
                symbols = [canonicalize_asset_symbol(split_binance_symbol(item)[0]) for item in settings.symbol_list]
                cryptocompare = self.cryptocompare_client.fetch_market_snapshot(symbols=symbols)
                if not cryptocompare.empty:
                    cryptocompare = cryptocompare.rename(
                        columns={"market_cap": "cryptocompare_market_cap", "supply": "cryptocompare_supply"}
                    )
                    frames.append(cryptocompare)
        except Exception as exc:
            logger.warning("CryptoCompare metadata unavailable: %s", exc)

        try:
            if settings.coinmarketcap_api_enabled:
                coinmarketcap = self.coinmarketcap_client.fetch_market_metrics(limit=500)
                if not coinmarketcap.empty:
                    frames.append(coinmarketcap)
        except Exception as exc:
            logger.warning("CoinMarketCap metadata unavailable: %s", exc)

        if not frames:
            return pd.DataFrame(columns=["canonical_symbol", "market_cap", "market_rank"])

        metadata = frames[0]
        for frame in frames[1:]:
            metadata = metadata.merge(frame, on="canonical_symbol", how="outer")

        metadata["market_cap"] = metadata.get("market_cap")
        if "market_cap_cmc" in metadata.columns:
            metadata["market_cap"] = metadata["market_cap"].fillna(metadata["market_cap_cmc"])
        metadata["market_rank"] = metadata.get("market_rank")
        if "market_rank_cmc" in metadata.columns:
            metadata["market_rank"] = metadata["market_rank"].fillna(metadata["market_rank_cmc"])

        keep = {
            "canonical_symbol",
            "market_cap",
            "market_rank",
            "circulating_supply",
            "global_volume",
            "cryptocompare_market_cap",
            "cryptocompare_supply",
        }
        return metadata.loc[:, [column for column in metadata.columns if column in keep]].drop_duplicates(subset=["canonical_symbol"]).reset_index(drop=True)

    def _merge_symbol_dataset(
        self,
        *,
        symbol: str,
        features: pd.DataFrame,
        candles: pd.DataFrame,
        market_metadata: pd.DataFrame,
        fear_greed_frame: pd.DataFrame,
        horizon_bars: int,
        threshold_pct: float,
    ) -> pd.DataFrame:
        base_asset, _ = split_binance_symbol(symbol)
        canonical_symbol = canonicalize_asset_symbol(base_asset)
        features = features.copy()
        candles = candles.copy()
        features["timestamp"] = self._normalize_timestamp(features["timestamp"])
        candles["timestamp"] = self._normalize_timestamp(candles["timestamp"])
        merged = features.merge(
            candles[["timestamp", "close", "high", "source"]] if "source" in candles.columns else candles[["timestamp", "close", "high"]],
            on="timestamp",
            how="inner",
            suffixes=("", "_candle"),
        )
        if "close_candle" in merged.columns:
            merged["close"] = merged["close_candle"]
            merged = merged.drop(columns=["close_candle"])
        if "source" not in merged.columns:
            merged["source"] = "exchange"

        symbol_metadata = market_metadata.loc[market_metadata["canonical_symbol"] == canonical_symbol]
        if not symbol_metadata.empty:
            metadata_row = symbol_metadata.iloc[0]
            merged["market_cap"] = metadata_row.get("market_cap")
            merged["market_rank"] = metadata_row.get("market_rank")
            merged["cryptocompare_market_cap"] = metadata_row.get("cryptocompare_market_cap")
            merged["cryptocompare_supply"] = metadata_row.get("cryptocompare_supply")
        else:
            merged["market_cap"] = None
            merged["market_rank"] = None
            merged["cryptocompare_market_cap"] = None
            merged["cryptocompare_supply"] = None

        merged = self._attach_fear_greed(merged, fear_greed_frame)

        merged["canonical_symbol"] = canonical_symbol
        merged["is_exchange_source"] = (merged["source"] == "exchange").astype(int)
        merged["is_external_source"] = (merged["source"] != "exchange").astype(int)
        merged["future_return_target"] = future_return_target(merged["close"], horizon_bars=horizon_bars)
        merged["up_move_target"] = up_move_target(merged["close"], horizon_bars=horizon_bars, threshold_pct=threshold_pct)
        merged["binary_breakout_target"] = binary_breakout_target(merged["high"], merged["close"], horizon_bars=horizon_bars, threshold_pct=threshold_pct)
        return merged.reset_index(drop=True)

    def _attach_btc_correlation(self, dataset: pd.DataFrame, window: int = 24) -> pd.DataFrame:
        if dataset.empty:
            return dataset
        enriched = dataset.copy()
        btc_rows = enriched.loc[enriched["symbol"] == "BTCUSDT", ["timestamp", "return_pct"]].rename(columns={"return_pct": "btc_return_pct"})
        if btc_rows.empty:
            enriched["btc_correlation_24"] = 0.0
            return enriched
        enriched = enriched.merge(btc_rows, on="timestamp", how="left")
        enriched["btc_return_pct"] = enriched["btc_return_pct"].fillna(0.0)
        correlations = []
        for _, frame in enriched.groupby("symbol", sort=False):
            corr = frame["return_pct"].rolling(window=window, min_periods=max(3, min(window, 5))).corr(frame["btc_return_pct"])
            correlations.append(corr)
        enriched["btc_correlation_24"] = pd.concat(correlations).sort_index().fillna(0.0)
        return enriched.drop(columns=["btc_return_pct"])

    def _load_cryptocompare_symbol_candles(self, *, symbol: str, interval: str) -> pd.DataFrame:
        base_asset, quote_asset = split_binance_symbol(symbol)
        quote = quote_asset if quote_asset != "UNKNOWN" else "USD"
        try:
            if interval.endswith("h"):
                frame = self.cryptocompare_client.fetch_hourly_history(base_asset, quote_symbol=quote)
            elif interval.endswith("d"):
                frame = self.cryptocompare_client.fetch_daily_history(base_asset, quote_symbol=quote)
            else:
                return pd.DataFrame(columns=MARKET_CANDLE_COLUMNS + ["source"])
        except Exception as exc:
            logger.warning("CryptoCompare history unavailable for %s %s: %s", symbol, interval, exc)
            return pd.DataFrame(columns=MARKET_CANDLE_COLUMNS + ["source"])

        if not frame.empty:
            output_path = settings.cryptocompare_raw_dir / f"{symbol.lower()}_{interval}.parquet"
            export_dataset(frame, output_path, include_csv=True)
        return frame

    def _load_fear_greed_index(self) -> pd.DataFrame:
        if not settings.fear_greed_api_enabled:
            return pd.DataFrame(columns=["timestamp", "fear_greed_value", "fear_greed_label"])
        try:
            frame = self.fear_greed_client.fetch_fear_greed_index(limit=365)
        except Exception as exc:
            logger.warning("Fear & Greed data unavailable: %s", exc)
            return pd.DataFrame(columns=["timestamp", "fear_greed_value", "fear_greed_label"])
        if not frame.empty:
            frame = frame.copy()
            frame["timestamp"] = self._normalize_timestamp(frame["timestamp"])
            export_dataset(frame, settings.fear_greed_raw_dir / "fear_greed_latest.parquet", include_csv=True)
        return frame

    def _attach_fear_greed(self, frame: pd.DataFrame, fear_greed_frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return frame
        enriched = frame.copy()
        if fear_greed_frame.empty:
            enriched["fear_greed_value"] = 50.0
            enriched["fear_greed_label"] = "Neutral"
            return enriched
        enriched["timestamp"] = self._normalize_timestamp(enriched["timestamp"])
        reference = fear_greed_frame.sort_values("timestamp").copy()
        reference["timestamp"] = self._normalize_timestamp(reference["timestamp"])
        merged = pd.merge_asof(
            enriched.sort_values("timestamp"),
            reference.loc[:, ["timestamp", "fear_greed_value", "fear_greed_label"]],
            on="timestamp",
            direction="backward",
        )
        merged["fear_greed_value"] = merged["fear_greed_value"].fillna(50.0)
        merged["fear_greed_label"] = merged["fear_greed_label"].fillna("Neutral")
        return merged.reset_index(drop=True)

    def _normalize_external_candles(self, frame: pd.DataFrame, *, interval: str) -> pd.DataFrame:
        normalized = frame.copy()
        aliases = {
            "date": "timestamp",
            "datetime": "timestamp",
            "time": "timestamp",
            "open_time": "timestamp",
            "ticker": "symbol",
            "pair": "symbol",
            "base_volume": "volume",
        }
        normalized = normalized.rename(columns={column: aliases[column] for column in normalized.columns if column in aliases})
        required = {"timestamp", "open", "high", "low", "close", "volume", "symbol"}
        if not required.issubset(normalized.columns):
            return pd.DataFrame(columns=MARKET_CANDLE_COLUMNS + ["source"])
        normalized["timestamp"] = self._normalize_timestamp(normalized["timestamp"])
        normalized["symbol"] = normalized["symbol"].astype(str).str.upper().str.replace("/", "", regex=False)
        normalized["interval"] = normalized.get("interval", interval)
        normalized["interval"] = normalized["interval"].fillna(interval)
        normalized["source"] = normalized.get("source", "external")
        for column in ["open", "high", "low", "close", "volume"]:
            normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
        return normalized.loc[:, [column for column in MARKET_CANDLE_COLUMNS + ["source"] if column in normalized.columns]]
