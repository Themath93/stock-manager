#!/usr/bin/env python3
"""
KIS OpenAPI Excel Parsing Script

Parses HTS_OPENAPI.xlsx "API 목록" sheet to generate TR_ID mapping table.

Usage:
    python scripts/parse_kis_excel.py

Output:
    docs/kis-openapi/_data/tr_id_mapping.json
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

import openpyxl

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Excel file path
EXCEL_FILE = Path(__file__).parent.parent / "HTS_OPENAPI.xlsx"
# Output JSON path
OUTPUT_FILE = Path(__file__).parent.parent / "docs" / "kis-openapi" / "_data" / "tr_id_mapping.json"


def parse_excel() -> Dict[str, Any]:
    """
    Parse HTS_OPENAPI.xlsx "API 목록" sheet.

    Returns:
        Dict[str, Any]: TR_ID mapping dictionary

    Structure:
        {
            "api_id": {
                "name": "API Name",
                "real_tr_id": "Real Trading TR_ID",
                "paper_tr_id": "Paper Trading TR_ID",
                "category": "Menu Location",
                "http_method": "GET/POST",
                "url": "/uapi/...",
                "communication_type": "REST/WEBSOCKET"
            }
        }
    """
    logger.info(f"Parsing Excel file: {EXCEL_FILE}")

    # Load workbook
    wb = openpyxl.load_workbook(EXCEL_FILE, data_only=True)

    # Get "API 목록" sheet
    if "API 목록" not in wb.sheetnames:
        raise ValueError("'API 목록' sheet not found in Excel file")

    ws = wb["API 목록"]

    # Initialize mapping dictionary
    tr_id_mapping: Dict[str, Any] = {}
    api_count = 0
    real_tr_id_count = 0
    paper_tr_id_count = 0

    # Iterate through rows (skip header row)
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        # Extract columns
        # Row structure:
        # 0: 순번, 1: API 통신방식, 2: 메뉴 위치, 3: API 명,
        # 4: API ID, 5: 실전 TR_ID, 6: 모의 TR_ID,
        # 7: HTTP Method, 8: URL 명, 9: 실전 Domain, 10: 모의 Domain
        seq_no = row[0]
        comm_type = row[1]
        menu_location = row[2]
        api_name = row[3]
        api_id = row[4]
        real_tr_id = row[5]
        paper_tr_id = row[6]
        http_method = row[7]
        url = row[8]

        # Skip if api_id is missing
        if not api_id:
            logger.warning(f"Row {row_idx}: Missing API ID, skipping")
            continue

        # Create API entry
        api_entry = {
            "name": api_name or "",
            "real_tr_id": real_tr_id or "",
            "paper_tr_id": paper_tr_id or "",
            "category": menu_location or "",
            "http_method": http_method or "",
            "url": url or "",
            "communication_type": comm_type or "",
        }

        # Add to mapping
        tr_id_mapping[api_id] = api_entry
        api_count += 1

        # Track TR_ID counts
        if real_tr_id:
            real_tr_id_count += 1
        if paper_tr_id:
            paper_tr_id_count += 1

    logger.info(f"Parsed {api_count} APIs")
    logger.info(f"  - Real TR_IDs: {real_tr_id_count}")
    logger.info(f"  - Paper TR_IDs: {paper_tr_id_count}")

    return tr_id_mapping


def validate_json_schema(data: Dict[str, Any]) -> bool:
    """
    Validate JSON schema.

    Args:
        data: TR_ID mapping dictionary

    Returns:
        bool: True if valid
    """
    logger.info("Validating JSON schema...")

    # Check if data is a dictionary
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")

    # Check if data is not empty
    if not data:
        raise ValueError("Data is empty")

    # Validate each API entry
    for api_id, entry in data.items():
        if not isinstance(entry, dict):
            raise ValueError(f"API {api_id}: Entry must be a dictionary")

        # Required fields
        required_fields = ["name", "real_tr_id", "paper_tr_id", "category", "http_method", "url", "communication_type"]
        for field in required_fields:
            if field not in entry:
                raise ValueError(f"API {api_id}: Missing required field '{field}'")

    logger.info("JSON schema validation passed")
    return True


def save_json(data: Dict[str, Any]) -> None:
    """
    Save JSON data to file.

    Args:
        data: TR_ID mapping dictionary
    """
    logger.info(f"Saving JSON to: {OUTPUT_FILE}")

    # Create output directory if it doesn't exist
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Save with pretty formatting
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f"JSON saved successfully ({len(data)} APIs)")


def main() -> None:
    """Main function."""
    try:
        # Parse Excel
        tr_id_mapping = parse_excel()

        # Validate schema
        validate_json_schema(tr_id_mapping)

        # Save JSON
        save_json(tr_id_mapping)

        logger.info("Excel parsing completed successfully!")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
