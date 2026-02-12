from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

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
