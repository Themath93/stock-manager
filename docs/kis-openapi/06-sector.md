# 업종 (Sector)

## 개요

업종 (Sector) 관련 API입니다.

## API 목록


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

def call_06_sector(access_token, appkey, appsecret, **params):
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
result = call_06_sector(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내업종 시간별지수(분)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내업종 시간별지수(분) |
| **API ID** | 국내주식-119 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/inquire-index-timeprice |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내업종 시간별지수(분) API입니다.

**Python 코드 예시:**
```python
import requests

def call_06_sector(access_token, appkey, appsecret, **params):
    """
    국내업종 시간별지수(분) API 호출
    
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
result = call_06_sector(
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

def call_06_sector(access_token, appkey, appsecret, **params):
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
result = call_06_sector(
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

def call_06_sector(access_token, appkey, appsecret, **params):
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
result = call_06_sector(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내업종 현재지수

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내업종 현재지수 |
| **API ID** | v1_국내주식-063 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/inquire-index-price |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내업종 현재지수 API입니다.

**Python 코드 예시:**
```python
import requests

def call_06_sector(access_token, appkey, appsecret, **params):
    """
    국내업종 현재지수 API 호출
    
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
result = call_06_sector(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내업종 시간별지수(초)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내업종 시간별지수(초) |
| **API ID** | 국내주식-064 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/inquire-index-tickprice |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내업종 시간별지수(초) API입니다.

**Python 코드 예시:**
```python
import requests

def call_06_sector(access_token, appkey, appsecret, **params):
    """
    국내업종 시간별지수(초) API 호출
    
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
result = call_06_sector(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내업종 일자별지수

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내업종 일자별지수 |
| **API ID** | v1_국내주식-065 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/inquire-index-daily-price |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내업종 일자별지수 API입니다.

**Python 코드 예시:**
```python
import requests

def call_06_sector(access_token, appkey, appsecret, **params):
    """
    국내업종 일자별지수 API 호출
    
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
result = call_06_sector(
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
