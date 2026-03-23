---
name: ship
description: "ship, deploy, merge - 테스트/커밋/푸시/PR/머지 전체 워크플로우 자동 실행"
---

# /ship — 테스트 → 커밋 → 푸시 → PR → 머지

변경사항을 검증하고 main에 머지하는 전체 워크플로우를 자율 실행한다.

## 실행 순서

### 0. 변경 감지 (가드)

- `git status --porcelain` 실행
- 출력이 비어 있으면 "커밋할 변경사항이 없습니다." 메시지 후 **즉시 종료**
- 변경이 있으면 다음 단계로 진행

### 1. 로컬 검증

- `uv run ruff check` 통과 확인
- `uv run pytest tests/unit tests/fixtures --cov=stock_manager --cov-fail-under=85 -q`
- 실패 시: 원인 파악 → 수정 → 재실행 (최대 2회)

### 2. 스테이징

- `git diff --name-only` 및 `git ls-files --others --exclude-standard`로 변경/추가 파일 목록 확인
- 아래 패턴에 해당하는 파일은 **절대 스테이징하지 않는다**:
  - `.env*`, `*.key`, `*.pem`, `credentials*`, `*secret*`
  - `*.pyc`, `__pycache__/`, `.venv/`, `htmlcov/`, `*.egg-info/`
  - `coverage.xml`, `reports/`
- 나머지 파일을 `git add <file1> <file2> ...`로 개별 스테이징
- 스테이징 후 `git diff --cached --stat`으로 최종 확인

### 3. 커밋

- 변경 내용 분석 후 conventional commit 메시지 작성
- `feat:` / `fix:` / `docs:` / `chore:` 중 선택, 스코프 포함
- `git commit -m "<type>(scope): <subject>"`

### 4. 푸시

- 현재 브랜치가 main이면 새 브랜치 생성 (`git checkout -b <branch-name>`)
- `git push -u origin HEAD`

### 5. PR 생성

- PR body 템플릿:
  ```
  ## Summary
  <변경사항 1~3줄 요약>

  ## Changes
  - <주요 변경 파일/기능 bullet list>

  ## Test Evidence
  - pytest: X passed, coverage YY%
  - ruff: clean
  ```
- `gh pr create --title "<conventional commit subject>" --body "<위 템플릿>"`
- **PR URL/번호 캡처**: `gh pr create` 출력에서 PR URL을 파싱하여 변수에 저장

### 6. 머지

- 캡처한 PR URL 사용: `gh pr merge <PR_URL> --squash --admin`
- branch protection 여부와 무관하게 `--admin`을 항상 포함
- 사용자에게 admin 머지 여부를 묻지 않는다

### 7. Cleanup

- `git checkout main`
- `git pull origin main`
- `git branch -d <feature-branch>` (로컬 feature branch 삭제)

## 에러 처리

- 각 단계 실패 시 원인 진단 후 최대 2회 재시도
- 테스트 실패 → 자동 수정 시도 (커버리지 부족 포함)
- 스테이징 시 민감 파일 감지 → 해당 파일 제외 후 계속
- PR 생성 실패 (이미 존재 등) → 기존 PR URL 탐색 후 머지 시도
- 해결 불가 시 현재 상태 보고 후 중단
