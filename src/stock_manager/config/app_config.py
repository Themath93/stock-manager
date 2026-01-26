"""통합 앱 설정

KIS, Slack, 공통 설정을 통합 관리합니다.
"""

from enum import Enum
from typing import Optional

from pydantic import ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings


class Mode(str, Enum):
    """운영 모드"""

    LIVE = "LIVE"
    PAPER = "PAPER"


class AppConfig(BaseSettings):
    """Stock Manager 통합 설정"""

    model_config = ConfigDict(env_file=".env", case_sensitive=False)

    # ===== KIS 설정 =====
    # 환경 모드
    kis_mode: Mode = Field(default=Mode.PAPER, description="운영 모드 (LIVE/PAPER)")

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
    kis_request_timeout: int = Field(default=30, description="API 요청 타임아웃 (초)")

    # 최대 재시도 횟수
    kis_max_retries: int = Field(default=3, description="최대 재시도 횟수")

    # ===== Slack 설정 =====
    slack_bot_token: str = Field(..., description="Slack Bot Token")
    slack_channel_id: str = Field(..., description="Slack Channel ID")

    # ===== 공통 설정 =====
    log_level: str = Field(default="INFO", description="로그 레벨")

    # 계좌 ID (선택사항)
    # TASK-001: SPEC-BACKEND-API-001-P3 Milestone 1 - Add account_id validation
    account_id: Optional[str] = Field(None, description="계좌 ID (10 digit numeric)")

    @field_validator("account_id")
    @classmethod
    def validate_account_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate account_id format (10 digit numeric)"""
        if v is None:
            return v
        if len(v) != 10 or not v.isdigit():
            raise ValueError("account_id must be exactly 10 digits")
        return v

    # ===== KIS URL 헬퍼 메서드 =====
    def get_kis_rest_base_url(self) -> str:
        """운영 모드에 따른 REST 기본 URL 반환"""
        if self.kis_mode == Mode.LIVE:
            return "https://openapi.koreainvestment.com:9443"
        return self.kis_rest_base_url

    def get_kis_token_url(self) -> str:
        """운영 모드에 따른 토큰 URL 반환"""
        if self.kis_mode == Mode.LIVE:
            return "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
        return self.kis_token_url

    def get_kis_hashkey_url(self) -> str:
        """운영 모드에 따른 해시키 URL 반환"""
        if self.kis_mode == Mode.LIVE:
            return "https://openapi.koreainvestment.com:9443/uapi/hashkey"
        return self.kis_hashkey_url

    def get_kis_ws_url(self) -> str:
        """운영 모드에 따른 WebSocket URL 반환"""
        if self.kis_mode == Mode.LIVE:
            return "ws://ops.koreainvestment.com:21000"
        return self.kis_ws_url
