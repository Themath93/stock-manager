# SPEC-KIS-DOCS-001: KIS OpenAPI 문서 재정비

## 메타데이터

- **SPEC ID**: SPEC-KIS-DOCS-001
- **제목**: KIS OpenAPI 문서 재정비 및 TR_ID 매핑 시스템 구축
- **생성일**: 2026-01-25
- **상태**: draft
- **버전**: 1.1.0
- **우선순위**: High
- **담당자**: Alfred (workflow-spec)
- **관련 SPEC**: 없음

---

## 변경 이력 (History)

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.1.0 | 2026-01-25 | Alfred | HTS_OPENAPI.xlsx 상세 분석 반영, TR_ID 불일치 문제 식별 |
| 1.0.0 | 2026-01-25 | Alfred | 초기 문서 작성 |

---

## 개요

한국투자증권(KIS) OpenAPI 문서를 HTS_OPENAPI.xlsx Excel 파일의 실제 데이터와 일치하도록 재정비합니다. 특히 각 API마다 다른 `tr_id` 헤더 값을 적용하고, 문서화되지 않은 221개의 API를 포함하여 전체 336개 API를 체계적으로 관리합니다.

**중요**: Phase 1A 분석 결과, 현재 문서와 코드에서 **TR_ID 불일치 문제**가 식별되었습니다.

---

## Phase 1A 분석 결과 (Analysis Results)

### 1. TR_ID 불일치 문제 (Critical Issue)

**문제**: 현재 문서는 API ID를 TR_ID로 잘못 사용하고 있습니다.

| 구분 | 현재 문서 | 실제 TR_ID |
|------|-----------|------------|
| 주식잔고조회 | `v1_국내주식-006` | `TTTC8434R` (실전), `VTTC8434R` (모의) |
| 주식주문(현금) 매수 | `v1_국내주식-001` | `TTTC0012U` (실전), `VTTC0012U` (모의) |
| 주식주문(현금) 매도 | `v1_국내주식-001` | `TTTC0011U` (실전), `VTTC0011U` (모의) |
| 매수가능조회 | `v1_국내주식-007` | `TTTC8908R` (실전), `VTTC8908R` (모의) |
| 주식현재가 시세 | `v1_국내주식-008` | `FHKST01010100` (동일) |

**영향**: API 호출 시 `tr_id` 헤더가 잘못되면 KIS 서버에서 오류 응답을 반환합니다.

### 2. 코드에서 tr_id 누락 문제

**현재 `KISRESTClient._get_headers()` 메서드 분석**:

```python
# 현재 구현 - tr_id 누락
def _get_headers(self, include_token: bool = True) -> dict:
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "appkey": self.config.kis_app_key,
        "appsecret": self.config.kis_app_secret,
    }
    if include_token and self.access_token:
        headers["authorization"] = f"Bearer {self.access_token}"
    # 주의: tr_id가 완전히 누락됨!
    return headers
```

**문제**: REST API 호출 시 필수 헤더인 `tr_id`가 포함되지 않습니다.

### 3. Excel API 통계 (HTS_OPENAPI.xlsx)

| 항목 | 개수 |
|------|------|
| 전체 API 수 | 336개 |
| REST API | 276개 |
| WebSocket API | 60개 |
| 실전 TR_ID 존재 | 332개 |
| 모의 TR_ID 존재 | 331개 |
| 모의 거래 미지원 | 223개 |

### 4. 핵심 TR_ID 참조 테이블

| API 명 | API ID | 실전 TR_ID | 모의 TR_ID |
|--------|--------|------------|------------|
| 접근토큰발급(P) | v1_인증-001 | TTTC0001T | VTTC0001T |
| 접근토큰발급 | v1_인증-002 | TTTC0001U | VTTC0001U |
| 주식잔고조회 | v1_국내주식-006 | TTTC8434R | VTTC8434R |
| 주식주문(현금) 매수 | v1_국내주식-001 | TTTC0012U | VTTC0012U |
| 주식주문(현금) 매도 | v1_국내주식-001 | TTTC0011U | VTTC0011U |
| 매수가능조회 | v1_국내주식-007 | TTTC8908R | VTTC8908R |
| 주식현재가 시세 | v1_국내주식-008 | FHKST01010100 | FHKST01010100 |
| 잔고현황(일자+잔고) | v1_국내주식-011 | TTTC8435R | VTTC8435R |

---

## 환경 (Environment)

### 기술 스택

- **문서 형식**: Markdown
- **데이터 소스**: HTS_OPENAPI.xlsx (openpyxl)
- **프로그래밍 언어**: Python 3.10+
- **문서 도구**: Nextra (추후)

### 현재 상태

- **Excel API 총개수**: 336개 (REST 276개, WebSocket 60개)
- **현재 문서화된 API**: 115개
- **누락된 API**: 221개
- **문서 파일**: 15개 카테고리별 파일
- **문제점**: TR_ID 불일치, 코드에서 tr_id 누락

---

## 가정 (Assumptions)

### 기술적 가정

1. HTS_OPENAPI.xlsx 파일이 프로젝트 루트에 존재하고 정상적으로 파싱 가능함
2. 각 API는 실전 거래용 TR_ID와 모의 거래용 TR_ID를 별도로 가짐
3. REST Client는 `tr_id` 헤더를 동적으로 설정할 수 있어야 함 (현재 미지원)
4. Excel 파일의 "API 목록" 시트가 모든 API의 메타데이터를 포함함
5. **[수정]** TR_ID는 API ID와 다른 별도의 식별자임

### 비즈니스 가정

1. 개발자는 실전/모의 환경을 쉽게 전환할 수 있어야 함
2. 모든 API는 일관된 문서 형식을 따라야 함
3. API 문서는 Excel 데이터의 단일 출처(Single Source of Truth)에서 생성되어야 함
4. **[추가]** TR_ID 헤더는 REST API 호출 시 필수임

### 검증 방법

- Excel 파일 파싱 테스트로 모든 데이터 접근성 확인
- 기존 REST Client 코드 검토로 `tr_id` 지원 가능성 확인 (현재 불가)
- 카테고리별 API 개수 검증으로 문서 완전성 확인

---

## 요구사항 (Requirements)

### R1: TR_ID 매핑 데이터베이스 생성 [Ubiquitous]

시스템은 모든 KIS OpenAPI의 TR_ID 정보를 포함하는 매핑 데이터베이스를 유지해야 한다.

**EARS 패턴**: Ubiquitous (시스템은 항상 TR_ID 매핑을 유지해야 한다)

**상세 설명**:
- Excel "API 목록" 시트에서 API ID, API 명, 실전 TR_ID, 모의 TR_ID 추출
- JSON 형식으로 `docs/kis-openapi/_data/tr_id_mapping.json` 저장
- 구조:
  ```json
  {
    "api_id": {
      "api_name": "API 명칭",
      "live_tr_id": "실전 TR_ID",
      "paper_tr_id": "모의 TR_ID 또는 null"
    }
  }
  ```
- 모의 미지원 API의 경우 `paper_tr_id: null`

**인수 기준**:
- 모든 336개 API의 TR_ID 매핑 포함
- JSON schema 유효성 검증 통과
- 실전/모의 환경별 TR_ID 존재
- **[추가]** API ID와 TR_ID가 명확히 구분됨

---

### R2: REST Client TR_ID 지원 [Event-Driven]

**WHEN** 개발자가 API를 호출할 때, **THEN** 시스템은 해당 API의 TR_ID를 헤더에 자동으로 포함해야 한다.

**EARS 패턴**: Event-Driven (이벤트 발생 시 응답)

**상세 설명**:
- `KISRESTClient`에 `get_tr_id(api_name: str, is_paper_trading: bool)` 메서드 추가
- `tr_id_mapping.json`에서 TR_ID 조회
- **[수정]** `_get_headers()` 메서드에 `tr_id` 파라미터 추가 및 헤더 포함 로직 구현
- 요청 헤더에 `tr_id` 필드 추가 (REST API의 경우 필수)
- 모의 거래 미지원 API의 경우 예외 처리

**인수 기준**:
- 유효한 API 이름으로 TR_ID 조회 성공
- 실전/모의 환경별 올바른 TR_ID 반환
- 존재하지 않는 API 이름으로 `KeyError` 발생
- **[추가]** 모든 API 요청에 tr_id 헤더 포함

---

### R3: 문서 카테고리 재구성 [State-Driven]

**IF** Excel의 "메뉴 위치"가 변경되면, **THEN** 시스템은 문서 카테고리 구조를 Excel에 맞춰 재구성해야 한다.

**EARS 패턴**: State-Driven (상태에 따른 조건부 동작)

**상세 설명**:
- 현재 15개 카테고리를 Excel "메뉴 위치" 기준으로 재분류
- **[수정]** 카테고리 구조를 Excel에서 파싱하여 동적으로 생성
- 각 카테고리별 API 개수를 Excel 데이터와 일치시킴

**인수 기준**:
- Excel "메뉴 위치"와 문서 카테고리 일치
- 각 카테고리별 API 개수 정확함
- 숫자 접두사(01, 02, ...) 제거

---

### R4: Excel 파싱 자동화 스크립트 [Event-Driven]

**WHEN** 개발자가 Excel 데이터를 갱신하면, **THEN** 시스템은 자동으로 TR_ID 매핑과 문서를 재생성해야 한다.

**EARS 패턴**: Event-Driven (이벤트 발생 시 응답)

**상세 설명**:
- `scripts/parse_kis_excel.py` 스크립트 생성
- 기능:
  1. Excel "API 목록" 시트 파싱
  2. TR_ID 매핑 JSON 생성 (`_data/tr_id_mapping.json`)
  3. 카테고리별 API 목록 생성 (`_data/categories.json`)
  4. 개별 API 시트에서 Request/Response 파싱
- CLI 인터페이스: `python scripts/parse_kis_excel.py --excel HTS_OPENAPI.xlsx --output docs/kis-openapi`

**인수 기준**:
- Excel 파싱 시 336개 API 모두 처리
- JSON 파일 유효성 검증 통과
- 실행 시간 10초 이내

---

### R5: 문서 템플릿 표준화 [Unwanted]

시스템은 일관되지 않은 문서 형식을 생성해서는 안 된다.

**EARS 패턴**: Unwanted (금지된 동작)

**상세 설명**:
- 모든 API 문서는 동일한 섹션 구조 따르기:
  1. API 개요 (이름, ID, 설명)
  2. **[추가]** TR_ID 정보 (실전/모의 구분)
  3. Request 헤더 (tr_id, appkey, appsecret 등)
  4. Request 파라미터 (쿼리/바디)
  5. Response 필드
  6. Python 코드 예시
  7. 에러 처리
- Jinja2 템플릿 사용: `templates/api_doc_template.md.j2`

**인수 기준**:
- 모든 문서가 템플릿 구조 준수
- 누락된 섹션 없음
- 코드 예시 실행 가능
- **[추가]** TR_ID가 명확히 표시됨

---

### R6: 누락된 API 문서화 [Optional]

**가능하면** 시스템은 현재 문서화되지 않은 221개의 API도 포함해야 한다.

**EARS 패턴**: Optional (선택적 기능)

**상세 설명**:
- 우선순위: Phase 1 (핵심 API) → Phase 2 (자주 사용되는 API) → Phase 3 (전체)
- 각 API별 개별 시트에서 상세 정보 추출
- 자동 생성 + 수동 검증 워크플로우

**인수 기준**:
- Phase 1: 115개 문서 보완 (TR_ID 매핑)
- Phase 2: 추가 100개 문서 생성
- Phase 3: 나머지 21개 문서 생성

---

### R7: 기존 문서 TR_ID 수정 [State-Driven] (NEW)

**IF** 현재 문서에 API ID가 TR_ID로 잘못 사용된 경우, **THEN** 시스템은 올바른 TR_ID로 수정해야 한다.

**EARS 패턴**: State-Driven (상태에 따른 조건부 동작)

**상세 설명**:
- 기존 115개 문서에서 `v1_국내주식-006` 같은 API ID를 실제 TR_ID(`TTTC8434R`)로 수정
- TR_ID 참조 테이블을 활용하여 일괄 변환
- 실전/모의 TR_ID를 명확히 구분하여 표시

**인수 기준**:
- 모든 기존 문서의 TR_ID가 올바른 값으로 수정됨
- 실전/모의 TR_ID가 명확히 구분됨
- 기존 문서의 다른 내용은 유지됨

---

### R8: REST Client 코드 수정 [State-Driven] (NEW)

**IF** REST Client에 tr_id 헤더가 누락된 경우, **THEN** 시스템은 tr_id 헤더를 추가하도록 코드를 수정해야 한다.

**EARS 패턴**: State-Driven (상태에 따른 조건부 동작)

**상세 설명**:
- `_get_headers()` 메서드에 `tr_id` 파라미터 추가
- `get_tr_id()` 메서드를 호출하여 TR_ID 조회
- 헤더에 `tr_id` 필드 포함
- 기존 API 호출 메서드들 수정하여 tr_id 전달

**인수 기준**:
- 모든 API 요청에 tr_id 헤더 포함
- 실전/모의 환경별 올바른 TR_ID 사용
- 기존 기능과 호환성 유지

---

## 명세 (Specifications)

### S1: TR_ID 매핑 JSON 스키마

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "api_id": {
      "type": "string",
      "description": "API ID (예: 'v1_국내주식-001')"
    },
    "api_name": {
      "type": "string",
      "description": "API 명칭"
    },
    "live_tr_id": {
      "type": "string",
      "description": "실전 거래 TR_ID"
    },
    "paper_tr_id": {
      "type": ["string", "null"],
      "description": "모의 거래 TR_ID (미지원 시 null)"
    },
    "http_method": {
      "type": "string",
      "enum": ["GET", "POST", "PUT", "DELETE"]
    },
    "url": {
      "type": "string",
      "description": "API 경로"
    },
    "category": {
      "type": "string",
      "description": "메뉴 위치"
    }
  },
  "required": ["api_id", "api_name", "live_tr_id", "http_method", "url", "category"]
}
```

### S2: REST Client 인터페이스

```python
class KISRESTClient:
    def get_tr_id(self, api_name: str, is_paper_trading: bool = False) -> str:
        """
        API 이름에 해당하는 TR_ID 반환

        Args:
            api_name: API 명칭 (예: '접근토큰발급(P)')
            is_paper_trading: 모의 거래 여부

        Returns:
            str: TR_ID 값

        Raises:
            KeyError: API 이름이 존재하지 않을 때
            ValueError: 모의 거래 미지원 API일 때
        """
        pass

    def _get_headers(self, tr_id: str, include_token: bool = True) -> dict:
        """
        요청 헤더 생성 (tr_id 포함)

        Args:
            tr_id: TR_ID 값
            include_token: 토큰 포함 여부

        Returns:
            dict: 요청 헤더
        """
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "appkey": self.config.kis_app_key,
            "appsecret": self.config.kis_app_secret,
            "tr_id": tr_id,  # 추가된 필드
        }
        if include_token and self.access_token:
            headers["authorization"] = f"Bearer {self.access_token}"
        return headers
```

### S3: 문서 디렉토리 구조

```
docs/kis-openapi/
├── index.md                    # 메인 페이지
├── _data/
│   ├── tr_id_mapping.json     # TR_ID 매핑
│   ├── categories.json        # 카테고리별 API 목록
│   └── api_summary.json       # 전체 API 요약
├── oauth/                     # OAuth인증 (4개)
├── domestic-stock-orders/     # 국내주식-주문계좌 (20개)
├── domestic-stock-market/     # 국내주식-시세 (17개)
├── domestic-stock-execution/  # 국내주식-체결 (14개)
├── domestic-stock-ranking/    # 국내주식-랭킹 (12개)
├── domestic-stock-schedule/   # 국내주식-일정 (12개)
├── domestic-stock-basic/      # 국내주식-기본정보 (2개)
├── domestic-stock-financial/  # 국내주식-재무정보 (8개)
├── domestic-stock-trend/      # 국내주식-시장동향 (11개)
├── domestic-stock-realtime/   # 국내주식-실시간 (14개)
├── futures-options/           # 선물옵션 (20개)
├── overseas-stock/            # 해외주식 (40개)
├── overseas-futures-options/  # 해외선물옵션 (15개)
├── bond/                      # 채권 (10개)
└── elw/                       # ELW (20개)
```

---

## 추적성 (Traceability)

### 태그 매핑

- `TAG-KIS-DOCS-001`: 문서 재정비 전체
- `TAG-KIS-TR-ID`: TR_ID 매핑 시스템
- `TAG-KIS-REST-CLIENT`: REST Client 수정
- `TAG-KIS-EXCEL-PARSER`: Excel 파싱 스크립트
- `TAG-KIS-TR-ID-FIX`: 기존 문서 TR_ID 수정 (NEW)
- `TAG-KIS-HEADER-FIX`: REST Client 헤더 수정 (NEW)

### 요구사항-명세 매트릭스

| 요구사항 | 명세 | 테스트 시나리오 |
|----------|------|----------------|
| R1 | S1, S3 | Excel → JSON 변환 검증 |
| R2 | S2 | TR_ID 조회 테스트 |
| R3 | S3 | 카테고리별 분류 검증 |
| R4 | S1 | 파싱 스크립트 실행 테스트 |
| R5 | S2, S3 | 템플릿 일관성 검증 |
| R6 | S3 | 전체 API 문서 생성 테스트 |
| R7 | S1 | 기존 문서 TR_ID 수정 검증 (NEW) |
| R8 | S2 | REST Client 헤더 포함 검증 (NEW) |

---

## 제약사항 (Constraints)

### 기술적 제약

1. Excel 파일 형식 변경 시 파싱 로직 수정 필요
2. TR_ID는 한국투자증권에서 정의한 값으로 변경 불가
3. 모의 거래 미지원 API는 모의 환경에서 테스트 불가
4. **[추가]** API ID와 TR_ID는 다른 값이며 혼동하면 안 됨

### 비즈니스 제약

1. 문서화 작업은 기능 개발보다 우선순위가 낮을 수 있음
2. Excel 업데이트 시 문서 동기화 필요
3. 한국어/영어 이중 언어 지원 고려

---

## 위험 요소 및 대응 계획

| 위험 | 영향 | 확률 | 대응 계획 |
|------|------|------|-----------|
| Excel 파일 형식 변경 | 높음 | 낮음 | 파싱 로직 유연성 확보, 버전 관리 |
| TR_ID 일관성 문제 | 높음 | 중간 | 단위 테스트로 검증, 자동화된 검증 도구 |
| 문서 유지보수 부담 | 중간 | 높음 | 자동화 스크립트, CI/CD 통합 |
| 모의 거래 미지원 API | 낮음 | 높음 | 명시적인 표시 및 예외 처리 |
| **[추가]** API ID/TR_ID 혼동 | 높음 | 높음 | 명확한 명명 규칙, 문서화 |

---

## 의존성

### 외부 의존성

- `openpyxl`: Excel 파일 파싱
- `jinja2`: 문서 템플릿 엔진
- `pydantic`: JSON schema 검증

### 내부 의존성

- `src/stock_manager/adapters/broker/kis/kis_rest_client.py`: REST Client 수정
- `docs/kis-openapi/*`: 기존 문서 구조
- `HTS_OPENAPI.xlsx`: 데이터 소스

---

## 성공 기준

### 정량적 기준

- TR_ID 매핑覆盖率: 100% (336/336개 API)
- 문서화覆盖率: 100% (336/336개 API, Phase 3 완료 시)
- 파싱 스크립트 실행 시간: 10초 이내
- JSON schema 유효성: 100% 통과
- **[추가]** 기존 문서 TR_ID 수정률: 100%
- **[추가]** REST Client tr_id 헤더 포함률: 100%

### 정성적 기준

- 개발자가 TR_ID 조회를 1초 이내에 완료
- 실전/모의 환경 전환이 코드 변경 없이 가능
- 문서 형식 일관성 유지
- Excel 데이터 변경 시 자동 재생성 가능
- **[추가]** API ID와 TR_ID 혼동 없이 명확히 구분

---

## 다음 단계 (Next Steps)

### Phase 1B: 코드 수정 및 문서 TR_ID 수정

1. **R8 구현**: REST Client 코드 수정
   - `_get_headers()` 메서드에 `tr_id` 파라미터 추가
   - `get_tr_id()` 메서드 구현
   - 기존 API 호출 메서드들 수정

2. **R7 구현**: 기존 문서 TR_ID 수정
   - TR_ID 참조 테이블 생성
   - 기존 115개 문서 일괄 변환
   - 실전/모의 TR_ID 구분 표시

3. **R1 구현**: TR_ID 매핑 JSON 생성
   - Excel 파싱 스크립트 작성
   - `_data/tr_id_mapping.json` 생성

### Phase 2: 문서 자동화

4. **R4 구현**: Excel 파싱 스크립트 완성
5. **R5 구현**: 문서 템플릿 생성
6. **R6 구현**: 누락된 API 문서화
