#!/usr/bin/env python3
"""
Fix TR_IDs in Existing KIS OpenAPI Documentation

Updates TR_ID values in existing documentation files based on the TR_ID mapping table.

Usage:
    python scripts/fix_existing_docs.py [--dry-run]

Arguments:
    --dry-run: Show what would be changed without making changes

Output:
    Updates documentation files with correct TR_IDs
"""

import argparse
import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# File paths
DOCS_DIR = Path(__file__).parent.parent / "docs" / "kis-openapi"
MAPPING_FILE = Path(__file__).parent.parent / "docs" / "kis-openapi" / "_data" / "tr_id_mapping.json"


def load_tr_id_mapping() -> Dict[str, Any]:
    """Load TR_ID mapping from JSON file.

    Returns:
        Dict[str, Any]: TR_ID mapping dictionary
    """
    logger.info(f"Loading TR_ID mapping from: {MAPPING_FILE}")

    with open(MAPPING_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_api_id_from_doc(content: str) -> str:
    """Extract API ID from documentation content.

    Args:
        content: Documentation file content

    Returns:
        str: API ID or empty string if not found
    """
    # Look for API ID pattern: **API ID** | xxxxx
    match = re.search(r'\*\*API ID\*\*\s*\|\s*([^\s|]+)', content)
    if match:
        return match.group(1)

    return ""


def find_tr_id_in_code(content: str) -> List[Tuple[int, str]]:
    """Find all tr_id occurrences in code blocks.

    Args:
        content: Documentation file content

    Returns:
        List[Tuple[int, str]]: List of (line_number, tr_id_value)
    """
    tr_ids = []

    # Find tr_id in Python code examples
    # Pattern: "tr_id": "value" or 'tr_id': 'value'
    pattern = re.compile(r'["\']tr_id["\']\s*:\s*["\']([^"\']+)["\']')

    for line_num, line in enumerate(content.split('\n'), start=1):
        matches = pattern.findall(line)
        for tr_id_value in matches:
            tr_ids.append((line_num, tr_id_value))

    return tr_ids


def fix_tr_ids_in_doc(file_path: Path, mapping: Dict[str, Any], dry_run: bool = False) -> bool:
    """Fix TR_IDs in a documentation file.

    Args:
        file_path: Path to documentation file
        mapping: TR_ID mapping dictionary
        dry_run: If True, don't actually modify files

    Returns:
        bool: True if file was modified (or would be modified)
    """
    # Read file content
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract API ID from document
    api_id = extract_api_id_from_doc(content)

    if not api_id:
        logger.warning(f"No API ID found in {file_path.name}")
        return False

    # Check if API ID exists in mapping
    if api_id not in mapping:
        logger.warning(f"API ID '{api_id}' not found in mapping ({file_path.name})")
        return False

    api_info = mapping[api_id]
    real_tr_id = api_info.get("real_tr_id", "")
    paper_tr_id = api_info.get("paper_tr_id", "")

    # Find existing TR_IDs in code blocks
    existing_tr_ids = find_tr_id_in_code(content)

    if not existing_tr_ids:
        logger.info(f"No TR_IDs found in {file_path.name}")
        return False

    # Check if TR_IDs need to be updated
    needs_update = False
    new_content = content

    for line_num, current_tr_id in existing_tr_ids:
        # Determine correct TR_ID
        # Prefer real_tr_id, use paper_tr_id if real is empty
        correct_tr_id = real_tr_id if real_tr_id else (paper_tr_id if paper_tr_id != "모의투자 미지원" else current_tr_id)

        if not correct_tr_id:
            logger.info(f"No valid TR_ID for API '{api_id}' ({file_path.name})")
            continue

        if current_tr_id != correct_tr_id:
            needs_update = True
            logger.info(f"Line {line_num}: '{current_tr_id}' -> '{correct_tr_id}'")

            # Replace TR_ID in content
            # Use regex to replace only the value part
            pattern = re.compile(
                r'(["\']tr_id["\']\s*:\s*["\'])' + re.escape(current_tr_id) + r'(["\'])'
            )
            replacement = r'\1' + correct_tr_id + r'\2'
            new_content = pattern.sub(replacement, new_content)

    if needs_update and not dry_run:
        # Write updated content back to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        logger.info(f"Updated {file_path.name}")

    return needs_update


def scan_directory(docs_dir: Path, mapping: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    """Scan documentation directory and fix TR_IDs.

    Args:
        docs_dir: Documentation directory path
        mapping: TR_ID mapping dictionary
        dry_run: If True, don't actually modify files

    Returns:
        Dict[str, Any]: Statistics
    """
    stats = {
        "total_files": 0,
        "files_with_tr_ids": 0,
        "files_updated": 0,
        "tr_ids_checked": 0,
        "tr_ids_updated": 0,
    }

    # Get all markdown files
    md_files = sorted(docs_dir.glob("*.md"))

    # Skip index.md and category files (they don't have TR_IDs)
    md_files = [f for f in md_files if f.name != "index.md"]

    logger.info(f"Scanning {len(md_files)} documentation files...")

    for md_file in md_files:
        stats["total_files"] += 1

        try:
            # Fix TR_IDs in file
            updated = fix_tr_ids_in_doc(md_file, mapping, dry_run)

            if updated:
                stats["files_updated"] += 1

            # Count TR_IDs checked
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
                tr_ids = find_tr_id_in_code(content)
                if tr_ids:
                    stats["files_with_tr_ids"] += 1
                    stats["tr_ids_checked"] += len(tr_ids)

                    if updated:
                        stats["tr_ids_updated"] += len(tr_ids)

        except Exception as e:
            logger.error(f"Error processing {md_file.name}: {e}")

    return stats


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(description="Fix TR_IDs in existing KIS OpenAPI documentation")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without making changes")

    args = parser.parse_args()

    try:
        if args.dry_run:
            logger.info("DRY RUN MODE - No files will be modified")

        # Load TR_ID mapping
        tr_id_mapping = load_tr_id_mapping()

        # Scan and fix documentation
        stats = scan_directory(DOCS_DIR, tr_id_mapping, dry_run=args.dry_run)

        # Print statistics
        logger.info("\n=== Statistics ===")
        logger.info(f"Total files scanned: {stats['total_files']}")
        logger.info(f"Files with TR_IDs: {stats['files_with_tr_ids']}")
        logger.info(f"Files updated: {stats['files_updated']}")
        logger.info(f"TR_IDs checked: {stats['tr_ids_checked']}")
        logger.info(f"TR_IDs updated: {stats['tr_ids_updated']}")

        if args.dry_run and stats['files_updated'] > 0:
            logger.info("\nRun without --dry-run to apply changes")

        logger.info("\nDone!")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
