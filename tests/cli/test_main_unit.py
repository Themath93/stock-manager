"""
CLI Unit Tests

Unit tests for main.py functions that can be tested directly.
Implements SPEC-CLI-001-008: CLI Tests.
"""


from stock_manager.main import setup_logging, signal_handler


class TestSetupLogging:
    """Test logging setup functionality"""

    def test_setup_logging_info(self):
        """Test setup_logging with INFO level doesn't raise errors"""
        # Should not raise any exceptions
        setup_logging("INFO")

    def test_setup_logging_debug(self):
        """Test setup_logging with DEBUG level doesn't raise errors"""
        # Should not raise any exceptions
        setup_logging("DEBUG")

    def test_setup_logging_warning(self):
        """Test setup_logging with WARNING level doesn't raise errors"""
        # Should not raise any exceptions
        setup_logging("WARNING")


class TestSignalHandler:
    """Test signal handling functionality"""

    def test_signal_handler_sets_shutdown_flag(self):
        """Test that signal handler sets global shutdown flag"""
        import stock_manager.main as main_module

        # Reset flag
        main_module._shutdown_requested = False

        # Call signal handler
        signal_handler(15, None)  # SIGTERM

        # Check flag is set
        assert main_module._shutdown_requested is True

    def test_signal_handler_sigterm(self):
        """Test SIGTERM signal handling"""
        import stock_manager.main as main_module

        main_module._shutdown_requested = False
        signal_handler(15, None)  # SIGTERM
        assert main_module._shutdown_requested is True

    def test_signal_handler_sigint(self):
        """Test SIGINT signal handling"""
        import stock_manager.main as main_module

        main_module._shutdown_requested = False
        signal_handler(2, None)  # SIGINT
        assert main_module._shutdown_requested is True


class TestCLIImports:
    """Test that CLI imports work correctly"""

    def test_main_imports(self):
        """Test that main module can be imported"""
        import stock_manager.main

        assert hasattr(stock_manager.main, "app")
        assert hasattr(stock_manager.main, "worker_start")
        assert hasattr(stock_manager.main, "health")
        assert hasattr(stock_manager.main, "main")

    def test_typer_app_exists(self):
        """Test that Typer app is configured"""
        from stock_manager.main import app

        assert app is not None
        assert app.info.name == "stock-manager"


# Import signal handler for tests
