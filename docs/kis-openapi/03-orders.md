# 주문 (Order)

## 개요

주문 관련 API는 주식 매수/매도 주문, 예약주문, 정정/취소 등을 수행합니다.

## API 목록

### 1. 주식주문(현금)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 주식주문(현금) |
| **API ID** | v1_국내주식-001 |
| **HTTP Method** | POST |
| **URL** | /uapi/domestic-stock/v1/trading/order-cash |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |
| **Hashkey 필요** | Y |

**설명:**
현금으로 주식을 매수/매도합니다.
※ TTC0802U(현금매수) 사용하셔서 미수매수 가능합니다. 단, 거래하시는 계좌가 증거금40%계좌로 신청이 되어있어야 가능합니다.

**Request Parameters:**
| Parameter | 한글명 | Type | Required | Description |
|-----------|----------|-------|-----------|-------------|
| CANO | 계좌번호 | string | Y | 8자리 계좌번호 |
| ACNT_PRDT_CD | 계좌상품코드 | string | Y | 01: 주식 |
| ODNO | 주문번호 | string | N | 정정/취소 시 필수 |
| SLL_BUY_DVSN_CD | 매도매수구분코드 | string | Y | 01: 매수, 02: 매도 |
| LSLL_DVSN_CD | 대매도대매수구분코드 | string | N | 00: 없음, 01: 대매도, 02: 대매수 |
| SHTN_PDNO | 종목코드 | string | Y | 종목코드 |
| ORD_QTY | 주문수량 | number | Y | 주문 수량 |
| UNIT_PRICE | 주문단가 | number | N | 지정가 주문 시 단가 |
| NMPR_TYPE_CD | 호가유형코드 | string | N | 00: 지정가, 01: 최우선호가, 02: 시장가 |
| KRX_NMPR_CNDT_CD | 거래소호가조건코드 | string | N | |
| CTAC_TLNO | 계좌전화번호 | string | N | |
| FUOP_ITEM_DVSN_CD | 기능파생상품구분코드 | string | N | |
| ORD_DVSN_CD | 주문구분코드 | string | N | 01: 정규주문, 02: 예약주문 |
| ALGO_NO | 알고리즘주문번호 | string | N | 알고리즘 주문 사용 시 |

**Response Fields:**
| Field | 한글명 | Type | Description |
|-------|----------|-------|-------------|
| ODNO | 주문번호 | string | 주문 번호 |
| ODNO_ITMNO | 주문번호_항번 | string | 주문번호와 항번 |
| ORD_TMD | 주문시간 | string | 주문 시간 |

**Python 코드 예시:**
```python
import requests
import hashlib

def place_cash_order(access_token, appkey, appsecret, 
                   cano, shtn_pdno, ord_qty, 
                   sll_buy_dvsn_cd="01", unit_price=None, 
                   nmpr_type_cd="00"):
    """
    현금 주식 주문
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        cano: 계좌번호
        shtn_pdno: 종목코드
        ord_qty: 주문수량
        sll_buy_dvsn_cd: 01:매수, 02:매도
        unit_price: 지정가 (None=시장가)
        nmpr_type_cd: 00:지정가, 01:최우선호가, 02:시장가
    
    Returns:
        dict: 주문 결과
    """
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/order-cash"
    
    # 주문 본문
    order_body = {
        "CANO": cano,
        "ACNT_PRDT_CD": "01",
        "SLL_BUY_DVSN_CD": sll_buy_dvsn_cd,
        "SHTN_PDNO": shtn_pdno,
        "ORD_QTY": str(ord_qty),
        "NMPR_TYPE_CD": nmpr_type_cd
    }
    
    if unit_price:
        order_body["UNIT_PRICE"] = str(unit_price)
    
    # 해시키 생성 (선택사항)
    hashkey = get_hashkey(appkey, appsecret, order_body)
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8",
        "tr_id": "v1_국내주식-001",
        "hashkey": hashkey  # 선택사항
    }
    
    response = requests.post(url, headers=headers, json=order_body)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"주문 실패: {response.status_code}, {response.text}")

def get_hashkey(appkey, appsecret, request_body):
    """해시키 생성"""
    url = "https://openapi.koreainvestment.com:9443/uapi/hashkey"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "appkey": appkey,
        "appsecret": appsecret
    }
    response = requests.post(url, headers=headers, json=request_body)
    if response.status_code == 200:
        return response.json()["HASH"]
    return ""

# 사용 예시
try:
    # 매수 주문 (지정가)
    result = place_cash_order(
        access_token="your_access_token",
        appkey="your_appkey",
        appsecret="your_appsecret",
        cano="00000000",
        shtn_pdno="005930",
        ord_qty=10,
        sll_buy_dvsn_cd="01",  # 매수
        unit_price=50000,  # 지정가 50,000원
        nmpr_type_cd="00"  # 지정가
    )
    print(f"주문 성공: {result}")
    
except Exception as e:
    print(f"주문 실패: {e}")
```

---

### 2. 주식주문(신용)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 주식주문(신용) |
| **API ID** | v1_국내주식-002 |
| **HTTP Method** | POST |
| **URL** | /uapi/domestic-stock/v1/trading/order-credit |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |
| **Hashkey 필요** | Y |

**설명:**
신용으로 주식을 매수합니다.

**Request Parameters:**
| Parameter | 한글명 | Type | Required | Description |
|-----------|----------|-------|-----------|-------------|
| CANO | 계좌번호 | string | Y | 8자리 계좌번호 |
| ACNT_PRDT_CD | 계좌상품코드 | string | Y | 01: 주식 |
| SLL_BUY_DVSN_CD | 매도매수구분코드 | string | Y | 01: 매수, 02: 매도 |
| SHTN_PDNO | 종목코드 | string | Y | 종목코드 |
| ORD_QTY | 주문수량 | number | Y | 주문 수량 |
| UNIT_PRICE | 주문단가 | number | N | 지정가 주문 시 단가 |
| LOAN_DT | 대출일자 | string | N | YYYYMMDD |
| CDTN_TCD | 대출거래코드 | string | N | |

---

### 3. 주식주문(정정취소)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 주식주문(정정취소) |
| **API ID** | v1_국내주식-020 |
| **HTTP Method** | POST |
| **URL** | /uapi/domestic-stock/v1/trading/order-rvsecnccl |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |
| **Hashkey 필요** | Y |

**설명:**
주식 주문을 정정 또는 취소합니다.

**Request Parameters:**
| Parameter | 한글명 | Type | Required | Description |
|-----------|----------|-------|-----------|-------------|
| CANO | 계좌번호 | string | Y | 8자리 계좌번호 |
| ACNT_PRDT_CD | 계좌상품코드 | string | Y | 01: 주식 |
| ODNO | 주문번호 | string | Y | 정정/취소할 주문번호 |
| RVSE_CLS_DVSN_CD | 정정취소구분코드 | string | Y | 02: 정정, 04: 취소 |
| ORG_ODNO | 원주문번호 | string | Y | 정정 시 원주문번호 |
| SHTN_PDNO | 종목코드 | string | Y | 종목코드 |
| ORD_QTY | 주문수량 | number | Y | 정정 수량 |
| ORD_DVSN_CD | 주문구분코드 | string | N | 01: 정규주문, 02: 예약주문 |

**Python 코드 예시:**
```python
def cancel_order(access_token, appkey, appsecret, 
               cano, odno, rvse_cls_dvsn_cd, 
               shtn_pdno, ord_qty):
    """
    주문 정정/취소
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        cano: 계좌번호
        odno: 주문번호
        rvse_cls_dvsn_cd: 02:정정, 04:취소
        shtn_pdno: 종목코드
        ord_qty: 정정수량
    
    Returns:
        dict: 정정/취소 결과
    """
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/order-rvsecnccl"
    
    order_body = {
        "CANO": cano,
        "ACNT_PRDT_CD": "01",
        "ODNO": odno,
        "RVSE_CLS_DVSN_CD": rvse_cls_dvsn_cd,
        "SHTN_PDNO": shtn_pdno,
        "ORD_QTY": str(ord_qty)
    }
    
    # 해시키 생성
    hashkey = get_hashkey(appkey, appsecret, order_body)
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8",
        "tr_id": "v1_국내주식-020",
        "hashkey": hashkey
    }
    
    response = requests.post(url, headers=headers, json=order_body)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"정정/취소 실패: {response.status_code}")

# 사용 예시
# 주문 취소
result = cancel_order(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret",
    cano="00000000",
    odno="0000000001",
    rvse_cls_dvsn_cd="04",  # 취소
    shtn_pdno="005930",
    ord_qty=10
)
print(f"취소 결과: {result}")
```

---

### 4. 주식예약주문

| 항목 | 내용 |
|--------|--------|
| **API 명** | 주식예약주문 |
| **API ID** | v1_국내주식-017 |
| **HTTP Method** | POST |
| **URL** | /uapi/domestic-stock/v1/trading/order-resv |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |
| **Hashkey 필요** | Y |

**설명:**
시장 시작 전 예약주문을 등록합니다.

---

### 5. 주식예약주문조회

| 항목 | 내용 |
|--------|--------|
| **API 명** | 주식예약주문조회 |
| **API ID** | v1_국내주식-019 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/trading/inquire-resv-order |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
등록된 예약주문을 조회합니다.

---

### 6. 주식예약주문정정취소

| 항목 | 내용 |
|--------|--------|
| **API 명** | 주식예약주문정정취소 |
| **API ID** | v1_국내주식-018,019 |
| **HTTP Method** | POST |
| **URL** | /uapi/domestic-stock/v1/trading/order-resv-rvsecncl |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |
| **Hashkey 필요** | Y |

**설명:**
예약주문을 정정 또는 취소합니다.

## 주의사항

### 주문 구분 코드

| 구분코드 | 설명 |
|----------|--------|
| SLL_BUY_DVSN_CD 01 | 매수 |
| SLL_BUY_DVSN_CD 02 | 매도 |
| NMPR_TYPE_CD 00 | 지정가 |
| NMPR_TYPE_CD 01 | 최우선호가 |
| NMPR_TYPE_CD 02 | 시장가 |
| RVSE_CLS_DVSN_CD 02 | 정정 |
| RVSE_CLS_DVSN_CD 04 | 취소 |

### 주의사항

1. **해시키(Hashkey)**: 주문/정정/취소 API는 보안을 위해 해시키 사용 권장
2. **주문수량**: 주문수량 단위 확인 (주당, 1계약 등)
3. **가능조회**: 주문 전 반드시 매수/매도 가능 확인 필요
4. **계좌상품코드**: 01(주식) 사용 시 증거금 부족 시 주문 불가
5. **시장가 주문**: 시장가 주문 시 UNIT_PRICE는 지정하지 않거나 0으로 설정
6. **모의투자**: 모의투자에서는 현금 주문만 가능

### 주문 워크플로우 예시

```python
# 1. 계좌 잔고 확인
balance = get_stock_balance(...)

# 2. 매수 가능 확인
buyable = get_buyable_qty(...)

# 3. 주문 전송
result = place_cash_order(...)

# 4. 주문 번호 저장
order_no = result.get('ODNO')

# 5. 체결 확인 (04-execution.md 참조)
execution = check_execution(...)
```
