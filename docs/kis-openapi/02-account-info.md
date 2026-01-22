# 계좌 정보 (Account Info)

## 개요

계좌 정보 관련 API는 사용자의 계좌 잔고, 자산, 예수금, 주문 가능 여부 등을 조회합니다.

## API 목록

### 1. 주식잔고조회

| 항목 | 내용 |
|--------|--------|
| **API 명** | 주식잔고조회 |
| **API ID** | v1_국내주식-006 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/trading/inquire-balance |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
계좌에 보유한 주식의 잔고 정보를 조회합니다.

**Request Parameters:**
| Parameter | 한글명 | Type | Required | Description |
|-----------|----------|-------|-----------|-------------|
| CANO | 계좌번호 | string | Y | 8자리 계좌번호 |
| ACNT_PRDT_CD | 계좌상품코드 | string | Y | 01: 주식, 02: 선물옵션 등 |
| AFHR_FLPR_YN | 앞면포함여부 | string | N | Y: 앞면포함, N: 앞면미포함 |
| OFR_YN | 주식미포함여부 | string | N | Y: 주식미포함, N: 주식포함 |
| INQR_DVSN | 조회구분 | string | N | 01: 시장가, 02: 예상가 |
| SRT_DD | 검색시작일자 | string | N | YYYYMMDD |
| END_DD | 검색종료일자 | string | N | YYYYMMDD |
| CTSN | 연속조회수 | string | N | 최대 100 |

**Response Fields:**
| Field | 한글명 | Type | Description |
|-------|----------|-------|-------------|
| output | 출력구분 | string | 1: 성공 |
| tlong | 장종가구분 | number | 1: 시장가, 2: 예상가 |
| rst_cnt | 조회건수 | number | 조회한 총 건수 |
| rt_cd | 응답코드 | string | 0: 성공, 그 외: 실패 |
| msg_cd | 메시지코드 | string | |
| msg1 | 메시지1 | string | |
| msg2 | 메시지2 | string | |
| tlong_pdno_list | 종목별잔고리스트 | array | 종목별 잔고 정보 |

**Python 코드 예시:**
```python
import requests

def get_stock_balance(access_token, appkey, appsecret, cano, acnt_prdt_cd):
    """
    주식 잔고 조회
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        cano: 계좌번호
        acnt_prdt_cd: 계좌상품코드 (01: 주식)
    
    Returns:
        dict: 잔고 정보
    """
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/inquire-balance"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8",
        "tr_id": "v1_국내주식-006"
    }
    
    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"잔고 조회 실패: {response.status_code}")

# 사용 예시
balance = get_stock_balance(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret",
    cano="00000000",
    acnt_prdt_cd="01"
)

for stock in balance.get('output', []).get('tlong_pdno_list', []):
    print(f"종목코드: {stock.get('pdno')}")
    print(f"종목명: {stock.get('prdt_name')}")
    print(f"보유수량: {stock.get('hldg_qty')}")
    print(f"평가금액: {stock.get('evlu_amt')}")
    print("-" * 40)
```

---

### 2. 매수가능조회

| 항목 | 내용 |
|--------|--------|
| **API 명** | 매수가능조회 |
| **API ID** | v1_국내주식-007 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/trading/inquire-psbl-order |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
주식 매수 가능 금액/수량을 조회합니다.

**Request Parameters:**
| Parameter | 한글명 | Type | Required | Description |
|-----------|----------|-------|-----------|-------------|
| CANO | 계좌번호 | string | Y | 8자리 계좌번호 |
| ACNT_PRDT_CD | 계좌상품코드 | string | Y | 01: 주식 |
| OVRS_EXCG_CD | 거래소코드 | string | N | 기본값: SHAA (한국거래소) |
| SRT_DN | 매수기준일자 | string | N | YYYYMMDD |
| ORD_GNO_BRNC | 일일주문번호분기 | string | N | N: 연속, Y: 분기 |
| CTAC_TLNO | 계좌전화번호 | string | N | |

**Response Fields:**
| Field | 한글명 | Type | Description |
|-------|----------|-------|-------------|
| output | 출력구분 | string | 1: 성공 |
| rsym | 주문가능금액 | number | 주문 가능 금액 |
| ord_psbl_qty | 주문가능수량 | number | 주문 가능 수량 |
| hldg_qty | 보유수량 | number | 현재 보유 수량 |
| rt_cd | 응답코드 | string | 0: 성공 |

**Python 코드 예시:**
```python
import requests

def get_buyable_qty(access_token, appkey, appsecret, cano):
    """
    매수 가능 수량 조회
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        cano: 계좌번호
    
    Returns:
        dict: 주문 가능 정보
    """
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/inquire-psbl-order"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8",
        "tr_id": "v1_국내주식-007"
    }
    
    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": "01"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"매수가능조회 실패: {response.status_code}")
```

---

### 3. 매도가능수량조회

| 항목 | 내용 |
|--------|--------|
| **API 명** | 매도가능수량조회 |
| **API ID** | v1_국내주식-039 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/trading/inquire-psbl-sell |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
보유 종목별 매도 가능 수량을 조회합니다.

**Request Parameters:**
| Parameter | 한글명 | Type | Required | Description |
|-----------|----------|-------|-----------|-------------|
| CANO | 계좌번호 | string | Y | 8자리 계좌번호 |
| ACNT_PRDT_CD | 계좌상품코드 | string | Y | 01: 주식 |
| SRT_DN | 매도기준일자 | string | N | YYYYMMDD |
| PDNO | 종목코드 | string | N | 종목코드 |

**Response Fields:**
| Field | 한글명 | Type | Description |
|-------|----------|-------|-------------|
| output | 출력구분 | string | 1: 성공 |
| psbl_qty | 매도가능수량 | number | 매도 가능 수량 |
| rt_cd | 응답코드 | string | 0: 성공 |

---

### 4. 투자계좌자산현황조회

| 항목 | 내용 |
|--------|--------|
| **API 명** | 투자계좌자산현황조회 |
| **API ID** | v1_국내주식-048 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/trading/inquire-account-balance |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
계좌별 자산 현황을 조회합니다.

**Request Parameters:**
| Parameter | 한글명 | Type | Required | Description |
|-----------|----------|-------|-----------|-------------|
| CANO | 계좌번호 | string | Y | 8자리 계좌번호 |
| ACNT_PRDT_CD | 계좌상품코드 | string | N | 01: 주식 |
| OFR_YN | 주식미포함여부 | string | N | Y: 주식미포함, N: 주식포함 |
| INQR_DVSN | 조회구분 | string | N | 01: 전체, 02: 예수금, 03: 증거금 |

---

### 5. 기간별계좌권리현황조회

| 항목 | 내용 |
|--------|--------|
| **API 명** | 기간별계좌권리현황조회 |
| **API ID** | 국내주식-211 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/trading/period-rights |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
기간별 계좌 권리 현황(배당, 유/무상증자 등)을 조회합니다.

**Request Parameters:**
| Parameter | 한글명 | Type | Required | Description |
|-----------|----------|-------|-----------|-------------|
| CANO | 계좌번호 | string | Y | 8자리 계좌번호 |
| SRT_DN | 검색시작일자 | string | Y | YYYYMMDD |
| END_DN | 검색종료일자 | string | Y | YYYYMMDD |
| CTAC_TLNO | 계좌전화번호 | string | N | |

---

### 6. 신용매수가능조회

| 항목 | 내용 |
|--------|--------|
| **API 명** | 신용매수가능조회 |
| **API ID** | v1_국내주식-042 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/trading/inquire-credit-psamount |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
신용 매수 가능 금액/수량을 조회합니다.

---

### 7. 주식통합증거금 현황

| 항목 | 내용 |
|--------|--------|
| **API 명** | 주식통합증거금 현황 |
| **API ID** | 국내주식-191 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/trading/intgr-margin |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
계좌의 통합 증거금 현황을 조회합니다.

---

### 8. 기간별매매손익현황조회

| 항목 | 내용 |
|--------|--------|
| **API 명** | 기간별매매손익현황조회 |
| **API ID** | 국내주식-212 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/trading/period-profit-loss |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
기간별 매매 손익 현황을 조회합니다.

---

### 9. 기간별손익일별합산조회

| 항목 | 내용 |
|--------|--------|
| **API 명** | 기간별손익일별합산조회 |
| **API ID** | 국내주식-213 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/trading/period-daily-profit-loss |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
기간별 손익을 일별로 합산하여 조회합니다.

---

### 10. 주식잔고조회_실현손익

| 항목 | 내용 |
|--------|--------|
| **API 명** | 주식잔고조회_실현손익 |
| **API ID** | v1_국내주식-041 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/trading/inquire-balance-rlz-pl |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
주식 잔고와 실현 손익을 함께 조회합니다.

---

### 11. 국내주식 신용잔고 일별추이

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 신용잔고 일별추이 |
| **API ID** | 국내주식-110 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/daily-credit-balance |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 신용잔고의 일별 추이를 조회합니다.

---

## 공통 사용 패턴

```python
# 주문 전 계좌 확인
balance = get_stock_balance(access_token, appkey, appsecret, cano, acnt_prdt_cd)

# 주문 가능 여부 확인
buyable = get_buyable_qty(access_token, appkey, appsecret, cano)

# 주문 실행 (03-orders.md 참조)
order_result = place_order(...)

# 체결 확인 (04-execution.md 참조)
execution_result = check_execution(...)
```

## 주의사항

1. **계좌번호(CANO)**: 한국투자증권에서 확인한 8자리 계좌번호 사용
2. **계좌상품코드(ACNT_PRDT_CD)**: 
   - 01: 주식
   - 02: 선물옵션 등
3. **거래소코드(OVRS_EXCG_CD)**:
   - SHAA: 한국거래소
   - SHCQ: 코스닥
   - SHDA: 코스피200
4. 일일 API 호출 횟수 제한 주의
