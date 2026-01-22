# 구현 계획: 한국투자증권 OpenAPI 브로커 어댑터

## 1. 개요

본 계획은 SPEC-BACKEND-API-001의 구현을 위한 단계별 작업을 정의합니다. REST API, WebSocket, 인증 관리, 테스트 등 4단계로 구성됩니다.

---

## 2. 기술 스택

| 분류 | 기술 | 버전 | 설명 |
|------|------|------|------|
| 언어 | Python | 3.13+ | 타입 힌트, dataclass 활용 |
| HTTP 클라이언트 | requests | 2.31+ | REST API 호출 |
| WebSocket | websocket-client | 1.7+ | WebSocket 통신 |
| 로깅 | logging | stdlib | 표준 라이브러리 |
| 테스트 | pytest | 7.4+ | 단위/통합 테스트 |
| 테스트 더블 | pytest-mock | 3.12+ | Mock/patch 지원 |

---

## 3. 작업 분해

### Phase 1: REST API 인증 및 주문 (Week 1)

#### Task 1.1: 프로젝트 구조 설정
- [ ] `src/stock_manager/adapters/broker/` 디렉토리 생성
- [ ] `src/stock_manager/adapters/broker/kis/` 하위 디렉토리 생성
- [ ] `__init__.py` 파일 구성
- [ ] 모듈 임포트 경로 설정

**의존성:** 없음
**담당:** 1개발자
**예상 시간:** 2시간

---

#### Task 1.2: BrokerPort 인터페이스 정의
- [ ] `port/broker_port.py` 생성
- [ ] 인터페이스 메서드 정의 (authenticate, place_order, cancel_order 등)
- [ ] 데이터 모델 정의 (OrderRequest, AuthenticationToken, FillEvent)
- [ ] 타입 힌트 추가

**파일:** `src/stock_manager/adapters/broker/port/broker_port.py`

**의존성:** Task 1.1
**담당:** 1개발자
**예상 시간:** 4시간

---

#### Task 1.3: REST 인증 구현
- [ ] `kis/kis_rest_client.py` 생성
- [ ] `get_access_token()` 구현 (/oauth2/tokenP)
- [ ] `get_approval_key()` 구현 (/oauth2/Approval)
- [ ] `get_hashkey()` 구현 (/uapi/hashkey) - 선택사항
- [ ] 환경 변수 로딩 (KIS_APP_KEY, KIS_APP_SECRET)
- [ ] 인증 토큰 캐싱 로직

**파일:** `src/stock_manager/adapters/broker/kis/kis_rest_client.py`

**의존성:** Task 1.2
**담당:** 1개발자
**예상 시간:** 8시간

**테스트:**
- [ ] 인증 성공 시 토큰 반환 테스트
- [ ] 잘못된 자격증명 시 AuthenticationError 발생 테스트
- [ ] 토큰 만료 시간 계산 테스트

---

#### Task 1.4: REST 주문 전송 구현
- [ ] `place_order()` 구현 (/uapi/domestic-stock/v1/trading/order-cash)
- [ ] `cancel_order()` 구현 (/uapi/domestic-stock/v1/trading/order-rvsecnccl)
- [ ] `get_orders()` 구현 (미체결 주문 조회)
- [ ] `get_cash()` 구현 (예수금 조회)
- [ ] Hashkey 헤더 적용 (Task 1.3의 get_hashkey 활용)

**파일:** `src/stock_manager/adapters/broker/kis/kis_rest_client.py` (추가)

**의존성:** Task 1.3
**담당:** 1개발자
**예상 시간:** 12시간

**테스트:**
- [ ] 지정가 매수 주문 성공 테스트
- [ ] 시장가 매수 주문 성공 테스트
- [ ] 매도 주문 성공 테스트
- [ ] 주문 취소 성공 테스트
- [ ] 401 Unauthorized 시 토큰 갱신 후 재시도 테스트
- [ ] 429 Rate Limit 시 재시도 테스트

---

#### Task 1.5: 토큰 자동 갱신 로직
- [ ] 토큰 만료 5분 전 체크 로직
- [ ] `refresh_token_if_needed()` 메서드
- [ ] 401 오류 발생 시 강제 갱신 로직
- [ ] 갱신 실패 시 AuthenticationError 발생

**파일:** `src/stock_manager/adapters/broker/kis/kis_rest_client.py` (추가)

**의존성:** Task 1.4
**담당:** 1개발자
**예상 시간:** 6시간

**테스트:**
- [ ] 만료 10분 전 갱신 안 함 테스트
- [ ] 만료 4분 전 갱신 테스트
- [ ] 401 발생 시 갱신 테스트

---

### Phase 2: WebSocket 연결 (Week 2)

#### Task 2.1: WebSocket 클라이언트 구현
- [ ] `kis/kis_websocket_client.py` 생성
- [ ] `connect_websocket()` 구현
- [ ] `disconnect_websocket()` 구현
- [ ] 헤더 설정 (approval_key)
- [ ] 핑/퐁 메시지 처리 (연결 유지)

**파일:** `src/stock_manager/adapters/broker/kis/kis_websocket_client.py`

**의존성:** Task 1.3
**담당:** 1개발자
**예상 시간:** 8시간

**테스트:**
- [ ] 연결 성공 테스트
- [ ] 연결 종료 테스트
- [ ] 잘못된 approval_key 시 실패 테스트

---

#### Task 2.2: 호가 구독 구현
- [ ] `subscribe_quotes()` 구현
- [ ] 메시지 파싱 (H0STASP0 또는 H0UNASP0)
- [ ] QuoteEvent로 변환
- [ ] 콜백 함수 등록/해제

**파일:** `src/stock_manager/adapters/broker/kis/kis_websocket_client.py` (추가)

**의존성:** Task 2.1
**담당:** 1개발자
**예상 시간:** 6시간

**테스트:**
- [ ] 호가 메시지 수신 테스트
- [ ] 콜백 호출 테스트
- [ ] 다중 종목 구독 테스트

---

#### Task 2.3: 체결 이벤트 구독 구현
- [ ] `subscribe_executions()` 구현
- [ ] 메시지 파싱 (H0STCNT0 또는 H0UNCNT0)
- [ ] FillEvent로 변환
- [ ] 콜백 함수 등록/해제

**파일:** `src/stock_manager/adapters/broker/kis/kis_websocket_client.py` (추가)

**의존성:** Task 2.1
**담당:** 1개발자
**예상 시간:** 6시간

**테스트:**
- [ ] 체결 메시지 수신 테스트
- [ ] 콜백 호출 테스트
- [ ] 여러 체결 메시지 순차 수신 테스트

---

#### Task 2.4: 재연결 로직
- [ ] 연결 끊김 감지
- [ ] 지수 백오프 재연결 (1s, 2s, 4s, 8s, 16s)
- [ ] 최대 5회 재시도
- [ ] 실패 시 ConnectionError 발생
- [ ] events 테이블에 로깅

**파일:** `src/stock_manager/adapters/broker/kis/kis_websocket_client.py` (추가)

**의존성:** Task 2.3
**담당:** 1개발자
**예상 시간:** 6시간

**테스트:**
- [ ] 연결 끊김 시 1회 재연결 성공 테스트
- [ ] 연결 끊김 시 3회 재연결 성공 테스트
- [ ] 5회 실패 후 ConnectionError 발생 테스트

---

### Phase 3: 어댑터 통합 (Week 3)

#### Task 3.1: KISBrokerAdapter 구현
- [ ] `kis_broker_adapter.py` 생성
- [ ] BrokerPort 인터페이스 구현
- [ ] KISRestClient, KISWebSocketClient 통합
- [ ] 계정 설정 로딩 (MODE, REST_URL, WS_URL)

**파일:** `src/stock_manager/adapters/broker/kis/kis_broker_adapter.py`

**의존성:** Task 1.5, Task 2.4
**담당:** 1개발자
**예상 시간:** 8시간

**테스트:**
- [ ] 전체 흐름 통합 테스트 (인증 → 주문 → 체결 수신)
- [ ] 환경별 URL 전환 테스트 (LIVE/PAPER)

---

#### Task 3.2: MockBrokerAdapter 구현 (테스트용)
- [ ] `mock_broker_adapter.py` 생성
- [ ] BrokerPort 인터페이스 구현
- [ ] 인-메모리 상태 관리
- [ ] 콜백 시뮬레이션

**파일:** `src/stock_manager/adapters/broker/mock/mock_broker_adapter.py`

**의존성:** Task 1.2
**담당:** 1개발자
**예상 시간:** 4시간

**테스트:**
- [ ] Mock 동작 테스트
- [ ] 상태 일관성 테스트

---

#### Task 3.3: 로깅 구현
- [ ] BrokerAdapter 기본 로거 설정
- [ ] API 호출 로깅 (요청 URL, 응답 상태)
- [ ] 오류 로깅 (스택 트레이스)
- [ ] 민감 정보 마스킹 (appkey, appsecret, token)

**파일:** `src/stock_manager/adapters/broker/common/logging_config.py`

**의존성:** Task 3.1
**담당:** 1개발자
**예상 시간:** 4시간

---

### Phase 4: 테스트 및 문서화 (Week 4)

#### Task 4.1: 단위 테스트 작성
- [ ] 인증 모듈 테스트 (Task 1.3)
- [ ] 주문 모듈 테스트 (Task 1.4)
- [ ] 토큰 갱신 테스트 (Task 1.5)
- [ ] WebSocket 클라이언트 테스트 (Task 2.1-2.4)
- [ ] 어댑터 통합 테스트 (Task 3.1)

**파일:** `tests/unit/test_broker_adapter.py`, `tests/integration/test_kis_api.py`

**의존성:** Phase 1-3 완료
**담당:** 1개발자
**예상 시간:** 16시간

---

#### Task 4.2: 커버리지 확인
- [ ] pytest-cov 설정
- [ ] 최소 70% 커버리지 확인
- [ ] 미달 시 추가 테스트 작성

**명령:** `pytest --cov=src/stock_manager/adapters/broker --cov-report=html`

**의존성:** Task 4.1
**담당:** 1개발자
**예상 시간:** 4시간

---

#### Task 4.3: 문서화
- [ ] README 작성 (사용법, 환경 설정)
- [ ] API 문서 작성 (메서드별 설명)
- [ ] 테스트 예시 코드 작성

**파일:** `src/stock_manager/adapters/broker/README.md`

**의존성:** Task 4.1
**담당:** 1개발자
**예상 시간:** 4시간

---

## 4. 리소스 요구사항

| 리소스 | 양 | 설명 |
|--------|------|------|
| 개발자 | 1명 | Python, HTTP/WebSocket 경험 |
| 기간 | 4주 | Phase 1-4 순차 진행 |
| 환경 | Python 3.13, PostgreSQL 15+ | 개발/테스트 환경 |
| API 계정 | 1개 | 한국투자증권 모의투자 계정 |

---

## 5. 타임라인

| 주차 | Phase | 주요 목표 |
|------|-------|-----------|
| Week 1 | Phase 1 | REST 인증 및 주문 완료 |
| Week 2 | Phase 2 | WebSocket 연결 및 구독 완료 |
| Week 3 | Phase 3 | 어댑터 통합 완료 |
| Week 4 | Phase 4 | 테스트 및 문서화 완료 |

---

## 6. 위험 분석 및 완화

| 위험 | 영향 | 확률 | 완화 전략 |
|------|------|------|-----------|
| KIS API 변경 | HIGH | MEDIUM | 버전 관리, Mock 테스트 우선 |
| Rate Limit 초과 | MEDIUM | HIGH | 요청 속도 제한, 캐싱 활용 |
| WebSocket 연결 불안정 | HIGH | MEDIUM | 재연결 로직, 예비 연결 |
| 인증 토큰 만료 | MEDIUM | LOW | 자동 갱신 로직 |
| 네트워크 타임아웃 | MEDIUM | HIGH | 지수 백오프 재시도 |

---

## 7. 성공 기준

- [ ] KISBrokerAdapter가 BrokerPort 인터페이스를 완전히 구현
- [ ] REST 인증, 주문, 조회 모든 기능 동작
- [ ] WebSocket 연결, 호가/체결 수신 정상
- [ ] 토큰 자동 갱신, 재연결 로직 동작
- [ ] 단위 테스트 커버리지 70% 이상
- [ ] MockBrokerAdapter로 통합 테스트 가능
- [ ] 문서화 완료 및 예시 코드 제공
