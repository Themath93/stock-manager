from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock
import json

import pytest
from typer.testing import CliRunner

from stock_manager.main import build_app
import stock_manager.cli.trading_commands as trading_commands


def test_help_includes_run_trade_smoke_commands() -> None:
    runner = CliRunner()

    result = runner.invoke(build_app(), ["--help"])

    assert result.exit_code == 0
    assert "run" in result.stdout
    assert "trade" in result.stdout
    assert "smoke" in result.stdout


def test_trade_buy_is_dry_run_by_default(monkeypatch) -> None:
    runner = CliRunner()
    client = MagicMock()
    runtime = SimpleNamespace(
        config=SimpleNamespace(use_mock=True),
        client=client,
        account_number="12345678",
        account_product_code="01",
    )
    monkeypatch.setattr(trading_commands, "_build_runtime_context", lambda: runtime)

    result = runner.invoke(build_app(), ["trade", "buy", "005930", "10", "--price", "70000"])

    assert result.exit_code == 0
    assert "DRY-RUN BUY" in result.stdout
    client.authenticate.assert_not_called()
    client.make_request.assert_not_called()


def test_trade_execute_blocks_live_without_confirm_live(monkeypatch) -> None:
    runner = CliRunner()
    client = MagicMock()
    runtime = SimpleNamespace(
        config=SimpleNamespace(use_mock=False),
        client=client,
        account_number="12345678",
        account_product_code="01",
    )
    monkeypatch.setattr(trading_commands, "_build_runtime_context", lambda: runtime)

    result = runner.invoke(
        build_app(),
        ["trade", "buy", "005930", "10", "--price", "70000", "--execute"],
    )

    assert result.exit_code == 1
    assert "--confirm-live" in result.stdout
    client.authenticate.assert_not_called()


def test_trade_execute_blocks_live_without_promotion_gate_even_with_confirm_live(
    monkeypatch,
) -> None:
    runner = CliRunner()
    client = MagicMock()
    runtime = SimpleNamespace(
        config=SimpleNamespace(use_mock=False),
        client=client,
        account_number="12345678",
        account_product_code="01",
    )
    monkeypatch.setattr(trading_commands, "_build_runtime_context", lambda: runtime)

    result = runner.invoke(
        build_app(),
        [
            "trade",
            "buy",
            "005930",
            "10",
            "--price",
            "70000",
            "--execute",
            "--confirm-live",
        ],
    )

    assert result.exit_code == 1
    assert "promotion gate" in result.stdout.lower()
    client.authenticate.assert_not_called()


def test_trade_execute_live_with_valid_promotion_gate(monkeypatch, tmp_path) -> None:
    runner = CliRunner()
    client = MagicMock()
    runtime = SimpleNamespace(
        config=SimpleNamespace(use_mock=False),
        client=client,
        account_number="12345678",
        account_product_code="01",
    )
    monkeypatch.setattr(trading_commands, "_build_runtime_context", lambda: runtime)

    gate_path = tmp_path / ".sisyphus" / "evidence" / "mock-promotion-gate.json"
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate_path.write_text(json.dumps({"mode": "mock", "pass": True}), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    class FakeExecutor:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        def buy(self, **kwargs):
            return SimpleNamespace(success=True, broker_order_id="OID123", message="")

        def sell(self, **kwargs):
            return SimpleNamespace(success=True, broker_order_id="OID124", message="")

    monkeypatch.setattr(trading_commands, "OrderExecutor", FakeExecutor)

    result = runner.invoke(
        build_app(),
        [
            "trade",
            "buy",
            "005930",
            "10",
            "--price",
            "70000",
            "--execute",
            "--confirm-live",
        ],
    )

    assert result.exit_code == 0
    assert "ORDER OK BUY" in result.stdout
    client.authenticate.assert_called_once()


def test_trade_requires_price_option() -> None:
    runner = CliRunner()

    result = runner.invoke(build_app(), ["trade", "buy", "005930", "10"])

    assert result.exit_code != 0


def test_smoke_runs_auth_price_balance_only(monkeypatch) -> None:
    runner = CliRunner()
    client = MagicMock()
    client.make_request.return_value = {"rt_cd": "0", "output1": []}

    runtime = SimpleNamespace(
        config=SimpleNamespace(use_mock=True),
        client=client,
        account_number="12345678",
        account_product_code="01",
    )
    monkeypatch.setattr(trading_commands, "_build_runtime_context", lambda: runtime)

    price_called = {"value": False}
    balance_called = {"value": False}

    def fake_inquire_current_price(*, client, stock_code, is_paper_trading):
        price_called["value"] = True
        assert stock_code == "005930"
        assert is_paper_trading is True
        return {"rt_cd": "0", "output": {"stck_prpr": "70000"}}

    def fake_inquire_balance(*, cano, acnt_prdt_cd, is_paper_trading, **kwargs):
        balance_called["value"] = True
        assert cano == "12345678"
        assert acnt_prdt_cd == "01"
        assert is_paper_trading is True
        assert kwargs["AFHR_FLPR_YN"] == "N"
        assert kwargs["INQR_DVSN"] == "01"
        assert kwargs["UNPR_DVSN"] == "01"
        assert kwargs["FUND_STTL_ICLD_YN"] == "N"
        assert kwargs["FNCG_AMT_AUTO_RDPT_YN"] == "N"
        assert kwargs["PRCS_DVSN"] == "00"
        assert kwargs["CTX_AREA_FK100"] == ""
        assert kwargs["CTX_AREA_NK100"] == ""
        return {
            "tr_id": "VTTC8434R",
            "url_path": "/uapi/domestic-stock/v1/trading/inquire-balance",
            "params": {"CANO": "12345678", "ACNT_PRDT_CD": "01", **kwargs},
        }

    class ForbiddenOrderExecutor:
        def __init__(self, *args, **kwargs) -> None:
            raise AssertionError("OrderExecutor must not be used by smoke command")

    monkeypatch.setattr(trading_commands, "inquire_current_price", fake_inquire_current_price)
    monkeypatch.setattr(trading_commands, "inquire_balance", fake_inquire_balance)
    monkeypatch.setattr(trading_commands, "OrderExecutor", ForbiddenOrderExecutor)

    result = runner.invoke(build_app(), ["smoke"])

    assert result.exit_code == 0
    assert "Smoke OK" in result.stdout
    assert price_called["value"] is True
    assert balance_called["value"] is True
    client.authenticate.assert_called_once()
    client.make_request.assert_called_once()


def test_run_starts_and_stops_engine_with_duration(monkeypatch) -> None:
    runner = CliRunner()
    runtime = SimpleNamespace(
        config=SimpleNamespace(use_mock=True),
        client=MagicMock(),
        account_number="12345678",
        account_product_code="01",
    )
    monkeypatch.setattr(trading_commands, "_build_runtime_context", lambda: runtime)

    started = {"value": False}
    stopped = {"value": False}

    class FakeEngine:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        def start(self):
            started["value"] = True

        def stop(self):
            stopped["value"] = True

    monotonic_values = iter([0.0, 1.5])
    monkeypatch.setattr(trading_commands, "TradingEngine", FakeEngine)
    monkeypatch.setattr(trading_commands.time, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(trading_commands.time, "sleep", lambda _: None)
    monkeypatch.setattr(trading_commands.signal, "getsignal", lambda *_: None)
    monkeypatch.setattr(trading_commands.signal, "signal", lambda *_: None)

    result = runner.invoke(build_app(), ["run", "--duration-sec", "1", "--skip-auth"])

    assert result.exit_code == 0
    assert started["value"] is True
    assert stopped["value"] is True


def test_run_returns_nonzero_when_engine_start_fails(monkeypatch) -> None:
    runner = CliRunner()
    runtime = SimpleNamespace(
        config=SimpleNamespace(use_mock=True),
        client=MagicMock(),
        account_number="12345678",
        account_product_code="01",
    )
    monkeypatch.setattr(trading_commands, "_build_runtime_context", lambda: runtime)

    class FakeEngine:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        def start(self):
            raise RuntimeError("Startup reconciliation failed: test")

        def stop(self):
            raise AssertionError("stop() must not be called when start() fails")

    monkeypatch.setattr(trading_commands, "TradingEngine", FakeEngine)

    result = runner.invoke(build_app(), ["run", "--duration-sec", "1", "--skip-auth"])

    assert result.exit_code == 1
    assert "Run failed:" in result.stdout


def test_run_blocks_live_without_promotion_gate(monkeypatch) -> None:
    runner = CliRunner()
    runtime = SimpleNamespace(
        config=SimpleNamespace(use_mock=False),
        client=MagicMock(),
        account_number="12345678",
        account_product_code="01",
    )
    monkeypatch.setattr(trading_commands, "_build_runtime_context", lambda: runtime)

    class ForbiddenEngine:
        def __init__(self, **kwargs) -> None:
            raise AssertionError("engine_started_before_live_gate")

    monkeypatch.setattr(trading_commands, "TradingEngine", ForbiddenEngine)

    result = runner.invoke(build_app(), ["run", "--duration-sec", "1", "--skip-auth"])

    assert result.exit_code == 1
    assert "promotion gate" in result.stdout.lower()


def test_run_live_with_valid_promotion_gate(monkeypatch, tmp_path) -> None:
    runner = CliRunner()
    runtime = SimpleNamespace(
        config=SimpleNamespace(use_mock=False),
        client=MagicMock(),
        account_number="12345678",
        account_product_code="01",
    )
    monkeypatch.setattr(trading_commands, "_build_runtime_context", lambda: runtime)

    gate_path = tmp_path / ".sisyphus" / "evidence" / "mock-promotion-gate.json"
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate_path.write_text(json.dumps({"mode": "mock", "pass": True}), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    started = {"value": False}
    stopped = {"value": False}

    class FakeEngine:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        def start(self):
            started["value"] = True

        def stop(self):
            stopped["value"] = True

    monotonic_values = iter([0.0, 1.5])
    monkeypatch.setattr(trading_commands, "TradingEngine", FakeEngine)
    monkeypatch.setattr(trading_commands.time, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(trading_commands.time, "sleep", lambda _: None)
    monkeypatch.setattr(trading_commands.signal, "getsignal", lambda *_: None)
    monkeypatch.setattr(trading_commands.signal, "signal", lambda *_: None)

    result = runner.invoke(build_app(), ["run", "--duration-sec", "1", "--skip-auth"])

    assert result.exit_code == 0
    assert started["value"] is True
    assert stopped["value"] is True


def test_runtime_context_mock_mode_uses_mock_account_when_present(monkeypatch) -> None:
    monkeypatch.setenv("KIS_USE_MOCK", "true")
    monkeypatch.setenv("KIS_MOCK_APP_KEY", "mock_key_abc")
    monkeypatch.setenv("KIS_MOCK_SECRET", "mock_secret_def")
    monkeypatch.setenv("KIS_MOCK_ACCOUNT_NUMBER", "87654321")
    monkeypatch.setenv("KIS_ACCOUNT_PRODUCT_CODE", "01")

    monkeypatch.setenv("KIS_APP_KEY", "real_key_should_not_be_used")
    monkeypatch.setenv("KIS_APP_SECRET", "real_secret_should_not_be_used")
    monkeypatch.setenv("KIS_ACCOUNT_NUMBER", "12345678")

    runtime = trading_commands._build_runtime_context()

    assert runtime.config.use_mock is True
    assert runtime.account_number == "87654321"
    assert runtime.account_product_code == "01"


def test_runtime_context_mock_mode_blocks_real_account_fallback(monkeypatch) -> None:
    monkeypatch.setenv("KIS_USE_MOCK", "true")
    monkeypatch.setenv("KIS_MOCK_APP_KEY", "mock_key_abc")
    monkeypatch.setenv("KIS_MOCK_SECRET", "mock_secret_def")
    monkeypatch.setenv("KIS_MOCK_ACCOUNT_NUMBER", "")
    monkeypatch.setenv("KIS_ACCOUNT_PRODUCT_CODE", "01")
    monkeypatch.setenv("KIS_ACCOUNT_NUMBER", "12345678")

    with pytest.raises(ValueError) as excinfo:
        trading_commands._build_runtime_context()

    message = str(excinfo.value)
    assert "KIS_MOCK_ACCOUNT_NUMBER" in message
    assert "OPSQ2000" in message


def test_runtime_context_mock_mode_blocks_real_credentials_fallback(monkeypatch) -> None:
    monkeypatch.setenv("KIS_USE_MOCK", "true")
    monkeypatch.setenv("KIS_MOCK_APP_KEY", "")
    monkeypatch.setenv("KIS_MOCK_SECRET", "")
    monkeypatch.setenv("KIS_MOCK_ACCOUNT_NUMBER", "87654321")
    monkeypatch.setenv("KIS_ACCOUNT_PRODUCT_CODE", "01")

    monkeypatch.setenv("KIS_APP_KEY", "real_key")
    monkeypatch.setenv("KIS_APP_SECRET", "real_secret")
    monkeypatch.setenv("KIS_ACCOUNT_NUMBER", "12345678")

    with pytest.raises(ValueError) as excinfo:
        trading_commands._build_runtime_context()

    assert "KIS_MOCK_APP_KEY" in str(excinfo.value)


def test_runtime_context_invalid_account_format_is_blocked_early(monkeypatch) -> None:
    monkeypatch.setenv("KIS_USE_MOCK", "false")
    monkeypatch.setenv("KIS_APP_KEY", "real_key")
    monkeypatch.setenv("KIS_APP_SECRET", "real_secret")
    monkeypatch.setenv("KIS_ACCOUNT_NUMBER", "1234")
    monkeypatch.setenv("KIS_ACCOUNT_PRODUCT_CODE", "01")

    with pytest.raises(ValueError) as excinfo:
        trading_commands._build_runtime_context()

    message = str(excinfo.value)
    assert "KIS_ACCOUNT_NUMBER" in message
    assert "exactly 8 digits" in message


def test_normalize_account_settings_parses_canonical_account_number() -> None:
    account_number, product_code = trading_commands._normalize_account_settings("12345678-01", "")
    assert account_number == "12345678"
    assert product_code == "01"


def test_normalize_account_settings_splits_10_digit_account_when_product_code_missing() -> None:
    account_number, product_code = trading_commands._normalize_account_settings("1234567801", "")
    assert account_number == "12345678"
    assert product_code == "01"


def test_run_rejects_negative_duration() -> None:
    runner = CliRunner()
    result = runner.invoke(build_app(), ["run", "--duration-sec", "-1", "--skip-auth"])
    assert result.exit_code == 1
    assert "--duration-sec" in result.stdout


def test_run_authenticates_when_skip_auth_false(monkeypatch) -> None:
    runner = CliRunner()
    client = MagicMock()
    runtime = SimpleNamespace(
        config=SimpleNamespace(use_mock=True),
        client=client,
        account_number="12345678",
        account_product_code="01",
    )
    monkeypatch.setattr(trading_commands, "_build_runtime_context", lambda: runtime)

    class FakeEngine:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        def start(self):
            return None

        def stop(self):
            return None

    monotonic_values = iter([0.0, 1.5])
    monkeypatch.setattr(trading_commands, "TradingEngine", FakeEngine)
    monkeypatch.setattr(trading_commands.time, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(trading_commands.time, "sleep", lambda _: None)
    monkeypatch.setattr(trading_commands.signal, "getsignal", lambda *_: None)
    monkeypatch.setattr(trading_commands.signal, "signal", lambda *_: None)

    result = runner.invoke(build_app(), ["run", "--duration-sec", "1"])

    assert result.exit_code == 0
    client.authenticate.assert_called_once()


def test_run_prints_opsq2000_hint_in_mock_mode(monkeypatch) -> None:
    runner = CliRunner()
    client = MagicMock()
    runtime = SimpleNamespace(
        config=SimpleNamespace(use_mock=True),
        client=client,
        account_number="12345678",
        account_product_code="01",
    )
    monkeypatch.setattr(trading_commands, "_build_runtime_context", lambda: runtime)

    class FakeEngine:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        def start(self):
            raise RuntimeError("OPSQ2000 ERROR : INPUT INVALID_CHECK_ACNO")

        def stop(self):
            return None

    monkeypatch.setattr(trading_commands, "TradingEngine", FakeEngine)
    monkeypatch.setattr(trading_commands.signal, "getsignal", lambda *_: None)
    monkeypatch.setattr(trading_commands.signal, "signal", lambda *_: None)

    result = runner.invoke(build_app(), ["run", "--duration-sec", "0", "--skip-auth"])

    assert result.exit_code == 1
    assert "OPSQ2000" in result.stdout
    assert "KIS_MOCK_ACCOUNT_NUMBER" in result.stdout


def test_trade_execution_prints_opsq2000_hint_in_mock_mode(monkeypatch) -> None:
    runner = CliRunner()
    client = MagicMock()
    runtime = SimpleNamespace(
        config=SimpleNamespace(use_mock=True),
        client=client,
        account_number="12345678",
        account_product_code="01",
    )
    monkeypatch.setattr(trading_commands, "_build_runtime_context", lambda: runtime)

    class RaisingExecutor:
        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("INVALID_CHECK_ACNO")

    monkeypatch.setattr(trading_commands, "OrderExecutor", RaisingExecutor)

    result = runner.invoke(
        build_app(),
        [
            "trade",
            "buy",
            "005930",
            "1",
            "--price",
            "70000",
            "--execute",
        ],
    )

    assert result.exit_code == 1
    assert "INVALID_CHECK_ACNO" in result.stdout
    assert "KIS_MOCK_ACCOUNT_NUMBER" in result.stdout


def test_smoke_prints_opsq2000_hint_when_balance_returns_invalid_account(monkeypatch) -> None:
    runner = CliRunner()
    client = MagicMock()
    client.make_request.return_value = {
        "rt_cd": "-1",
        "msg1": "OPSQ2000 ERROR : INPUT INVALID_CHECK_ACNO",
    }

    runtime = SimpleNamespace(
        config=SimpleNamespace(use_mock=True),
        client=client,
        account_number="12345678",
        account_product_code="01",
    )
    monkeypatch.setattr(trading_commands, "_build_runtime_context", lambda: runtime)

    monkeypatch.setattr(
        trading_commands,
        "inquire_current_price",
        lambda **_: {"rt_cd": "0", "output": {"stck_prpr": "70000"}},
    )
    monkeypatch.setattr(
        trading_commands,
        "inquire_balance",
        lambda **_: {
            "tr_id": "VTTC8434R",
            "url_path": "/uapi/domestic-stock/v1/trading/inquire-balance",
            "params": {"CANO": "12345678", "ACNT_PRDT_CD": "01"},
        },
    )

    result = runner.invoke(build_app(), ["smoke"])

    assert result.exit_code == 1
    assert "OPSQ2000" in result.stdout
    assert "KIS_MOCK_ACCOUNT_NUMBER" in result.stdout
