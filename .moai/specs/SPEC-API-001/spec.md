# SPEC-API-001: KIS API Integration Fixes

## 메타데이터

- **SPEC ID**: SPEC-API-001
- **제목**: KIS API Integration Fixes
- **생성일**: 2026-01-28
- **상태**: planned
- **버전**: 1.0.0
- **우선순위**: MEDIUM
- **담당자**: Alfred (workflow-spec)
- **관련 SPEC**: SPEC-BACKEND-API-001-P3 (연관)
- **유형**: Bug Fix

---

## 개요 (Overview)

KIS Rest Client에서 TR_ID 헤더가 전송되지 않는 문제를 해결합니다.

**문제 정의:**
1. KISRestClient._get_headers()는 TR_ID 매개변수를 받지만
2. 실제 _make_request() 호출 시 tr_id=None으로 전달되어 헤더에 포함되지 않음

**현재 상태:**
- get_tr_id() 메서드로 TR_ID 조회 가능
- _get_headers(tr_id=...)로 헤더 생성 가능
- 하지만 _make_request() 호출 시 tr_id가 전달되지 않음

**목표:**
- API 호출에 필요한 TR_ID 헤더 정상 전송
- TR_ID 매핑 파일 활용

---

## 환경 (Environment)

### 기술 스택

- **Python**: 3.13+
- **HTTP 클라이언트**: httpx
- **KIS API**: 한국투자증권 OpenAPI

### 영향 받는 파일

1. **수정 파일**
   - `src/stock_manager/adapters/broker/kis/kis_rest_client.py`

---

## 요구사항 (Requirements)

### TAG BLOCK

```
TAG-SPEC-API-001-001: TR_ID 헤더 전송 구현
TAG-SPEC-API-001-002: place_order TR_ID 추가
TAG-SPEC-API-001-003: cancel_order TR_ID 추가
TAG-SPEC-API-001-004: get_orders TR_ID 추가
```

### 1. Ubiquitous Requirements (항상 지원)

**REQ-UB-001: TR_ID 헤더 전송**
- KIS API 호출은 필수 TR_ID 헤더를 포함해야 한다 (SHALL)
- TR_ID는 API별로 할당된 고유 값이어야 한다 (SHALL)
- 왜: KIS API 요구사항
- 영향: 401/403 에러

**REQ-UB-002: TR_ID 매핑 활용**
- TR_ID는 tr_id_mapping.json 파일에서 조회해야 한다 (SHALL)
- 모의투자/실거래 TR_ID를 구분해야 한다 (SHALL)
- 왜: KIS API 환경 차이
- 영향: 인증 실패

### 2. Event-Driven Requirements (WHEN X, THEN Y)

**REQ-ED-001: 주문 전송 시**
- WHEN place_order 호출됨
- THEN SHALL include correct TR_ID for order API
- AND SHALL pass tr_id to _make_request
- 왜: KIS API가 TR_ID로 API 식별
- 영향: "0000" 에러 코드

**REQ-ED-002: 주문 취소 시**
- WHEN cancel_order 호출됨
- THEN SHALL include correct TR_ID for cancel API
- 왜: 주문 취소는 별도 TR_ID

**REQ-ED-003: TR_ID 미존재 시**
- WHEN API ID가 매핑에 없음
- THEN SHALL raise ValueError with clear message
- 왜: 잘못된 API 호출 방지
- 영향: 디버깅 어려움

### 3. Unwanted Behaviors (금지된 동작)

**REQ-UN-001: TR_ID 누락 금지**
- API 호출 시 TR_ID 헤더를 누락해서는 안 됨 (MUST NOT)
- tr_id=None으로 _make_request 호출해서는 안 됨 (MUST NOT)
- 왜: KIS API 필수 요구사항
- 영향: 인증 실패

---

## 상세 설계 (Specifications)

### 현재 코드 문제 분석

**kis_rest_client.py (line 342-380):**

```python
def place_order(self, order: OrderRequest) -> str:
    # ... body construction ...

    # 해시키 생성
    hashkey = self.get_hashkey(body)
    headers = self._get_headers()  # <- tr_id=None (기본값)
    if hashkey:
        headers["hashkey"] = hashkey

    # 주문 전송
    response = self._make_request(
        "POST",
        "/uapi/domestic-stock/v1/trading/order-cash",
        json_data=body,
        # tr_id 전달 안됨
    )
```

### 수정 방안

**1. API ID 정의**

각 KIS API 메서드에 해당하는 API ID 매핑:

```python
class KISRestClient:
    # API ID constants
    API_ORDER_CASH = "국내주식-008"      # 주식 주문 (현금)
    API_ORDER_CANCEL = "국내주식-009"    # 주식 정정취소
    API_INQUIRE_BALANCE = "국내주식-017" # 주식잔고조회
```

**2. place_order 수정**

```python
def place_order(self, order: OrderRequest) -> str:
    """주문 전송

    Args:
        order: 주문 요청

    Returns:
        str: 브로커 주문 ID
    """
    # TR_ID 조회
    is_paper = (self.config.mode == Mode.PAPER)
    tr_id = self.get_tr_id(self.API_ORDER_CASH, is_paper_trading=is_paper)

    if not tr_id:
        raise ValueError(f"TR_ID not found for API: {self.API_ORDER_CASH}")

    # 주문 본문 구성
    body = {
        "CANO": order.account_id[:8],
        "ACNT_PRDT_CD": order.account_id[8:],
        "PDNO": order.symbol,
        "SLL_BK_DVSN_CD": "01" if order.side == OrderSide.BUY else "02",
        "ORD_QTY": str(order.qty),
        "ORD_UNPR": str(order.price) if order.price else "",
        "ORD_DVSN": "01" if order.order_type == OrderType.MARKET else "00",
    }

    # 해시키 생성
    hashkey = self.get_hashkey(body)

    # TR_ID 포함 헤더 생성
    headers = self._get_headers(tr_id=tr_id)
    if hashkey:
        headers["hashkey"] = hashkey

    # 주문 전송 (명시적 tr_id 전달)
    response = self._make_request(
        "POST",
        "/uapi/domestic-stock/v1/trading/order-cash",
        json_data=body,
        tr_id=tr_id,  # TAG-SPEC-API-001-002
    )

    return response["output"]["ODNO"]
```

**3. cancel_order 수정**

```python
def cancel_order(self, broker_order_id: str, account_id: str) -> bool:
    """주문 취소"""
    # TAG-SPEC-API-001-003: cancel_order TR_ID 추가
    is_paper = (self.config.mode == Mode.PAPER)
    tr_id = self.get_tr_id(self.API_ORDER_CANCEL, is_paper_trading=is_paper)

    if not tr_id:
        raise ValueError(f"TR_ID not found for API: {self.API_ORDER_CANCEL}")

    body = {
        "CANO": account_id[:8],
        "ACNT_PRDT_CD": account_id[8:],
        "ODNO": broker_order_id,
        "ORD_DVSN": "02",
    }

    headers = self._get_headers(tr_id=tr_id)

    try:
        response = self._make_request(
            "POST",
            "/uapi/domestic-stock/v1/trading/order-rvsecncl",
            json_data=body,
            tr_id=tr_id,
        )
        return response["rt_cd"] == "0"
    except Exception as e:
        logger.error(f"Cancel order failed: {e}")
        return False
```

**4. get_orders 수정**

```python
def get_orders(self, account_id: str) -> list[Order]:
    """주문 목록 조회"""
    # TAG-SPEC-API-001-004: get_orders TR_ID 추가
    is_paper = (self.config.mode == Mode.PAPER)
    tr_id = self.get_tr_id(self.API_INQUIRE_BALANCE, is_paper_trading=is_paper)

    if not tr_id:
        raise ValueError(f"TR_ID not found for API: {self.API_INQUIRE_BALANCE}")

    params = {
        "CANO": account_id[:8],
        "ACNT_PRDT_CD": account_id[8:],
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }

    headers = self._get_headers(tr_id=tr_id)

    response = self._make_request(
        "GET",
        "/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl",
        params=params,
        tr_id=tr_id,
    )

    # ... rest of implementation
```

---

## 추적성 (Traceability)

### TAG Mapping

| TAG | 설명 | 파일 | 수정 라인 |
|-----|------|------|----------|
| TAG-SPEC-API-001-001 | TR_ID 헤더 전송 구현 | kis_rest_client.py | _make_request 호출 |
| TAG-SPEC-API-001-002 | place_order TR_ID 추가 | kis_rest_client.py | place_order 메서드 |
| TAG-SPEC-API-001-003 | cancel_order TR_ID 추가 | kis_rest_client.py | cancel_order 메서드 |
| TAG-SPEC-API-001-004 | get_orders TR_ID 추가 | kis_rest_client.py | get_orders 메서드 |

---

## 의존성 (Dependencies)

### 선행 SPEC (Prerequisites)
- **SPEC-KIS-DOCS-001**: KIS OpenAPI Documentation (TR_ID 매핑 파일)

### 후속 SPEC (Dependents)
None - 이 SPEC은 독립적으로 완료 가능

---

## TR_ID 매핑 파일 참조

**docs/kis-openapi/_data/tr_id_mapping.json:**

```json
{
  "국내주식-008": {
    "name": "주식주문(현금)",
    "real_tr_id": "TTTC0801U",
    "paper_tr_id": "TTTC0801U",
    "url": "/uapi/domestic-stock/v1/trading/order-cash"
  },
  "국내주식-009": {
    "name": "주식정정취소주문",
    "real_tr_id": "TTTC0901U",
    "paper_tr_id": "TTTC0901U",
    "url": "/uapi/domestic-stock/v1/trading/order-rvsecncl"
  },
  "국내주식-017": {
    "name": "주식잔고조회",
    "real_tr_id": "TTTC8434R",
    "paper_tr_id": "TTTC8434R",
    "url": "/uapi/domestic-stock/v1/trading/inquire-balance"
  }
}
```
