---
id: SPEC-BACKEND-API-001
version: "1.0.0"
status: "draft"
created: "2026-01-23"
updated: "2026-01-23"
author: "Alfred"
priority: "HIGH"
---

# HISTORY

| Version | Date | Author | Changes |
|---------|------|--------|---------|
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

## 5. 구현 우선순위

| Phase | 기능 | 우선순위 |
|-------|------|----------|
| 1 | REST 인증 (access_token) | HIGH |
| 1 | REST 주문 전송 | HIGH |
| 2 | WebSocket 연결 (approval_key) | HIGH |
| 2 | 호가 구독 | MEDIUM |
| 3 | 체결 이벤트 수신 | HIGH |
| 4 | 해시키 생성 | LOW |
| 4 | 토큰 자동 갱신 | MEDIUM |
| 5 | 재연결 로직 | MEDIUM |
