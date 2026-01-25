---
id: SPEC-OBSERVABILITY-001
version: "1.0.0"
status: "completed"
created: "2026-01-25"
updated: "2026-01-25"
completed: "2026-01-25"
author: "Alfred"
priority: "HIGH"
tags: ["observability", "logging", "slack", "alerts"]
lifecycle: "spec-first"
related_specs: []
---

# HISTORY

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-25 | Alfred | 초기 문서 작성 |
| 1.1.0 | 2026-01-25 | Alfred | 구현 완료 및 동기화 |

# IMPLEMENTATION STATUS

| Phase | Status | Completed Date | Notes |
|-------|--------|----------------|-------|
| Phase 1: 기반 구조 | ✅ 완료 | 2026-01-25 | AlertLevel, AlertMapping, SlackHandlerConfig 구현 |
| Phase 2: AlertMapper | ✅ 완료 | 2026-01-25 | 로그 레벨 매핑 로직 구현 |
| Phase 3: SlackFormatter | ✅ 완료 | 2026-01-25 | 포맷팅 및 민감 정보 마스킹 구현 |
| Phase 4: SlackHandler | ✅ 완료 | 2026-01-25 | logging.Handler 통합 완료 |
| Phase 5: 중복 제거 및 보안 | ✅ 완료 | 2026-01-25 | 중복 필터 및 마스킹 강화 |
| Phase 6: 테스트 및 통합 | ✅ 완료 | 2026-01-25 | 95% 커버리지 달성 |
| Phase 7: 문서화 | ✅ 완료 | 2026-01-25 | API 문서 완료 |

### 품질 지표
- **테스트 커버리지**: 95% (목표 85% 초과)
- **테스트 통과율**: 100% (57/57 tests passed)
- **TRUST 5 준수**: 준수 완료

---

# 로그 레벨 기반 Slack 알림 시스템

## 1. 개요

본 SPEC은 Python 표준 logging 모듈과 Slack 통합을 통한 로그 레벨 기반 알림 시스템을 구현하기 위한 요구사항을 정의합니다. 기존 Slack 유틸리티를 개선하고, logging.Handler를 통합하여 비동기 알림 전송 기능을 제공합니다.

## 2. 시스템 컨텍스트

### 2.1 기존 시스템 분석

| 구성요소 | 현재 상태 | 개선 필요 사항 |
|----------|-----------|----------------|
| SlackClient | `src/stock_manager/utils/slack.py` | logging 모듈 통합 필요 |
| 메시지 포맷팅 | 단순 텍스트 | 구조화된 로그 포맷 필요 |
| 전송 방식 | 동기 호출 | 비동기 전송으로 개선 필요 |
| 로그 레벨 매핑 | 기본 프리픽스만 | 체계적 레벨별 알림 정책 필요 |

### 2.2 새로운 아키텍처

```
src/stock_manager/adapters/observability/
├── slack_handler.py      # logging.Handler 구현
├── alert_mapper.py       # 로그 레벨 → Slack 알림 매핑
└── slack_formatter.py    # 구조화된 로그 포맷터
```

### 2.3 의존성

| 의존성 | 버전 | 용도 |
|--------|------|------|
| slack-sdk | >=3.27 | Slack WebClient (이미 설치됨) |
| Python logging | 표준 라이브러리 | 로깅 프레임워크 |
| asyncio | 표준 라이브러리 | 비동기 전송 |
| pydantic-settings | >=2.4 | 설정 관리 (이미 설치됨) |

---

# Event-Driven Requirements (이벤트 주도 요구사항)

### ED-001: 에러 로그 기록 이벤트
**설명:** 애플리케이션에서 ERROR 또는 CRITICAL 레벨 로그 기록

**트리거:** logger.error() 또는 logger.critical() 호출

**동작:**
1. LogRecord 생성
2. SlackHandler.emit() 트리거
3. AlertMapper에서 알림 레벨 결정
4. 비동기 큐에 메시지 추가
5. Slack API로 알림 전송

**출력:**
- 성공: Slack 메시지 전송 완료
- 실패: 내부 로그에 에러 기록, 애플리케이션 동작에는 영향 없음

---

### ED-002: 장애 레벨 결정 이벤트
**설명:** 로그 레벨에 따라 알림 범위 결정

**트리거:** LogRecord 수신

**동작:**
1. CRITICAL: 즉시 알림 + 스택 트레이스 포함
2. ERROR: 즉시 알림
3. WARNING: 배치 전송 (5분 집계)
4. INFO: 알림 없음

**출력:**
- 알림 대상 결정
- 메시지 포맷 결정

---

# When-Then Requirements (조건-결과 요구사항)

### WT-001: CRITICAL 레벨 알림 조건
**When:** logger.critical()이 호출되는 경우

**Then:**
1. 즉시 Slack으로 알림 전송
2. 스택 트레이스 포함
3. 붉은색 (!) 이모지로 표시
4. 채널: #alerts-critical

**검증:** 메시지가 5초 이내에 Slack에 도착

---

### WT-002: ERROR 레벨 알림 조건
**When:** logger.error()가 호출되는 경우

**Then:**
1. 즉시 Slack으로 알림 전송
2. 에러 메시지와 context 포함
3. 빨간색 (x) 이모지로 표시
4. 채널: #alerts-errors

**검증:** 메시지가 10초 이내에 Slack에 도착

---

### WT-003: WARNING 레벨 배치 처리
**When:** logger.warning()가 호출되는 경우

**Then:**
1. 메시지를 배치 큐에 추가
2. 5분 동안 수집
3. 집계된 메시지를 하나로 전송
4. 노란색 (warning) 이모지로 표시
5. 채널: #alerts-warnings

**검증:** 5분 후 집계된 메시지가 전송됨

---

### WT-004: INFO 레벨 필터링
**When:** logger.info()가 호출되는 경우

**Then:**
1. Slack으로 전송하지 않음
2. 파일/콘솔 핸들러로만 처리

**검증:** Slack에 INFO 메시지가 도착하지 않음

---

# Wherewithal Requirements (자원/환경 요구사항)

### WH-001: Slack 설정
**필요 자원:**
- `SLACK_BOT_TOKEN`: Slack Bot Token (xoxb-*)
- `SLACK_ALERT_CHANNEL_CRITICAL`: CRITICAL 알림 채널 ID
- `SLACK_ALERT_CHANNEL_ERROR`: ERROR 알림 채널 ID
- `SLACK_ALERT_CHANNEL_WARNING`: WARNING 알림 채널 ID

**검증:** 모든 환경 변수가 설정되어 있어야 핸들러 초기화 가능

---

### WH-002: 로거 설정
**필요 환경:**
- 애플리케이션 로거에 SlackHandler 추가
- 로그 레벨 설정 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- 기본 포맷터: SlqckFormatter

**검증:** logging.getLogger()가 SlackHandler를 포함

---

# Unwanted Behavior Requirements (금지 동작 요구사항)

### UB-001: 로깅이 애플리케이션 성능에 영향 금지
**설명:** Slack 전송 실패가 애플리케이션 동작을 방해하면 안 됨

**금지 동작:**
- Slack API 타임아웃으로 애플리케이션 블록
- 전송 실패로 예외 발생
- 로깅으로 인한 주요 로직 지연

**구현:**
- 모든 Slack 전송은 비동기 (background thread)
- 실패 시 내부 로그에만 기록
- 타임아웃 설정 (3초)

---

### UB-002: 중복 알림 방지
**설명:** 동일 에러에 대한 중복 알림을 방지

**금지 동작:**
- 1분 이내 동일 메시지 재전송
- 스택 트레이스가 같은 에러 중복 알림

**구현:**
- 메시지 해시 기반 중복 제거
- 1분 윈도우 내 중복 필터

---

### UB-003: 민감 정보 노출 금지
**설명:** 로그에 포함된 민감 정보가 Slack으로 전송되면 안 됨

**금지 동작:**
- 토큰, 비밀키, API 키 전송
- 개인정보 (PII) 전송

**구현:**
- SlackFormatter에서 자동 마스킹
- 키워드 기반 필터링 (token, secret, password, api_key)

---

# Optional Requirements (선택 요구사항)

### OP-001: 멀티스레딩 최적화
**설명:** 멀티스레드 환경에서 안전한 큐 관리

**구현 옵션:**
- queue.Queue 사용 (기본)
- asyncio.Queue 사용 (비동기 환경)

**권장:** 애플리케이션 패턴에 따라 선택

---

### OP-002: 메트릭 수집
**설명:** 알림 전송 통계 수집

**구현 옵션:**
- 전송 성공/실패 카운터
- 평균 전송 시간 추적
- 배치 큐 사이즈 모니터링

**권장:** 운영 관점에서 유용

---

# Ubiquitous Requirements (전반적 요구사항)

### UBQ-001: Python 표준 logging 호환
**시스템은 항상 Python 표준 logging.Handler를 상속해야 한다.**

- logging.Handler의 모든 표준 메서드 구현 (emit, close, format)
- 표준 LogRecord 처리
- 기존 logging 설정과 호환

---

### UBQ-002: 역호환성 유지
**시스템은 기존 SlackClient와 호환되어야 한다.**

- 기존 SlackClient 클래스 유지
- 새로운 SlackHandler는 SlackClient 사용
- 기존 코드 수정 불필요

---

### UBQ-003: 테스트 용이성
**시스템은 테스트 가능하도록 설계되어야 한다.**

- MockSlackHandler 제공
- 설정 주입 가능
- 전송 결과 검증 가능

---

## 3. 데이터 모델

### 3.1 AlertLevel

```python
from enum import Enum

class AlertLevel(Enum):
    """알림 레벨 정의"""
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"
```

### 3.2 AlertMapping

```python
from dataclasses import dataclass

@dataclass
class AlertMapping:
    """로그 레벨 → 알림 설정 매핑"""
    log_level: int
    alert_level: AlertLevel
    channel: str
    emoji: str
    immediate: bool  # 즉시 전송 여부
    batch_window: int | None  # 배치 윈도우 (초)
```

### 3.3 SlackHandlerConfig

```python
from pydantic import BaseModel

class SlackHandlerConfig(BaseBaseModel):
    """Slack 핸들러 설정"""
    bot_token: str
    critical_channel: str
    error_channel: str
    warning_channel: str
    timeout: float = 3.0
    batch_interval: int = 300  # 5분
    enable_duplicates_filter: bool = True
    duplicate_window: int = 60  # 1분
```

## 4. 인터페이스 정의

### 4.1 AlertMapper

```python
class AlertMapper:
    """로그 레벨 → 알림 설정 매핑"""

    def get_alert_mapping(self, log_level: int) -> AlertMapping:
        """로그 레벨에 따른 알림 설정 반환"""
        pass

    def should_alert(self, log_level: int) -> bool:
        """알림 전송 여부 결정"""
        pass
```

### 4.2 SlackFormatter

```python
class SlackFormatter(logging.Formatter):
    """Slack 메시지 포맷터"""

    def format(self, record: logging.LogRecord) -> str:
        """LogRecord를 Slack 메시지로 포맷팅"""
        pass

    def mask_sensitive_data(self, message: str) -> str:
        """민감 정보 마스킹"""
        pass
```

### 4.3 SlackHandler

```python
class SlackHandler(logging.Handler):
    """Slack 알림 로깅 핸들러"""

    def __init__(self, config: SlackHandlerConfig):
        """핸들러 초기화"""
        pass

    def emit(self, record: logging.LogRecord) -> None:
        """LogRecord 처리 및 전송"""
        pass

    def close(self) -> None:
        """핸들러 종료 및 정리"""
        pass
```

## 5. 성공 기준

1. **기능 완료:** 모든 EARS 요구사항 구현
2. **테스트 커버리지:** 최소 85% (pytest 기준)
3. **성능:** Slack 전송이 주요 로직에 영향을 주지 않음 (비동기 처리)
4. **안정성:** Slack API 실패 시 애플리케이션 동작에 영향 없음
5. **호환성:** 기존 SlackClient와 역호환 유지
