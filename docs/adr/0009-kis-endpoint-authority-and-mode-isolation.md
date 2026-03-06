# ADR-0009: KIS Endpoint Authority and Mode Isolation

- Status: Accepted
- Date: 2026-03-05
- Decision Makers: stock-manager maintainers

## Context

On 2026-03-05, Slack `/sm start --mock` failed after startup preflight/strategy fetch because
some domestic stock API wrappers used hardcoded absolute endpoints (`https://api.koreainvestment.com`).
This bypassed `KISConfig.api_base_url`, so runtime mode (`KIS_USE_MOCK`) and actual request destination diverged.

Resulting risk:
- mock mode accidentally calling non-mock domain,
- intermittent engine crash during preflight or strategy execution,
- hard-to-diagnose behavior where some APIs succeed and others fail.

## Decision

Adopt strict endpoint authority rules:

1. `KISConfig.api_base_url` is the single source of truth for REST authority (host+port).
2. KIS API wrapper modules must pass relative paths (`/uapi/...`) to `KISRestClient.make_request`.
3. `KISRestClient.make_request` enforces runtime origin policy:
   - relative paths are always allowed,
   - absolute URLs are allowed only when origin exactly matches current `api_base_url`,
   - cross-mode absolute URLs are rejected immediately with `KISAPIError`.
4. CI enforces static policy via `scripts/validate_kis_endpoint_policy.py`.

## Consequences

Positive:
- Mock/real mode drift is blocked both statically (CI) and dynamically (runtime).
- Endpoint regressions fail fast with explicit error context.
- Strategy and preflight behavior becomes deterministic by configured mode.

Negative:
- Legacy code using absolute endpoint wrappers requires migration to relative paths.
- Absolute URLs in tests/mocks must now match configured origin or use relative paths.

## Alternatives Considered

1. Keep absolute URLs and rely on code review.
- Rejected: regression risk remains high and failures occur only at runtime.

2. Allow any KIS-like host and only log warning.
- Rejected: warnings are easy to ignore and do not enforce mode safety.

3. Remove runtime guard and enforce policy only in CI.
- Rejected: runtime safety should not depend solely on CI coverage.

## See Also

- [ADR-0001](0001-mock-first-safety-gate.md) - Mock-first operational policy.
- [kis-endpoint-guardrails.md](../kis-endpoint-guardrails.md) - Incident runbook and checklist.
