# 관심종목 (Watchlist)

## 개요

관심종목 (Watchlist) 관련 API입니다.

## API 목록


### 관심종목 그룹별 종목조회

| 항목 | 내용 |
|--------|--------|
| **API 명** | 관심종목 그룹별 종목조회 |
| **API ID** | 국내주식-203 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/intstock-stocklist-by-group |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
관심종목 그룹별 종목조회 API입니다.

**Python 코드 예시:**
```python
import requests

def call_12_watchlist(access_token, appkey, appsecret, **params):
    """
    관심종목 그룹별 종목조회 API 호출
    
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
result = call_12_watchlist(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 관심종목 그룹조회

| 항목 | 내용 |
|--------|--------|
| **API 명** | 관심종목 그룹조회 |
| **API ID** | 국내주식-204 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/intstock-grouplist |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
관심종목 그룹조회 API입니다.

**Python 코드 예시:**
```python
import requests

def call_12_watchlist(access_token, appkey, appsecret, **params):
    """
    관심종목 그룹조회 API 호출
    
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
result = call_12_watchlist(
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

def call_12_watchlist(access_token, appkey, appsecret, **params):
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
result = call_12_watchlist(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 관심종목등록 상위

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 관심종목등록 상위 |
| **API ID** | v1_국내주식-102 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ranking/top-interest-stock |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 관심종목등록 상위 API입니다.

**Python 코드 예시:**
```python
import requests

def call_12_watchlist(access_token, appkey, appsecret, **params):
    """
    국내주식 관심종목등록 상위 API 호출
    
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
result = call_12_watchlist(
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
