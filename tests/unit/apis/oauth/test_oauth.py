"""Comprehensive unit tests for KIS OAuth API functions.

Tests cover all OAuth functions including:
- issue_access_token (3 variants)
- revoke_access_token (3 variants)
- generate_hash_key (3 variants)
- approve_websocket_key (3 variants)
- get_oauth_url helper

Edge cases include:
- HTTP errors (4xx, 5xx)
- Timeouts
- Invalid responses
- Network errors
"""

import json
from unittest.mock import Mock, patch

import httpx
import pytest

from stock_manager.adapters.broker.kis.apis.oauth.oauth import (
    approve_websocket_key,
    approve_websocket_key_paper,
    approve_websocket_key_real,
    generate_hash_key,
    generate_hash_key_paper,
    generate_hash_key_real,
    get_oauth_url,
    issue_access_token,
    issue_access_token_paper,
    issue_access_token_real,
    revoke_access_token,
    revoke_access_token_paper,
    revoke_access_token_real,
)


# =============================================================================
# Test Constants
# =============================================================================

TEST_APP_KEY = "test_app_key_12345"
TEST_APP_SECRET = "test_app_secret_67890"
TEST_ACCESS_TOKEN = "test_access_token_abc"
TEST_CUSTTYPE_P = "P"
TEST_CUSTTYPE_B = "B"

SUCCESS_TOKEN_RESPONSE = {
    "rt_cd": "0",
    "msg_cd": "000",
    "msg1": "정상적으로 처리되었습니다.",
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 86400,
}

SUCCESS_REVOKE_RESPONSE = {
    "rt_cd": "0",
    "msg_cd": "000",
    "msg1": "정상적으로 처리되었습니다.",
}

SUCCESS_HASH_RESPONSE = {
    "rt_cd": "0",
    "msg_cd": "000",
    "msg1": "정상적으로 처리되었습니다.",
    "hash": "dGVzdF9oYXNoX2tleQ==",
}

SUCCESS_WEBSOCKET_RESPONSE = {
    "rt_cd": "0",
    "msg_cd": "000",
    "msg1": "정상적으로 처리되었습니다.",
    "approval_key": "test_approval_key_xyz",
    "token_type": "Bearer",
}

ERROR_RESPONSE = {
    "rt_cd": "1",
    "msg_cd": "EGW00223",
    "msg1": "그래도 HTTP STATUS CODE: 401",
}


# =============================================================================
# get_oauth_url Tests
# =============================================================================

class TestGetOAuthUrl:
    """Tests for get_oauth_url helper function."""

    def test_get_oauth_url_paper_trading(self):
        """Test URL generation for paper trading environment."""
        url = get_oauth_url("/oauth2/tokenP", is_paper_trading=True)
        assert url == "https://openapivts.koreainvestment.com:29443/oauth2/tokenP"

    def test_get_oauth_url_real_trading(self):
        """Test URL generation for real trading environment."""
        url = get_oauth_url("/oauth2/tokenP", is_paper_trading=False)
        assert url == "https://openapi.koreainvestment.com:9443/oauth2/tokenP"

    def test_get_oauth_url_different_paths(self):
        """Test URL generation with different API paths."""
        paths = [
            "/oauth2/tokenP",
            "/oauth2/revokeP",
            "/uapi/hashkey",
            "/oauth2/Approval",
        ]
        for path in paths:
            url = get_oauth_url(path, is_paper_trading=True)
            assert url.startswith("https://openapivts.koreainvestment.com:29443")
            assert url.endswith(path)

    def test_get_oauth_url_default_paper_trading(self):
        """Test that default is_paper_trading is True."""
        url = get_oauth_url("/oauth2/tokenP")
        assert url == "https://openapivts.koreainvestment.com:29443/oauth2/tokenP"


# =============================================================================
# issue_access_token Tests
# =============================================================================

class TestIssueAccessToken:
    """Tests for issue_access_token function and variants."""

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_issue_access_token_paper_trading_success(self, mock_post):
        """Test successful access token issuance for paper trading."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SUCCESS_TOKEN_RESPONSE
        mock_post.return_value = mock_response

        result = issue_access_token(
            app_key=TEST_APP_KEY,
            app_secret=TEST_APP_SECRET,
            is_paper_trading=True,
        )

        assert result["rt_cd"] == "0"
        assert "access_token" in result
        assert result["token_type"] == "Bearer"
        assert result["expires_in"] == 86400

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://openapivts.koreainvestment.com:29443/oauth2/tokenP"
        assert call_args[1]["json"]["grant_type"] == "client_credentials"
        assert call_args[1]["headers"]["appkey"] == TEST_APP_KEY
        assert call_args[1]["headers"]["appsecret"] == TEST_APP_SECRET
        assert call_args[1]["timeout"] == 30.0

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_issue_access_token_real_trading_success(self, mock_post):
        """Test successful access token issuance for real trading."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SUCCESS_TOKEN_RESPONSE
        mock_post.return_value = mock_response

        result = issue_access_token(
            app_key=TEST_APP_KEY,
            app_secret=TEST_APP_SECRET,
            is_paper_trading=False,
        )

        assert result["rt_cd"] == "0"
        assert "access_token" in result

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://openapi.koreainvestment.com:9443/oauth2/tokenP"

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_issue_access_token_corporate_custtype(self, mock_post):
        """Test access token issuance with corporate customer type."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SUCCESS_TOKEN_RESPONSE
        mock_post.return_value = mock_response

        result = issue_access_token(
            app_key=TEST_APP_KEY,
            app_secret=TEST_APP_SECRET,
            custtype="B",
        )

        assert result["rt_cd"] == "0"

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["headers"]["custtype"] == "B"

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_issue_access_token_http_error_401(self, mock_post):
        """Test handling of HTTP 401 Unauthorized error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=Mock(), response=mock_response
        )
        mock_post.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            issue_access_token(
                app_key=TEST_APP_KEY,
                app_secret=TEST_APP_SECRET,
            )

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_issue_access_token_http_error_500(self, mock_post):
        """Test handling of HTTP 500 Internal Server error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Internal Server Error", request=Mock(), response=mock_response
        )
        mock_post.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            issue_access_token(
                app_key=TEST_APP_KEY,
                app_secret=TEST_APP_SECRET,
            )

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_issue_access_token_timeout(self, mock_post):
        """Test handling of request timeout."""
        mock_post.side_effect = httpx.TimeoutException(
            "Request timed out", request=Mock()
        )

        with pytest.raises(httpx.TimeoutException):
            issue_access_token(
                app_key=TEST_APP_KEY,
                app_secret=TEST_APP_SECRET,
            )

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_issue_access_token_network_error(self, mock_post):
        """Test handling of network connection error."""
        mock_post.side_effect = httpx.NetworkError(
            "Connection failed", request=Mock()
        )

        with pytest.raises(httpx.NetworkError):
            issue_access_token(
                app_key=TEST_APP_KEY,
                app_secret=TEST_APP_SECRET,
            )


# =============================================================================
# issue_access_token_real Tests
# =============================================================================

class TestIssueAccessTokenReal:
    """Tests for issue_access_token_real convenience function."""

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_issue_access_token_real_success(self, mock_post):
        """Test successful access token issuance for real trading."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SUCCESS_TOKEN_RESPONSE
        mock_post.return_value = mock_response

        result = issue_access_token_real(
            app_key=TEST_APP_KEY,
            app_secret=TEST_APP_SECRET,
        )

        assert result["rt_cd"] == "0"

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://openapi.koreainvestment.com:9443/oauth2/tokenP"

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_issue_access_token_real_with_custtype(self, mock_post):
        """Test real trading token issuance with customer type."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SUCCESS_TOKEN_RESPONSE
        mock_post.return_value = mock_response

        result = issue_access_token_real(
            app_key=TEST_APP_KEY,
            app_secret=TEST_APP_SECRET,
            custtype="B",
        )

        assert result["rt_cd"] == "0"

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["headers"]["custtype"] == "B"


# =============================================================================
# issue_access_token_paper Tests
# =============================================================================

class TestIssueAccessTokenPaper:
    """Tests for issue_access_token_paper convenience function."""

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_issue_access_token_paper_success(self, mock_post):
        """Test successful access token issuance for paper trading."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SUCCESS_TOKEN_RESPONSE
        mock_post.return_value = mock_response

        result = issue_access_token_paper(
            app_key=TEST_APP_KEY,
            app_secret=TEST_APP_SECRET,
        )

        assert result["rt_cd"] == "0"

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://openapivts.koreainvestment.com:29443/oauth2/tokenP"

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_issue_access_token_paper_with_custtype(self, mock_post):
        """Test paper trading token issuance with customer type."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SUCCESS_TOKEN_RESPONSE
        mock_post.return_value = mock_response

        result = issue_access_token_paper(
            app_key=TEST_APP_KEY,
            app_secret=TEST_APP_SECRET,
            custtype="B",
        )

        assert result["rt_cd"] == "0"

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["headers"]["custtype"] == "B"


# =============================================================================
# revoke_access_token Tests
# =============================================================================

class TestRevokeAccessToken:
    """Tests for revoke_access_token function and variants."""

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_revoke_access_token_paper_trading_success(self, mock_post):
        """Test successful token revocation for paper trading."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SUCCESS_REVOKE_RESPONSE
        mock_post.return_value = mock_response

        result = revoke_access_token(
            app_key=TEST_APP_KEY,
            app_secret=TEST_APP_SECRET,
            access_token=TEST_ACCESS_TOKEN,
            is_paper_trading=True,
        )

        assert result["rt_cd"] == "0"
        assert result["msg1"] == "정상적으로 처리되었습니다."

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://openapivts.koreainvestment.com:29443/oauth2/revokeP"
        assert call_args[1]["json"]["token"] == TEST_ACCESS_TOKEN

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_revoke_access_token_real_trading_success(self, mock_post):
        """Test successful token revocation for real trading."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SUCCESS_REVOKE_RESPONSE
        mock_post.return_value = mock_response

        result = revoke_access_token(
            app_key=TEST_APP_KEY,
            app_secret=TEST_APP_SECRET,
            access_token=TEST_ACCESS_TOKEN,
            is_paper_trading=False,
        )

        assert result["rt_cd"] == "0"

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://openapi.koreainvestment.com:9443/oauth2/revokeP"

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_revoke_access_token_with_corporate_custtype(self, mock_post):
        """Test token revocation with corporate customer type."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SUCCESS_REVOKE_RESPONSE
        mock_post.return_value = mock_response

        result = revoke_access_token(
            app_key=TEST_APP_KEY,
            app_secret=TEST_APP_SECRET,
            access_token=TEST_ACCESS_TOKEN,
            custtype="B",
        )

        assert result["rt_cd"] == "0"

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["headers"]["custtype"] == "B"

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_revoke_access_token_http_error_404(self, mock_post):
        """Test handling of HTTP 404 Not Found error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=mock_response
        )
        mock_post.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            revoke_access_token(
                app_key=TEST_APP_KEY,
                app_secret=TEST_APP_SECRET,
                access_token=TEST_ACCESS_TOKEN,
            )

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_revoke_access_token_timeout(self, mock_post):
        """Test handling of timeout during token revocation."""
        mock_post.side_effect = httpx.TimeoutException(
            "Request timed out", request=Mock()
        )

        with pytest.raises(httpx.TimeoutException):
            revoke_access_token(
                app_key=TEST_APP_KEY,
                app_secret=TEST_APP_SECRET,
                access_token=TEST_ACCESS_TOKEN,
            )

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_revoke_access_token_network_error(self, mock_post):
        """Test handling of network error during token revocation."""
        mock_post.side_effect = httpx.NetworkError(
            "Connection failed", request=Mock()
        )

        with pytest.raises(httpx.NetworkError):
            revoke_access_token(
                app_key=TEST_APP_KEY,
                app_secret=TEST_APP_SECRET,
                access_token=TEST_ACCESS_TOKEN,
            )


# =============================================================================
# revoke_access_token_real Tests
# =============================================================================

class TestRevokeAccessTokenReal:
    """Tests for revoke_access_token_real convenience function."""

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_revoke_access_token_real_success(self, mock_post):
        """Test successful token revocation for real trading."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SUCCESS_REVOKE_RESPONSE
        mock_post.return_value = mock_response

        result = revoke_access_token_real(
            app_key=TEST_APP_KEY,
            app_secret=TEST_APP_SECRET,
            access_token=TEST_ACCESS_TOKEN,
        )

        assert result["rt_cd"] == "0"

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://openapi.koreainvestment.com:9443/oauth2/revokeP"

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_revoke_access_token_real_with_custtype(self, mock_post):
        """Test real trading token revocation with customer type."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SUCCESS_REVOKE_RESPONSE
        mock_post.return_value = mock_response

        result = revoke_access_token_real(
            app_key=TEST_APP_KEY,
            app_secret=TEST_APP_SECRET,
            access_token=TEST_ACCESS_TOKEN,
            custtype="B",
        )

        assert result["rt_cd"] == "0"

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["headers"]["custtype"] == "B"


# =============================================================================
# revoke_access_token_paper Tests
# =============================================================================

class TestRevokeAccessTokenPaper:
    """Tests for revoke_access_token_paper convenience function."""

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_revoke_access_token_paper_success(self, mock_post):
        """Test successful token revocation for paper trading."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SUCCESS_REVOKE_RESPONSE
        mock_post.return_value = mock_response

        result = revoke_access_token_paper(
            app_key=TEST_APP_KEY,
            app_secret=TEST_APP_SECRET,
            access_token=TEST_ACCESS_TOKEN,
        )

        assert result["rt_cd"] == "0"

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://openapivts.koreainvestment.com:29443/oauth2/revokeP"

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_revoke_access_token_paper_with_custtype(self, mock_post):
        """Test paper trading token revocation with customer type."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SUCCESS_REVOKE_RESPONSE
        mock_post.return_value = mock_response

        result = revoke_access_token_paper(
            app_key=TEST_APP_KEY,
            app_secret=TEST_APP_SECRET,
            access_token=TEST_ACCESS_TOKEN,
            custtype="B",
        )

        assert result["rt_cd"] == "0"

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["headers"]["custtype"] == "B"


# =============================================================================
# generate_hash_key Tests
# =============================================================================

class TestGenerateHashKey:
    """Tests for generate_hash_key function and variants."""

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_generate_hash_key_paper_trading_success(self, mock_post):
        """Test successful hash key generation for paper trading."""
        test_payload = {"symbol": "005930", "qty": 10}
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SUCCESS_HASH_RESPONSE
        mock_post.return_value = mock_response

        result = generate_hash_key(
            app_key=TEST_APP_KEY,
            app_secret=TEST_APP_SECRET,
            payload=test_payload,
            is_paper_trading=True,
        )

        assert result == "dGVzdF9oYXNoX2tleQ=="

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://openapivts.koreainvestment.com:29443/uapi/hashkey"
        assert call_args[1]["json"] == test_payload

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_generate_hash_key_real_trading_success(self, mock_post):
        """Test successful hash key generation for real trading."""
        test_payload = {"symbol": "005930", "qty": 10}
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SUCCESS_HASH_RESPONSE
        mock_post.return_value = mock_response

        result = generate_hash_key(
            app_key=TEST_APP_KEY,
            app_secret=TEST_APP_SECRET,
            payload=test_payload,
            is_paper_trading=False,
        )

        assert result == "dGVzdF9oYXNoX2tleQ=="

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://openapi.koreainvestment.com:9443/uapi/hashkey"

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_generate_hash_key_with_complex_payload(self, mock_post):
        """Test hash key generation with complex payload."""
        test_payload = {
            "symbol": "005930",
            "qty": 10,
            "price": 85000,
            "order_type": "limit",
        }
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SUCCESS_HASH_RESPONSE
        mock_post.return_value = mock_response

        result = generate_hash_key(
            app_key=TEST_APP_KEY,
            app_secret=TEST_APP_SECRET,
            payload=test_payload,
        )

        assert result == "dGVzdF9oYXNoX2tleQ=="

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["json"] == test_payload

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_generate_hash_key_http_error_400(self, mock_post):
        """Test handling of HTTP 400 Bad Request error."""
        test_payload = {"symbol": "005930"}
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=Mock(), response=mock_response
        )
        mock_post.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            generate_hash_key(
                app_key=TEST_APP_KEY,
                app_secret=TEST_APP_SECRET,
                payload=test_payload,
            )

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_generate_hash_key_timeout(self, mock_post):
        """Test handling of timeout during hash key generation."""
        test_payload = {"symbol": "005930"}
        mock_post.side_effect = httpx.TimeoutException(
            "Request timed out", request=Mock()
        )

        with pytest.raises(httpx.TimeoutException):
            generate_hash_key(
                app_key=TEST_APP_KEY,
                app_secret=TEST_APP_SECRET,
                payload=test_payload,
            )

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_generate_hash_key_network_error(self, mock_post):
        """Test handling of network error during hash key generation."""
        test_payload = {"symbol": "005930"}
        mock_post.side_effect = httpx.NetworkError(
            "Connection failed", request=Mock()
        )

        with pytest.raises(httpx.NetworkError):
            generate_hash_key(
                app_key=TEST_APP_KEY,
                app_secret=TEST_APP_SECRET,
                payload=test_payload,
            )

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_generate_hash_key_empty_hash_in_response(self, mock_post):
        """Test handling of missing hash key in response."""
        test_payload = {"symbol": "005930"}
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"rt_cd": "0", "msg_cd": "000", "msg1": "OK"}
        mock_post.return_value = mock_response

        result = generate_hash_key(
            app_key=TEST_APP_KEY,
            app_secret=TEST_APP_SECRET,
            payload=test_payload,
        )

        assert result == ""


# =============================================================================
# generate_hash_key_real Tests
# =============================================================================

class TestGenerateHashKeyReal:
    """Tests for generate_hash_key_real convenience function."""

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_generate_hash_key_real_success(self, mock_post):
        """Test successful hash key generation for real trading."""
        test_payload = {"symbol": "005930", "qty": 10}
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SUCCESS_HASH_RESPONSE
        mock_post.return_value = mock_response

        result = generate_hash_key_real(
            app_key=TEST_APP_KEY,
            app_secret=TEST_APP_SECRET,
            payload=test_payload,
        )

        assert result == "dGVzdF9oYXNoX2tleQ=="

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://openapi.koreainvestment.com:9443/uapi/hashkey"


# =============================================================================
# generate_hash_key_paper Tests
# =============================================================================

class TestGenerateHashKeyPaper:
    """Tests for generate_hash_key_paper convenience function."""

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_generate_hash_key_paper_success(self, mock_post):
        """Test successful hash key generation for paper trading."""
        test_payload = {"symbol": "005930", "qty": 10}
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SUCCESS_HASH_RESPONSE
        mock_post.return_value = mock_response

        result = generate_hash_key_paper(
            app_key=TEST_APP_KEY,
            app_secret=TEST_APP_SECRET,
            payload=test_payload,
        )

        assert result == "dGVzdF9oYXNoX2tleQ=="

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://openapivts.koreainvestment.com:29443/uapi/hashkey"


# =============================================================================
# approve_websocket_key Tests
# =============================================================================

class TestApproveWebsocketKey:
    """Tests for approve_websocket_key function and variants."""

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_approve_websocket_key_paper_trading_success(self, mock_post):
        """Test successful WebSocket approval key generation for paper trading."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SUCCESS_WEBSOCKET_RESPONSE
        mock_post.return_value = mock_response

        result = approve_websocket_key(
            app_key=TEST_APP_KEY,
            app_secret=TEST_APP_SECRET,
            access_token=TEST_ACCESS_TOKEN,
            is_paper_trading=True,
        )

        assert result["rt_cd"] == "0"
        assert result["approval_key"] == "test_approval_key_xyz"

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://openapivts.koreainvestment.com:29443/oauth2/Approval"
        assert call_args[1]["headers"]["Authorization"] == f"Bearer {TEST_ACCESS_TOKEN}"
        assert call_args[1]["json"] == {}

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_approve_websocket_key_real_trading_success(self, mock_post):
        """Test successful WebSocket approval key generation for real trading."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SUCCESS_WEBSOCKET_RESPONSE
        mock_post.return_value = mock_response

        result = approve_websocket_key(
            app_key=TEST_APP_KEY,
            app_secret=TEST_APP_SECRET,
            access_token=TEST_ACCESS_TOKEN,
            is_paper_trading=False,
        )

        assert result["rt_cd"] == "0"
        assert result["approval_key"] == "test_approval_key_xyz"

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://openapi.koreainvestment.com:9443/oauth2/Approval"

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_approve_websocket_key_with_corporate_custtype(self, mock_post):
        """Test WebSocket approval key with corporate customer type."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SUCCESS_WEBSOCKET_RESPONSE
        mock_post.return_value = mock_response

        result = approve_websocket_key(
            app_key=TEST_APP_KEY,
            app_secret=TEST_APP_SECRET,
            access_token=TEST_ACCESS_TOKEN,
            custtype="B",
        )

        assert result["rt_cd"] == "0"

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["headers"]["custtype"] == "B"

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_approve_websocket_key_http_error_403(self, mock_post):
        """Test handling of HTTP 403 Forbidden error."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Forbidden", request=Mock(), response=mock_response
        )
        mock_post.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            approve_websocket_key(
                app_key=TEST_APP_KEY,
                app_secret=TEST_APP_SECRET,
                access_token=TEST_ACCESS_TOKEN,
            )

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_approve_websocket_key_timeout(self, mock_post):
        """Test handling of timeout during WebSocket key approval."""
        mock_post.side_effect = httpx.TimeoutException(
            "Request timed out", request=Mock()
        )

        with pytest.raises(httpx.TimeoutException):
            approve_websocket_key(
                app_key=TEST_APP_KEY,
                app_secret=TEST_APP_SECRET,
                access_token=TEST_ACCESS_TOKEN,
            )

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_approve_websocket_key_network_error(self, mock_post):
        """Test handling of network error during WebSocket key approval."""
        mock_post.side_effect = httpx.NetworkError(
            "Connection failed", request=Mock()
        )

        with pytest.raises(httpx.NetworkError):
            approve_websocket_key(
                app_key=TEST_APP_KEY,
                app_secret=TEST_APP_SECRET,
                access_token=TEST_ACCESS_TOKEN,
            )


# =============================================================================
# approve_websocket_key_real Tests
# =============================================================================

class TestApproveWebsocketKeyReal:
    """Tests for approve_websocket_key_real convenience function."""

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_approve_websocket_key_real_success(self, mock_post):
        """Test successful WebSocket approval key for real trading."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SUCCESS_WEBSOCKET_RESPONSE
        mock_post.return_value = mock_response

        result = approve_websocket_key_real(
            app_key=TEST_APP_KEY,
            app_secret=TEST_APP_SECRET,
            access_token=TEST_ACCESS_TOKEN,
        )

        assert result["rt_cd"] == "0"
        assert result["approval_key"] == "test_approval_key_xyz"

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://openapi.koreainvestment.com:9443/oauth2/Approval"

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_approve_websocket_key_real_with_custtype(self, mock_post):
        """Test real trading WebSocket key with customer type."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SUCCESS_WEBSOCKET_RESPONSE
        mock_post.return_value = mock_response

        result = approve_websocket_key_real(
            app_key=TEST_APP_KEY,
            app_secret=TEST_APP_SECRET,
            access_token=TEST_ACCESS_TOKEN,
            custtype="B",
        )

        assert result["rt_cd"] == "0"

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["headers"]["custtype"] == "B"


# =============================================================================
# approve_websocket_key_paper Tests
# =============================================================================

class TestApproveWebsocketKeyPaper:
    """Tests for approve_websocket_key_paper convenience function."""

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_approve_websocket_key_paper_success(self, mock_post):
        """Test successful WebSocket approval key for paper trading."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SUCCESS_WEBSOCKET_RESPONSE
        mock_post.return_value = mock_response

        result = approve_websocket_key_paper(
            app_key=TEST_APP_KEY,
            app_secret=TEST_APP_SECRET,
            access_token=TEST_ACCESS_TOKEN,
        )

        assert result["rt_cd"] == "0"
        assert result["approval_key"] == "test_approval_key_xyz"

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://openapivts.koreainvestment.com:29443/oauth2/Approval"

    @patch("stock_manager.adapters.broker.kis.apis.oauth.oauth.httpx.post")
    def test_approve_websocket_key_paper_with_custtype(self, mock_post):
        """Test paper trading WebSocket key with customer type."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SUCCESS_WEBSOCKET_RESPONSE
        mock_post.return_value = mock_response

        result = approve_websocket_key_paper(
            app_key=TEST_APP_KEY,
            app_secret=TEST_APP_SECRET,
            access_token=TEST_ACCESS_TOKEN,
            custtype="B",
        )

        assert result["rt_cd"] == "0"

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["headers"]["custtype"] == "B"
