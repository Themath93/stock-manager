# Stock Manager

Stock Manager는 국내 주식 운용을 위한 Python 3.13 기반 트레이딩 봇입니다.
안전한 **paper-first** 흐름을 기본으로 설계되어, 명시적인 승격(승인) 검사를 통과한 경우에만 실거래를 허용합니다.

## 이 저장소에서 제공하는 기능
- 거래 세션을 설정하고 검증하며 실행/모니터링할 수 있는 CLI 명령어 제공.
- 주문 처리, 리스크 검사, 영속성(상태 저장/복구)을 담당하는 모듈형 어댑터와 도메인 서비스.
- 주문 실행, 재조정, 리스크 이벤트에 대한 Slack 알림 연동.
- 개발/CI에서 사용할 수 있는 오프라인 안전 검증 경로(`mock`) 제공.

## 시스템 아키텍처

```
CLI (main.py)
  └─ TradingEngine (engine.py)
       ├─ Strategy Layer
       │    ├─ GrahamScreener (기존)
       │    └─ ConsensusStrategy (신규) ← Strategy ABC drop-in
       │         └─ ConsensusEvaluator
       │              ├─ 10 Investor Personas (병렬 평가)
       │              │   Graham, Buffett, Lynch, Soros, Dalio,
       │              │   Munger, Templeton, Livermore, Fisher, Simons
       │              ├─ Wood Advisory (10+1, 투표 제외)
       │              └─ VoteAggregator (7/10 이상 BUY → 통과)
       ├─ TradingPipelineRunner (11-state FSM)
       │    ├─ BuySpecialist → KIS 매수 주문
       │    ├─ PositionMonitor (손절/익절/트레일링스톱)
       │    └─ SellSpecialist → KIS 매도 주문
       ├─ KIS Broker Adapter (모의/실전 자동 전환)
       ├─ PipelineJsonLogger (NDJSON, 12 이벤트 타입)
       └─ Slack Notifications (Block Kit, 5채널 라우팅)
```

## 저장소 구조 (요약)

```
stock_manager/
├── cli/                          # CLI 명령 핸들러
├── adapters/broker/kis/          # KIS 증권사 연동 (모의/실전)
├── trading/
│   ├── strategies/               # 전략 (graham, consensus)
│   ├── personas/                 # 10+1 투자 페르소나
│   │   └── prompts/              # LLM 시스템 프롬프트 (YAML)
│   ├── consensus/                # 투표 집계, 평가기, 파서
│   ├── pipeline/                 # 11-state 파이프라인 (runner, buy/sell, monitor)
│   ├── indicators/               # 기술 지표 + KIS 데이터 페처
│   ├── llm/                      # LLM 클라이언트, 서킷브레이커
│   ├── logging/                  # NDJSON 파이프라인 로거
│   └── reflexivity/              # Soros 반사성 사이클 분석
├── notifications/                # Slack Block Kit 알림
├── pipeline/                     # 기본 지표 함수
├── qa/                           # Mock Promotion Gate
└── tests/                        # 단위/통합 테스트
```

## Consensus 트레이딩 파이프라인

### 10+1 페르소나 시스템

10명의 투자 대가 페르소나가 각 종목을 독립적으로 평가합니다. 각 페르소나는 고유한 투자 철학(가치투자, 성장투자, 모멘텀 등)에 기반한 규칙으로 BUY/SELL/HOLD 투표를 수행합니다.

| 페르소나 | 투자 철학 |
|----------|-----------|
| Benjamin Graham | 안전 마진 중심 가치투자 |
| Warren Buffett | 경제적 해자, 장기 보유 |
| Peter Lynch | 성장주, 일상에서 발견하는 투자 |
| George Soros | 반사성 이론, 매크로 모멘텀 |
| Ray Dalio | 리스크 패리티, 분산 투자 |
| Charlie Munger | 역발상, 정신 모델 |
| John Templeton | 글로벌 가치투자, 역발상 |
| Jesse Livermore | 가격 추세, 모멘텀 |
| Philip Fisher | 성장주 질적 분석 |
| Jim Simons | 계량적 신호, 통계 차익 |

**Cathie Wood Advisory**: 11번째 페르소나로 혁신 기술 관점의 자문을 제공합니다. 투표에는 포함되지 않으며, 별도 참고 의견으로 활용됩니다.

### 투표 집계 (VoteAggregator)

4단계 게이트를 통해 합의 결과를 판정합니다.

1. **정족수 확인**: 전체 페르소나의 60% 이상이 투표에 참여해야 합니다.
2. **임계값 확인**: 10명 중 7명 이상이 BUY 투표를 해야 합니다.
3. **최소 확신도**: 페르소나별 확신도 점수가 0.5 이상이어야 합니다.
4. **카테고리 다양성**: 서로 다른 투자 철학 카테고리에서 2개 이상의 BUY가 있어야 합니다.

### Hybrid 2-Stage 아키텍처

불필요한 LLM 비용을 최소화하면서 정확도를 높이는 2단계 구조를 채택합니다.

- **1단계 (규칙 기반)**: 모든 종목에 대해 규칙 기반 평가를 수행합니다. 추가 비용 없이 빠르게 후보군을 좁힙니다.
- **2단계 (선택적 LLM 검증)**: 1단계를 통과한 약 15%의 종목에 대해 `claude-agent-sdk`를 사용한 LLM 검증을 수행합니다. 모호한 케이스나 고확신 케이스에서만 트리거됩니다.

### 11-state 파이프라인 상태 전이

```
WATCHLIST → SCREENING → EVALUATING → CONSENSUS_APPROVED
                                    → CONSENSUS_REJECTED
CONSENSUS_APPROVED → BUY_PENDING → BOUGHT → MONITORING
MONITORING → SELL_PENDING → SOLD
(모든 상태에서) → ERROR
```

## 사전 요구 사항
- Python 3.13+
- 의존성/테스크 실행용 `uv` (또는 동등한 환경 도구)
- 선택 사항: 모드에 따라 PostgreSQL, Slack 앱 토큰, 브로커 키.

## 설치 및 초기화
```bash
# 저장소 클론 후 의존성 설치
git clone <repo-url>
cd stock-manager
uv sync --extra dev --extra cli

# 대화형 설정 마법사 실행 (.env 생성)
stock-manager setup
```

## 환경 변수

최소한의 필수 변수는 `.env.example`에 정리되어 있습니다.

### 모드 전환
- `KIS_USE_MOCK=true` → 모의(페이퍼) 거래 모드.
- `KIS_USE_MOCK=false` → 실거래 모드.

### 모의 모드 자격 증명 규칙
`KIS_USE_MOCK=true`일 때는 모의 전용 키만 허용됩니다:
- `KIS_MOCK_APP_KEY`
- `KIS_MOCK_SECRET`
- `KIS_MOCK_ACCOUNT_NUMBER`

실거래 키를 모의 모드에서 대체값으로 허용하지 않습니다.

### 공통 설정
- `KIS_ACCOUNT_PRODUCT_CODE` (2자리, 기본값 `01`)
- Slack 알림을 사용할 경우 토큰/채널 값(선택).

## 주요 명령

### `stock-manager setup`
`.env` 값 입력을 도와주는 대화형 설정 마법사.

### `stock-manager doctor`
환경 설정과 파일 포맷을 검증합니다.

### `stock-manager smoke`
실거래가 발생하지 않는 상태 점검 명령입니다.
- 인증
- 단일 가격 조회
- 잔고 조회

빠른 준비 상태 점검용 명령입니다.

### `stock-manager trade`
`stock-manager trade buy|sell SYMBOL QTY --price PRICE`

- 기본 동작은 **dry-run**(실행 없음)입니다.
- 모의 모드에서 주문을 제출하려면 `--execute`를 사용합니다.
- 실거래 실행은 `--execute --confirm-live`를 사용하고, 승격 게이트 통과가 필요합니다.

### `stock-manager run`
거래 엔진 루프를 시작합니다.

권장 실행 순서:
1. 로컬 점검을 위해 `stock-manager run --skip-auth` 실행.
2. 모의 모드에서 `stock-manager smoke` 실행.
3. 모의 모드와 전략 옵션으로 `stock-manager run --duration-sec N` 실행.
4. mock promotion gate 산출물을 생성/검토.
5. `KIS_USE_MOCK=false --confirm-live --execute`로 실거래 실행(게이트 통과 상태).

### 전략/런타임 옵션
`run`은 전략과 websocket 알림/탐색 동작을 조절할 수 있습니다:
- `--strategy`, `--strategy-symbols`
- `--strategy-order-quantity`, `--strategy-max-symbols-per-cycle`, `--strategy-max-buys-per-cycle`
- `--strategy-run-interval-sec`
- `--strategy-auto-discover`, `--strategy-discovery-limit`, `--strategy-discovery-fallback-symbols`
- `--websocket-monitoring-enabled`, `--websocket-execution-notice-enabled`

## 전략 비교

| 전략 | 설명 | 사용법 |
|------|------|--------|
| `graham` | 벤저민 그레이엄 가치투자 스크리너 | `--strategy graham` |
| `consensus` | 10+1 페르소나 합의 투표 시스템 | `--strategy consensus` |

## 거래 동작 개요
1. 환경 변수/검증 결과로 런타임 컨텍스트를 구성합니다.
2. 브로커 클라이언트 인증을 수행합니다.
3. 전략/심볼/제한값으로 전략 컨텍스트를 구성합니다.
4. 엔진 루프를 시작하고 재조정(reconciliation) 생명주기를 실행합니다.
5. 진입 전 리스크 검사가 선행됩니다.
6. 핵심 체크포인트에서 Slack 이벤트를 발행합니다.
7. 주문 실행은 `OrderExecutor`를 통해 모의/실거래 동작을 분리해 처리합니다.

## Slack 알림
운영상 의미 있는 이벤트에 대해 Slack 알림을 발송합니다.

- 모의 모드 알림은 `[MOCK]` 접두사로 구분됩니다.
- 에러, 실행 공지, 리스크 이벤트, 상태 전환 알림을 포함합니다.
- 포맷 상세는 `ai_developer_guides/SLACK_NOTIFICATION_GUIDE.md`를 참고하세요.

Slack 사용 여부는 환경 변수로 제어하며, 사용 시 필수 키는 `doctor`에서 확인합니다.

## Mock Promotion Gate (mock → live)
실거래는 mock promotion gate 통과 전에는 차단됩니다.

- 게이트 파일: `.sisyphus/evidence/mock-promotion-gate.json`
- 필수 조건 예시: `mode = mock`, `pass = true`
- 게이트를 적용하는 명령:
  - `stock-manager run` (실거래)
  - `stock-manager trade ... --execute --confirm-live` (실거래)

예시:
```bash
uv run python scripts/mock_qa_gate.py --emit .sisyphus/evidence/mock-promotion-gate.json
cat .sisyphus/evidence/mock-promotion-gate.json
```

## 비거래 시간대 검증(폐장 시) 전략
시장 폐장 시에는 단위 테스트와 오프라인 검증으로 가능한 한 많이 확인합니다.

```bash
uv run pytest --no-cov tests/unit/test_mock_qa_gate.py -q
uv run pytest --no-cov tests/unit/test_cli_main.py -q
uv run pytest --no-cov tests/unit/test_doctor.py -q
```

전체 테스트 실행 시 저장소는 글로벌 커버리지 게이트(`--cov-fail-under=80`)를 적용합니다.
작은 변경은 위와 같이 `--no-cov`로 핵심 테스트만 빠르게 검증할 수 있습니다.

권장 커버리지 점검 항목:
- 핵심 거래 실행 경로의 높은 신뢰도 검증
- Slack 알림 및 진단 경로 단언
- 모의 모드 자격 증명/안전 장치 테스트

## 테스트

```bash
# 전체 테스트 실행
uv run pytest

# 커버리지 포함
uv run pytest --cov=stock_manager --cov-fail-under=80

# 특정 모듈 테스트
uv run pytest tests/unit/test_consensus_pipeline.py -v
uv run pytest tests/unit/test_pipeline_runner.py -v
uv run pytest tests/unit/test_buy_specialist.py -v
```

## 사용 예시

```bash
# 모의 모드: smoke 실행
KIS_USE_MOCK=true uv run stock-manager smoke

# 모의 모드: 전략 자동 탐색으로 1개 종목 실행
KIS_USE_MOCK=true uv run stock-manager run --duration-sec 60 --strategy graham --strategy-auto-discover

# 모의 모드: Consensus 전략으로 특정 종목 평가
stock-manager run --strategy consensus --strategy-symbols "005930,000660,035420" --duration-sec 300

# 모의 모드: 자동 탐색 + fallback 종목
stock-manager run --strategy consensus --strategy-auto-discover --strategy-discovery-fallback-symbols "005930,000660"

# 모의 모드: 주문 실행(비실거래)
KIS_USE_MOCK=true uv run stock-manager trade buy 005930 1 --price 70000 --execute

# 실거래: confirm-live + gate 필요
KIS_USE_MOCK=false uv run stock-manager trade buy 005930 1 --price 70000 --execute --confirm-live
```

## FAQ
- `doctor` 실행 결과가 "Doctor result: NOT OK"라면, 환경 변수를 수정한 뒤 다시 실행하세요.
- promotion gate 메시지로 주문이 막히면 mock gate 스크립트를 실행해 산출물을 확인하세요.
- smoke는 통과했는데 mock 모드에서 run이 실패한다면 계좌 형식과 출력에 포함된 OPSQ2000 힌트를 확인하세요.

## Contributing

### 개발 환경

- Python 3.13 이상 필요
- 패키지 및 태스크 실행에 `uv`를 사용합니다.

```bash
uv sync --extra dev --extra cli
```

### 브랜치 전략

브랜치명은 `feature/SPEC-XXX-description` 형식을 따릅니다.

예시:
- `feature/SPEC-001-consensus-strategy`
- `feature/SPEC-002-trailing-stop`

### PR 제출 전 필수 확인 사항

```bash
# 테스트 통과 확인
uv run pytest

# 린트 검사
uv run ruff check

# 타입 검사
uv run mypy stock_manager
```

### 커밋 메시지

한국어 또는 영어로 작성하며, 변경 사유를 명시합니다.

예시:
- `feat: Consensus 전략 투표 집계기 추가 (7/10 임계값)`
- `fix: KIS 모의 모드에서 계좌 번호 검증 누락 수정`

### 코드 스타일

- `ruff` 포맷터 규칙을 준수합니다.
- 모든 공개 함수와 클래스에 type hints를 필수로 작성합니다.
- 새로운 비즈니스 로직에는 단위 테스트를 함께 제출합니다.

## 참고
- 개발 기본 경로는 모의 모드입니다.
- 프로젝트는 보수적으로 동작하며, 실거래는 명시적 의도와 안전 검사 완료가 선행되어야 합니다.
