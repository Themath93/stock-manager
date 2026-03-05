# ADR-0004: Disk-Backed OAuth Token Cache

- Status: Accepted
- Date: 2026-03-02
- Decision Makers: stock-manager maintainers

## Context

KIS OAuth token issuance is rate-limited to one request per minute.
Tokens are valid for approximately 24 hours.
Without persistence, every process restart triggers a new token request, risking rate-limit violations during rapid development or crash-recovery cycles.

## Decision

Persist OAuth tokens to disk at `~/.stock_manager/kis_token_{mode}.json`:

- **Atomic write**: Write to a temp file, `fsync`, then `os.rename` to prevent corruption on crash.
- **App-key fingerprint**: SHA-256 hash of the app key is stored alongside the token to invalidate cache when credentials change.
- **Minimum TTL**: Tokens with less than 60 seconds remaining are treated as expired to avoid mid-request expiration.
- **File permissions**: `0600` (owner read/write only) to protect the bearer token at rest.

On startup, the cache is read first. Only on miss or expiry is a new token requested from KIS.

## Consequences

Positive:
- Eliminates redundant token requests across restarts, staying well within rate limits.
- Atomic write prevents partial-read corruption.
- Credential rotation is detected automatically via fingerprint mismatch.

Negative:
- Tokens at rest on disk are a security surface; mitigated by `0600` permissions.
- Cache file must be excluded from version control (covered by `.gitignore`).

## Alternatives Considered

1. In-memory cache only.
   - Rejected because every restart would consume a rate-limited token request.
2. Redis or external cache store.
   - Rejected as over-engineered for a single-user desktop application.
3. SQLite token store.
   - Rejected; a single JSON file is simpler and sufficient for one token per mode.

## See Also

- [ADR-0003](0003-kis-broker-adapter-pattern.md) — KIS 브로커 어댑터 패턴 (어댑터 하위 시스템)
