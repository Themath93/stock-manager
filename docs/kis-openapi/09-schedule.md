# 일정 (Schedule)

## 개요

일정 (Schedule) 관련 API입니다.

## API 목록


### 예탁원정보(상장정보일정)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 예탁원정보(상장정보일정) |
| **API ID** | 국내주식-150 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ksdinfo/list-info |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
예탁원정보(상장정보일정) API입니다.

**Python 코드 예시:**
```python
import requests

def call_09_schedule(access_token, appkey, appsecret, **params):
    """
    예탁원정보(상장정보일정) API 호출
    
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
result = call_09_schedule(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 예탁원정보(공모주청약일정)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 예탁원정보(공모주청약일정) |
| **API ID** | 국내주식-151 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ksdinfo/pub-offer |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
예탁원정보(공모주청약일정) API입니다.

**Python 코드 예시:**
```python
import requests

def call_09_schedule(access_token, appkey, appsecret, **params):
    """
    예탁원정보(공모주청약일정) API 호출
    
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
result = call_09_schedule(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 예탁원정보(자본감소일정)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 예탁원정보(자본감소일정) |
| **API ID** | 국내주식-149 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ksdinfo/cap-dcrs |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
예탁원정보(자본감소일정) API입니다.

**Python 코드 예시:**
```python
import requests

def call_09_schedule(access_token, appkey, appsecret, **params):
    """
    예탁원정보(자본감소일정) API 호출
    
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
result = call_09_schedule(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 예탁원정보(무상증자일정)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 예탁원정보(무상증자일정) |
| **API ID** | 국내주식-144 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ksdinfo/bonus-issue |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
예탁원정보(무상증자일정) API입니다.

**Python 코드 예시:**
```python
import requests

def call_09_schedule(access_token, appkey, appsecret, **params):
    """
    예탁원정보(무상증자일정) API 호출
    
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
result = call_09_schedule(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 예탁원정보(배당일정)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 예탁원정보(배당일정) |
| **API ID** | 국내주식-145 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ksdinfo/dividend |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
예탁원정보(배당일정) API입니다.

**Python 코드 예시:**
```python
import requests

def call_09_schedule(access_token, appkey, appsecret, **params):
    """
    예탁원정보(배당일정) API 호출
    
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
result = call_09_schedule(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 예탁원정보(주주총회일정)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 예탁원정보(주주총회일정) |
| **API ID** | 국내주식-154 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ksdinfo/sharehld-meet |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
예탁원정보(주주총회일정) API입니다.

**Python 코드 예시:**
```python
import requests

def call_09_schedule(access_token, appkey, appsecret, **params):
    """
    예탁원정보(주주총회일정) API 호출
    
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
result = call_09_schedule(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 예탁원정보(합병/분할일정)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 예탁원정보(합병/분할일정) |
| **API ID** | 국내주식-147 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/ksdinfo/merger-split |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
예탁원정보(합병/분할일정) API입니다.

**Python 코드 예시:**
```python
import requests

def call_09_schedule(access_token, appkey, appsecret, **params):
    """
    예탁원정보(합병/분할일정) API 호출
    
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
result = call_09_schedule(
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

def call_09_schedule(access_token, appkey, appsecret, **params):
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
result = call_09_schedule(
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
