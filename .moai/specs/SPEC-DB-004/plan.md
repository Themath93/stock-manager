# SPEC-DB-004: 구현 계획 (Implementation Plan)

## 구현 마일스톤

### 1차 마일스톤: Enum 호환성 해결 (Priority: HIGH)

**목표:** psycopg2 Enum 타입 에러 해결

**작업:**
- [ ] `enum_helper.py` 유틸리티 모듈 생성
- [ ] `order_service.py`에서 enum_to_string 사용
- [ ] 기타 Service 레이어 Enum 사용处 검토
- [ ] 단위 테스트 추가

**검증:**
```python
# Test Enum conversion
from stock_manager.utils.enum_helper import enum_to_string
from stock_manager.adapters.broker.port import OrderSide

result = enum_to_string(OrderSide.BUY)
assert result == "BUY"
```

---

### 2차 마일스톤: Position id 필드 수정 (Priority: HIGH)

**목표:** PositionService 초기화 에러 해결

**작업:**
- [ ] `position_service.py` _initialize_position 수정
- [ ] id=0 placeholder 추가
- [ ] 테스트 검증

**검증:**
```python
# Test Position initialization
position = position_service._initialize_position("AAPL")
assert position.id == 0
assert position.symbol == "AAPL"
```

---

### 3차 마일스톤: 누락된 테이블 마이그레이션 생성 (Priority: HIGH)

**목표:** Service 레이어에서 참조하는 모든 테이블 존재

**작업:**
- [ ] 0003_add_missing_tables.sql 생성
- [ ] 0004_fix_fills_side.sql 생성 (검증용)
- [ ] 마이그레이션 적용 테스트
- [ ] 기존 데이터 보존 확인

**검증:**
```sql
-- Verify tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('stock_locks', 'worker_processes', 'daily_summaries');
```

---

## 위험 완화

### 위험 1: 기존 데이터 호환성

**위험:** fills 테이블에 기존 데이터가 존재할 경우 타입 변경 실패

**완화:**
- 0004 마이그레이션에서 조건부 실행
- 데이터 백업 후 진행
- 테스트 환경에서 먼저 검증

### 위험 2: Enum 변환 누락

**위험:** 다른 Service에서 Enum을 직접 사용하는 곳이 존재

**완화:**
- Grep으로 Enum 사용처 전체 검색
- enum_to_string으로 일괄 변환
- 통합 테스트로 검증

---

## 구현 순서

1. **enum_helper.py 생성** (영향 범위 작음)
2. **position_service.py 수정** (단일 파일)
3. **order_service.py 수정** (Enum 변환 적용)
4. **마이그레이션 생성** (데이터베이스 변경)
5. **통합 테스트** (전체 검증)
