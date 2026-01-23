# 자동매매 봇 개발 스펙 (Python 3.13 + PostgreSQL)

본 문서는 구현 수준의 상세 스펙을 정의한다. 계획서의 원칙을 유지하되, 실제 개발자가 바로 작업할 수 있도록 요구사항, 데이터 모델, 인터페이스, 상태 전이, 예외 정책을 구체화한다.

---

## 1. 범위 및 목표

- **범위**: 장 시작 초기화 → 상태 복구 → 장중 이벤트 기반 매매 → 주문/체결 기록 → 리스크 가드레일 적용.
- **목표**: 재시작/장애 상황에서도 동일 상태 복구 가능, 중복 주문 방지, 운영 안정성 확보.
- **AI 활용**: 전략 파라미터 생성 및 매매일지는 AI 배치 작업으로 작성하되 검증/승인 후 DB 반영.

---

## 2. 용어 정의

- **전략(Strategy)**: 신호 생성 로직. 주문을 직접 호출하지 않고 주문 의도를 반환.
- **실행(Execution)**: 주문 생성/전송/관리 및 리스크 검증 담당.
- **브로커(Broker)**: 한국투자증권 오픈API 같은 외부 주문/체결 시스템.
- **상태 복구(State Recovery)**: DB + 브로커 상태를 비교하여 현재 상태 스냅샷을 만드는 과정.
- **거래 중지(Stop Mode)**: 주문 전송을 차단하고 감시/기록만 수행.
- **관찰 모드(Observe Mode)**: 신호 계산은 하지만 주문은 전송하지 않음.
- **AI 배치(AI Jobs)**: 장 종료 후 매매일지 작성, 야간 전략 파라미터 생성과 같은 비실시간 작업.

---

## 3. 시스템 컨텍스트

- 입력: 실시간 시세, 주문/체결 이벤트, DB에 저장된 전략 파라미터.
- 출력: 주문 전송, 주문/체결 DB 기록, 운영 로그/이벤트.

외부 의존성:
- 한국투자증권 오픈API (브로커, REST + WebSocket)
  - 실전 REST: `https://openapi.koreainvestment.com:9443`
  - 실전 WebSocket: `ws://ops.koreainvestment.com:21000`
  - 모의 REST: `https://openapivts.koreainvestment.com:29443`
  - 모의 WebSocket: `ws://ops.koreainvestment.com:31000`
  - REST TLS: **1.2 / 1.3만 허용** (TLS 1.0/1.1은 2025-12-12 이후 미지원)
  - 인증: REST `access_token`, WebSocket `approval_key` 발급 필요
- PostgreSQL (상태 저장)
- AI 모델 API (전략/일지 생성 전용)

---

## 4. 기능 요구사항 (Functional Requirements)

### 4.1 장 시작 프로세스

1) 설정 로드 및 환경 검증
- `.env`/설정 파일 읽기
- 운영 모드(실계좌/모의) 확인

2) 로그인 및 세션 확인
- OAuth 토큰 발급(access_token)
- WebSocket 접속키 발급(approval_key)
- 결과 이벤트 수신
- 실패 시 N회 재시도 후 중지

3) 계좌/잔고/예수금 확인
- 계좌 리스트 확인
- 예수금 조회
- 권한 검증

4) 전략 파라미터 로드
- 오늘 날짜 + ACTIVE 파라미터 조회
- 없을 경우 정책 적용(기본 정책 확정 필요)

5) 상태 복구
- DB 미종결 주문 조회
- 브로커 주문 상태 조회
- 충돌 해결 및 동기화
- 포지션 재계산

6) 리스크 가드레일 초기화
- 일 손실 한도 / 종목별 노출 / 총 포지션 수

7) 유니버스 확정
- DB 저장 종목 리스트
  - 한국투자증권 종목정보 마스터파일 최신화 여부 확인(정기 업데이트 시간 반영)
  - 업데이트 시간(매일): 06:00, 06:55, 07:35, 07:55, 08:45, 09:46, 10:55, 17:10, 17:30, 17:55, 18:10, 18:30, 18:55

8) 실시간 이벤트 등록
- 체결, 주문 상태, 실시간 호가/체결 이벤트

### 4.2 장중 프로세스

- 실시간 이벤트 수신
- Market State 업데이트
- 전략 신호 계산
- 리스크 검증
- 주문 생성 및 전송
- 주문/체결 DB 기록
- 킬 스위치 조건 감시

---

## 5. 비기능 요구사항 (Non-Functional)

- **신뢰성**: 주문 상태는 DB 단일 원본으로 유지.
- **안전성**: 실패 시 항상 거래 중지 방향.
- **성능**: 실시간 이벤트 처리 지연 최소화.
- **추적성**: 모든 주문/체결/에러 이벤트 기록.
- **재시작 복구**: N초 내 상태 복구 가능.

---

## 6. 아키텍처 및 모듈 책임

### 6.1 포트/어댑터 구조

- **Domain**: 전략, 리스크, 주문 모델
- **Port**: 브로커 인터페이스, DB 인터페이스
- **Adapter**: 한국투자증권 오픈API 어댑터, PostgreSQL 어댑터

### 6.2 핵심 모듈 책임

- `domain/` : 전략/리스크/주문 모델 (순수 로직)
- `service_layer/` : 장 시작/복구/주문 실행 유스케이스
- `adapters/broker/` : 한국투자증권 REST/WS 연결
- `adapters/storage/` : DB CRUD, 트랜잭션 관리
- `adapters/notifications/` : Slack 등 알림
- `adapters/observability/` : logger/metrics
- `entrypoints/` : CLI/worker/scheduler
- `utils/` : 공통 유틸리티(로그, 시간, 검증)

### 6.3 알림(Slack) 유틸 규칙

- Slack 알림 구현 기준은 `ai_developer_guides/SLACK_NOTIFICATION_GUIDE.md`를 따른다.
- 채널은 **ID만 사용**하며 채널명 조회/변환은 금지한다.
- Slack 호출 실패는 예외 대신 결과 타입으로 반환하여 거래 흐름을 중단하지 않는다.

---

## 7. 데이터 모델 (PostgreSQL)

스키마/DDL의 **단일 기준**은 `ai_developer_guides/DB_SCHEMA_DDL.md`이다. 이 문서는 개념적 범위만 요약한다.

- Core: `strategies`, `strategy_params`, `orders`, `fills`, `positions`, `events`
- Optional(AI): `strategy_param_drafts`, `trade_journals`, `ai_job_runs`

---

## 8. 주문 상태 전이 규칙

- NEW → SENT → PARTIAL → FILLED
- NEW → SENT → CANCELED
- NEW → SENT → REJECTED
- 상태 전이는 **단방향**이며 되돌릴 수 없다.

---

## 9. Idempotency

- 주문 생성 시 `idempotency_key` 필수
- 동일 키로 재요청 시 기존 주문 반환
- 브로커 중복 호출 방지

---

## 10. 상태 복구 정책

1) DB 미종결 주문 조회
2) 브로커 주문 상태 조회
3) 충돌 해결 규칙
- 브로커 상태를 우선 기준으로 채택
- 차이가 발생한 주문은 `events` 기록
4) 포지션 재계산

---

## 11. 리스크 정책

- 일 손실 한도: 실현손익 기준 (기본)
- 종목별 최대 노출: 수량 기준 또는 평가금액 기준
- 총 포지션 수 제한
- 조건 위반 시 주문 전송 차단

---

## 12. 브로커 인터페이스 스펙

필수 메서드:
- `login()`
- `issue_access_token()`
- `issue_approval_key()`
- `get_accounts()`
- `get_cash(account_id)`
- `get_orders(account_id)`
- `place_order(order)`
- `cancel_order(broker_order_id)`
- `subscribe_quotes(symbols)`
- `subscribe_order_events()`

---

## 13. 설정 (.env)

- `MODE=LIVE|PAPER`
- `DB_URL=postgresql+psycopg://...`
- `KIS_APP_KEY` / `KIS_APP_SECRET`
- `KIS_REST_BASE_URL` / `KIS_WS_URL`
- `LOG_LEVEL=INFO`

---

## 14. 에러 처리 및 재시도

- 외부 API 호출 실패 → 최대 N회 재시도(지수 백오프)
- 복구 실패 → 거래 중지 모드 전환
- 모든 예외는 `events` 테이블 기록

---

## 15. 테스트 스펙

- 전략, 리스크: 순수 함수 단위 테스트
- DB/브로커: 통합 테스트 (Mock 어댑터)
- 상태 복구 로직: 시나리오 테스트
- 목표 커버리지: 핵심 모듈 70% 이상

---

## 16. 운영 및 배포

- 로컬: 단일 프로세스 실행
- 향후: Windows 서비스/스케줄러 등록
- 운영 로그: 일자별 롤링

---

## 17. AI 활용 가이드 참고

- AI의 적용 범위, 검증/승인 프로세스, 추천 테이블은 아래 문서를 따른다.
  - `ai_developer_guides/AI_USAGE_GUIDE.md`

---

## 18. 완료 기준(Definition of Done)

- 장 시작 → 상태 복구 → 장중 실행 플로우 정상 동작
- 주문/체결 데이터가 DB에 정확히 기록
- 재시작 후 동일 상태 복구
- 주요 실패 시 거래 중지 모드로 안전 종료

---

## 19. 추후 확장

- 다중 전략 동시 실행
- 분산 처리 구조 (멀티 프로세스)
- UI 대시보드
