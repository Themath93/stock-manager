# {{api_name}}

## Overview

**API ID**: `{{api_id}}`
**Category**: {{category}}
**HTTP Method**: {{http_method}}
**URL**: `{{url}}`
**Communication Type**: {{communication_type}}

## Description

{{api_name}} API for {{category}}.

## TR_ID Information

| Environment | TR_ID |
|-------------|-------|
| Real Trading | `{{real_tr_id}}` |
| Paper Trading | `{{paper_tr_id}}` |

{% if real_tr_id == "" and paper_tr_id == "" %}
**Note**: This API does not require a TR_ID.
{% elif paper_tr_id == "모의투자 미지원" %}
**Note**: Paper trading is not supported for this API.
{% endif %}

## Endpoint

```
{{http_method}} {{url}}
```

## Request Parameters

{% if has_params %}
### Required Parameters

| Parameter | Type | Description | Required |
|-----------|------|-------------|----------|
| `tr_id` | string | TR_ID (Real: `{{real_tr_id}}`, Paper: `{{paper_tr_id}}`) | Yes |

### Optional Parameters

{% if api_id.startswith("국내주식") or api_id.startswith("해외주식") %}
For detailed parameter information, refer to the official KIS OpenAPI documentation.
{% endif %}
{% else %}
No additional parameters required beyond standard authentication headers.
{% endif %}

## Response

### Response Format

{% if communication_type == "REST" %}
JSON response format.

```json
{
  "rt_cd": "0",
  "msg_cd": "",
  "msg1": "",
  "output": {
    // Response data
  }
}
```
{% elif communication_type == "WEBSOCKET" %}
WebSocket real-time data format.

```json
{
  "tr_id": "{{real_tr_id}}",
  "rt_cd": "0",
  "msg_cd": "",
  "msg1": "",
  "output": {
    // Real-time data
  }
}
```
{% endif %}

### Response Fields

For detailed field information, refer to the official KIS OpenAPI documentation.

## Example Usage

### Python Example

```python
import requests

# Set your API credentials
app_key = "your_app_key"
app_secret = "your_app_secret"
access_token = "your_access_token"

# Set TR_ID based on environment
tr_id = "{{real_tr_id}}"  # Use "{{paper_tr_id}}" for paper trading

# Make API request
url = "https://api.koreainvestment.com{{url}}"
headers = {
    "Authorization": f"Bearer {access_token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": tr_id,
    "custtype": "P"  # P: Individual, B: Corporate
}

{% if http_method == "GET" %}
params = {
    # Add required parameters
}

response = requests.get(url, headers=headers, params=params)
{% elif http_method == "POST" %}
data = {
    # Add required parameters
}

response = requests.post(url, headers=headers, json=data)
{% endif %}

result = response.json()
print(result)
```

## Notes

- This API requires valid authentication credentials (app_key, app_secret, access_token)
- TR_ID must be set according to the trading environment (real or paper)
- For detailed parameter specifications and response fields, refer to the [official KIS OpenAPI documentation](https://apiportal.koreainvestment.com/)

## Related APIs

{% if related_apis %}
- {% for related_api in related_apis %}[{{related_api.name}}](../{{related_api.category}}/{{related_api.id}}.md)
{% endfor %}
{% endif %}

## Category

[Back to {{category}}](../index.md)
