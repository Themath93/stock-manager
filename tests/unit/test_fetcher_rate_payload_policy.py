"""Tests for TechnicalDataFetcher payload/rate-limit guardrails."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from stock_manager.adapters.broker.kis.exceptions import KISAPIError
from stock_manager.trading.indicators.fetcher import TechnicalDataFetcher


def _build_client(*, use_mock: bool) -> MagicMock:
    client = MagicMock()
    client.config = SimpleNamespace(use_mock=use_mock)
    return client


class TestTechnicalDataFetcherGuardrails:
    def test_default_fetcher_rate_limit_is_8_per_second(self) -> None:
        fetcher = TechnicalDataFetcher(client=_build_client(use_mock=False))
        assert fetcher._rate_limiter.max_requests == 8

    def test_mock_mode_skips_real_only_growth_api(self) -> None:
        fetcher = TechnicalDataFetcher(client=_build_client(use_mock=True))

        with patch("stock_manager.trading.indicators.fetcher.get_growth_ratio") as mock_growth:
            result = fetcher._fetch_growth_ratio("000660")

        assert result == {}
        mock_growth.assert_not_called()

    def test_growth_ratio_call_includes_market_division_code(self) -> None:
        fetcher = TechnicalDataFetcher(client=_build_client(use_mock=False))

        with patch("stock_manager.trading.indicators.fetcher.get_growth_ratio") as mock_growth:
            mock_growth.return_value = {"rt_cd": "0", "output": {"sale_gror": "10", "thtr_ntin_gror": "9"}}
            fetcher._fetch_growth_ratio("000660")

        _, kwargs = mock_growth.call_args
        assert kwargs["fid_input_iscd"] == "000660"
        assert kwargs["fid_cond_mrkt_div_code"] == "J"

    def test_technicals_call_includes_market_division_code(self) -> None:
        fetcher = TechnicalDataFetcher(client=_build_client(use_mock=False))

        with patch.object(fetcher, "_call_kis_api", return_value={}) as mock_call:
            fetcher._fetch_technicals("000660")

        _, kwargs = mock_call.call_args
        assert kwargs["fid_cond_mrkt_div_code"] == "J"

    def test_fetcher_uses_rate_limiter_before_api_call(self) -> None:
        rate_limiter = MagicMock()
        rate_limiter.acquire.return_value = True
        fetcher = TechnicalDataFetcher(
            client=_build_client(use_mock=False),
            rate_limiter=rate_limiter,
        )

        with patch("stock_manager.trading.indicators.fetcher.inquire_current_price") as mock_price:
            mock_price.return_value = {"rt_cd": "0", "output": {"stck_prpr": "1000"}}
            fetcher._fetch_current_price("005930")

        rate_limiter.acquire.assert_called_once()

    def test_rate_limit_error_is_logged_as_warning_and_degraded(self, caplog: pytest.LogCaptureFixture) -> None:
        fetcher = TechnicalDataFetcher(client=_build_client(use_mock=False))
        caplog.set_level("WARNING")
        error = KISAPIError(
            "API request failed: 500 Internal Server Error",
            status_code=500,
            response_data={"msg_cd": "EGW00201", "msg1": "초당 거래건수를 초과하였습니다."},
        )

        with patch("stock_manager.trading.indicators.fetcher.get_stability_ratio") as mock_stability:
            mock_stability.side_effect = error
            result = fetcher._fetch_stability_ratio("000660")

        assert result == {}
        assert "Rate limit exceeded while calling get_stability_ratio" in caplog.text


class TestMockModeRealClientFallback:
    def test_mock_with_real_client_uses_real_client(self) -> None:
        """mock 모드 + real_client → real_client로 API 함수 호출."""
        mock_client = _build_client(use_mock=True)
        real_client = MagicMock()
        fetcher = TechnicalDataFetcher(client=mock_client, real_client=real_client)

        with patch("stock_manager.trading.indicators.fetcher.get_growth_ratio") as mock_fn:
            mock_fn.return_value = {"rt_cd": "0", "output": {}}
            fetcher._fetch_growth_ratio("000660")

        assert mock_fn.call_args[0][0] is real_client

    def test_mock_without_real_client_returns_empty(self) -> None:
        """mock 모드 + real_client 없음 → {} (기존 동작)."""
        fetcher = TechnicalDataFetcher(client=_build_client(use_mock=True))

        with patch("stock_manager.trading.indicators.fetcher.get_growth_ratio") as mock_fn:
            result = fetcher._fetch_growth_ratio("000660")

        assert result == {}
        mock_fn.assert_not_called()

    def test_mock_real_client_exception_returns_empty(self) -> None:
        """real_client 예외 → {} 반환."""
        real_client = MagicMock()
        fetcher = TechnicalDataFetcher(client=_build_client(use_mock=True), real_client=real_client)

        with patch("stock_manager.trading.indicators.fetcher.get_growth_ratio") as mock_fn:
            mock_fn.side_effect = Exception("connection error")
            result = fetcher._fetch_growth_ratio("000660")

        assert result == {}

    def test_real_mode_ignores_real_client(self) -> None:
        """실서버 모드에서는 real_client 무시, 기본 client 사용."""
        main_client = _build_client(use_mock=False)
        real_client = MagicMock()
        fetcher = TechnicalDataFetcher(client=main_client, real_client=real_client)

        with patch("stock_manager.trading.indicators.fetcher.get_growth_ratio") as mock_fn:
            mock_fn.return_value = {"rt_cd": "0", "output": {}}
            fetcher._fetch_growth_ratio("000660")

        assert mock_fn.call_args[0][0] is main_client
