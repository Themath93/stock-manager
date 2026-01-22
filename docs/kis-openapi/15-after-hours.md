# 시간외 시장 (After-hours)

## 개요

시간외 시장 (After-hours) 관련 API입니다.

## API 목록


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

def call_15_after_hours(access_token, appkey, appsecret, **params):
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
result = call_15_after_hours(
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

def call_15_after_hours(access_token, appkey, appsecret, **params):
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
result = call_15_after_hours(
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

def call_15_after_hours(access_token, appkey, appsecret, **params):
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
result = call_15_after_hours(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 시간외호가

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 시간외호가 |
| **API ID** | 국내주식-077 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/inquire-overtime-asking-price |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 시간외호가 API입니다.

**Python 코드 예시:**
```python
import requests

def call_15_after_hours(access_token, appkey, appsecret, **params):
    """
    국내주식 시간외호가 API 호출
    
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
result = call_15_after_hours(
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

def call_15_after_hours(access_token, appkey, appsecret, **params):
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
result = call_15_after_hours(
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

def call_15_after_hours(access_token, appkey, appsecret, **params):
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
result = call_15_after_hours(
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

def call_15_after_hours(access_token, appkey, appsecret, **params):
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
result = call_15_after_hours(
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

def call_15_after_hours(access_token, appkey, appsecret, **params):
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
result = call_15_after_hours(
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

def call_15_after_hours(access_token, appkey, appsecret, **params):
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
result = call_15_after_hours(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 시간외 실시간호가 (KRX)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 시간외 실시간호가 (KRX) |
| **API ID** | 실시간-025 |
| **HTTP Method** | POST |
| **URL** | /tryitout/H0STOAA0 |
| **Domain (실전)** | ws://ops.koreainvestment.com:21000 |

**설명:**
국내주식 시간외 실시간호가 (KRX) API입니다.

**Python 코드 예시:**
```python
import requests

def call_15_after_hours(access_token, appkey, appsecret, **params):
    """
    국내주식 시간외 실시간호가 (KRX) API 호출
    
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
result = call_15_after_hours(
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

def call_15_after_hours(access_token, appkey, appsecret, **params):
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
result = call_15_after_hours(
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
