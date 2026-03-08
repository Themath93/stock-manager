# Slack `/sm` Command Protocol for AI

이 문서는 AI 에이전트가 Slack `/sm` 명령을 생성하거나 추천할 때 따라야 하는 규칙입니다.
목표는 `잘못된 플래그 조합`, `위험한 실전 전환`, `운영자 의도와 다른 명령 생성`을 막는 것입니다.

## 역할

AI는 `/sm` 명령을 다음 원칙으로 생성해야 합니다.

- 기본값은 `보수적`이어야 한다.
- 사용자가 실전을 명시하지 않으면 `mock`를 우선한다.
- 문법상 가능한 명령이 아니라, 정책상 안전한 명령만 제안한다.
- 지원되지 않는 플래그를 발명하지 않는다.

## 지원 서브커맨드

정확히 아래만 사용한다.

- `start`
- `stop`
- `status`
- `config`
- `help`
- `balance`
- `orders`
- `sell-all`

지원되지 않는 `/sm` 명령은 생성하지 않는다.

## `start`에서 허용되는 플래그

정확히 아래만 사용한다.

- `--strategy NAME`
- `--symbols A,B`
- `--duration SEC`
- `--mock`
- `--no-mock`
- `--order-quantity N`
- `--run-interval SEC`
- `--auto-discover`
- `--discovery-limit N`
- `--fallback-symbols A,B`
- `--llm-mode off|selective`

절대 생성하지 말 것:

- `--confirm-live`
- `--execute`
- `--price`
- `--websocket-monitoring-enabled`
- `--websocket-execution-notice-enabled`

이들은 CLI 경로에서는 있을 수 있어도 `/sm` parser에는 없다.

## 필수 제약 조건

AI는 아래 규칙을 만족하는 명령만 만들어야 한다.

- `--auto-discover`를 쓰면 반드시 `--strategy`를 함께 준다.
- `--discovery-limit`를 쓰면 반드시 `--strategy`를 함께 준다.
- `--fallback-symbols`를 쓰면 반드시 `--auto-discover`를 함께 준다.
- `--llm-mode`를 쓰면 반드시 `--strategy`를 함께 준다.
- `--llm-mode selective`를 쓰면 반드시 `--strategy consensus`를 함께 준다.

위 규칙을 만족하지 않으면 명령을 생성하지 말고, 조건을 먼저 설명한다.

## 모드 선택 규칙

기본 규칙:
- 사용자가 실전을 명시하지 않으면 `--mock`를 붙인다.
- 사용자가 실전을 명시한 경우에만 `--no-mock`를 붙인다.
- 사용자가 모드를 명확히 주지 않았고 조직 정책을 모르면 `--mock`를 붙이는 것이 기본이다.

실전 관련 규칙:
- `/sm start --no-mock`는 가능하지만 promotion gate에서 차단될 수 있다.
- AI는 실전 명령을 생성할 때 반드시 `promotion gate가 통과되어 있어야 한다`는 경고를 함께 준다.
- `/sm` 경로에는 `--confirm-live`가 없으므로, 이를 안내에 섞지 않는다.

## 기본값

사용자가 값을 주지 않으면 내부 기본값은 아래라고 이해한다.

- `duration_sec = 0`
- `order_quantity = 1`
- `run_interval_sec = 60.0`
- `strategy_auto_discover = false`
- `strategy_discovery_limit = 20`
- `llm_mode = off`
- `is_mock = None`
  이 경우 런타임은 env의 `KIS_USE_MOCK`를 따른다.

하지만 AI는 운영 명확성을 위해 `start`를 추천할 때 가능하면 `--mock` 또는 `--no-mock`를 명시하는 편이 낫다.

## 응답 규칙

사용자 의도별 추천 방식:

- 세션 시작 요청:
  명령 한 줄과 핵심 주의점 한 줄을 준다.
- 세션 중 상태 확인 요청:
  `/sm status`
- 현재 설정 확인 요청:
  `/sm config`
- 잔고 요청:
  `/sm balance`
- 당일 주문 요청:
  `/sm orders`
- 긴급 청산 요청:
  먼저 `/sm sell-all`, 실행 의사가 명확하면 `/sm sell-all --confirm`

## 안전 우선순위

AI는 다음 우선순위를 따른다.

1. `mock`
2. `짧은 duration`
3. `작은 order-quantity`
4. `명시적 symbols`
5. 그 다음에만 `auto-discover`

즉, 모호한 요청에 대해 바로 이런 명령을 만들지 않는다.

```text
/sm start --strategy consensus --auto-discover --no-mock
```

더 안전한 기본 예시는 아래다.

```text
/sm start --strategy consensus --symbols 005930,000660 --duration 1800 --order-quantity 1 --mock
```

## 권장 생성 패턴

### 1. 가장 안전한 기본 시작

```text
/sm start --strategy consensus --symbols 005930,000660 --duration 1800 --order-quantity 1 --mock
```

언제 쓰나:
- 사용자가 “일단 테스트용으로 돌려보자”라고 할 때

### 2. 자동 탐색 mock 시작

```text
/sm start --strategy consensus --auto-discover --discovery-limit 7 --fallback-symbols 005930,000660 --duration 1800 --order-quantity 1 --mock
```

언제 쓰나:
- 사용자가 종목 자동 탐색을 원할 때

### 3. selective LLM mock 시작

```text
/sm start --strategy consensus --auto-discover --discovery-limit 7 --fallback-symbols 005930,000660 --llm-mode selective --duration 1800 --order-quantity 1 --mock
```

언제 쓰나:
- 사용자가 consensus 전략에서 selective LLM overlay를 원할 때

### 4. 실전 시작

```text
/sm start --strategy consensus --symbols 005930,000660 --duration 1800 --order-quantity 1 --no-mock
```

이 명령을 제안할 때 반드시 같이 말할 것:
- promotion gate가 통과되어 있어야 함
- mock 검증을 먼저 끝내는 것이 권장됨

## 생성 금지 예시

잘못된 예시:

```text
/sm start --llm-mode selective --mock
```

이유:
- `--llm-mode`는 `--strategy`가 필요하다.

잘못된 예시:

```text
/sm start --strategy graham --llm-mode selective --mock
```

이유:
- selective는 consensus 전용이다.

잘못된 예시:

```text
/sm start --fallback-symbols 005930,000660 --mock
```

이유:
- `--fallback-symbols`는 `--auto-discover` 없이는 불가하다.

잘못된 예시:

```text
/sm start --strategy consensus --confirm-live --no-mock
```

이유:
- `/sm`에는 `--confirm-live`가 없다.

## 채널 가시성 이해

AI는 Slack 응답 visibility도 이해해야 한다.

- `start`, `stop`, `sell-all --confirm` 결과는 채널에 보일 수 있다.
- `status`, `config`, `balance`, `orders`, `help`, `sell-all` 미리보기는 보통 ephemeral이다.

따라서 공개 채널에서 테스트 명령을 추천할 때는 더 보수적으로 생성한다.

## 출력 포맷 권장

AI가 실제 사용자에게 명령을 추천할 때는 다음 포맷이 가장 안전하다.

```text
추천 명령:
/sm start --strategy consensus --symbols 005930,000660 --duration 1800 --order-quantity 1 --mock

주의:
- mock 모드입니다.
- selective LLM은 현재 consensus 전략에서만 가능합니다.
```
