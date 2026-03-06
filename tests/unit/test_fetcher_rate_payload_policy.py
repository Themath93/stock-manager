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
