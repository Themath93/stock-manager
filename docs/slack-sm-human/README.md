# Slack `/sm` 명령어 가이드

이 문서는 사람이 Slack에서 `Stock Manager` 봇을 사용할 때 보는 운영 가이드입니다.
목표는 `/sm` 명령을 빠르게, 안전하게, 실수 없이 쓰게 하는 것입니다.

## 한눈에 보기

`/sm`은 Slack에서 트레이딩 세션을 시작하고, 상태를 조회하고, 긴급 청산을 수행하는 명령어입니다.

지원 명령:
- `/sm start`
- `/sm stop`
- `/sm status`
- `/sm config`
- `/sm balance`
- `/sm orders`
- `/sm sell-all`
- `/sm help`

기본 원칙:
- 세션은 한 번에 하나만 실행됩니다.
- 실전은 `--no-mock`를 쓴다고 바로 열리지 않습니다. promotion gate를 통과해야 합니다.
- `sell-all --confirm`는 실제 매도입니다.
- `start`와 `sell-all --confirm`는 사용자별 10초 쿨다운이 있습니다.

## 가장 많이 쓰는 명령

### 1. 모의 세션 시작

```text
/sm start --strategy consensus --symbols 005930,000660 --mock
```

의미:
- `consensus` 전략으로
- 삼성전자, SK하이닉스 두 종목을
- 모의투자 모드에서 시작합니다.

### 2. 자동 탐색으로 세션 시작

```text
/sm start --strategy consensus --auto-discover --discovery-limit 7 --fallback-symbols 005930,000660 --mock
```

의미:
- 종목을 직접 적지 않고 자동 탐색을 사용합니다.
- 최대 7개를 탐색합니다.
- 탐색 실패 시 fallback 종목을 씁니다.

### 3. selective LLM 모드로 시작

```text
/sm start --strategy consensus --auto-discover --discovery-limit 7 --fallback-symbols 005930,000660 --llm-mode selective --mock
```

주의:
- `--llm-mode selective`는 `--strategy consensus`일 때만 허용됩니다.
- 현재 selective는 Dalio persona에만 LLM overlay를 적용합니다.

### 4. 실행 중 상태 확인

```text
/sm status
```

### 5. 계좌 잔고 확인

```text
/sm balance
```

### 6. 당일 주문 내역 확인

```text
/sm orders
```

### 7. 전체 포지션 정리

미리보기:

```text
/sm sell-all
```

실행:

```text
/sm sell-all --confirm
```

## `start` 옵션 설명

`/sm start`에서 쓸 수 있는 주요 옵션:

- `--strategy NAME`
  어떤 전략을 실행할지 지정합니다.
- `--symbols A,B`
  종목 코드를 쉼표로 나열합니다.
- `--duration SEC`
  세션 실행 시간을 초 단위로 제한합니다. `0`이면 수동 종료까지 계속 실행됩니다.
- `--mock`
  모의투자 모드입니다.
- `--no-mock`
  실전투자 모드입니다.
- `--order-quantity N`
  전략이 매수할 때 기본 주문 수량입니다.
- `--run-interval SEC`
  전략 사이클 주기입니다.
- `--auto-discover`
  종목 자동 탐색을 켭니다.
- `--discovery-limit N`
  자동 탐색 최대 종목 수입니다.
- `--fallback-symbols A,B`
  자동 탐색 실패 시 대체 종목입니다.
- `--llm-mode off|selective`
  LLM 보강 모드입니다.

## 조합 규칙

아래 조합은 중요합니다.

- `--auto-discover`는 `--strategy`가 있어야 합니다.
- `--discovery-limit`는 `--strategy`가 있어야 합니다.
- `--fallback-symbols`는 `--auto-discover`가 있어야 합니다.
- `--llm-mode`는 `--strategy`가 있어야 합니다.
- `--llm-mode selective`는 `--strategy consensus`에서만 허용됩니다.
- `--mock`와 `--no-mock`를 동시에 쓰지 않는 것이 좋습니다.
- `--symbols` 없이 `--auto-discover`도 끄면 전략이 사실상 빈 입력으로 시작할 수 있으니, 운영에서는 둘 중 하나는 명확히 주는 편이 안전합니다.

## 각 명령이 Slack에 어떻게 보이는지

- `start`: 채널에 보입니다.
- `stop`: 채널에 보입니다.
- `sell-all --confirm`: 채널에 보입니다.
- `status`: 본인에게만 보입니다.
- `config`: 본인에게만 보입니다.
- `balance`: 본인에게만 보입니다.
- `orders`: 본인에게만 보입니다.
- `sell-all` 미리보기: 본인에게만 보입니다.
- `help`: 본인에게만 보입니다.

## 실전 운영 규칙

- 실전은 반드시 `--no-mock`로 시작합니다.
- 실전 세션은 promotion gate에 걸리면 Slack에서 바로 차단됩니다.
- 실전 전에 최소한 아래 순서를 권장합니다.

1. mock 세션으로 먼저 전략/심볼/자동탐색을 검증합니다.
2. `/sm status`, `/sm balance`, `/sm orders`로 기초 상태를 확인합니다.
3. promotion gate 산출물을 확인합니다.
4. 그 다음에만 `--no-mock`로 시작합니다.

예시:

```text
/sm start --strategy consensus --symbols 005930,000660 --no-mock
```

주의:
- Slack `/sm start`에는 `--confirm-live`가 없습니다.
- 실전 차단은 Slack 레벨이 아니라 promotion gate와 세션 매니저 정책에서 일어납니다.

## 자주 발생하는 실패

### `차단됨: Live trading is blocked by promotion gate ...`

의미:
- 실전 승격 조건을 아직 통과하지 못했습니다.

조치:
- mock 검증 산출물과 promotion gate 파일을 먼저 확인합니다.

### `Session already active`

의미:
- 이미 세션이 돌고 있습니다.

조치:
- `/sm status`로 상태를 확인하고, 필요하면 `/sm stop`을 사용합니다.

### `--llm-mode selective requires --strategy consensus.`

의미:
- selective LLM은 consensus 전용입니다.

조치:
- 전략을 `consensus`로 바꾸거나 `--llm-mode off`로 시작합니다.

### `활성 트레이딩 세션이 없습니다.`

의미:
- `balance`, `orders`, `sell-all`, `stop` 등을 실행할 세션이 없습니다.

조치:
- 먼저 `/sm start ...`로 세션을 시작합니다.

## 추천 운영 예시

모의:

```text
/sm start --strategy consensus --auto-discover --discovery-limit 10 --fallback-symbols 005930,000660 --mock
```

모의 + selective:

```text
/sm start --strategy consensus --auto-discover --discovery-limit 7 --fallback-symbols 005930,000660 --llm-mode selective --mock
```

실전:

```text
/sm start --strategy consensus --symbols 005930,000660 --no-mock
```

긴급 청산:

```text
/sm sell-all
/sm sell-all --confirm
```
