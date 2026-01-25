# SPEC-KIS-DOCS-001: 인수 기준

## 메타데이터

- **SPEC ID**: SPEC-KIS-DOCS-001
- **생성일**: 2026-01-25
- **마지막 수정일**: 2026-01-25
- **담당자**: Alfred

---

## 개요

KIS OpenAPI 문서 재정비 프로젝트의 인수 기준을 Gherkin 형식(Given-When-Then)으로 정의합니다.

---

## 인수 기준 (Acceptance Criteria)

### AC1: TR_ID 매핑 JSON 생성

**Story**: Excel 파일의 모든 API TR_ID 정보가 JSON으로 변환되어야 한다

#### Scenario 1.1: Excel 파일 파싱 성공

**Given** HTS_OPENAPI.xlsx 파일이 존재하고
**And** 파일에 336개의 API가 포함되어 있을 때
**When** 개발자가 `python scripts/parse_kis_excel.py`를 실행하면
**Then** `docs/kis-openapi/_data/tr_id_mapping.json` 파일이 생성되어야 하고
**And** JSON 파일에 336개의 API 정보가 포함되어야 하고
**And** 각 API는 `api_id`, `api_name`, `live_tr_id`, `paper_tr_id`, `http_method`, `url`, `category` 필드를 가져야 한다

#### Scenario 1.2: 모의 거래 미지원 API 처리

**Given** Excel 파일에 모의 거래 미지원 API가 포함되어 있을 때
**When** 파싱 스크립트가 실행되면
**Then** 해당 API의 `paper_tr_id` 필드는 `null`이거나 `"모의투자 미지원"`이어야 하고
**And** `live_tr_id` 필드는 유효한 값이어야 한다

#### Scenario 1.3: JSON Schema 유효성 검증

**Given** `tr_id_mapping.json` 파일이 생성되었을 때
**When** JSON Schema 검증을 실행하면
**Then** 모든 필수 필드가 존재하고
**And** 데이터 타입이 올바르고
**And** 열거형 값(`http_method`, `is_websocket`)이 유효해야 한다

---

### AC2: REST Client TR_ID 조회

**Story**: REST Client가 API 이름으로 TR_ID를 조회할 수 있어야 한다

#### Scenario 2.1: 실전 TR_ID 조회 성공

**Given** KISRESTClient가 초기화되었고
**And** `tr_id_mapping.json`이 로드되었을 때
**When** 개발자가 `client.get_tr_id("접근토큰발급(P)", is_paper_trading=False)`를 호출하면
**Then** 실전 TR_ID 값이 반환되어야 하고
**And** 반환된 값은 빈 문자열이 아니어야 하고
**And** 반환된 값은 Excel의 "실전 TR_ID" 컬럼 값과 일치해야 한다

#### Scenario 2.2: 모의 TR_ID 조회 성공

**Given** KISRESTClient가 초기화되었고
**And** API가 모의 거래를 지원할 때
**When** 개발자가 `client.get_tr_id("접근토큰발급(P)", is_paper_trading=True)`를 호출하면
**Then** 모의 TR_ID 값이 반환되어야 하고
**And** 반환된 값은 Excel의 "모의 TR_ID" 컬럼 값과 일치해야 한다

#### Scenario 2.3: 모의 미지원 API 예외 처리

**Given** KISRESTClient가 초기화되었고
**And** API가 모의 거래를 지원하지 않을 때
**When** 개발자가 `client.get_tr_id("기간별계좌권리현황조회", is_paper_trading=True)`를 호출하면
**Then** `ValueError` 예외가 발생해야 하고
**And** 예외 메시지에 "모의 투자가 지원되지 않는 API"가 포함되어야 한다

#### Scenario 2.4: 존재하지 않는 API 예외 처리

**Given** KISRESTClient가 초기화되었을 때
**When** 개발자가 `client.get_tr_id("존재하지않는API")`를 호출하면
**Then** `KeyError` 예외가 발생해야 하고
**And** 예외 메시지에 "API를 찾을 수 없습니다"가 포함되어야 한다

#### Scenario 2.5: 요청 헤더에 TR_ID 포함

**Given** KISRESTClient가 초기화되었을 때
**When** 개발자가 API를 호출하면
**Then** 요청 헤더에 `tr_id` 필드가 포함되어야 하고
**And** `tr_id` 값은 실전/모의 환경에 따라 올바른 값이어야 하고
**And** 다른 헤더 필드(`appkey`, `appsecret`, `Authorization`)도 포함되어야 한다

---

### AC3: 문서 카테고리 재구성

**Story**: 문서가 Excel의 "메뉴 위치"에 따라 카테고리별로 재구성되어야 한다

#### Scenario 3.1: 카테고리별 디렉토리 생성

**Given** Excel 파일에 16개의 고유한 "메뉴 위치"가 존재할 때
**When** 문서 재구성 스크립트가 실행되면
**Then** 16개의 카테고리별 디렉토리가 생성되어야 하고
**And** 각 디렉토리에 `index.md` 파일이 존재해야 한다

#### Scenario 3.2: 카테고리별 API 개수 정확성

**Given** Excel 파일의 "메뉴 위치"별 API 개수가 주어졌을 때
**When** 문서 재구성이 완료되면
**Then** 각 카테고리 디렉토리의 API 개수가 Excel과 일치해야 하고
**And** `categories.json` 파일에 정확한 개수가 기록되어야 한다

**예시**:
- OAuth인증: 4개
- 국내주식-주문계좌: 20개
- 국내주식-시세: 17개
- 국내주식-체결: 14개
- 국내주식-랭킹: 12개
- 국내주식-일정: 12개
- 국내주식-기본정보: 2개
- 국내주식-재무정보: 8개
- 국내주식-시장동향: 11개
- 국내주식-실시간: 14개
- 선물옵션: 20개
- 해외주식: 40개
- 해외선물옵션: 15개
- 채권: 10개
- ELW: 20개

#### Scenario 3.3: 기존 문서 마이그레이션

**Given** 기존 문서가 `01-authentication.md`, `02-account-info.md` 등으로 저장되어 있을 때
**When** 문서 재구성이 완료되면
**Then** 기존 문서의 내용이 새로운 카테고리 디렉토리로 이동되어야 하고
**And** TR_ID 정보가 추가되어야 하고
**And** 기존 파일은 삭제되거나 `.backup`으로 이동되어야 한다

---

### AC4: 문서 템플릿 표준화

**Story**: 모든 API 문서는 일관된 템플릿 구조를 따라야 한다

#### Scenario 4.1: 필수 섹션 포함

**Given** API 문서가 생성될 때
**When** 템플릿이 적용되면
**Then** 다음 섹션이 포함되어야 한다:
  - API 개요 (이름, ID, HTTP Method, URL)
  - Request Header (tr_id 포함)
  - Request 파라미터 (쿼리/바디)
  - Response 필드
  - Python 코드 예시
  - 주의사항

#### Scenario 4.2: TR_ID 정보 표시

**Given** API 문서가 생성될 때
**And** API가 실전/모의 TR_ID를 가질 때
**When** Request Header 섹션이 생성되면
**Then** `tr_id` 행이 포함되어야 하고
**And** 실전 TR_ID와 모의 TR_ID가 모두 표시되어야 하고
**And** 형식은 `실전: XXX / 모의: YYY`이어야 한다

#### Scenario 4.3: 모의 미지원 API 표시

**Given** API가 모의 거래를 지원하지 않을 때
**When** 문서가 생성되면
**Then** 주의사항 섹션에 "모의 투자 미지원" 경고가 표시되어야 하고
**And** Request Header에 `모의: 지원되지 않음`이 표시되어야 한다

---

### AC5: Excel 파싱 자동화

**Story**: Excel 파일 변경 시 자동으로 문서가 재생성되어야 한다

#### Scenario 5.1: 파싱 스크립트 실행 가능

**Given** Excel 파일이 존재할 때
**When** 개발자가 `python scripts/parse_kis_excel.py --excel HTS_OPENAPI.xlsx --output docs/kis-openapi`를 실행하면
**Then** 스크립트가 성공적으로 완료되어야 하고
**And** `tr_id_mapping.json`, `categories.json`, `api_summary.json`이 생성되어야 하고
**And** 실행 시간이 10초 이내여야 한다

#### Scenario 5.2: CLI 인터페이스 지원

**Given** 파싱 스크립트가 있을 때
**When** 개발자가 `--help` 플래그로 실행하면
**Then** 사용법이 표시되어야 하고
**And** `--excel`, `--output`, `--verbose` 옵션에 대한 설명이 포함되어야 한다

#### Scenario 5.3: Excel 변경 감지

**Given** Excel 파일이 수정되었을 때
**When** 파싱 스크립트가 다시 실행되면
**Then** 변경된 내용이 반영된 새로운 JSON 파일이 생성되어야 하고
**And** 콘솔에 변경된 API 개수가 표시되어야 한다

---

### AC6: 전체 API 문서화

**Story**: 336개 전체 API가 문서화되어야 한다

#### Scenario 6.1: Phase 1 - 기존 115개 문서 보완

**Given** 기존 115개 API 문서가 존재할 때
**When** Milestone 1이 완료되면
**Then** 모든 문서에 TR_ID 정보가 추가되어야 하고
**And** 모든 문서가 새로운 템플릿 구조를 따라야 하고
**And** Request Header에 `tr_id` 필드가 포함되어야 한다

#### Scenario 6.2: Phase 2 - 추가 100개 문서 생성

**Given** 자주 사용되는 API 100개가 선택되었을 때
**When** 문서 생성 스크립트가 실행되면
**Then** 100개의 API 문서가 생성되어야 하고
**And** 각 문서는 템플릿 구조를 따라야 하고
**And** 각 문서는 올바른 카테고리 디렉토리에 위치해야 한다

#### Scenario 6.3: Phase 3 - 전체 336개 문서화 완료

**Given** 나머지 121개 API가 남아있을 때
**When** 최종 문서 생성이 완료되면
**Then** 총 336개의 API 문서가 존재해야 하고
**And** `api_summary.json`의 `total_apis` 필드가 336이어야 하고
**And** 모든 카테고리에 `index.md`가 존재해야 한다

#### Scenario 6.4: 문서 간 일관성

**Given** 336개의 API 문서가 생성되었을 때
**When** 일관성 검증 스크립트가 실행되면
**Then** 모든 문서가 템플릿 구조를 따라야 하고
**And** 모든 문서에 TR_ID 정보가 포함되어야 하고
**And** 중복되는 내용이 없어야 하고
**And** 깨진 링크가 없어야 한다

---

## 품질 게이트 (Quality Gates)

### QG1: 코드 커버리지

- [ ] Excel 파싱 스크립트: 100% 커버리지
- [ ] REST Client TR_ID 메서드: 90% 이상 커버리지
- [ ] 통합 테스트: 주요 시나리오 포함

### QG2: 정적 분석

- [ ] `ruff` linter 통과 (0 errors, 0 warnings)
- [ ] `mypy` 타입 검증 통과
- [ ] `black` 포맷팅 적용

### QG3: JSON Schema 검증

- [ ] `tr_id_mapping.json` schema 유효성
- [ ] `categories.json` schema 유효성
- [ ] `api_summary.json` schema 유효성

### QG4: 문서 품질

- [ ] 모든 문서가 템플릿 구조 준수
- [ ] 모든 문서에 TR_ID 정보 포함
- [ ] 링크 깨짐 없음
- [ ] 코드 예시 실행 가능

### QG5: 성능 기준

- [ ] Excel 파싱: 10초 이내
- [ ] TR_ID 조회: 1초 이내
- [ ] 문서 생성: 336개 30초 이내

---

## 정의 완료 (Definition of Done)

### Milestone 1 완료 기준

- [x] `scripts/parse_kis_excel.py` 스크립트 구현
- [x] `docs/kis-openapi/_data/tr_id_mapping.json` 생성
- [x] `src/stock_manager/adapters/broker/kis/kis_rest_client.py`에 `get_tr_id()` 메서드 추가
- [x] 단위 테스트 통과 (TR_ID 조회, 예외 처리)
- [x] 기존 115개 문서에 TR_ID 정보 추가

### Milestone 2 완료 기준

- [x] 16개 카테고리별 디렉토리 생성
- [x] `categories.json` 생성 및 검증
- [x] 기존 문서 새로운 디렉토리로 이전
- [x] `templates/api_doc_template.md.j2` 템플릿 생성
- [x] 문서 일관성 검증 통과

### Milestone 3 완료 기준

- [x] 336개 전체 API 문서 생성
- [x] 각 카테고리 `index.md` 생성
- [x] `api_summary.json` 생성
- [x] 모든 문서 템플릿 구조 준수
- [x] TR_ID 매핑 100% 완료

### Milestone 4 완료 기준

- [x] CI/CD 파이프라인 통합
- [x] pre-commit hook 구성
- [x] 개발자 가이드 작성
- [x] 마이그레이션 가이드 작성
- [x] Excel → 문서 자동화 파이프라인 작동

---

## 검증 방법 및 도구

### 자동화된 검증

**스크립트**: `scripts/validate_docs.py`

```python
def validate_tr_id_mapping():
    """TR_ID 매핑 JSON 검증"""
    mapping = load_json("docs/kis-openapi/_data/tr_id_mapping.json")
    assert len(mapping) == 336, f"Expected 336 APIs, got {len(mapping)}"
    # ... 추가 검증

def validate_document_structure():
    """문서 구조 검증"""
    for doc in glob("docs/kis-openapi/**/*.md"):
        # 필수 섹션 존재 확인
        # TR_ID 정보 존재 확인
        # ...

def validate_links():
    """링크 깨짐 검증"""
    # 상대 링크 검증
    # ...
```

### 수동 검증 체크리스트

- [ ] 문서 가독성 확인
- [ ] 코드 예시 실행 가능성 확인
- [ ] TR_ID 값 Excel과 비교 검증
- [ ] 실전/모의 환경별 동작 테스트

---

## 롤백 계획

### 롤백 시나리오 1: TR_ID 매핑 오류

**조건**: TR_ID 매핑에 심각한 오류가 발생했을 때
**작업**:
1. Git 이전 커밋으로 롤백
2. Excel 데이터 재검증
3. 파싱 로직 수정
4. 재배포

### 롤백 시나리오 2: REST Client 호환성 문제

**조건**: REST Client 변경으로 기존 코드가 깨질 때
**작업**:
1. 이전 `kis_rest_client.py` 복원
2. 호환성 래퍼 구현
3. 점진적 마이그레이션

### 롤백 시나리오 3: 문서 구조 문제

**조건**: 새로운 문서 구조에 문제가 있을 때
**작업**:
1. 기존 `01-*.md` 파일 구조 복원
2. TR_ID 정보만 추가하는 방식으로 수정
3. 점진적 마이그레이션

---

## 다음 단계

### /moai:2-run 실행 전 확인사항

- [ ] Excel 파일 준비 완료
- [ ] 의존성 패키지 설치 완료
- [ ] 디렉토리 구조 준비 완료
- [ ] 테스트 환경 설정 완료

### 예상 실행 순서

1. `python scripts/parse_kis_excel.py`로 TR_ID 매핑 생성
2. `pytest tests/unit/test_tr_id_mapping.py`로 단위 테스트
3. `pytest tests/integration/test_excel_parsing.py`로 통합 테스트
4. 기존 문서 마이그레이션
5. 전체 API 문서 생성
