# Domestic Quotations Payload Contract

- Updated: 2026-03-06
- Scope: `domestic_stock/basic.py` quotation endpoints used by consensus fetcher
- Source baseline: KIS MCP sample code + production error evidence (`OPSQ2001`)

## MCP References

- `inquire_daily_itemchartprice` main:
  `https://github.com/koreainvestment/open-trading-api/tree/main/examples_llm/domestic_stock/inquire_daily_itemchartprice/inquire_daily_itemchartprice.py`
- `inquire_daily_itemchartprice` check:
  `https://github.com/koreainvestment/open-trading-api/tree/main/examples_llm/domestic_stock/inquire_daily_itemchartprice/chk_inquire_daily_itemchartprice.py`
- `inquire_daily_price` main:
  `https://github.com/koreainvestment/open-trading-api/tree/main/examples_llm/domestic_stock/inquire_daily_price/inquire_daily_price.py`
- `inquire_daily_price` check:
  `https://github.com/koreainvestment/open-trading-api/tree/main/examples_llm/domestic_stock/inquire_daily_price/chk_inquire_daily_price.py`

## Contract

| Endpoint | Required Params | Default Params |
|---|---|---|
| `/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice` | `fid_input_iscd`, `fid_cond_mrkt_div_code` | `fid_cond_mrkt_div_code=J`, `fid_org_adj_prc=1` |
| `/uapi/domestic-stock/v1/quotations/inquire-daily-price` | `fid_input_iscd`, `fid_cond_mrkt_div_code` | `fid_cond_mrkt_div_code=J`, `fid_org_adj_prc=1`, `fid_period_div_code=D` |

## Enforcement

- Wrapper-level normalization:
  - Missing market code is auto-injected as `fid_cond_mrkt_div_code=J`.
- Wrapper-level validation:
  - Blank `fid_input_iscd` is rejected with `ValueError`.
  - Blank `fid_cond_mrkt_div_code` is rejected with `ValueError`.
- Fetcher-level explicit payload:
  - `TechnicalDataFetcher._fetch_technicals()` always passes `fid_cond_mrkt_div_code="J"`.
