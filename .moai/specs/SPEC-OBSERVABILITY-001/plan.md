# 구현 계획: SPEC-OBSERVABILITY-001

TAG: SPEC-OBSERVABILITY-001
생성일: 2026-01-25
상태: completed
완료일: 2026-01-25

---

## 1. 개요

본 계획서는 로그 레벨 기반 Slack 알림 시스템 구현을 위한 상세 계획을 정의합니다.

---

## 2. 구현 마일스톤

### Phase 1: 기반 구조 (우선순위: HIGH) ✅

**목표:** 핵심 데이터 모델과 인터페이스 정의

- [x] AlertLevel Enum 정의
- [x] AlertMapping 데이터클래스 정의
- [x] SlackHandlerConfig Pydantic 모델 정의
- [x] AlertMapper 인터페이스 정의
- [x] SlackFormatter 인터페이스 정의
- [x] SlackHandler 인터페이스 정의

**완료 기준:**
- [x] 모든 데이터 모델이 타입 힌트와 함께 정의됨
- [x] 인터페이스가 추상 메서드와 함께 정의됨
- [x] 단위 테스트가 통과 (데이터 모델 검증)

---

### Phase 2: AlertMapper 구현 (우선순위: HIGH) ✅

**목표:** 로그 레벨 → 알림 설정 매핑 로직 구현

- [x] AlertMapper.get_alert_mapping() 구현
- [x] AlertMapper.should_alert() 구현
- [x] 기본 매핑 테이블 정의
  - CRITICAL → 즉시, #alerts-critical, (!)
  - ERROR → 즉시, #alerts-errors, (x)
  - WARNING → 배치(5분), #alerts-warnings, (warning)
  - INFO/DEBUG → 알림 없음

**완료 기준:**
- [x] 모든 로그 레벨에 대한 매핑이 정의됨
- [x] 단위 테스트가 모든 매핑을 커버

---

### Phase 3: SlackFormatter 구현 (우선순위: HIGH) ✅

**목표:** 구조화된 Slack 메시지 포맷팅

- [x] SlackFormatter.format() 구현
  - 로그 레벨, 메시지, 타임스탬프 포함
  - 스택 트레이스 포함 (CRITICAL용)
  - 이모지 추가
- [x] SlackFormatter.mask_sensitive_data() 구현
  - 토큰, 키, 비밀번호 패턴 마스킹
  - 정규표현식 기반 필터링

**완료 기준:**
- [x] 모든 로그 레벨에 대한 포맷이 정의됨
- [x] 민감 정보 마스킹이 동작함
- [x] 단위 테스트가 포맷과 마스킹을 검증

---

### Phase 4: SlackHandler 구현 (우선순위: HIGH) ✅

**목표:** logging.Handler를 통한 Slack 알림 전송

- [x] SlackHandler.__init__() 구현
  - 설정 초기화
  - SlackClient 연결
  - 비동기 큐 설정
- [x] SlackHandler.emit() 구현
  - LogRecord 수신
  - AlertMapper로 매핑
  - SlackFormatter로 포맷
  - 비동기 큐에 추가 (또는 즉시 전송)
- [x] SlackHandler.close() 구현
  - 큐 정리
  - 리소스 해제
- [x] 배치 처리 로직 (WARNING용)
  - 5분 타이머
  - 집계된 메시지 전송

**완료 기준:**
- [x] logging.Handler 표준을 준수
- [x] 모든 로그 레벨이 올바르게 처리됨
- [x] 단위 테스트와 통합 테스트 통과

---

### Phase 5: 중복 제거 및 보안 (우선순위: MEDIUM) ✅

**목표:** 중복 알림 방지 및 민감 정보 보호

- [x] 중복 필터 구현
  - 메시지 해시 계산
  - 1분 윈도우 내 중복 체크
  - LRU 캐시 사용
- [x] 민감 정보 마스킹 강화
  - 더 많은 키워드 패턴 추가
  - JSON 포맷 데이터 처리

**완료 기준:**
- [x] 중복 알림이 필터링됨
- [x] 민감 정보가 마스킹됨
- [x] 단위 테스트로 검증

---

### Phase 6: 테스트 및 통합 (우선순위: HIGH) ✅

**목표:** 전체 시스템 테스트 및 기존 코드와 통합

- [x] 단위 테스트 작성
  - AlertMapper 테스트
  - SlackFormatter 테스트
  - SlackHandler 테스트
  - MockSlackHandler 테스트
- [x] 통합 테스트 작성
  - logging 모듈과의 통합
  - 실제 Slack API 호출 (모의)
  - 배치 처리 테스트
- [x] 기존 SlackClient와의 호환성 확인
  - 기존 코드가 여전히 동작하는지 확인

**완료 기준:**
- [x] 최소 85% 테스트 커버리지 (실제 95% 달성)
- [x] 모든 테스트가 통과 (57/57)
- [x] 기존 기능과 호환됨

---

### Phase 7: 문서화 (우선순위: MEDIUM) ✅

**목표:** 사용 가이드 및 API 문서 작성

- [x] README 업데이트
  - SlackHandler 사용법
  - 설정 예제
- [x] API 문서 작성
  - 각 클래스 및 메서드 문서화
- [x] 마이그레이션 가이드
  - 기존 SlackClient → SlackHandler 마이그레이션

**완료 기준:**
- [x] 모든 공개 API가 문서화됨
- [x] 사용 예제가 제공됨

---

## 3. 기술 스택

| 컴포넌트 | 버전 | 용도 |
|----------|------|------|
| Python | 3.13+ | 표준 라이브러리 (logging, asyncio) |
| slack-sdk | >=3.27 | Slack WebClient (이미 설치됨) |
| pydantic-settings | >=2.4 | 설정 관리 (이미 설치됨) |
| pytest | >=7.4 | 테스트 프레임워크 (이미 설치됨) |

---

## 4. 파일 구조

```
src/stock_manager/adapters/observability/
├── __init__.py
├── alert_mapper.py       # AlertMapper 구현
├── slack_formatter.py    # SlackFormatter 구현
├── slack_handler.py      # SlackHandler 구현
└── models.py             # 데이터 모델 (AlertLevel, AlertMapping, Config)

tests/unit/adapters/observability/
├── __init__.py
├── test_alert_mapper.py
├── test_slack_formatter.py
├── test_slack_handler.py
└── test_integration.py
```

---

## 5. 의존성 관계

```
SlackHandler
  ├── AlertMapper (로그 레벨 → 설정 매핑)
  ├── SlackFormatter (메시지 포맷팅)
  │   └── mask_sensitive_data()
  └── SlackClient (기존 유틸리티)
      └── slack_sdk.WebClient
```

---

## 6. 리스크 분석 및 완화 계획

| 리스크 | 영향 | 확률 | 완화 계획 |
|--------|------|------|-----------|
| Slack API 타임아웃 | HIGH | MEDIUM | 비동기 전송, 타임아웃 설정 (3초) |
| 중복 알림 스팸 | MEDIUM | MEDIUM | 메시지 해시 기반 중복 필터 |
| 민감 정보 노출 | HIGH | LOW | 자동 마스킹, 키워드 필터링 |
| 성능 영향 | MEDIUM | LOW | 비동기 처리, 배치 전송 |
| 기존 코드 호환성 | MEDIUM | LOW | 기존 SlackClient 유지 |

---

## 7. 추정 작업량

| Phase | 작업량 | 의존성 |
|-------|--------|--------|
| Phase 1: 기반 구조 | 4시간 | 없음 |
| Phase 2: AlertMapper | 3시간 | Phase 1 |
| Phase 3: SlackFormatter | 4시간 | Phase 1 |
| Phase 4: SlackHandler | 8시간 | Phase 2, Phase 3 |
| Phase 5: 중복 제거 | 3시간 | Phase 4 |
| Phase 6: 테스트 | 6시간 | Phase 4, Phase 5 |
| Phase 7: 문서화 | 2시간 | Phase 6 |
| **합계** | **30시간** | |

---

## 8. 다음 단계

1. `/moai:2-run SPEC-OBSERVABILITY-001` 실행
2. Phase 1부터 순차적 구현
3. 각 Phase 완료 후 커밋
4. 전체 완료 후 `/moai:3-sync SPEC-OBSERVABILITY-001`로 문서화
