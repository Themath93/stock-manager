# 시장 동향 (Market Trend)

## 개요

시장 동향 (Market Trend) 관련 API입니다.

## API 목록


### 프로그램매매 종합현황(시간)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 프로그램매매 종합현황(시간) |
| **API ID** | 국내주식-114 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/comp-program-trade-today |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
프로그램매매 종합현황(시간) API입니다.

**Python 코드 예시:**
```python
import requests

def call_13_market_trend(access_token, appkey, appsecret, **params):
    """
    프로그램매매 종합현황(시간) API 호출
    
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
result = call_13_market_trend(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 시장별 투자자매매동향(일별)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 시장별 투자자매매동향(일별) |
| **API ID** | 국내주식-075 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/inquire-investor-daily-by-market |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
시장별 투자자매매동향(일별) API입니다.

**Python 코드 예시:**
```python
import requests

def call_13_market_trend(access_token, appkey, appsecret, **params):
    """
    시장별 투자자매매동향(일별) API 호출
    
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
result = call_13_market_trend(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 종목별 투자자매매동향(일별)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 종목별 투자자매매동향(일별) |
| **API ID** | 종목별 투자자매매동향(일별) |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/investor-trade-by-stock-daily |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
종목별 투자자매매동향(일별) API입니다.

**Python 코드 예시:**
```python
import requests

def call_13_market_trend(access_token, appkey, appsecret, **params):
    """
    종목별 투자자매매동향(일별) API 호출
    
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
result = call_13_market_trend(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 프로그램매매 종합현황(일별)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 프로그램매매 종합현황(일별) |
| **API ID** | 국내주식-115 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/comp-program-trade-daily |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
프로그램매매 종합현황(일별) API입니다.

**Python 코드 예시:**
```python
import requests

def call_13_market_trend(access_token, appkey, appsecret, **params):
    """
    프로그램매매 종합현황(일별) API 호출
    
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
result = call_13_market_trend(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내주식 매물대/거래비중

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내주식 매물대/거래비중 |
| **API ID** | 국내주식-196 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/pbar-tratio |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내주식 매물대/거래비중 API입니다.

**Python 코드 예시:**
```python
import requests

def call_13_market_trend(access_token, appkey, appsecret, **params):
    """
    국내주식 매물대/거래비중 API 호출
    
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
result = call_13_market_trend(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 국내기관_외국인 매매종목가집계

| 항목 | 내용 |
|--------|--------|
| **API 명** | 국내기관_외국인 매매종목가집계 |
| **API ID** | 국내주식-037 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/foreign-institution-total |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
국내기관_외국인 매매종목가집계 API입니다.

**Python 코드 예시:**
```python
import requests

def call_13_market_trend(access_token, appkey, appsecret, **params):
    """
    국내기관_외국인 매매종목가집계 API 호출
    
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
result = call_13_market_trend(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 종목별 프로그램매매추이(일별)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 종목별 프로그램매매추이(일별) |
| **API ID** | 국내주식-113 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/program-trade-by-stock-daily |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
종목별 프로그램매매추이(일별) API입니다.

**Python 코드 예시:**
```python
import requests

def call_13_market_trend(access_token, appkey, appsecret, **params):
    """
    종목별 프로그램매매추이(일별) API 호출
    
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
result = call_13_market_trend(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 종목별 외인기관 추정가집계

| 항목 | 내용 |
|--------|--------|
| **API 명** | 종목별 외인기관 추정가집계 |
| **API ID** | v1_국내주식-046 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/investor-trend-estimate |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
종목별 외인기관 추정가집계 API입니다.

**Python 코드 예시:**
```python
import requests

def call_13_market_trend(access_token, appkey, appsecret, **params):
    """
    종목별 외인기관 추정가집계 API 호출
    
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
result = call_13_market_trend(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 프로그램매매 투자자매매동향(당일)

| 항목 | 내용 |
|--------|--------|
| **API 명** | 프로그램매매 투자자매매동향(당일) |
| **API ID** | 국내주식-116 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/investor-program-trade-today |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
프로그램매매 투자자매매동향(당일) API입니다.

**Python 코드 예시:**
```python
import requests

def call_13_market_trend(access_token, appkey, appsecret, **params):
    """
    프로그램매매 투자자매매동향(당일) API 호출
    
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
result = call_13_market_trend(
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

def call_13_market_trend(access_token, appkey, appsecret, **params):
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
result = call_13_market_trend(
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

def call_13_market_trend(access_token, appkey, appsecret, **params):
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
result = call_13_market_trend(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 외국계 매매종목 가집계

| 항목 | 내용 |
|--------|--------|
| **API 명** | 외국계 매매종목 가집계 |
| **API ID** | 국내주식-161 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/frgnmem-trade-estimate |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
외국계 매매종목 가집계 API입니다.

**Python 코드 예시:**
```python
import requests

def call_13_market_trend(access_token, appkey, appsecret, **params):
    """
    외국계 매매종목 가집계 API 호출
    
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
result = call_13_market_trend(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 종목별 외국계 순매수추이

| 항목 | 내용 |
|--------|--------|
| **API 명** | 종목별 외국계 순매수추이 |
| **API ID** | 국내주식-164 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/frgnmem-pchs-trend |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
종목별 외국계 순매수추이 API입니다.

**Python 코드 예시:**
```python
import requests

def call_13_market_trend(access_token, appkey, appsecret, **params):
    """
    종목별 외국계 순매수추이 API 호출
    
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
result = call_13_market_trend(
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

def call_13_market_trend(access_token, appkey, appsecret, **params):
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
result = call_13_market_trend(
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

def call_13_market_trend(access_token, appkey, appsecret, **params):
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
result = call_13_market_trend(
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

def call_13_market_trend(access_token, appkey, appsecret, **params):
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
result = call_13_market_trend(
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

def call_13_market_trend(access_token, appkey, appsecret, **params):
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
result = call_13_market_trend(
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
