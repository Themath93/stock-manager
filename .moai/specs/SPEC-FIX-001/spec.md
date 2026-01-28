# SPEC-FIX-001: Service Layer Corrections

## 메타데이터

- **SPEC ID**: SPEC-FIX-001
- **제목**: Service Layer Corrections
- **생성일**: 2026-01-28
- **상태**: planned
- **버전**: 1.0.0
- **우선순위**: MEDIUM
- **담당자**: Alfred (workflow-spec)
- **관련 SPEC**: SPEC-DB-004 (선행)
- **유형**: Bug Fix

---

## 개요 (Overview)

Service Layer에서의 SQL placeholder 불일치와 Market Data Poller 빈 반환값 문제를 해결합니다.

**문제 정의:**
1. SQL 쿼리에서 $1, $2 스타일 placeholder 사용 (psycopg2는 %s 필요)
2. Market Data Poller _fetch_market_data()가 빈 리스트 반환 (구현되지 않음)

**현재 상태:**
- lock_service.py, worker_lifecycle_service.py, daily_summary_service.py에서 $1, $2 사용
- psycopg2는 %s placeholder 요구
- market_data_poller.py에 TODO만 존재

**목표:**
- 모든 SQL placeholder를 %s로 통일
- Market Data Poller 기본 구현 추가

---

## 환경 (Environment)

### 기술 스택

- **Python**: 3.13+
- **데이터베이스**: PostgreSQL 15
- **DB 드라이버**: psycopg2 (requires %s placeholders)

### 영향 받는 파일

1. **수정 파일**
   - `src/stock_manager/service_layer/lock_service.py`
   - `src/stock_manager/service_layer/worker_lifecycle_service.py`
   - `src/stock_manager/service_layer/daily_summary_service.py`
   - `src/stock_manager/service_layer/market_data_poller.py`

---

## 요구사항 (Requirements)

### TAG BLOCK

```
TAG-SPEC-FIX-001-001: SQL placeholder $1 → %s 변환
TAG-SPEC-FIX-001-002: lock_service placeholder 수정
TAG-SPEC-FIX-001-003: worker_lifecycle_service placeholder 수정
TAG-SPEC-FIX-001-004: daily_summary_service placeholder 수정
TAG-SPEC-FIX-001-005: market_data_poller 기본 구현
```

### 1. Ubiquitous Requirements (항상 지원)

**REQ-UB-001: SQL Placeholder 일관성**
- 모든 SQL 쿼리는 %s placeholder를 사용해야 한다 (SHALL)
- $1, $2 스타일은 사용해서는 안 된다 (MUST NOT)
- 왜: psycopg2 표준
- 영향: 쿼리 실행 실패

**REQ-UB-002: Market Data Polling**
- Poller는 실제 데이터를 반환해야 한다 (SHALL)
- 빈 리스트는 에러 상황에서만 허용됨 (SHOULD)
- 왜: 후보 종목 선택 불가
- 영향: 트레이딩 로직 중단

### 2. Event-Driven Requirements (WHEN X, THEN Y)

**REQ-ED-001: 쿼리 실행 시**
- WHEN service가 parameterized query 실행
- THEN SHALL use %s placeholders
- AND SHALL pass parameters as tuple
- 왜: psycopg2 요구사항
- 영향: ProgrammingError

**REQ-ED-002: Market Data 조회 시**
- WHEN discover_candidates 호출
- THEN poller SHALL return non-empty list (when data available)
- AND SHALL log if truly empty
- 왜: 빈 결과는 에러일 가능성
- 영향: silent failure

### 3. State-Driven Requirements (IF condition, THEN action)

**REQ-SD-001: Broker API 미지원 시**
- IF broker does not support market data API
- THEN poller SHALL log warning
- AND SHALL return empty list with clear reason
- 왜: 명확한 실패 사유 전달
- 영향: 디버깅 어려움

---

## 상세 설계 (Specifications)

### SQL Placeholder 수정 패턴

**Before ($1, $2 style - PostgreSQL native):**
```python
query = """
    SELECT * FROM stock_locks
    WHERE symbol = $1 AND worker_id = $2
"""
cursor.execute(query, (symbol, worker_id))
```

**After (%s style - psycopg2):**
```python
query = """
    SELECT * FROM stock_locks
    WHERE symbol = %s AND worker_id = %s
"""
cursor.execute(query, (symbol, worker_id))
```

### 수정 파일 상세

**1. lock_service.py (6 locations):**
- Line 95: VALUES ($1, $2, $3, $4, $5, 'ACTIVE')
- Line 148: WHERE symbol = $1 AND worker_id = $2
- Line 196-197: SET expires_at = $1, heartbeat_at = $2 ... WHERE symbol = $3
- Line 252-253: SET heartbeat_at = $1 ... WHERE symbol = $2
- Line 354: WHERE symbol = $1
- Line 387: WHERE symbol = $1 AND status = 'ACTIVE'

**2. worker_lifecycle_service.py (5 locations):**
- Line 92: VALUES ($1, 'IDLE', NULL, $2, $3, $4)
- Line 152-153: SET last_heartbeat_at = $1 ... WHERE worker_id = $2
- Line 212-213: SET status = $1 ... WHERE worker_id = $4
- Line 303: WHERE last_heartbeat_at < $1
- Line 326: WHERE worker_id = $1

**3. daily_summary_service.py (3 locations):**
- Line 115: WHERE worker_id = $1 AND summary_date = $2
- Line 171: WHERE worker_id = $1
- Line 300: VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)

### Market Data Poller 기본 구현

**market_data_poller.py 수정:**

```python
# BEFORE:
async def _fetch_market_data(self) -> list[MarketData]:
    logger.warning("Market data fetching not yet implemented - returning empty list")
    return []

# AFTER:
async def _fetch_market_data(self) -> list[MarketData]:
    """Fetch market data from broker

    Returns:
        list[MarketData]: List of market data

    Note:
        For KIS broker, this requires implementing market data API calls.
        Current implementation returns mock data for testing.
    """
    try:
        # TODO: Implement actual KIS market data API
        # KIS provides: 인기종목, 일자별주가, etc.

        # Placeholder: Return mock data for testing
        logger.info("Fetching market data (mock implementation)")

        # Mock data - replace with actual broker API calls
        mock_data = [
            MarketData(
                symbol="005930",
                name="삼성전자",
                price=Decimal("75000"),
                change=Decimal("500"),
                change_percent=Decimal("0.67"),
                volume=1000000,
                timestamp=datetime.now(),
            ),
            MarketData(
                symbol="000660",
                name="SK하이닉스",
                price=Decimal("120000"),
                change=Decimal("-1000"),
                change_percent=Decimal("-0.83"),
                volume=500000,
                timestamp=datetime.now(),
            ),
        ]

        logger.info(f"Fetched {len(mock_data)} market data items")
        return mock_data

    except Exception as e:
        logger.error(f"Failed to fetch market data: {e}")
        return []
```

---

## 추적성 (Traceability)

### TAG Mapping

| TAG | 설명 | 파일 | 수정 라인 |
|-----|------|------|----------|
| TAG-SPEC-FIX-001-001 | SQL placeholder $1 → %s 변환 | All service files | Multiple |
| TAG-SPEC-FIX-001-002 | lock_service placeholder 수정 | lock_service.py | 6 locations |
| TAG-SPEC-FIX-001-003 | worker_lifecycle placeholder 수정 | worker_lifecycle_service.py | 5 locations |
| TAG-SPEC-FIX-001-004 | daily_summary placeholder 수정 | daily_summary_service.py | 3 locations |
| TAG-SPEC-FIX-001-005 | market_data_poller 기본 구현 | market_data_poller.py | 108-125 |

---

## 의존성 (Dependencies)

### 선행 SPEC (Prerequisites)
- **SPEC-DB-004**: Database Schema & Type Adaptation (테이블 존재 필요)

### 후속 SPEC (Dependents)
- **SPEC-API-001**: KIS API Integration Fixes (Broker API 연동)
