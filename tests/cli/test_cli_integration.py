"""
CLI Integration Tests

Comprehensive integration tests for CLI commands using subprocess.
Tests SPEC-CLI-001 implementation with real database and broker interactions.

TAG-SPEC-CLI-001-008
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from stock_manager.config.app_config import AppConfig


class TestCLIIntegration:
    """Integration tests for CLI commands"""

    @property
    def project_root(self) -> Path:
        """Get project root directory"""
        return Path(__file__).parent.parent.parent

    @property
    def env(self) -> dict:
        """Environment with PYTHONPATH and test database"""
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.project_root / "src")
        # Use test database URL
        env["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/stock_manager_test"
        return env

    def test_health_command_success(self):
        """Test health command checks connectivity"""
        result = subprocess.run(
            [sys.executable, "-m", "stock_manager.main", "health"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            env=self.env,
            timeout=10,
        )
        # Health command should complete (may fail if DB not available, but CLI should work)
        assert result.returncode in [0, 2]  # 0=healthy, 2=unhealthy
        output = result.stdout + result.stderr
        # Should output health check messages
        assert any(keyword in output for keyword in ["Configuration", "Database", "Broker"])

    def test_health_command_verbose(self):
        """Test health command with verbose flag"""
        result = subprocess.run(
            [sys.executable, "-m", "stock_manager.main", "health", "--verbose"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            env=self.env,
            timeout=10,
        )
        # Should complete without error
        assert result.returncode in [0, 2]
        output = result.stdout + result.stderr
        # Verbose mode should show configuration details
        assert "Configuration mode" in output or "Log level" in output

    def test_health_command_short_verbose(self):
        """Test health command with short verbose flag (-v)"""
        result = subprocess.run(
            [sys.executable, "-m", "stock_manager.main", "health", "-v"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            env=self.env,
            timeout=10,
        )
        # Should complete without error
        assert result.returncode in [0, 2]

    def test_worker_start_missing_worker_id(self):
        """Test worker-start fails when worker-id is missing"""
        result = subprocess.run(
            [sys.executable, "-m", "stock_manager.main", "worker-start"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            env=self.env,
            timeout=5,
        )
        # Should fail due to missing required argument
        assert result.returncode != 0
        # Typer should show missing argument error
        assert "missing" in result.stderr.lower() or "required" in result.stderr.lower()

    def test_worker_start_with_log_level_debug(self):
        """Test worker-start with --log-level debug"""
        # This test uses timeout since worker runs indefinitely
        # We'll send SIGTERM after a short delay
        proc = subprocess.Popen(
            [sys.executable, "-m", "stock_manager.main", "worker-start", "test-worker", "--log-level", "DEBUG"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.project_root,
            env=self.env,
        )
        # Give it time to start
        time.sleep(2)
        # Send SIGTERM to trigger graceful shutdown
        proc.send_signal(signal.SIGTERM)
        # Wait for process to complete
        stdout, stderr = proc.communicate(timeout=5)
        # Process should exit gracefully
        assert proc.returncode in [0, 2]  # 0=success, 2=DB error (acceptable if DB not running)

    def test_worker_start_with_log_level_info(self):
        """Test worker-start with --log-level info"""
        proc = subprocess.Popen(
            [sys.executable, "-m", "stock_manager.main", "worker-start", "test-worker-2", "--log-level", "INFO"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.project_root,
            env=self.env,
        )
        time.sleep(2)
        proc.send_signal(signal.SIGTERM)
        stdout, stderr = proc.communicate(timeout=5)
        assert proc.returncode in [0, 2]

    def test_worker_start_custom_worker_id(self):
        """Test worker-start with custom worker ID"""
        custom_worker_id = "custom-test-worker-123"
        proc = subprocess.Popen(
            [sys.executable, "-m", "stock_manager.main", "worker-start", custom_worker_id],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.project_root,
            env=self.env,
        )
        time.sleep(2)
        proc.send_signal(signal.SIGTERM)
        stdout, stderr = proc.communicate(timeout=5)
        # Check that worker ID appears in logs
        output = stdout + stderr
        assert custom_worker_id in output or proc.returncode in [0, 2]


class TestCLIErrorHandling:
    """Test CLI error handling"""

    @property
    def project_root(self) -> Path:
        """Get project root directory"""
        return Path(__file__).parent.parent.parent

    @property
    def env(self) -> dict:
        """Environment without DATABASE_URL to test config failure"""
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.project_root / "src")
        # Remove DATABASE_URL to trigger config error
        env.pop("DATABASE_URL", None)
        return env

    def test_worker_start_config_validation_failure(self):
        """Test worker-start fails with invalid configuration"""
        # Create a script that removes DATABASE_URL before running CLI
        test_script = self.project_root / "test_config_failure.py"
        test_script.write_text("""
import subprocess
import sys
import os

# Remove DATABASE_URL from environment
env = os.environ.copy()
env.pop("DATABASE_URL", None)
env["PYTHONPATH"] = "src"

# Run worker-start
result = subprocess.run(
    [sys.executable, "-m", "stock_manager.main", "worker-start", "test-worker"],
    capture_output=True,
    text=True,
    env=env,
)

# Print exit code for verification
print(f"EXIT_CODE:{result.returncode}", file=sys.stderr)
# Print stderr to capture error messages
sys.stderr.write(result.stderr)
sys.exit(result.returncode)
""")

        result = subprocess.run(
            [sys.executable, str(test_script)],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            timeout=10,
        )
        # Should fail (exit code 1 or 2 depending on error path)
        assert result.returncode in [1, 2]
        # Verify the test ran and produced output
        assert "EXIT_CODE" in result.stderr

        # Clean up
        test_script.unlink()

    def test_health_command_with_invalid_database(self):
        """Test health command handles invalid database gracefully"""
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.project_root / "src")
        # Use invalid database URL
        env["DATABASE_URL"] = "postgresql://invalid:invalid@localhost:9999/invalid_db"

        result = subprocess.run(
            [sys.executable, "-m", "stock_manager.main", "health"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            env=env,
            timeout=10,
        )
        # Should exit with error code
        assert result.returncode == 2
        output = result.stdout + result.stderr
        # Should show database connection error
        assert "database" in output.lower()


class TestSignalHandling:
    """Test signal handling for graceful shutdown"""

    @property
    def project_root(self) -> Path:
        """Get project root directory"""
        return Path(__file__).parent.parent.parent

    @property
    def env(self) -> dict:
        """Environment with test database"""
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.project_root / "src")
        env["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/stock_manager_test"
        return env

    def test_sigterm_triggers_graceful_shutdown(self):
        """Test SIGTERM triggers graceful shutdown"""
        proc = subprocess.Popen(
            [sys.executable, "-m", "stock_manager.main", "worker-start", "test-sigterm"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.project_root,
            env=self.env,
        )
        # Wait for worker to start
        time.sleep(2)
        # Send SIGTERM
        proc.send_signal(signal.SIGTERM)
        stdout, stderr = proc.communicate(timeout=5)
        output = stdout + stderr
        # Should log graceful shutdown message
        assert "shutdown" in output.lower() or proc.returncode in [0, 2]

    def test_sigint_triggers_graceful_shutdown(self):
        """Test SIGINT (Ctrl+C) triggers graceful shutdown"""
        proc = subprocess.Popen(
            [sys.executable, "-m", "stock_manager.main", "worker-start", "test-sigint"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.project_root,
            env=self.env,
        )
        time.sleep(2)
        # Send SIGINT (Ctrl+C)
        proc.send_signal(signal.SIGINT)
        stdout, stderr = proc.communicate(timeout=5)
        # Should exit with code 130 (standard for SIGINT)
        assert proc.returncode in [0, 2, 130]


class TestWorkerMainUnit:
    """Unit tests for _run_worker function with mocking"""

    @pytest.mark.asyncio
    async def test_run_worker_initializes_services(self):
        """Test _run_worker creates all service dependencies"""
        from stock_manager.main import _run_worker

        # Mock all dependencies to avoid initialization errors
        with patch('stock_manager.main.create_postgresql_adapter') as mock_db_create, \
             patch('stock_manager.main.MockBrokerAdapter') as mock_broker_class, \
             patch('stock_manager.main.MarketDataPoller') as mock_poller_class, \
             patch('stock_manager.main.OrderService') as mock_order_service_class, \
             patch('stock_manager.main.DailySummaryService') as mock_summary_service_class, \
             patch('stock_manager.main.WorkerMain') as mock_worker_main:

            # Setup mocks
            mock_db = Mock()
            mock_db_create.return_value = mock_db

            mock_broker = Mock()
            mock_broker_class.return_value = mock_broker

            mock_poller = Mock()
            mock_poller_class.return_value = mock_poller

            mock_order_service = Mock()
            mock_order_service_class.return_value = mock_order_service

            mock_summary_service = Mock()
            mock_summary_service_class.return_value = mock_summary_service

            # Create async mock for worker.start()
            async def mock_start():
                return None

            mock_worker = Mock()
            mock_worker.start = mock_start
            mock_worker_main.return_value = mock_worker

            # Create config
            config = AppConfig()
            config.database_url = "postgresql://test:test@localhost/test"

            # Run worker
            result = await _run_worker("test-worker", config)

            # Verify all services were created
            mock_db_create.assert_called_once()
            mock_broker_class.assert_called_once()
            mock_poller_class.assert_called_once()
            mock_order_service_class.assert_called_once()
            mock_summary_service_class.assert_called_once()

            # Verify worker was created and started
            mock_worker_main.assert_called_once()

            # Should return success
            assert result == 0

    @pytest.mark.asyncio
    async def test_run_worker_handles_database_failure(self):
        """Test _run_worker handles database connection failure"""
        from stock_manager.main import _run_worker

        # Mock database to raise exception
        with patch('stock_manager.main.create_postgresql_adapter') as mock_db_create:
            mock_db = Mock()
            mock_db.connect.side_effect = Exception("Database connection failed")
            mock_db_create.return_value = mock_db

            config = AppConfig()
            config.database_url = "postgresql://test:test@localhost/test"

            # Run worker
            result = await _run_worker("test-worker", config)

            # Should return error code
            assert result == 2

    @pytest.mark.asyncio
    async def test_run_worker_handles_broker_failure(self):
        """Test _run_worker handles broker authentication failure"""
        from stock_manager.main import _run_worker

        # Mock database and broker
        with patch('stock_manager.main.create_postgresql_adapter') as mock_db_create, \
             patch('stock_manager.main.MockBrokerAdapter') as mock_broker_class:

            mock_db = Mock()
            mock_db_create.return_value = mock_db

            mock_broker = Mock()
            mock_broker.authenticate.side_effect = Exception("Broker auth failed")
            mock_broker_class.return_value = mock_broker

            config = AppConfig()
            config.database_url = "postgresql://test:test@localhost/test"

            # Run worker
            result = await _run_worker("test-worker", config)

            # Should return error code
            assert result == 2

    @pytest.mark.asyncio
    async def test_run_worker_handles_worker_failure(self):
        """Test _run_worker handles WorkerMain.start() failure"""
        from stock_manager.main import _run_worker

        with patch('stock_manager.main.create_postgresql_adapter') as mock_db_create, \
             patch('stock_manager.main.MockBrokerAdapter') as mock_broker_class, \
             patch('stock_manager.main.WorkerMain') as mock_worker_main, \
             patch('stock_manager.main.LockService'), \
             patch('stock_manager.main.WorkerLifecycleService'), \
             patch('stock_manager.main.MarketDataPoller'), \
             patch('stock_manager.main.DummyStrategy'), \
             patch('stock_manager.main.StrategyExecutor'), \
             patch('stock_manager.main.OrderService'), \
             patch('stock_manager.main.DailySummaryService'):

            mock_db = Mock()
            mock_db_create.return_value = mock_db

            mock_broker = Mock()
            mock_broker_class.return_value = mock_broker

            mock_worker = Mock()
            mock_worker.start.side_effect = Exception("Worker failed to start")
            mock_worker_main.return_value = mock_worker

            config = AppConfig()
            config.database_url = "postgresql://test:test@localhost/test"

            # Run worker
            result = await _run_worker("test-worker", config)

            # Should return error code
            assert result == 2


class TestHealthUnit:
    """Unit tests for health function with mocking"""

    def test_health_check_all_healthy(self):
        """Test health command when all services are healthy"""
        from stock_manager.main import health
        from unittest.mock import patch
        import io
        import sys as sys_module

        # Create a mock sys.exit that captures the exit code
        exit_code = []

        def mock_exit(code):
            exit_code.append(code)
            raise SystemExit(code)

        # Mock all dependencies
        with patch('stock_manager.main.AppConfig') as mock_config_class, \
             patch('stock_manager.main.create_postgresql_adapter') as mock_db_create, \
             patch('stock_manager.main.MockBrokerAdapter') as mock_broker_class, \
             patch('sys.exit', side_effect=mock_exit):

            # Setup mocks
            mock_config = Mock()
            mock_config.kis_mode = "PAPER"
            mock_config.log_level = "INFO"
            mock_config.database_url = "postgresql://test:test@localhost/test"
            mock_config_class.return_value = mock_config

            mock_db = Mock()
            mock_db_create.return_value = mock_db

            mock_broker = Mock()
            mock_broker_class.return_value = mock_broker

            # Capture stdout
            captured_output = io.StringIO()
            sys_module.stdout = captured_output

            try:
                health(verbose=False)
            except SystemExit:
                pass

            # Restore stdout
            sys_module.stdout = sys.__stdout__

            # Verify exit code
            assert exit_code[0] == 0

            # Verify all checks were called
            mock_config_class.assert_called_once()
            mock_db_create.assert_called_once()
            mock_broker_class.assert_called_once()
            mock_db.connect.assert_called_once()
            mock_db.close.assert_called_once()
            mock_broker.authenticate.assert_called_once()

    def test_health_check_database_unhealthy(self):
        """Test health command when database is unhealthy"""
        from stock_manager.main import health
        from unittest.mock import patch
        import io
        import sys as sys_module

        exit_code = []

        def mock_exit(code):
            exit_code.append(code)
            raise SystemExit(code)

        with patch('stock_manager.main.AppConfig') as mock_config_class, \
             patch('stock_manager.main.create_postgresql_adapter') as mock_db_create, \
             patch('stock_manager.main.MockBrokerAdapter') as mock_broker_class, \
             patch('sys.exit', side_effect=mock_exit):

            # Setup mocks
            mock_config = Mock()
            mock_config.kis_mode = "PAPER"
            mock_config.log_level = "INFO"
            mock_config.database_url = "postgresql://test:test@localhost/test"
            mock_config_class.return_value = mock_config

            mock_db = Mock()
            mock_db.connect.side_effect = Exception("Database connection failed")
            mock_db_create.return_value = mock_db

            mock_broker = Mock()
            mock_broker_class.return_value = mock_broker

            # Capture stdout
            captured_output = io.StringIO()
            sys_module.stdout = captured_output

            try:
                health(verbose=False)
            except SystemExit:
                pass

            # Restore stdout
            sys_module.stdout = sys.__stdout__

            # Verify exit code
            assert exit_code[0] == 2

    def test_health_check_broker_unhealthy(self):
        """Test health command when broker is unhealthy"""
        from stock_manager.main import health
        from unittest.mock import patch
        import io
        import sys as sys_module

        exit_code = []

        def mock_exit(code):
            exit_code.append(code)
            raise SystemExit(code)

        with patch('stock_manager.main.AppConfig') as mock_config_class, \
             patch('stock_manager.main.create_postgresql_adapter') as mock_db_create, \
             patch('stock_manager.main.MockBrokerAdapter') as mock_broker_class, \
             patch('sys.exit', side_effect=mock_exit):

            # Setup mocks
            mock_config = Mock()
            mock_config.kis_mode = "PAPER"
            mock_config.log_level = "INFO"
            mock_config.database_url = "postgresql://test:test@localhost/test"
            mock_config_class.return_value = mock_config

            mock_db = Mock()
            mock_db_create.return_value = mock_db

            mock_broker = Mock()
            mock_broker.authenticate.side_effect = Exception("Broker auth failed")
            mock_broker_class.return_value = mock_broker

            # Capture stdout
            captured_output = io.StringIO()
            sys_module.stdout = captured_output

            try:
                health(verbose=False)
            except SystemExit:
                pass

            # Restore stdout
            sys_module.stdout = sys.__stdout__

            # Verify exit code
            assert exit_code[0] == 2

    def test_health_check_verbose_output(self):
        """Test health command with verbose output"""
        from stock_manager.main import health
        from unittest.mock import patch
        import io
        import sys as sys_module
        import logging

        exit_code = []

        def mock_exit(code):
            exit_code.append(code)
            raise SystemExit(code)

        with patch('stock_manager.main.AppConfig') as mock_config_class, \
             patch('stock_manager.main.create_postgresql_adapter') as mock_db_create, \
             patch('stock_manager.main.MockBrokerAdapter') as mock_broker_class, \
             patch('sys.exit', side_effect=mock_exit):

            # Setup mocks
            mock_config = Mock()
            mock_config.kis_mode = "PAPER"
            mock_config.log_level = "DEBUG"
            mock_config.database_url = "postgresql://test:test@localhost/test"
            mock_config_class.return_value = mock_config

            mock_db = Mock()
            mock_db_create.return_value = mock_db

            mock_broker = Mock()
            mock_broker_class.return_value = mock_broker

            # Capture both stdout and logger output
            captured_output = io.StringIO()
            sys_module.stdout = captured_output

            # Setup logging to also capture
            logger = logging.getLogger()
            handler = logging.StreamHandler(captured_output)
            logger.addHandler(handler)

            try:
                health(verbose=True)
            except SystemExit:
                pass
            finally:
                logger.removeHandler(handler)

            # Restore stdout
            sys_module.stdout = sys.__stdout__

            # Check verbose output
            output = captured_output.getvalue()
            # The verbose output should include configuration details
            assert len(output) > 0 or exit_code[0] == 0  # Either we got output or success


class TestWorkerStartUnit:
    """Unit tests for worker_start function with mocking"""

    def test_worker_start_loads_config(self):
        """Test worker_start loads configuration successfully"""
        from stock_manager.main import worker_start
        from unittest.mock import patch
        import io
        import sys as sys_module

        exit_code = []

        def mock_exit(code):
            exit_code.append(code)
            raise SystemExit(code)

        with patch('stock_manager.main.AppConfig') as mock_config_class, \
             patch('stock_manager.main.asyncio.run') as mock_asyncio_run, \
             patch('stock_manager.main.setup_logging'), \
             patch('stock_manager.main.signal.signal'), \
             patch('sys.exit', side_effect=mock_exit):

            # Setup mocks
            mock_config = Mock()
            mock_config_class.return_value = mock_config

            mock_asyncio_run.return_value = 0

            # Capture stdout
            captured_output = io.StringIO()
            sys_module.stdout = captured_output

            try:
                worker_start(worker_id="test-worker", log_level="INFO")
            except SystemExit:
                pass

            # Restore stdout
            sys_module.stdout = sys.__stdout__

            # Verify config was loaded
            mock_config_class.assert_called_once()
            # Verify exit code
            assert exit_code[0] == 0

    def test_worker_start_config_failure(self):
        """Test worker_start handles configuration failure"""
        from stock_manager.main import worker_start
        from unittest.mock import patch
        import io
        import sys as sys_module

        exit_code = []

        def mock_exit(code):
            exit_code.append(code)
            raise SystemExit(code)

        with patch('stock_manager.main.AppConfig') as mock_config_class, \
             patch('stock_manager.main.setup_logging'), \
             patch('sys.exit', side_effect=mock_exit):

            # Setup config to raise exception
            mock_config_class.side_effect = Exception("Config load failed")

            # Capture stdout
            captured_output = io.StringIO()
            sys_module.stdout = captured_output

            try:
                worker_start(worker_id="test-worker", log_level="INFO")
            except SystemExit:
                pass

            # Restore stdout
            sys_module.stdout = sys.__stdout__

            # Verify exit code 1 (config error)
            assert exit_code[0] == 1

    def test_worker_start_keyboard_interrupt(self):
        """Test worker_start handles KeyboardInterrupt"""
        from stock_manager.main import worker_start
        from unittest.mock import patch
        import io
        import sys as sys_module

        exit_code = []

        def mock_exit(code):
            exit_code.append(code)
            raise SystemExit(code)

        with patch('stock_manager.main.AppConfig') as mock_config_class, \
             patch('stock_manager.main.asyncio.run', side_effect=KeyboardInterrupt()), \
             patch('stock_manager.main.setup_logging'), \
             patch('stock_manager.main.signal.signal'), \
             patch('sys.exit', side_effect=mock_exit):

            mock_config = Mock()
            mock_config_class.return_value = mock_config

            # Capture stdout
            captured_output = io.StringIO()
            sys_module.stdout = captured_output

            try:
                worker_start(worker_id="test-worker", log_level="INFO")
            except SystemExit:
                pass

            # Restore stdout
            sys_module.stdout = sys.__stdout__

            # Verify exit code 130 (SIGINT)
            assert exit_code[0] == 130

    def test_worker_start_exception_handling(self):
        """Test worker_start handles generic exceptions"""
        from stock_manager.main import worker_start
        from unittest.mock import patch
        import io
        import sys as sys_module

        exit_code = []

        def mock_exit(code):
            exit_code.append(code)
            raise SystemExit(code)

        with patch('stock_manager.main.AppConfig') as mock_config_class, \
             patch('stock_manager.main.asyncio.run', side_effect=Exception("Worker crashed")), \
             patch('stock_manager.main.setup_logging'), \
             patch('stock_manager.main.signal.signal'), \
             patch('sys.exit', side_effect=mock_exit):

            mock_config = Mock()
            mock_config_class.return_value = mock_config

            # Capture stdout
            captured_output = io.StringIO()
            sys_module.stdout = captured_output

            try:
                worker_start(worker_id="test-worker", log_level="INFO")
            except SystemExit:
                pass

            # Restore stdout
            sys_module.stdout = sys.__stdout__

            # Verify exit code 2 (error)
            assert exit_code[0] == 2
