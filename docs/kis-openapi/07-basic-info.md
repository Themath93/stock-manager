# 기본정보 (Basic Info)

## 개요

기본정보 (Basic Info) 관련 API입니다.

## API 목록


### 상품기본조회

| 항목 | 내용 |
|--------|--------|
| **API 명** | 상품기본조회 |
| **API ID** | v1_국내주식-029 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/search-info |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
상품기본조회 API입니다.

**Python 코드 예시:**
```python
import requests

def call_07_basic_info(access_token, appkey, appsecret, **params):
    """
    상품기본조회 API 호출
    
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
result = call_07_basic_info(
    access_token="your_access_token",
    appkey="your_appkey",
    appsecret="your_appsecret"
)
print(result)
```

---


### 주식기본조회

| 항목 | 내용 |
|--------|--------|
| **API 명** | 주식기본조회 |
| **API ID** | v1_국내주식-067 |
| **HTTP Method** | GET |
| **URL** | /uapi/domestic-stock/v1/quotations/search-stock-info |
| **Domain (실전)** | https://openapi.koreainvestment.com:9443 |

**설명:**
주식기본조회 API입니다.

**Python 코드 예시:**
```python
import requests

def call_07_basic_info(access_token, appkey, appsecret, **params):
    """
    주식기본조회 API 호출
    
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
result = call_07_basic_info(
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
