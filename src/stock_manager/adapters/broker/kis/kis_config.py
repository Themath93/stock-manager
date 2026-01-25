"""KIS OpenAPI Configuration"""

from enum import Enum
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings

from stock_manager.config.app_config import AppConfig

class Mode(str, Enum):
    """운영 모드"""

    LIVE = "LIVE"
    PAPER = "PAPER"


class KISConfig(AppConfig):
    """한국투자증권 OpenAPI 설정"""

    # Note: All fields are inherited from AppConfig
    # - kis_mode (from AppConfig.kis_mode)
    # - kis_app_key, kis_app_secret (from AppConfig)
    # - URL fields, timeout, retries (from AppConfig)

    @property
    def mode(self) -> Mode:
        """운영 모드 (AppConfig.kis_mode 별칭)"""
        return self.kis_mode

    @property
    def request_timeout(self) -> int:
        """요청 타임아웃 (AppConfig.kis_request_timeout 별칭)"""
        return self.kis_request_timeout

    @property
    def max_retries(self) -> int:
        """최대 재시도 횟수 (AppConfig.kis_max_retries 별칭)"""
        return self.kis_max_retries

    class Config:
        env_prefix = "KIS_"
        env_file = ".env"
        case_sensitive = False

    def get_rest_base_url(self) -> str:
        """운영 모드에 따른 REST 기본 URL 반환"""
        if self.kis_mode == Mode.LIVE:
            return "https://openapi.koreainvestment.com:9443"
        return self.get_kis_rest_base_url()

    def get_token_url(self) -> str:
        """운영 모드에 따른 토큰 URL 반환"""
        if self.kis_mode == Mode.LIVE:
            return "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
        return self.get_kis_token_url()

    def get_hashkey_url(self) -> str:
        """운영 모드에 따른 해시키 URL 반환"""
        if self.kis_mode == Mode.LIVE:
            return "https://openapi.koreainvestment.com:9443/uapi/hashkey"
        return self.get_kis_hashkey_url()

    def get_ws_url(self) -> str:
        """운영 모드에 따른 WebSocket URL 반환"""
        if self.kis_mode == Mode.LIVE:
            return "ws://ops.koreainvestment.com:21000"
        return self.get_kis_ws_url()

    def get_approval_url(self) -> str:
        """운영 모드에 따른 approval_key 발급 URL 반환
        
        TAG-001: SPEC-BACKEND-API-001 NEW-001 WebSocket approval_key 발급
        """
        if self.kis_mode == Mode.LIVE:
            return "https://openapi.koreainvestment.com:9443/oauth2/Approval"
        # 모의투자 URL
        return "https://openapivts.koreainvestment.com:29443/oauth2/Approval"
