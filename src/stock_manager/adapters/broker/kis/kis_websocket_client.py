"""KIS OpenAPI WebSocket Client"""

import json
import logging
import threading
import time
from datetime import datetime
from decimal import Decimal
from typing import Callable, Optional

import websocket

from ..port.broker_port import ConnectionError, FillEvent, OrderSide, QuoteEvent
from .kis_config import KISConfig

logger = logging.getLogger(__name__)


class KISWebSocketClient:
    """한국투자증권 OpenAPI WebSocket 클라이언트"""

    def __init__(self, config: KISConfig, approval_key: str):
        self.config = config
        self.approval_key = approval_key
        self.ws: Optional[websocket.WebSocketApp] = None
        self._quote_callbacks: list[Callable[[QuoteEvent], None]] = []
        self._execution_callbacks: list[Callable[[FillEvent], None]] = []
        self._connected = False
        self._subscribed_symbols: set[str] = set()
        self._subscriptions_executions = False
        self._reconnect_attempts = 0
        self._max_retries = 5
        self._base_delay = 1
        self._ping_thread: Optional[threading.Thread] = None
        self._stop_ping = False

    def _get_approval_key(self) -> str:
        """WebSocket 인증 키 발급"""
        # TODO: REST API를 통해 approval_key 발급 필요
        # 현재는 초기화 시 받은 키 사용
        return self.approval_key

    def _on_open(self, ws):
        """WebSocket 연결 열림"""
        logger.info("WebSocket connected")
        self._connected = True
        self._reconnect_attempts = 0

        # 핑 스레드 시작 (연결 유지)
        self._stop_ping = False
        self._ping_thread = threading.Thread(target=self._ping_loop, daemon=True)
        self._ping_thread.start()

    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket 연결 닫힘"""
        logger.warning(f"WebSocket closed: {close_status_code} - {close_msg}")
        self._connected = False
        self._stop_ping = True

    def _on_error(self, ws, error):
        """WebSocket 에러"""
        logger.error(f"WebSocket error: {error}")

    def _on_message(self, ws, message):
        """WebSocket 메시지 수신"""
        try:
            data = json.loads(message)

            # 호가 데이터 처리 (H0STASP0)
            if data.get("tr_id") == "H0STASP0":
                self._handle_quote(data)
            # 체결 데이터 처리 (H0STCNT0)
            elif data.get("tr_id") == "H0STCNT0":
                self._handle_execution(data)

        except Exception as e:
            logger.error(f"Failed to parse message: {e}")

    def _handle_quote(self, data: dict):
        """호가 메시지 처리"""
        try:
            output = data.get("output", [])

            # 단일 종목 또는 다중 종목
            if isinstance(output, dict):
                output = [output]

            for item in output:
                quote = QuoteEvent(
                    symbol=item.get("mksc_shrn_iscd", ""),
                    bid_price=Decimal(item.get("bidp1", 0)),
                    ask_price=Decimal(item.get("askp1", 0)),
                    bid_qty=Decimal(item.get("bidq1", 0)),
                    ask_qty=Decimal(item.get("askq1", 0)),
                    timestamp=datetime.now(),
                )

                for callback in self._quote_callbacks:
                    try:
                        callback(quote)
                    except Exception as e:
                        logger.error(f"Quote callback error: {e}")

        except Exception as e:
            logger.error(f"Failed to handle quote: {e}")

    def _handle_execution(self, data: dict):
        """체결 메시지 처리"""
        try:
            output = data.get("output", [])

            # 단일 종목 또는 다중 종목
            if isinstance(output, dict):
                output = [output]

            for item in output:
                fill = FillEvent(
                    broker_order_id=item.get("odno", ""),
                    symbol=item.get("mksc_shrn_iscd", ""),
                    side=OrderSide.BUY if item.get("sll_bk_dvsn") == "BUY" else OrderSide.SELL,
                    qty=Decimal(item.get("cntg_qty", 0)),
                    price=Decimal(item.get("cntg_pr", 0)),
                    filled_at=datetime.now(),
                )

                for callback in self._execution_callbacks:
                    try:
                        callback(fill)
                    except Exception as e:
                        logger.error(f"Execution callback error: {e}")

        except Exception as e:
            logger.error(f"Failed to handle execution: {e}")

    def _ping_loop(self):
        """핑 루프 (연결 유지)"""
        while not self._stop_ping and self._connected:
            try:
                if self.ws and self.ws.sock:
                    self.ws.sock.ping()
                time.sleep(30)  # 30초마다 핑
            except Exception as e:
                logger.error(f"Ping error: {e}")
                break

    def connect_websocket(self) -> None:
        """WebSocket 연결"""
        try:
            self.ws = websocket.WebSocketApp(
                self.config.get_ws_url(),
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                header={
                    "Content-Type": "application/json",
                    "authorization": self._get_approval_key(),
                },
            )

            # 별도 스레드에서 실행
            wst = threading.Thread(target=self.ws.run_forever, daemon=True)
            wst.start()

            # 연결 대기
            timeout = 10
            start_time = time.time()
            while not self._connected and time.time() - start_time < timeout:
                time.sleep(0.1)

            if not self._connected:
                raise ConnectionError("WebSocket connection timeout")

        except Exception as e:
            logger.error(f"Failed to connect WebSocket: {e}")
            self._reconnect_with_backoff()

    def _reconnect_with_backoff(self) -> None:
        """지수 백오프로 재연결"""
        if self._reconnect_attempts >= self._max_retries:
            logger.error(f"Max reconnection attempts ({self._max_retries}) reached")
            raise ConnectionError("Failed to reconnect after maximum attempts")

        delay = self._base_delay * (2**self._reconnect_attempts)
        self._reconnect_attempts += 1

        logger.info(
            f"Reconnecting in {delay}s (attempt {self._reconnect_attempts}/{self._max_retries})..."
        )
        time.sleep(delay)

        try:
            self.connect_websocket()

            # 재연결 성공 시 이전 구독 복구
            if self._subscribed_symbols:
                self._subscribe_quotes(list(self._subscribed_symbols))
            if self._subscriptions_executions:
                self._subscribe_executions()

        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            self._reconnect_with_backoff()

    def disconnect_websocket(self) -> None:
        """WebSocket 연결 종료"""
        self._stop_ping = True
        self._connected = False

        if self.ws:
            self.ws.close()

        if self._ping_thread:
            self._ping_thread.join(timeout=5)

        logger.info("WebSocket disconnected")

    def subscribe_quotes(self, symbols: list[str], callback: Callable[[QuoteEvent], None]) -> None:
        """호가 구독

        Args:
            symbols: 구독할 종목 코드 목록
            callback: 호가 이벤트 수신 콜백
        """
        self._quote_callbacks.append(callback)
        self._subscribe_quotes(symbols)

    def _subscribe_quotes(self, symbols: list[str]) -> None:
        """호가 구독 전송"""
        if not self._connected:
            logger.warning("WebSocket not connected, deferring quote subscription")
            self._subscribed_symbols.update(symbols)
            return

        for symbol in symbols:
            self._subscribed_symbols.add(symbol)

            # 호가 구독 메시지
            message = {
                "header": {
                    "approval_key": self._get_approval_key(),
                    "custtype": "P",
                    "tr_type": "1",
                    "content-type": "utf-8",
                },
                "body": {
                    "tr_id": "H0STASP0",
                    "tr_key": symbol,
                },
            }

            try:
                self.ws.send(json.dumps(message))
                logger.info(f"Subscribed to quotes: {symbol}")
            except Exception as e:
                logger.error(f"Failed to subscribe to quotes: {e}")

    def subscribe_executions(self, callback: Callable[[FillEvent], None]) -> None:
        """체결 구독

        Args:
            callback: 체결 이벤트 수신 콜백
        """
        self._execution_callbacks.append(callback)
        self._subscribe_executions()

    def _subscribe_executions(self) -> None:
        """체결 구독 전송"""
        if not self._connected:
            logger.warning("WebSocket not connected, deferring execution subscription")
            self._subscriptions_executions = True
            return

        self._subscriptions_executions = True

        # 체결 구독 메시지 (전체 체결)
        message = {
            "header": {
                "approval_key": self._get_approval_key(),
                "custtype": "P",
                "tr_type": "1",
                "content-type": "utf-8",
            },
            "body": {
                "tr_id": "H0STCNT0",
                "tr_key": "ALL",
            },
        }

        try:
            self.ws.send(json.dumps(message))
            logger.info("Subscribed to executions")
        except Exception as e:
            logger.error(f"Failed to subscribe to executions: {e}")
