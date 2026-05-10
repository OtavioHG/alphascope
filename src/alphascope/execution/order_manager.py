from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from alphascope.alerts import AlertDispatcher
from alphascope.config.settings import settings
from alphascope.execution.account_manager import AccountManager
from alphascope.execution.compat import (
    BinanceAPIException,
    BinanceOrderException,
    EXECUTION_STATUS_CLOSED,
    EXECUTION_STATUS_BLOCKED_INSUFFICIENT_BALANCE,
    EXECUTION_STATUS_BLOCKED_MIN_NOTIONAL,
    EXECUTION_STATUS_BLOCKED_INVALID_QUANTITY,
    EXECUTION_STATUS_BLOCKED_INVALID_STEP_SIZE,
    EXECUTION_STATUS_OPEN,
    get_safe_sell_quantity,
    get_safe_quantity,
    call_authenticated_binance,
    is_binance_timestamp_error,
    retry,
    retry_if_exception_type,
    sync_binance_time,
    stop_after_attempt,
    wait_exponential,
)
from alphascope.execution.logging_utils import build_component_logger
from alphascope.execution.quantity_normalizer import (
    is_quantity_precision_error_message,
    validate_order_quantity,
)
from alphascope.storage.repositories import StorageRepository


class OrderRequest(BaseModel):
    symbol: str
    side: str
    quantity: float | None = Field(default=None)
    order_type: str
    price: float | None = None
    score: float | None = None
    source: str = "alphascope"


class OrderBlockedError(RuntimeError):
    def __init__(self, reason: str, details: dict[str, Any]) -> None:
        super().__init__(f"Order blocked: {reason}")
        self.reason = reason
        self.details = details


class OrderManager:
    def __init__(
        self,
        client: Any,
        repository: StorageRepository | None = None,
        alert_dispatcher: AlertDispatcher | None = None,
        account_manager: AccountManager | None = None,
    ) -> None:
        self.client = client
        self.repository = repository or StorageRepository()
        self.alert_dispatcher = alert_dispatcher or AlertDispatcher()
        self.account_manager = account_manager or AccountManager(client=client, repository=self.repository)
        self.logger = build_component_logger("order_manager", settings.order_manager_log_path)
        self._pending_orders: set[str] = set()
        self._exchange_info_cache: dict[str, Any] | None = None

    @staticmethod
    def _max_allowed_clock_drift_ms() -> int | None:
        return 5000 if settings.live_trading_mode == "live" else None

    def place_market_buy(self, symbol: str, quantity: float, *, score: float | None = None, source: str = "ranking") -> dict[str, Any]:
        return self._place_order(OrderRequest(symbol=symbol.upper(), side="BUY", quantity=quantity, order_type="MARKET", score=score, source=source))

    def place_market_sell(self, symbol: str, quantity: float | None = None, *, score: float | None = None, source: str = "stop_manager") -> dict[str, Any]:
        return self._place_order(OrderRequest(symbol=symbol.upper(), side="SELL", quantity=quantity, order_type="MARKET", score=score, source=source))

    def place_limit_buy(self, symbol: str, quantity: float, price: float, *, score: float | None = None, source: str = "ranking") -> dict[str, Any]:
        return self._place_order(OrderRequest(symbol=symbol.upper(), side="BUY", quantity=quantity, order_type="LIMIT", price=price, score=score, source=source))

    def place_limit_sell(self, symbol: str, quantity: float, price: float, *, score: float | None = None, source: str = "stop_manager") -> dict[str, Any]:
        return self._place_order(OrderRequest(symbol=symbol.upper(), side="SELL", quantity=quantity, order_type="LIMIT", price=price, score=score, source=source))

    def cancel_order(self, symbol: str, order_id: str) -> dict[str, Any]:
        response = call_authenticated_binance(
            self.client,
            self.client.cancel_order,
            symbol=symbol.upper(),
            orderId=order_id,
            logger=self.logger,
            sync_before=True,
            max_allowed_drift_ms=self._max_allowed_clock_drift_ms(),
        )
        self.logger.warning("symbol={} score=- saldo=- quantidade=- preco=- pnl=- risco=- motivo=cancel_order {}", symbol.upper(), order_id)
        return dict(response)

    def cancel_all_orders(self, symbol: str | None = None) -> list[dict[str, Any]]:
        open_orders = self.account_manager.get_open_orders(symbol=symbol.upper() if symbol else None)
        cancelled: list[dict[str, Any]] = []
        for order in open_orders:
            cancelled.append(self.cancel_order(str(order["symbol"]), str(order["orderId"])))
        return cancelled

    def get_order_status(self, symbol: str, order_id: str) -> dict[str, Any]:
        return dict(
            call_authenticated_binance(
                self.client,
                self.client.get_order,
                symbol=symbol.upper(),
                orderId=order_id,
                logger=self.logger,
                sync_before=True,
                max_allowed_drift_ms=self._max_allowed_clock_drift_ms(),
            )
        )

    def place_order(self, symbol: str, side: str, quantity: float | None, order_type: str = "MARKET", price: float | None = None) -> dict[str, Any]:
        request = OrderRequest(symbol=symbol.upper(), side=side.upper(), quantity=quantity, order_type=order_type.upper(), price=price)
        return self._place_order(request)

    @retry(
        reraise=True,
        stop=stop_after_attempt(max(settings.request_retries, 1)),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    )
    def _submit_to_binance(self, request: OrderRequest) -> dict[str, Any]:
        validation = self._normalize_and_validate_order(request)
        params: dict[str, Any] = {
            "symbol": request.symbol,
            "side": request.side,
            "type": request.order_type,
            "quantity": validation["normalized_quantity_str"],
        }
        if request.order_type == "LIMIT":
            params["timeInForce"] = "GTC"
            params["price"] = request.price
        response = dict(
            call_authenticated_binance(
                self.client,
                self.client.create_order,
                logger=self.logger,
                sync_before=True,
                max_allowed_drift_ms=self._max_allowed_clock_drift_ms(),
                **params,
            )
        )
        response["_normalized_quantity"] = validation["normalized_quantity"]
        response["_validation"] = validation
        response["_reference_price"] = validation["reference_price"]
        return response

    def _place_order(self, request: OrderRequest) -> dict[str, Any]:
        order_key = f"{request.symbol}:{request.side}:{request.order_type}"
        self._sync_before_order(request.symbol, source=f"before_{request.side.lower()}")
        if order_key in self._pending_orders:
            raise RuntimeError(f"Duplicate order blocked for {order_key}")
        self._pending_orders.add(order_key)
        try:
            response = self._submit_to_binance(request)
            finalized_request = self._request_with_filled_quantity(request, response)
            self._validate_response(response)
            persisted_status = EXECUTION_STATUS_CLOSED if self._is_sell_request(finalized_request) else EXECUTION_STATUS_OPEN
            self._persist_execution(finalized_request, response, status=persisted_status)
            self._log_order(finalized_request, response, "submitted")
            self._send_alert("trade_closed" if self._is_sell_request(finalized_request) else "trade_opened", finalized_request, response)
            self._sync_after_order(request.symbol, source=f"after_{request.side.lower()}")
            return response
        except BinanceAPIException as exc:
            if self._is_controlled_sell_error(request, exc):
                blocked_response = self._handle_controlled_sell_error(request, exc)
                self._sync_after_error(request.symbol, exc)
                return blocked_response
            if self._should_retry_with_normalized_quantity(exc):
                retried_request, response = self._retry_with_normalized_quantity(request, exc)
                self._validate_response(response)
                retried_status = EXECUTION_STATUS_CLOSED if self._is_sell_request(retried_request) else EXECUTION_STATUS_OPEN
                self._persist_execution(retried_request, response, status=retried_status)
                self._log_order(retried_request, response, "submitted_after_quantity_retry")
                self._send_alert("trade_closed" if self._is_sell_request(retried_request) else "trade_opened", retried_request, response)
                self._sync_after_order(request.symbol, source=f"after_retry_{request.side.lower()}")
                return response
            self._handle_binance_error(request, exc)
            self._sync_after_error(request.symbol, exc)
            raise
        except BinanceOrderException as exc:
            if self._is_sell_request(request):
                blocked_response = self._build_blocked_response(
                    request,
                    status=EXECUTION_STATUS_BLOCKED_INVALID_QUANTITY,
                    reason=str(exc),
                    validation={"validation_status": EXECUTION_STATUS_BLOCKED_INVALID_QUANTITY, "validation_reason": str(exc)},
                )
                self._sync_after_error(request.symbol, exc)
                return blocked_response
            if self._should_retry_with_normalized_quantity(exc):
                retried_request, response = self._retry_with_normalized_quantity(request, exc)
                self._validate_response(response)
                retried_status = EXECUTION_STATUS_CLOSED if self._is_sell_request(retried_request) else EXECUTION_STATUS_OPEN
                self._persist_execution(retried_request, response, status=retried_status)
                self._log_order(retried_request, response, "submitted_after_quantity_retry")
                self._send_alert("trade_closed" if self._is_sell_request(retried_request) else "trade_opened", retried_request, response)
                self._sync_after_order(request.symbol, source=f"after_retry_{request.side.lower()}")
                return response
            self._handle_order_error(request, exc)
            self._sync_after_error(request.symbol, exc)
            raise
        except OrderBlockedError as exc:
            if self._is_sell_request(request):
                return self._build_blocked_response(request, status=exc.reason, reason=str(exc.details.get("validation_reason", exc.reason)), validation=exc.details)
            self._handle_blocked_order(request, exc)
            raise
        except Exception as exc:
            if self._is_sell_request(request):
                blocked_response = self._build_blocked_response(
                    request,
                    status=EXECUTION_STATUS_BLOCKED_INVALID_QUANTITY,
                    reason=str(exc),
                    validation={"validation_status": EXECUTION_STATUS_BLOCKED_INVALID_QUANTITY, "validation_reason": str(exc)},
                )
                self._sync_after_error(request.symbol, exc)
                return blocked_response
            self._handle_generic_error(request, exc)
            self._sync_after_error(request.symbol, exc)
            raise
        finally:
            self._pending_orders.discard(order_key)

    def _validate_response(self, response: dict[str, Any]) -> None:
        if not response.get("symbol") or not response.get("orderId"):
            raise RuntimeError("Invalid Binance response: missing symbol or orderId")

    def _persist_execution(self, request: OrderRequest, response: dict[str, Any], *, status: str) -> None:
        execution = self._extract_execution_details(request, response)
        payload = {
            "timestamp": datetime.now(UTC),
            "symbol": request.symbol,
            "side": request.side,
            "quantity": execution["executed_qty"],
            "entry_price": execution["executed_price"],
            "exit_price": None,
            "stop_loss_price": 0.0,
            "take_profit_price": 0.0,
            "pnl": 0.0,
            "pnl_pct": 0.0,
            "status": status,
            "order_id": str(response["orderId"]),
            "source": request.source,
            "mode": settings.live_trading_mode,
            "confidence_score": float(request.score or 0.0),
            "notes": response.get("status", ""),
            "created_at": datetime.now(UTC),
        }
        self.logger.info("order_response={}", response)
        self.logger.info(
            "executed_price={} executed_qty={} executed_value={}",
            execution["executed_price"],
            execution["executed_qty"],
            execution["executed_value"],
        )
        self.repository.save_trade_execution(payload)

    def _send_alert(self, event_type: str, request: OrderRequest, response: dict[str, Any]) -> None:
        execution = self._extract_execution_details(request, response)
        payload = {
            "symbol": request.symbol,
            "side": request.side,
            "quantity": execution["executed_qty"],
            "price": execution["executed_price"],
            "score": request.score,
            "mode": settings.live_trading_mode,
            "order_id": response.get("orderId"),
        }
        if event_type == "trade_opened":
            self.alert_dispatcher.trade_opened(payload)
        else:
            self.alert_dispatcher.trade_closed(payload)

    def _handle_binance_error(self, request: OrderRequest, exc: BinanceAPIException) -> None:
        reason = "binance_unavailable"
        if is_binance_timestamp_error(exc):
            reason = "timestamp_out_of_sync"
            self.logger.warning("Timestamp error detected. Resyncing Binance clock...")
            try:
                sync_binance_time(self.client, logger=self.logger)
            except Exception as sync_exc:
                self.logger.error("binance_clock_resync_failed error={}", str(sync_exc))
        if getattr(exc, "code", None) == -2010:
            reason = "insufficient_balance"
        elif getattr(exc, "code", None) == -1121:
            reason = "invalid_symbol"
        elif self._should_retry_with_normalized_quantity(exc):
            reason = "quantity_precision_error"
        self.logger.error(
            "symbol={} score={} saldo={} quantidade={} preco={} pnl=- risco=- motivo={}",
            request.symbol,
            request.score,
            self.account_manager.get_free_balance("USDT"),
            request.quantity,
            request.price,
            reason,
        )
        self.alert_dispatcher.critical_error(component="order_manager", error=reason, context={"symbol": request.symbol, "mode": settings.live_trading_mode})

    def _handle_order_error(self, request: OrderRequest, exc: BinanceOrderException) -> None:
        message = str(exc).lower()
        reason = "invalid_quantity" if "quantity" in message or is_quantity_precision_error_message(message) else "order_rejected"
        self.logger.error(
            "symbol={} score={} saldo={} quantidade={} preco={} pnl=- risco=- motivo={}",
            request.symbol,
            request.score,
            self.account_manager.get_free_balance("USDT"),
            request.quantity,
            request.price,
            reason,
        )
        self.alert_dispatcher.critical_error(component="order_manager", error=reason, context={"symbol": request.symbol})

    def _handle_blocked_order(self, request: OrderRequest, exc: OrderBlockedError) -> None:
        details = exc.details
        self.logger.warning(
            "symbol={} local_quantity={} real_balance={} requested_quantity={} safe_quantity={} normalized_quantity={} price={} notional={} min_notional={} final_status={} motivo={} source={} order_id=- pnl=- risco={} saldo={}",
            request.symbol,
            request.quantity,
            details.get("real_balance", 0.0),
            details.get("requested_quantity", request.quantity),
            details.get("safe_quantity", 0.0),
            details.get("normalized_quantity", 0.0),
            details.get("price", 0.0),
            details.get("notional", details.get("notional_value", 0.0)),
            details.get("min_notional", 0.0),
            exc.reason,
            details.get("validation_reason", exc.reason),
            request.source,
            settings.max_position_size_pct,
            self.account_manager.get_free_balance("USDT"),
        )

    def _handle_generic_error(self, request: OrderRequest, exc: Exception) -> None:
        self.logger.error(
            "symbol={} score={} saldo={} quantidade={} preco={} pnl=- risco=- motivo={}",
            request.symbol,
            request.score,
            self.account_manager.get_free_balance("USDT"),
            request.quantity,
            request.price,
            str(exc),
        )
        self.alert_dispatcher.critical_error(component="order_manager", error=str(exc), context={"symbol": request.symbol})

    def _log_order(self, request: OrderRequest, response: dict[str, Any], decision: str) -> None:
        execution = self._extract_execution_details(request, response)
        validation = response.get("_validation") or {}
        self.logger.info(
            "symbol={} local_quantity={} real_balance={} requested_quantity={} safe_quantity={} normalized_quantity={} price={} notional={} min_notional={} final_status={} motivo={} source={} order_id={} pnl=- risco={} saldo={}",
            request.symbol,
            request.quantity,
            validation.get("real_balance", 0.0),
            validation.get("requested_quantity", request.quantity),
            validation.get("safe_quantity", execution["executed_qty"]),
            execution["executed_qty"],
            execution["executed_price"],
            validation.get("notional", execution["executed_value"]),
            validation.get("min_notional", 0.0),
            response.get("status", EXECUTION_STATUS_OPEN),
            decision,
            request.source,
            response.get("orderId"),
            settings.max_position_size_pct,
            self.account_manager.get_free_balance("USDT"),
        )

    def _get_exchange_info(self) -> dict[str, Any]:
        if self._exchange_info_cache is None:
            self._exchange_info_cache = dict(self.client.get_exchange_info())
        return self._exchange_info_cache

    def get_exchange_info(self) -> dict[str, Any]:
        return self._get_exchange_info()

    def get_safe_quantity(self, symbol: str, requested_quantity: float | None = None) -> dict[str, Any]:
        return get_safe_quantity(
            self.client,
            symbol,
            requested_quantity,
            side="SELL",
            exchange_info=self._get_exchange_info(),
            account_info=self.account_manager.get_account_info(),
        )

    def get_safe_sell_quantity(self, symbol: str, requested_quantity: float | None = None, *, price: float | None = None) -> dict[str, Any]:
        return get_safe_sell_quantity(
            self.client,
            symbol,
            requested_quantity,
            exchange_info=self._get_exchange_info(),
            price=price,
            account_info=self.account_manager.get_account_info(),
        )

    def _get_reference_price(self, request: OrderRequest) -> float:
        if request.price is not None and request.price > 0:
            return float(request.price)
        ticker = self.client.get_symbol_ticker(symbol=request.symbol)
        return float(ticker["price"])

    def _prepare_request(self, request: OrderRequest) -> OrderRequest:
        validation = self._normalize_and_validate_order(request)
        return OrderRequest(**{**request.model_dump(), "quantity": float(validation["normalized_quantity"])})

    def _normalize_and_validate_order(self, request: OrderRequest) -> dict[str, Any]:
        if request.side.upper() == "BUY" and (request.quantity is None or float(request.quantity) <= 0):
            raise OrderBlockedError(
                EXECUTION_STATUS_BLOCKED_INVALID_QUANTITY,
                {"validation_status": EXECUTION_STATUS_BLOCKED_INVALID_QUANTITY, "validation_reason": "buy_quantity_required"},
            )
        if self._is_sell_request(request):
            current_price = self._get_reference_price(request)
            validation = get_safe_quantity(
                self.client,
                request.symbol,
                request.quantity,
                side="SELL",
                exchange_info=self._get_exchange_info(),
                price=current_price,
                account_info=self.account_manager.get_account_info(),
            )
            self.logger.info(
                "symbol={} local_quantity={} real_balance={} requested_quantity={} safe_quantity={} normalized_quantity={} price={} notional={} min_notional={} final_status={} motivo={} source={} order_id=- pnl=- risco={} saldo={}",
                request.symbol,
                request.quantity,
                validation["real_balance"],
                validation["requested_quantity"],
                validation["safe_quantity"],
                validation["normalized_quantity"],
                validation["price"],
                validation["notional"],
                validation["min_notional"],
                validation["validation_status"],
                validation["validation_reason"],
                request.source,
                settings.max_position_size_pct,
                self.account_manager.get_free_balance("USDT"),
            )
            if not validation["valid"]:
                raise OrderBlockedError(str(validation["validation_status"]), validation)
            validation["reference_price"] = current_price
            return validation

        exchange_info = self._get_exchange_info()
        current_price = self._get_reference_price(request)
        validation = get_safe_quantity(
            self.client,
            request.symbol,
            float(request.quantity or 0.0),
            side="BUY",
            exchange_info=exchange_info,
            price=current_price,
            account_info=self.account_manager.get_account_info(),
        )
        self.logger.info(
            "order_quantity_normalized symbol={} raw_quantity={} normalized_quantity={} step_size={} min_qty={} max_qty={} min_notional={} price={} notional_value={} real_balance={} safe_quantity={} final_status={} motivo={}",
            request.symbol,
            request.quantity,
            validation["normalized_quantity"],
            validation["step_size"],
            validation["min_qty"],
            validation["max_qty"],
            validation["min_notional"],
            current_price,
            validation["notional"],
            validation["real_balance"],
            validation["safe_quantity"],
            validation["validation_status"],
            validation["validation_reason"],
        )
        if not validation["valid"]:
            raise OrderBlockedError(str(validation["validation_status"]), validation)
        buy_valid, details = validate_order_quantity(
            symbol=request.symbol,
            quantity=float(validation["normalized_quantity"] or 0.0),
            price=current_price,
            exchange_info=exchange_info,
            side=request.side,
        )
        if not buy_valid:
            merged = {**validation, **details}
            raise OrderBlockedError(str(details["reason"]), merged)
        merged = {**details, **validation, "raw_quantity": float(request.quantity or 0.0)}
        merged["reference_price"] = current_price
        return merged

    def _request_with_filled_quantity(self, request: OrderRequest, response: dict[str, Any]) -> OrderRequest:
        validation = response.get("_validation") or {}
        quantity = float(validation.get("normalized_quantity", request.quantity))
        return OrderRequest(**{**request.model_dump(), "quantity": quantity})

    def _should_retry_with_normalized_quantity(self, exc: Exception) -> bool:
        if isinstance(exc, BinanceAPIException) and getattr(exc, "code", None) == -1111:
            return True
        return is_quantity_precision_error_message(str(exc))

    def _retry_with_normalized_quantity(self, request: OrderRequest, exc: Exception) -> tuple[OrderRequest, dict[str, Any]]:
        self.logger.warning(
            "order_retry_after_quantity_error symbol={} quantity={} price={} error={}",
            request.symbol,
            request.quantity,
            request.price,
            str(exc),
        )
        retried_request = self._prepare_request(request)
        response = self._submit_to_binance(retried_request)
        return self._request_with_filled_quantity(retried_request, response), response

    def _extract_execution_details(self, request: OrderRequest, response: dict[str, Any]) -> dict[str, float]:
        current_price = float(response.get("_reference_price") or request.price or 0.0)
        latest_price = current_price
        executed_price = self._first_positive_number(
            self._extract_fill_price(response),
            response.get("price"),
            current_price,
            latest_price,
            0,
        )
        executed_qty = self._first_positive_number(
            response.get("executedQty"),
            response.get("origQty"),
            response.get("_normalized_quantity"),
            request.quantity,
            0,
        )
        executed_value = executed_price * executed_qty
        response["executed_price"] = executed_price
        response["executed_qty"] = executed_qty
        response["executed_value"] = executed_value
        return {
            "executed_price": executed_price,
            "executed_qty": executed_qty,
            "executed_value": executed_value,
        }

    @staticmethod
    def _is_sell_request(request: OrderRequest) -> bool:
        return request.side.upper() == "SELL"

    def _is_controlled_sell_error(self, request: OrderRequest, exc: BinanceAPIException) -> bool:
        return self._is_sell_request(request) and getattr(exc, "code", None) == -2010

    def _handle_controlled_sell_error(self, request: OrderRequest, exc: BinanceAPIException) -> dict[str, Any]:
        validation = self._safe_sell_validation_from_request(request)
        return self._build_blocked_response(
            request,
            status=EXECUTION_STATUS_BLOCKED_INSUFFICIENT_BALANCE,
            reason=str(exc),
            validation=validation,
            error_code=getattr(exc, "code", None),
        )

    def _safe_sell_validation_from_request(self, request: OrderRequest) -> dict[str, Any]:
        try:
            return get_safe_sell_quantity(
                self.client,
                request.symbol,
                request.quantity,
                exchange_info=self._get_exchange_info(),
                price=self._get_reference_price(request),
                account_info=self.account_manager.get_account_info(),
            )
        except Exception:
            return {
                "symbol": request.symbol,
                "real_balance": 0.0,
                "requested_quantity": request.quantity,
                "safe_quantity": 0.0,
                "normalized_quantity": 0.0,
                "price": float(request.price or 0.0),
                "notional": 0.0,
                "min_notional": 0.0,
                "validation_status": EXECUTION_STATUS_BLOCKED_INVALID_QUANTITY,
                "validation_reason": "safe_sell_validation_failed",
            }

    def _sync_before_order(self, symbol: str, *, source: str) -> None:
        self.account_manager.sync_positions_with_binance()
        self.logger.info("symbol={} source={} motivo=pre_order_sync", symbol.upper(), source)

    def _sync_after_order(self, symbol: str, *, source: str) -> None:
        self.account_manager.sync_positions_with_binance()
        self.account_manager.generate_snapshot()
        self.alert_dispatcher.dispatch_raw(
            "sync_completed",
            "Order sync completed",
            "\n".join([f"symbol: {symbol.upper()}", f"source: {source}"]),
            {"symbol": symbol.upper(), "source": source},
        )

    def _sync_after_error(self, symbol: str, exc: Exception) -> None:
        try:
            self.account_manager.sync_positions_with_binance()
            self.account_manager.generate_snapshot()
        except Exception as sync_exc:
            self.logger.error("symbol={} motivo=post_error_sync_failed error={}", symbol.upper(), str(sync_exc))
        self.alert_dispatcher.dispatch_raw(
            "run_loop_continue",
            "Run loop continuing after error",
            "\n".join([f"symbol: {symbol.upper()}", f"error: {str(exc)}", "run_loop: continuing"]),
            {"symbol": symbol.upper(), "error": str(exc)},
        )

    def _build_blocked_response(
        self,
        request: OrderRequest,
        *,
        status: str,
        reason: str,
        validation: dict[str, Any],
        error_code: int | None = None,
    ) -> dict[str, Any]:
        response = {
            "symbol": request.symbol,
            "side": request.side,
            "status": status,
            "blocked": True,
            "reason": reason,
            "orderId": None,
            "executedQty": "0",
            "origQty": str(validation.get("normalized_quantity", 0.0)),
            "_validation": validation,
            "_reference_price": validation.get("price", request.price),
            "error_code": error_code,
        }
        self.logger.warning(
            "symbol={} local_quantity={} real_balance={} requested_quantity={} safe_quantity={} normalized_quantity={} price={} notional={} min_notional={} final_status={} motivo={} source={} order_id=- pnl=- risco={} saldo={}",
            request.symbol,
            request.quantity,
            validation.get("real_balance", 0.0),
            validation.get("requested_quantity", request.quantity),
            validation.get("safe_quantity", 0.0),
            validation.get("normalized_quantity", 0.0),
            validation.get("price", request.price or 0.0),
            validation.get("notional", 0.0),
            validation.get("min_notional", 0.0),
            status,
            reason,
            request.source,
            settings.max_position_size_pct,
            self.account_manager.get_free_balance("USDT"),
        )
        self.alert_dispatcher.dispatch_raw(
            "execution_blocked",
            f"Execution blocked [{status}]",
            "\n".join(
                [
                    f"symbol: {request.symbol}",
                    f"status: {status}",
                    f"reason: {reason}",
                    f"real_balance: {float(validation.get('real_balance', 0.0)):.8f}",
                    f"requested_quantity: {float(validation.get('requested_quantity') or 0.0):.8f}",
                    f"normalized_quantity: {float(validation.get('normalized_quantity', 0.0)):.8f}",
                    f"price: {float(validation.get('price', 0.0)):.8f}",
                    f"notional: {float(validation.get('notional', 0.0)):.8f}",
                    f"min_notional: {float(validation.get('min_notional', 0.0)):.8f}",
                    "run_loop: continuing",
                ]
            ),
            {
                "symbol": request.symbol,
                "status": status,
                "reason": reason,
                "source": request.source,
                **validation,
            },
        )
        return response

    @staticmethod
    def _extract_fill_price(response: dict[str, Any]) -> str | float | None:
        fills = response.get("fills", [{}]) or [{}]
        return fills[0].get("price")

    @staticmethod
    def _first_positive_number(*values: object) -> float:
        for value in values:
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            if number > 0:
                return number
        return 0.0
