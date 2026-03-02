# Harness Week-1 Execution Plan (No Logic Changes)

이 문서는 최근 Audit 결과를 기준으로, 1주 안에 수행할 수 있는 harness 개선 실행 계획이다.

원칙:
- 트레이딩 비즈니스 로직(전략/주문/리스크)은 수정하지 않는다.
- 문서, 설정, 검증 가시성(quality gates), 지식 구조만 개선한다.
- 모든 항목은 "완료 기준"과 "증거"를 남긴다.

## 1. Week-1 목표

- 목적: 에이전트 작업 신뢰도를 높이고 문서-검증 드리프트를 줄인다.
- 목표 차원: B(Enforcement), D(Operations) 우선 개선.
- 기대 결과:
  - 루트 문서와 CI 정책 불일치 제거
  - quality gate(무엇이 어디서 강제되는지) 단일 지도 확보
  - 다음 Audit에서 재현성/운영 차원 점수 상승

## 2. 우선순위 Backlog (Week-1)

| 우선순위 | 작업 | 산출물 | 완료 기준 |
|---|---|---|---|
| P0 | 커버리지 임계값 정책 고정 (85) | 정책 결정 기록 + 문서 반영 | AGENTS/README/pytest/CI가 동일 기준(85) 사용 |
| P0 | quality gate 가시화 | `docs/quality-gates.md` | lint/type/test/build의 강제 위치가 표로 명시 |
| P1 | 문서 드리프트 정리 | `docs/knowledge-map.md` 업데이트 | drift 섹션이 현재 상태와 일치 |
| P1 | ADR 부트스트랩 | `docs/adr/README.md` + ADR 2개 초안 | 핵심 의사결정 탐색 경로 확보 |
| P2 | 모듈 진입 노트 추가 | core 디렉토리별 "where to start" | 신규 에이전트가 2-hop 내 진입 가능 |

## 3. 일자별 실행 계획

### Day 1 - Baseline Lock

- 작업:
  - 기준 감사 점수/이슈를 고정하고 범위를 문서화
  - "no logic change" 범위를 팀 규칙으로 재확인
- 산출물:
  - 본 문서 승인
  - 업데이트 대상 파일 목록
- 증거:
  - 변경 파일 diff

### Day 2 - Quality Gate Map

- 작업:
  - 현재 gate 상태를 문서화 (CI/local pre-check/manual)
  - 누락 gate(lint/type/build)를 명시
- 산출물:
  - `docs/quality-gates.md`
- 증거:
  - CI workflow 경로와 명령어 링크

### Day 3 - Policy Alignment

- 작업:
  - coverage threshold 기준 단일화
  - 루트 문서/설정 간 불일치 제거
- 산출물:
  - 일치된 임계값 정책
- 증거:
  - 관련 파일에서 동일 값 확인

### Day 4 - Entry Hardening

- 작업:
  - AGENTS/README/knowledge-map의 cross-reference 정리
  - 중복/오해 유발 문구 제거
- 산출물:
  - 루트 entry 문서 정합성 확보
- 증거:
  - 링크 검토 결과(깨진 내부 참조 0)

### Day 5 - ADR Bootstrap

- 작업:
  - ADR 인덱스와 템플릿 추가
  - 이미 코드에 존재하는 결정 2개를 ADR로 기록
- 산출물:
  - `docs/adr/README.md`, `docs/adr/0001-*.md`, `docs/adr/0002-*.md`
- 증거:
  - README/knowledge-map에서 ADR 경로 탐색 가능

### Day 6 - Module Entry Notes

- 작업:
  - `trading/`, `adapters/`, `monitoring/`, `persistence/`에 시작점 노트 추가
- 산출물:
  - 각 영역 "where to start" 문서
- 증거:
  - 에이전트가 핵심 진입점을 2-hop 내 찾을 수 있음

### Day 7 - Re-Audit and Delta

- 작업:
  - harness-diagnostics Audit 재실행
  - 점수 변화, 미해결 리스크, 다음 주 backlog 확정
- 산출물:
  - delta 리포트
- 증거:
  - 이전/현재 점수 비교표

## 4. 검증 체크리스트 (Week-1 Exit)

- [ ] 문서와 CI 정책이 서로 충돌하지 않는다.
- [ ] quality gates가 "어디서 강제되는지"를 한 문서에서 확인할 수 있다.
- [ ] entry 문서에서 핵심 모듈로 2-hop 내 이동 가능하다.
- [ ] ADR 진입점이 존재하고 최소 2개 결정이 기록된다.
- [ ] 재감사 결과와 다음 단계가 문서화된다.

## 5. 리스크 및 완화

| 리스크 | 영향 | 완화 |
|---|---|---|
| 문서만 갱신하고 실제 gate 반영이 지연됨 | 점수 개선 제한 | Day 2에 "현재/목표"를 분리해 추적 |
| coverage 기준 합의 지연 | 정책 drift 지속 | Day 3에 단일 값 결정 회의 고정 |
| ADR 작성이 과도하게 길어짐 | 실행 지연 | 첫 주는 핵심 결정 2개만 작성 |
