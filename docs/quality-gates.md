# Quality Gates Matrix

This document is the single map for where each quality gate is defined and enforced.

Scope:
- Focus on docs and enforcement visibility.
- Do not change trading business logic.

## Policy Decision

- Canonical coverage threshold: `--cov-fail-under=85`
- Why: CI already enforces 85 and this value is now aligned across root policy docs and pytest defaults.

## Current Enforcement Matrix

| Gate | Command | Local (manual) | CI (blocking) | Source of Truth |
|---|---|---|---|---|
| Lint | `uv run ruff check` | Yes | Yes | `.github/workflows/ci.yml`, `pyproject.toml` |
| Type Check | `uv run mypy stock_manager` | Yes | Yes | `.github/workflows/ci.yml`, `pyproject.toml` |
| Unit Tests + Coverage | `uv run pytest tests/unit tests/fixtures --cov=stock_manager --cov-fail-under=85` | Yes | Yes | `.github/workflows/ci.yml`, `pyproject.toml` |
| Full Tests | `uv run pytest` | Yes | Yes (nightly) | `.github/workflows/nightly-full-suite.yml`, `pyproject.toml`, `AGENTS.md`, `README.md` |
| Architecture Boundary Check | `uv run lint-imports --config pyproject.toml` | Yes | Yes | `.github/workflows/ci.yml`, `pyproject.toml` |
| Drift/GC Scheduled Gate | `uv run python scripts/mock_qa_gate.py --emit .sisyphus/evidence/mock-promotion-gate.json` | Yes | Yes (scheduled) | `.github/workflows/drift-gc.yml`, `stock_manager/qa/mock_gate.py` |
| Build | `uv build` | Yes | Yes | `.github/workflows/ci.yml`, `AGENTS.md`, `README.md` |

## Gap List (Week-1)

| Gap | Impact | Planned Action |
|---|---|---|
| Full-suite tests are not in PR blocking path | 일부 통합/느린 회귀가 PR 단계에서 늦게 발견될 수 있음 | Keep fast PR gates and use `.github/workflows/nightly-full-suite.yml` for broad coverage |

## Related Decisions

- [ADR-0001: Mock-first safety gate](adr/0001-mock-first-safety-gate.md) — Drift/GC gate의 mock-first 정책 근거.
- [ADR-0002: Coverage threshold 85%](adr/0002-coverage-threshold-85.md) — 85% 커버리지 임계값 결정 근거.

## Verification Checklist

- [ ] Coverage threshold is consistent in CI, pytest config, and root docs.
- [ ] Every gate has a command and enforcement location.
- [ ] New contributors can find this matrix from AGENTS and README.
