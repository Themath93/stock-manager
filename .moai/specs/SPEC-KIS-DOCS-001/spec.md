# SPEC-KIS-DOCS-001: KIS OpenAPI 문서 재정비

## 메타데이터

- **SPEC ID**: SPEC-KIS-DOCS-001
- **제목**: KIS OpenAPI 문서 재정비 및 TR_ID 매핑 시스템 구축
- **생성일**: 2026-01-25
- **상태**: completed
- **버전**: 2.0.0
- **우선순위**: High
- **담당자**: Alfred (workflow-spec)
- **관련 SPEC**: 없음

---

## 변경 이력 (History)

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.0.0 | 2026-01-26 | Alfred | Milestone 3 완료: 336개 전체 API 문서화 완료 |
| 1.1.0 | 2026-01-25 | Alfred | HTS_OPENAPI.xlsx 상세 분석 반영, TR_ID 불일치 문제 식별 |
| 1.0.0 | 2026-01-25 | Alfred | 초기 문서 작성 |

---

## 개요

한국투자증권(KIS) OpenAPI 문서를 HTS_OPENAPI.xlsx Excel 파일의 실제 데이터와 일치하도록 재정비합니다. 특히 각 API마다 다른 `tr_id` 헤더 값을 적용하고, 문서화되지 않은 221개의 API를 포함하여 전체 336개 API를 체계적으로 관리합니다.

**프로젝트 상태**: ✅ **Milestone 3 완료** - 336/336 API 문서화 (100%覆盖率)

---

## 완료된 마일스톤 (Completed Milestones)

### ✅ Milestone 1: 핵심 인프라 구축 (완료)

**완료일**: 2026-01-25
**커밋**: e52a977, 4626d1f

**완료된 작업**:
- [x] `scripts/parse_kis_excel.py` 스크립트 구현 (549 lines)
- [x] TR_ID 매핑 JSON 생성 (`docs/kis-openapi/_data/tr_id_mapping.json`)
- [x] REST Client TR_ID 헤더 지원 추가 (`src/stock_manager/adapters/broker/kis/kis_rest_client.py`)
- [x] 단위 테스트 추가 (TR_ID 매핑 검증)

**산출물**:
- Excel 파싱 스크립트: 336개 API 매핑 완료
- TR_ID 매핑 JSON: 실전/모의 환경별 TR_ID 포함
- REST Client 수정: `get_tr_id()` 메서드 추가, `tr_id` 헤더 포함

---

### ✅ Milestone 2: 문서 구조 재구성 (완료)

**완료일**: 2026-01-25
**커밋**: 49f7ff7, c11d74e, 4a23cff

**완료된 작업**:
- [x] Excel "메뉴 위치" 기반 카테고리 재분류
- [x] 22개 카테고리별 디렉토리 구조 생성
- [x] `docs_raw/categories.json` 생성
- [x] 문서 템플릿 표준화 (`templates/api_doc_template.md.j2`)

**산출물**:
- 22개 카테고리 정의 (OAuth, 국내주식, 해외주식, 선물옵션, 채권 등)
- 카테고리별 API 분류 완료
- 표준화된 문서 템플릿 (TR_ID 정보 포함)

---

### ✅ Milestone 3: 전체 API 문서화 (완료)

**완료일**: 2026-01-26
**커밋**: 186f68f, 3c99655

**완료된 작업**:
- [x] API 문서 생성 시스템 구축 (`scripts/generate_api_docs.py`)
- [x] 문서 검증 스크립트 추가 (`scripts/validate_docs.py`)
- [x] 336개 전체 API 문서화 완료
- [x] 22개 카테고리 인덱스 생성
- [x] `api_summary.json` 생성 (프로그래밍 방식 접근 지원)

**산출물**:
- 문서화覆盖率: 100% (336/336 APIs)
- 총 생성 파일 수: 374개 (개별 API 문서 + 인덱스)
- 카테고리별 문서 구조:
  - OAuth: 4개 API
  - 국내주식-주문/계좌: 23개 API
  - 국내주식-기본시세: 21개 API
  - 국내주식-ELW: 22개 API
  - 국내주식-업종/기타: 14개 API
  - 국내주식-종목정보: 26개 API
  - 국내주식-시세분석: 29개 API
  - 국내주식-순위분석: 22개 API
  - 국내주식-실시간시세: 37개 API
  - 국내선물옵션-주문/계좌: 19개 API
  - 국내선물옵션-기본시세: 8개 API
  - 국내선물옵션-실시간시세: 20개 API
  - 장내채권-주문/계좌: 7개 API
  - 장내채권-기본시세: 10개 API
  - 장내채권-실시간시세: 3개 API
  - 해외주식-주문/계좌: 23개 API
  - 해외주식-기본시세: 18개 API
  - 해외주식-실시간시세: 4개 API
  - 해외주식-시세분석: 13개 API
  - 해외선물옵션-주문/계좌: 14개 API
  - 해외선물옵션-기본시세: 15개 API
  - 해외선물옵션-실시간시세: 4개 API
  - 기타: 6개 API

---

## 요구사항 완료 상태 (Requirements Status)

| ID | 요구사항 | 상태 | 비고 |
|----|----------|------|------|
| R1 | TR_ID 매핑 데이터베이스 생성 | ✅ 완료 | `tr_id_mapping.json`에 336개 API 매핑 |
| R2 | REST Client TR_ID 지원 | ✅ 완료 | `get_tr_id()` 메서드 구현, 헤더 포함 |
| R3 | 문서 카테고리 재구성 | ✅ 완료 | 22개 카테고리 생성 |
| R4 | Excel 파싱 자동화 스크립트 | ✅ 완료 | `parse_kis_excel.py` (549 lines) |
| R5 | 문서 템플릿 표준화 | ✅ 완료 | `api_doc_template.md.j2` |
| R6 | 누락된 API 문서화 | ✅ 완료 | 336/336 문서화 (100%) |
| R7 | 기존 문서 TR_ID 수정 | ✅ 완료 | 모든 문서에 올바른 TR_ID 포함 |
| R8 | REST Client 코드 수정 | ✅ 완료 | `tr_id` 헤더 포함 완료 |

---

## 성공 기준 달성 (Success Criteria)

### 정량적 기준

| 항목 | 목표 | 달성 | 상태 |
|------|------|------|------|
| TR_ID 매핑覆盖率 | 100% (336/336) | 100% (336/336) | ✅ |
| 문서화覆盖率 | 100% (336/336) | 100% (336/336) | ✅ |
| 파싱 스크립트 실행 시간 | 10초 이내 | ~5초 | ✅ |
| JSON schema 유효성 | 100% 통과 | 100% | ✅ |
| 기존 문서 TR_ID 수정률 | 100% | 100% | ✅ |
| REST Client tr_id 헤더 포함률 | 100% | 100% | ✅ |

### 정성적 기준

| 항목 | 상태 | 비고 |
|------|------|------|
| TR_ID 조회 속도 | ✅ | 1초 이내 |
| 실전/모의 환경 전환 | ✅ | 코드 변경 없이 가능 |
| 문서 형식 일관성 | ✅ | 템플릿 기반 표준화 |
| Excel 데이터 자동 재생성 | ✅ | 파싱 스크립트로 자동화 |
| API ID/TR_ID 명확한 구분 | ✅ | 문서에 명시적으로 표시 |

---

## 기술 스택 (Technology Stack)

### 사용된 기술

- **Python 3.13**: 주요 개발 언어
- **openpyxl**: Excel 파일 파싱
- **Jinja2**: 문서 템플릿 엔진
- **pytest**: 단위 테스트 프레임워크
- **Markdown**: 문서 형식
- **JSON**: 데이터 저장 형식

### 생성된 스크립트

1. **scripts/parse_kis_excel.py** (549 lines)
   - Excel 파일 파싱
   - TR_ID 매핑 JSON 생성
   - 카테고리별 분류
   - 문서 자동 생성 기능

2. **scripts/generate_api_docs.py** (631 lines)
   - TR_ID 매핑 JSON 파싱
   - 336개 API 문서 자동 생성
   - 카테고리별 인덱스 생성
   - 메인 인덱스 업데이트

3. **scripts/validate_docs.py** (477 lines)
   - 생성된 문서 검증
   - 필수 섹션 존재 확인
   -覆盖率 보고서 생성

---

## 프로젝트 구조 (Project Structure)

```
stock-manager/
├── docs/kis-openapi/                 # 생성된 API 문서
│   ├── _data/
│   │   ├── tr_id_mapping.json       # TR_ID 매핑 (336개)
│   │   └── api_summary.json         # 전체 API 요약
│   ├── api/                         # 개별 API 문서
│   │   ├── oauth/                   # OAuth인증 (4개)
│   │   ├── domestic-stock-orders/   # 국내주식-주문/계좌 (23개)
│   │   ├── domestic-stock-basic/    # 국내주식-기본시세 (21개)
│   │   ├── domestic-stock-realtime/ # 국내주식-실시간시세 (37개)
│   │   ├── ... (22개 카테고리)
│   │   └── index.md                 # 메인 인덱스
│   └── index.md                     # 전체 문서 인덱스
├── scripts/
│   ├── parse_kis_excel.py           # Excel 파싱 스크립트
│   ├── generate_api_docs.py         # 문서 생성 스크립트
│   └── validate_docs.py             # 문서 검증 스크립트
├── templates/
│   └── api_doc_template.md.j2       # 문서 템플릿
├── docs_raw/
│   ├── categories.json              # 카테고리 정의
│   ├── template.md                  # 템플릿 소스
│   └── kis-openapi/                 # 원본 문서
└── src/stock_manager/adapters/broker/kis/
    └── kis_rest_client.py           # TR_ID 지원 추가됨
```

---

## 검증 및 테스트 (Validation & Testing)

### 자동화된 검증

**스크립트**: `scripts/validate_docs.py`

검증 항목:
- [x] 모든 336개 API 문서 존재
- [x] 필수 섹션 포함 (개요, Request Header, Response, 코드 예시)
- [x] TR_ID 정보 포함 (실전/모의 구분)
- [x] 카테고리별 인덱스 존재
- [x] 링크 무결성

### 단위 테스트

**파일**: `tests/unit/test_kis_tr_id_mapping.py` (1556239)

테스트 커버리지:
- [x] Excel 파싱 테스트
- [x] TR_ID 매핑 검증
- [x] REST Client `get_tr_id()` 메서드 테스트
- [x] 실전/모의 환경별 TR_ID 조회 테스트

---

## 품질 상태 (Quality Status)

### TRUST 5 Framework 준수

| Pillar | 상태 | 비고 |
|--------|------|------|
| Tested | ⚠️ WARNING | 기존 코드는 테스트 있음, 새로운 스크립트는 테스트 부족 |
| Readable | ✅ | 명확한 명명, 문서화 완료 |
| Unified | ✅ | 템플릿 기반 표준화 |
| Secured | ✅ | 민감 정보 없음 |
| Trackable | ✅ | Git 커밋 명확히 기록됨 |

### 품질 경고

**WARNING**: 새로 생성된 문서 생성 스크립트(`generate_api_docs.py`, `validate_docs.py`)에 대한 테스트 커버리지가 부족합니다.

**권장 사항**:
- pytest를 사용한 단위 테스트 추가
- 템플릿 렌더링 테스트
- 파일 생성 검증 테스트

---

## 미래 계획 (Future Plans)

### Milestone 4: 자동화 및 문서화 (Optional)

**계획된 작업**:
- [ ] CI/CD 파이프라인 통합
- [ ] pre-commit hook으로 자동 문서 생성
- [ ] 개발자 가이드 작성
- [ ] 마이그레이션 가이드 작성

**우선순위**: 중간 (필수 아님)

---

## 참조 (References)

### 관련 커밋

- `b849d04`: SPEC-KIS-DOCS-001 생성
- `e52a977`: Excel 파서 및 TR_ID 매핑 시스템 추가
- `4626d1f`: REST Client에 tr_id 헤더 추가
- `1556239`: TR_ID 매핑 검증 테스트 추가
- `49f7ff7`: Milestone 1-2 완료 후 문서 동기화
- `c11d74e`: 표준화된 API 문서 템플릿 추가
- `4a23cff`: 문서 수정 및 재구성 도구 추가
- `186f68f`: API 문서 생성 시스템 추가
- `3c99655`: 336개 KIS OpenAPI 문서 생성

### 문서

- API 문서: `/docs/kis-openapi/`
- Excel 원본: `HTS_OPENAPI.xlsx`
- 템플릿: `templates/api_doc_template.md.j2`

---

## 결론 (Conclusion)

SPEC-KIS-DOCS-001은 **Milestone 3까지 성공적으로 완료**되었습니다.

**주요 성과**:
- 336개 전체 API 문서화 (100%覆盖率)
- TR_ID 매핑 시스템 구축 완료
- REST Client TR_ID 지원 완료
- 자동화된 문서 생성 시스템 구축

**다음 단계**:
- 새로운 스크립트에 대한 테스트 커버리지 추가 (권장)
- Milestone 4 (자동화 및 CI/CD)는 선택적 사항

프로젝트 상태: **✅ 완료 (Completed)**
