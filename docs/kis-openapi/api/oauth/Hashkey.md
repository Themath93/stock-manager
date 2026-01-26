# Hashkey

## API Overview

**API ID**: `Hashkey`
**Category**: OAuth인증
**HTTP Method**: POST
**URL**: `/uapi/hashkey`
**Communication Type**: REST

## Description

Hashkey API for OAuth인증.

## TR_ID Information

| Environment | TR_ID |
|-------------|-------|
| Real Trading | `N/A` |
| Paper Trading | `Not Supported` |

**Note**: This API does not require a TR_ID.

## Endpoint

```
POST /uapi/hashkey
```

## Request Headers

| Header | Value | Required | Description |
|--------|-------|----------|-------------|
| `Authorization` | `Bearer {access_token}` | Yes | OAuth 2.0 access token |
| `appkey` | `{app_key}` | Yes | KIS OpenAPI app key |
| `appsecret` | `{app_secret}` | Yes | KIS OpenAPI app secret |
| `tr_id` | `N/A` | Conditional | TR_ID for real trading |
| `tr_id` | `N/A` | Conditional | TR_ID for paper trading |
| `custtype` | `P` or `B` | Yes | Customer type (P: Individual, B: Corporate) |


## Request Parameters

### Required Parameters

| Parameter | Type | Description | Required |
|-----------|------|-------------|----------|
| `grant_type` | string | Grant type for OAuth 2.0 | Conditional |
| `code` | string | Authorization code | Conditional |
| `client_id` | string | OAuth 2.0 client ID | Conditional |
| `client_secret` | string | OAuth 2.0 client secret | Conditional |

### Optional Parameters

For detailed parameter information, refer to the official KIS OpenAPI documentation.


## Response


### Response Format (REST)

JSON response format with standard KIS OpenAPI structure.

```json
{
  "rt_cd": "0",
  "msg_cd": "",
  "msg1": "Normal processing completed",
  "output": {
    // Response data fields
  }
}
```

### Response Fields

For detailed field information, refer to the official KIS OpenAPI documentation.


## Error Handling

### Error Response Format

```json
{
  "rt_cd": "1",
  "msg_cd": "EGW00223",
  "msg1": "Error message description"
}
```

### Common Error Codes

| Error Code | Description | Action |
|------------|-------------|--------|
| `EGW00123` | Invalid access token | Refresh access token |
| `EGW00223` | Invalid request parameters | Check request parameters |
| `EGW00331` | Rate limit exceeded | Implement retry with exponential backoff |
| `EGW00415` | Unauthorized access | Check authentication credentials |

## Example Usage

### Python Example

```python
import requests
from typing import Dict, Any

# Configuration
APP_KEY = "your_app_key"
APP_SECRET = "your_app_secret"
ACCESS_TOKEN = "your_access_token"
BASE_URL = "https://api.koreainvestment.com"
# No TR_ID required for this API
TR_ID = None

def make_api_request() -> Dict[str, Any]:
    """
    Make API request to Hashkey.

    Returns:
        Dict[str, Any]: API response data
    """
    url = f"{BASE_URL}/uapi/hashkey"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "custtype": "P",  # P: Individual, B: Corporate
    }


    data = {
        # Add required parameters here
    }

    response = requests.post(url, headers=headers, json=data)

    response.raise_for_status()
    return response.json()

# Example usage
if __name__ == "__main__":
    try:
        result = make_api_request()

        if result.get("rt_cd") == "0":
            print("API call successful")
            print(f"Response: {result.get('output')}")
        else:
            print(f"API error: {result.get('msg1')}")
            print(f"Error code: {result.get('msg_cd')}")

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
```

### Using KISRestClient (Recommended)

```python
from stock_manager.adapters.broker.kis import KISConfig, KISRestClient

# Configure client
config = KISConfig(
    kis_app_key="your_app_key",
    kis_app_secret="your_app_secret",
)

client = KISRestClient(config)

# Get TR_ID automatically
tr_id = client.get_tr_id(
    api_id="Hashkey",
    is_paper_trading=False  # Set to True for paper trading
)

# Make request
response = client.make_request(
    method="post",
    url="/uapi/hashkey",
    params={...}  # Request parameters
)
```

## Notes

- This API requires valid OAuth 2.0 authentication credentials (app_key, app_secret, access_token)
- TR_ID must be set according to the trading environment (real or paper)
- For detailed parameter specifications and response fields, refer to the [official KIS OpenAPI documentation](https://apiportal.koreainvestment.com/)
- Rate limiting: Implement exponential backoff retry logic for rate limit errors
- Token refresh: Access tokens expire periodically; implement automatic token refresh

## Related APIs


## Category

[Back to OAuth인증](../index.md) | [API Documentation Index](../../index.md)