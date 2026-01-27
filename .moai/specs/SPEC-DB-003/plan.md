# SPEC-DB-003: Implementation Plan

## 메타데이터

- **SPEC ID**: SPEC-DB-003
- **계획 버전**: 1.0.0
- **마일스톤**: 1단계 (필수 구현)

---

## 구현 마일스톤

### Milestone 1: init_test_db Fixture 구현 (필수)

**목표:** Integration test용 데이터베이스 자동 초기화

#### 작업 항목

1. **conftest.py에 init_test_db fixture 추가**
   - autouse=True, scope="module" 설정
   - 데이터베이스 이름 검증
   - PostgreSQL 연결 및 에러 처리

2. **데이터베이스 생성 로직**
   - postgres(default db)로 연결
   - CREATE DATABASE IF NOT EXISTS
   - 연결 실패 시 skip 처리

3. **마이그레이션 적용**
   - 모든 .sql 파일 순차 적용
   - 0001_init.sql → 0002_add_order_fill_fields.sql → market_lifecycle_schema.sql
   - 실패 시 명확한 에러 메시지

4. **스키마 검증**
   - 필수 테이블 존재 확인
   - enum 타입 존재 확인

### Milestone 2: DB Utils Helper (선택)

**목표:** 재사용 가능한 DB 초기화 헬퍼

#### 작업 항목

1. **db_utils.py 모듈 생성**
   - create_database_if_not_exists()
   - apply_migration()
   - verify_schema()
   - truncate_tables()

2. **fixture와 헬퍼 연동**
   - fixture가 db_utils 사용하도록 리팩토링
   - 코드 중복 제거

---

## 기술 접근 방법

### 1. DDD 개발 방법론 적용

**ANALYZE 단계:**
- 현재 integration test 구조 분석
- 마이그레이션 파일 순서 확인
- PostgreSQL 권한 요구사항 확인

**PRESERVE 단계:**
- 기존 conftest.py fixture 보존
- test_db_url fixture 유지
- 환경 변수 설정 유지

**IMPROVE 단계:**
- init_test_db fixture 추가
- 자동 스키마 초기화
- 테스트 격리 개선

### 2. 수정 전략

**파일 1:** `tests/integration/conftest.py`

**추가 내용:**
- init_test_db fixture (new)
- import 문 추가 (new)

**수정 원칙:**
- 기존 fixture는 보존
- 새 fixture만 추가
- autouse로 자동 실행

**파일 2:** `tests/integration/db_utils.py` (new)

**추가 내용:**
- DB 초기화 헬퍼 함수들
- 스키마 검증 함수
- 데이터 정리 함수

**수정 원칙:**
- 순수 함수형 유틸리티
- fixture와 분리
- 재사용 가능하도록 설계

### 3. 테스트 전략

**기존 테스트 (자동으로 개선됨):**
- Integration tests가 자동으로 유효한 스키마 획득
- 4개 에러가 자동으로 해결됨

**새로운 검증:**
- Fixture 실행 확인
- 스키마 생성 확인
- 테스트 격리 확인

---

## 아키텍처 설계

### Fixture 실행 흐름

```
pytest tests/integration/
        │
        ▼
Fixture Discovery
        │
        ├──▶ test_db_url (existing)
        │    Returns: "postgresql://...stock_manager_test"
        │
        └──▶ init_test_db (NEW, autouse=True)
             │
             ├── 1. Validate db_name == "stock_manager_test"
             ├── 2. Connect to postgres (admin)
             ├── 3. CREATE DATABASE IF NOT EXISTS
             ├── 4. Apply migrations (in order)
             ├── 5. Verify schema
             ├── 6. YIELD to tests
             └── 7. Cleanup (keep database)
        │
        ▼
Test Execution
        │
        ├── test_full_market_lifecycle (now works)
        ├── test_system_state_persistence (now works)
        ├── test_state_recovery_with_orders (now works)
        └── test_daily_settlement_creation (now works)
```

### 코드 구조

**init_test_db Fixture 구조:**

```python
@pytest.fixture(scope="module", autouse=True)
def init_test_db():
    # 1. 환경 변수 확인
    db_url = os.getenv("DATABASE_URL", default_url)
    parsed = urlparse(db_url)
    db_name = parsed.path.lstrip("/")

    # 2. 데이터베이스 이름 검증
    if db_name == "stock_manager":
        raise ValueError("Protecting dev database")
    if db_name != "stock_manager_test":
        pytest.skip("Wrong test database")

    # 3. PostgreSQL 연결
    admin_conn = connect_to_postgres()
    if not admin_conn:
        pytest.skip("PostgreSQL not available")

    # 4. 데이터베이스 생성
    create_database_if_not_exists(admin_conn, db_name)

    # 5. 마이그레이션 적용
    test_conn = connect_to_test_db(db_url)
    for migration in migrations:
        apply_migration(test_conn, migration)

    # 6. 스키마 검증
    verify_schema(test_conn)

    # 7. 테스트 실행
    yield

    # 8. 정리
    pass  # 데이터베이스 유지
```

### DB Utils 모듈 구조

```
tests/integration/db_utils.py
│
├── create_database_if_not_exists(admin_url, db_name)
│   ├── Connect to postgres (admin)
│   ├── Check if db exists
│   ├── CREATE DATABASE if needed
│   └── Return True/False
│
├── apply_migration(db_url, migration_file)
│   ├── Read SQL file
│   ├── Connect to database
│   ├── Execute SQL
│   └── Commit
│
├── verify_schema(db_url, expected_tables)
│   ├── Query information_schema
│   ├── Check table existence
│   └── Return True/False
│
└── truncate_tables(db_url, exclude_tables)
    ├── Get all tables
    ├── Disable triggers
    ├── TRUNCATE each table
    └── Re-enable triggers
```

---

## 위험 요소 및 대응 계획

### Risk 1: PostgreSQL 권한 문제

**위험:** postgres 사용자가 데이터베이스 생성 권한이 없음

**확률:** LOW
**영향:** HIGH

**대응:**
- docker-compose에서 권한 부여 확인
- 권한 없을 경우 skip 메시지 명확화
- 대안: 수동으로 stock_manager_test 생성 문서화

### Risk 2: 마이그레이션 순서 오류

**위험:** 마이그레이션 파일 순서가 틀리면 FK 오류

**확률:** LOW
**영향:** HIGH

**대응:**
- 파일 번호 순서대로 적용
- FK 제약조건 확인
- 순서 변경 시 테스트로 검증

### Risk 3: 개발 데이터베이스 실수로 수정

**위험:** DATABASE_URL 설정 실수로 개발 DB 수정

**확률:** MEDIUM
**영향:** CRITICAL

**대응:**
- 데이터베이스 이름 강력 검증
- stock_manager이면 에러 발생
- 환경 변수 이름 분리 (TEST_DATABASE_URL)

### Risk 4: 테스트 간 데이터 간섭

**위험:** 한 테스트가 다른 테스트 데이터 남김

**확률:** MEDIUM
**영향:** MEDIUM

**대응:**
- 각 테스트가 자신의 데이터 cleanup
- fixture는 데이터베이스만 초기화
- 필요시 truncate_tables() 헬퍼 제공

---

## 성공 기준

### Milestone 1 완료 기준

- [ ] init_test_db fixture 구현 완료
- [ ] stock_manager_test 데이터베이스 자동 생성
- [ ] 모든 마이그레이션 적용 완료
- [ ] 4개 에러 테스트가 PASS로 변경
- [ ] 개발 데이터베이스 보호 검증
- [ ] PostgreSQL 없을 때 skip 정상 작동

### Milestone 2 완료 기준

- [ ] db_utils.py 모듈 생성 완료
- [ ] 재사용 가능한 헬퍼 함수들
- [ ] fixture가 db_utils 사용
- [ ] 코드 중복 제거

---

## 의존성

### 선행 조건

- PostgreSQL 15 실행 중 (docker-compose 또는 로컬)
- postgres 사용자로 데이터베이스 생성 권한
- pytest 환경 설정 완료

### 후속 작업

- Integration tests 자동화
- CI/CD 통합 (선택)

---

## 구현 예상 시간

- Milestone 1: 3-4시간
  - init_test_db fixture 구현: 2시간
  - 마이그레이션 적용 로직: 1시간
  - 테스트 및 검증: 1시간

- Milestone 2: 1-2시간 (선택)
  - db_utils.py 모듈: 1시간
  - fixture 리팩토링: 0.5시간
  - 테스트: 0.5시간

**총 예상 시간:** 4-6시간

---

## 환경 설정 가이드

### 개발 환경

**1. PostgreSQL docker-compose:**
```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
```

**2. 환경 변수:**
```bash
# .env 또는 shell export
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/stock_manager_test"
```

**3. 실행:**
```bash
# PostgreSQL 시작
docker-compose up -d postgres

# Integration tests 실행
pytest tests/integration/ -v
```

### CI/CD 환경 (선택)

**GitHub Actions 예시:**
```yaml
- name: Run integration tests
  env:
    DATABASE_URL: postgresql://postgres:postgres@localhost:5432/stock_manager_test
  run: |
    docker-compose up -d postgres
    pytest tests/integration/ -v
```
