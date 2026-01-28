# SPEC-INFRA-001: 구현 계획 (Implementation Plan)

## 구현 마일스톤 (Implementation Milestones)

### 1차 마일스톤: 진입점 생성 (Priority: HIGH)

**목표:** 애플리케이션 진입점 파일 생성

**작업:**
- [ ] `src/stock_manager/main.py` 파일 생성
- [ ] `main()` 함수 구현
- [ ] 설정 로딩 로직 추가
- [ ] 기본 서비스 초기화 로직 추가
- [ ] 에러 핸들링 및 로깅 추가

**검증:**
```bash
# 파일 존재 확인
ls -la src/stock_manager/main.py

# 진입점 실행 테스트
python -m stock_manager.main
```

**완료 기준:**
- main.py 파일이 존재하고 main() 함수를 export
- `python -m stock_manager.main` 실행 시 ImportError 없음
- 로그 메시지가 출력됨

---

### 2차 마일스톤: 환경설정 접두사 수정 (Priority: HIGH)

**목표:** KISConfig env_prefix 문제 해결

**작업:**
- [ ] `kis_config.py`에서 Config 클래스 제거
- [ ] KISConfig가 AppConfig 설정을 상속하도록 수정
- [ ] 환경변수 매핑 검증
- [ ] 기존 테스트가 통과하는지 확인

**검증:**
```python
# 테스트 코드
from stock_manager.config.app_config import AppConfig
from stock_manager.adapters.broker.kis.kis_config import KISConfig

# AppConfig로 SLACK_BOT_TOKEN 로드 가능해야 함
config = AppConfig()
assert hasattr(config, 'slack_bot_token')

# KISConfig도 동일하게 동작해야 함
kis_config = KISConfig()
assert hasattr(kis_config, 'slack_bot_token')
```

**완료 기준:**
- KISConfig 초기화 시 KIS_SLACK_BOT_TOKEN 요구하지 않음
- SLACK_BOT_TOKEN 환경변수로 정상 초기화
- 기존 동작 유지 (KIS_APP_KEY, KIS_APP_SECRET)

---

### 3차 마일스톤: 완전한 애플리케이션 시작 검증 (Priority: MEDIUM)

**목표:** 실제 환경에서 애플리케이션 시작 가능 확인

**작업:**
- [ ] .env.example 파일 업데이트
- [ ] 완전한 시작 흐름 테스트
- [ ] 에러 시나리오 테스트
- [ ] 로그 출력 검증

**검증:**
```bash
# 1. 환경변수 설정
export SLACK_BOT_TOKEN=test-token
export SLACK_CHANNEL_ID=C123456
export KIS_APP_KEY=test-key
export KIS_APP_SECRET=test-secret

# 2. 애플리케이션 시작
python -m stock_manager.main

# 3. 또는 pyproject.toml 스크립트 사용
pip install -e .
stock-manager
```

**완료 기준:**
- 애플리케이션이 정상적으로 시작
- 설정이 올바르게 로드됨
- 에러 발생 시 명확한 메시지 출력

---

## 기술 접근 (Technical Approach)

### 1. 파일 구조

```
src/stock_manager/
├── __init__.py
├── main.py                    # NEW - Entry point
├── config/
│   ├── __init__.py
│   └── app_config.py          # MODIFY - Document env behavior
└── adapters/
    └── broker/
        └── kis/
            ├── __init__.py
            └── kis_config.py  # MODIFY - Remove env_prefix
```

### 2. Pydantic Settings 동작 이해

**env_prefix 작동 원리:**
```python
class AppConfig(BaseSettings):
    slack_bot_token: str
    # Reads from: SLACK_BOT_TOKEN

class KISConfig(AppConfig):
    class Config:
        env_prefix = "KIS_"
    # Now reads from: KIS_SLACK_BOT_TOKEN (PROBLEM!)
```

**해결 방법:**
```python
class KISConfig(AppConfig):
    pass  # Simply inherit without overriding Config
    # Reads from: SLACK_BOT_TOKEN (correct!)
```

### 3. 에러 핸들링 전략

**환경변수 누락 시:**
- Pydantic가 자동으로 ValidationError 발생
- main()에서 try-except로 캡처
- 사용자 친화적 에러 메시지 출력

**데이터베이스 연결 실패 시:**
- 연결 실패를 명확히 로깅
- 재시도 로직 (선택 사항)
- 안전한 종료

---

## 위험 완화 (Risk Mitigation)

### 위험 1: 기존 환경설정 호환성

**위험:** 기존 사용자가 KIS_SLACK_BOT_TOKEN을 사용 중일 수 있음

**완화:**
- 마이그레이션 가이드 제공
- 이중 환경변수 지원 (일시적)
- 명확한 문서화

### 위험 2: Circle Import

**위험:** main.py에서 여러 모듈 import 시 순환 의존성 발생 가능

**완화:**
- main.py에서는 최소한의 import만 수행
- 실제 로직은 함수 내부에서 지연 import (lazy import)
- 의존성 다이어그램 검토

### 위험 3: WorkerMain 구현 의존

**위험:** main.py가 WorkerMain에 의존하지만 구현이 완료되지 않았을 수 있음

**완화:**
- 우선 placeholder WorkerMain 사용
- 또는 main.py를 점진적으로 구현
- 테스트용 mock 서비스 사용

---

## 구현 순서 (Implementation Order)

1. **kis_config.py 수정** (가장 빠름, 영향 범위 작음)
   - Config 클래스 제거
   - 테스트로 검증

2. **main.py 생성** (핵심 작업)
   - 기본 구조 구현
   - 설정 로딩
   - 서비스 초기화 (mock/placeholder)

3. **통합 테스트** (검증)
   - 전체 시작 흐름 테스트
   - 에러 시나리오 테스트

---

## 테스트 전략 (Test Strategy)

### 단위 테스트

```python
# tests/unit/test_main.py
def test_main_entry_point_exists():
    """main.py의 main 함수가 존재하는지 확인"""
    from stock_manager.main import main
    assert callable(main)

def test_config_loads_without_kis_prefix():
    """KISConfig가 KIS_ 접두사 없이 로드되는지 확인"""
    os.environ['SLACK_BOT_TOKEN'] = 'test-token'
    from stock_manager.adapters.broker.kis.kis_config import KISConfig
    config = KISConfig()
    assert config.slack_bot_token == 'test-token'
```

### 통합 테스트

```python
# tests/integration/test_entry_point.py
def test_application_starts():
    """애플리케이션이 시작하는지 통합 테스트"""
    # 모든 필수 환경변수 설정
    # 데이터베이스 mock
    # main() 실행
    # 프로세스가 정상적으로 초기화되는지 확인
```

---

## 다음 단계 (Next Steps)

1. SPEC-INFRA-001 완료 후:
   - SPEC-DB-004 진행 (데이터베이스 스키마 수정)
   - SPEC-FIX-001 진행 (서비스 레이어 수정)
   - SPEC-API-001 진행 (KIS API 수정)

2. SPEC-INFRA-001이 해결하는 문제:
   - 진입점 부재로 인한 실행 불가
   - 환경설정 로드 실패

3. 후속 SPEC들이 의존하는 부분:
   - main.py가 존재해야 통합 테스트 가능
   - 환경설정이 올바르게 로드되어야 서비스 초기화 가능
