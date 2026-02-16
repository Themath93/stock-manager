from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import json
import logging
import threading
import time
from typing import Any, Callable, Literal, Protocol

import websocket

from stock_manager.adapters.broker.kis.exceptions import KISAPIError

logger = logging.getLogger(__name__)

KIS_WS_URL_MOCK = "ws://ops.koreainvestment.com:31000"
KIS_WS_URL_REAL = "ws://ops.koreainvestment.com:21000"

DEFAULT_QUOTE_TR_ID = "H0STASP0"
DEFAULT_EXECUTION_TR_ID = "H0STCNT0"

_QUOTE_TR_IDS = {
    "H0STASP0",
    "H0NXASP0",
    "H0UNASP0",
    "H0EWASP0",
    "H0STOAA0",
}

_EXECUTION_TR_IDS = {
    "H0STCNT0",
    "H0NXCNT0",
    "H0UNCNT0",
    "H0EWCNT0",
    "H0STOUP0",
    "H0STCNI0",
    "H0STCNI9",
}


def get_kis_websocket_url(*, is_paper_trading: bool) -> str:
    return KIS_WS_URL_MOCK if is_paper_trading else KIS_WS_URL_REAL


@dataclass(frozen=True)
class KISQuoteEvent:
    symbol: str
    bid_price: Decimal | None
    ask_price: Decimal | None
    bid_quantity: Decimal | None
    ask_quantity: Decimal | None
    timestamp: datetime
    tr_id: str
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class KISExecutionEvent:
    symbol: str
    order_id: str | None
    side: Literal["buy", "sell"] | None
    price: Decimal | None
    quantity: Decimal | None
    timestamp: datetime
    tr_id: str
    raw_payload: dict[str, Any]


QuoteCallback = Callable[[KISQuoteEvent], None]
ExecutionCallback = Callable[[KISExecutionEvent], None]


class _WebSocketAppLike(Protocol):
    sock: Any

    def send(self, payload: str) -> Any: ...

    def close(self) -> Any: ...

    def run_forever(self) -> Any: ...


class _WebSocketAppFactory(Protocol):
    def __call__(
        self,
        url: str,
        *,
        on_open: Callable[[Any], None],
        on_message: Callable[[Any, str], None],
        on_error: Callable[[Any, Any], None],
        on_close: Callable[[Any, Any, Any], None],
        header: list[str],
    ) -> _WebSocketAppLike: ...


class KISWebSocketClient:
    def __init__(
        self,
        *,
        websocket_url: str,
        websocket_app_factory: _WebSocketAppFactory | None = None,
        reconnect_max_attempts: int = 5,
        reconnect_base_delay_sec: float = 1.0,
    ) -> None:
        self._websocket_url = websocket_url
        self._websocket_app_factory = websocket_app_factory or websocket.WebSocketApp
        self._reconnect_max_attempts = max(1, reconnect_max_attempts)
        self._reconnect_base_delay_sec = max(0.1, reconnect_base_delay_sec)

        self._ws: _WebSocketAppLike | None = None
        self._thread: threading.Thread | None = None
        self._connected = False
        self._connected_event = threading.Event()
        self._lock = threading.Lock()

        self._approval_key: str = ""
        self._custtype: Literal["P", "B"] = "P"
        self._closing = False
        self._reconnect_in_progress = False

        self._quote_callbacks: list[QuoteCallback] = []
        self._execution_callbacks: list[ExecutionCallback] = []
        self._quote_subscriptions: dict[str, str] = {}
        self._execution_subscription: tuple[str, str] | None = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(
        self,
        *,
        approval_key: str,
        custtype: Literal["P", "B"] = "P",
        timeout_sec: float = 5.0,
    ) -> None:
        with self._lock:
            if self._connected:
                return

            self._approval_key = approval_key.strip()
            if not self._approval_key:
                raise KISAPIError("approval_key is required for WebSocket connection")

            self._custtype = custtype
            self._closing = False
            self._connected_event.clear()
            self._start_socket_thread()

        if not self._connected_event.wait(timeout=max(0.1, timeout_sec)):
            self.disconnect(join_timeout=0.5)
            raise KISAPIError("WebSocket connection timed out")

    def disconnect(self, *, join_timeout: float = 2.0) -> None:
        with self._lock:
            self._closing = True
            self._connected = False
            self._connected_event.clear()
            ws = self._ws
            self._ws = None
            thread = self._thread
            self._thread = None

        if ws is not None:
            try:
                ws.close()
            except Exception:
                logger.debug("Failed to close websocket cleanly", exc_info=True)

        if thread is not None and thread.is_alive():
            thread.join(timeout=max(0.1, join_timeout))

    def register_quote_callback(self, callback: QuoteCallback) -> None:
        self._quote_callbacks.append(callback)

    def register_execution_callback(self, callback: ExecutionCallback) -> None:
        self._execution_callbacks.append(callback)

    def subscribe_quotes(
        self,
        symbols: list[str],
        *,
        callback: QuoteCallback | None = None,
        tr_id: str = DEFAULT_QUOTE_TR_ID,
    ) -> None:
        if callback is not None:
            self.register_quote_callback(callback)

        for symbol in symbols:
            normalized = symbol.strip().upper()
            if not normalized:
                continue
            self._quote_subscriptions[normalized] = tr_id

        if self._connected:
            for symbol, symbol_tr_id in self._quote_subscriptions.items():
                self._send_subscription(tr_id=symbol_tr_id, tr_key=symbol)

    def subscribe_executions(
        self,
        *,
        callback: ExecutionCallback | None = None,
        tr_id: str = DEFAULT_EXECUTION_TR_ID,
        tr_key: str = "ALL",
    ) -> None:
        if callback is not None:
            self.register_execution_callback(callback)

        self._execution_subscription = (tr_id, tr_key)
        if self._connected:
            self._send_subscription(tr_id=tr_id, tr_key=tr_key)

    def _start_socket_thread(self) -> None:
        headers = [
            f"approval_key: {self._approval_key}",
            f"custtype: {self._custtype}",
            "content-type: utf-8",
        ]
        ws = self._websocket_app_factory(
            self._websocket_url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            header=headers,
        )
        self._ws = ws
        self._thread = threading.Thread(target=ws.run_forever, daemon=True, name="KISWebSocket")
        self._thread.start()

    def _on_open(self, _ws: Any) -> None:
        self._connected = True
        self._connected_event.set()
        self._reconnect_in_progress = False
        self._replay_subscriptions()

    def _on_close(self, _ws: Any, _close_code: Any, _close_msg: Any) -> None:
        self._connected = False
        self._connected_event.clear()
        if self._closing:
            return
        self._schedule_reconnect()

    def _on_error(self, _ws: Any, error: Any) -> None:
        logger.warning("KIS WebSocket error: %s", error)

    def _on_message(self, _ws: Any, message: str) -> None:
        payload = self._decode_message(message)
        if payload is None:
            return

        tr_id = self._extract_tr_id(payload)
        if not tr_id:
            return

        if tr_id in _QUOTE_TR_IDS:
            self._dispatch_quote(payload=payload, tr_id=tr_id)
            return

        if tr_id in _EXECUTION_TR_IDS:
            self._dispatch_execution(payload=payload, tr_id=tr_id)

    def _schedule_reconnect(self) -> None:
        with self._lock:
            if self._reconnect_in_progress or self._closing:
                return
            self._reconnect_in_progress = True

        threading.Thread(
            target=self._reconnect_loop, daemon=True, name="KISWebSocketReconnect"
        ).start()

    def _reconnect_loop(self) -> None:
        for attempt in range(1, self._reconnect_max_attempts + 1):
            if self._closing:
                self._reconnect_in_progress = False
                return

            delay = self._reconnect_base_delay_sec * (2 ** (attempt - 1))
            time.sleep(delay)

            try:
                with self._lock:
                    self._connected_event.clear()
                    self._start_socket_thread()

                if self._connected_event.wait(timeout=5.0):
                    self._reconnect_in_progress = False
                    return
            except Exception:
                logger.debug("Reconnect attempt %s failed", attempt, exc_info=True)

        self._reconnect_in_progress = False
        logger.warning(
            "KIS WebSocket reconnect exhausted after %s attempts", self._reconnect_max_attempts
        )

    def _replay_subscriptions(self) -> None:
        for symbol, tr_id in self._quote_subscriptions.items():
            self._send_subscription(tr_id=tr_id, tr_key=symbol)

        if self._execution_subscription is not None:
            tr_id, tr_key = self._execution_subscription
            self._send_subscription(tr_id=tr_id, tr_key=tr_key)

    def _send_subscription(self, *, tr_id: str, tr_key: str) -> None:
        ws = self._ws
        if ws is None or not self._connected:
            return

        message = {
            "header": {
                "approval_key": self._approval_key,
                "custtype": self._custtype,
                "tr_type": "1",
                "content-type": "utf-8",
            },
            "body": {
                "tr_id": tr_id,
                "tr_key": tr_key,
            },
        }

        ws.send(json.dumps(message))

    @staticmethod
    def _decode_message(message: str) -> dict[str, Any] | None:
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            logger.debug("Ignoring non-JSON websocket payload")
            return None
        if isinstance(data, dict):
            return data
        return None

    @staticmethod
    def _extract_tr_id(payload: dict[str, Any]) -> str:
        direct = payload.get("tr_id")
        if isinstance(direct, str):
            return direct

        header = payload.get("header")
        if isinstance(header, dict):
            tr_id = header.get("tr_id")
            if isinstance(tr_id, str):
                return tr_id

        body = payload.get("body")
        if isinstance(body, dict):
            tr_id = body.get("tr_id")
            if isinstance(tr_id, str):
                return tr_id

        return ""

    @staticmethod
    def _extract_primary_record(payload: dict[str, Any]) -> dict[str, Any]:
        output = payload.get("output")
        if isinstance(output, dict):
            return output
        if isinstance(output, list):
            for item in output:
                if isinstance(item, dict):
                    return item

        body = payload.get("body")
        if isinstance(body, dict):
            body_output = body.get("output")
            if isinstance(body_output, dict):
                return body_output
            if isinstance(body_output, list):
                for item in body_output:
                    if isinstance(item, dict):
                        return item
            return body

        return payload

    @staticmethod
    def _to_decimal(value: Any) -> Decimal | None:
        if value in (None, ""):
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None

    @staticmethod
    def _normalize_side(value: Any) -> Literal["buy", "sell"] | None:
        if value is None:
            return None

        normalized = str(value).strip().lower()
        if normalized in {"buy", "b", "2"}:
            return "buy"
        if normalized in {"sell", "s", "1"}:
            return "sell"
        return None

    def _dispatch_quote(self, *, payload: dict[str, Any], tr_id: str) -> None:
        record = self._extract_primary_record(payload)
        symbol = str(
            record.get("mksc_shrn_iscd")
            or record.get("pdno")
            or record.get("symbol")
            or record.get("tr_key")
            or ""
        )

        event = KISQuoteEvent(
            symbol=symbol,
            bid_price=self._to_decimal(record.get("bidp1") or record.get("bid_price")),
            ask_price=self._to_decimal(record.get("askp1") or record.get("ask_price")),
            bid_quantity=self._to_decimal(record.get("bidq1") or record.get("bid_qty")),
            ask_quantity=self._to_decimal(record.get("askq1") or record.get("ask_qty")),
            timestamp=datetime.now(timezone.utc),
            tr_id=tr_id,
            raw_payload=payload,
        )

        for callback in self._quote_callbacks:
            try:
                callback(event)
            except Exception:
                logger.debug("Quote callback error", exc_info=True)

    def _dispatch_execution(self, *, payload: dict[str, Any], tr_id: str) -> None:
        record = self._extract_primary_record(payload)
        symbol = str(
            record.get("mksc_shrn_iscd") or record.get("pdno") or record.get("symbol") or ""
        )

        event = KISExecutionEvent(
            symbol=symbol,
            order_id=(
                str(record.get("odno"))
                if record.get("odno") not in (None, "")
                else (
                    str(record.get("order_id"))
                    if record.get("order_id") not in (None, "")
                    else None
                )
            ),
            side=self._normalize_side(record.get("sll_bk_dvsn") or record.get("side")),
            price=self._to_decimal(record.get("cntg_pr") or record.get("price")),
            quantity=self._to_decimal(record.get("cntg_qty") or record.get("qty")),
            timestamp=datetime.now(timezone.utc),
            tr_id=tr_id,
            raw_payload=payload,
        )

        for callback in self._execution_callbacks:
            try:
                callback(event)
            except Exception:
                logger.debug("Execution callback error", exc_info=True)
