# PostgreSQL 데이터베이스 설정 가이드

## 개요

Stock Manager 워커 아키텍처를 위한 PostgreSQL 데이터베이스 설정 방법입니다.

**필요한 스키마 파일**:
- `orders_schema.sql` - 주문 및 체결 테이블
- `fills_schema.sql` - 체결 테이블
- `worker_schema.sql` - 워커 관련 테이블 (stock_locks, worker_processes, daily_summaries)

---

## 전제 조건

- PostgreSQL 15+ 설치
- PostgreSQL 서버 실행 중
- 데이터베이스 생성 권한

---

## 데이터베이스 생성

### 1. 데이터베이스 생성

```bash
# PostgreSQL 접속
psql -U postgres

# 데이터베이스 생성
CREATE DATABASE stock_manager;

# 데이터베이스 권한 설정
GRANT ALL PRIVILEGES ON DATABASE stock_manager TO postgres;

# 데이터베이스 접속 테스트
\c stock_manager
\q
```

### 2. 사용자 생성 (선택사항)

```sql
-- 사용자 생성
CREATE USER stock_manager_user WITH PASSWORD 'your_password';

-- 권한 부여
GRANT ALL PRIVILEGES ON DATABASE stock_manager TO stock_manager_user;

-- 스키마 권한 부여
GRANT ALL ON SCHEMA public TO stock_manager_user;
```

---

## 스키마 적용

### 1. orders_schema.sql 적용

```bash
# 프로젝트 루트에서 실행
psql -U postgres -d stock_manager -f src/stock_manager/adapters/storage/schema/orders_schema.sql
```

**테이블**:
- `orders` - 주문 정보
- `order_fills` - 주문 체결 정보 (테이블 이름 확인 필요)

### 2. fills_schema.sql 적용

```bash
psql -U postgres -d stock_manager -f src/stock_manager/adapters/storage/schema/fills_schema.sql
```

**테이블**:
- `fills` - 체결 정보

### 3. worker_schema.sql 적용

```bash
psql -U postgres -d stock_manager -f src/stock_manager/adapters/storage/schema/worker_schema.sql
```

**테이블**:
- `stock_locks` - 분산 락 관리
- `worker_processes` - 워커 프로세스 추적
- `daily_summaries` - 일일 성과 요약

**함수 및 트리거**:
- `update_updated_at_column()` - updated_at 자동 업데이트 함수
- Triggers for stock_locks, worker_processes, daily_summaries

---

## 모든 스키마 일괄 적용

```bash
# 프로젝트 루트에서 실행
psql -U postgres -d stock_manager \
  -f src/stock_manager/adapters/storage/schema/orders_schema.sql \
  -f src/stock_manager/adapters/storage/schema/fills_schema.sql \
  -f src/stock_manager/adapters/storage/schema/worker_schema.sql
```

---

## 스키마 검증

### 테이블 목록 확인

```bash
psql -U postgres -d stock_manager -c "\dt"
```

**예상 결과**:
```
              List of relations
 Schema |       Name        | Type  |   Owner
--------+-------------------+-------+----------
 public | daily_summaries   | table | postgres
 public | fills            | table | postgres
 public | orders           | table | postgres
 public | stock_locks      | table | postgres
 public | worker_processes  | table | postgres
```

### 테이블 구조 확인

```bash
# stock_locks 테이블 구조
psql -U postgres -d stock_manager -c "\d stock_locks"

# worker_processes 테이블 구조
psql -U postgres -d stock_manager -c "\d worker_processes"

# daily_summaries 테이블 구조
psql -U postgres -d stock_manager -c "\d daily_summaries"
```

### 인덱스 확인

```bash
# 인덱스 목록
psql -U postgres -d stock_manager -c "\di"

# stock_locks 인덱스
psql -U postgres -d stock_manager -c "\di stock_locks"
```

**예상 인덱스 (stock_locks)**:
- `idx_stock_locks_symbol`
- `idx_stock_locks_worker_id`
- `idx_stock_locks_expires_at`
- `idx_stock_locks_status`

---

## 환경 변수 설정

`.env` 파일에 데이터베이스 연결 정보 추가:

```bash
# Database Configuration
DATABASE_URL=postgresql://postgres:password@localhost:5432/stock_manager
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=stock_manager
DATABASE_USER=postgres
DATABASE_PASSWORD=password
```

**또는 사용자별**:
```bash
DATABASE_URL=postgresql://stock_manager_user:your_password@localhost:5432/stock_manager
```

---

## Docker 사용 (추천)

### Docker Compose 설정

`docker-compose.yml` 파일 생성:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: stock-manager-db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_DB: stock_manager
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

### Docker 실행

```bash
# 컨테이너 시작
docker-compose up -d

# 컨테이너 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs postgres

# 스키마 적용
docker-compose exec postgres psql -U postgres -d stock_manager \
  -f /path/to/orders_schema.sql \
  -f /path/to/fills_schema.sql \
  -f /path/to/worker_schema.sql
```

---

## 테스트 쿼리

### stock_locks 테스트

```sql
-- 테스트 락 삽입
INSERT INTO stock_locks (symbol, worker_id, acquired_at, expires_at, heartbeat_at, status)
VALUES ('005930', 'worker-001', NOW(), NOW() + INTERVAL '5 minutes', NOW(), 'ACTIVE');

-- 락 조회
SELECT * FROM stock_locks WHERE symbol = '005930';

-- 락 해제
UPDATE stock_locks SET status = 'EXPIRED', updated_at = NOW()
WHERE symbol = '005930';
```

### worker_processes 테스트

```sql
-- 워커 등록
INSERT INTO worker_processes (worker_id, status, started_at, last_heartbeat_at, heartbeat_interval)
VALUES ('worker-001', 'IDLE', NOW(), NOW(), INTERVAL '30 seconds');

-- 워커 조회
SELECT * FROM worker_processes WHERE worker_id = 'worker-001';

-- 워커 상태 업데이트
UPDATE worker_processes SET status = 'SCANNING', updated_at = NOW()
WHERE worker_id = 'worker-001';
```

### daily_summaries 테스트

```sql
-- 일일 요약 생성
INSERT INTO daily_summaries (
    worker_id,
    summary_date,
    total_trades,
    winning_trades,
    losing_trades,
    gross_profit,
    gross_loss,
    net_pnl,
    unrealized_pnl,
    max_drawdown,
    win_rate,
    profit_factor
) VALUES (
    'worker-001',
    CURRENT_DATE,
    10,
    6,
    4,
    500000,
    300000,
    200000,
    100000,
    150000,
    0.6000,
    1.6667
);

-- 일일 요약 조회
SELECT * FROM daily_summaries
WHERE worker_id = 'worker-001'
ORDER BY summary_date DESC;
```

---

## 트러블슈팅

### 1. 연결 오류

**문제**:
```
psql: connection to server at "localhost" (::1), port 5432 failed
```

**해결**:
```bash
# PostgreSQL 서버 상태 확인
sudo systemctl status postgresql

# 서버 시작
sudo systemctl start postgresql

# 또는 macOS (Homebrew)
brew services start postgresql@15
```

### 2. 권한 오류

**문제**:
```
ERROR: permission denied for schema public
```

**해결**:
```sql
-- 권한 부여
GRANT ALL ON SCHEMA public TO stock_manager_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO stock_manager_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO stock_manager_user;
```

### 3. 스키마 파일 오타

**문제**:
```
ERROR: syntax error at or near "winning_trades"
```

**해결**:
```bash
# 스키마 파일 검증
psql -U postgres -d stock_manager -c "\f src/stock_manager/adapters/storage/schema/worker_schema.sql"

# 또는 파일을 직접 검사하여 오타 수정
```

### 4. 테이블 이미 존재

**문제**:
```
ERROR: relation "stock_locks" already exists
```

**해결**:
```bash
# 테이블 삭제 (주의: 데이터 손실)
psql -U postgres -d stock_manager -c "DROP TABLE IF EXISTS stock_locks CASCADE;"
psql -U postgres -d stock_manager -c "DROP TABLE IF EXISTS worker_processes CASCADE;"
psql -U postgres -d stock_manager -c "DROP TABLE IF EXISTS daily_summaries CASCADE;"

# 스키마 재적용
psql -U postgres -d stock_manager -f src/stock_manager/adapters/storage/schema/worker_schema.sql
```

---

## 백업 및 복구

### 백업

```bash
# 전체 데이터베이스 백업
pg_dump -U postgres stock_manager > stock_manager_backup_$(date +%Y%m%d).sql

# 또는 Docker 사용
docker exec stock-manager-db pg_dump -U postgres stock_manager > backup.sql
```

### 복구

```bash
# 백업 복구
psql -U postgres stock_manager < stock_manager_backup_20250124.sql

# 또는 Docker 사용
docker exec -i stock-manager-db psql -U postgres stock_manager < backup.sql
```

---

## 다음 단계

데이터베이스 설정이 완료되면:

1. **DatabasePort 구현**: PostgreSQL 어댑터 구현
2. **애플리케이션 설정**: `.env` 파일 설정
3. **연결 테스트**: 데이터베이스 연결 테스트
4. **워커 실행**: 워커 실행 및 테스트

---

## 참고 자료

- [PostgreSQL 공식 문서](https://www.postgresql.org/docs/15/)
- [Row-Level Locking](https://www.postgresql.org/docs/current/explicit-locking.html)
- [PostgreSQL JSON](https://www.postgresql.org/docs/15/datatype-json.html)
- [Docker PostgreSQL](https://hub.docker.com/_/postgres)
