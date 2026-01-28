# SPEC-FIX-001: 구현 계획 (Implementation Plan)

## 구현 마일스톤

### 1차 마일스톤: SQL Placeholder 통일 (Priority: MEDIUM)

**목표:** 모든 Service 레이어 SQL 쿼리가 %s 사용

**작업:**
- [ ] lock_service.py: 6개 location 수정
- [ ] worker_lifecycle_service.py: 5개 location 수정
- [ ] daily_summary_service.py: 3개 location 수정
- [ ] Grep으로 $1, $2 패턴 전체 검색 및 수정 확인
- [ ] 각 Service 단위 테스트 실행

**검증:**
```bash
# 모든 $1, $2 패턴 제거 확인
grep -r '\$[1-9]' src/stock_manager/service_layer/
# Expected: No results
```

---

### 2차 마일스톤: Market Data Poller 구현 (Priority: MEDIUM)

**목표:** Market Data Poller가 실제 데이터 반환

**작업:**
- [ ] _fetch_market_data() mock 구현
- [ ] MarketData 객체 반환 로직 추가
- [ ] 로깅 개선
- [ ] 빈 리스트 반환 시 명확한 사유 로그

**검증:**
```python
# Test discover_candidates
candidates = await poller.discover_candidates()
assert len(candidates) > 0  # Mock data 반환
assert candidates[0].symbol == "005930"
```

---

## 위험 완화

### 위험 1: SQL Placeholder 누락

**위험:** 일부 쿼리에서 $1 패턴이 누락될 수 있음

**완화:**
- Grep 전체 검색으로 누락 방지
- PR Review 시 코드 diff 확인
- 통합 테스트로 검증

### 위험 2: Mock Data 의존성

**위험:** Mock 데이터로 인해 실제 환경에서 동작 안 할 수 있음

**완화:**
- 명확한 TODO 주석 추가
- 실제 KIS API 연동은 SPEC-API-001에서 처리
- 환경변수로 mock/real 모드 전환 지원

---

## 구현 순서

1. **SQL Placeholder 일괄 수정** (기존 기능 복구)
   - lock_service.py
   - worker_lifecycle_service.py
   - daily_summary_service.py

2. **Market Data Poller Mock 구현** (신규 기능)

3. **통합 테스트** (전체 검증)

---

## 수정 예시

### lock_service.py 수정

```python
# Line 95
# BEFORE:
VALUES ($1, $2, $3, $4, $5, 'ACTIVE')
# AFTER:
VALUES (%s, %s, %s, %s, %s, 'ACTIVE')

# Line 148
# BEFORE:
WHERE symbol = $1 AND worker_id = $2
# AFTER:
WHERE symbol = %s AND worker_id = %s
```

### worker_lifecycle_service.py 수정

```python
# Line 92
# BEFORE:
VALUES ($1, 'IDLE', NULL, $2, $3, $4)
# AFTER:
VALUES (%s, 'IDLE', NULL, %s, %s, %s)
```

### daily_summary_service.py 수정

```python
# Line 300 (12개 placeholder)
# BEFORE:
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
# AFTER:
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
```
