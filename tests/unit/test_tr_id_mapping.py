"""Unit tests for TR_ID mapping functionality"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from stock_manager.adapters.broker.kis import KISConfig
from stock_manager.adapters.broker.kis.kis_rest_client import KISRestClient


class TestTRIdMapping:
    """TR_ID mapping 테스트"""

    @pytest.fixture
    def config(self):
        """테스트용 설정"""
        return KISConfig(
            kis_app_key="test_key",
            kis_app_secret="test_secret",
        )

    @pytest.fixture
    def sample_mapping_data(self):
        """샘플 TR_ID 매핑 데이터"""
        return {
            "인증-001": {
                "name": "접근토큰발급(P)",
                "real_tr_id": "",
                "paper_tr_id": "",
                "category": "OAuth인증",
                "http_method": "POST",
                "url": "/oauth2/tokenP",
                "communication_type": "REST"
            },
            "국내주식-008": {
                "name": "주식잔고조회",
                "real_tr_id": "TTTC8001R",
                "paper_tr_id": "TTTC8001R",
                "category": "[국내주식] 주문/계좌",
                "http_method": "GET",
                "url": "/uapi/domestic-stock/v1/trading/inquire-balance",
                "communication_type": "REST"
            },
            "국내주식-211": {
                "name": "기간별계좌권리현황조회",
                "real_tr_id": "CTRGA011R",
                "paper_tr_id": "모의투자 미지원",
                "category": "[국내주식] 주문/계좌",
                "http_method": "GET",
                "url": "/uapi/domestic-stock/v1/trading/period-rights",
                "communication_type": "REST"
            }
        }

    @pytest.fixture
    def client_with_mapping(self, config, sample_mapping_data):
        """TR_ID 매핑이 로드된 클라이언트"""
        client = KISRestClient(config)

        # Create temporary mapping file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(sample_mapping_data, f, ensure_ascii=False)
            temp_file = Path(f.name)

        try:
            # Override the mapping file path
            client._TR_ID_MAPPING_FILE = temp_file
            yield client
        finally:
            # Clean up temp file
            temp_file.unlink(missing_ok=True)

    def test_get_tr_id_real_trading_success(self, client_with_mapping):
        """실전 투자 TR_ID 조회 성공 테스트"""
        tr_id = client_with_mapping.get_tr_id("국내주식-008", is_paper_trading=False)

        assert tr_id == "TTTC8001R"

    def test_get_tr_id_paper_trading_success(self, client_with_mapping):
        """모의 투자 TR_ID 조회 성공 테스트"""
        tr_id = client_with_mapping.get_tr_id("국내주식-008", is_paper_trading=True)

        assert tr_id == "TTTC8001R"

    def test_get_tr_id_paper_trading_unsupported_returns_none(self, client_with_mapping):
        """모의 투자 미지원 API는 None 반환 테스트"""
        tr_id = client_with_mapping.get_tr_id("국내주식-211", is_paper_trading=True)

        assert tr_id is None

    def test_get_tr_id_empty_tr_id_returns_none(self, client_with_mapping):
        """빈 TR_ID는 None 반환 테스트"""
        tr_id = client_with_mapping.get_tr_id("인증-001", is_paper_trading=False)

        assert tr_id is None

    def test_get_tr_id_api_id_not_found_raises_error(self, client_with_mapping):
        """존재하지 않는 API ID로 조회 시 ValueError 발생"""
        with pytest.raises(ValueError) as exc_info:
            client_with_mapping.get_tr_id("존재하지않는-API", is_paper_trading=False)

        assert "not found in TR_ID mapping" in str(exc_info.value)

    def test_load_tr_id_mapping_file_not_found(self, config):
        """매핑 파일이 존재하지 않을 때 빈 딕셔너리 반환 테스트"""
        client = KISRestClient(config)

        # Set non-existent file path
        client._TR_ID_MAPPING_FILE = Path("/nonexistent/path/tr_id_mapping.json")

        # Should return empty dict without raising exception
        mapping = client._load_tr_id_mapping()

        assert mapping == {}

    def test_load_tr_id_mapping_caching(self, client_with_mapping):
        """매핑 캐싱 기능 테스트"""
        # First load
        mapping1 = client_with_mapping._load_tr_id_mapping()

        # Second load should return cached version
        mapping2 = client_with_mapping._load_tr_id_mapping()

        assert mapping1 is mapping2  # Same object reference

    def test_load_tr_id_mapping_thread_safety(self, config, sample_mapping_data):
        """스레드 안전성 테스트"""
        client = KISRestClient(config)

        # Create temporary mapping file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(sample_mapping_data, f, ensure_ascii=False)
            temp_file = Path(f.name)

        try:
            client._TR_ID_MAPPING_FILE = temp_file

            # Load from multiple threads
            import threading

            results = []
            def load_mapping():
                results.append(client._load_tr_id_mapping())

            threads = [threading.Thread(target=load_mapping) for _ in range(10)]

            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # All threads should get the same result
            assert len(results) == 10
            assert all(r is results[0] for r in results)

        finally:
            temp_file.unlink(missing_ok=True)

    def test_get_headers_with_tr_id(self, client_with_mapping):
        """tr_id가 포함된 헤더 생성 테스트"""
        from stock_manager.adapters.broker.port import AuthenticationToken
        from datetime import datetime, timedelta

        # Set token to avoid refresh
        client_with_mapping.token_manager._token = AuthenticationToken(
            access_token="test_token",
            token_type="Bearer",
            expires_in=3600,
            expires_at=datetime.now() + timedelta(hours=1),
        )

        headers = client_with_mapping._get_headers(tr_id="TTTC8001R", include_token=True)

        assert headers["tr_id"] == "TTTC8001R"
        assert headers["authorization"] == "Bearer test_token"
        assert headers["appkey"] == "test_key"

    def test_get_headers_without_tr_id(self, client_with_mapping):
        """tr_id가 없는 헤더 생성 테스트"""
        from stock_manager.adapters.broker.port import AuthenticationToken
        from datetime import datetime, timedelta

        # Set token to avoid refresh
        client_with_mapping.token_manager._token = AuthenticationToken(
            access_token="test_token",
            token_type="Bearer",
            expires_in=3600,
            expires_at=datetime.now() + timedelta(hours=1),
        )

        headers = client_with_mapping._get_headers(include_token=True)

        assert "tr_id" not in headers
        assert headers["authorization"] == "Bearer test_token"

    def test_get_headers_without_token(self, client_with_mapping):
        """토큰 없는 헤더 생성 테스트"""
        headers = client_with_mapping._get_headers(tr_id="TTTC8001R", include_token=False)

        assert headers["tr_id"] == "TTTC8001R"
        assert "authorization" not in headers

    def test_get_tr_id_paper_trading_unsupported_logs_warning(self, client_with_mapping, caplog):
        """모의 투자 미지원 API 경고 로그 테스트"""
        import logging

        with caplog.at_level(logging.WARNING):
            tr_id = client_with_mapping.get_tr_id("국내주식-211", is_paper_trading=True)

        assert tr_id is None
        assert any("not supported in paper trading" in record.message for record in caplog.records)

    def test_load_tr_id_mapping_invalid_json(self, config):
        """잘못된 JSON 파일 처리 테스트"""
        client = KISRestClient(config)

        # Create invalid JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{invalid json content")
            temp_file = Path(f.name)

        try:
            client._TR_ID_MAPPING_FILE = temp_file

            # Should return empty dict for invalid JSON
            mapping = client._load_tr_id_mapping()

            assert mapping == {}

        finally:
            temp_file.unlink(missing_ok=True)

    def test_get_tr_id_wrong_api_id_raises_error(self, client_with_mapping):
        """잘못된 API ID로 조회 시 ValueError 발생 테스트"""
        # Wrong API ID
        with pytest.raises(ValueError) as exc_info:
            client_with_mapping.get_tr_id("인증-999", is_paper_trading=False)

        assert "not found in TR_ID mapping" in str(exc_info.value)

        # Correct API ID should work
        tr_id = client_with_mapping.get_tr_id("국내주식-008", is_paper_trading=False)
        assert tr_id == "TTTC8001R"
