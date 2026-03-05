# Domain Glossary

핵심 도메인 용어 24개를 정의합니다. 각 용어의 한 줄 정의와 소스 파일 경로를 포함합니다.

## Order & Position Management

| Term | Definition | Source |
|------|------------|--------|
| Order | 멱등 키 기반 매수/매도 트랜잭션. 8단계 상태 머신. | `trading/models.py` |
| OrderStatus | CREATED→VALIDATING→SUBMITTED→...→FILLED/REJECTED | `trading/models.py` |
| Position | 보유 종목. P&L, 손절/익절 수준 포함 | `trading/models.py` |
| PositionStatus | OPEN, OPEN_RECONCILED, CLOSED, STALE | `trading/models.py` |
| TradingConfig | 리스크 한도, 폴링 간격, 전략 파라미터 설정 (frozen) | `trading/models.py` |

## Investor Personas & Voting

| Term | Definition | Source |
|------|------------|--------|
| InvestorPersona | 규칙 기반 평가의 추상 베이스. screen_rule 메서드 필수 | `trading/personas/base.py` |
| PersonaCategory | VALUE, GROWTH, MOMENTUM, MACRO, QUANTITATIVE, INNOVATION 6종 | `trading/personas/models.py` |
| screen_rule | 결정론적 평가 메서드. MarketSnapshot → PersonaVote 반환 | `trading/personas/base.py` |
| VoteAction | BUY, SELL, HOLD, ABSTAIN, ADVISORY 5종 | `trading/personas/models.py` |
| PersonaVote | 바인딩 투표. conviction(0.0-1.0) + reasoning 포함 | `trading/personas/models.py` |
| AdvisoryVote | WoodAdvisory 전용 비바인딩 투표. 합의 계산에서 제외 | `trading/personas/models.py` |
| MarketSnapshot | 46개 필드의 불변 시장 데이터 (가격, 밸류에이션, 기술적, 재무건전성, 성장, 대차대조표, 이력, 시장 맥락) | `trading/personas/models.py` |
| EvaluationRequest | 심볼 + 스냅샷 + 컨텍스트 묶음. 합의 파이프라인 입력 | `trading/personas/models.py` |

## Consensus & Aggregation

| Term | Definition | Source |
|------|------------|--------|
| ConsensusEvaluator | ThreadPoolExecutor로 페르소나 병렬 평가 오케스트레이터 | `trading/consensus/evaluator.py` |
| ConsensusResult | 투표 집계 결과. passes_threshold, avg_conviction, category_diversity | `trading/personas/models.py` |
| VoteAggregator | 4-gate 합의: Quorum(≥60%) → Threshold(≥7 BUY) → Conviction(≥0.5) → Diversity(≥2 카테고리). 모두 통과해야 매수 | `trading/consensus/aggregator.py` |

## LLM Integration

| Term | Definition | Source |
|------|------------|--------|
| CircuitBreaker | 3-상태 FSM (CLOSED→OPEN→HALF_OPEN). LLM API 장애 보호 | `trading/llm/circuit_breaker.py` |
| CircuitState | CLOSED(정상), OPEN(차단), HALF_OPEN(시험) | `trading/llm/circuit_breaker.py` |
| LLMConfig | 환경변수 기반 설정. 모델, 타임아웃, 재시도, 일일 한도 | `trading/llm/config.py` |
| InvocationCounter | 스레드 안전 일일 카운터. 자정(KST) 리셋 | `trading/llm/config.py` |

## Broker Integration (KIS)

| Term | Definition | Source |
|------|------------|--------|
| KISConfig | 모의/실전 모드 선택. 토큰 캐싱, 재시도 안정화 | `adapters/broker/kis/config.py` |
| KISAccessToken | OAuth 토큰. Authorization 헤더 포맷팅, 유효성 검사 | `adapters/broker/kis/config.py` |
| KISConnectionState | 현재 연결 상태 (설정, 토큰, 만료, 인증 플래그) | `adapters/broker/kis/config.py` |

## See Also

- [README.md](../README.md) — 프로젝트 개요 및 시스템 아키텍처
- [execution-diagrams.md](execution-diagrams.md) — 클래스 다이어그램 및 실행 흐름 시각화
- [ADR-0005](adr/0005-investor-persona-consensus-model.md) — 10+1 페르소나 합의 모델 결정
- [ADR-0008](adr/0008-pydantic-settings-dataclasses-split.md) — TradingConfig/KISConfig 분리 결정
