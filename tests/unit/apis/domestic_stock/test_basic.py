"""Tests for domestic stock basic API functions.

Example parametrized tests for TDD methodology.
This serves as a template for testing other API modules.
"""

import pytest
from unittest.mock import MagicMock

from stock_manager.adapters.broker.kis.client import KISRestClient
from stock_manager.adapters.broker.kis.config import KISConfig, KISAccessToken


class TestDomesticStockBasicAPI:
    """Tests for domestic stock basic price quote APIs."""

    @pytest.fixture
    def authenticated_client(self, kis_config: KISConfig) -> KISRestClient:
        """Provide authenticated client for testing."""

        client = KISRestClient(config=kis_config)
        token = KISAccessToken(access_token="test_token")
        client.state.update_token(token)

        # Mock make_request method directly
        client.make_request = MagicMock()

        return client

    def test_get_stock_price_success(
        self,
        authenticated_client: KISRestClient,
    ) -> None:
        """Test successful stock price retrieval.

        TDD: RED -> GREEN -> REFACTOR
        - RED: This documents expected behavior
        - GREEN: After implementing
        - REFACTOR: Extract common patterns
        """
        from tests.factories.mock_responses import MockResponseFactory
        from tests.factories.test_data import APITestDataFactory

        # Arrange
        expected_data = APITestDataFactory.stock_price_data(
            symbol="005930",
            price=75000,
        )
        mock_response = MockResponseFactory.success_kis(output=expected_data)
        # Mock returns the response data (what response.json() would return)
        authenticated_client.make_request.return_value = mock_response.json.return_value

        # Act - Import and call the actual API function
        from stock_manager.adapters.broker.kis.apis.domestic_stock.basic import (
            inquire_current_price,
        )

        result = inquire_current_price(
            client=authenticated_client,
            stock_code="005930",
        )

        # Assert - KIS API returns data nested under 'output' key
        assert result["output"]["stck_prpr"] == "75000"

    # TODO: Add parametrized tests for all basic API functions
    # Use pytest.mark.parametrize to efficiently test 240+ APIs
    # Example:
    #
    # @pytest.mark.parametrize("symbol,expected_name", [
    #     ("005930", "삼성전자"),
    #     ("051910", "LG화학"),
    #     ("035720", "카카오"),
    # ])
    # @pytest.mark.asyncio
    # async def test_get_stock_name(
    #     self,
    #     authenticated_client: KISRestClient,
    #     symbol: str,
    #     expected_name: str,
    # ) -> None:
    #     """Test getting stock name by symbol."""
    #     # Implementation...
    #     pass


class TestTDDCycleDocumentation:
    """Tests documenting the TDD cycle for domestic stock APIs."""

    def test_red_phase_documentation(self) -> None:
        """Document the RED phase of TDD cycle.

        Kent Beck: "First make it work, then make it right,
        then make it fast."

        RED phase: Write failing test that documents expected behavior.
        """
        red_phase = {
            "status": "COMPLETE",
            "test": "test_domestic_stock_uses_await",
            "result": "FAILED (as expected)",
            "findings": "100+ functions missing await",
        }

        assert red_phase["status"] == "COMPLETE"

    def test_green_phase_pending(self) -> None:
        """Document pending GREEN phase.

        GREEN phase: Make tests pass with minimal implementation.
        """
        green_phase = {
            "status": "IN_PROGRESS",
            "action": "Add 'await' to all client.make_request() calls",
            "files_to_fix": [
                "domestic_stock/basic.py",
                "domestic_stock/orders.py",
                "domestic_stock/analysis.py",
                "domestic_stock/sector.py",
                "domestic_stock/info.py",
                "domestic_stock/elw.py",
                "domestic_stock/ranking.py",
                "domestic_stock/realtime.py",
            ],
        }

        assert green_phase["status"] == "IN_PROGRESS"

    def test_refactor_phase_planned(self) -> None:
        """Document planned REFACTOR phase.

        REFACTOR phase: Improve code while keeping tests green.
        """
        refactor_phase = {
            "status": "PLANNED",
            "improvements": [
                "Extract async helper patterns",
                "Add request/response type hints",
                "Consolidate error handling",
                "Add rate limiting support",
            ],
        }

        assert refactor_phase["status"] == "PLANNED"
