#!/usr/bin/env python3
"""
Reorganize KIS OpenAPI Documentation by Category

Creates category directories and moves documentation files based on API categories.
Also generates categories.json metadata file.

Usage:
    python scripts/reorganize_categories.py [--dry-run]

Arguments:
    --dry-run: Show what would be changed without making changes

Output:
    - Creates 16 category directories
    - Generates docs/kis-openapi/_data/categories.json
    - Moves existing docs to new categories
"""

import argparse
import json
import logging
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# File paths
DOCS_DIR = Path(__file__).parent.parent / "docs" / "kis-openapi"
MAPPING_FILE = Path(__file__).parent.parent / "docs" / "kis-openapi" / "_data" / "tr_id_mapping.json"
CATEGORIES_FILE = Path(__file__).parent.parent / "docs" / "kis-openapi" / "_data" / "categories.json"


# Category mapping (16 categories as per SPEC)
CATEGORY_MAPPING = {
    "OAuth인증": "01-authentication",
    "[국내주식] 주문/계좌": "02-domestic-orders",
    "[국내주식] 잔고/예수금": "03-domestic-balance",
    "[국내주식] 현재가/시세": "04-domestic-market-data",
    "[국내주식] 일별/기간별시세": "05-domestic-historical",
    "[국내주식] 기초/종목/투자지표": "06-domestic-fundamental",
    "[국내주식] 공시/일정/배당": "07-domestic-corporate",
    "[국내주식] 순위/검색": "08-domestic-ranking",
    "[국내주식] 체결/잔량/투자자": "09-domestic-realtime",
    "[국내주식] 시간외/야간": "10-domestic-after-hours",
    "[국내선물옵션] 주문/잔고/시세": "11-domestic-derivatives",
    "ELW": "12-elw",
    "[해외주식] 주문/계좌/잔고": "13-overseas-orders",
    "[해외주식] 현재가/시세": "14-overseas-market-data",
    "[해외주식] 해외선물옵션": "15-overseas-derivatives",
    "채권": "16-bond",
}


def load_tr_id_mapping() -> Dict[str, Any]:
    """Load TR_ID mapping from JSON file.

    Returns:
        Dict[str, Any]: TR_ID mapping dictionary
    """
    logger.info(f"Loading TR_ID mapping from: {MAPPING_FILE}")

    with open(MAPPING_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_api_id_from_file(file_path: Path) -> str:
    """Extract API ID from documentation file.

    Args:
        file_path: Path to documentation file

    Returns:
        str: API ID or empty string if not found
    """
    import re

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Look for API ID pattern: **API ID** | xxxxx
    match = re.search(r'\*\*API ID\*\*\s*\|\s*([^\s|]+)', content)
    if match:
        return match.group(1)

    return ""


def build_api_to_category_map(mapping: Dict[str, Any]) -> Dict[str, str]:
    """Build mapping from API ID to category directory.

    Args:
        mapping: TR_ID mapping dictionary

    Returns:
        Dict[str, str]: API ID to category directory mapping
    """
    api_to_category = {}

    for api_id, api_info in mapping.items():
        category = api_info.get("category", "")

        if category in CATEGORY_MAPPING:
            api_to_category[api_id] = CATEGORY_MAPPING[category]
        else:
            # Uncategorized
            api_to_category[api_id] = "00-uncategorized"

    return api_to_category


def generate_categories_metadata(mapping: Dict[str, Any]) -> Dict[str, Any]:
    """Generate categories metadata JSON.

    Args:
        mapping: TR_ID mapping dictionary

    Returns:
        Dict[str, Any]: Categories metadata
    """
    # Count APIs per category
    category_counts = defaultdict(int)
    category_apis = defaultdict(list)

    for api_id, api_info in mapping.items():
        category = api_info.get("category", "")
        category_counts[category] += 1
        category_apis[category].append(api_id)

    # Build categories metadata
    categories = {}

    # Add all 16 categories
    for korean_name, english_name in CATEGORY_MAPPING.items():
        categories[english_name] = {
            "name_ko": korean_name,
            "name_en": english_name.replace("-", " ").title(),
            "api_count": category_counts.get(korean_name, 0),
        }

    # Add uncategorized category if needed
    if any(cat not in CATEGORY_MAPPING for cat in category_counts.keys()):
        categories["00-uncategorized"] = {
            "name_ko": "미분류",
            "name_en": "Uncategorized",
            "api_count": sum(count for cat, count in category_counts.items() if cat not in CATEGORY_MAPPING),
        }

    return categories


def create_category_directories(dry_run: bool = False) -> List[Path]:
    """Create category directories.

    Args:
        dry_run: If True, don't actually create directories

    Returns:
        List[Path]: List of created directory paths
    """
    created_dirs = []

    for category_name in CATEGORY_MAPPING.values():
        category_dir = DOCS_DIR / category_name

        if not category_dir.exists():
            if not dry_run:
                category_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {category_dir}")
            else:
                logger.info(f"Would create directory: {category_dir}")

            created_dirs.append(category_dir)
        else:
            logger.info(f"Directory already exists: {category_dir}")

    return created_dirs


def move_docs_to_categories(api_to_category: Dict[str, str], dry_run: bool = False) -> Dict[str, Any]:
    """Move documentation files to category directories.

    Args:
        api_to_category: API ID to category directory mapping
        dry_run: If True, don't actually move files

    Returns:
        Dict[str, Any]: Statistics
    """
    stats = {
        "total_files": 0,
        "files_moved": 0,
        "files_skipped": 0,
        "files_not_found": 0,
    }

    # Get all markdown files in docs directory (not in subdirectories)
    md_files = sorted(DOCS_DIR.glob("*.md"))

    # Skip index.md and files already in subdirectories
    md_files = [f for f in md_files if f.name != "index.md" and f.parent == DOCS_DIR]

    logger.info(f"Found {len(md_files)} documentation files to process")

    for md_file in md_files:
        stats["total_files"] += 1

        # Extract API ID from file
        api_id = extract_api_id_from_file(md_file)

        if not api_id:
            logger.warning(f"No API ID found in {md_file.name}, skipping")
            stats["files_skipped"] += 1
            continue

        # Get category for this API
        if api_id not in api_to_category:
            logger.warning(f"No category found for API ID '{api_id}' ({md_file.name}), skipping")
            stats["files_skipped"] += 1
            continue

        category_dir_name = api_to_category[api_id]
        category_dir = DOCS_DIR / category_dir_name
        dest_file = category_dir / md_file.name

        # Check if destination file already exists
        if dest_file.exists():
            logger.warning(f"Destination file already exists: {dest_file}, skipping")
            stats["files_skipped"] += 1
            continue

        # Move file
        if not dry_run:
            shutil.move(str(md_file), str(dest_file))
            logger.info(f"Moved {md_file.name} -> {category_dir_name}/")
        else:
            logger.info(f"Would move {md_file.name} -> {category_dir_name}/")

        stats["files_moved"] += 1

    return stats


def save_categories_metadata(categories: Dict[str, Any], dry_run: bool = False) -> None:
    """Save categories metadata to JSON file.

    Args:
        categories: Categories metadata dictionary
        dry_run: If True, don't actually save file
    """
    logger.info(f"Saving categories metadata to: {CATEGORIES_FILE}")

    if not dry_run:
        CATEGORIES_FILE.parent.mkdir(parents=True, exist_ok=True)

        with open(CATEGORIES_FILE, "w", encoding="utf-8") as f:
            json.dump(categories, f, ensure_ascii=False, indent=2)

        logger.info(f"Categories metadata saved ({len(categories)} categories)")
    else:
        logger.info(f"Would save categories metadata ({len(categories)} categories)")


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(description="Reorganize KIS OpenAPI documentation by category")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without making changes")

    args = parser.parse_args()

    try:
        if args.dry_run:
            logger.info("DRY RUN MODE - No files will be modified")

        # Load TR_ID mapping
        tr_id_mapping = load_tr_id_mapping()

        # Build API to category map
        api_to_category = build_api_to_category_map(tr_id_mapping)

        # Generate categories metadata
        categories = generate_categories_metadata(tr_id_mapping)

        # Create category directories
        logger.info("\n=== Creating Category Directories ===")
        create_category_directories(dry_run=args.dry_run)

        # Move documentation files
        logger.info("\n=== Moving Documentation Files ===")
        move_stats = move_docs_to_categories(api_to_category, dry_run=args.dry_run)

        # Save categories metadata
        logger.info("\n=== Saving Categories Metadata ===")
        save_categories_metadata(categories, dry_run=args.dry_run)

        # Print statistics
        logger.info("\n=== Statistics ===")
        logger.info(f"Total files processed: {move_stats['total_files']}")
        logger.info(f"Files moved: {move_stats['files_moved']}")
        logger.info(f"Files skipped: {move_stats['files_skipped']}")
        logger.info(f"Files not found: {move_stats['files_not_found']}")
        logger.info(f"Categories created: {len(CATEGORY_MAPPING)}")

        if args.dry_run and move_stats['files_moved'] > 0:
            logger.info("\nRun without --dry-run to apply changes")

        logger.info("\nDone!")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
