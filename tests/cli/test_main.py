"""
CLI Tests

Tests for stock-manager CLI commands.
Implements SPEC-CLI-001-008: CLI Tests.
"""

import os
import subprocess
import sys
from pathlib import Path


class TestCLICommands:
    """Test CLI command structure and invocation"""

    @property
    def project_root(self):
        """Get project root directory"""
        return Path(__file__).parent.parent.parent

    @property
    def env(self):
        """Environment with PYTHONPATH set"""
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.project_root / "src")
        return env

    def test_worker_start_help(self):
        """Test worker-start command shows help"""
        result = subprocess.run(
            [sys.executable, "-m", "stock_manager.main", "worker-start", "--help"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            env=self.env,
        )
        assert result.returncode == 0
        assert "worker_id" in result.stdout.lower()
        assert "log-level" in result.stdout.lower()

    def test_health_help(self):
        """Test health command shows help"""
        result = subprocess.run(
            [sys.executable, "-m", "stock_manager.main", "health", "--help"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            env=self.env,
        )
        assert result.returncode == 0
        assert "verbose" in result.stdout.lower()

    def test_main_help(self):
        """Test main CLI shows help"""
        result = subprocess.run(
            [sys.executable, "-m", "stock_manager.main", "--help"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            env=self.env,
        )
        assert result.returncode == 0
        assert "worker-start" in result.stdout
        assert "health" in result.stdout


class TestCLICharacterization:
    """Characterization tests for CLI behavior (PRESERVE phase)"""

    @property
    def project_root(self):
        """Get project root directory"""
        return Path(__file__).parent.parent.parent

    @property
    def env(self):
        """Environment with PYTHONPATH set"""
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.project_root / "src")
        return env

    def test_worker_start_missing_worker_id(self):
        """Characterize worker-start behavior when worker-id is missing"""
        result = subprocess.run(
            [sys.executable, "-m", "stock_manager.main", "worker-start"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            env=self.env,
        )
        # Current behavior: returns non-zero exit code
        assert result.returncode != 0

    def test_health_verbose_flag(self):
        """Characterize health command with verbose flag"""
        result = subprocess.run(
            [sys.executable, "-m", "stock_manager.main", "health", "--verbose"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            env=self.env,
        )
        # Current behavior: runs health check
        # (Will fail without database, but CLI structure is tested)
        assert "Configuration" in result.stdout or "Database" in result.stdout or "Broker" in result.stdout
