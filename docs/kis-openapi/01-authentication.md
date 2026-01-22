# 인증 (Authentication)

## 개요

인증 관련 API는 한국투자증권 OpenAPI를 사용하기 위한 인증 절차와 토큰 관리를 제공합니다.

## API 목록

### 1. Hashkey

| 항목 | 내용 |
|--------|--------|
| **API 명** | Hashkey |
| **API ID** | Hashkey |
| **HTTP Method** | POST |
| **URL** | /uapi/hashkey |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |
| **Domain (모의)** | https://openapivts.koreainvestment.com:29443 |

**설명:**
해시키(Hashkey)는 보안을 위한 요소로 사용자가 보낸 요청 값을 중간에 탈취하여 변조하지 못하도록 하는 데 사용됩니다.
해시키를 사용하면 POST로 보내는 요청(주로 주문/정정/취소 API 해당)의 body 값을 사전에 암호화시킬 수 있습니다.
해시키는 비필수값으로 사용하지 않아도 POST API 호출은 가능합니다.

**Request Header:**
| Element | 한글명 | Type | Required | Description |
|----------|----------|-------|-----------|-------------|
| content-type | 컨텐츠타입 | string | N | application/json; charset=utf-8 |
| appkey | 앱키 | string | Y | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 한국투자증권 홈페이지에서 발급받은 appsecret (절대 노출되지 않도록 주의해주세요.) |

**Request Body:**
| Element | 한글명 | Type | Required | Description |
|----------|----------|-------|-----------|-------------|
| JsonBody | 요청값 | object | Y | POST로 보낼 body값 |

**Response Body:**
| Element | 한글명 | Type | Required | Description |
|----------|----------|-------|-----------|-------------|
| JsonBody | 요청값 | object | Y | 요청한 JsonBody |
| HASH | 해시키 | string | Y | [POST API 대상] Client가 요청하는 Request Body를 hashkey api로 생성한 Hash값 |

**Python 코드 예시:**
```python
import requests

def get_hashkey(appkey, appsecret, request_body):
    """
    해시키 발급
    
    Args:
        appkey: 앱키
        appsecret: 앱시크릿키
        request_body: 요청 본문 (dict)
    
    Returns:
        str: 해시키
    """
    url = "https://openapi.koreainvestment.com:9443/uapi/hashkey"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "appkey": appkey,
        "appsecret": appsecret
    }
    
    response = requests.post(url, headers=headers, json=request_body)
    
    if response.status_code == 200:
        return response.json()["HASH"]
    else:
        raise Exception(f"해시키 발급 실패: {response.status_code}, {response.text}")

# 사용 예시
appkey = "PSg5dctL9dKPo727J13Ur405OSXXXXXXXXXX"
appsecret = "yo2t8zS68zpdjGuWvFyM9VikjXE0i0CbgPEamnqPA00G0bIfrdfQb2RUD1xP7SqatQXr1cD1fGUNsb78MMXoq6o4lAYt9YTtHAjbMoFy+c72kbq5owQY1Pvp39/x6ejpJlXCj7gE3yVOB/h25Hvl+URmYeBTfrQeOqIAOYc/OIXXXXXXXXXX"

order_body = {
    "CANO": "00000000",
    "ACNT_PRDT_CD": "01",
    "SHTN_PDNO": "005930",
    "ORD_QTY": "10",
    "UNIT_PRICE": "50000",
    "ORD_DVSN_CD": "01",
    "CANO": "00000000"
}

hashkey = get_hashkey(appkey, appsecret, order_body)
print(f"Hashkey: {hashkey}")
```

---

### 2. 실시간 (웹소켓) 접속키 발급

| 항목 | 내용 |
|--------|--------|
| **API 명** | 실시간 (웹소켓) 접속키 발급 |
| **API ID** | 실시간-000 |
| **HTTP Method** | POST |
| **URL** | /oauth2/Approval |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |
| **Domain (모의)** | https://openapivts.koreainvestment.com:29443 |

**설명:**
실시간 (웹소켓) 접속키 발급받으실 수 있는 API 입니다.
웹소켓 이용 시 해당 키를 appkey와 appsecret 대신 헤더에 넣어 API를 호출합니다.

접속키의 유효기간은 24시간이지만, 접속키는 세션 연결 시 초기 1회만 사용하기 때문에 접속키 인증 후에는 세션종료되지 않는 이상 접속키 신규 발급받지 않으셔도 365일 내내 웹소켓 데이터 수신하실 수 있습니다.

**Python 코드 예시:**
```python
import requests

def get_approval_key(appkey, appsecret):
    """
    웹소켓 접속키 발급
    
    Args:
        appkey: 앱키
        appsecret: 앱시크릿키
    
    Returns:
        str: 접속키
    """
    url = "https://openapi.koreainvestment.com:9443/oauth2/Approval"
    headers = {
        "Content-Type": "application/json"
    }
    
    data = {
        "grant_type": "client_credentials",
        "appkey": appkey,
        "secretkey": appsecret
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        result = response.json()
        return result["approval_key"]
    else:
        raise Exception(f"접속키 발급 실패: {response.status_code}")

# 웹소켓 연결 시 헤더 사용
import websocket

ws_headers = {
    "approval_key": get_approval_key(appkey, appsecret)
}

ws = websocket.WebSocketApp(
    "wss://openapi.koreainvestment.com:9443/ws",
    header=ws_headers
)
```

---

### 3. 접근토큰폐기(P)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 접근토큰폐기(P) |
| **API ID** | 인증-002 |
| **HTTP Method** | POST |
| **URL** | /oauth2/revokeP |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |
| **Domain (모의)** | https://openapivts.koreainvestment.com:29443 |

**설명:**
부여받은 접근토큰을 더 이상 활용하지 않을 때 사용합니다.

**Python 코드 예시:**
```python
import requests

def revoke_access_token(appkey, appsecret):
    """
    접근토큰 폐기
    
    Args:
        appkey: 앱키
        appsecret: 앱시크릿키
    
    Returns:
        bool: 성공 여부
    """
    url = "https://openapi.koreainvestment.com:9443/oauth2/revokeP"
    headers = {
        "Content-Type": "application/json"
    }
    
    data = {
        "appkey": appkey,
        "appsecret": appsecret
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    return response.status_code == 200
```

---

### 4. 접근토큰발급(P)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 접근토큰발급(P) |
| **API ID** | 인증-001 |
| **HTTP Method** | POST |
| **URL** | /oauth2/tokenP |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |
| **Domain (모의)** | https://openapivts.koreainvestment.com:29443 |

**설명:**
본인 계좌에 필요한 인증 절차로, 인증을 통해 접근 토큰을 부여받아 오픈API 활용이 가능합니다.

1. 접근토큰(access_token)의 유효기간은 24시간이며(1일 1회발급 원칙)
   갱신발급주기는 6시간입니다.(6시간 이내는 기존 발급키로 응답)

2. 접근토큰발급(/oauth2/tokenP) 시 접근토큰값(access_token)과 함께 수신되는
   접근토큰 유효기간(acess_token_token_expired)을 이용해 접근토큰을 관리하실 수 있습니다.

**[참고]**
23.4.28 이후 지나치게 잦은 토큰 발급 요청건을 제어하기 위해 신규 접근토큰발급 이후 일정시간 이내에 재호출 시에는 직전 토큰값을 리턴하게 되었습니다. 일정시간 이후 접근토큰발급 API 호출 시에는 신규 토큰값을 리턴합니다.
접근토큰발급 API 호출 및 코드 작성하실 때 해당 사항을 참고하시길 바랍니다.

**Request Body:**
| Element | 한글명 | Type | Required | Length | Description |
|----------|----------|-------|-----------|---------|-------------|
| grant_type | 권한부여 Type | string | Y | 18 | client_credentials |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appsecret (절대 노출되지 않도록 주의해주세요.) |

**Response Body:**
| Element | 한글명 | Type | Required | Length | Description |
|----------|----------|-------|-----------|---------|-------------|
| access_token | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token |
| token_type | 접근토큰유형 | string | Y | 20 | 접근토큰유형 : "Bearer" |
| expires_in | 접근토큰 유효기간 | number | Y | 10 | 유효기간(초) |
| access_token_token_expired | 접근토큰 유효기간(일시표시) | string | Y | 50 | 유효기간(년:월:일 시:분:초) |

**Python 코드 예시:**
```python
import requests
from datetime import datetime

def get_access_token(appkey, appsecret):
    """
    접근토큰 발급
    
    Args:
        appkey: 앱키
        appsecret: 앱시크릿키
    
    Returns:
        dict: access_token, token_type, expires_in, access_token_token_expired
    """
    url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
    headers = {
        "Content-Type": "application/json"
    }
    
    data = {
        "grant_type": "client_credentials",
        "appkey": appkey,
        "appsecret": appsecret
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        result = response.json()
        return {
            "access_token": result["access_token"],
            "token_type": result["token_type"],
            "expires_in": result["expires_in"],
            "access_token_token_expired": result.get("access_token_token_expired")
        }
    else:
        raise Exception(f"접근토큰 발급 실패: {response.status_code}, {response.text}")

# 사용 예시
appkey = "PSg5dctL9dKPo727J13Ur405OSXXXXXXXXXX"
appsecret = "yo2t8zS68zpdjGuWvFyM9VikjXE0i0CbgPEamnqPA00G0bIfrdfQb2RUD1xP7SqatQXr1cD1fGUNsb78MMXoq6o4lAYt9YTtHAjbMoFy+c72kbq5owQY1Pvp39/x6ejpJlXCj7gE3yVOB/h25Hvl+URmYeBTfrQeOqIAOYc/OIXXXXXXXXXX"

token_info = get_access_token(appkey, appsecret)
print(f"Access Token: {token_info['access_token']}")
print(f"Token Type: {token_info['token_type']}")
print(f"Expires: {token_info['access_token_token_expired']}")

# API 호출 시 헤더 설정
api_headers = {
    "Authorization": f"Bearer {token_info['access_token']}",
    "appkey": appkey,
    "appsecret": appsecret,
    "Content-Type": "application/json; charset=utf-8"
}
```

## 인증 절차 요약

1. 한국투자증권 홈페이지에서 앱키, 앱시크릿키 발급
2. 접근토큰 발급 (/oauth2/tokenP)
3. (선택사항) 해시키 발급 (/uapi/hashkey)
4. API 호출 시 Authorization 헤더에 Bearer 토큰 포함

## 주의사항

- 접근토큰 유효기간 만료 시 재발급 필요 (일반개인: 24시간)
- 해시키는 보안 강화를 위해 사용 권장 (주문/정정/취소 API)
- 토큰 값은 절대 노출되지 않도록 주의
- Rate Limit 주의하여 과도한 호출 방지
