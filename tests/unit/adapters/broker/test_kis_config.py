"""Unit tests for KISConfig"""

import pytest
from pydantic import ValidationError

from src.stock_manager.adapters.broker.kis import KISConfig, Mode


class TestKISConfig:
    """KISConfig 설정 테스트"""

    def test_default_mode_is_paper(self):
        """기본 모드가 PAPER인지 확인"""
        config = KISConfig(
            kis_app_key="test_key",
            kis_app_secret="test_secret",
        )
        assert config.mode == Mode.PAPER

    def test_live_mode_urls(self):
        """LIVE 모드 URL 확인"""
        config = KISConfig(
            mode=Mode.LIVE,
            kis_app_key="test_key",
            kis_app_secret="test_secret",
        )

        assert "openapi.koreainvestment.com:9443" in config.get_rest_base_url()
        assert "openapi.koreainvestment.com:9443" in config.get_token_url()
        assert "openapi.koreainvestment.com:9443" in config.get_hashkey_url()
        assert "ws://ops.koreainvestment.com:21000" == config.get_ws_url()

    def test_paper_mode_urls(self):
        """PAPER 모드 URL 확인"""
        config = KISConfig(
            mode=Mode.PAPER,
            kis_app_key="test_key",
            kis_app_secret="test_secret",
        )

        assert "openapivts.koreainvestment.com:29443" in config.get_rest_base_url()
        assert "openapivts.koreainvestment.com:29443" in config.get_token_url()
        assert "openapivts.koreainvestment.com:29443" in config.get_hashkey_url()
        assert "ws://ops.koreainvestment.com:31000" == config.get_ws_url()

    def test_custom_urls_override(self):
        """커스텀 URL 오버라이드 확인"""
        config = KISConfig(
            kis_rest_base_url="https://custom.rest.com",
            kis_ws_url="ws://custom.ws.com",
            kis_app_key="test_key",
            kis_app_secret="test_secret",
        )

        assert "custom.rest.com" in config.get_rest_base_url()
        assert "custom.ws.com" == config.get_ws_url()

    def test_missing_app_key_raises_error(self):
        """app_key 누락 시 ValidationError"""
        with pytest.raises(ValidationError):
            KISConfig(
                kis_app_secret="test_secret",
            )

    def test_missing_app_secret_raises_error(self):
        """app_secret 누락 시 ValidationError"""
        with pytest.raises(ValidationError):
            KISConfig(
                kis_app_key="test_key",
            )

    def test_request_timeout_default(self):
        """요청 타임아웃 기본값 확인"""
        config = KISConfig(
            kis_app_key="test_key",
            kis_app_secret="test_secret",
        )
        assert config.request_timeout == 30

    def test_max_retries_default(self):
        """최대 재시도 횟수 기본값 확인"""
        config = KISConfig(
            kis_app_key="test_key",
            kis_app_secret="test_secret",
        )
        assert config.max_retries == 3
