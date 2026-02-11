# Stock Manager 실행 다이어그램

## 목차
1. [시스템 아키텍처 개요](#1-시스템-아키텍처-개요)
2. [초기화 흐름](#2-초기화-흐름)
3. [OAuth 인증 흐름](#3-oauth-인증-흐름)
4. [주문 실행 흐름](#4-주문-실행-흐름)
5. [가격 모니터링 흐름](#5-가격-모니터링-흐름)
6. [포지션 조정 흐름](#6-포지션-조정-흐름)
7. [상태 저장 및 복구 흐름](#7-상태-저장-및-복구-흐름)
8. [컴포넌트 관계도](#8-컴포넌트-관계도)
9. [클래스 다이어그램](#9-클래스-다이어그램)

---

## 1. 시스템 아키텍처 개요

```mermaid
graph TB
    subgraph "User Layer"
        USER[사용자 코드]
    end

    subgraph "Engine Layer"
        ENGINE[TradingEngine<br/>메인 오케스트레이터]
    end

    subgraph "Trading Components"
        EXECUTOR[OrderExecutor<br/>주문 실행]
        POSITIONS[PositionManager<br/>포지션 관리]
        RISK[RiskManager<br/>리스크 검증]
        LIMITER[RateLimiter<br/>요청 제한]
    end

    subgraph "Background Threads"
        MONITOR[PriceMonitor<br/>가격 모니터링]
        RECONCILER[PositionReconciler<br/>포지션 조정]
    end

    subgraph "Persistence Layer"
        STATE[TradingState<br/>상태 관리]
        RECOVERY[Recovery<br/>복구 프로토콜]
    end

    subgraph "KIS API Adapter"
        CLIENT[KISRestClient<br/>HTTP 클라이언트]
        CONFIG[KISConfig<br/>설정 관리]
        CONN[KISConnectionState<br/>연결 상태]
    end

    subgraph "KIS APIs"
        OAUTH[OAuth API]
        DOMESTIC[Domestic Stock API<br/>195+ 함수]
    end

    USER --> ENGINE
    ENGINE --> EXECUTOR
    ENGINE --> POSITIONS
    ENGINE --> RISK
    ENGINE --> MONITOR
    ENGINE --> RECONCILER
    ENGINE --> STATE

    EXECUTOR --> LIMITER
    EXECUTOR --> CLIENT
    MONITOR --> CLIENT
    RECONCILER --> CLIENT

    CLIENT --> CONFIG
    CLIENT --> CONN
    CLIENT --> OAUTH
    CLIENT --> DOMESTIC

    STATE --> RECOVERY

    style ENGINE fill:#e1f5fe
    style CLIENT fill:#fff3e0
    style POSITIONS fill:#e8f5e9
    style STATE fill:#fce4ec
```

---

## 2. 초기화 흐름

```mermaid
sequenceDiagram
    autonumber
    participant User as 사용자
    participant Engine as TradingEngine
    participant Client as KISRestClient
    participant Config as KISConfig
    participant OAuth as OAuth API
    participant State as TradingState
    participant Monitor as PriceMonitor
    participant Reconciler as PositionReconciler

    User->>Config: KISConfig.from_env()
    Note over Config: .env 파일에서<br/>APP_KEY, APP_SECRET<br/>ACCOUNT_NUMBER 로드

    User->>Client: KISRestClient(config)
    Client->>Client: HTTP 클라이언트 초기화
    Client->>Client: 헤더 설정

    User->>Client: client.authenticate()
    Client->>OAuth: POST /oauth2/tokenP
    Note over OAuth: grant_type: client_credentials<br/>appkey, appsecret
    OAuth-->>Client: access_token (24시간 유효)
    Client->>Client: KISConnectionState.update_token()

    User->>Engine: TradingEngine(client, config)
    Engine->>Engine: 내부 컴포넌트 초기화

    User->>Engine: engine.start()
    Engine->>State: load_state()
    Note over State: ~/.stock_manager/state.json

    Engine->>Engine: startup_reconciliation()
    Note over Engine: 브로커 = 진실의 원천<br/>로컬 ↔ 브로커 비교

    Engine->>Monitor: PriceMonitor.start()
    Note over Monitor: daemon=True<br/>2초 간격 폴링

    Engine->>Reconciler: PositionReconciler.start()
    Note over Reconciler: daemon=True<br/>60초 간격 조정

    Engine-->>User: RecoveryReport 반환
```

---

## 3. OAuth 인증 흐름

```mermaid
flowchart TB
    subgraph "인증 요청"
        A[client.authenticate 호출] --> B{모의투자?}
        B -->|Yes| C[POST /oauth2/tokenP]
        B -->|No| D[POST /oauth2/token]
    end

    subgraph "요청 구성"
        C --> E[Headers: appkey, appsecret]
        D --> E
        E --> F[Body: grant_type=client_credentials]
    end

    subgraph "응답 처리"
        F --> G[KIS API 서버]
        G --> H{성공?}
        H -->|Yes| I[access_token 수신<br/>expires_in: 86400]
        H -->|No| J[KISAuthenticationError]
    end

    subgraph "상태 저장"
        I --> K[KISAccessToken 생성]
        K --> L[KISConnectionState.update_token]
        L --> M[is_authenticated = True]
    end

    subgraph "후속 요청"
        M --> N[모든 API 요청에<br/>Authorization: Bearer token]
    end

    style A fill:#e3f2fd
    style G fill:#fff9c4
    style M fill:#c8e6c9
    style J fill:#ffcdd2
```

---

## 4. 주문 실행 흐름

```mermaid
sequenceDiagram
    autonumber
    participant User as 사용자
    participant Engine as TradingEngine
    participant Executor as OrderExecutor
    participant Limiter as RateLimiter
    participant API as domestic_stock.orders
    participant Client as KISRestClient
    participant KIS as KIS API 서버
    participant Pos as PositionManager
    participant State as TradingState

    User->>Engine: engine.buy("005930", 10, 70000)

    Engine->>Engine: _running 확인

    Engine->>Executor: buy(symbol, qty, price)
    Executor->>Executor: idempotency_key 생성 (UUID)
    Executor->>Executor: 중복 키 확인

    Executor->>API: cash_order(params)
    Note over API: TR_ID, URL, 파라미터 구성
    API-->>Executor: 요청 설정 반환

    Executor->>Limiter: acquire()
    Note over Limiter: 슬라이딩 윈도우<br/>20 req/sec

    alt 제한 초과
        Limiter-->>Executor: 대기 후 재시도
    else 여유 있음
        Limiter-->>Executor: 진행
    end

    Executor->>Client: make_request(POST, /orders/cash-order)
    Client->>Client: 인증 헤더 추가
    Client->>Client: hashkey 추가

    Client->>KIS: HTTP POST
    KIS-->>Client: {rt_cd: "0", output: {odno: "12345"}}

    Client->>Client: 응답 검증 (rt_cd, msg_cd)
    Client-->>Executor: 응답 데이터

    Executor->>Executor: OrderResult 생성
    Executor-->>Engine: OrderResult

    alt 성공
        Engine->>Pos: open_position(Position)
        Engine->>Engine: PriceMonitor.add_symbol()
        Engine->>State: 상태 업데이트
        Engine->>State: save_state_atomic()
        Note over State: tmp 쓰기 → fsync → rename
    else 실패
        Engine->>Engine: 에러 로깅
    end

    Engine-->>User: OrderResult 반환
```

---

## 5. 가격 모니터링 흐름

```mermaid
flowchart TB
    subgraph "PriceMonitor 스레드"
        A[시작: daemon=True] --> B[2초 대기]
        B --> C{종료 신호?}
        C -->|Yes| D[스레드 종료]
        C -->|No| E[모니터링 심볼 순회]
    end

    subgraph "가격 조회"
        E --> F[inquire_current_price]
        F --> G[GET /quotations/inquire-price]
        G --> H[응답: stck_prpr]
    end

    subgraph "콜백 처리"
        H --> I[callback: symbol, price]
        I --> J[PositionManager.update_price]
    end

    subgraph "포지션 업데이트"
        J --> K[current_price 갱신]
        K --> L[unrealized_pnl 계산]
        L --> M{손절가 체크}
    end

    subgraph "손절/익절 트리거"
        M -->|price ≤ stop_loss| N[_handle_stop_loss]
        N --> O[자동 매도 주문]
        M -->|No| P{익절가 체크}
        P -->|price ≥ take_profit| Q[_handle_take_profit]
        Q --> O
        P -->|No| B
    end

    O --> R[OrderResult]
    R --> S[포지션 청산]
    S --> B

    style A fill:#e8f5e9
    style N fill:#ffcdd2
    style Q fill:#c8e6c9
    style D fill:#e0e0e0
```

---

## 6. 포지션 조정 흐름

```mermaid
sequenceDiagram
    autonumber
    participant Reconciler as PositionReconciler
    participant Client as KISRestClient
    participant KIS as KIS API
    participant Pos as PositionManager
    participant Engine as TradingEngine

    loop 60초마다
        Reconciler->>Client: inquire_balance()
        Client->>KIS: GET /balance
        KIS-->>Client: 브로커 포지션 목록
        Client-->>Reconciler: 응답 데이터

        Reconciler->>Pos: get_all_positions()
        Pos-->>Reconciler: 로컬 포지션 목록

        Reconciler->>Reconciler: 비교 분석

        Note over Reconciler: 분석 항목:<br/>1. orphan_positions (브로커에만 존재)<br/>2. missing_positions (로컬에만 존재)<br/>3. quantity_mismatches (수량 불일치)

        alt 불일치 발견
            Reconciler->>Engine: on_discrepancy(result)
            Note over Engine: 경고 로깅<br/>브로커 = 진실의 원천
        end
    end
```

```mermaid
flowchart LR
    subgraph "브로커 상태"
        B1[005930: 100주]
        B2[035720: 50주]
    end

    subgraph "로컬 상태"
        L1[005930: 100주]
        L2[000660: 30주]
    end

    subgraph "조정 결과"
        R1[✓ 005930: 일치]
        R2[⚠ 035720: orphan<br/>브로커에만 존재]
        R3[⚠ 000660: missing<br/>로컬에만 존재]
    end

    B1 --> R1
    L1 --> R1
    B2 --> R2
    L2 --> R3

    style R1 fill:#c8e6c9
    style R2 fill:#fff9c4
    style R3 fill:#ffcdd2
```

---

## 7. 상태 저장 및 복구 흐름

### 7.1 원자적 상태 저장

```mermaid
flowchart TB
    subgraph "save_state_atomic"
        A[TradingState.to_dict] --> B[JSON 직렬화]
        B --> C[임시 파일 생성<br/>.state.json.tmp]
        C --> D[JSON 쓰기]
        D --> E[flush 버퍼]
        E --> F[fsync 파일<br/>디스크 강제 기록]
        F --> G[rename: tmp → state.json<br/>POSIX 원자적 연산]
        G --> H[fsync 디렉토리<br/>rename 영속성 보장]
    end

    subgraph "저장 데이터"
        I[positions: dict]
        J[pending_orders: dict]
        K[last_updated: datetime]
        L[version: 1]
    end

    I --> A
    J --> A
    K --> A
    L --> A

    style F fill:#fff9c4
    style G fill:#c8e6c9
    style H fill:#fff9c4
```

### 7.2 복구 흐름

```mermaid
sequenceDiagram
    autonumber
    participant Engine as TradingEngine
    participant State as TradingState
    participant File as state.json
    participant Pos as PositionManager
    participant Client as KISRestClient
    participant KIS as KIS API

    Engine->>State: load_state(path)
    State->>File: 파일 읽기
    File-->>State: JSON 데이터

    State->>State: TradingState.from_dict()
    State-->>Engine: TradingState 객체

    Engine->>Pos: 포지션 복원

    Engine->>Engine: startup_reconciliation()

    Engine->>Client: inquire_balance()
    Client->>KIS: GET /balance
    KIS-->>Client: 브로커 실제 포지션

    Engine->>Engine: 로컬 vs 브로커 비교

    Note over Engine: RecoveryResult:<br/>CLEAN / RECONCILED / FAILED

    alt CLEAN
        Note over Engine: 불일치 없음
    else RECONCILED
        Engine->>Pos: 브로커 상태로 업데이트
        Engine->>State: 조정된 상태 저장
    else FAILED
        Note over Engine: 심각한 오류 로깅
    end

    Engine-->>Engine: RecoveryReport 반환
```

---

## 8. 컴포넌트 관계도

```mermaid
graph TB
    subgraph "stock_manager/"
        ENGINE[engine.py<br/>TradingEngine]
    end

    subgraph "adapters/broker/kis/"
        CLIENT[client.py<br/>KISRestClient]
        CONFIG[config.py<br/>KISConfig, KISConnectionState]
        EXCEPTIONS[exceptions.py<br/>KISException 계층]

        subgraph "apis/"
            OAUTH[oauth/oauth.py<br/>인증 함수]

            subgraph "domestic_stock/"
                BASIC[basic.py<br/>22 함수]
                ORDERS[orders.py<br/>25 함수]
                ANALYSIS[analysis.py<br/>30+ 함수]
                ELW[elw.py<br/>23 함수]
                INFO[info.py<br/>27 함수]
                RANKING[ranking.py<br/>23 함수]
                REALTIME[realtime.py<br/>30 함수]
                SECTOR[sector.py<br/>15 함수]
            end
        end
    end

    subgraph "trading/"
        MODELS[models.py<br/>Order, Position, Config]
        EXECUTOR[executor.py<br/>OrderExecutor]
        POSITIONS[positions.py<br/>PositionManager]
        RATE[rate_limiter.py<br/>RateLimiter]
        RISK[risk.py<br/>RiskManager]

        subgraph "strategies/"
            STRAT_BASE[base.py<br/>Strategy]
            GRAHAM[graham.py<br/>Graham전략]
        end

        subgraph "reflexivity/"
            CYCLE[cycle_detector.py]
            SIZING[sizing.py]
            THESIS[thesis.py]
        end
    end

    subgraph "monitoring/"
        PRICE_MON[price_monitor.py<br/>PriceMonitor]
        RECON[reconciler.py<br/>PositionReconciler]
    end

    subgraph "persistence/"
        STATE[state.py<br/>TradingState]
        RECOVERY[recovery.py<br/>복구 프로토콜]
    end

    ENGINE --> CLIENT
    ENGINE --> EXECUTOR
    ENGINE --> POSITIONS
    ENGINE --> RISK
    ENGINE --> PRICE_MON
    ENGINE --> RECON
    ENGINE --> STATE

    EXECUTOR --> ORDERS
    EXECUTOR --> RATE
    PRICE_MON --> BASIC
    RECON --> ORDERS

    CLIENT --> CONFIG
    CLIENT --> EXCEPTIONS
    CLIENT --> OAUTH

    STATE --> RECOVERY

    STRAT_BASE --> GRAHAM

    style ENGINE fill:#e1f5fe,stroke:#0288d1
    style CLIENT fill:#fff3e0,stroke:#ff9800
    style STATE fill:#fce4ec,stroke:#e91e63
```

---

## 9. 클래스 다이어그램

```mermaid
classDiagram
    class TradingEngine {
        -KISRestClient client
        -TradingConfig config
        -OrderExecutor executor
        -PositionManager positions
        -RiskManager risk
        -PriceMonitor monitor
        -PositionReconciler reconciler
        -TradingState state
        -bool _running
        +start() RecoveryReport
        +stop() void
        +buy(symbol, qty, price) OrderResult
        +sell(symbol, qty, price) OrderResult
        +get_positions() dict
        +get_status() EngineStatus
    }

    class KISRestClient {
        -KISConfig config
        -KISConnectionState state
        -httpx.Client _client
        +authenticate() void
        +make_request(method, path, params) dict
        +revoke_token() void
    }

    class KISConfig {
        +SecretStr app_key
        +SecretStr app_secret
        +str account_number
        +bool use_mock
        +api_base_url() str
        +is_mock_trading() bool
    }

    class KISConnectionState {
        +KISConfig config
        +KISAccessToken access_token
        +bool is_authenticated
        +update_token(token) void
        +clear_token() void
    }

    class OrderExecutor {
        -KISRestClient client
        -RateLimiter limiter
        -set _submitted_keys
        +buy(symbol, qty, price) OrderResult
        +sell(symbol, qty, price) OrderResult
        -_execute_order() OrderResult
    }

    class PositionManager {
        -dict _positions
        -RLock _lock
        +open_position(position) void
        +close_position(symbol) void
        +update_price(symbol, price) void
        +get_all_positions() dict
    }

    class RateLimiter {
        -int max_requests
        -float window
        -list _requests
        -Lock _lock
        +acquire(timeout) bool
        +try_acquire() bool
        +available() int
    }

    class PriceMonitor {
        -KISRestClient client
        -list symbols
        -Thread _thread
        -Event _stop_event
        +start() void
        +stop() void
        +add_symbol(symbol) void
        +remove_symbol(symbol) void
    }

    class TradingState {
        +dict positions
        +dict pending_orders
        +datetime last_updated
        +to_dict() dict
        +from_dict(data) TradingState
    }

    class Order {
        +str order_id
        +str idempotency_key
        +str symbol
        +str side
        +int quantity
        +int price
        +OrderStatus status
        +str broker_order_id
    }

    class Position {
        +str symbol
        +int quantity
        +Decimal entry_price
        +Decimal current_price
        +Decimal stop_loss
        +Decimal take_profit
        +Decimal unrealized_pnl
        +PositionStatus status
    }

    TradingEngine --> KISRestClient
    TradingEngine --> OrderExecutor
    TradingEngine --> PositionManager
    TradingEngine --> PriceMonitor
    TradingEngine --> TradingState

    KISRestClient --> KISConfig
    KISRestClient --> KISConnectionState

    OrderExecutor --> KISRestClient
    OrderExecutor --> RateLimiter

    PositionManager --> Position
    TradingState --> Position
    TradingState --> Order
```

---

## 10. API 함수 호출 패턴

```mermaid
flowchart TB
    subgraph "API 함수 패턴"
        A[API 함수 호출<br/>inquire_current_price]
        A --> B[TR_ID 결정<br/>모의투자 여부]
        B --> C[요청 설정 구성<br/>path, params, headers]
        C --> D[client.make_request 호출]
    end

    subgraph "make_request 내부"
        D --> E[인증 헤더 추가<br/>appkey, appsecret, token]
        E --> F[hashkey 계산<br/>계좌번호 보안]
        F --> G[HTTP 요청 전송]
        G --> H{응답 검증}
    end

    subgraph "응답 처리"
        H -->|rt_cd = 0| I[성공: output 반환]
        H -->|rt_cd = -1| J[KISAPIError]
        H -->|HTTP 429| K[KISRateLimitError]
        H -->|HTTP 4xx/5xx| L[KISAPIError]
    end

    style A fill:#e3f2fd
    style D fill:#fff9c4
    style I fill:#c8e6c9
    style J fill:#ffcdd2
    style K fill:#ffcdd2
    style L fill:#ffcdd2
```

---

## 11. 에러 처리 계층

```mermaid
graph TB
    subgraph "예외 계층"
        BASE[KISException<br/>기본 예외]
        BASE --> CONFIG_ERR[KISConfigurationError<br/>설정 오류]
        BASE --> AUTH_ERR[KISAuthenticationError<br/>인증 오류]
        BASE --> API_ERR[KISAPIError<br/>API 오류]
        BASE --> VALID_ERR[KISValidationError<br/>검증 오류]
        API_ERR --> RATE_ERR[KISRateLimitError<br/>요청 제한 초과]
    end

    subgraph "발생 시점"
        CONFIG_ERR -.-> S1[설정 누락/무효]
        AUTH_ERR -.-> S2[토큰 만료/무효 자격증명]
        API_ERR -.-> S3[HTTP 오류/API 오류 응답]
        RATE_ERR -.-> S4[HTTP 429/20 req/sec 초과]
        VALID_ERR -.-> S5[잘못된 입력 파라미터]
    end

    style BASE fill:#e0e0e0
    style CONFIG_ERR fill:#fff9c4
    style AUTH_ERR fill:#ffcdd2
    style API_ERR fill:#ffcdd2
    style RATE_ERR fill:#ffcdd2
    style VALID_ERR fill:#fff9c4
```

---

## 요약

| 구성요소 | 역할 | 스레드 안전 |
|---------|------|-----------|
| **TradingEngine** | 메인 오케스트레이터 | Context Manager |
| **KISRestClient** | HTTP 통신 | httpx.Client |
| **OrderExecutor** | 주문 실행, 멱등성 | UUID 키 |
| **PositionManager** | 포지션 관리 | RLock |
| **RateLimiter** | 20 req/sec 제한 | Lock |
| **PriceMonitor** | 2초 가격 폴링 | daemon 스레드 |
| **PositionReconciler** | 60초 조정 | daemon 스레드 |
| **TradingState** | 원자적 저장 | fsync + rename |

**핵심 원칙**: 브로커가 진실의 원천 (Broker is Source of Truth)
