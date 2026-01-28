# SPEC-INFRA-001: 수용 기준 (Acceptance Criteria)

## 개요 (Overview)

SPEC-INFRA-001의 완료를 확인하기 위한 Given-When-Then 형식의 수용 기준입니다.

---

## 수용 기준 (Acceptance Criteria)

### AC-001: 진입점 파일 존재

**Given:** 프로젝트가 설치되어 있고 pyproject.toml이 존재

**When:** 개발자가 파일 시스템을 검사

**Then:** src/stock_manager/main.py 파일이 존재해야 함

**검증 방법:**
```bash
test -f src/stock_manager/main.py
echo $?  # 0이어야 함
```

---

### AC-002: main 함수 export

**Given:** main.py 파일이 존재

**When:** Python이 main 모듈을 import

**Then:** main() 함수가 callable로 export되어야 함

**검증 방법:**
```python
# Python REPL
from stock_manager.main import main
assert callable(main)
```

---

### AC-003: pyproject.toml과 진입점 일치

**Given:** pyproject.toml에 `[project.scripts]` 섹션이 존재

**When:** 설치 후 stock-manager 명령을 실행

**Then:** main.py의 main() 함수가 호출되어야 함

**검증 방법:**
```bash
pip install -e .
stock-manager --help  # 또는
python -m stock_manager.main
```

---

### AC-004: KISConfig env_prefix 제거

**Given:** kis_config.py가 KISConfig를 정의

**When:** KISConfig 클래스 정의를 검사

**Then:** 내부 Config 클래스가 존재하지 않아야 함

**검증 방법:**
```python
# Python REPL
from stock_manager.adapters.broker.kis.kis_config import KISConfig
assert not hasattr(KISConfig, 'Config')
```

---

### AC-005: SLACK_BOT_TOKEN 환경변수 로드

**Given:** .env 파일에 SLACK_BOT_TOKEN이 설정되어 있음

**When:** AppConfig를 초기화

**Then:** slack_bot_token 필드가 올바르게 로드되어야 함

**검증 방법:**
```python
# .env 파일 내용
# SLACK_BOT_TOKEN=test-token-123

# Python REPL
from stock_manager.config.app_config import AppConfig
config = AppConfig()
assert config.slack_bot_token == "test-token-123"
```

---

### AC-006: KIS_SLACK_BOT_TOKEN 불필요

**Given:** SLACK_BOT_TOKEN만 설정되어 있고 KIS_SLACK_BOT_TOKEN은 설정되지 않음

**When:** KISConfig를 초기화

**Then:** ValidationError 없이 초기화되어야 함

**검증 방법:**
```python
# 환경 설정
import os
os.environ['SLACK_BOT_TOKEN'] = 'test-token'
os.environ['SLACK_CHANNEL_ID'] = 'C123456'
os.environ['KIS_APP_KEY'] = 'test-key'
os.environ['KIS_APP_SECRET'] = 'test-secret'
# KIS_SLACK_BOT_TOKEN는 설정하지 않음

# Python REPL
from stock_manager.adapters.broker.kis.kis_config import KISConfig
config = KISConfig()  # ValidationError 없어야 함
assert config.slack_bot_token == 'test-token'
```

---

### AC-007: KIS 설정 정상 로드

**Given:** KIS_APP_KEY, KIS_APP_SECRET 환경변수가 설정되어 있음

**When:** KISConfig를 초기화

**Then:** kis_app_key, kis_app_secret 필드가 올바르게 로드되어야 함

**검증 방법:**
```python
# 환경 설정
import os
os.environ['KIS_APP_KEY'] = 'my-app-key'
os.environ['KIS_APP_SECRET'] = 'my-app-secret'

# Python REPL
from stock_manager.adapters.broker.kis.kis_config import KISConfig
config = KISConfig()
assert config.kis_app_key == 'my-app-key'
assert config.kis_app_secret == 'my-app-secret'
```

---

### AC-008: 애플리케이션 시작 시 로그 출력

**Given:** 모든 필수 환경변수가 설정되어 있음

**When:** python -m stock_manager.main을 실행

**Then:** "Starting Stock Manager Trading Bot..." 메시지가 출력되어야 함

**검증 방법:**
```bash
python -m stock_manager.main 2>&1 | grep "Starting Stock Manager"
echo $?  # 0이어야 함 (메시지 발견)
```

---

### AC-009: 환경변수 누락 시 명확한 에러

**Given:** 필수 환경변수가 설정되지 않음

**When:** AppConfig를 초기화

**Then:** Pydantic ValidationError가 발생하고 누락된 필드명이 메시지에 포함되어야 함

**검증 방법:**
```python
# 모든 환경변수 제거
import os
for key in list(os.environ.keys()):
    if 'SLACK' in key or 'KIS' in key:
        del os.environ[key]

# Python REPL
try:
    from stock_manager.config.app_config import AppConfig
    config = AppConfig()
    assert False, "Should have raised ValidationError"
except Exception as e:
    assert 'slack_bot_token' in str(e).lower() or 'missing' in str(e).lower()
```

---

### AC-010: 진입점 실행 후 안전 종료

**Given:** main()이 실행 중이지만 치명적 에러 발생

**When:** main() 내부에서 예외 발생

**Then:** 에러를 로깅하고 non-zero exit code로 종료해야 함

**검증 방법:**
```python
# test_main_exit_code.py
import subprocess
result = subprocess.run(
    ["python", "-m", "stock_manager.main"],
    env={**os.environ, "SLACK_BOT_TOKEN": ""},  # 에러 유발
    capture_output=True
)
assert result.returncode != 0
assert b"error" in result.stderr.lower() or b"error" in result.stdout.lower()
```

---

## 통합 테스트 시나리오 (Integration Test Scenarios)

### 시나리오 1: 정상 시작 흐름

```gherkin
Feature: 애플리케이션 정상 시작

  Scenario: 모든 필수 환경변수가 설정된 경우
    Given SLACK_BOT_TOKEN이 "test-token"으로 설정되어 있음
    And SLACK_CHANNEL_ID가 "C123456"으로 설정되어 있음
    And KIS_APP_KEY가 "test-key"로 설정되어 있음
    And KIS_APP_SECRET가 "test-secret"으로 설정되어 있음
    And 데이터베이스가 실행 중임
    When 사용자가 "python -m stock_manager.main"을 실행
    Then "Starting Stock Manager Trading Bot..." 메시지가 출력됨
    And "Configuration loaded successfully" 메시지가 출력됨
    And 프로세스가 초기화 단계까지 진행됨
```

---

### 시나리오 2: 환경변수 누락

```gherkin
Feature: 환경변수 누락 처리

  Scenario: SLACK_BOT_TOKEN이 누락된 경우
    Given KIS_APP_KEY와 KIS_APP_SECRET는 설정되어 있음
    But SLACK_BOT_TOKEN이 설정되어 있지 않음
    When 사용자가 애플리케이션을 시작
    Then ValidationError가 발생
    And 에러 메시지에 "slack_bot_token"이 포함됨
    And 프로세스가 exit code 1로 종료됨
```

---

### 시나리오 3: 데이터베이스 연결 실패

```gherkin
Feature: 데이터베이스 연결 실패 처리

  Scenario: PostgreSQL에 연결할 수 없는 경우
    Given 모든 필수 환경변수가 설정되어 있음
    But PostgreSQL이 실행 중이지 않음
    When 사용자가 애플리케이션을 시작
    Then "Database connection failed" 메시지가 출력됨
    And 에러 스택 트레이스가 로깅됨
    And 프로세스가 안전하게 종료됨
```

---

## 품질 게이트 (Quality Gates)

### 게이트 1: 파일 구조 완결성

- [ ] src/stock_manager/main.py 존재
- [ ] main() 함수가 callable
- [ ] pyproject.toml 진입점과 일치

### 게이트 2: 환경설정 정합성

- [ ] KISConfig에 Config 클래스 없음
- [ ] SLACK_BOT_TOKEN으로 로드 가능
- [ ] KIS_SLACK_BOT_TOKEN 불필요
- [ ] KIS_APP_KEY, KIS_APP_SECRET 정상 로드

### 게이트 3: 실행 가능성

- [ ] python -m stock_manager.main 실행 가능
- [ ] stock-manager 명령 실행 가능 (설치 후)
- [ ] 로그 메시지 출력됨
- [ ] 에러 시 명확한 메시지와 종료 코드

### 게이트 4: 테스트 커버리지

- [ ] 단위 테스트 통과
- [ ] 통합 테스트 통과
- [ ] 모든 AC 검증 완료

---

## 자동화된 검증 (Automated Validation)

### 검증 스크립트

```bash
#!/bin/bash
# verify_spec_infra_001.sh

set -e

echo "=== SPEC-INFRA-001 Verification ==="

# AC-001: File exists
echo "Checking AC-001: main.py exists..."
test -f src/stock_manager/main.py
echo "  PASS: main.py exists"

# AC-002: main function export
echo "Checking AC-002: main function exported..."
python -c "from stock_manager.main import main; assert callable(main)"
echo "  PASS: main() is callable"

# AC-004: Config class removed
echo "Checking AC-004: KISConfig Config removed..."
python -c "from stock_manager.adapters.broker.kis.kis_config import KISConfig; assert not hasattr(KISConfig, 'Config')"
echo "  PASS: Config class removed"

# AC-006: SLACK_BOT_TOKEN loads without KIS_ prefix
echo "Checking AC-006: Environment variable loading..."
export SLACK_BOT_TOKEN=test-token
export SLACK_CHANNEL_ID=C123456
export KIS_APP_KEY=test-key
export KIS_APP_SECRET=test-secret
python -c "from stock_manager.adapters.broker.kis.kis_config import KISConfig; c = KISConfig(); assert c.slack_bot_token == 'test-token'"
echo "  PASS: SLACK_BOT_TOKEN loads correctly"

echo "=== All Checks Passed ==="
```

---

## Definition of Done

SPEC-INFRA-001은 다음 조건이 모두 충족될 때 "완료"로 간주합니다:

1. **구현 완료**
   - [ ] main.py 생성 완료
   - [ ] kis_config.py 수정 완료
   - [ ] 모든 코드가 리뷰됨

2. **테스트 완료**
   - [ ] 모든 수용 기준 통과
   - [ ] 단위 테스트 작성 완료
   - [ ] 통합 테스트 통과

3. **문서화 완료**
   - [ ] .env.example 업데이트
   - [ ] README에 진입점 사용법 추가
   - [ ] Migration guide 제공 (필요시)

4. **품질 게이트 통과**
   - [ ] ruff linting 통과
   - [ ] mypy type checking 통과
   - [ ] 테스트 커버리지 80% 이상
