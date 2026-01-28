# SPEC-INFRA-001: Entry Point & Configuration Fix

## 메타데이터

- **SPEC ID**: SPEC-INFRA-001
- **제목**: Entry Point & Configuration Fix
- **생성일**: 2026-01-28
- **상태**: planned
- **버전**: 1.0.0
- **우선순위**: HIGH
- **담당자**: Alfred (workflow-spec)
- **관련 SPEC**: None (최초 인프라 수정)
- **유형**: Infrastructure Fix

---

## 개요 (Overview)

진입점(entry point) 누락과 환경설정 접두사(prefix) 문제를 해결하여 애플리케이션이 정상적으로 시작할 수 있도록 합니다.

**문제 정의:**
1. `pyproject.toml`은 `stock_manager.main:main`을 참조하지만 `src/stock_manager/main.py`가 존재하지 않음
2. `KISConfig`의 `env_prefix = "KIS_"` 설정으로 인해 `SLACK_BOT_TOKEN`이 `KIS_SLACK_BOT_TOKEN`으로 변형되어 초기화 실패
3. 애플리케이션 시작 방법이 없음 (`python -m stock_manager` 실패)

**목표:**
- `main.py` 진입점 생성
- 환경변수 접두사 문제 해결 (Slack 설정 분리)
- 애플리케이션 정상 시작 가능 확인

---

## 요구사항 (Requirements)

### TAG BLOCK

```
TAG-SPEC-INFRA-001-001: main.py 진입점 구현
TAG-SPEC-INFRA-001-002: KISConfig env_prefix 제거
TAG-SPEC-INFRA-001-003: Slack 설정 환경변수 분리
TAG-SPEC-INFRA-001-004: 애플리케이션 시작 검증
```

### 핵심 요구사항

**REQ-UB-001: 진입점 존재**
- 애플리케이션은 반드시 진입점(main.py)을 가져야 한다 (SHALL)
- 진입점은 `main()` 함수를 export해야 한다 (SHALL)

**REQ-UB-002: 환경설정 일관성**
- KIS 관련 설정만 `KIS_` prefix를 사용해야 한다 (SHALL)
- Slack 설정은 `SLACK_` prefix를 사용해야 한다 (SHALL)

**REQ-UN-001: 이중 접두사 금지**
- KISConfig는 환경변수에 KIS_ 접두사를 추가해서는 안 된다 (MUST NOT)
- Slack 필드에 KIS_SLACK_* 형식을 요구해서는 안 된다 (MUST NOT)

---

## 상세 설계 (Specifications)

### 핵심 구현: main.py

**src/stock_manager/main.py (new file):**

```python
"""
Stock Manager Trading Bot Entry Point
"""

import logging
import sys

from stock_manager.config.app_config import AppConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> int:
    """
    Main entry point for the stock manager trading bot.

    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    try:
        logger.info("Starting Stock Manager Trading Bot...")

        # Load configuration
        config = AppConfig()
        logger.info(f"Configuration loaded: KIS Mode={config.kis_mode}")

        # TODO: Initialize services and start worker
        logger.info("Initialization complete")

        return 0

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

### 핵심 수정: kis_config.py

**src/stock_manager/adapters/broker/kis/kis_config.py (modify):**

```python
# BEFORE (문제):
class KISConfig(AppConfig):
    class Config:
        env_prefix = "KIS_"  # 문제 원인

# AFTER (수정):
class KISConfig(AppConfig):
    """한국투자증권 OpenAPI 설정"""
    # Config 클래스 제거로 AppConfig 설정 상속
    pass
```

---

## 추적성 (Traceability)

### TAG Mapping

| TAG | 설명 | 파일 | 상태 |
|-----|------|------|------|
| TAG-SPEC-INFRA-001-001 | main.py 진입점 구현 | main.py | TODO |
| TAG-SPEC-INFRA-001-002 | KISConfig env_prefix 제거 | kis_config.py | TODO |
| TAG-SPEC-INFRA-001-003 | Slack 설정 환경변수 분리 | app_config.py | Existing |
| TAG-SPEC-INFRA-001-004 | 애플리케이션 시작 검증 | main.py | TODO |

---

## 의존성 (Dependencies)

### 선행 SPEC (Prerequisites)
None - 이 SPEC은 독립적으로 실행 가능

### 후속 SPEC (Dependents)
- **SPEC-DB-004**: Database Schema & Type Adaptation
- **SPEC-FIX-001**: Service Layer Corrections
- **SPEC-API-001**: KIS API Integration Fixes
