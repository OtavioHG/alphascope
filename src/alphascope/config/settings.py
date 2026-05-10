"""Environment-backed settings for AlphaScope V1."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from alphascope.config.constants import DEFAULT_CANDLE_LIMIT, DEFAULT_INTERVAL, DEFAULT_SYMBOLS


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value is not None else default


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value is not None else default


def _get_optional_str(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _is_valid_http_url(value: str) -> bool:
    return value.startswith("https://") or value.startswith("http://")


ROOT_DIR = Path(__file__).resolve().parents[3]
_load_env_file(ROOT_DIR / ".env")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "AlphaScope")
    environment: str = os.getenv("APP_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format: str = os.getenv("LOG_FORMAT", "plain").strip().lower()
    data_dir: Path = ROOT_DIR / os.getenv("DATA_DIR", "data")
    log_dir: Path = ROOT_DIR / os.getenv("LOG_DIR", "logs")
    sqlite_path: Path = ROOT_DIR / os.getenv("SQLITE_PATH", "data/alphascope.db")
    database_url_override: str | None = _get_optional_str("DATABASE_URL")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    risk_profile: str = os.getenv("RISK_PROFILE", "moderate").strip().lower()
    kaggle_data_dir_name: str = os.getenv("KAGGLE_DATA_DIR", "data/external/kaggle")
    hf_datasets_dir_name: str = os.getenv("HF_DATASETS_DIR", "data/external/huggingface")
    large_data_format: str = os.getenv("LARGE_DATA_FORMAT", "parquet").lower()
    market_dataset_path_name: str = os.getenv("MARKET_DATASET_PATH", "data/processed/market_training_dataset.parquet")
    news_dataset_path_name: str = os.getenv("NEWS_DATASET_PATH", "data/news/news_training_dataset.parquet")
    binance_base_url: str = os.getenv("BINANCE_BASE_URL", "https://api.binance.com")
    cryptocompare_base_url: str = os.getenv("CRYPTOCOMPARE_BASE_URL", "https://min-api.cryptocompare.com")
    coingecko_base_url: str = os.getenv("COINGECKO_BASE_URL", "https://api.coingecko.com")
    coinmarketcap_base_url: str = os.getenv("COINMARKETCAP_BASE_URL", "https://pro-api.coinmarketcap.com")
    gdelt_base_url: str = os.getenv("GDELT_BASE_URL", "https://api.gdeltproject.org")
    fear_greed_api_url: str = os.getenv("FEAR_GREED_API", "https://api.alternative.me/fng/")
    request_timeout: int = _get_int("REQUEST_TIMEOUT", 10)
    request_retries: int = _get_int("REQUEST_RETRIES", 3)
    default_interval: str = os.getenv("DEFAULT_INTERVAL", DEFAULT_INTERVAL)
    default_candle_limit: int = _get_int("DEFAULT_CANDLE_LIMIT", DEFAULT_CANDLE_LIMIT)
    symbols: str = os.getenv("SYMBOLS", ",".join(DEFAULT_SYMBOLS))
    auto_universe_top_n: int = _get_int("AUTO_UNIVERSE_TOP_N", 200)
    auto_universe_quote_asset: str = os.getenv("AUTO_UNIVERSE_QUOTE_ASSET", "USDT").upper()
    auto_universe_min_volume: float = _get_float("AUTO_UNIVERSE_MIN_VOLUME", 10_000_000.0)
    auto_universe_path_name: str = os.getenv("AUTO_UNIVERSE_PATH", "data/processed/market_universe_top200.csv")
    coingecko_api_key: str | None = _get_optional_str("COINGECKO_API_KEY")
    coinmarketcap_api_key: str | None = _get_optional_str("COINMARKETCAP_API_KEY")
    api_key_secret: str = os.getenv("API_KEY_SECRET", "local-dev-secret-change-me")
    jwt_secret: str = os.getenv("JWT_SECRET", os.getenv("API_KEY_SECRET", "local-dev-secret-change-me"))
    enable_binance: bool = _get_bool("ENABLE_BINANCE", True)
    enable_cryptocompare: bool = _get_bool("ENABLE_CRYPTOCOMPARE", True)
    enable_coingecko: bool = _get_bool("ENABLE_COINGECKO", True)
    enable_coinmarketcap: bool = _get_bool("ENABLE_COINMARKETCAP", False)
    enable_fear_greed: bool = _get_bool("ENABLE_FEAR_GREED", True)
    enable_gdelt: bool = _get_bool("ENABLE_GDELT", True)
    primary_market_source: str = os.getenv("PRIMARY_MARKET_SOURCE", "binance")
    fallback_sources: str = os.getenv("FALLBACK_SOURCES", "coingecko,coinmarketcap")
    external_market_page_size: int = _get_int("EXTERNAL_MARKET_PAGE_SIZE", 250)
    external_market_max_pages: int = _get_int("EXTERNAL_MARKET_MAX_PAGES", 2)
    ranking_mode: str = os.getenv("RANKING_MODE", "heuristic")
    ranking_ml_weight: float = _get_float("RANKING_ML_WEIGHT", 0.7)
    ranking_heuristic_weight: float = _get_float("RANKING_HEURISTIC_WEIGHT", 0.3)
    ranking_news_weight: float = _get_float("RANKING_NEWS_WEIGHT", 0.0)
    market_target_name: str = os.getenv("MARKET_TARGET_NAME", "up_move_target")
    target_horizon_bars: int = _get_int("TARGET_HORIZON_BARS", 6)
    target_threshold_pct: float = _get_float("TARGET_THRESHOLD_PCT", 0.01)
    training_train_fraction: float = _get_float("TRAINING_TRAIN_FRACTION", 0.8)
    nlp_model_name: str = os.getenv("NLP_MODEL_NAME", "distilbert-base-uncased-finetuned-sst-2-english")
    nlp_topic_model_name: str = os.getenv("NLP_TOPIC_MODEL_NAME", "facebook/bart-large-mnli")
    huggingface_sentiment_dataset: str = os.getenv("HUGGINGFACE_SENTIMENT_DATASET", "financial_phrasebank")
    ranking_news_lookback_hours: int = _get_int("RANKING_NEWS_LOOKBACK_HOURS", 72)
    optuna_trials: int = _get_int("OPTUNA_TRIALS", 20)
    short_window: int = _get_int("SHORT_WINDOW", 9)
    long_window: int = _get_int("LONG_WINDOW", 21)
    rsi_window: int = _get_int("RSI_WINDOW", 14)
    volatility_window: int = _get_int("VOLATILITY_WINDOW", 20)
    volume_window: int = _get_int("VOLUME_WINDOW", 20)
    momentum_window: int = _get_int("MOMENTUM_WINDOW", 5)
    backtest_initial_cash: float = _get_float("BACKTEST_INITIAL_CASH", 10_000.0)
    backtest_fee_rate: float = _get_float("BACKTEST_FEE_RATE", 0.001)
    paper_initial_cash: float = _get_float("PAPER_INITIAL_CASH", 10_000.0)
    paper_max_positions: int = _get_int("PAPER_MAX_POSITIONS", 5)
    paper_position_size: float = _get_float("PAPER_POSITION_SIZE", 0.2)
    paper_fee_rate: float = _get_float("PAPER_FEE_RATE", 0.001)
    default_order_usd: float = _get_float("DEFAULT_ORDER_USD", 15.0)
    min_position_usd: float = _get_float("MIN_POSITION_USD", 15.0)
    max_position_usd: float = _get_float("MAX_POSITION_USD", 25.0)
    risk_per_trade: float = _get_float("RISK_PER_TRADE", 0.10)
    rank_buy_threshold: float = _get_float("RANK_BUY_THRESHOLD", 0.6)
    rank_sell_threshold: float = _get_float("RANK_SELL_THRESHOLD", 0.4)
    binance_api_key: str | None = _get_optional_str("BINANCE_API_KEY")
    binance_api_secret: str | None = _get_optional_str("BINANCE_API_SECRET")
    live_trading_enabled: bool = _get_bool("LIVE_TRADING_ENABLED", False)
    live_trading_mode: str = os.getenv("LIVE_TRADING_MODE", "paper").strip().lower()
    live_market_type: str = os.getenv("LIVE_MARKET_TYPE", "spot").lower()
    live_testnet_base_url: str = os.getenv("BINANCE_TESTNET_BASE_URL", "https://testnet.binance.vision/api")
    live_kill_switch_enabled: bool = _get_bool("LIVE_KILL_SWITCH_ENABLED", True)
    live_emergency_stop: bool = _get_bool("LIVE_EMERGENCY_STOP", False)
    live_allow_live_mode: bool = _get_bool("LIVE_ALLOW_LIVE_MODE", False)
    live_require_explicit_confirmation: bool = _get_bool("LIVE_REQUIRE_EXPLICIT_CONFIRMATION", True)
    live_allowed_symbols: str = os.getenv("LIVE_ALLOWED_SYMBOLS", "BTCUSDT,ETHUSDT,SOLUSDT")
    max_open_trades: int = _get_int("MAX_OPEN_TRADES", 3)
    max_position_size_pct: float = _get_float("MAX_POSITION_SIZE_PCT", 0.02)
    max_daily_loss_pct: float = _get_float("MAX_DAILY_LOSS_PCT", 0.03)
    max_drawdown_allowed: float = _get_float("MAX_DRAWDOWN_ALLOWED", 0.20)
    max_account_exposure_pct: float = _get_float("MAX_ACCOUNT_EXPOSURE_PCT", 0.20)
    stop_loss_pct: float = _get_float("STOP_LOSS_PCT", 0.02)
    take_profit_pct: float = _get_float("TAKE_PROFIT_PCT", 0.04)
    trailing_stop_pct: float = _get_float("TRAILING_STOP_PCT", 0.01)
    min_confidence_score: float = _get_float("MIN_CONFIDENCE_SCORE", 0.45)
    min_model_confidence: float = _get_float("MIN_MODEL_CONFIDENCE", 0.55)
    min_notional_usdt: float = _get_float("MIN_NOTIONAL_USDT", 10.0)
    min_trade_value: float = _get_float("MIN_TRADE_VALUE", 10.0)
    min_balance_required: float = _get_float("MIN_BALANCE_REQUIRED", 20.0)
    order_size_usdt: float = _get_float("ORDER_SIZE_USDT", _get_float("DEFAULT_ORDER_SIZE_USDT", 15.0))
    max_consecutive_losses: int = _get_int("MAX_CONSECUTIVE_LOSSES", 3)
    auto_sync_account: bool = _get_bool("AUTO_SYNC_ACCOUNT", True)
    auto_sync_interval_seconds: int = _get_int("AUTO_SYNC_INTERVAL_SECONDS", 300)
    enable_order_retry: bool = _get_bool("ENABLE_ORDER_RETRY", True)
    max_order_retries: int = _get_int("MAX_ORDER_RETRIES", 3)
    enable_cooldown: bool = _get_bool("ENABLE_COOLDOWN", True)
    cooldown_minutes_per_symbol: int = _get_int("COOLDOWN_MINUTES_PER_SYMBOL", 30)
    enable_duplicate_position_block: bool = _get_bool("ENABLE_DUPLICATE_POSITION_BLOCK", True)
    enable_orphan_position_detection: bool = _get_bool("ENABLE_ORPHAN_POSITION_DETECTION", True)
    enable_position_timeout: bool = _get_bool("ENABLE_POSITION_TIMEOUT", True)
    max_position_duration_hours: int = _get_int("MAX_POSITION_DURATION_HOURS", 12)
    enable_partial_take_profit: bool = _get_bool("ENABLE_PARTIAL_TAKE_PROFIT", True)
    partial_take_profit_pct: float = _get_float("PARTIAL_TAKE_PROFIT_PCT", 0.02)
    partial_take_profit_size: float = _get_float("PARTIAL_TAKE_PROFIT_SIZE", 0.5)
    enable_break_even: bool = _get_bool("ENABLE_BREAK_EVEN", True)
    break_even_trigger_pct: float = _get_float("BREAK_EVEN_TRIGGER_PCT", 0.01)
    break_even_offset_pct: float = _get_float("BREAK_EVEN_OFFSET_PCT", 0.001)
    auto_close_on_api_error: bool = _get_bool("AUTO_CLOSE_ON_API_ERROR", True)
    auto_close_on_daily_loss: bool = _get_bool("AUTO_CLOSE_ON_DAILY_LOSS", True)
    enable_market_regime_filter: bool = _get_bool("ENABLE_MARKET_REGIME_FILTER", True)
    allow_trades_in_sideways_market: bool = _get_bool("ALLOW_TRADES_IN_SIDEWAYS_MARKET", False)
    min_relative_volume: float = _get_float("MIN_RELATIVE_VOLUME", 1.2)
    min_trend_strength: float = _get_float("MIN_TREND_STRENGTH", 0.6)
    min_breakout_strength: float = _get_float("MIN_BREAKOUT_STRENGTH", 0.008)
    block_overbought_rsi: bool = _get_bool("BLOCK_OVERBOUGHT_RSI", True)
    max_buy_rsi: float = _get_float("MAX_BUY_RSI", 68.0)
    enable_btc_confirmation: bool = _get_bool("ENABLE_BTC_CONFIRMATION", True)
    btc_confirmation_symbol: str = os.getenv("BTC_CONFIRMATION_SYMBOL", "BTCUSDT").upper()
    btc_confirmation_min_score: float = _get_float("BTC_CONFIRMATION_MIN_SCORE", 0.30)
    auto_retrain_enabled: bool = _get_bool("AUTO_RETRAIN_ENABLED", True)
    auto_retrain_min_trades: int = _get_int("AUTO_RETRAIN_MIN_TRADES", 50)
    auto_retrain_interval_hours: int = _get_int("AUTO_RETRAIN_INTERVAL_HOURS", 24)
    auto_retrain_min_win_rate: float = _get_float("AUTO_RETRAIN_MIN_WIN_RATE", 0.45)
    auto_retrain_max_drawdown: float = _get_float("AUTO_RETRAIN_MAX_DRAWDOWN", 0.15)
    auto_retrain_min_model_score: float = _get_float("AUTO_RETRAIN_MIN_MODEL_SCORE", 0.55)
    llm_enable_external: bool = _get_bool("LLM_ENABLE_EXTERNAL", False)
    llm_force_local_fallback: bool = _get_bool("LLM_FORCE_LOCAL_FALLBACK", True)
    llm_timeout_seconds: int = _get_int("LLM_TIMEOUT_SECONDS", 20)
    llm_max_retries: int = _get_int("LLM_MAX_RETRIES", 2)
    openrouter_api_key: str | None = _get_optional_str("OPENROUTER_API_KEY")
    openrouter_base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
    market_agent_model: str = os.getenv("MARKET_AGENT_MODEL", "nvidia/nemotron-3-super-120b-a12b:free").strip()
    market_agent_fallback_model: str = os.getenv("MARKET_AGENT_FALLBACK_MODEL", "local-market-heuristic").strip()
    news_agent_model: str = os.getenv("NEWS_AGENT_MODEL", "openai/gpt-oss-120b:free").strip()
    news_agent_fallback_model: str = os.getenv("NEWS_AGENT_FALLBACK_MODEL", "local-news-heuristic").strip()
    risk_agent_model: str = os.getenv("RISK_AGENT_MODEL", "minimax/minimax-m2.5:free").strip()
    risk_agent_fallback_model: str = os.getenv("RISK_AGENT_FALLBACK_MODEL", "local-risk-heuristic").strip()
    execution_agent_model: str = os.getenv("EXECUTION_AGENT_MODEL", "minimax/minimax-m2.5:free").strip()
    execution_agent_fallback_model: str = os.getenv("EXECUTION_AGENT_FALLBACK_MODEL", "local-execution-policy").strip()
    memory_agent_model: str = os.getenv("MEMORY_AGENT_MODEL", "arcee-ai/trinity-large-preview:free").strip()
    memory_agent_fallback_model: str = os.getenv("MEMORY_AGENT_FALLBACK_MODEL", "local-memory-engine").strip()
    multi_agent_buy_threshold: float = _get_float("MULTI_AGENT_BUY_THRESHOLD", 0.66)
    multi_agent_sell_threshold: float = _get_float("MULTI_AGENT_SELL_THRESHOLD", 0.34)
    multi_agent_train_on_runtime_cycle: bool = _get_bool("MULTI_AGENT_TRAIN_ON_RUNTIME_CYCLE", True)
    multi_agent_apply_dynamic_thresholds_on_runtime_cycle: bool = _get_bool("MULTI_AGENT_APPLY_DYNAMIC_THRESHOLDS_ON_RUNTIME_CYCLE", True)
    continuous_learning_enabled: bool = _get_bool("CONTINUOUS_LEARNING_ENABLED", True)
    dynamic_thresholds_enabled: bool = _get_bool("DYNAMIC_THRESHOLDS_ENABLED", True)
    echo_sql: bool = _get_bool("ECHO_SQL", False)
    enable_scheduler: bool = _get_bool("ENABLE_SCHEDULER", True)
    enable_continuous_pipeline: bool = _get_bool("ENABLE_CONTINUOUS_PIPELINE", True)
    enable_live_simulated: bool = _get_bool("ENABLE_LIVE_SIMULATED", False)
    cycle_interval_seconds: int = _get_int("CYCLE_INTERVAL_SECONDS", 300)
    news_refresh_interval_seconds: int = _get_int("NEWS_REFRESH_INTERVAL_SECONDS", 3600)
    heartbeat_interval_seconds: int = _get_int("HEARTBEAT_INTERVAL_SECONDS", 60)
    daemon_pid_file_name: str = os.getenv("DAEMON_PID_FILE", "data/runtime/alphascope.pid")
    daemon_status_file_name: str = os.getenv("DAEMON_STATUS_FILE", "data/runtime/daemon_status.json")
    heartbeat_file_name: str = os.getenv("HEARTBEAT_FILE", "data/runtime/heartbeat.json")
    max_consecutive_errors: int = _get_int("MAX_CONSECUTIVE_ERRORS", 10)
    retry_backoff_seconds: int = _get_int("RETRY_BACKOFF_SECONDS", 5)
    telegram_enabled: bool = _get_bool("TELEGRAM_ENABLED", _get_bool("ENABLE_TELEGRAM_ALERTS", False))
    enable_telegram_alerts: bool = _get_bool("ENABLE_TELEGRAM_ALERTS", _get_bool("TELEGRAM_ENABLED", False))
    telegram_bot_token: str | None = _get_optional_str("TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str | None = _get_optional_str("TELEGRAM_CHAT_ID")
    telegram_parse_mode: str = os.getenv("TELEGRAM_PARSE_MODE", "Markdown")
    telegram_poll_seconds: int = _get_int("TELEGRAM_POLL_SECONDS", 1)
    alerts_history_file_name: str = os.getenv("ALERTS_HISTORY_FILE", "data/runtime/alerts/alerts.jsonl")
    alerts_state_file_name: str = os.getenv("ALERTS_STATE_FILE", "data/runtime/alerts/alerts_state.json")

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        return f"sqlite:///{self.sqlite_path.as_posix()}"

    @property
    def binance_api_enabled(self) -> bool:
        return self.enable_binance

    @property
    def coingecko_api_enabled(self) -> bool:
        return self.enable_coingecko

    @property
    def cryptocompare_api_enabled(self) -> bool:
        return self.enable_cryptocompare

    @property
    def coinmarketcap_api_enabled(self) -> bool:
        return self.enable_coinmarketcap and bool(self.coinmarketcap_api_key)

    @property
    def fear_greed_api_enabled(self) -> bool:
        return self.enable_fear_greed

    @property
    def coingecko_using_api_key(self) -> bool:
        return bool(self.coingecko_api_key)

    @property
    def symbol_list(self) -> list[str]:
        return [symbol.strip().upper() for symbol in self.symbols.split(",") if symbol.strip()]

    @property
    def fallback_sources_list(self) -> list[str]:
        return [source.strip().lower() for source in self.fallback_sources.split(",") if source.strip()]

    @property
    def live_allowed_symbols_list(self) -> list[str]:
        return [symbol.strip().upper() for symbol in self.live_allowed_symbols.split(",") if symbol.strip()]

    @property
    def external_llm_available(self) -> bool:
        return self.llm_enable_external and not self.llm_force_local_fallback and bool(self.openrouter_api_key)

    @property
    def multi_agent_model_registry(self) -> dict[str, dict[str, str | bool]]:
        external_active = self.external_llm_available
        return {
            "market": {
                "primary": self.market_agent_model,
                "fallback": self.market_agent_fallback_model,
                "active": self.market_agent_model if external_active else self.market_agent_fallback_model,
                "external": external_active,
            },
            "news": {
                "primary": self.news_agent_model,
                "fallback": self.news_agent_fallback_model,
                "active": self.news_agent_model if external_active else self.news_agent_fallback_model,
                "external": external_active,
            },
            "risk": {
                "primary": self.risk_agent_model,
                "fallback": self.risk_agent_fallback_model,
                "active": self.risk_agent_model if external_active else self.risk_agent_fallback_model,
                "external": external_active,
            },
            "execution": {
                "primary": self.execution_agent_model,
                "fallback": self.execution_agent_fallback_model,
                "active": self.execution_agent_model if external_active else self.execution_agent_fallback_model,
                "external": external_active,
            },
            "memory": {
                "primary": self.memory_agent_model,
                "fallback": self.memory_agent_fallback_model,
                "active": self.memory_agent_model if external_active else self.memory_agent_fallback_model,
                "external": external_active,
            },
        }

    @property
    def market_universe_dir(self) -> Path:
        return self.data_dir / "market_universe"

    @property
    def raw_data_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def raw_market_data_dir(self) -> Path:
        return self.raw_data_dir / "market"

    @property
    def cryptocompare_raw_dir(self) -> Path:
        return self.raw_market_data_dir / "cryptocompare"

    @property
    def fear_greed_raw_dir(self) -> Path:
        return self.raw_market_data_dir / "fear_greed"

    @property
    def raw_news_data_dir(self) -> Path:
        return self.raw_data_dir / "news"

    @property
    def external_data_dir(self) -> Path:
        return self.data_dir / "external"

    @property
    def training_data_dir(self) -> Path:
        return self.data_dir / "training"

    @property
    def processed_data_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def auto_universe_path(self) -> Path:
        return ROOT_DIR / self.auto_universe_path_name

    @property
    def labels_data_dir(self) -> Path:
        return self.data_dir / "labels"

    @property
    def news_data_dir(self) -> Path:
        return self.data_dir / "news"

    @property
    def kaggle_data_dir(self) -> Path:
        return ROOT_DIR / self.kaggle_data_dir_name

    @property
    def hf_datasets_dir(self) -> Path:
        return ROOT_DIR / self.hf_datasets_dir_name

    @property
    def market_dataset_path(self) -> Path:
        return ROOT_DIR / self.market_dataset_path_name

    @property
    def news_dataset_path(self) -> Path:
        return ROOT_DIR / self.news_dataset_path_name

    @property
    def model_dir(self) -> Path:
        return ROOT_DIR / "models"

    @property
    def market_model_dir(self) -> Path:
        return self.model_dir / "market"

    @property
    def production_model_dir(self) -> Path:
        return self.model_dir / "production"

    @property
    def staging_model_dir(self) -> Path:
        return self.model_dir / "staging"

    @property
    def archive_model_dir(self) -> Path:
        return self.model_dir / "archive"

    @property
    def best_model_dir(self) -> Path:
        return self.model_dir / "best"

    @property
    def experiments_model_dir(self) -> Path:
        return self.model_dir / "experiments"

    @property
    def nlp_model_dir(self) -> Path:
        return self.model_dir / "nlp"

    @property
    def market_model_path(self) -> Path:
        return self.market_model_dir / "best_market_model.joblib"

    @property
    def news_model_path(self) -> Path:
        return self.nlp_model_dir / "news_sentiment_model.joblib"

    @property
    def scored_news_path(self) -> Path:
        return self.processed_data_dir / "scored_news_latest.csv"

    @property
    def optuna_dir(self) -> Path:
        return self.data_dir / "optuna"

    @property
    def runtime_dir(self) -> Path:
        return self.data_dir / "runtime"

    @property
    def runtime_log_dir(self) -> Path:
        return self.log_dir / "runtime"

    @property
    def live_trading_state_file(self) -> Path:
        return self.runtime_dir / "live_trading_state.json"

    @property
    def live_trading_log_path(self) -> Path:
        return self.log_dir / "live_trading.log"

    @property
    def risk_manager_log_path(self) -> Path:
        return self.log_dir / "risk_manager.log"

    @property
    def order_manager_log_path(self) -> Path:
        return self.log_dir / "order_manager.log"

    @property
    def account_manager_log_path(self) -> Path:
        return self.log_dir / "account_manager.log"

    @property
    def live_binance_base_url(self) -> str:
        if self.live_trading_mode == "testnet":
            return self.live_testnet_base_url
        return self.binance_base_url

    @property
    def live_mode_safe(self) -> bool:
        return self.live_trading_mode in {"testnet", "paper"} or not self.live_trading_enabled

    @property
    def daemon_pid_file(self) -> Path:
        return ROOT_DIR / self.daemon_pid_file_name

    @property
    def daemon_status_file(self) -> Path:
        return ROOT_DIR / self.daemon_status_file_name

    @property
    def heartbeat_file(self) -> Path:
        return ROOT_DIR / self.heartbeat_file_name

    @property
    def alerts_history_file(self) -> Path:
        return ROOT_DIR / self.alerts_history_file_name

    @property
    def alerts_state_file(self) -> Path:
        return ROOT_DIR / self.alerts_state_file_name

    @property
    def DATABASE_URL(self) -> str:  # legacy compatibility shim
        return self.database_url

    @property
    def DEBUG(self) -> bool:  # legacy compatibility shim
        return self.log_level == "DEBUG"

    @property
    def API_KEY_SECRET(self) -> str:  # legacy compatibility shim
        return self.api_key_secret

    def api_status_summary(self) -> dict[str, str]:
        """Return a user-facing summary of external API readiness."""
        return {
            "binance": "enabled" if self.binance_api_enabled else "disabled by flag",
            "cryptocompare": "enabled" if self.cryptocompare_api_enabled else "disabled by flag",
            "coingecko": "enabled with api key" if self.coingecko_using_api_key else "enabled without api key",
            "coinmarketcap": (
                "enabled with api key"
                if self.coinmarketcap_api_enabled
                else "disabled"
                if not self.enable_coinmarketcap
                else "disabled because COINMARKETCAP_API_KEY is empty"
            ),
            "gdelt": "enabled" if self.enable_gdelt else "disabled by flag",
            "fear_greed": "enabled" if self.fear_greed_api_enabled else "disabled by flag",
            "openrouter": (
                "enabled with fallback protection"
                if self.external_llm_available
                else "configured but forced local fallback"
                if self.llm_enable_external and self.llm_force_local_fallback
                else "disabled because OPENROUTER_API_KEY is empty"
                if self.llm_enable_external and not self.openrouter_api_key
                else "disabled"
            ),
        }

    def validate(self) -> None:
        """Validate runtime configuration and fail fast on invalid combinations."""
        valid_ranking_modes = {"heuristic", "ml", "hybrid", "hybrid_with_news"}
        if self.ranking_mode not in valid_ranking_modes:
            raise RuntimeError(f"Invalid RANKING_MODE: {self.ranking_mode}. Expected one of {sorted(valid_ranking_modes)}.")
        if self.large_data_format not in {"parquet", "csv"}:
            raise RuntimeError(f"Invalid LARGE_DATA_FORMAT: {self.large_data_format}. Expected 'parquet' or 'csv'.")
        if self.ranking_mode == "hybrid_with_news" and self.ranking_news_weight <= 0:
            raise RuntimeError("RANKING_MODE=hybrid_with_news requires RANKING_NEWS_WEIGHT > 0.")
        if self.ranking_news_weight < 0 or self.ranking_ml_weight < 0 or self.ranking_heuristic_weight < 0:
            raise RuntimeError("Ranking weights must be non-negative.")
        if self.target_horizon_bars <= 0:
            raise RuntimeError("TARGET_HORIZON_BARS must be greater than zero.")
        if self.target_threshold_pct < 0:
            raise RuntimeError("TARGET_THRESHOLD_PCT must be non-negative.")
        base_urls = {
            "BINANCE_BASE_URL": self.binance_base_url,
            "BINANCE_TESTNET_BASE_URL": self.live_testnet_base_url,
            "CRYPTOCOMPARE_BASE_URL": self.cryptocompare_base_url,
            "COINGECKO_BASE_URL": self.coingecko_base_url,
            "COINMARKETCAP_BASE_URL": self.coinmarketcap_base_url,
            "GDELT_BASE_URL": self.gdelt_base_url,
            "FEAR_GREED_API": self.fear_greed_api_url,
            "OPENROUTER_BASE_URL": self.openrouter_base_url,
        }
        for name, value in base_urls.items():
            if not _is_valid_http_url(value):
                raise RuntimeError(f"Invalid {name}: {value}. Expected an http or https base URL.")
        if self.enable_binance and "binance" not in self.binance_base_url.lower():
            logger.warning(
                "BINANCE_BASE_URL does not look like a standard Binance host: %s",
                self.binance_base_url,
            )
        if self.enable_coingecko and not self.coingecko_api_key:
            logger.warning(
                "COINGECKO_API_KEY is empty. CoinGecko will run in unauthenticated mode with stricter public rate limits."
            )
        if self.enable_coinmarketcap and not self.coinmarketcap_api_key:
            logger.warning(
                "ENABLE_COINMARKETCAP=true but COINMARKETCAP_API_KEY is empty. CoinMarketCap will be disabled without breaking the pipeline."
            )
        if self.llm_enable_external and not self.openrouter_api_key:
            logger.warning(
                "LLM_ENABLE_EXTERNAL=true but OPENROUTER_API_KEY is empty. Multi-agent inference will stay on local fallback heuristics."
            )
        if self.llm_force_local_fallback and self.llm_enable_external:
            logger.warning(
                "LLM_FORCE_LOCAL_FALLBACK=true. External LLMs remain configured but AlphaScope will operate on local multi-agent heuristics until the flag is disabled."
            )
        if (self.telegram_enabled or self.enable_telegram_alerts) and (not self.telegram_bot_token or not self.telegram_chat_id):
            logger.warning(
                "Telegram is enabled but TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is empty. Telegram delivery will be skipped."
            )
        if self.live_trading_mode not in {"paper", "testnet", "live"}:
            raise RuntimeError("LIVE_TRADING_MODE must be 'paper', 'testnet' or 'live'.")
        if self.log_format not in {"plain", "json"}:
            raise RuntimeError("LOG_FORMAT must be 'plain' or 'json'.")
        if self.live_trading_enabled and self.live_trading_mode == "live" and not self.live_allow_live_mode:
            raise RuntimeError(
                "LIVE_TRADING_ENABLED=true with LIVE_TRADING_MODE=live requires LIVE_ALLOW_LIVE_MODE=true for explicit activation."
            )
        if self.live_trading_mode == "live" and self.live_require_explicit_confirmation and not self.live_allow_live_mode:
            raise RuntimeError("Live trading confirmation guard blocked startup. Set LIVE_ALLOW_LIVE_MODE=true only after explicit review.")
        if self.live_market_type != "spot":
            raise RuntimeError("LIVE_MARKET_TYPE currently supports only 'spot'.")
        if self.max_open_trades <= 0:
            raise RuntimeError("MAX_OPEN_TRADES must be greater than zero.")
        if self.default_order_usd <= 0:
            raise RuntimeError("DEFAULT_ORDER_USD must be greater than zero.")
        if self.min_position_usd <= 0:
            raise RuntimeError("MIN_POSITION_USD must be greater than zero.")
        if self.max_position_usd <= 0:
            raise RuntimeError("MAX_POSITION_USD must be greater than zero.")
        if self.min_position_usd > self.max_position_usd:
            raise RuntimeError("MIN_POSITION_USD cannot be greater than MAX_POSITION_USD.")
        if self.default_order_usd > self.max_position_usd:
            raise RuntimeError("DEFAULT_ORDER_USD cannot be greater than MAX_POSITION_USD.")
        pct_fields = {
            "RISK_PER_TRADE": self.risk_per_trade,
            "MAX_POSITION_SIZE_PCT": self.max_position_size_pct,
            "MAX_DAILY_LOSS_PCT": self.max_daily_loss_pct,
            "MAX_DRAWDOWN_ALLOWED": self.max_drawdown_allowed,
            "MAX_ACCOUNT_EXPOSURE_PCT": self.max_account_exposure_pct,
            "STOP_LOSS_PCT": self.stop_loss_pct,
            "TAKE_PROFIT_PCT": self.take_profit_pct,
            "TRAILING_STOP_PCT": self.trailing_stop_pct,
        }
        for name, value in pct_fields.items():
            if value <= 0 or value >= 1:
                raise RuntimeError(f"{name} must be between 0 and 1.")
        if self.min_confidence_score < 0 or self.min_confidence_score > 1:
            raise RuntimeError("MIN_CONFIDENCE_SCORE must be between 0 and 1.")
        if self.multi_agent_buy_threshold < 0 or self.multi_agent_buy_threshold > 1:
            raise RuntimeError("MULTI_AGENT_BUY_THRESHOLD must be between 0 and 1.")
        if self.multi_agent_sell_threshold < 0 or self.multi_agent_sell_threshold > 1:
            raise RuntimeError("MULTI_AGENT_SELL_THRESHOLD must be between 0 and 1.")
        if self.multi_agent_sell_threshold >= self.multi_agent_buy_threshold:
            raise RuntimeError("MULTI_AGENT_SELL_THRESHOLD must be lower than MULTI_AGENT_BUY_THRESHOLD.")
        if self.min_notional_usdt <= 0:
            raise RuntimeError("MIN_NOTIONAL_USDT must be greater than zero.")
        if self.min_trade_value <= 0:
            raise RuntimeError("MIN_TRADE_VALUE must be greater than zero.")
        if self.min_balance_required <= 0:
            raise RuntimeError("MIN_BALANCE_REQUIRED must be greater than zero.")
        if self.order_size_usdt <= 0:
            raise RuntimeError("ORDER_SIZE_USDT must be greater than zero.")
        if self.min_model_confidence < 0 or self.min_model_confidence > 1:
            raise RuntimeError("MIN_MODEL_CONFIDENCE must be between 0 and 1.")
        if self.max_position_duration_hours <= 0:
            raise RuntimeError("MAX_POSITION_DURATION_HOURS must be greater than zero.")
        if self.auto_retrain_min_trades <= 0:
            raise RuntimeError("AUTO_RETRAIN_MIN_TRADES must be greater than zero.")
        if self.auto_retrain_interval_hours <= 0:
            raise RuntimeError("AUTO_RETRAIN_INTERVAL_HOURS must be greater than zero.")
        if self.auto_retrain_min_win_rate < 0 or self.auto_retrain_min_win_rate > 1:
            raise RuntimeError("AUTO_RETRAIN_MIN_WIN_RATE must be between 0 and 1.")
        if self.auto_retrain_max_drawdown <= 0 or self.auto_retrain_max_drawdown >= 1:
            raise RuntimeError("AUTO_RETRAIN_MAX_DRAWDOWN must be between 0 and 1.")
        if self.auto_retrain_min_model_score < 0 or self.auto_retrain_min_model_score > 1:
            raise RuntimeError("AUTO_RETRAIN_MIN_MODEL_SCORE must be between 0 and 1.")
        if self.llm_timeout_seconds <= 0:
            raise RuntimeError("LLM_TIMEOUT_SECONDS must be greater than zero.")
        if self.llm_max_retries < 0:
            raise RuntimeError("LLM_MAX_RETRIES cannot be negative.")
        for name, value in {
            "MARKET_AGENT_MODEL": self.market_agent_model,
            "MARKET_AGENT_FALLBACK_MODEL": self.market_agent_fallback_model,
            "NEWS_AGENT_MODEL": self.news_agent_model,
            "NEWS_AGENT_FALLBACK_MODEL": self.news_agent_fallback_model,
            "RISK_AGENT_MODEL": self.risk_agent_model,
            "RISK_AGENT_FALLBACK_MODEL": self.risk_agent_fallback_model,
            "EXECUTION_AGENT_MODEL": self.execution_agent_model,
            "EXECUTION_AGENT_FALLBACK_MODEL": self.execution_agent_fallback_model,
            "MEMORY_AGENT_MODEL": self.memory_agent_model,
            "MEMORY_AGENT_FALLBACK_MODEL": self.memory_agent_fallback_model,
        }.items():
            if not value:
                raise RuntimeError(f"{name} cannot be empty.")
        if self.live_trading_enabled and self.live_trading_mode == "live" and not (self.binance_api_key and self.binance_api_secret):
            logger.warning("LIVE_TRADING_ENABLED=true in live mode without Binance credentials. Order execution will fail closed.")


settings = Settings()
settings.validate()
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.log_dir.mkdir(parents=True, exist_ok=True)
settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
settings.raw_data_dir.mkdir(parents=True, exist_ok=True)
settings.raw_market_data_dir.mkdir(parents=True, exist_ok=True)
settings.cryptocompare_raw_dir.mkdir(parents=True, exist_ok=True)
settings.fear_greed_raw_dir.mkdir(parents=True, exist_ok=True)
settings.raw_news_data_dir.mkdir(parents=True, exist_ok=True)
settings.external_data_dir.mkdir(parents=True, exist_ok=True)
settings.market_universe_dir.mkdir(parents=True, exist_ok=True)
settings.training_data_dir.mkdir(parents=True, exist_ok=True)
settings.processed_data_dir.mkdir(parents=True, exist_ok=True)
settings.labels_data_dir.mkdir(parents=True, exist_ok=True)
settings.news_data_dir.mkdir(parents=True, exist_ok=True)
settings.kaggle_data_dir.mkdir(parents=True, exist_ok=True)
settings.hf_datasets_dir.mkdir(parents=True, exist_ok=True)
settings.market_dataset_path.parent.mkdir(parents=True, exist_ok=True)
settings.news_dataset_path.parent.mkdir(parents=True, exist_ok=True)
settings.model_dir.mkdir(parents=True, exist_ok=True)
settings.market_model_dir.mkdir(parents=True, exist_ok=True)
settings.production_model_dir.mkdir(parents=True, exist_ok=True)
settings.staging_model_dir.mkdir(parents=True, exist_ok=True)
settings.archive_model_dir.mkdir(parents=True, exist_ok=True)
settings.best_model_dir.mkdir(parents=True, exist_ok=True)
settings.experiments_model_dir.mkdir(parents=True, exist_ok=True)
settings.nlp_model_dir.mkdir(parents=True, exist_ok=True)
settings.optuna_dir.mkdir(parents=True, exist_ok=True)
settings.runtime_dir.mkdir(parents=True, exist_ok=True)
settings.runtime_log_dir.mkdir(parents=True, exist_ok=True)
settings.live_trading_state_file.parent.mkdir(parents=True, exist_ok=True)
settings.daemon_pid_file.parent.mkdir(parents=True, exist_ok=True)
settings.daemon_status_file.parent.mkdir(parents=True, exist_ok=True)
settings.heartbeat_file.parent.mkdir(parents=True, exist_ok=True)
settings.alerts_history_file.parent.mkdir(parents=True, exist_ok=True)
settings.alerts_state_file.parent.mkdir(parents=True, exist_ok=True)
