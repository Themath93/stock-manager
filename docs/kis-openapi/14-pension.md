# 퇴직연금 (Pension)

## 개요

퇴직연금 (Pension) 관련 API입니다.

## API 목록


### 퇴직연금 예수금조회

| 항목 | 내용 |
|--------|--------|
| **API 명** | 퇴직연금 예수금조회 |
| **API ID** | v1_국내주식-035 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/trading/pension/inquire-deposit |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
퇴직연금 예수금조회 API입니다.

**Python 코드 예시:**
```python
import requests

def call_14_pension(access_token, appkey, appsecret, **params):
    """
    퇴직연금 예수금조회 API 호출
    
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
result = call_14_pension(
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

def call_14_pension(access_token, appkey, appsecret, **params):
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
result = call_14_pension(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 퇴직연금 매수가능조회

| 항목 | 내용 |
|--------|--------|
| **API 명** | 퇴직연금 매수가능조회 |
| **API ID** | v1_국내주식-034 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/trading/pension/inquire-psbl-order |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
퇴직연금 매수가능조회 API입니다.

**Python 코드 예시:**
```python
import requests

def call_14_pension(access_token, appkey, appsecret, **params):
    """
    퇴직연금 매수가능조회 API 호출
    
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
result = call_14_pension(
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

def call_14_pension(access_token, appkey, appsecret, **params):
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
result = call_14_pension(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 퇴직연금 잔고조회

| 항목 | 내용 |
|--------|--------|
| **API 명** | 퇴직연금 잔고조회 |
| **API ID** | v1_국내주식-036 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/trading/pension/inquire-balance |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
퇴직연금 잔고조회 API입니다.

**Python 코드 예시:**
```python
import requests

def call_14_pension(access_token, appkey, appsecret, **params):
    """
    퇴직연금 잔고조회 API 호출
    
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
result = call_14_pension(
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
