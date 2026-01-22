"""KIS OpenAPI Configuration"""

from enum import Enum
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Mode(str, Enum):
    """운영 모드"""
    LIVE = "LIVE"
    PAPER = "PAPER"


class KISConfig(BaseSettings):
    """한국투자증권 OpenAPI 설정"""

    # 환경 모드
    mode: Mode = Field(default=Mode.PAPER, description="운영 모드 (LIVE/PAPER)")

    # API 키
    kis_app_key: str = Field(..., description="KIS 앱키")
    kis_app_secret: str = Field(..., description="KIS 앱시크릿키")

    # REST API URL
    kis_rest_base_url: str = Field(
        default="https://openapivts.koreainvestment.com:29443",
        description="REST API 기본 URL (기본: 모의투자)",
    )
    kis_token_url: str = Field(
        default="https://openapivts.koreainvestment.com:29443/oauth2/tokenP",
        description="토큰 발급 URL (기본: 모의투자)",
    )
    kis_hashkey_url: str = Field(
        default="https://openapivts.koreainvestment.com:29443/uapi/hashkey",
        description="해시키 발급 URL (기본: 모의투자)",
    )

    # WebSocket URL
    kis_ws_url: str = Field(
        default="ws://ops.koreainvestment.com:31000",
        description="WebSocket URL (기본: 모의투자)",
    )

    # 요청 타임아웃
    request_timeout: int = Field(default=30, description="API 요청 타임아웃 (초)")

    # 최대 재시도 횟수
    max_retries: int = Field(default=3, description="최대 재시도 횟수")

    class Config:
        env_prefix = "KIS_"
        env_file = ".env"
        case_sensitive = False

    def get_rest_base_url(self) -> str:
        """운영 모드에 따른 REST 기본 URL 반환"""
        if self.mode == Mode.LIVE:
            return "https://openapi.koreainvestment.com:9443"
        return self.kis_rest_base_url

    def get_token_url(self) -> str:
        """운영 모드에 따른 토큰 URL 반환"""
        if self.mode == Mode.LIVE:
            return "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
        return self.kis_token_url

    def get_hashkey_url(self) -> str:
        """운영 모드에 따른 해시키 URL 반환"""
        if self.mode == Mode.LIVE:
            return "https://openapi.koreainvestment.com:9443/uapi/hashkey"
        return self.kis_hashkey_url

    def get_ws_url(self) -> str:
        """운영 모드에 따른 WebSocket URL 반환"""
        if self.mode == Mode.LIVE:
            return "ws://ops.koreainvestment.com:21000"
        return self.kis_ws_url
