# 랭킹 (Ranking)

## 개요

랭킹 (Ranking) 관련 API입니다.

## API 목록


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

def call_10_ranking(access_token, appkey, appsecret, **params):
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
result = call_10_ranking(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 호가잔량 순위

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 호가잔량 순위 |
| **API ID** | 국내주식-089 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ranking/quote-balance |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 호가잔량 순위 API입니다.

**Python 코드 예시:**
```python
import requests

def call_10_ranking(access_token, appkey, appsecret, **params):
    """
    국내주식 호가잔량 순위 API 호출
    
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
result = call_10_ranking(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 신용잔고 상위

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 신용잔고 상위 |
| **API ID** | 국내주식-109 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ranking/credit-balance |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 신용잔고 상위 API입니다.

**Python 코드 예시:**
```python
import requests

def call_10_ranking(access_token, appkey, appsecret, **params):
    """
    국내주식 신용잔고 상위 API 호출
    
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
result = call_10_ranking(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 시간외거래량순위

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 시간외거래량순위 |
| **API ID** | 국내주식-139 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ranking/overtime-volume |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 시간외거래량순위 API입니다.

**Python 코드 예시:**
```python
import requests

def call_10_ranking(access_token, appkey, appsecret, **params):
    """
    국내주식 시간외거래량순위 API 호출
    
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
result = call_10_ranking(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 배당률 상위

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 배당률 상위 |
| **API ID** | 국내주식-106 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ranking/dividend-rate |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 배당률 상위 API입니다.

**Python 코드 예시:**
```python
import requests

def call_10_ranking(access_token, appkey, appsecret, **params):
    """
    국내주식 배당률 상위 API 호출
    
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
result = call_10_ranking(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 시간외잔량 순위

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 시간외잔량 순위 |
| **API ID** | v1_국내주식-093 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ranking/after-hour-balance |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 시간외잔량 순위 API입니다.

**Python 코드 예시:**
```python
import requests

def call_10_ranking(access_token, appkey, appsecret, **params):
    """
    국내주식 시간외잔량 순위 API 호출
    
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
result = call_10_ranking(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 공매도 상위종목

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 공매도 상위종목 |
| **API ID** | 국내주식-133 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ranking/short-sale |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 공매도 상위종목 API입니다.

**Python 코드 예시:**
```python
import requests

def call_10_ranking(access_token, appkey, appsecret, **params):
    """
    국내주식 공매도 상위종목 API 호출
    
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
result = call_10_ranking(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 이격도 순위

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 이격도 순위 |
| **API ID** | v1_국내주식-095 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ranking/disparity |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 이격도 순위 API입니다.

**Python 코드 예시:**
```python
import requests

def call_10_ranking(access_token, appkey, appsecret, **params):
    """
    국내주식 이격도 순위 API 호출
    
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
result = call_10_ranking(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### HTS조회상위20종목

| 항목 | 내용 |
|--------|--------|
| **API 명** | HTS조회상위20종목 |
| **API ID** | 국내주식-214 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ranking/hts-top-view |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
HTS조회상위20종목 API입니다.

**Python 코드 예시:**
```python
import requests

def call_10_ranking(access_token, appkey, appsecret, **params):
    """
    HTS조회상위20종목 API 호출
    
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
result = call_10_ranking(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 거래량순위

| 항목 | 내용 |
|--------|--------|
| **API 명** | 거래량순위 |
| **API ID** | v1_국내주식-047 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/volume-rank |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
거래량순위 API입니다.

**Python 코드 예시:**
```python
import requests

def call_10_ranking(access_token, appkey, appsecret, **params):
    """
    거래량순위 API 호출
    
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
result = call_10_ranking(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 수익자산지표 순위

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 수익자산지표 순위 |
| **API ID** | v1_국내주식-090 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ranking/profit-asset-index |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 수익자산지표 순위 API입니다.

**Python 코드 예시:**
```python
import requests

def call_10_ranking(access_token, appkey, appsecret, **params):
    """
    국내주식 수익자산지표 순위 API 호출
    
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
result = call_10_ranking(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 신고/신저근접종목 상위

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 신고/신저근접종목 상위 |
| **API ID** | v1_국내주식-105 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ranking/near-new-highlow |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 신고/신저근접종목 상위 API입니다.

**Python 코드 예시:**
```python
import requests

def call_10_ranking(access_token, appkey, appsecret, **params):
    """
    국내주식 신고/신저근접종목 상위 API 호출
    
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
result = call_10_ranking(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 우선주/괴리율 상위

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 우선주/괴리율 상위 |
| **API ID** | v1_국내주식-094 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ranking/prefer-disparate-ratio |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 우선주/괴리율 상위 API입니다.

**Python 코드 예시:**
```python
import requests

def call_10_ranking(access_token, appkey, appsecret, **params):
    """
    국내주식 우선주/괴리율 상위 API 호출
    
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
result = call_10_ranking(
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

def call_10_ranking(access_token, appkey, appsecret, **params):
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
result = call_10_ranking(
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

def call_10_ranking(access_token, appkey, appsecret, **params):
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
result = call_10_ranking(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 시가총액 상위

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 시가총액 상위 |
| **API ID** | v1_국내주식-091 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ranking/market-cap |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 시가총액 상위 API입니다.

**Python 코드 예시:**
```python
import requests

def call_10_ranking(access_token, appkey, appsecret, **params):
    """
    국내주식 시가총액 상위 API 호출
    
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
result = call_10_ranking(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 당사매매종목 상위

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 당사매매종목 상위 |
| **API ID** | v1_국내주식-104 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ranking/traded-by-company |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 당사매매종목 상위 API입니다.

**Python 코드 예시:**
```python
import requests

def call_10_ranking(access_token, appkey, appsecret, **params):
    """
    국내주식 당사매매종목 상위 API 호출
    
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
result = call_10_ranking(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 등락률 순위

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 등락률 순위 |
| **API ID** | v1_국내주식-088 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ranking/fluctuation |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 등락률 순위 API입니다.

**Python 코드 예시:**
```python
import requests

def call_10_ranking(access_token, appkey, appsecret, **params):
    """
    국내주식 등락률 순위 API 호출
    
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
result = call_10_ranking(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 시장가치 순위

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 시장가치 순위 |
| **API ID** | v1_국내주식-096 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ranking/market-value |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 시장가치 순위 API입니다.

**Python 코드 예시:**
```python
import requests

def call_10_ranking(access_token, appkey, appsecret, **params):
    """
    국내주식 시장가치 순위 API 호출
    
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
result = call_10_ranking(
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

def call_10_ranking(access_token, appkey, appsecret, **params):
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
result = call_10_ranking(
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

def call_10_ranking(access_token, appkey, appsecret, **params):
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
result = call_10_ranking(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 시간외등락율순위

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 시간외등락율순위 |
| **API ID** | 국내주식-138 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ranking/overtime-fluctuation |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 시간외등락율순위 API입니다.

**Python 코드 예시:**
```python
import requests

def call_10_ranking(access_token, appkey, appsecret, **params):
    """
    국내주식 시간외등락율순위 API 호출
    
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
result = call_10_ranking(
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
