"""
Stock Manager CLI

Command-line interface for worker management and health checks.
Implements SPEC-CLI-001: CLI Worker Entrypoints.
"""

import asyncio
import logging
import signal
import sys

# TAG-SPEC-CLI-001-001
import typer
from rich.logging import RichHandler

from stock_manager.config.app_config import AppConfig
from stock_manager.service_layer.worker_main import WorkerMain
from stock_manager.service_layer.lock_service import LockService
from stock_manager.service_layer.worker_lifecycle_service import WorkerLifecycleService
from stock_manager.service_layer.market_data_poller import MarketDataPoller
from stock_manager.service_layer.strategy_executor import StrategyExecutor
from stock_manager.service_layer.dummy_strategy import DummyStrategy
from stock_manager.service_layer.order_service import OrderService
from stock_manager.service_layer.daily_summary_service import DailySummaryService
from stock_manager.adapters.broker.mock import MockBrokerAdapter
from stock_manager.adapters.storage.postgresql_adapter import create_postgresql_adapter

# CLI app
app = typer.Typer(
    name="stock-manager",
    help="Stock Manager - Automated trading bot CLI",
    add_completion=False,
)

# Global shutdown flag for signal handling
# TAG-SPEC-CLI-001-003
_shutdown_requested = False


def setup_logging(log_level: str = "INFO") -> None:
    """Setup logging with RichHandler for colored output

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # TAG-SPEC-CLI-001-002
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )


def signal_handler(signum: int, frame) -> None:
    """Handle shutdown signals (SIGTERM, SIGINT)

    Sets global flag to trigger graceful shutdown.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    global _shutdown_requested
    _shutdown_requested = True
    logging.info(f"Received signal {signum}, initiating graceful shutdown...")


async def _run_worker(worker_id: str, config: AppConfig) -> int:
    """Run worker async orchestrator

    Bridge function to execute async WorkerMain from sync CLI context.

    Args:
        worker_id: Worker instance ID
        config: Application configuration

    Returns:
        int: Exit code (0=success, 2=infrastructure error)
    """
    try:
        # TAG-SPEC-CLI-001-010
        # Initialize database connection
        db_adapter = create_postgresql_adapter(
            database_url=config.database_url,
        )
        db_adapter.connect()

        # Initialize broker adapter
        broker_adapter = MockBrokerAdapter()
        broker_adapter.authenticate()

        # Initialize all services
        lock_service = LockService(db_adapter)
        worker_lifecycle = WorkerLifecycleService(db_adapter)

        # Initialize market data poller (placeholder - needs real implementation)
        market_data_poller = MarketDataPoller(
            broker_adapter=broker_adapter,
            db_adapter=db_adapter,
        )

        # Initialize strategy executor with dummy strategy for PoC
        strategy = DummyStrategy()
        strategy_executor = StrategyExecutor(strategy=strategy)

        # Initialize order service
        order_service = OrderService(
            broker=broker_adapter,
            db=db_adapter,
            config=config,
        )

        # Initialize daily summary service
        daily_summary_service = DailySummaryService(db_adapter)

        # Create and start WorkerMain
        worker = WorkerMain(
            worker_id=worker_id,
            lock_service=lock_service,
            worker_lifecycle=worker_lifecycle,
            market_data_poller=market_data_poller,
            strategy_executor=strategy_executor,
            order_service=order_service,
            daily_summary_service=daily_summary_service,
        )

        # Start worker event loop
        await worker.start()

        return 0

    except Exception as e:
        logging.error(f"Worker failed: {e}", exc_info=True)
        return 2


@app.command()
def worker_start(
    worker_id: str = typer.Argument(..., help="Worker instance ID"),
    log_level: str = typer.Option("INFO", help="Log level"),
) -> None:
    """Start worker process

    Implements SPEC-CLI-001: worker_start command with signal handling.

    Args:
        worker_id: Worker instance ID
        log_level: Log level (default: INFO)
    """
    # TAG-SPEC-CLI-001-004
    global _shutdown_requested

    # Setup logging
    setup_logging(log_level)
    logger = logging.getLogger(__name__)

    # Load configuration
    try:
        config = AppConfig()
        logger.info(f"Loaded configuration for worker: {worker_id}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        # TAG-SPEC-CLI-001-009
        sys.exit(1)

    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Run worker async loop
    # TAG-SPEC-CLI-001-005
    try:
        exit_code = asyncio.run(_run_worker(worker_id, config))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        logger.error(f"Worker crashed: {e}", exc_info=True)
        sys.exit(2)


@app.command()
def health(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Check system health

    Tests connectivity to database and broker services.

    Args:
        verbose: Enable verbose output
    """
    # TAG-SPEC-CLI-001-006
    setup_logging("INFO")
    logger = logging.getLogger(__name__)

    all_healthy = True

    # Load configuration
    try:
        config = AppConfig()
        logger.info("✅ Configuration loaded")
    except Exception as e:
        logger.error(f"❌ Configuration failed: {e}")
        all_healthy = False

    # Check database connectivity
    try:
        db_adapter = create_postgresql_adapter(
            database_url=config.database_url,
        )
        db_adapter.connect()
        logger.info("✅ Database connection successful")
        db_adapter.close()
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        all_healthy = False

    # Check broker connectivity
    try:
        broker_adapter = MockBrokerAdapter()
        broker_adapter.authenticate()
        logger.info("✅ Broker connection successful")
    except Exception as e:
        logger.error(f"❌ Broker connection failed: {e}")
        all_healthy = False

    if verbose:
        logger.info(f"Configuration mode: {config.kis_mode}")
        logger.info(f"Log level: {config.log_level}")

    # Exit with appropriate code
    sys.exit(0 if all_healthy else 2)


def main() -> None:
    """Main entry point for CLI"""
    app()


if __name__ == "__main__":
    main()
