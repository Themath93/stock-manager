# 실시간 데이터 (Real-time)

## 개요

실시간 데이터 (Real-time) 관련 API입니다.

## API 목록


### 실시간 (웹소켓) 접속키 발급

| 항목 | 내용 |
|--------|--------|
| **API 명** | 실시간 (웹소켓) 접속키 발급 |
| **API ID** | 실시간-000 |
| **HTTP Method** | POST |
| **URL** | /oauth2/Approval |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
실시간 (웹소켓) 접속키 발급 API입니다.

**Python 코드 예시:**
```python
import requests

def call_11_realtime(access_token, appkey, appsecret, **params):
    """
    실시간 (웹소켓) 접속키 발급 API 호출
    
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
result = call_11_realtime(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 회원사 실시간 매매동향(틱)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 회원사 실시간 매매동향(틱) |
| **API ID** | 국내주식-163 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/frgnmem-trade-trend |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
회원사 실시간 매매동향(틱) API입니다.

**Python 코드 예시:**
```python
import requests

def call_11_realtime(access_token, appkey, appsecret, **params):
    """
    회원사 실시간 매매동향(틱) API 호출
    
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
result = call_11_realtime(
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

def call_11_realtime(access_token, appkey, appsecret, **params):
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
result = call_11_realtime(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 실시간회원사 (NXT)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 실시간회원사 (NXT) |
| **API ID** | 국내주식 실시간회원사 (NXT) |
| **HTTP Method** | POST |
| **URL** | /tryitout/H0NXMBC0 |
| **Domain (실전)** | ws://ops.koreainvestment.com:21000 |

**설명:**
국내주식 실시간회원사 (NXT) API입니다.

**Python 코드 예시:**
```python
import requests

def call_11_realtime(access_token, appkey, appsecret, **params):
    """
    국내주식 실시간회원사 (NXT) API 호출
    
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
result = call_11_realtime(
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

def call_11_realtime(access_token, appkey, appsecret, **params):
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
result = call_11_realtime(
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

def call_11_realtime(access_token, appkey, appsecret, **params):
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
result = call_11_realtime(
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

def call_11_realtime(access_token, appkey, appsecret, **params):
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
result = call_11_realtime(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 실시간프로그램매매 (통합)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 실시간프로그램매매 (통합) |
| **API ID** | 국내주식 실시간프로그램매매 (통합) |
| **HTTP Method** | POST |
| **URL** | /tryitout/H0UNPGM0 |
| **Domain (실전)** | ws://ops.koreainvestment.com:21000 |

**설명:**
국내주식 실시간프로그램매매 (통합) API입니다.

**Python 코드 예시:**
```python
import requests

def call_11_realtime(access_token, appkey, appsecret, **params):
    """
    국내주식 실시간프로그램매매 (통합) API 호출
    
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
result = call_11_realtime(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 실시간호가 (통합)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 실시간호가 (통합) |
| **API ID** | 국내주식 실시간호가 (통합) |
| **HTTP Method** | POST |
| **URL** | /tryitout/H0UNASP0 |
| **Domain (실전)** | ws://ops.koreainvestment.com:21000 |

**설명:**
국내주식 실시간호가 (통합) API입니다.

**Python 코드 예시:**
```python
import requests

def call_11_realtime(access_token, appkey, appsecret, **params):
    """
    국내주식 실시간호가 (통합) API 호출
    
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
result = call_11_realtime(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 실시간프로그램매매 (KRX)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 실시간프로그램매매 (KRX) |
| **API ID** | 실시간-048 |
| **HTTP Method** | POST |
| **URL** | /tryitout/H0STPGM0 |
| **Domain (실전)** | ws://ops.koreainvestment.com:21000 |

**설명:**
국내주식 실시간프로그램매매 (KRX) API입니다.

**Python 코드 예시:**
```python
import requests

def call_11_realtime(access_token, appkey, appsecret, **params):
    """
    국내주식 실시간프로그램매매 (KRX) API 호출
    
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
result = call_11_realtime(
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

def call_11_realtime(access_token, appkey, appsecret, **params):
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
result = call_11_realtime(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내지수 실시간프로그램매매

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내지수 실시간프로그램매매 |
| **API ID** | 실시간-028 |
| **HTTP Method** | POST |
| **URL** | /tryitout/H0UPPGM0 |
| **Domain (실전)** | ws://ops.koreainvestment.com:21000 |

**설명:**
국내지수 실시간프로그램매매 API입니다.

**Python 코드 예시:**
```python
import requests

def call_11_realtime(access_token, appkey, appsecret, **params):
    """
    국내지수 실시간프로그램매매 API 호출
    
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
result = call_11_realtime(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 실시간회원사 (통합)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 실시간회원사 (통합) |
| **API ID** | 국내주식 실시간회원사 (통합) |
| **HTTP Method** | POST |
| **URL** | /tryitout/H0UNMBC0 |
| **Domain (실전)** | ws://ops.koreainvestment.com:21000 |

**설명:**
국내주식 실시간회원사 (통합) API입니다.

**Python 코드 예시:**
```python
import requests

def call_11_realtime(access_token, appkey, appsecret, **params):
    """
    국내주식 실시간회원사 (통합) API 호출
    
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
result = call_11_realtime(
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

def call_11_realtime(access_token, appkey, appsecret, **params):
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
result = call_11_realtime(
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

def call_11_realtime(access_token, appkey, appsecret, **params):
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
result = call_11_realtime(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 실시간호가 (KRX)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 실시간호가 (KRX) |
| **API ID** | 실시간-004 |
| **HTTP Method** | POST |
| **URL** | /tryitout/H0STASP0 |
| **Domain (실전)** | ws://ops.koreainvestment.com:21000 |

**설명:**
국내주식 실시간호가 (KRX) API입니다.

**Python 코드 예시:**
```python
import requests

def call_11_realtime(access_token, appkey, appsecret, **params):
    """
    국내주식 실시간호가 (KRX) API 호출
    
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
result = call_11_realtime(
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

def call_11_realtime(access_token, appkey, appsecret, **params):
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
result = call_11_realtime(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 실시간호가 (NXT)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 실시간호가 (NXT) |
| **API ID** | 국내주식 실시간호가 (NXT) |
| **HTTP Method** | POST |
| **URL** | /tryitout/H0NXASP0 |
| **Domain (실전)** | ws://ops.koreainvestment.com:21000 |

**설명:**
국내주식 실시간호가 (NXT) API입니다.

**Python 코드 예시:**
```python
import requests

def call_11_realtime(access_token, appkey, appsecret, **params):
    """
    국내주식 실시간호가 (NXT) API 호출
    
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
result = call_11_realtime(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 실시간프로그램매매 (NXT)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 실시간프로그램매매 (NXT) |
| **API ID** | 국내주식 실시간프로그램매매 (NXT) |
| **HTTP Method** | POST |
| **URL** | /tryitout/H0NXPGM0 |
| **Domain (실전)** | ws://ops.koreainvestment.com:21000 |

**설명:**
국내주식 실시간프로그램매매 (NXT) API입니다.

**Python 코드 예시:**
```python
import requests

def call_11_realtime(access_token, appkey, appsecret, **params):
    """
    국내주식 실시간프로그램매매 (NXT) API 호출
    
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
result = call_11_realtime(
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

def call_11_realtime(access_token, appkey, appsecret, **params):
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
result = call_11_realtime(
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

def call_11_realtime(access_token, appkey, appsecret, **params):
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
result = call_11_realtime(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 실시간회원사 (KRX)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 실시간회원사 (KRX) |
| **API ID** | 실시간-047 |
| **HTTP Method** | POST |
| **URL** | /tryitout/H0STMBC0 |
| **Domain (실전)** | ws://ops.koreainvestment.com:21000 |

**설명:**
국내주식 실시간회원사 (KRX) API입니다.

**Python 코드 예시:**
```python
import requests

def call_11_realtime(access_token, appkey, appsecret, **params):
    """
    국내주식 실시간회원사 (KRX) API 호출
    
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
result = call_11_realtime(
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

def call_11_realtime(access_token, appkey, appsecret, **params):
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
result = call_11_realtime(
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

def call_11_realtime(access_token, appkey, appsecret, **params):
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
result = call_11_realtime(
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
