# SPEC-DB-004: 수용 기준 (Acceptance Criteria)

## 수용 기준

### AC-001: Enum → String 변환

**Given:** OrderSide.BUY Enum 객체

**When:** enum_to_string 함수 호출

**Then:** "BUY" 문자열 반환

### AC-002: OrderService Enum 처리

**Given:** FillEvent with OrderSide Enum

**When:** _create_fill_in_db 실행

**Then:** "can't adapt type" 에러 없이 DB 저장

### AC-003: Position id 필드

**Given:** _initialize_position 호출

**When:** Position 객체 생성

**Then:** id 필드가 0으로 설정됨

### AC-004: 누락된 테이블 존재

**Given:** 모든 마이그레이션 적용

**When:** information_schema查询

**Then:** stock_locks, worker_processes, daily_summaries 테이블 존재

### AC-005: fills.side VARCHAR

**Given:** fills 테이블

**When:** column_type 확인

**Then:** side 컬럼이 VARCHAR 타입

## Definition of Done

- [ ] 모든 AC 통과
- [ ] 단위 테스트 작성
- [ ] 마이그레이션 테스트 통과
- [ ] 기존 데이터 보존 확인
