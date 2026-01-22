# 구현 계획: 장 시작/종료 및 상태 복구 라이프사이클

## 1. 개요

본 계획은 SPEC-BACKEND-INFRA-003의 구현을 위한 단계별 작업을 정의합니다. 장 라이프사이클 서비스, 상태 복구, 장 종료 정산, 스케줄러 통합, 테스트 등 4단계로 구성됩니다.

---

## 2. 기술 스택

| 분류 | 기술 | 버전 | 설명 |
|------|------|------|------|
| 언어 | Python | 3.13+ | 타입 힌트, dataclass 활용 |
| 스케줄러 | APScheduler | 3.10+ | 장 시작/종료 스케줄링 |
| 타임존 | pytz | 2023.3+ | Asia/Seoul 시간대 |
| 이벤트 버스 | custom | - | Pydantic 기반 이벤트 버스 |
| 로깅 | logging | stdlib | 표준 라이브러리 |
| 테스트 | pytest | 7.4+ | 단위/통합 테스트 |
| 테스트 더블 | pytest-mock | 3.12+ | Mock/patch 지원 |

---

## 3. 작업 분해

### Phase 1: 장 라이프사이클 서비스 기본 구현 (Week 1)

#### Task 1.1: 데이터 모델 정의
- [ ] `domain/models/lifecycle.py` 생성
- [ ] SystemState, DailySettlement dataclass 정의
- [ ] SystemState, RecoveryStatus enum 정의
- [ ] 타입 힌트 추가

**파일:** `src/stock_manager/domain/models/lifecycle.py`

**의존성:** 없음
**담당:** 1개발자
**예상 시간:** 4시간

---

#### Task 1.2: MarketLifecycleService 인터페이스 정의
- [ ] `service_layer/market_lifecycle_service.py` 생성
- [ ] 추상 메서드 정의 (open_market, close_market, get_system_state)
- [ ] MarketLifecyclePort 인터페이스 정의
- [ ] 타입 힌트 추가

**파일:** `src/stock_manager/service_layer/market_lifecycle_service.py`

**의존성:** Task 1.1
**담당:** 1개발자
**예상 시간:** 4시간

---

#### Task 1.3: MarketLifecycleServiceImpl 기본 구현
- [ ] `service_layer/market_lifecycle_service_impl.py` 생성
- [ ] `open_market()` 구현 (뼈대)
- [ ] `close_market()` 구현 (뼈대)
- [ ] `get_system_state()` 구현
- [ ] 시스템 상태 관리
- [ ] 이벤트 발행 (MarketOpenEvent, MarketCloseEvent)

**파일:** `src/stock_manager/service_layer/market_lifecycle_service_impl.py`

**의존성:** Task 1.2
**담당:** 1개발자
**예상 시간:** 8시간

**테스트:**
- [ ] 시스템 상태 전이 테스트 (OFFLINE → INITIALIZING → READY)
- [ ] 이벤트 발행 테스트

---

### Phase 2: 상태 복구 구현 (Week 2)

#### Task 2.1: StateRecoveryService 인터페이스 및 구현
- [ ] `service_layer/state_recovery_service.py` 생성
- [ ] StateRecoveryPort 인터페이스 정의
- [ ] `recover()` 구현 (뼈대)
- [ ] `sync_unfilled_orders()` 구현
- [ ] `recalculate_positions()` 구현

**파일:** `src/stock_manager/service_layer/state_recovery_service.py`

**의존성:** SPEC-BACKEND-002 완료 (OrderService, PositionService)
**담당:** 1개발자
**예상 시간:** 12시간

**테스트:**
- [ ] 상태 복구 성공 테스트
- [ ] 미체결 주문 동기화 테스트
- [ ] 포지션 재계산 테스트

---

#### Task 2.2: DB/브로커 상태 비교 로직
- [ ] DB 미체결 주문 조회
- [ ] 브로커 주문 상태 조회
- [ ] 상태 불일치 시 동기화
- [ ] 브로커 상태 우선 적용
- [ ] 불일치 이력 기록

**파일:** `src/stock_manager/service_layer/state_recovery_service.py` (추가)

**의존성:** Task 2.1, SPEC-BACKEND-API-001 완료
**담당:** 1개발자
**예상 시간:** 10시간

**테스트:**
- [ ] DB 상태와 브로커 상태 동일 시 동기화 안 함 테스트
- [ ] DB 상태와 브로커 상태 다르면 동기화 테스트
- [ ] 여러 불일치 주문 처리 테스트

---

#### Task 2.3: 장 시작 프로세스 구현
- [ ] 장 시작 단계별 구현 (1~9단계)
  1. 설정 로드
  2. 인증
  3. 계좌 확인
  4. 전략 파라미터 로드
  5. 상태 복구
  6. 리스크 가드레일 초기화
  7. 유니버스 확정
  8. 실시간 이벤트 등록
  9. 시스템 상태 READY 전환

**파일:** `src/stock_manager/service_layer/market_lifecycle_service_impl.py` (추가)

**의존성:** Task 1.3, Task 2.2, SPEC-BACKEND-API-001, SPEC-BACKEND-002 완료
**담당:** 1개발자
**예상 시간:** 16시간

**테스트:**
- [ ] 장 시작 전체 프로세스 테스트
- [ ] 각 단계 실패 시 오류 처리 테스트
- [ ] 장 시작 완료 후 시스템 상태 READY 테스트

---

### Phase 3: 장 종료 정산 (Week 3)

#### Task 3.1: 장 종료 프로세스 구현
- [ ] 장 종료 단계별 구현 (1~8단계)
  1. 시스템 상태 CLOSING 전환
  2. 미체결 주문 취소 확인
  3. 포지션 스냅샷 생성
  4. 일일 정산 계산
  5. DailySettlementEvent 발행
  6. 실시간 이벤트 구독 해제
  7. WebSocket 연결 종료
  8. 시스템 상태 CLOSED 전환

**파일:** `src/stock_manager/service_layer/market_lifecycle_service_impl.py` (추가)

**의존성:** Task 2.3
**담당:** 1개발자
**예상 시간:** 12시간

**테스트:**
- [ ] 장 종료 전체 프로세스 테스트
- [ ] 포지션 스냅샷 생성 테스트
- [ ] 일일 정산 계산 테스트
- [ ] 장 종료 완료 후 시스템 상태 CLOSED 테스트

---

#### Task 3.2: 포지션 스냅샷 생성
- [ ] 모든 포지션 조회
- [ ] 현재 시간 스냅샷 생성
- [ ] positions 테이블에 스냅샷 저장 (또는 별도 테이블)
- [ ] JSONB로 포지션 데이터 저장

**파일:** `src/stock_manager/service_layer/market_lifecycle_service_impl.py` (추가)

**의존성:** Task 3.1, SPEC-BACKEND-002 완료
**담당:** 1개발자
**예상 시간:** 6시간

**테스트:**
- [ ] 포지션 스냅샷 생성 테스트
- [ ] 스냅샷 데이터 정확성 테스트

---

#### Task 3.3: 일일 정산 계산
- [ ] 실현 손익 계산 (fills 기반)
- [ ] 평가 손익 계산 (현재 포지션 * 현재 가격)
- [ ] 총 손익 계산
- [ ] DailySettlement 레코드 생성

**파일:** `src/stock_manager/service_layer/market_lifecycle_service_impl.py` (추가)

**의존성:** Task 3.2
**담당:** 1개발자
**예상 시간:** 8시간

**테스트:**
- [ ] 실현 손익 계산 테스트
- [ ] 평가 손익 계산 테스트
- [ ] 총 손익 계산 테스트

---

### Phase 4: 스케줄러 통합 및 테스트 (Week 4)

#### Task 4.1: 스케줄러 설정
- [ ] APScheduler 설정
- [ ] 장 시작 스케줄 등록 (08:30:00 KST)
- [ ] 장 종료 스케줄 등록 (15:30:00 KST)
- [ ] Asia/Seoul 시간대 설정
- [ ] 환경 변수로 장 시간 설정 가능

**파일:** `src/stock_manager/entrypoints/scheduler.py`

**의존성:** Task 2.3, Task 3.1
**담당:** 1개발자
**예상 시간:** 6시간

**테스트:**
- [ ] 스케줄러 시작/정지 테스트
- [ ] 장 시작 시간 정확성 테스트
- [ ] 장 종료 시간 정확성 테스트

---

#### Task 4.2: 거래 중지 모드 구현
- [ ] STOPPED 상태 정의
- [ ] 주문 전송 차단 로직
- [ ] 감시/기록만 수행
- [ ] 수동 재시작 메서드

**파일:** `src/stock_manager/service_layer/market_lifecycle_service_impl.py` (추가)

**의존성:** Task 2.3
**담당:** 1개발자
**예상 시간:** 6시간

**테스트:**
- [ ] STOPPED 상태로 전환 테스트
- [ ] STOPPED 상태에서 주문 차단 테스트
- [ ] 수동 재시작 테스트

---

#### Task 4.3: 단위 테스트 작성
- [ ] MarketLifecycleService 테스트 (Task 1.3, 2.3, 3.1, 4.2)
- [ ] StateRecoveryService 테스트 (Task 2.1, 2.2)
- [ ] 스케줄러 테스트 (Task 4.1)

**파일:**
- `tests/unit/test_market_lifecycle_service.py`
- `tests/unit/test_state_recovery_service.py`
- `tests/unit/test_scheduler.py`

**의존성:** Phase 1-3 완료
**담당:** 1개개발자
**예상 시간:** 16시간

---

#### Task 4.4: 통합 테스트 작성
- [ ] 전체 장 시작/종료 흐름 테스트
- [ ] 상태 복구 통합 테스트
- [ ] 장 마감 정산 통합 테스트
- [ ] 거래 중지 모드 통합 테스트

**파일:** `tests/integration/test_market_lifecycle.py`

**의존성:** Task 4.3
**담당:** 1개발자
**예상 시간:** 12시간

---

#### Task 4.5: 커버리지 확인 및 리팩터링
- [ ] pytest-cov 설정
- [ ] 최소 70% 커버리지 확인
- [ ] 미달 시 추가 테스트 작성
- [ ] 코드 리팩터링 (중복 제거, 가독성 개선)

**명령:** `pytest --cov=src/stock_manager/service_layer --cov-report=html`

**의존성:** Task 4.4
**담당:** 1개발자
**예상 시간:** 8시간

---

#### Task 4.6: 문서화
- [ ] README 작성 (사용법, 스케줄 설정)
- [ ] API 문서 작성 (메서드별 설명)
- [ ] 장 시작/종료 프로세스 다이어그램 작성

**파일:** `src/stock_manager/service_layer/README.md`

**의존성:** Task 4.5
**담당:** 1개발자
**예상 시간:** 4시간

---

## 4. 리소스 요구사항

| 리소스 | 양 | 설명 |
|--------|------|------|
| 개발자 | 1명 | Python, 스케줄러, 트랜잭션 경험 |
| 기간 | 4주 | Phase 1-4 순차 진행 |
| 환경 | Python 3.13, PostgreSQL 15+ | 개발/테스트 환경 |
| 의존 | SPEC-BACKEND-API-001, SPEC-BACKEND-002 완료 | BrokerPort, OrderService, PositionService 필요 |

---

## 5. 타임라인

| 주차 | Phase | 주요 목표 |
|------|-------|-----------|
| Week 1 | Phase 1 | 장 라이프사이클 서비스 기본 구현 완료 |
| Week 2 | Phase 2 | 상태 복구, 장 시작 프로세스 완료 |
| Week 3 | Phase 3 | 장 종료 정산 완료 |
| Week 4 | Phase 4 | 스케줄러 통합, 테스트, 문서화 완료 |

---

## 6. 위험 분석 및 완화

| 위험 | 영향 | 확률 | 완화 전략 |
|------|------|------|-----------|
| 상태 복구 실패 | HIGH | MEDIUM | 복구 실패 시 거래 중지, 로그 기록 |
| 장 시작 시간 지연 | HIGH | LOW | 스케줄러 설정 확인, 시간대 설정 |
| DB/브로커 상태 불일치 | MEDIUM | MEDIUM | 브로커 우선, 불일치 로그 |
| 스케줄러 충돌 | MEDIUM | LOW | 단일 인스턴스 실행, 락 메커니즘 |
| 장 종료 시 정산 오류 | MEDIUM | LOW | 정산 실패 시 로그 기록, 다음 장 재시도 |

---

## 7. 성공 기준

- [ ] MarketLifecycleService가 MarketLifecyclePort 인터페이스를 완전히 구현
- [ ] StateRecoveryService가 StateRecoveryPort 인터페이스를 완전히 구현
- [ ] 장 시작 프로세스 완료 (1~9단계)
- [ ] 상태 복구 기능 동작 (DB/브로커 동기화)
- [ ] 미체결 주문 복구 기능 동작
- [ ] 장 종료 프로세스 완료 (1~8단계)
- [ ] 포지션 스냅샷 생성 기능 동작
- [ ] 일일 정산 계산 기능 동작
- [ ] 스케줄러 통합 기능 동작
- [ ] 거래 중지 모드 기능 동작
- [ ] 단위 테스트 커버리지 70% 이상
- [ ] 통합 테스트 전체 흐름 정상
- [ ] 문서화 완료
