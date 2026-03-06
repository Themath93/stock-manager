# Domestic Finance Payload Contract

- Updated: 2026-03-05
- Scope: `domestic_stock/info.py` finance endpoints used by consensus fetcher
- Source baseline: KIS OpenAPI requirement + production error evidence (`OPSQ2001`)

## Contract

| Endpoint | Required Params | Default Params |
|---|---|---|
| `/uapi/domestic-stock/v1/finance/balance-sheet` | `fid_input_iscd` | `fid_cond_mrkt_div_code=J` |
| `/uapi/domestic-stock/v1/finance/income-statement` | `fid_input_iscd` | `fid_cond_mrkt_div_code=J` |
| `/uapi/domestic-stock/v1/finance/financial-ratio` | `fid_input_iscd` | `fid_cond_mrkt_div_code=J` |
| `/uapi/domestic-stock/v1/finance/profit-ratio` | `fid_input_iscd` | `fid_cond_mrkt_div_code=J` |
| `/uapi/domestic-stock/v1/finance/other-major-ratios` | `fid_input_iscd` | `fid_cond_mrkt_div_code=J` |
| `/uapi/domestic-stock/v1/finance/stability-ratio` | `fid_input_iscd` | `fid_cond_mrkt_div_code=J` |
| `/uapi/domestic-stock/v1/finance/growth-ratio` | `fid_input_iscd` | `fid_cond_mrkt_div_code=J` |

## Enforcement

- Wrapper-level normalization: missing `fid_cond_mrkt_div_code` is auto-injected.
- Wrapper-level validation: missing `fid_input_iscd` raises `ValueError`.
- Consensus fetcher always passes `fid_input_iscd` and uses throttled API call path.
