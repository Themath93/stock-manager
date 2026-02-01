"""KIS API Tests.

Test suite following Kent Beck's TDD methodology for the
Korea Investment Securities (KIS) OpenAPI adapter.

Test Organization:
- tests/conftest.py: Global fixtures and test configuration
- tests/factories/: Mock response and test data factories
- tests/unit/: Unit tests for individual components
- tests/integration/: Integration tests (when needed)

TDD Cycle:
1. RED: Write failing test that documents expected behavior
2. GREEN: Make test pass with minimal implementation
3. REFACTOR: Improve code while keeping tests green

Coverage Targets:
- Overall: 85%
- client.py: 95%
- config.py: 90%
- OAuth APIs: 90%
- Domestic stock APIs: 85%
- Overseas stock APIs: 80%
"""
