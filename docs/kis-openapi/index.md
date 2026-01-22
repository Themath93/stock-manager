# 한국투자증권 OpenAPI 가이드라인

## 개요

본 가이드라인은 한국투자증권(KIS) OpenAPI를 사용하여 국내주식 자동매매 봇을 개발하는 Python 개발자를 위한 상세한 API 문서입니다.

## 퀵스타트

### 1. 앱키/앱시크릿키 발급

한국투자증권 홈페이지에서 OpenAPI 사용을 위한 앱키(appkey)와 앱시크릿키(appsecret)를 발급받아야 합니다.

1. [한국투자증권 홈페이지](https://member.koreainvestment.com) 접속
2. 마이페이지 > OpenAPI 접속
3. 앱키/앱시크릿키 발급 신청

**주의사항:**
- 앱키와 앱시크릿키는 절대 노출되지 않도록 주의해주세요.
- 보안을 위해 환경변수 또는 별도 설정 파일에 저장하는 것을 권장합니다.

### 2. 접근 토큰 발급

```python
import requests

ACCESS_TOKEN_URL = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"

def get_access_token(appkey, appsecret):
    """
    접근 토큰 발급
    
    Args:
        appkey: 한국투자증권에서 발급받은 앱키
        appsecret: 한국투자증권에서 발급받은 앱시크릿키
    
    Returns:
        dict: access_token, token_type, expires_in
    """
    headers = {
        "Content-Type": "application/json"
    }
    
    data = {
        "grant_type": "client_credentials",
        "appkey": appkey,
        "appsecret": appsecret
    }
    
    response = requests.post(ACCESS_TOKEN_URL, headers=headers, json=data)
    
    if response.status_code == 200:
        result = response.json()
        return {
            "access_token": result["access_token"],
            "token_type": result["token_type"],
            "expires_in": result["expires_in"],
            "access_token_token_expired": result.get("access_token_token_expired")
        }
    else:
        raise Exception(f"접근 토큰 발급 실패: {response.status_code}, {response.text}")
```

**토큰 유효기간:**
- 일반개인고객/일반법인고객: 24시간 (1일 1회 발급 원칙)
- 갱신발급주기: 6시간 (6시간 이내 재호출 시 직전 토큰값 리턴)
- 제휴법인: 접근 토큰 유효기간 3개월

### 3. 해시키(Hashkey) 발급 (선택사항)

POST 요청(주문/정정/취소 API)에 대해 보안을 강화하기 위해 해시키를 발급받을 수 있습니다.

```python
def get_hashkey(appkey, appsecret, request_body):
    """
    해시키 발급
    
    Args:
        appkey: 앱키
        appsecret: 앱시크릿키
        request_body: 요청 본문 (dict)
    
    Returns:
        str: 해시키
    """
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "appkey": appkey,
        "appsecret": appsecret
    }
    
    response = requests.post(
        "https://openapi.koreainvestment.com:9443/uapi/hashkey",
        headers=headers,
        json=request_body
    )
    
    if response.status_code == 200:
        return response.json()["HASH"]
    else:
        raise Exception(f"해시키 발급 실패: {response.status_code}")
```

## API 카테고리

| 카테고리 | 파일 | 설명 | API 개수 |
|----------|------|----------|----------|
| 인증 (Authentication) | `01-authentication.md` | API 인증 및 토큰 관리 | 4개 |
| 계좌 정보 (Account Info) | `02-account-info.md` | 계좌 잔고, 자산, 예수금 조회 | 12개 |
| 주문 (Order) | `03-orders.md` | 주식 매수/매도 주문, 정정/취소 | 5개 |
| 체결/미체결 (Execution) | `04-execution.md` | 주문 체결 내역, 미체결 현황 | 17개 |
| 시세 (Market Data) | `05-market-data.md` | 주식 현재가, 호가, 기간별 시세 | 17개 |
| 업종 (Sector) | `06-sector.md` | 업종 지수, 업종별 시세 | 3개 |
| 기본정보 (Basic Info) | `07-basic-info.md` | 종목 기본정보, 상품정보 | 2개 |
| 재무정보 (Financial) | `08-financial.md` | 재무비율, 손익계산서, 대차대조표 | 8개 |
| 일정 (Schedule) | `09-schedule.md` | 배당, 주주총회, 공모주 등 일정 | 12개 |
| 랭킹 (Ranking) | `10-ranking.md` | 시가총액, 등락률, 거래량 순위 | 12개 |
| 실시간 데이터 (Real-time) | `11-realtime.md` | 실시간 체결가, 호가, 예상체결 | 14개 |
| 관심종목 (Watchlist) | `12-watchlist.md` | 관심종목 그룹, 멀티종목 조회 | 2개 |
| 시장 동향 (Market Trend) | `13-market-trend.md` | 프로그램매매, 외국인/기관 동향 | 11개 |
| 퇴직연금 (Pension) | `14-pension.md` | 퇴직연금 관련 API | 0개 |
| 시간외 시장 (After-hours) | `15-after-hours.md` | 시간외 거래 관련 API | 1개 |

**총 API: 115개**

## 일반적인 워크플로우

### 1. 인증
```
접근 토큰 발급 → 해시키 발급(선택사항)
```

### 2. 계좌 정보 조회
```
계좌 잔고 조회 → 매수/매도 가능 조회
```

### 3. 주문
```
해시키 생성 → 주문 전송(매수/매도) → 주문 번호 확인
```

### 4. 체결 확인
```
주문 체결 내역 조회 → 미체결 내역 확인 → 포지션 확인
```

## 주의사항

### Rate Limit
- 일일 API 호출 횟수 제한이 있습니다.
- 과도한 호출은 서비스 차단될 수 있습니다.

### Error Handling
```python
def call_api(url, headers, data):
    try:
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            raise Exception("인증 실패: 접근 토큰 갱신 필요")
        elif response.status_code == 429:
            raise Exception("Rate Limit 초과")
        else:
            raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")
            
    except requests.exceptions.RequestException as e:
        raise Exception(f"네트워크 오류: {e}")
```

### 트러블슈팅

| 문제 | 해결 방법 |
|------|-----------|
| 401 Unauthorized | 접근 토큰이 만료되었습니다. 새로 발급받으세요. |
| 429 Too Many Requests | API 호출 빈도가 너무 높습니다. 호출 간격을 늘리세요. |
| Hashkey 관련 에러 | 해시키를 사용하지 않거나 잘못된 형식입니다. |
| 계좌 잔고 불일치 | 캐시를 확인하거나 API 재호출을 시도하세요. |

## 참고 자료

- [한국투자증권 OpenAPI 개발가이드](https://apiportal.koreainvestment.com/)
- [GitHub Examples](https://github.com/koreainvestment)
