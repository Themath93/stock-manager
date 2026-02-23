"""Unit tests for PipelineJsonLogger NDJSON pipeline event logger."""

import json
import threading
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch


from stock_manager.trading.logging.pipeline_logger import PipelineJsonLogger


def _read_lines(path: Path) -> list[dict]:
    """Read all NDJSON lines from a file as parsed dicts."""
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _get_log_file(log_dir: Path, prefix: str = "pipeline") -> Path:
    """Return the daily log file path from log_dir."""
    from datetime import datetime
    today = datetime.now().strftime("%Y%m%d")
    return log_dir / f"{prefix}-{today}.ndjson"


class TestPipelineLoggerInit:
    """Test logger initialisation."""

    def test_creates_log_dir_if_missing(self, tmp_path):
        """Log directory is created automatically when it does not exist."""
        log_dir = tmp_path / "nested" / "pipeline"
        PipelineJsonLogger(log_dir)
        assert log_dir.is_dir()

    def test_default_prefix_is_pipeline(self, tmp_path):
        """Default prefix results in pipeline-YYYYMMDD.ndjson filenames."""
        logger = PipelineJsonLogger(tmp_path)
        logger.log_state_change("005930", "IDLE", "SCREENING", "start")
        log_file = _get_log_file(tmp_path, "pipeline")
        assert log_file.exists()

    def test_custom_prefix_used_in_filename(self, tmp_path):
        """Custom prefix is reflected in the log filename."""
        logger = PipelineJsonLogger(tmp_path, prefix="trading")
        logger.log_state_change("005930", "IDLE", "SCREENING", "start")
        log_file = _get_log_file(tmp_path, "trading")
        assert log_file.exists()

    def test_accepts_path_object(self, tmp_path):
        """Constructor accepts a Path object for log_dir."""
        logger = PipelineJsonLogger(Path(tmp_path))
        logger.log_state_change("005930", "IDLE", "SCREENING", "start")
        assert _get_log_file(tmp_path).exists()


class TestNdjsonFormat:
    """Test that output is valid NDJSON (one JSON object per line)."""

    def test_each_line_is_valid_json(self, tmp_path):
        """Every written line must parse as valid JSON."""
        logger = PipelineJsonLogger(tmp_path)
        logger.log_state_change("005930", "IDLE", "SCREENING", "start")
        logger.log_state_change("000660", "SCREENING", "CONSENSUS", "screened")

        log_file = _get_log_file(tmp_path)
        raw_lines = log_file.read_text(encoding="utf-8").strip().splitlines()
        for line in raw_lines:
            parsed = json.loads(line)  # raises if invalid
            assert isinstance(parsed, dict)

    def test_each_record_has_timestamp(self, tmp_path):
        """Every record must include an ISO-format timestamp."""
        logger = PipelineJsonLogger(tmp_path)
        logger.log_state_change("005930", "IDLE", "SCREENING", "start")

        records = _read_lines(_get_log_file(tmp_path))
        assert "timestamp" in records[0]
        # Basic ISO format check
        assert "T" in records[0]["timestamp"]

    def test_each_record_has_session_id(self, tmp_path):
        """Every record must include a session_id."""
        logger = PipelineJsonLogger(tmp_path)
        logger.log_state_change("005930", "IDLE", "SCREENING", "start")

        records = _read_lines(_get_log_file(tmp_path))
        assert "session_id" in records[0]
        assert len(records[0]["session_id"]) > 0

    def test_multiple_events_append_separate_lines(self, tmp_path):
        """Multiple log calls append separate lines to the same file."""
        logger = PipelineJsonLogger(tmp_path)
        logger.log_state_change("005930", "IDLE", "SCREENING", "start")
        logger.log_state_change("005930", "SCREENING", "CONSENSUS", "done")

        records = _read_lines(_get_log_file(tmp_path))
        assert len(records) == 2


class TestLogStateChange:
    """Test log_state_change method."""

    def test_writes_state_change_event(self, tmp_path):
        """log_state_change writes a record with event='state_change'."""
        logger = PipelineJsonLogger(tmp_path)
        logger.log_state_change("005930", "IDLE", "SCREENING", "market open")

        records = _read_lines(_get_log_file(tmp_path))
        assert len(records) == 1
        r = records[0]
        assert r["event"] == "state_change"
        assert r["symbol"] == "005930"
        assert r["from_state"] == "IDLE"
        assert r["to_state"] == "SCREENING"
        assert r["reason"] == "market open"

    def test_state_change_fields_complete(self, tmp_path):
        """state_change record contains all required fields."""
        logger = PipelineJsonLogger(tmp_path)
        logger.log_state_change("000660", "CONSENSUS", "BUYING", "consensus passed")

        records = _read_lines(_get_log_file(tmp_path))
        r = records[0]
        required = {"event", "symbol", "from_state", "to_state", "reason", "timestamp", "session_id"}
        assert required.issubset(r.keys())


class TestLogScreeningComplete:
    """Test log_screening_complete method."""

    def test_writes_screening_complete_event(self, tmp_path):
        """log_screening_complete writes a record with event='screening_complete'."""
        logger = PipelineJsonLogger(tmp_path)
        summary = {"price": 70000, "volume": 1000000, "rsi": 55.2}
        logger.log_screening_complete("005930", summary)

        records = _read_lines(_get_log_file(tmp_path))
        assert len(records) == 1
        r = records[0]
        assert r["event"] == "screening_complete"
        assert r["symbol"] == "005930"
        assert r["snapshot_summary"] == summary

    def test_screening_complete_with_empty_summary(self, tmp_path):
        """log_screening_complete handles empty summary dict."""
        logger = PipelineJsonLogger(tmp_path)
        logger.log_screening_complete("005930", {})

        records = _read_lines(_get_log_file(tmp_path))
        assert records[0]["snapshot_summary"] == {}


class TestLogConsensusResult:
    """Test log_consensus_result method."""

    def test_writes_consensus_result_passed(self, tmp_path):
        """log_consensus_result writes passed=True case correctly."""
        logger = PipelineJsonLogger(tmp_path)
        categories = {"value": 2, "growth": 1}
        logger.log_consensus_result(
            symbol="005930",
            passed=True,
            buy_count=3,
            total_count=4,
            avg_conviction=0.82,
            categories=categories,
        )

        records = _read_lines(_get_log_file(tmp_path))
        r = records[0]
        assert r["event"] == "consensus_result"
        assert r["symbol"] == "005930"
        assert r["passed"] is True
        assert r["buy_count"] == 3
        assert r["total_count"] == 4
        assert abs(r["avg_conviction"] - 0.82) < 1e-9
        assert r["categories"] == categories

    def test_writes_consensus_result_failed(self, tmp_path):
        """log_consensus_result writes passed=False case correctly."""
        logger = PipelineJsonLogger(tmp_path)
        logger.log_consensus_result(
            symbol="000660",
            passed=False,
            buy_count=1,
            total_count=4,
            avg_conviction=0.35,
            categories={"value": 1},
        )

        records = _read_lines(_get_log_file(tmp_path))
        r = records[0]
        assert r["passed"] is False
        assert r["buy_count"] == 1

    def test_consensus_result_fields_complete(self, tmp_path):
        """consensus_result record contains all required fields."""
        logger = PipelineJsonLogger(tmp_path)
        logger.log_consensus_result("005930", True, 3, 4, 0.8, {})

        records = _read_lines(_get_log_file(tmp_path))
        required = {"event", "symbol", "passed", "buy_count", "total_count",
                    "avg_conviction", "categories", "timestamp", "session_id"}
        assert required.issubset(records[0].keys())


class TestLogBuyDecision:
    """Test log_buy_decision method."""

    def test_writes_buy_decision_event(self, tmp_path):
        """log_buy_decision writes a record with event='buy_decision'."""
        logger = PipelineJsonLogger(tmp_path)
        logger.log_buy_decision(
            symbol="005930",
            price=Decimal("70000"),
            quantity=10,
            order_type="LIMIT",
            stop_loss=Decimal("63000"),
        )

        records = _read_lines(_get_log_file(tmp_path))
        r = records[0]
        assert r["event"] == "buy_decision"
        assert r["symbol"] == "005930"
        assert r["quantity"] == 10
        assert r["order_type"] == "LIMIT"

    def test_buy_decision_serialises_decimal(self, tmp_path):
        """Decimal price and stop_loss are serialised to string in JSON."""
        logger = PipelineJsonLogger(tmp_path)
        logger.log_buy_decision("005930", Decimal("70000"), 5, "MARKET", Decimal("63000"))

        records = _read_lines(_get_log_file(tmp_path))
        r = records[0]
        # Decimal values serialised as strings via default=str
        assert str(Decimal("70000")) == r["price"]
        assert str(Decimal("63000")) == r["stop_loss"]

    def test_buy_decision_fields_complete(self, tmp_path):
        """buy_decision record contains all required fields."""
        logger = PipelineJsonLogger(tmp_path)
        logger.log_buy_decision("005930", Decimal("70000"), 10, "LIMIT", Decimal("63000"))

        records = _read_lines(_get_log_file(tmp_path))
        required = {"event", "symbol", "price", "quantity", "order_type", "stop_loss",
                    "timestamp", "session_id"}
        assert required.issubset(records[0].keys())


class TestLogSellTrigger:
    """Test log_sell_trigger method."""

    def test_writes_sell_trigger_event(self, tmp_path):
        """log_sell_trigger writes a record with event='sell_trigger'."""
        logger = PipelineJsonLogger(tmp_path)
        logger.log_sell_trigger(
            symbol="005930",
            trigger_reason="stop_loss",
            trigger_value=-0.07,
            current_pnl=Decimal("-5000"),
        )

        records = _read_lines(_get_log_file(tmp_path))
        r = records[0]
        assert r["event"] == "sell_trigger"
        assert r["symbol"] == "005930"
        assert r["trigger_reason"] == "stop_loss"
        assert abs(r["trigger_value"] - (-0.07)) < 1e-9

    def test_sell_trigger_serialises_decimal_pnl(self, tmp_path):
        """current_pnl Decimal is serialised correctly."""
        logger = PipelineJsonLogger(tmp_path)
        logger.log_sell_trigger("005930", "take_profit", 0.15, Decimal("12000"))

        records = _read_lines(_get_log_file(tmp_path))
        assert str(Decimal("12000")) == records[0]["current_pnl"]

    def test_sell_trigger_fields_complete(self, tmp_path):
        """sell_trigger record contains all required fields."""
        logger = PipelineJsonLogger(tmp_path)
        logger.log_sell_trigger("005930", "stop_loss", -0.07, Decimal("-5000"))

        records = _read_lines(_get_log_file(tmp_path))
        required = {"event", "symbol", "trigger_reason", "trigger_value", "current_pnl",
                    "timestamp", "session_id"}
        assert required.issubset(records[0].keys())


class TestLogTradeComplete:
    """Test log_trade_complete method."""

    def test_writes_trade_complete_event(self, tmp_path):
        """log_trade_complete writes a record with event='trade_complete'."""
        logger = PipelineJsonLogger(tmp_path)
        logger.log_trade_complete(
            symbol="005930",
            entry_price=Decimal("70000"),
            exit_price=Decimal("77000"),
            pnl=Decimal("70000"),
            holding_days=10,
            return_pct=10.0,
        )

        records = _read_lines(_get_log_file(tmp_path))
        r = records[0]
        assert r["event"] == "trade_complete"
        assert r["symbol"] == "005930"
        assert r["holding_days"] == 10
        assert abs(r["return_pct"] - 10.0) < 1e-9

    def test_trade_complete_serialises_decimal_prices(self, tmp_path):
        """entry_price, exit_price, and pnl Decimals are serialised."""
        logger = PipelineJsonLogger(tmp_path)
        logger.log_trade_complete(
            symbol="005930",
            entry_price=Decimal("70000"),
            exit_price=Decimal("77000"),
            pnl=Decimal("70000"),
            holding_days=10,
            return_pct=10.0,
        )

        records = _read_lines(_get_log_file(tmp_path))
        r = records[0]
        assert r["entry_price"] == str(Decimal("70000"))
        assert r["exit_price"] == str(Decimal("77000"))
        assert r["pnl"] == str(Decimal("70000"))

    def test_trade_complete_fields_complete(self, tmp_path):
        """trade_complete record contains all required fields."""
        logger = PipelineJsonLogger(tmp_path)
        logger.log_trade_complete("005930", Decimal("70000"), Decimal("77000"),
                                  Decimal("70000"), 10, 10.0)

        records = _read_lines(_get_log_file(tmp_path))
        required = {"event", "symbol", "entry_price", "exit_price", "pnl",
                    "holding_days", "return_pct", "timestamp", "session_id"}
        assert required.issubset(records[0].keys())


class TestLogError:
    """Test log_error method."""

    def test_writes_error_event(self, tmp_path):
        """log_error writes a record with event='error'."""
        logger = PipelineJsonLogger(tmp_path)
        error = ValueError("price fetch failed")
        logger.log_error("005930", error)

        records = _read_lines(_get_log_file(tmp_path))
        r = records[0]
        assert r["event"] == "error"
        assert r["symbol"] == "005930"
        assert r["error_type"] == "ValueError"
        assert r["error_message"] == "price fetch failed"

    def test_log_error_with_context(self, tmp_path):
        """log_error includes context dict when provided."""
        logger = PipelineJsonLogger(tmp_path)
        ctx = {"retry_count": 3, "endpoint": "/price"}
        logger.log_error("005930", RuntimeError("timeout"), context=ctx)

        records = _read_lines(_get_log_file(tmp_path))
        r = records[0]
        assert r["context"] == ctx

    def test_log_error_without_context_defaults_empty_dict(self, tmp_path):
        """log_error stores empty dict when no context provided."""
        logger = PipelineJsonLogger(tmp_path)
        logger.log_error("005930", KeyError("missing"))

        records = _read_lines(_get_log_file(tmp_path))
        assert records[0]["context"] == {}

    def test_log_error_captures_error_type_name(self, tmp_path):
        """error_type field is the exception class name, not module path."""
        logger = PipelineJsonLogger(tmp_path)

        class CustomTradingError(Exception):
            pass

        logger.log_error("005930", CustomTradingError("bad"))

        records = _read_lines(_get_log_file(tmp_path))
        assert records[0]["error_type"] == "CustomTradingError"

    def test_error_fields_complete(self, tmp_path):
        """error record contains all required fields."""
        logger = PipelineJsonLogger(tmp_path)
        logger.log_error("005930", Exception("oops"))

        records = _read_lines(_get_log_file(tmp_path))
        required = {"event", "symbol", "error_type", "error_message", "context",
                    "timestamp", "session_id"}
        assert required.issubset(records[0].keys())


class TestDailyRotation:
    """Test that log files rotate based on the current date."""

    def test_creates_new_file_when_date_changes(self, tmp_path):
        """When the date changes, writes go to a new NDJSON file."""
        logger = PipelineJsonLogger(tmp_path)

        # Write on "day 1"
        with patch("stock_manager.trading.logging.pipeline_logger.datetime") as mock_dt:
            mock_dt.now.return_value.isoformat.return_value = "2026-02-21T10:00:00"
            mock_dt.now.return_value.strftime.return_value = "20260221"
            logger.log_state_change("005930", "IDLE", "SCREENING", "day1")

        # Write on "day 2"
        with patch("stock_manager.trading.logging.pipeline_logger.datetime") as mock_dt:
            mock_dt.now.return_value.isoformat.return_value = "2026-02-22T10:00:00"
            mock_dt.now.return_value.strftime.return_value = "20260222"
            logger.log_state_change("005930", "IDLE", "SCREENING", "day2")

        file_day1 = tmp_path / "pipeline-20260221.ndjson"
        file_day2 = tmp_path / "pipeline-20260222.ndjson"
        assert file_day1.exists(), "Day 1 log file should exist"
        assert file_day2.exists(), "Day 2 log file should exist"

    def test_same_day_events_go_to_same_file(self, tmp_path):
        """Multiple events on the same day all append to the same file."""
        logger = PipelineJsonLogger(tmp_path)
        for i in range(5):
            logger.log_state_change("005930", "IDLE", f"STATE_{i}", f"reason_{i}")

        log_file = _get_log_file(tmp_path)
        records = _read_lines(log_file)
        assert len(records) == 5


class TestThreadSafety:
    """Test RLock-based thread safety."""

    def test_concurrent_writes_produce_valid_ndjson(self, tmp_path):
        """Concurrent writes from multiple threads all produce valid JSON lines."""
        logger = PipelineJsonLogger(tmp_path)
        errors: list[Exception] = []

        def write_events():
            try:
                for i in range(20):
                    logger.log_state_change("005930", "IDLE", "SCREENING", f"t{i}")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=write_events) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread errors: {errors}"

        log_file = _get_log_file(tmp_path)
        records = _read_lines(log_file)
        # 5 threads x 20 events each
        assert len(records) == 100

    def test_rlock_is_used(self, tmp_path):
        """Logger uses threading.RLock for thread safety."""
        logger = PipelineJsonLogger(tmp_path)
        assert isinstance(logger._lock, type(threading.RLock()))

    def test_same_thread_can_reenter_lock(self, tmp_path):
        """RLock allows re-entrant acquisition from the same thread (no deadlock)."""
        logger = PipelineJsonLogger(tmp_path)

        # Acquire the lock then call a log method — RLock must not deadlock
        with logger._lock:
            logger.log_state_change("005930", "IDLE", "SCREENING", "reentrant")

        records = _read_lines(_get_log_file(tmp_path))
        assert len(records) == 1
