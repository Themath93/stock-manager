# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- SPEC-CLI-001: CLI Worker Entrypoints Implementation (2026-01-29)
  - Typer-based CLI framework with `worker-start` and `health` commands
  - Graceful shutdown with SIGTERM/SIGINT signal handling
  - Async-to-sync bridge using `asyncio.run()`
  - Structured logging with RichHandler
  - Environment variable validation (AppConfig, Database, Broker)
  - 94.90% test coverage with 36 CLI tests passing
  - Exit codes: 0=success, 1=config error, 2=infrastructure error, 130=SIGINT

### Fixed
- Replace deprecated `datetime.utcnow()` with `datetime.now(timezone.utc)` throughout codebase

### Changed
- Updated AppConfig to include `database_url` field
- Updated project dependencies to include `typer>=0.12` for CLI support

## [0.1.0] - 2026-01-25

### Added
- SPEC-OBSERVABILITY-001: Log level-based Slack notification system
- SPEC-BACKEND-WORKER-004: Worker architecture with distributed locking
- SPEC-BACKEND-INFRA-003: Market lifecycle and state recovery services

### Added
- SPEC-BACKEND-API-001: Korea Investment Securities OpenAPI broker adapter
- SPEC-BACKEND-002: Order execution and state management system
- SPEC-KIS-DOCS-001: KIS OpenAPI documentation reorganization and TR_ID mapping

## [0.0.1] - Initial Release

### Added
- Project boilerplate with Python 3.13
- Domain models for orders, positions, workers
- Service layer foundation
- PostgreSQL adapter with migrations
- Mock broker adapter for testing
- Basic test framework with pytest
