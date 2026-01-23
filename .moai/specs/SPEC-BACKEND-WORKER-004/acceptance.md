# 검수 기준: SPEC-BACKEND-WORKER-004

## 1. 개요

본 문서는 자동매매 봇 Worker 프로세스 아키텍처의 검수 기준을 정의합니다. Given-When-Then 형식으로 구현된 기능의 동작을 검증합니다.

## 2. 시나리오 기반 검수 기준

### SC-001: Worker 시작 및 초기화

**설명:** Worker 프로세스 시작 시 정상적으로 초기화되어야 함

**Given:**
- Worker 프로세스 시작
- 환경 변수/설정 파일에 필요한 설정 (계좌/모드/한도액/전략 파라미터) 존재

**When:**
- Worker 실행 명령 수행

**Then:**
1. 환경/설정이 정상적으로 로드됨
2. API 인증이 성공하고 토큰이 발급됨
3. 리스크 기본값이 설정됨 (일 손실 한도, 한도액, 청산 시각)
4. Worker 상태가 DB에 등록됨 (status: IDLE)
5. Worker 상태가 IDLE → SCAN으로 전이됨
6. WorkerStartedEvent가 발행됨

**검증 방법:**
- 로그 확인 (설정 로드, 인증 성공, 상태 전이)
- DB 확인 (workers 테이블에 worker_id 존재, status = IDLE/SCAN)
- 이벤트 로그 확인 (WorkerStartedEvent)

---

### SC-002: 후보 종목 탐색

**설명:** 주기적 폴링으로 매수 가능한 후보 종목 탐색

**Given:**
- Worker 상태: SCAN
- 유니버스(전체 종목 또는 특정 종목군) 설정됨
- 폴링 간격 설정됨 (1~60초)

**When:**
- 폴링 타이머 트리거

**Then:**
1. 종목 리스트가 수집됨 (현재가/거래량/거래대금/등락률/장중 고저/전일 고저)
2. 프리프로세스 필터링이 적용됨:
   - 최소 거래량/거래대금 미달 종목 제외
   - 스프레드/호가 공백 큰 종목 제외
3. 단기 캔들 기반 지표가 계산됨 (이평, 돌파 등)
4. 매수 가능 후보 리스트가 생성됨
5. 매수 신호가 평가됨 (전략 파라미터 적용)
6. CandidateScannedEvent가 발행됨

**검증 방법:**
- 로그 확인 (폴링 시작, 필터링 결과, 후보 리스트)
- DB 확인 (candidates 테이블에 데이터 존재, signal = True인 것)
- 이벤트 로그 확인 (CandidateScannedEvent)

---

### SC-003: 종목 락 획득 성공

**설명:** 후보 종목 선정 후 다른 Worker가 소유하지 않은 종목의 락 획득 성공

**Given:**
- 매수 신호 충족 (후보 종목 선정)
- 해당 종목 락이 존재하지 않음

**When:**
- LockService.acquire_lock() 호출

**Then:**
1. DB에 락 정보가 저장됨 (symbol, worker_id, locked_at, ttl, heartbeat_at)
2. LockAcquiredEvent가 발행됨
3. 락 획득 성공으로 응답됨 (True 반환)
4. 매수 주문 실행 단계로 진행

**검증 방법:**
- DB 확인 (stock_locks 테이블에 symbol 존재, worker_id = 현재 worker_id)
- 이벤트 로그 확인 (LockAcquiredEvent)
- 로그 확인 (락 획득 성공)

---

### SC-004: 종목 락 획득 실패 (다른 Worker 소유)

**설명:** 후보 종목 선정 후 다른 Worker가 이미 소유한 종목의 락 획득 실패

**Given:**
- 매수 신호 충족 (후보 종목 선정)
- 해당 종목 락이 다른 Worker에 의해 소유됨

**When:**
- LockService.acquire_lock() 호출

**Then:**
1. DB에 새로운 락이 저장되지 않음 (UNIQUE 제약 위반)
2. LockRejectedEvent가 발행됨
3. 락 획득 실패로 응답됨 (False 반환)
4. 다른 종목으로 후보 탐색 계속

**검증 방법:**
- DB 확인 (stock_locks 테이블에 해당 symbol의 worker_id 변경 없음)
- 이벤트 로그 확인 (LockRejectedEvent)
- 로그 확인 (락 획득 실패, 다른 종목 시도)

---

### SC-005: 매수 주문 실행 및 체결

**설명:** 락 획득 후 매수 주문 전송 및 체결

**Given:**
- 락 획득 성공
- 한도액(capital_limit) 설정됨
- OrderService 및 BrokerPort 사용 가능

**When:**
- 매수 주문 실행 단계 진입

**Then:**
1. 수량이 산정됨 (한도액 / 현재가)
2. 주문 방식이 결정됨 (시장가/지정가)
3. OrderService.create_order() 호출로 주문 생성됨
4. OrderService.send_order() 호출로 주문 전송됨
5. 주문 상태 추적으로 체결 확인됨
6. orders/fills/positions 스냅샷이 저장됨
7. "진입가격/진입시간/전략버전/파라미터버전"이 기록됨
8. Worker 상태가 SCAN → HOLD로 전이됨
9. PositionEnteredEvent가 발행됨

**검증 방법:**
- DB 확인 (orders 테이블에 주문 존재, status = FILLED)
- DB 확인 (fills 테이블에 체결 기록 존재)
- DB 확인 (positions 테이블에 포지션 존재, qty > 0)
- DB 확인 (workers 테이블 current_symbol = 해당 종목, status = HOLD)
- 이벤트 로그 확인 (PositionEnteredEvent)
- 로그 확인 (주문 전송, 체결)

---

### SC-006: 보유 종목 감시 (매도 조건 미충족)

**설명:** 매수 이후 매도 조건만 반복 감시, 아직 매도 조건 충족하지 않음

**Given:**
- Worker 상태: HOLD
- 현재 포지션 존재
- 매도 조건 충족하지 않음

**When:**
- 주기적 폴링 타이머 트리거

**Then:**
1. 현재가/지표가 업데이트됨
2. 매도 조건이 평가됨:
   - 손절: -x% (미도달)
   - 익절: +y% (미도달)
   - 추세 훼손: 단기 이평 이탈 여부 (미도달)
   - 시간 조건: 청산 시각 임박 여부 (미도달)
3. MonitoringEvent가 발행됨
4. Worker 상태 유지 (HOLD)
5. 매도 주문 전송하지 않음

**검증 방법:**
- 로그 확인 (폴링 수행, 매도 조건 평가 결과)
- DB 확인 (positions 테이블 포지션 변화 없음)
- 이벤트 로그 확인 (MonitoringEvent)

---

### SC-007: 매도 조건 충족 (손절/익절/추세훼손)

**설명:** 매도 조건 충족 시 즉시 매도 주문 실행

**Given:**
- Worker 상태: HOLD
- 현재 포지션 존재
- 매도 조건 충족 (손절/익절/추세훼손 중 하나)

**When:**
- 매도 조건 평가에서 충족 확인

**Then:**
1. OrderService.create_order() 호출로 매수 주문 생성됨 (side = SELL)
2. OrderService.send_order() 호출로 주문 전송됨
3. 체결 확인 및 fills/positions 정리됨
4. PnL이 계산되고 저장됨
5. 종목 락 해제됨 (stock_locks 테이블에서 해당 레코드 삭제)
6. Worker 상태가 HOLD → SCAN로 전이됨
7. PositionExitedEvent가 발행됨

**검증 방법:**
- DB 확인 (orders 테이블에 매도 주문 존재, status = FILLED)
- DB 확인 (fills 테이블에 매도 체결 기록 존재)
- DB 확인 (positions 테이블 해당 종목 qty = 0)
- DB 확인 (stock_locks 테이블 해당 symbol 존재하지 않음)
- DB 확인 (workers 테이블 current_symbol = NULL, status = SCAN)
- DB 확인 (daily_summaries 테이블 PnL 누적 업데이트)
- 이벤트 로그 확인 (PositionExitedEvent)
- 로그 확인 (매도 주문 전송, 체결, 락 해제)

---

### SC-008: 당일 강제 청산

**설명:** 청산 시각 T-Δ(장 마감 10~15분 전)부터 무조건 현금화

**Given:**
- 현재시각 >= 청산 시각 (장 마감 10~15분 전)
- 현재 포지션 존재

**When:**
- 강제 청산 체크 타이머 트리거

**Then:**
1. 현재 포지션 있는지 확인됨
2. 유동성 부족 종목 확인 (더 일찍 청산)
3. 시장가/보수적 주문으로 강제 청산됨
4. 유동성 고려됨
5. 부분체결 시 재시도됨
6. MandatoryLiquidationEvent가 발행됨
7. SC-007 매도 주문 실행 단계 진입

**검증 방법:**
- DB 확인 (모든 positions qty = 0)
- DB 확인 (stock_locks 테이블 비어 있음)
- DB 확인 (workers 테이블 모든 worker의 current_symbol = NULL)
- 이벤트 로그 확인 (MandatoryLiquidationEvent, PositionExitedEvent)
- 로그 확인 (강제 청산 실행)

---

### SC-009: Worker 장애 시 락 회수

**설명:** Worker 하트비트 중단 또는 TTL 만료 시 락 회수

**Given:**
- Worker 상태: HOLD
- Worker 하트비트 중단 (프로세스 장애) 또는 TTL 만료

**When:**
- 락 만료 체크 타이머 트리거

**Then:**
1. 해당 Worker가 보유한 모든 락 회수됨 (stock_locks 테이블에서 해당 worker_id의 모든 레코드 삭제)
2. 락 회수 이벤트 발행됨
3. LockReleasedEvent가 발행됨
4. Worker 상태 EXIT로 설정됨
5. 다른 Worker가 해당 종목 차지 가능해짐

**검증 방법:**
- DB 확인 (stock_locks 테이블에서 해당 worker_id의 레코드 삭제됨)
- DB 확인 (workers 테이블 해당 worker의 status = EXIT)
- 이벤트 로그 확인 (LockReleasedEvent)
- 로그 확인 (Worker 장애 감지, 락 회수)

---

### SC-010: 다중 Worker 협력 (락 경쟁)

**설명:** 여러 Worker 동시 실행 시 중복 매수 방지

**Given:**
- 2개 이상의 Worker 동시 실행
- Worker A와 Worker B가 동시에 동일 종목의 락 획득 시도

**When:**
- Worker A: LockService.acquire_lock() 호출
- Worker B: LockService.acquire_lock() 호출 (거의 동시)

**Then:**
1. 먼저 락을 획득한 Worker만 락 보유 (예: Worker A)
2. 나중에 락 획득을 시도한 Worker는 실패 (예: Worker B)
3. Worker B는 LockRejectedEvent 발행
4. Worker B는 다른 종목으로 후보 탐색 계속
5. Worker A는 매수 주문 실행 진행

**검증 방법:**
- DB 확인 (stock_locks 테이블에 해당 symbol 1개 존재, worker_id = Worker A)
- Worker A 로그 확인 (락 획득 성공, 매수 진행)
- Worker B 로그 확인 (락 획득 실패, 다른 종목 시도)
- 이벤트 로그 확인 (Worker A: LockAcquiredEvent, Worker B: LockRejectedEvent)

---

### SC-011: PnL 계산 및 일일 요약 저장

**설명:** 매도 체결 시 PnL 계산 및 일일 성과 저장

**Given:**
- 매도 체결 발생
- 매수 가격/수량 및 매도 가격/수량 기록됨

**When:**
- PositionExitedEvent 발생 (매도 완료)

**Then:**
1. PnL이 계산됨: (매도가 - 매수가) * 수량 - 수수료
2. 일일 요약 업데이트됨:
   - 일 손익 누적 (pnl += 이번 거래 PnL)
   - 승률 계산 (win_count / total_count)
   - 평균 손익 계산 (total_pnl / total_count)
   - 최대 손실 갱신 (min(current_max_loss, 이번 거래 PnL) if PnL < 0)
   - 거래 횟수 증가 (trades_count += 1)
3. 다음날 파라미터 개선 데이터 저장됨:
   - 어떤 필터가 유효했는지
   - 유동성 부족으로 불리한 체결이 있었는지
   - 강제 청산으로 손실 확대 여부 등
4. DailySummary DB에 저장됨

**검증 방법:**
- DB 확인 (daily_summaries 테이블에 해당 날짜의 레코드 존재)
- DB 확인 (pnl, win_rate, avg_pnl, max_loss, trades_count 값 계산 확인)
- 로그 확인 (PnL 계산, 일일 요약 저장)

---

## 3. 엣지 케이스

### EC-001: 폴링 중 API 타임아웃

**설명:** 마켓 데이터 폴링 중 API 타임아웃 발생

**Given:**
- Worker 상태: SCAN
- 폴링 타이머 트리거

**When:**
- BrokerPort 호출 시 TimeoutError 발생

**Then:**
1. 에러 로그 기록됨 (로그 레벨: ERROR)
2. WorkerError 또는 하위 예외 발생됨
3. 재시도 로직이 트리거됨 (지수 백오프 최대 3회)
4. 재시도 성공 시 후보 탐색 계속
5. 재시도 실패 시 Worker 상태 유지 (SCAN), 다음 폴링 타이머 대기

**검증 방법:**
- 로그 확인 (API 타임아웃, 재시도 로그)
- Worker 상태 확인 (SCAN 유지, 정상 동작)

---

### EC-002: 주문 전송 실패

**설명:** 매수/매도 주문 전송 실패

**Given:**
- 락 획득 성공 (매수) 또는 매도 조건 충족 (매도)
- OrderService.send_order() 호출

**When:**
- BrokerPort.place_order() 호출 실패 (예: 리스크 위반, 잔고 부족)

**Then:**
1. OrderRejectedEvent 또는 OrderError 발행됨
2. 에러 로그 기록됨 (로그 레벨: WARN)
3. 종목 락 해제됨 (stock_locks 테이블에서 해당 레코드 삭제)
4. Worker 상태 HOLD → SCAN 전이
5. 다른 종목으로 후보 탐색 계속

**검증 방법:**
- DB 확인 (orders 테이블 주문 status = REJECTED)
- DB 확인 (stock_locks 테이블 해당 symbol 존재하지 않음)
- 이벤트 로그 확인 (OrderRejectedEvent)
- 로그 확인 (주문 전송 실패, 락 해제)

---

### EC-003: 미체결 발생

**설명:** 주문 전송 후 미체결 발생 (유동성 부족)

**Given:**
- 주문 전송됨 (status = SENT)
- 유동성 부족 종목

**When:**
- 청산 시각 도달
- 시장가 주문 전송
- 부분 체결 발생

**Then:**
1. 미체결 수량 확인됨
2. 재시도 로직 트리거됨 (최대 3회)
3. 시장가/보수적 주문으로 재시도
4. 전량 체결 실패 시:
   - 에러 로그 기록됨 (로그 레벨: WARN)
   - 일일 요약에 "유동성 부족으로 불리한 체결" 기록
5. 체결 완료 시 락 해제
6. Worker 상태 HOLD → SCAN 전이

**검증 방법:**
- DB 확인 (fills 테이블 부분 체결 기록)
- 로그 확인 (미체결 재시도 로그)
- 일일 요약 확인 (유동성 부족 기록)

---

### EC-004: 리스크 한도 초과

**설명:** 일 손실 한도 또는 한도액 초과 시 주문 차단

**Given:**
- Worker 상태: SCAN
- 일 손실 한도 또는 한도액 설정됨
- 매수 주문 전송 시도

**When:**
- 리스크 검증:
   - 현재 일일 손실 + 예상 손실 > 일 손실 한도
   - 또는 주문 수량 * 현재가 > 한도액

**Then:**
1. RiskViolationEvent 발행됨
2. 에러 로그 기록됨 (로그 레벨: WARN)
3. 주문 전송 차단됨
4. Worker 상태 유지 (SCAN), 매수 중지
5. 보유 종목만 청산 허용

**검증 방법:**
- DB 확인 (orders 테이블에 주문 생성되지 않음)
- 이벤트 로그 확인 (RiskViolationEvent)
- 로그 확인 (리스크 한도 초과, 주문 차단)

---

## 4. 성능 기준

### 4.1 응답 시간

| 작업 | 목표 응답 시간 |
|-------|---------------|
| 후보 종목 탐색 (100개 기준) | 2초 이내 |
| 락 획득/해제 | 100ms 이내 |
| 매수/매도 주문 전송 | 500ms 이내 |
| 보유 종목 감시 (폴링) | 1초 이내 |

### 4.2 동시성

| 시나리오 | 목표 |
|--------|------|
| 다중 Worker 동시 실행 | Worker당 독립된 성능, 락 경쟁 최소화 |
| 락 경쟁 | PostgreSQL row-level lock 사용, 대기 시간 < 1초 |

## 5. 보안 기준

### 5.1 데이터 보안
- [ ] 환경 변수/설정 파일에 민감 정보(앱키/시크릿) 암호화 저장
- [ ] 로그에 민감 정보 제외 (appkey/appsecret/mode)
- [ ] DB 연결에 TLS 사용

### 5.2 액세스 제어
- [ ] Worker 실행 시 인증 확인 (설정 파일/환경 변수)
- [ ] 무단 Worker 실행 차단 (파라미터 불충분 시 에러)

## 6. 로그 기준

### 6.1 로그 레벨

| 로그 레벨 | 사용 시나리오 |
|----------|-------------|
| INFO | Worker 시작/종료, 상태 전이, 주문 전송, 체결, PnL 계산 |
| WARN | 락 경쟁, 리스크 위반, 미체결, 주문 거부 |
| ERROR | API 타임아웃, Worker 장애, 치명적 오류 |

### 6.2 필수 로그 항목
- [ ] Worker 시작/종료 (worker_id, pid, status)
- [ ] 상태 전이 (IDLE → SCAN → HOLD → SCAN → EXIT)
- [ ] 락 획득/해제 (symbol, worker_id, locked_at)
- [ ] 주문 생성/전송 (order_id, symbol, side, qty, status)
- [ ] 체결 수신 (fill_id, symbol, price, qty)
- [ ] PnL 계산 (pnl, win/loss)
- [ ] 에러 발생 (에러 타입, 스택 트레이스)
