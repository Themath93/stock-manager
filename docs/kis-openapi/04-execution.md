# 체결/미체결 (Execution)

## 개요

체결/미체결 (Execution) 관련 API입니다.

## API 목록


### 주식예약주문정정취소

| 항목 | 내용 |
|--------|--------|
| **API 명** | 주식예약주문정정취소 |
| **API ID** | v1_국내주식-018,019 |
| **HTTP Method** | POST |
| **URL** | /uapi/domestic-stock/v1/trading/order-resv-rvsecncl |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
주식예약주문정정취소 API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    주식예약주문정정취소 API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 퇴직연금 미체결내역

| 항목 | 내용 |
|--------|--------|
| **API 명** | 퇴직연금 미체결내역 |
| **API ID** | v1_국내주식-033 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/trading/pension/inquire-daily-ccld |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
퇴직연금 미체결내역 API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    퇴직연금 미체결내역 API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 주식주문(정정취소)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 주식주문(정정취소) |
| **API ID** | v1_국내주식-003 |
| **HTTP Method** | POST |
| **URL** | /uapi/domestic-stock/v1/trading/order-rvsecncl |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
주식주문(정정취소) API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    주식주문(정정취소) API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 퇴직연금 체결기준잔고

| 항목 | 내용 |
|--------|--------|
| **API 명** | 퇴직연금 체결기준잔고 |
| **API ID** | v1_국내주식-032 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/trading/pension/inquire-present-balance |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
퇴직연금 체결기준잔고 API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    퇴직연금 체결기준잔고 API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 주식일별주문체결조회

| 항목 | 내용 |
|--------|--------|
| **API 명** | 주식일별주문체결조회 |
| **API ID** | v1_국내주식-005 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/trading/inquire-daily-ccld |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
주식일별주문체결조회 API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    주식일별주문체결조회 API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 주식정정취소가능주문조회

| 항목 | 내용 |
|--------|--------|
| **API 명** | 주식정정취소가능주문조회 |
| **API ID** | v1_국내주식-004 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
주식정정취소가능주문조회 API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    주식정정취소가능주문조회 API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 주식현재가 시간외시간별체결

| 항목 | 내용 |
|--------|--------|
| **API 명** | 주식현재가 시간외시간별체결 |
| **API ID** | v1_국내주식-025 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/inquire-time-overtimeconclusion |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
주식현재가 시간외시간별체결 API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    주식현재가 시간외시간별체결 API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 주식현재가 당일시간대별체결

| 항목 | 내용 |
|--------|--------|
| **API 명** | 주식현재가 당일시간대별체결 |
| **API ID** | v1_국내주식-023 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
주식현재가 당일시간대별체결 API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    주식현재가 당일시간대별체결 API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 주식현재가 호가/예상체결

| 항목 | 내용 |
|--------|--------|
| **API 명** | 주식현재가 호가/예상체결 |
| **API ID** | v1_국내주식-011 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
주식현재가 호가/예상체결 API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    주식현재가 호가/예상체결 API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 주식현재가 체결

| 항목 | 내용 |
|--------|--------|
| **API 명** | 주식현재가 체결 |
| **API ID** | v1_국내주식-009 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/inquire-ccnl |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
주식현재가 체결 API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    주식현재가 체결 API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 장마감 예상체결가

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 장마감 예상체결가 |
| **API ID** | 국내주식-120 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/exp-closing-price |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 장마감 예상체결가 API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    국내주식 장마감 예상체결가 API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 예상체결지수 추이

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 예상체결지수 추이 |
| **API ID** | 국내주식-121 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/exp-index-trend |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 예상체결지수 추이 API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    국내주식 예상체결지수 추이 API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 예상체결 전체지수

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 예상체결 전체지수 |
| **API ID** | 국내주식-122 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/exp-total-index |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 예상체결 전체지수 API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    국내주식 예상체결 전체지수 API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 종목별일별매수매도체결량

| 항목 | 내용 |
|--------|--------|
| **API 명** | 종목별일별매수매도체결량 |
| **API ID** | v1_국내주식-056 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/inquire-daily-trade-volume |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
종목별일별매수매도체결량 API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    종목별일별매수매도체결량 API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 체결금액별 매매비중

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 체결금액별 매매비중 |
| **API ID** | 국내주식-192 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/tradprt-byamt |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 체결금액별 매매비중 API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    국내주식 체결금액별 매매비중 API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 예상체결가 추이

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 예상체결가 추이 |
| **API ID** | 국내주식-118 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/exp-price-trend |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 예상체결가 추이 API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    국내주식 예상체결가 추이 API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 종목별 프로그램매매추이(체결)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 종목별 프로그램매매추이(체결) |
| **API ID** | v1_국내주식-044 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/program-trade-by-stock |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
종목별 프로그램매매추이(체결) API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    종목별 프로그램매매추이(체결) API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 시간외예상체결등락률

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 시간외예상체결등락률 |
| **API ID** | 국내주식-140 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ranking/overtime-exp-trans-fluct |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 시간외예상체결등락률 API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    국내주식 시간외예상체결등락률 API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 예상체결 상승/하락상위

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 예상체결 상승/하락상위 |
| **API ID** | v1_국내주식-103 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ranking/exp-trans-updown |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 예상체결 상승/하락상위 API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    국내주식 예상체결 상승/하락상위 API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 대량체결건수 상위

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 대량체결건수 상위 |
| **API ID** | 국내주식-107 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ranking/bulk-trans-num |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 대량체결건수 상위 API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    국내주식 대량체결건수 상위 API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 체결강도 상위

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 체결강도 상위 |
| **API ID** | v1_국내주식-101 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ranking/volume-power |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 체결강도 상위 API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    국내주식 체결강도 상위 API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내지수 실시간예상체결

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내지수 실시간예상체결 |
| **API ID** | 실시간-027 |
| **HTTP Method** | POST |
| **URL** | /tryitout/H0UPANC0 |
| **Domain (실전)** | ws://ops.koreainvestment.com:21000 |

**설명:**
국내지수 실시간예상체결 API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    국내지수 실시간예상체결 API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 실시간체결통보

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 실시간체결통보 |
| **API ID** | 실시간-005 |
| **HTTP Method** | POST |
| **URL** | /tryitout/H0STCNI0 |
| **Domain (실전)** | ws://ops.koreainvestment.com:21000 |

**설명:**
국내주식 실시간체결통보 API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    국내주식 실시간체결통보 API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 시간외 실시간예상체결 (KRX)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 시간외 실시간예상체결 (KRX) |
| **API ID** | 실시간-024 |
| **HTTP Method** | POST |
| **URL** | /tryitout/H0STOAC0 |
| **Domain (실전)** | ws://ops.koreainvestment.com:21000 |

**설명:**
국내주식 시간외 실시간예상체결 (KRX) API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    국내주식 시간외 실시간예상체결 (KRX) API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 실시간체결가 (KRX)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 실시간체결가 (KRX) |
| **API ID** | 실시간-003 |
| **HTTP Method** | POST |
| **URL** | /tryitout/H0STCNT0 |
| **Domain (실전)** | ws://ops.koreainvestment.com:21000 |

**설명:**
국내주식 실시간체결가 (KRX) API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    국내주식 실시간체결가 (KRX) API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내지수 실시간체결

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내지수 실시간체결 |
| **API ID** | 실시간-026 |
| **HTTP Method** | POST |
| **URL** | /tryitout/H0UPCNT0 |
| **Domain (실전)** | ws://ops.koreainvestment.com:21000 |

**설명:**
국내지수 실시간체결 API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    국내지수 실시간체결 API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 실시간예상체결 (KRX)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 실시간예상체결 (KRX) |
| **API ID** | 실시간-041 |
| **HTTP Method** | POST |
| **URL** | /tryitout/H0STANC0 |
| **Domain (실전)** | ws://ops.koreainvestment.com:21000 |

**설명:**
국내주식 실시간예상체결 (KRX) API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    국내주식 실시간예상체결 (KRX) API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 실시간체결가 (통합)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 실시간체결가 (통합) |
| **API ID** | 국내주식 실시간체결가 (통합) |
| **HTTP Method** | POST |
| **URL** | /tryitout/H0UNCNT0 |
| **Domain (실전)** | ws://ops.koreainvestment.com:21000 |

**설명:**
국내주식 실시간체결가 (통합) API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    국내주식 실시간체결가 (통합) API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 실시간체결가 (NXT)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 실시간체결가 (NXT) |
| **API ID** | 국내주식 실시간체결가 (NXT) |
| **HTTP Method** | POST |
| **URL** | /tryitout/H0NXCNT0 |
| **Domain (실전)** | ws://ops.koreainvestment.com:21000 |

**설명:**
국내주식 실시간체결가 (NXT) API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    국내주식 실시간체결가 (NXT) API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 실시간예상체결 (NXT)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 실시간예상체결 (NXT) |
| **API ID** | 국내주식 실시간예상체결 (NXT) |
| **HTTP Method** | POST |
| **URL** | /tryitout/H0NXANC0 |
| **Domain (실전)** | ws://ops.koreainvestment.com:21000 |

**설명:**
국내주식 실시간예상체결 (NXT) API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    국내주식 실시간예상체결 (NXT) API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 실시간예상체결 (통합)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 실시간예상체결 (통합) |
| **API ID** | 국내주식 실시간예상체결 (통합) |
| **HTTP Method** | POST |
| **URL** | /tryitout/H0UNANC0 |
| **Domain (실전)** | ws://ops.koreainvestment.com:21000 |

**설명:**
국내주식 실시간예상체결 (통합) API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    국내주식 실시간예상체결 (통합) API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 시간외 실시간체결가 (KRX)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 시간외 실시간체결가 (KRX) |
| **API ID** | 실시간-042 |
| **HTTP Method** | POST |
| **URL** | /tryitout/H0STOUP0 |
| **Domain (실전)** | ws://ops.koreainvestment.com:21000 |

**설명:**
국내주식 시간외 실시간체결가 (KRX) API입니다.

**Python 코드 예시:**
```python
import requests

def call_04_execution(access_token, appkey, appsecret, **params):
    """
    국내주식 시간외 실시간체결가 (KRX) API 호출
    
    Args:
        access_token: 접근 토큰
        appkey: 앱키
        appsecret: 앱시크릿키
        **params: 추가 파라미터
    
    Returns:
        dict: API 응답
    """
    url = f"{api['domain']}{api['url']}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")

# 사용 예시
result = call_04_execution(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


## 주의사항

- API 호출 전 반드시 필요한 파라미터 확인
- Rate Limit 주의
- 에러 발생 시 적절한 오류 처리 필요
