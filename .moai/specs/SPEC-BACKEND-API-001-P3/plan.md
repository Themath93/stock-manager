# Implementation Plan: SPEC-BACKEND-API-001-P3

## 개요

본 문서는 SPEC-BACKEND-API-001-P3 (KISBrokerAdapter 구현 완료)의 구현 계획을 정의합니다. 우선순위 기반 마일스톤과 기술 접근 방식을 제공합니다.

---

## 마일스톤 (Priority-Based)

### Primary Goal (최우선)

**Milestone 1: account_id 저장 및 cancel_order 완성**

구현 파일:
- `src/stock_manager/adapters/broker/kis/kis_broker_adapter.py`
- `src/stock_manager/service_layer/order_service.py`
- `src/stock_manager/config/app_config.py`

작업 내용:

1. **AppConfig.account_id 추가**
   - AppConfig Pydantic 모델에 account_id 필드 추가
   - 환경 변수 ACCOUNT_ID 로드
   - 검증: account_id는 10자리 숫자여야 함

2. **KISBrokerAdapter.__init__ 수정**
   - account_id 파라미터 추가
   - account_id 검증 (None 또는 빈 문자열인 경우 ValueError)
   - self.account_id 인스턴스 변수 저장

3. **KISBrokerAdapter.cancel_order 완성**
   - TODO 코멘트 제거
   - self.account_id 사용하여 rest_client.cancel_order() 호출
   - 에러 처리: APIError 캐치 후 False 반환
   - 로깅: 취소 성공/실패 로그 추가

4. **OrderService._to_broker_order_request 수정**
   - 하드코딩된 "0000000000" 제거
   - self.config.account_id 사용 (OrderService는 AppConfig 주입)

완료 기준:
- [x] AppConfig에 account_id 필드 정의
- [x] KISBrokerAdapter 생성자에 account_id 파라미터 추가
- [x] cancel_order 메서드에서 self.account_id 사용
- [x] TODO 코멘트 모두 제거
- [x] 단위 테스트 통과 (account_id 관련)

**Milestone 1 완료 알림**: 2026-01-27 기준으로 모든 완료 기준 충족. 다음 Milestone 2(통합 테스트 작성)로 진행 예정.

의존성:
- KISRestClient.cancel_order(broker_order_id, account_id) 이미 구현됨
- AppConfig는 이미 Pydantic v2.9 기반으로 구현됨

---

### Secondary Goal (차순위)

**Milestone 2: 통합 테스트 작성**

구현 파일:
- `tests/integration/test_kis_broker_adapter.py`

작업 내용:

1. **테스트 환경 설정**
   - Mock KIS API 응답 (httpx.MockTransport)
   - Mock WebSocket 연결
   - 테스트용 계좌 ID 설정

2. **생명주기 테스트**
   - authenticate() → 토큰 발급 검증
   - place_order() → broker_order_id 반환 검증
   - cancel_order() → 성공/실패 케이스 검증
   - get_orders(), get_cash(), get_stock_balance() → 데이터 반환 검증

3. **WebSocket 테스트**
   - connect_websocket() → 연결 성공 검증
   - subscribe_quotes() → 콜백 등록 검증
   - subscribe_executions() → 체결 이벤트 수신 검증
   - disconnect_websocket() → 연결 종료 검증

4. **에러 케이스 테스트**
   - 잘못된 broker_order_id로 cancel_order() → False 반환
   - API 401 에러 → 토큰 자동 갱신 후 재시도
   - WebSocket 연결 실패 → 재연결 시도

완료 기준:
- [ ] 최소 10개 통합 테스트 케이스 작성
- [ ] 모든 정상 케이스 통과
- [ ] 모든 에러 케이스 통과
- [ ] 테스트 커버리지 85% 이상

의존성:
- Milestone 1 완료 필요
- pytest, pytest-asyncio 필요
- docker-compose PostgreSQL 필요 (다른 테스트에서 이미 사용 중)

---

### Final Goal (최종)

**Milestone 3: 문서화 및 코드 정리**

구현 파일:
- `README.md`
- `docs/architecture/broker-adapter.md` (신규)

작업 내용:

1. **README 업데이트**
   - SPEC-BACKEND-API-001 상태: 85% → 100% 완료로 업데이트
   - Phase 3 완료 작업 목록 추가
   - 사용 예제 코드 추가

2. **아키텍처 문서 작성**
   - KISBrokerAdapter 구조 설명
   - 데이터 흐름 다이어그램
   - WebSocket 연결 관리 방식

3. **코드 정리**
   - 모든 TODO 제거
   - 타입 힌트 추가 (typing 완료도 100%)
   - 에러 메시지 개선
   - 로깅 레벨 조정

4. **TRUST 5 준수 확인**
   - Tested: 단위 테스트, 통합 테스트 통과
   - Readable: ruff linter 통과
   - Unified: black formatter 통과
   - Secured: account_id, approval_key 마스킹 확인
   - Trackable: Git 커밋 메시지 규칙 준수

완료 기준:
- [ ] README Phase 3 상태 업데이트
- [ ] 아키텍처 문서 작성
- [ ] TODO 검색 결과 0개
- [ ] ruff, black 통과
- [ ] TRUST 5 점수 90% 이상

의존성:
- Milestone 1, 2 완료 필요

---

## 기술 접근 방식 (Technical Approach)

### 아키텍처 패턴

**Port/Adapter Pattern (Hexagonal Architecture)**

```
┌─────────────────────────────────────────────────────────────┐
│                   Application Layer                          │
│                    (OrderService)                            │
└─────────────────────────────┬───────────────────────────────┘
                              │ Port Interface
                              │ (BrokerPort)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Adapter Layer                           │
│                   (KISBrokerAdapter)                         │
│  ┌──────────────────┐          ┌──────────────────┐        │
│  │  KISRestClient   │          │KISWebSocketClient│        │
│  └──────────────────┘          └──────────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

**Why Port/Adapter?**
- 서비스 로직을 브로커 구현으로부터 분리
- MockBrokerAdapter로 쉬운 테스트 가능
- 다른 브로커로 교체 시 최소한의 변경

### 의존성 주입 (Dependency Injection)

**OrderService 초기화**

```python
# app_factory.py
from stock_manager.config.app_config import AppConfig
from stock_manager.adapters.broker.kis.kis_broker_adapter import KISBrokerAdapter
from stock_manager.adapters.broker.kis.kis_config import KISConfig
from stock_manager.service_layer.order_service import OrderService

def create_order_service(config: AppConfig) -> OrderService:
    """OrderService 팩토리 함수"""

    # KIS 설정 로드
    kis_config = KISConfig(
        app_key=config.kis_app_key,
        app_secret=config.kis_app_secret,
        mode=config.mode,  # LIVE or PAPER
    )

    # 브로커 어댑터 생성
    broker_adapter = KISBrokerAdapter(
        config=kis_config,
        account_id=config.account_id,  # NEW (Phase 3)
    )

    # 주문 서비스 생성
    return OrderService(
        broker=broker_adapter,
        db_connection=config.db_connection,
    )
```

**Advantages:**
- 느슨한 결합: OrderService는 KISBrokerAdapter 구현을 알 필요 없음
- 테스트 가능성: MockBrokerAdapter로 쉽게 교체
- 설정 중앙화: AppConfig에서 모든 설정 관리

### 동시성 제어 (Concurrency Control)

**Thread Safety Guarantees**

1. **TokenManager 스레드 안전성**
   - threading.Lock으로 토큰 갱신 보호
   - 이미 완성됨 (Phase 2)

2. **WebSocket 콜백 스레드**
   - KISWebSocketClient는 별도 스레드에서 메시지 수신
   - 콜백 실행은 동기식 (blocking)
   - 서비스 레이어는 콜백에서 DB 접근 시 주의 필요

3. **KISBrokerAdapter 상태**
   - _initialized 플래그: bool 원자적 업데이트 (Python GIL 보호)
   - _approval_key: 초기화 후 읽기 전용 (불변)
   - account_id: 초기화 후 읽기 전용 (불변)

**Thread Safety Strategy:**
- 쓰기 가능한 상태 최소화 (_initialized만 변경)
- 읽기 전용 데이터는 불변으로 취급
- REST API 호출은 httpx가 스레드 안전성 보장

### 에러 처리 전략 (Error Handling Strategy)

**예외 계층 구조**

```
Exception
├── BrokerError (base)
│   ├── AuthenticationError (토큰, approval_key 실패)
│   ├── ConnectionError (WebSocket 연결 실패)
│   ├── APIError (KIS API 4xx, 5xx 에러)
│   └── RateLimitError (429 Too Many Requests)
```

**에러 처리 규칙**

1. **KISBrokerAdapter 레벨**
   - KIS API 에러를 BrokerPort 예외로 변환
   - 로깅: 에러 컨텍스트 포함
   - 서비스 레이어로 전파: 주요 에러만

2. **OrderService 레벨**
   - BrokerError를 처리하여 비즈니스 로직 보호
   - OrderError로 래핑하여 도메인 에러로 변환
   - 사용자에게 적절한 피드백 제공

3. **에러 복구**
   - AuthenticationError: 토큰 자동 갱신 후 재시도
   - RateLimitError: 지수 백오프 후 재시도
   - ConnectionError: WebSocket 재연결 시도

---

## 위험 및 완화 계획 (Risks and Mitigation)

### 기술적 위험

**Risk 1: account_id 환경 변수 누락**
- **확률**: MEDIUM
- **영향**: HIGH (런타임 실패)
- **완화**:
  - AppConfig에서 account_id 필수 필드로 정의
  - 초기화 시 ValueError 발생 (Fail-fast)
  - .env.example에 ACCOUNT_ID 추가

**Risk 2: WebSocket 재연결 시 구독 손실**
- **확률**: LOW (KISWebSocketClient 이미 구현됨)
- **영향**: MEDIUM (실시간 데이터 누락)
- **완화**:
  - KISWebSocketClient._reconnect_with_backoff()가 구독 복구
  - 테스트로 재연결 시나리오 검증

**Risk 3: KIS API rate limit 초과**
- **확률**: LOW (일일 100건 가정)
- **영향**: MEDIUM (주문 지연)
- **완화**:
  - KISRestClient에 이미 재시도 로직 구현됨
  - 주문 빈도 모니터링 로직 고려 (추후)

**Risk 4: 스레드 안전성 위반**
- **확률**: LOW (대부분 읽기 전용 상태)
- **영향**: HIGH (데이터 레이스, 크래시)
- **완화**:
  - 읽기 전용 데이터 불변성 유지
  - pytest-asyncio로 비동기 테스트
  - 다중 스레드 스트레스 테스트

### 운영적 위험

**Risk 5: 모의투자 계좌 부족**
- **확률**: MEDIUM
- **영향**: MEDIUM (통합 테스트 불가)
- **완화**:
  - MockBrokerAdapter로 대부분 테스트
  - KIS API 모의투자 환경 사용 가능 시 일부 실제 테스트

**Risk 6: PROD 환경 설정 실수**
- **확률**: LOW
- **영향**: CRITICAL (실전 주문 오류)
- **완화**:
  - MODE 환경 변수 강제 (PAPER 기본값)
  - LIVE 모드 시 추가 확인 절차
  - Slack 알림으로 LIVE 모드 전파

---

## 품질 계획 (Quality Plan)

### TRUST 5 Framework

**Tested (테스트)**
- 목표: 85% 커버리지
- 단위 테스트: KISBrokerAdapter 메서드별
- 통합 테스트: 전체 주문 생명주기
- 테스트 도구: pytest, pytest-asyncio, pytest-cov

**Readable (가독성)**
- ruff linter 통과
- 네이밍 컨벤션: PEP 8 준수
- 타입 힌트: 모든 함수/메서드
- 독스트링: Google 스타일

**Unified (일관성)**
- black formatter 적용
- import 정렬: isort
- 줄 길이: 100자 (프로젝트 표준)

**Secured (보안)**
- account_id 로그 시 마스킹: "123456****"
- approval_key 로그 시 마스킹: "abcd1234..."
- 환경 변수로 민감 정보 관리
- .env를 .gitignore에 등록

**Trackable (추적 가능성)**
- Git 커밋 메시지: Conventional Commits
- TAG 주석: 코드에 SPEC 태그 추가
- 이슈 추적: GitHub Issues 연동

### 정적 분석 (Static Analysis)

```bash
# ruff (linter)
ruff check src/stock_manager/adapters/broker/kis/

# black (formatter)
black --check src/stock_manager/adapters/broker/kis/

# mypy (type checker)
mypy src/stock_manager/adapters/broker/kis/
```

### 커버리지 목표

| 파일 | 목표 커버리지 | 현재 | 목표 |
|------|---------------|------|------|
| kis_broker_adapter.py | 90% | 0% | 90% |
| kis_rest_client.py | 85% | 85% | 유지 |
| kis_websocket_client.py | 85% | 80% | 85% |
| **전체** | **85%** | **85%** | **85%** |

---

## 다음 단계 (Next Steps)

### 1. SPEC 승인
- [ ] Stakeholder 리뷰 및 승인
- [ ] 일정 및 우선순위 확정

### 2. 구현 시작
```bash
# Phase 2 실행 (DDD 방식)
/moai:2-run SPEC-BACKEND-API-001-P3
```

### 3. 품질 검증
- [ ] 단위 테스트 통과
- [ ] 통합 테스트 통과
- [ ] TRUST 5 점수 90% 달성

### 4. 문서화
```bash
# Phase 3 실행 (문서화)
/moai:3-sync SPEC-BACKEND-API-001-P3
```

### 5. 배포
- [ ] Feature 브랜치 병합
- [ ] PROD 배포 (PAPER 모드 먼저)
- [ ] LIVE 모드 전환 (추후)

---

## 참고 (References)

### 구현 가이드

- [MoAI DDD 개발 방법론](https://github.com/moai-adk/moai-foundation-core)
- [TRUST 5 품질 프레임워크](https://github.com/moai-adk/moai-foundation-core)
- [Python 3.13 Best Practices](https://docs.python.org/3.13/)

### 관련 SPEC

- [SPEC-BACKEND-API-001](../SPEC-BACKEND-API-001/) - 부모 SPEC
- [SPEC-BACKEND-002](../SPEC-BACKEND-002/) - 주문 실행 시스템
