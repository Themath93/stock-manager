"""Unit tests for KISConfig"""

import os
import pytest
from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class TestKISConfig:
    """KISConfig 설정 테스트"""

    def test_default_mode_is_paper(self, monkeypatch, tmp_path):
        """기본 모드가 PAPER인지 확인"""
        # .env 파일이 없는 임시 디렉토리에서 실행
        monkeypatch.chdir(tmp_path)

        # 환경 변수 제거
        for key in ["KIS_MODE", "KIS_APP_KEY", "KIS_APP_SECRET", "SLACK_BOT_TOKEN", "SLACK_CHANNEL_ID"]:
            monkeypatch.delenv(key, raising=False)

        from stock_manager.adapters.broker.kis import KISConfig, Mode

        config = KISConfig(
            kis_app_key="test_key",
            kis_app_secret="test_secret",
            slack_bot_token="test_slack_token",
            slack_channel_id="test_channel_id",
        )
        assert config.mode == Mode.PAPER

    def test_live_mode_urls(self, monkeypatch, tmp_path):
        """LIVE 모드 URL 확인"""
        monkeypatch.chdir(tmp_path)

        for key in ["KIS_MODE", "KIS_APP_KEY", "KIS_APP_SECRET", "SLACK_BOT_TOKEN", "SLACK_CHANNEL_ID"]:
            monkeypatch.delenv(key, raising=False)

        from stock_manager.adapters.broker.kis import KISConfig, Mode

        config = KISConfig(
            kis_mode=Mode.LIVE,
            kis_app_key="test_key",
            kis_app_secret="test_secret",
            slack_bot_token="test_slack_token",
            slack_channel_id="test_channel_id",
        )

        assert "openapi.koreainvestment.com:9443" in config.get_rest_base_url()
        assert "openapi.koreainvestment.com:9443" in config.get_token_url()
        assert "openapi.koreainvestment.com:9443" in config.get_hashkey_url()
        assert "ws://ops.koreainvestment.com:21000" == config.get_ws_url()

    def test_paper_mode_urls(self, monkeypatch, tmp_path):
        """PAPER 모드 URL 확인"""
        monkeypatch.chdir(tmp_path)

        for key in ["KIS_MODE", "KIS_APP_KEY", "KIS_APP_SECRET", "SLACK_BOT_TOKEN", "SLACK_CHANNEL_ID"]:
            monkeypatch.delenv(key, raising=False)

        from stock_manager.adapters.broker.kis import KISConfig, Mode

        config = KISConfig(
            kis_mode=Mode.PAPER,
            kis_app_key="test_key",
            kis_app_secret="test_secret",
            slack_bot_token="test_slack_token",
            slack_channel_id="test_channel_id",
        )

        assert "openapivts.koreainvestment.com:29443" in config.get_rest_base_url()
        assert "openapivts.koreainvestment.com:29443" in config.get_token_url()
        assert "openapivts.koreainvestment.com:29443" in config.get_hashkey_url()
        assert "ws://ops.koreainvestment.com:31000" == config.get_ws_url()

    def test_custom_urls_override(self, monkeypatch, tmp_path):
        """커스텀 URL 오버라이드 확인"""
        monkeypatch.chdir(tmp_path)

        for key in ["KIS_MODE", "KIS_APP_KEY", "KIS_APP_SECRET", "SLACK_BOT_TOKEN", "SLACK_CHANNEL_ID"]:
            monkeypatch.delenv(key, raising=False)

        from stock_manager.adapters.broker.kis import KISConfig, Mode

        config = KISConfig(
            kis_mode=Mode.PAPER,  # PAPER 모드로 설정
            kis_rest_base_url="https://custom.rest.com",
            kis_ws_url="ws://custom.ws.com",
            kis_app_key="test_key",
            kis_app_secret="test_secret",
            slack_bot_token="test_slack_token",
            slack_channel_id="test_channel_id",
        )

        assert "custom.rest.com" in config.get_rest_base_url()
        assert "ws://custom.ws.com" == config.get_ws_url()

    def test_missing_app_key_raises_error(self, monkeypatch, tmp_path):
        """app_key 누락 시 ValidationError"""
        monkeypatch.chdir(tmp_path)

        for key in ["KIS_APP_KEY", "SLACK_BOT_TOKEN", "SLACK_CHANNEL_ID"]:
            monkeypatch.delenv(key, raising=False)

        from stock_manager.adapters.broker.kis import KISConfig

        with pytest.raises(ValidationError):
            KISConfig(
                kis_app_secret="test_secret",
                slack_bot_token="test_slack_token",
                slack_channel_id="test_channel_id",
            )

    def test_missing_app_secret_raises_error(self, monkeypatch, tmp_path):
        """app_secret 누락 시 ValidationError"""
        monkeypatch.chdir(tmp_path)

        for key in ["KIS_APP_SECRET", "SLACK_BOT_TOKEN", "SLACK_CHANNEL_ID"]:
            monkeypatch.delenv(key, raising=False)

        from stock_manager.adapters.broker.kis import KISConfig

        with pytest.raises(ValidationError):
            KISConfig(
                kis_app_key="test_key",
                slack_bot_token="test_slack_token",
                slack_channel_id="test_channel_id",
            )

    def test_request_timeout_default(self, monkeypatch, tmp_path):
        """요청 타임아웃 기본값 확인"""
        monkeypatch.chdir(tmp_path)

        for key in ["KIS_APP_KEY", "KIS_APP_SECRET", "SLACK_BOT_TOKEN", "SLACK_CHANNEL_ID"]:
            monkeypatch.delenv(key, raising=False)

        from stock_manager.adapters.broker.kis import KISConfig

        config = KISConfig(
            kis_app_key="test_key",
            kis_app_secret="test_secret",
            slack_bot_token="test_slack_token",
            slack_channel_id="test_channel_id",
        )
        assert config.request_timeout == 30

    def test_max_retries_default(self, monkeypatch, tmp_path):
        """최대 재시도 횟수 기본값 확인"""
        monkeypatch.chdir(tmp_path)

        for key in ["KIS_APP_KEY", "KIS_APP_SECRET", "SLACK_BOT_TOKEN", "SLACK_CHANNEL_ID"]:
            monkeypatch.delenv(key, raising=False)

        from stock_manager.adapters.broker.kis import KISConfig

        config = KISConfig(
            kis_app_key="test_key",
            kis_app_secret="test_secret",
            slack_bot_token="test_slack_token",
            slack_channel_id="test_channel_id",
        )
        assert config.max_retries == 3
