# 시세 (Market Data)

## 개요

시세 (Market Data) 관련 API입니다.

## API 목록


### 주식현재가 일자별

| 항목 | 내용 |
|--------|--------|
| **API 명** | 주식현재가 일자별 |
| **API ID** | v1_국내주식-010 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/inquire-daily-price |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
주식현재가 일자별 API입니다.

**Python 코드 예시:**
```python
import requests

def call_05_market_data(access_token, appkey, appsecret, **params):
    """
    주식현재가 일자별 API 호출
    
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
result = call_05_market_data(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 주식현재가 시세

| 항목 | 내용 |
|--------|--------|
| **API 명** | 주식현재가 시세 |
| **API ID** | v1_국내주식-008 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/inquire-price |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
주식현재가 시세 API입니다.

**Python 코드 예시:**
```python
import requests

def call_05_market_data(access_token, appkey, appsecret, **params):
    """
    주식현재가 시세 API 호출
    
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
result = call_05_market_data(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 시간외현재가

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 시간외현재가 |
| **API ID** | 국내주식-076 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/inquire-overtime-price |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 시간외현재가 API입니다.

**Python 코드 예시:**
```python
import requests

def call_05_market_data(access_token, appkey, appsecret, **params):
    """
    국내주식 시간외현재가 API 호출
    
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
result = call_05_market_data(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### ETF 구성종목시세

| 항목 | 내용 |
|--------|--------|
| **API 명** | ETF 구성종목시세 |
| **API ID** | 국내주식-073 |
| **HTTP Method** | GET |
| **URL** | /uapi/etfetn/v1/quotations/inquire-component-stock-price |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
ETF 구성종목시세 API입니다.

**Python 코드 예시:**
```python
import requests

def call_05_market_data(access_token, appkey, appsecret, **params):
    """
    ETF 구성종목시세 API 호출
    
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
result = call_05_market_data(
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

def call_05_market_data(access_token, appkey, appsecret, **params):
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
result = call_05_market_data(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### NAV 비교추이(종목)

| 항목 | 내용 |
|--------|--------|
| **API 명** | NAV 비교추이(종목) |
| **API ID** | v1_국내주식-069 |
| **HTTP Method** | GET |
| **URL** | /uapi/etfetn/v1/quotations/nav-comparison-trend |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
NAV 비교추이(종목) API입니다.

**Python 코드 예시:**
```python
import requests

def call_05_market_data(access_token, appkey, appsecret, **params):
    """
    NAV 비교추이(종목) API 호출
    
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
result = call_05_market_data(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 주식현재가 시간외일자별주가

| 항목 | 내용 |
|--------|--------|
| **API 명** | 주식현재가 시간외일자별주가 |
| **API ID** | v1_국내주식-026 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/inquire-daily-overtimeprice |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
주식현재가 시간외일자별주가 API입니다.

**Python 코드 예시:**
```python
import requests

def call_05_market_data(access_token, appkey, appsecret, **params):
    """
    주식현재가 시간외일자별주가 API 호출
    
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
result = call_05_market_data(
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

def call_05_market_data(access_token, appkey, appsecret, **params):
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
result = call_05_market_data(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 주식현재가 시세2

| 항목 | 내용 |
|--------|--------|
| **API 명** | 주식현재가 시세2 |
| **API ID** | v1_국내주식-054 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/inquire-price-2 |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
주식현재가 시세2 API입니다.

**Python 코드 예시:**
```python
import requests

def call_05_market_data(access_token, appkey, appsecret, **params):
    """
    주식현재가 시세2 API 호출
    
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
result = call_05_market_data(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 주식일별분봉조회

| 항목 | 내용 |
|--------|--------|
| **API 명** | 주식일별분봉조회 |
| **API ID** | 국내주식-213 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
주식일별분봉조회 API입니다.

**Python 코드 예시:**
```python
import requests

def call_05_market_data(access_token, appkey, appsecret, **params):
    """
    주식일별분봉조회 API 호출
    
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
result = call_05_market_data(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식기간별시세(일/주/월/년)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식기간별시세(일/주/월/년) |
| **API ID** | v1_국내주식-016 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식기간별시세(일/주/월/년) API입니다.

**Python 코드 예시:**
```python
import requests

def call_05_market_data(access_token, appkey, appsecret, **params):
    """
    국내주식기간별시세(일/주/월/년) API 호출
    
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
result = call_05_market_data(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### NAV 비교추이(일)

| 항목 | 내용 |
|--------|--------|
| **API 명** | NAV 비교추이(일) |
| **API ID** | v1_국내주식-071 |
| **HTTP Method** | GET |
| **URL** | /uapi/etfetn/v1/quotations/nav-comparison-daily-trend |
| **Domain (실전)** |  |

**설명:**
NAV 비교추이(일) API입니다.

**Python 코드 예시:**
```python
import requests

def call_05_market_data(access_token, appkey, appsecret, **params):
    """
    NAV 비교추이(일) API 호출
    
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
result = call_05_market_data(
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

def call_05_market_data(access_token, appkey, appsecret, **params):
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
result = call_05_market_data(
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

def call_05_market_data(access_token, appkey, appsecret, **params):
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
result = call_05_market_data(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 주식현재가 회원사

| 항목 | 내용 |
|--------|--------|
| **API 명** | 주식현재가 회원사 |
| **API ID** | v1_국내주식-013 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/inquire-member |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
주식현재가 회원사 API입니다.

**Python 코드 예시:**
```python
import requests

def call_05_market_data(access_token, appkey, appsecret, **params):
    """
    주식현재가 회원사 API 호출
    
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
result = call_05_market_data(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### NAV 비교추이(분)

| 항목 | 내용 |
|--------|--------|
| **API 명** | NAV 비교추이(분) |
| **API ID** | v1_국내주식-070 |
| **HTTP Method** | GET |
| **URL** | /uapi/etfetn/v1/quotations/nav-comparison-time-trend |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
NAV 비교추이(분) API입니다.

**Python 코드 예시:**
```python
import requests

def call_05_market_data(access_token, appkey, appsecret, **params):
    """
    NAV 비교추이(분) API 호출
    
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
result = call_05_market_data(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 주식현재가 투자자

| 항목 | 내용 |
|--------|--------|
| **API 명** | 주식현재가 투자자 |
| **API ID** | v1_국내주식-012 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/inquire-investor |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
주식현재가 투자자 API입니다.

**Python 코드 예시:**
```python
import requests

def call_05_market_data(access_token, appkey, appsecret, **params):
    """
    주식현재가 투자자 API 호출
    
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
result = call_05_market_data(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### ETF/ETN 현재가

| 항목 | 내용 |
|--------|--------|
| **API 명** | ETF/ETN 현재가 |
| **API ID** | v1_국내주식-068 |
| **HTTP Method** | GET |
| **URL** | /uapi/etfetn/v1/quotations/inquire-price |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
ETF/ETN 현재가 API입니다.

**Python 코드 예시:**
```python
import requests

def call_05_market_data(access_token, appkey, appsecret, **params):
    """
    ETF/ETN 현재가 API 호출
    
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
result = call_05_market_data(
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

def call_05_market_data(access_token, appkey, appsecret, **params):
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
result = call_05_market_data(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 주식당일분봉조회

| 항목 | 내용 |
|--------|--------|
| **API 명** | 주식당일분봉조회 |
| **API ID** | v1_국내주식-022 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
주식당일분봉조회 API입니다.

**Python 코드 예시:**
```python
import requests

def call_05_market_data(access_token, appkey, appsecret, **params):
    """
    주식당일분봉조회 API 호출
    
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
result = call_05_market_data(
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

def call_05_market_data(access_token, appkey, appsecret, **params):
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
result = call_05_market_data(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식업종기간별시세(일/주/월/년)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식업종기간별시세(일/주/월/년) |
| **API ID** | v1_국내주식-021 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/inquire-daily-indexchartprice |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식업종기간별시세(일/주/월/년) API입니다.

**Python 코드 예시:**
```python
import requests

def call_05_market_data(access_token, appkey, appsecret, **params):
    """
    국내주식업종기간별시세(일/주/월/년) API 호출
    
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
result = call_05_market_data(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내업종 구분별전체시세

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내업종 구분별전체시세 |
| **API ID** | v1_국내주식-066 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/inquire-index-category-price |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내업종 구분별전체시세 API입니다.

**Python 코드 예시:**
```python
import requests

def call_05_market_data(access_token, appkey, appsecret, **params):
    """
    국내업종 구분별전체시세 API 호출
    
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
result = call_05_market_data(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 업종 분봉조회

| 항목 | 내용 |
|--------|--------|
| **API 명** | 업종 분봉조회 |
| **API ID** | v1_국내주식-045 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/inquire-time-indexchartprice |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
업종 분봉조회 API입니다.

**Python 코드 예시:**
```python
import requests

def call_05_market_data(access_token, appkey, appsecret, **params):
    """
    업종 분봉조회 API 호출
    
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
result = call_05_market_data(
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

def call_05_market_data(access_token, appkey, appsecret, **params):
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
result = call_05_market_data(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 주식현재가 회원사 종목매매동향

| 항목 | 내용 |
|--------|--------|
| **API 명** | 주식현재가 회원사 종목매매동향 |
| **API ID** | 국내주식-197 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/inquire-member-daily |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
주식현재가 회원사 종목매매동향 API입니다.

**Python 코드 예시:**
```python
import requests

def call_05_market_data(access_token, appkey, appsecret, **params):
    """
    주식현재가 회원사 종목매매동향 API 호출
    
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
result = call_05_market_data(
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

def call_05_market_data(access_token, appkey, appsecret, **params):
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
result = call_05_market_data(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 시장별 투자자매매동향(시세)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 시장별 투자자매매동향(시세) |
| **API ID** | v1_국내주식-074 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/inquire-investor-time-by-market |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
시장별 투자자매매동향(시세) API입니다.

**Python 코드 예시:**
```python
import requests

def call_05_market_data(access_token, appkey, appsecret, **params):
    """
    시장별 투자자매매동향(시세) API 호출
    
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
result = call_05_market_data(
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

def call_05_market_data(access_token, appkey, appsecret, **params):
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
result = call_05_market_data(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 관심종목(멀티종목) 시세조회

| 항목 | 내용 |
|--------|--------|
| **API 명** | 관심종목(멀티종목) 시세조회 |
| **API ID** | 국내주식-205 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/intstock-multprice |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
관심종목(멀티종목) 시세조회 API입니다.

**Python 코드 예시:**
```python
import requests

def call_05_market_data(access_token, appkey, appsecret, **params):
    """
    관심종목(멀티종목) 시세조회 API 호출
    
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
result = call_05_market_data(
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

def call_05_market_data(access_token, appkey, appsecret, **params):
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
result = call_05_market_data(
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

def call_05_market_data(access_token, appkey, appsecret, **params):
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
result = call_05_market_data(
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

def call_05_market_data(access_token, appkey, appsecret, **params):
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
result = call_05_market_data(
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

def call_05_market_data(access_token, appkey, appsecret, **params):
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
result = call_05_market_data(
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

def call_05_market_data(access_token, appkey, appsecret, **params):
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
result = call_05_market_data(
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

def call_05_market_data(access_token, appkey, appsecret, **params):
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
result = call_05_market_data(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내ETF NAV추이

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내ETF NAV추이 |
| **API ID** | 실시간-051 |
| **HTTP Method** | POST |
| **URL** | /tryitout/H0STNAV0 |
| **Domain (실전)** | ws://ops.koreainvestment.com:21000 |

**설명:**
국내ETF NAV추이 API입니다.

**Python 코드 예시:**
```python
import requests

def call_05_market_data(access_token, appkey, appsecret, **params):
    """
    국내ETF NAV추이 API 호출
    
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
result = call_05_market_data(
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
