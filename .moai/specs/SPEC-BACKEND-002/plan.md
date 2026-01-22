# 구현 계획: 주문 실행 및 상태 관리 시스템

## 1. 개요

본 계획은 SPEC-BACKEND-002의 구현을 위한 단계별 작업을 정의합니다. 주문 서비스, 체결 처리, 포지션 관리, 리스크 검증, 테스트 등 5단계로 구성됩니다.

---

## 2. 기술 스택

| 분류 | 기술 | 버전 | 설명 |
|------|------|------|------|
| 언어 | Python | 3.13+ | 타입 힌트, dataclass 활용 |
| ORM | SQLAlchemy | 2.0+ | PostgreSQL ORM |
| 트랜잭션 | SQLAlchemy Core | 2.0+ | DB 트랜잭션 관리 |
| 이벤트 버스 | custom | - | Pydantic 기반 이벤트 버스 |
| 로깅 | logging | stdlib | 표준 라이브러리 |
| 테스트 | pytest | 7.4+ | 단위/통합 테스트 |
| 테스트 더블 | pytest-mock | 3.12+ | Mock/patch 지원 |

---

## 3. 작업 분해

### Phase 1: 주문 서비스 기본 구현 (Week 1)

#### Task 1.1: 데이터 모델 정의
- [ ] `domain/models/order.py` 생성
- [ ] Order, Fill, Position dataclass 정의
- [ ] OrderRequest DTO 정의
- [ ] OrderSide, OrderType, OrderStatus enum 정의
- [ ] 타입 힌트 추가

**파일:**
- `src/stock_manager/domain/models/order.py`

**의존성:** 없음
**담당:** 1개발자
**예상 시간:** 4시간

---

#### Task 1.2: OrderService 인터페이스 정의
- [ ] `service_layer/order_service.py` 생성
- [ ] 추상 메서드 정의 (create_order, send_order, cancel_order 등)
- [ ] OrderServicePort 인터페이스 정의
- [ ] 타입 힌트 추가

**파일:** `src/stock_manager/service_layer/order_service.py`

**의존성:** Task 1.1
**담당:** 1개발자
**예상 시간:** 4시간

---

#### Task 1.3: OrderRepository 구현
- [ ] `adapters/storage/order_repository.py` 생성
- [ ] SQLAlchemy 모델 정의 (orders, fills, positions 테이블)
- [ ] CRUD 메서드 구현
- [ ] DB 트랜잭션 관리
- [ ] idempotency_key 중복 체크 로직

**파일:**
- `src/stock_manager/adapters/storage/models.py` (SQLAlchemy 모델)
- `src/stock_manager/adapters/storage/order_repository.py`

**의존성:** Task 1.1
**담당:** 1개발자
**예상 시간:** 12시간

**테스트:**
- [ ] 주문 생성 테스트
- [ ] idempotency_key 중복 시 기존 주문 반환 테스트
- [ ] 주문 조회 테스트
- [ ] 미종결 주문 조회 테스트

---

#### Task 1.4: OrderServiceImpl 기본 구현
- [ ] `service_layer/order_service_impl.py` 생성
- [ ] `create_order()` 구현 (idempotency_key 생성, 주문 저장)
- [ ] `get_order()` 구현
- [ ] `get_pending_orders()` 구현
- [ ] 이벤트 발행 (OrderCreatedEvent)

**파일:** `src/stock_manager/service_layer/order_service_impl.py`

**의존성:** Task 1.2, Task 1.3
**담당:** 1개발자
**예상 시간:** 8시간

**테스트:**
- [ ] 주문 생성 성공 테스트
- [ ] idempotency_key 중복 방지 테스트
- [ ] 주문 조회 테스트

---

### Phase 2: 주문 전송 및 체결 처리 (Week 2)

#### Task 2.1: 주문 전송 구현
- [ ] `send_order()` 구현
- [ ] BrokerPort.place_order() 호출
- [ ] broker_order_id 저장
- [ ] 주문 상태 업데이트 (NEW → SENT)
- [ ] DB 트랜잭션 내에서 실행

**파일:** `src/stock_manager/service_layer/order_service_impl.py` (추가)

**의존성:** Task 1.4, SPEC-BACKEND-API-001 완료
**담당:** 1개발자
**예상 시간:** 8시간

**테스트:**
- [ ] 주문 전송 성공 테스트
- [ ] 브로커 오류 시 주문 상태 ERROR 테스트
- [ ] DB 트랜잭션 실패 시 롤백 테스트

---

#### Task 2.2: 체결 처리 구현
- [ ] `process_fill()` 구현
- [ ] FillEvent 파싱
- [ ] fills 테이블에 체결 레코드 생성
- [ ] 체결 누적 계산
- [ ] 주문 상태 업데이트 (SENT → PARTIAL 또는 FILLED)
- [ ] 포지션 업데이트 트리거

**파일:** `src/stock_manager/service_layer/order_service_impl.py` (추가)

**의존성:** Task 2.1, Task 3.1
**담당:** 1개발자
**예상 시간:** 10시간

**테스트:**
- [ ] 체결 레코드 생성 테스트
- [ ] 체결 누적 시 주문 상태 PARTIAL → FILLED 테스트
- [ ] 일부 체결 시 주문 상태 PARTIAL 테스트
- [ ] 포지션 업데이트 트리거 테스트

---

### Phase 3: 포지션 관리 (Week 2)

#### Task 3.1: PositionService 인터페이스 및 구현
- [ ] `service_layer/position_service.py` 생성
- [ ] PositionService 인터페이스 정의
- [ ] PositionRepository 구현 (CRUD)
- [ ] `calculate_position()` 구현 (전체 체결 기록 조회 후 계산)
- [ ] `update_position()` 구현 (체결 발생 시 업서트)
- [ ] `get_position()`, `get_all_positions()` 구현

**파일:**
- `src/stock_manager/service_layer/position_service.py`
- `src/stock_manager/adapters/storage/position_repository.py`

**의존성:** Task 1.3
**담당:** 1개발자
**예상 시간:** 8시간

**테스트:**
- [ ] 포지션 계산 테스트 (매수 체결, 매도 체결)
- [ ] 평균가 계산 테스트
- [ ] 포지션 업서트 테스트

---

#### Task 3.2: 포지션 계산 로직
- [ ] 수량 계산: total_qty = sum(buy_qty) - sum(sell_qty)
- [ ] 평균가 계산: weighted average by fill price
- [ ] 롱/숏 상태 판별
- [ ] 포지션 수량 0 시 평균가 초기화

**파일:** `src/stock_manager/service_layer/position_service.py` (추가)

**의존성:** Task 3.1
**담당:** 1개발자
**예상 시간:** 6시간

**테스트:**
- [ ] 단일 매수 체결 시 포지션 계산 테스트
- [ ] 여러 매수 체결 시 평균가 계산 테스트
- [ ] 매수/매도 체결 혼합 시 포지션 계산 테스트
- [ ] 전량 매도 시 포지션 수량 0 테스트

---

### Phase 4: 리스크 검증 및 주문 취소 (Week 3)

#### Task 4.1: 리스크 검증 통합
- [ ] RiskService 인터페이스 정의
- [ ] 리스크 검증 로직 구현 (일 손실 한도, 종목별 노출, 총 포지션 수)
- [ ] OrderService.create_order()에 리스크 검증 추가
- [ ] 리스크 위반 시 주문 상태 REJECTED
- [ ] RiskViolationEvent 발행

**파일:** `src/stock_manager/service_layer/risk_service.py`

**의존성:** Task 1.4
**담당:** 1개발자
**예상 시간:** 10시간

**테스트:**
- [ ] 리스크 통과 시 주문 전송 테스트
- [ ] 리스크 위반 시 주문 거부 테스트
- [ ] 리스크 위반 시 주문 상태 REJECTED 테스트

---

#### Task 4.2: 주문 취소 구현
- [ ] `cancel_order()` 구현
- [ ] BrokerPort.cancel_order() 호출
- [ ] 주문 상태 업데이트 (SENT → CANCELED)
- [ ] 이미 체결된 주문 취소 실패 처리
- [ ] OrderCanceledEvent 발행

**파일:** `src/stock_manager/service_layer/order_service_impl.py` (추가)

**의존성:** Task 2.1
**담당:** 1개발자
**예상 시간:** 6시간

**테스트:**
- [ ] 주문 취소 성공 테스트
- [ ] 이미 체결된 주문 취소 실패 테스트
- [ ] 취소 시 주문 상태 CANCELED 테스트

---

### Phase 5: 상태 동기화 및 테스트 (Week 3-4)

#### Task 5.1: 상태 동기화 로직
- [ ] `sync_order_status()` 구현
- [ ] DB 주문 상태와 브로커 주문 상태 비교
- [ ] 브로커 상태 우선 적용
- [ ] DB 상태 업데이트
- [ ] StateSyncEvent 발행

**파일:** `src/stock_manager/service_layer/order_service_impl.py` (추가)

**의존성:** Task 2.2, SPEC-BACKEND-API-001 완료
**담당:** 1개발자
**예상 시간:** 8시간

**테스트:**
- [ ] DB 상태와 브로커 상태 동일 시 동기화 안 함 테스트
- [ ] DB 상태와 브로커 상태 다르면 동기화 테스트
- [ ] 브로커 상태 FILLED, DB 상태 PARTIAL 시 동기화 테스트

---

#### Task 5.2: 단위 테스트 작성
- [ ] OrderService 테스트 (Task 1.4, 2.1, 2.2, 4.2, 5.1)
- [ ] PositionService 테스트 (Task 3.1, 3.2)
- [ ] RiskService 테스트 (Task 4.1)
- [ ] OrderRepository 테스트 (Task 1.3)
- [ ] PositionRepository 테스트 (Task 3.1)

**파일:**
- `tests/unit/test_order_service.py`
- `tests/unit/test_position_service.py`
- `tests/unit/test_risk_service.py`
- `tests/unit/test_order_repository.py`
- `tests/unit/test_position_repository.py`

**의존성:** Phase 1-4 완료
**담당:** 1개발자
**예상 시간:** 20시간

---

#### Task 5.3: 통합 테스트 작성
- [ ] 전체 주문 흐름 테스트 (생성 → 전송 → 체결 → 포지션)
- [ ] idempotency_key 중복 방지 통합 테스트
- [ ] 리스크 위반 통합 테스트
- [ ] 상태 동기화 통합 테스트

**파일:** `tests/integration/test_order_flow.py`

**의존성:** Task 5.2
**담당:** 1개발자
**예상 시간:** 12시간

---

#### Task 5.4: 커버리지 확인 및 리팩터링
- [ ] pytest-cov 설정
- [ ] 최소 70% 커버리지 확인
- [ ] 미달 시 추가 테스트 작성
- [ ] 코드 리팩터링 (중복 제거, 가독성 개선)

**명령:** `pytest --cov=src/stock_manager/service_layer --cov-report=html`

**의존성:** Task 5.3
**담당:** 1개발자
**예상 시간:** 8시간

---

#### Task 5.5: 문서화
- [ ] README 작성 (사용법, 예시)
- [ ] API 문서 작성 (메서드별 설명)
- [ ] 상태 전이 다이어그램 작성

**파일:** `src/stock_manager/service_layer/README.md`

**의존성:** Task 5.4
**담당:** 1개발자
**예상 시간:** 4시간

---

## 4. 리소스 요구사항

| 리소스 | 양 | 설명 |
|--------|------|------|
| 개발자 | 1명 | Python, ORM, 트랜잭션 경험 |
| 기간 | 4주 | Phase 1-5 순차 진행 |
| 환경 | Python 3.13, PostgreSQL 15+ | 개발/테스트 환경 |
| 의존 | SPEC-BACKEND-API-001 완료 | BrokerPort 구현 필요 |

---

## 5. 타임라인

| 주차 | Phase | 주요 목표 |
|------|-------|-----------|
| Week 1 | Phase 1 | 주문 서비스 기본 구현 완료 |
| Week 2 | Phase 2-3 | 주문 전송, 체결 처리, 포지션 관리 완료 |
| Week 3 | Phase 4 | 리스크 검증, 주문 취소, 상태 동기화 완료 |
| Week 4 | Phase 5 | 테스트, 리팩터링, 문서화 완료 |

---

## 6. 위험 분석 및 완화

| 위험 | 영향 | 확률 | 완화 전략 |
|------|------|------|-----------|
| DB 트랜잭션 복잡성 | HIGH | MEDIUM | 명확한 트랜잭션 경계, 롤백 테스트 |
| idempotency_key 충돌 | MEDIUM | LOW | UUID v4 사용, UNIQUE 제약 |
| 포지션 계산 오류 | HIGH | LOW | 단위 테스트 충분 작성 |
| 동시성 이슈 | MEDIUM | MEDIUM | row-level lock, 트랜잭션 격리 수준 |
| 브로커 통신 실패 | HIGH | HIGH | 에러 처리, 재시도 로직, 상태 동기화 |

---

## 7. 성공 기준

- [ ] OrderService가 OrderServicePort 인터페이스를 완전히 구현
- [ ] PositionService가 PositionServicePort 인터페이스를 완전히 구현
- [ ] idempotency_key 중복 방지 기능 동작
- [ ] 주문 생성/전송/상태 추적 정상
- [ ] 체결 처리 및 포지션 업데이트 정상
- [ ] 리스크 검증 통합 기능 동작
- [ ] 주문 취소 기능 동작
- [ ] 상태 동기화 기능 동작
- [ ] 단위 테스트 커버리지 70% 이상
- [ ] 통합 테스트 전체 흐름 정상
- [ ] 문서화 완료
