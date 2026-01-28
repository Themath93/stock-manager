# SPEC-API-001: 구현 계획 (Implementation Plan)

## 구현 마일스톤

### 1차 마일스톤: API ID 상수 정의 (Priority: MEDIUM)

**목표:** KIS API ID 상수화

**작업:**
- [ ] KISRestClient 클래스에 API ID 상수 추가
- [ ] 주문 관련 API ID 정의
- [ ] 조회 관련 API ID 정의

**검증:**
```python
from stock_manager.adapters.broker.kis.kis_rest_client import KISRestClient
assert hasattr(KISRestClient, 'API_ORDER_CASH')
assert KISRestClient.API_ORDER_CASH == "국내주식-008"
```

---

### 2차 마일스톤: place_order TR_ID 추가 (Priority: HIGH)

**목표:** 주문 전송 시 TR_ID 헤더 포함

**작업:**
- [ ] get_tr_id() 호출로 TR_ID 조회
- [ ] _get_headers(tr_id=...)로 헤더 생성
- [ ] _make_request(tr_id=...)로 명시적 전달

**검증:**
```python
# Mock test
client = KISRestClient(config)
order = OrderRequest(...)

# Verify _get_headers called with tr_id
with patch.object(client, '_make_request') as mock_request:
    client.place_order(order)
    call_kwargs = mock_request.call_args[1]
    assert 'tr_id' in call_kwargs
    assert call_kwargs['tr_id'] is not None
```

---

### 3차 마일스톤: cancel_order, get_orders TR_ID 추가 (Priority: MEDIUM)

**목표:** 모든 KIS API 메서드에 TR_ID 포함

**작업:**
- [ ] cancel_order 수정
- [ ] get_orders 수정
- [ ] 기타 API 메서드 검토

**검증:**
```python
# Verify all API calls include tr_id
assert client._make_request.call_count > 0
for call in client._make_request.call_args_list:
    assert 'tr_id' in call.kwargs
```

---

## 위험 완화

### 위험 1: TR_ID 매핑 파일 누락

**위험:** tr_id_mapping.json 파일이 존재하지 않을 수 있음

**완화:**
- _load_tr_id_mapping()에서 파일 없을 시 빈 dict 반환
- get_tr_id()에서 ValueError 발생
- 명활한 에러 메시지

### 위험 2: 모의투자 미지원 API

**위험:** 일부 API는 모의투자 미지원 ("모의투자 미지원" 문자열)

**완화:**
- get_tr_id()에서 None 반환
- 호출 측에서 None 체크 후 에러 처리

### 위험 3: TR_ID 변경

**위험:** KIS에서 TR_ID 변경 가능

**완화:**
- tr_id_mapping.json 파일로 분리
- 코드가 아닌 데이터로 관리
- 문서화

---

## 구현 순서

1. **API ID 상수 정의** (기초 작업)
2. **place_order 수정** (가장 중요)
3. **cancel_order 수정** (두 번째 중요)
4. **get_orders 수정** (조회 API)
5. **통합 테스트** (전체 검증)

---

## 테스트 전략

### 단위 테스트

```python
def test_place_order_includes_tr_id():
    """place_order가 TR_ID를 포함하는지 확인"""
    config = MockConfig(mode=Mode.PAPER)
    client = KISRestClient(config)

    # _make_request mock
    with patch.object(client, '_make_request') as mock_request:
        mock_request.return_value = {"output": {"ODNO": "12345"}}

        order = OrderRequest(
            account_id="1234567890",
            symbol="005930",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("10"),
            price=None,
            idempotency_key="test-key"
        )

        result = client.place_order(order)

        # Verify tr_id passed
        call_kwargs = mock_request.call_args[1]
        assert 'tr_id' in call_kwargs
        assert call_kwargs['tr_id'] == 'TTTC0801U'  # 모의투자 TR_ID
```

### 통합 테스트

```python
@pytest.mark.integration
def test_real_kis_order_with_tr_id():
    """실제 KIS API에 TR_ID 포함하여 호출"""
    # Requires valid credentials and paper trading environment
    # This test should only run in integration environment
    pass
```
