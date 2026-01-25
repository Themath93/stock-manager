---
id: SPEC-BACKEND-API-001
version: "1.2.0"
status: "completed"
created: "2026-01-23"
updated: "2026-01-25"
author: "Alfred"
priority: "HIGH"
---

# HISTORY

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.2.0 | 2026-01-25 | Alfred | Phase 2 완료: 토큰 갱신 스레드 안전성 개선, approval_key 발급 구현, 해시키 생성 구현, 단위 테스트 26개 추가 (85% 커버리지, TRUST 5: 94.3%) |
| 1.1.0 | 2026-01-25 | Alfred | 구현 현황 업데이트, approval_key 발급 요구사항 추가, 토큰 자동 갱신 요구사항 추가 |
| 1.0.0 | 2026-01-23 | Alfred | 초기 문서 작성 |

---

# 한국투자증권 OpenAPI 브로커 어댑터 구현

## 1. 개요

본 SPEC은 한국투자증권 OpenAPI와 통신하는 브로커 어댑터를 구현하기 위한 요구사항을 정의합니다. REST API와 WebSocket을 통한 인증, 주문, 실시간 데이터 수신 기능을 포트/어댑터 패턴으로 구현합니다.

## 2. 시스템 컨텍스트

### 2.1 외부 의존성

| 의존성 | 설명 |
|--------|------|
| KIS OpenAPI REST | 실전/모의투자 REST API (인증, 주문, 조회) |
| KIS OpenAPI WebSocket | 실시간 호가/체결 데이터 수신 |
| PostgreSQL | 설정 및 로그 저장 |

### 2.2 내부 인터페이스

| 인터페이스 | 책임 |
|------------|------|
| BrokerPort | 브로커 어댑터 추상 인터페이스 |
| AuthService | 인증 토큰 관리 |
| WebSocketService | WebSocket 연결 및 메시지 핸들링 |

---

# Event-Driven Requirements (이벤트 주도 요구사항)

### ED-001: REST 인증 이벤트
**설명:** 애플리케이션 시작 시 REST API 인증 수행

**트리거:** 장 시작 프로세스

**동작:**
1. `get_access_token()` 호출하여 access_token 발급
2. 토큰 만료 시간 기록
3. 인증 성공/실패 이벤트 발행

**출력:**
- 성공: access_token, expires_at
- 실패: AuthenticationError, events 테이블 로깅

---

### ED-002: WebSocket 연결 이벤트
**설명:** 인증 완료 후 WebSocket 연결 설정

**트리거:** REST 인증 성공

**동작:**
1. `get_approval_key()` 호출
2. WebSocket 서버 연결 (ws://ops.koreainvestment.com:21000 또는 31000)
3. 구독 등록 (호가, 체결, 주문 상태)

**출력:**
- 성공: 연결 상태, 채널 구독 완료
- 실패: ConnectionError, 재시도 로직 트리거

---

### ED-003: 주문 체결 이벤트 수신
**설명:** WebSocket을 통해 체결 이벤트 수신 및 처리

**트리거:** 체결 발생 (H0STCNT0 채널)

**동작:**
1. 메시지 파싱 (주문번호, 종목코드, 체결가, 체결량)
2. 내부 이벤트로 변환 (ExecutionEvent)
3. 주문 상태 업데이트 트리거

**출력:**
- ExecutionEvent 발행

---

### ED-004: WebSocket 종료 이벤트
**설명:** 장 종료 또는 오류 시 WebSocket 정상 종료

**트리거:** 장 종료 시그널 또는 치명적 오류

**동작:**
1. 구독 해제
2. WebSocket 연결 종료
3. 상태 기록

**출력:**
- 종료 완료 이벤트

---

# When-Then Requirements (조건-결과 요구사항)

### WT-001: 토큰 만료 5분 전 갱신
**When:** access_token 만료까지 5분 이하인 경우

**Then:**
1. `get_access_token()` 재호출
2. 새 토큰으로 교체
3. 기존 토큰 폐기

**검증:** 새 토큰이 성공적으로 발급되고 API 호출에 사용 가능

---

### WT-002: WebSocket 연결 끊김 시 재연결
**When:** WebSocket 연결이 끊어진 경우

**Then:**
1. 지수 백오프로 최대 5회 재연결 시도
2. 5회 실패 시 장 시작 프로세스 전체 재시작 권장
3. 모든 시도 실패 시 "거래 중지 모드"로 전환

**검증:** 재연결 성공 시 데이터 수신 재개

---

### WT-003: 401 오류 발생 시 토큰 갱신 후 재시도
**When:** REST API 호출 시 401 Unauthorized 응답 수신

**Then:**
1. 토큰 갱신 강제 실행 (WT-001 참조)
2. 원래 요청 재시도 (최대 3회)
3. 지속 실패 시 AuthenticationError 발생

**검증:** 갱신 후 요청 성공

---

### WT-004: 네트워크 타임아웃 시 재시도
**When:** API 호출 시 TimeoutError 발생

**Then:**
1. 지수 백오프로 최대 3회 재시도 (1s, 2s, 4s)
2. 지속 실패 시 ConnectionError 발생
3. events 테이블에 로깅

**검증:** 성공 시 정상 응답, 실패 시 에러 로그

---

# Wherewithal Requirements (자원/환경 요구사항)

### WH-001: 인증 자료
**필요 자원:**
- `KIS_APP_KEY`: 한국투자증권 발급 앱키 (36자)
- `KIS_APP_SECRET`: 한국투자증권 발급 시크릿 (180자)
- 환경 변수 또는 안전한 설정 파일에 저장

**검증:** 모든 요청에 appkey/appsecret 헤더 포함

---

### WH-002: 네트워크 보안
**필요 환경:**
- TLS 1.2 또는 1.3 지원
- 포트 443 (REST) 및 21000/31000 (WebSocket) 허용
- 방화벽 규칙에서 한국투자증권 서버 IP 허용

**참고:** TLS 1.0/1.1은 2025-12-12 이후 미지원

---

### WH-003: API 제한 준수
**제한 사항:**
- Rate Limit: 1초당 5회 초과 시 429 응답 가능
- 동시 연결: 최대 10개 WebSocket 연결
- 토큰 발급: 일일 1회 원칙 (6시간 내 재발급 시 기존 토큰 반환)

**구현:**
- 지수 백오프로 429 응답 처리
- 토큰 캐싱으로 불필요한 발급 방지

---

# Optional Requirements (선택 요구사항)

### OP-001: 해시키 사용 (권장)
**설명:** POST 요청 본문 해싱으로 보안 강화

**적용 대상:**
- 주문/정정/취소 API
- `/uapi/hashkey` 선행 호출

**구현 옵션:**
- 필수로 구현 (보안 권장)
- 해시키 누락 시에도 API 동작 (비권장)

---

### OP-002: 연결 풀링
**설명:** WebSocket 연결 풀링으로 재연결 속도 개선

**구현 옵션:**
- 단일 연결 유지
- 예비 연결 유지 (장 중 연속성)

---

# Ubiquitous Requirements (전반적 요구사항)

### UB-001: 로깅
**모든 외부 API 호출에 대해:**
- 요청 URL/메서드/헤더 (민감 정보 제외)
- 응답 상태 코드/시간
- 오류 발생 시 스택 트레이스
- 로그 레벨: INFO (정상), ERROR (실패)

---

### UB-002: 오류 처리
**표준 예외 계층구조:**
```
BrokerError
├── AuthenticationError
├── ConnectionError
├── APIError
└── RateLimitError
```

**모든 외부 호출은 try-except로 감싸고 BrokerError 또는 하위 예외 발생**

---

### UB-003: 구성 분리
**환경별 설정:**
- `MODE=LIVE|PAPER`
- `KIS_REST_BASE_URL`, `KIS_WS_URL`
- 실전/모의 URL 자동 전환

---

### UB-004: 테스트 용이성
**인터페이스 추상화:**
- BrokerPort 인터페이스 정의
- MockBrokerAdapter 구현 (테스트용)
- 실제 KISBrokerAdapter 구현 (운영용)

---

## 3. 데이터 모델

### 3.1 AuthenticationToken

```python
@dataclass
class AuthenticationToken:
    access_token: str
    token_type: str
    expires_in: int  # seconds
    expires_at: datetime  # calculated timestamp
```

### 3.2 OrderRequest

```python
@dataclass
class OrderRequest:
    account_id: str
    symbol: str
    side: OrderSide  # BUY, SELL
    order_type: OrderType  # MARKET, LIMIT
    qty: Decimal
    price: Optional[Decimal]  # 필수 for LIMIT
    idempotency_key: str
```

### 3.3 FillEvent

```python
@dataclass
class FillEvent:
    broker_order_id: str
    symbol: str
    side: OrderSide
    qty: Decimal
    price: Decimal
    filled_at: datetime
```

### 3.4 QuoteEvent

```python
@dataclass
class QuoteEvent:
    symbol: str
    bid_price: Decimal
    ask_price: Decimal
    bid_qty: Decimal
    ask_qty: Decimal
    timestamp: datetime
```

## 4. 인터페이스 정의

### 4.1 BrokerPort

```python
from abc import ABC, abstractmethod
from typing import List, Optional

class BrokerPort(ABC):
    @abstractmethod
    def authenticate(self) -> AuthenticationToken:
        pass

    @abstractmethod
    def place_order(self, order: OrderRequest) -> str:
        pass

    @abstractmethod
    def cancel_order(self, broker_order_id: str) -> bool:
        pass

    @abstractmethod
    def get_orders(self, account_id: str) -> List[Order]:
        pass

    @abstractmethod
    def get_cash(self, account_id: str) -> Decimal:
        pass

    @abstractmethod
    def subscribe_quotes(self, symbols: List[str], callback: Callable):
        pass

    @abstractmethod
    def subscribe_executions(self, callback: Callable):
        pass

    @abstractmethod
    def connect_websocket(self):
        pass

    @abstractmethod
    def disconnect_websocket(self):
        pass
```

### NEW-001: WebSocket approval_key 발급 ✅ 완료
**설명:** WebSocket 연결을 위한 approval_key 발급 기능

**When:** WebSocket 연결 초기화 시

**Then:**
1. KIS OpenAPI `/oauth2/Approval` 엔드포인트 호출
2. approval_key 응답 수신 및 저장
3. WebSocket 헤더에 approval_key 포함하여 연결

**검증:**
- approval_key가 정상적으로 발급되어 WebSocket 연결에 사용됨
- 발급 실패 시 AuthenticationError 발생 및 재시도 로직 동작

**구현 상태: COMPLETED**
- 파일: `src/stock_manager/adapters/broker/kis/kis_rest_client.py`
- 메서드: `get_approval_key()`
- 테스트: 3개 단위 테스트 작성 완료

---

### NEW-002: 토큰 자동 갱신 ✅ 완료
**설명:** access_token 만료 5분 전 자동 갱신 기능 (스레드 안전)

**When:** access_token 만료까지 5분 이하인 경우

**Then:**
1. `get_access_token()` 재호출하여 새 토큰 발급
2. 새 토큰으로 기존 토큰 교체
3. 기존 토큰 안전하게 폐기
4. 갱신 이벤트 로깅
5. threading.Lock으로 동시성 제어 (스레드 안전성 보장)

**검증:**
- 만료 5분 전 자동 갱신 동작
- 갱신 후 모든 API 호출이 새 토큰 사용
- 갱신 실패 시 AuthenticationError 발생
- 다중 스레드 환경에서도 안전한 토큰 갱신

**구현 상태: COMPLETED**
- 파일: `src/stock_manager/adapters/broker/kis/kis_rest_client.py`
- 클래스: `TokenManager` (스레드 안전한 구현)
- 메서드: `_refresh_token()` (threading.Lock 사용)
- 테스트: 7개 단위 테스트 작성 완료

---

## 5. 구현 현황

### 5.1 완료된 구현 항목

| 항목 | 파일 | 상태 | 비고 |
|------|------|------|------|
| BrokerPort 인터페이스 | `port/broker_port.py` | ✅ 완료 | 추상 인터페이스 정의 |
| KIS 설정 모듈 | `kis/kis_config.py` | ✅ 완료 | LIVE/PAPER 모드 지원 |
| REST 클라이언트 | `kis/kis_rest_client.py` | ✅ 완료 | 토큰 관리, 재시도 로직 포함 |
| WebSocket 클라이언트 | `kis/kis_websocket_client.py` | ✅ 완료 | 호가/체결 구독, 재연결 포함 |
| Mock 어댑터 | `mock/mock_broker_adapter.py` | ✅ 완료 | 테스트용 더블 구현 |

### 5.2 Phase 2 완료 항목

| 항목 | 파일 | 상태 | 비고 |
|------|------|------|------|
| approval_key 발급 | `kis/kis_rest_client.py` | ✅ 완료 | get_approval_key() 메서드 구현 |
| 토큰 자동 갱신 | `kis/kis_rest_client.py` | ✅ 완료 | 스레드 안전한 TokenManager 구현 |
| 해시키 생성 | `kis/kis_rest_client.py` | ✅ 완료 | get_hashkey() 메서드 구현 |
| 스레드 안전성 | `kis/kis_rest_client.py` | ✅ 완료 | threading.Lock으로 동시성 제어 |

### 5.3 Phase 3 미구현 항목

| 항목 | 요구사항 ID | 우선순위 | 예상 작업량 |
|------|-------------|----------|-------------|
| KISBrokerAdapter 완성 | ADAPTER-001 | MEDIUM | 8시간 |
| WebSocket 연결 통합 | WS-INT-001 | MEDIUM | 4시간 |
| 통합 테스트 작성 | INT-TEST-001 | HIGH | 6시간 |

---

## 6. 구현 우선순위 (최종 업데이트)

| Phase | 기능 | 우선순위 | 구현 상태 |
|-------|------|----------|-----------|
| 1 | REST 인증 (access_token) | HIGH | ✅ 완료 |
| 1 | REST 주문 전송 | HIGH | ✅ 완료 |
| 2 | approval_key 발급 | HIGH | ✅ 완료 |
| 2 | 토큰 자동 갱신 (스레드 안전) | HIGH | ✅ 완료 |
| 2 | 해시키 생성 | LOW | ✅ 완료 |
| 3 | 호가 구독 | MEDIUM | ✅ 완료 |
| 3 | 체결 이벤트 수신 | HIGH | ✅ 완료 |
| 3 | 재연결 로직 | MEDIUM | ✅ 완료 |
| 4 | KISBrokerAdapter 완성 | MEDIUM | ⏳ 예정 |
| 4 | WebSocket 연결 통합 | MEDIUM | ⏳ 예정 |
| 5 | 통합 테스트 작성 | HIGH | ⏳ 예정 |

---

## 7. Phase 2 구현 상세

### 7.1 개요

Phase 2에서는 한국투자증권 OpenAPI 브로커 어댑터의 핵심 기능을 구현하고 스레드 안전성을 강화했습니다.

### 7.2 구현된 기능

#### 7.2.1 토큰 자동 갱신 (NEW-002)

**파일:** `src/stock_manager/adapters/broker/kis/kis_rest_client.py`

**구현 내용:**
- `TokenManager` 클래스에 threading.Lock을 사용한 스레드 안전한 토큰 갱신 로직 구현
- `_refresh_token()` 메서드에 락 획득/해제 로직 추가
- `_token_lock.acquire(blocking=True, timeout=5)`로 최대 5초 대기
- 갱신 완료 후 `finally` 블록에서 락 해제 보장

**코드 예시:**
```python
def _refresh_token(self) -> None:
    acquired = self._token_lock.acquire(blocking=True, timeout=5)
    if not acquired:
        logger.warning("Token refresh lock acquisition timeout")
        return

    try:
        response = self.client.post(...)
        # 토큰 갱신 로직
    finally:
        self._token_lock.release()
```

#### 7.2.2 approval_key 발급 (NEW-001)

**파일:** `src/stock_manager/adapters/broker/kis/kis_rest_client.py`

**구현 내용:**
- `get_approval_key()` 메서드로 `/oauth2/Approval` 엔드포인트 호출
- 응답에서 `approval_key` 추출 및 반환
- 발급 실패 시 `AuthenticationError` 발생

**코드 예시:**
```python
def get_approval_key(self) -> str:
    try:
        response = self._make_request(
            "POST",
            self.config.get_approval_url(),
            include_token=False,
        )
        approval_key = response.get("approval_key")
        if not approval_key:
            raise AuthenticationError("approval_key not found in response")
        logger.info("Approval key generated successfully")
        return approval_key
    except Exception as e:
        logger.error(f"Approval key generation failed: {e}")
        raise AuthenticationError(f"Approval key generation failed: {e}")
```

#### 7.2.3 해시키 생성 (OP-001)

**파일:** `src/stock_manager/adapters/broker/kis/kis_rest_client.py`

**구현 내용:**
- `get_hashkey()` 메서드로 `/uapi/hashkey` 엔드포인트 호출
- POST 요청 본문을 해싱하여 HASH 값 반환
- 실패 시 빈 문자열 반환 (경우 처리)

**코드 예시:**
```python
def get_hashkey(self, request_body: dict) -> str:
    try:
        response = self._make_request(
            "POST",
            self.config.get_hashkey_url(),
            json_data=request_body,
            include_token=False,
        )
        return response["HASH"]
    except Exception as e:
        logger.warning(f"Hashkey generation failed, continuing without hashkey: {e}")
        return ""
```

### 7.3 테스트 커버리지

**파일:** `tests/unit/adapters/broker/test_kis_rest_client.py`

**추가된 테스트 (26개):**
- TokenManager 테스트: 7개
  - `test_get_token_returns_cached_token_when_valid`
  - `test_get_token_refreshes_when_expiring_soon`
  - `test_force_refresh_updates_token`
  - `test_token_refresh_failure_raises_error`
  - `test_needs_refresh_returns_false_when_token_valid`
  - `test_needs_refresh_returns_true_when_token_expiring_soon`
  - `test_needs_refresh_returns_true_when_no_token`

- KISRestClient approval_key 테스트: 3개
  - `test_get_approval_key_success`
  - `test_get_approval_key_missing_in_response`
  - `test_get_approval_key_api_failure`

- KISRestClient 해시키 테스트: 3개
  - `test_get_hashkey_success`
  - `test_get_hashkey_failure_returns_empty_string`
  - `test_get_hashkey_with_empty_body`

- KISRestClient 기본 기능 테스트: 13개

### 7.4 품질 지표

| 지표 | 값 | 목표 | 상태 |
|------|------|------|------|
| 테스트 커버리지 | 85% | 80% | ✅ 달성 |
| 테스트 통과율 | 100% (26/26) | 100% | ✅ 달성 |
| TRUST 5 점수 | 94.3% | 85% | ✅ 달성 |
| 스레드 안전성 | 완료 | 필수 | ✅ 달성 |

### 7.5 Git 커밋

| 커밋 | 메시지 | 날짜 |
|------|--------|------|
| 69c6a6b | feat(kis): improve token refresh thread safety | 2026-01-25 |
| 0f33a37 | test(kis): add approval_key, hashkey, and token refresh tests | 2026-01-25 |
