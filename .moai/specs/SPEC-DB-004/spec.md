# SPEC-DB-004: Database Schema & Type Adaptation

## 메타데이터

- **SPEC ID**: SPEC-DB-004
- **제목**: Database Schema & Type Adaptation
- **생성일**: 2026-01-28
- **상태**: planned
- **버전**: 1.0.0
- **우선순위**: HIGH
- **담당자**: Alfred (workflow-spec)
- **관련 SPEC**: SPEC-DB-001, SPEC-DB-002, SPEC-DB-003
- **유형**: Database Fix

---

## 개요 (Overview)

데이터베이스 스키마 불일치와 Enum 타입 호환성 문제를 해결하여 모든 서비스가 정상적으로 동작하도록 합니다.

**문제 정의:**
1. OrderSide Enum을 psycopg2에 전달 시 "can't adapt type 'OrderSide'" 에러 발생
2. Service에서 기대하는 테이블이 누락됨 (fills.side, stock_locks, worker_processes, daily_summaries, system_states, daily_settlements)
3. Position Service가 Position 객체 생성 시 required id 필드 누락

**현재 상태:**
- 2개 마이그레이션만 존재 (0001_init.sql, 0002_add_order_fill_fields.sql)
- service_layer에서 참조하는 테이블들이 존재하지 않음
- Enum → String 변환 로직이 일관되지 않음

**목표:**
- Enum 타입을 String으로 변환하여 psycopg2 호환성 확보
- 누락된 테이블 마이그레이션 생성
- Position Service id 필드 수정

---

## 환경 (Environment)

### 기술 스택

- **Python**: 3.13+
- **데이터베이스**: PostgreSQL 15
- **ORM 드라이버**: psycopg2-binary

### 영향 받는 파일

1. **수정 파일**
   - `src/stock_manager/service_layer/order_service.py` (Enum → String 변환)
   - `src/stock_manager/service_layer/position_service.py` (id 필드 수정)

2. **생성 파일**
   - `db/migrations/0003_add_missing_tables.sql` (새 마이그레이션)
   - `db/migrations/0004_fix_fills_side.sql` (fills.side 컬럼 수정)

---

## 요구사항 (Requirements)

### TAG BLOCK

```
TAG-SPEC-DB-004-001: Enum String 변환 래퍼 구현
TAG-SPEC-DB-004-002: fills 테이블 side 컬럼 VARCHAR 변경
TAG-SPEC-DB-004-003: 누락된 테이블 마이그레이션 생성
TAG-SPEC-DB-004-004: Position id 필드 수정
```

### 1. Ubiquitous Requirements (항상 지원)

**REQ-UB-001: Enum 호환성**
- 모든 Enum 타입은 psycopg2에 전달 전 String으로 변환되어야 한다 (SHALL)
- Enum 변환 로직은 재사용 가능해야 한다 (SHALL)
- 왜: psycopg2는 Python Enum을 직접 처리하지 못함
- 영향: "can't adapt type" 에러

**REQ-UB-002: 스키마 완결성**
- Service에서 참조하는 모든 테이블이 존재해야 한다 (SHALL)
- 마이그레이션은 순서대로 적용 가능해야 한다 (SHALL)
- 왜: 쿼리 실행 실패
- 영향: 서비스 시작 불가

### 2. Event-Driven Requirements (WHEN X, THEN Y)

**REQ-ED-001: Enum 전달 시 변환**
- WHEN OrderSide Enum이 psycopg2에 전달됨
- THEN SHALL convert to string value
- AND SHALL preserve enum semantics
- 왜: 데이터베이스는 VARCHAR로 저장
- 영향: 쿼리 실패

**REQ-ED-002: 마이그레이션 적용 시**
- WHEN 0003_add_missing_tables.sql이 실행됨
- THEN SHALL create all missing tables
- AND SHALL NOT drop existing data
- 왜: 안전한 스키마 업그레이드
- 영향: 데이터 손실

### 3. Unwanted Behaviors (금지된 동작)

**REQ-UN-001: Enum 직접 전달 금지**
- Service는 Enum을 직접 쿼리 파라미터로 전달해서는 안 된다 (MUST NOT)
- Enum.value 속성을 사용해서 변환해야 한다 (SHALL)
- 왜: psycopg2 타입 에러
- 영향: 실행 실패

---

## 상세 설계 (Specifications)

### 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                  Enum → String Conversion                   │
│                                                             │
│  1. Domain Layer                                            │
│     OrderSide.BUY -> Enum object                           │
│                                                             │
│  2. Service Layer (Before)                                  │
│     cursor.execute("INSERT ... (%s)", (OrderSide.BUY,))    │
│     ERROR: can't adapt type 'OrderSide'                    │
│                                                             │
│  3. Service Layer (After)                                   │
│     side_str = OrderSide.BUY.value                          │
│     cursor.execute("INSERT ... (%s)", (side_str,))         │
│     SUCCESS: "BUY" stored in VARCHAR                       │
└─────────────────────────────────────────────────────────────┘
```

### 핵심 구현: Enum 변돈

**Helper function 추가:**

```python
# src/stock_manager/utils/enum_helper.py (new file)

from enum import Enum
from typing import Union

def enum_to_string(enum_value: Union[Enum, str]) -> str:
    """
    Convert Enum to string for psycopg2 compatibility.

    Args:
        enum_value: Enum instance or string

    Returns:
        str: String value of enum
    """
    if isinstance(enum_value, Enum):
        return enum_value.value
    return str(enum_value)
```

### 핵심 수정: order_service.py

```python
# BEFORE (line 470-471):
side_value = fill_event.side.value if isinstance(fill_event.side, OrderSide) else fill_event.side

# AFTER (일관된 패턴):
from ..utils.enum_helper import enum_to_string

side_value = enum_to_string(fill_event.side)
```

### 핵심 수정: position_service.py

```python
# BEFORE (line 153-161):
def _initialize_position(self, symbol: str) -> Position:
    return Position(
        symbol=symbol,
        qty=Decimal("0"),
        avg_price=Decimal("0"),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
# ERROR: missing required field 'id'

# AFTER:
def _initialize_position(self, symbol: str) -> Position:
    return Position(
        id=0,  # Placeholder for new positions
        symbol=symbol,
        qty=Decimal("0"),
        avg_price=Decimal("0"),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
```

### 마이그레이션 생성

**db/migrations/0003_add_missing_tables.sql:**

```sql
-- Missing tables referenced by services

-- stock_locks table (lock_service.py)
CREATE TABLE IF NOT EXISTS stock_locks (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    worker_id VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    locked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    heartbeat_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, status)
);

-- worker_processes table (worker_lifecycle_service.py)
CREATE TABLE IF NOT EXISTS worker_processes (
    id SERIAL PRIMARY KEY,
    worker_id VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'IDLE',
    current_symbol VARCHAR(20),
    last_heartbeat_at TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- daily_summaries table (daily_summary_service.py)
CREATE TABLE IF NOT EXISTS daily_summaries (
    id SERIAL PRIMARY KEY,
    worker_id VARCHAR(100) NOT NULL,
    summary_date DATE NOT NULL,
    total_orders INTEGER DEFAULT 0,
    total_fills INTEGER DEFAULT 0,
    total_volume NUMERIC(20, 4) DEFAULT 0,
    total_pnl NUMERIC(20, 4) DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(worker_id, summary_date)
);
```

**db/migrations/0004_fix_fills_side.sql:**

```sql
-- Fix fills.side column type
-- Already VARCHAR in 0001_init.sql, ensuring consistency

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'fills' AND column_name = 'side'
    ) THEN
        -- Verify side is VARCHAR
        ALTER TABLE fills ALTER COLUMN side TYPE VARCHAR(10);
    END IF;
END $$;
```

---

## 추적성 (Traceability)

### TAG Mapping

| TAG | 설명 | 파일 | 상태 |
|-----|------|------|------|
| TAG-SPEC-DB-004-001 | Enum String 변환 래퍼 구현 | enum_helper.py | TODO |
| TAG-SPEC-DB-004-002 | fills 테이블 side 컬럼 VARCHAR 변경 | 0004_fix_fills_side.sql | TODO |
| TAG-SPEC-DB-004-003 | 누락된 테이블 마이그레이션 생성 | 0003_add_missing_tables.sql | TODO |
| TAG-SPEC-DB-004-004 | Position id 필드 수정 | position_service.py | TODO |

---

## 의존성 (Dependencies)

### 선행 SPEC (Prerequisites)
- **SPEC-DB-003**: Integration Test Database Schema (마이그레이션 시스템)

### 후속 SPEC (Dependents)
- **SPEC-FIX-001**: Service Layer Corrections (의존)
