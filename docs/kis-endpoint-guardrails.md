# KIS Endpoint Guardrails Runbook

## Purpose

Prevent recurring outages where KIS API calls hit the wrong REST domain (mock vs real),
causing startup failures or strategy-time network/API errors.

## Incident Snapshot (2026-03-05)

- Symptom: `/sm start --strategy consensus --symbols 005930,000660 --mock` started then stopped.
- Observed behavior: balance inquiry path succeeded, then strategy data fetch failed with network/API errors.
- Root cause: 일부 API wrapper가 절대 URL(`https://api.koreainvestment.com`)을 하드코딩해서
  `KIS_USE_MOCK=true`일 때도 mock base URL을 우회함.

## Endpoint Authority Policy

- REST authority is decided only by `KISConfig.api_base_url`.
- API wrapper modules must pass **relative** paths (`/uapi/...`) to `KISRestClient.make_request`.
- Absolute endpoint URLs are forbidden in wrapper modules.
- If an absolute URL is passed at runtime, it must exactly match current mode origin:
  - mock: `https://openapivts.koreainvestment.com:29443`
  - real: `https://openapi.koreainvestment.com:9443`

## Guardrails

1. Runtime guard (`KISRestClient.make_request`)
- Rejects cross-mode absolute origins with immediate `KISAPIError`.
- Prevents silent mock/real drift at runtime.

2. Static CI gate (`scripts/validate_kis_endpoint_policy.py`)
- Scans `stock_manager/adapters/broker/kis/apis/**` (excluding `oauth/`).
- Fails build if `_BASE_URL = "https://..."` or `path = "https://..."` appears in wrappers.

3. Documentation/ADR
- This runbook + ADR-0009 define the policy and failure handling path.

## Payload + Rate Limit Runbook

### Payload policy

- Policy: auto-correct safe defaults + fail fast on core required values.
- `inquire_period_price` must always send `fid_cond_mrkt_div_code` (default: `J`).
- Blank `fid_input_iscd` / blank `fid_cond_mrkt_div_code` are rejected locally with `ValueError`.
- Contract source:
  - `docs/kis-openapi/finance-payload-contract.md`
  - `docs/kis-openapi/quotations-payload-contract.md`

### Rate-limit policy

- Global client limiter: `KIS_REQUEST_RATE_LIMIT_PER_SEC` (default: `8`).
- Limiter is enforced before every `make_request()` attempt, including retries.
- `EGW00201` is treated as a rate-limit event regardless of HTTP status:
  - HTTP 500 with JSON body `msg_cd=EGW00201`
  - HTTP 200 with KIS error payload `msg_cd=EGW00201`
- Retry backoff uses exponential + jitter to avoid synchronized retry spikes.

## Operational Checklist

1. Before starting Slack engine:
- Verify mode: `KIS_USE_MOCK=true|false`.
- Run: `uv run stock-manager doctor`.

2. If `/sm start` crashes:
- Check first failing API in logs.
- If message includes `Disallowed absolute endpoint origin`, treat as endpoint-policy violation.
- Run local guard: `uv run python scripts/validate_kis_endpoint_policy.py`.

3. If local guard passes but failures continue:
- Validate KIS status and credentials by mode.
- Re-check account and token cache separation between mock/real.
- Check `error.log` for:
  - `OPSQ2001 ... FID_COND_MRKT_DIV_CODE` (payload contract violation)
  - `EGW00201 ... 초당 거래건수를 초과` (rate-limit pressure)

## Fast Validation Commands

- `uv run python scripts/validate_kis_endpoint_policy.py`
- `uv run pytest tests/unit/test_client.py tests/unit/apis/domestic_stock/test_basic.py tests/unit/test_fetcher_rate_payload_policy.py --no-cov -q`
- `uv run ruff check stock_manager/adapters/broker/kis/client.py scripts/validate_kis_endpoint_policy.py`
