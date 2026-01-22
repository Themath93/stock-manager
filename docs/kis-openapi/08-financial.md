# 재무정보 (Financial)

## 개요

재무정보 (Financial) 관련 API입니다.

## API 목록


### 기간별매매손익현황조회

| 항목 | 내용 |
|--------|--------|
| **API 명** | 기간별매매손익현황조회 |
| **API ID** | v1_국내주식-060 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/trading/inquire-period-trade-profit |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
기간별매매손익현황조회 API입니다.

**Python 코드 예시:**
```python
import requests

def call_08_financial(access_token, appkey, appsecret, **params):
    """
    기간별매매손익현황조회 API 호출
    
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
result = call_08_financial(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 기간별손익일별합산조회

| 항목 | 내용 |
|--------|--------|
| **API 명** | 기간별손익일별합산조회 |
| **API ID** | v1_국내주식-052 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/trading/inquire-period-profit |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
기간별손익일별합산조회 API입니다.

**Python 코드 예시:**
```python
import requests

def call_08_financial(access_token, appkey, appsecret, **params):
    """
    기간별손익일별합산조회 API 호출
    
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
result = call_08_financial(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 주식잔고조회_실현손익

| 항목 | 내용 |
|--------|--------|
| **API 명** | 주식잔고조회_실현손익 |
| **API ID** | v1_국내주식-041 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/trading/inquire-balance-rlz-pl |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
주식잔고조회_실현손익 API입니다.

**Python 코드 예시:**
```python
import requests

def call_08_financial(access_token, appkey, appsecret, **params):
    """
    주식잔고조회_실현손익 API 호출
    
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
result = call_08_financial(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 재무비율

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 재무비율 |
| **API ID** | v1_국내주식-080 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/finance/financial-ratio |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 재무비율 API입니다.

**Python 코드 예시:**
```python
import requests

def call_08_financial(access_token, appkey, appsecret, **params):
    """
    국내주식 재무비율 API 호출
    
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
result = call_08_financial(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 안정성비율

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 안정성비율 |
| **API ID** | v1_국내주식-083 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/finance/stability-ratio |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 안정성비율 API입니다.

**Python 코드 예시:**
```python
import requests

def call_08_financial(access_token, appkey, appsecret, **params):
    """
    국내주식 안정성비율 API 호출
    
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
result = call_08_financial(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 수익성비율

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 수익성비율 |
| **API ID** | v1_국내주식-081 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/finance/profit-ratio |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 수익성비율 API입니다.

**Python 코드 예시:**
```python
import requests

def call_08_financial(access_token, appkey, appsecret, **params):
    """
    국내주식 수익성비율 API 호출
    
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
result = call_08_financial(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 손익계산서

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 손익계산서 |
| **API ID** | v1_국내주식-079 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/finance/income-statement |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 손익계산서 API입니다.

**Python 코드 예시:**
```python
import requests

def call_08_financial(access_token, appkey, appsecret, **params):
    """
    국내주식 손익계산서 API 호출
    
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
result = call_08_financial(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 성장성비율

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 성장성비율 |
| **API ID** | v1_국내주식-085 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/finance/growth-ratio |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 성장성비율 API입니다.

**Python 코드 예시:**
```python
import requests

def call_08_financial(access_token, appkey, appsecret, **params):
    """
    국내주식 성장성비율 API 호출
    
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
result = call_08_financial(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 대차대조표

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 대차대조표 |
| **API ID** | v1_국내주식-078 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/finance/balance-sheet |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 대차대조표 API입니다.

**Python 코드 예시:**
```python
import requests

def call_08_financial(access_token, appkey, appsecret, **params):
    """
    국내주식 대차대조표 API 호출
    
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
result = call_08_financial(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 재무비율 순위

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 재무비율 순위 |
| **API ID** | v1_국내주식-092 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ranking/finance-ratio |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 재무비율 순위 API입니다.

**Python 코드 예시:**
```python
import requests

def call_08_financial(access_token, appkey, appsecret, **params):
    """
    국내주식 재무비율 순위 API 호출
    
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
result = call_08_financial(
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
