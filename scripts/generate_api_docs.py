#!/usr/bin/env python3
"""
KIS OpenAPI Documentation Generation Script

Generates markdown documentation for all KIS OpenAPI endpoints from TR_ID mapping.

Usage:
    # Generate all API documentation
    python scripts/generate_api_docs.py

    # Generate top priority APIs only
    python scripts/generate_api_docs.py --phase 1

    # Generate remaining APIs
    python scripts/generate_api_docs.py --phase 2

    # Validate existing documentation
    python scripts/generate_api_docs.py --validate

Output:
    docs/kis-openapi/api/*.md - Individual API documentation files
    docs/kis-openapi/api/*/index.md - Category index files
    docs/kis-openapi/_data/api_summary.json - API summary statistics
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, Template

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# File paths
PROJECT_ROOT = Path(__file__).parent.parent
TR_ID_MAPPING_FILE = PROJECT_ROOT / "docs" / "kis-openapi" / "_data" / "tr_id_mapping.json"
CATEGORIES_FILE = PROJECT_ROOT / "docs_raw" / "categories.json"
TEMPLATE_FILE = PROJECT_ROOT / "templates" / "api_doc_template.md.j2"
API_DOCS_DIR = PROJECT_ROOT / "docs" / "kis-openapi" / "api"
API_SUMMARY_FILE = PROJECT_ROOT / "docs" / "kis-openapi" / "_data" / "api_summary.json"

# Category slug mapping (Korean to English slug)
CATEGORY_SLUGS = {
    "OAuth인증": "oauth",
    "[국내주식] 기본시세": "domestic-stock-basic",
    "[국내주식] 실시간시세": "domestic-stock-realtime",
    "[국내주식] 주문/계좌": "domestic-stock-orders",
    "[국내주식] 시세분석": "domestic-stock-analysis",
    "[국내주식] 순위분석": "domestic-stock-ranking",
    "[국내주식] 종목정보": "domestic-stock-info",
    "[국내주식] ELW 시세": "domestic-stock-elw",
    "[국내주식] 업종/기타": "domestic-stock-sector",
    "[국내선물옵션] 기본시세": "domestic-futures-basic",
    "[국내선물옵션] 실시간시세": "domestic-futures-realtime",
    "[국내선물옵션] 주문/계좌": "domestic-futures-orders",
    "[장내채권] 기본시세": "bond-basic",
    "[장내채권] 실시간시세": "bond-realtime",
    "[장내채권] 주문/계좌": "bond-orders",
    "[해외주식] 기본시세": "overseas-stock-basic",
    "[해외주식] 실시간시세": "overseas-stock-realtime",
    "[해외주식] 주문/계좌": "overseas-stock-orders",
    "[해외주식] 시세분석": "overseas-stock-analysis",
    "[해외선물옵션] 기본시세": "overseas-futures-basic",
    "[해외선물옵션]실시간시세": "overseas-futures-realtime",
    "[해외선물옵션] 주문/계좌": "overseas-futures-orders",
}

# Priority categories for Phase 1 (top ~100 APIs)
PRIORITY_CATEGORIES = [
    "oauth",                        # 4 APIs
    "domestic-stock-orders",        # 23 APIs
    "domestic-stock-realtime",      # 29 APIs
    "overseas-stock-orders",        # 18 APIs
    "domestic-stock-basic",         # 21 APIs
]


def sanitize_filename(api_id: str) -> str:
    """
    Sanitize API ID for use as filename.

    Args:
        api_id: Raw API ID from mapping

    Returns:
        str: Sanitized filename-safe string
    """
    # Replace special characters with hyphens
    sanitized = re.sub(r'[^\w\-]', '-', api_id)
    # Remove consecutive hyphens
    sanitized = re.sub(r'-+', '-', sanitized)
    # Remove leading/trailing hyphens
    sanitized = sanitized.strip('-')
    return sanitized


def load_tr_id_mapping() -> Dict[str, Any]:
    """
    Load TR_ID mapping from JSON file.

    Returns:
        Dict[str, Any]: TR_ID mapping dictionary
    """
    logger.info(f"Loading TR_ID mapping from: {TR_ID_MAPPING_FILE}")

    if not TR_ID_MAPPING_FILE.exists():
        raise FileNotFoundError(f"TR_ID mapping file not found: {TR_ID_MAPPING_FILE}")

    with open(TR_ID_MAPPING_FILE, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    logger.info(f"Loaded {len(mapping)} APIs")
    return mapping


def load_categories() -> Dict[str, Any]:
    """
    Load categories configuration from JSON file.

    Returns:
        Dict[str, Any]: Categories dictionary
    """
    logger.info(f"Loading categories from: {CATEGORIES_FILE}")

    if not CATEGORIES_FILE.exists():
        logger.warning("Categories file not found, using empty categories")
        return {"categories": []}

    with open(CATEGORIES_FILE, "r", encoding="utf-8") as f:
        categories = json.load(f)

    logger.info(f"Loaded {len(categories.get('categories', []))} categories")
    return categories


def load_template() -> Template:
    """
    Load Jinja2 template for documentation generation.

    Returns:
        Template: Jinja2 template object
    """
    logger.info(f"Loading template from: {TEMPLATE_FILE}")

    if not TEMPLATE_FILE.exists():
        raise FileNotFoundError(f"Template file not found: {TEMPLATE_FILE}")

    # Create Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_FILE.parent)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Load template
    template = env.get_template(TEMPLATE_FILE.name)

    logger.info("Template loaded successfully")
    return template


def categorize_apis(tr_id_mapping: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Categorize APIs by their category slug.

    Args:
        tr_id_mapping: TR_ID mapping dictionary

    Returns:
        Dict[str, List[Dict]]: Categorized APIs
    """
    categorized = {}

    for api_id, api_data in tr_id_mapping.items():
        category = api_data["category"]
        category_slug = CATEGORY_SLUGS.get(category, "other")

        if category_slug not in categorized:
            categorized[category_slug] = []

        categorized[category_slug].append({
            "id": sanitize_filename(api_id),
            "api_id": api_id,
            "category_slug": category_slug,
            **api_data
        })

    # Log category distribution
    logger.info(f"APIs categorized into {len(categorized)} groups:")
    for category_slug, apis in sorted(categorized.items()):
        logger.info(f"  - {category_slug}: {len(apis)} APIs")

    return categorized


def generate_api_doc(
    template: Template,
    api: Dict[str, Any],
    output_file: Path
) -> None:
    """
    Generate individual API documentation file.

    Args:
        template: Jinja2 template
        api: API data dictionary
        output_file: Output file path
    """
    # Prepare template context
    context = {
        "api_id": api["api_id"],
        "api_name": api["name"],
        "category": api["category"],
        "http_method": api["http_method"],
        "url": api["url"],
        "communication_type": api["communication_type"],
        "real_tr_id": api["real_tr_id"],
        "paper_tr_id": api["paper_tr_id"],
        "has_params": api["http_method"] in ["GET", "POST"],
        "related_apis": []  # Could be enhanced with related API logic
    }

    # Render template
    content = template.render(**context)

    # Write to file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)


def generate_category_index(
    category_slug: str,
    apis: List[Dict[str, Any]],
    category_info: Dict[str, Any]
) -> str:
    """
    Generate category index content.

    Args:
        category_slug: Category slug
        apis: List of APIs in this category
        category_info: Category metadata

    Returns:
        str: Index markdown content
    """
    category_name = category_info.get("name", category_slug.replace("-", " ").title())
    category_desc = category_info.get("description", "")

    content = f"# {category_name}\n\n"
    
    if category_desc:
        content += f"{category_desc}\n\n"
    
    content += f"**Total APIs**: {len(apis)}\n\n"
    content += "---\n\n"
    content += "## API List\n\n"

    for api in sorted(apis, key=lambda x: x["name"]):
        content += f"- [{api['name']}]({api['id']}.md) - `{api['api_id']}`\n"

    content += "\n---\n\n"
    content += "[Back to API Documentation Index](../index.md)\n"

    return content


def generate_api_docs(
    categorized_apis: Dict[str, List[Dict[str, Any]]],
    categories_info: Dict[str, Any],
    phase: Optional[int] = None
) -> Dict[str, Any]:
    """
    Generate API documentation files.

    Args:
        categorized_apis: Categorized APIs dictionary
        categories_info: Categories metadata
        phase: Generation phase (1 = priority, 2 = remaining, None = all)

    Returns:
        Dict[str, Any]: Generation statistics
    """
    logger.info("Generating API documentation files...")

    # Load template
    template = load_template()

    # Filter based on phase
    if phase == 1:
        logger.info(f"Phase {phase}: Generating priority APIs only")
        filtered_apis = {
            cat: apis for cat, apis in categorized_apis.items()
            if cat in PRIORITY_CATEGORIES
        }
    elif phase == 2:
        logger.info(f"Phase {phase}: Generating remaining APIs")
        filtered_apis = {
            cat: apis for cat, apis in categorized_apis.items()
            if cat not in PRIORITY_CATEGORIES
        }
    else:
        logger.info("Generating all APIs (all phases)")
        filtered_apis = categorized_apis

    # Statistics
    stats = {
        "total_apis": 0,
        "total_categories": len(filtered_apis),
        "categories": {},
        "generated_files": []
    }

    # Build categories info lookup
    cat_info_lookup = {
        cat["id"]: cat
        for cat in categories_info.get("categories", [])
    }

    # Generate documentation for each category
    for category_slug, apis in filtered_apis.items():
        logger.info(f"Processing category: {category_slug} ({len(apis)} APIs)")

        # Create category directory
        category_dir = API_DOCS_DIR / category_slug
        category_dir.mkdir(parents=True, exist_ok=True)

        # Generate category index
        category_info = cat_info_lookup.get(category_slug, {})
        index_content = generate_category_index(category_slug, apis, category_info)
        index_file = category_dir / "index.md"

        with open(index_file, "w", encoding="utf-8") as f:
            f.write(index_content)

        stats["categories"][category_slug] = {
            "name": category_info.get("name", category_slug),
            "api_count": len(apis),
            "index_file": str(index_file.relative_to(PROJECT_ROOT))
        }

        # Generate individual API documentation
        for api in apis:
            output_file = category_dir / f"{api['id']}.md"
            generate_api_doc(template, api, output_file)

            stats["total_apis"] += 1
            stats["generated_files"].append(str(output_file.relative_to(PROJECT_ROOT)))

    logger.info(f"Generated {stats['total_apis']} API documentation files")
    logger.info(f"Documentation directory: {API_DOCS_DIR}")

    return stats


def generate_main_index(
    categorized_apis: Dict[str, List[Dict[str, Any]]],
    categories_info: Dict[str, Any]
) -> None:
    """
    Generate main API documentation index.

    Args:
        categorized_apis: Categorized APIs dictionary
        categories_info: Categories metadata
    """
    logger.info("Generating main API index...")

    # Build categories info lookup
    cat_info_lookup = {
        cat["id"]: cat
        for cat in categories_info.get("categories", [])
    }

    # Generate index content
    content = "# KIS OpenAPI Documentation\n\n"
    content += f"**Total APIs**: {sum(len(apis) for apis in categorized_apis.values())}\n\n"
    content += "---\n\n"
    content += "## Categories\n\n"

    for category_slug in sorted(categorized_apis.keys()):
        cat_info = cat_info_lookup.get(category_slug, {})
        cat_name = cat_info.get("name", category_slug.replace("-", " ").title())
        cat_desc = cat_info.get("description", "")
        api_count = len(categorized_apis[category_slug])

        content += f"### [{cat_name}](api/{category_slug}/index.md)\n\n"
        if cat_desc:
            content += f"{cat_desc}\n\n"
        content += f"**APIs**: {api_count}\n\n"

    content += "---\n\n"
    content += "## Quick Links\n\n"

    for category_slug in sorted(categorized_apis.keys()):
        cat_info = cat_info_lookup.get(category_slug, {})
        cat_name = cat_info.get("name", category_slug)
        content += f"- [{cat_name}](api/{category_slug}/index.md) ({len(categorized_apis[category_slug])} APIs)\n"

    # Write main index
    main_index_file = API_DOCS_DIR.parent / "index.md"
    main_index_file.parent.mkdir(parents=True, exist_ok=True)

    with open(main_index_file, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"Generated main API index: {main_index_file}")


def generate_api_summary(
    categorized_apis: Dict[str, List[Dict[str, Any]]],
    generation_stats: Dict[str, Any]
) -> None:
    """
    Generate API summary JSON file.

    Args:
        categorized_apis: Categorized APIs dictionary
        generation_stats: Generation statistics
    """
    logger.info("Generating API summary...")

    # Build summary
    summary = {
        "generated_at": datetime.now().isoformat(),
        "version": "1.0.0",
        "total_apis": generation_stats["total_apis"],
        "total_categories": generation_stats["total_categories"],
        "categories": []
    }

    for category_slug, category_stats in generation_stats["categories"].items():
        apis = categorized_apis.get(category_slug, [])
        
        # Count by HTTP method
        method_counts = {}
        for api in apis:
            method = api["http_method"]
            method_counts[method] = method_counts.get(method, 0) + 1

        # Count by communication type
        comm_counts = {}
        for api in apis:
            comm = api["communication_type"]
            comm_counts[comm] = comm_counts.get(comm, 0) + 1

        summary["categories"].append({
            "id": category_slug,
            "name": category_stats["name"],
            "api_count": category_stats["api_count"],
            "http_methods": method_counts,
            "communication_types": comm_counts,
            "index_file": category_stats["index_file"]
        })

    # Write summary
    API_SUMMARY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(API_SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    logger.info(f"Generated API summary: {API_SUMMARY_FILE}")


def validate_docs() -> bool:
    """
    Validate existing documentation.

    Returns:
        bool: True if validation passes
    """
    logger.info("Validating documentation...")

    # Load TR_ID mapping
    tr_id_mapping = load_tr_id_mapping()
    categorized_apis = categorize_apis(tr_id_mapping)

    # Validation results
    validation_results = {
        "total_apis": len(tr_id_mapping),
        "documented_apis": 0,
        "missing_apis": [],
        "broken_links": [],
        "errors": []
    }

    # Check each API
    for category_slug, apis in categorized_apis.items():
        for api in apis:
            doc_file = API_DOCS_DIR / category_slug / f"{api['id']}.md"
            
            if doc_file.exists():
                validation_results["documented_apis"] += 1
                
                # Check if file is not empty
                if doc_file.stat().st_size == 0:
                    validation_results["errors"].append(f"Empty file: {doc_file}")
            else:
                validation_results["missing_apis"].append({
                    "api_id": api["api_id"],
                    "expected_file": str(doc_file)
                })

    # Check category indices
    for category_slug in categorized_apis.keys():
        index_file = API_DOCS_DIR / category_slug / "index.md"
        if not index_file.exists():
            validation_results["errors"].append(f"Missing category index: {index_file}")

    # Print validation results
    logger.info(f"Validation Results:")
    logger.info(f"  Total APIs: {validation_results['total_apis']}")
    logger.info(f"  Documented APIs: {validation_results['documented_apis']}")
    logger.info(f"  Missing APIs: {len(validation_results['missing_apis'])}")
    logger.info(f"  Errors: {len(validation_results['errors'])}")

    if validation_results["missing_apis"]:
        logger.warning(f"Missing documentation for {len(validation_results['missing_apis'])} APIs:")
        for missing in validation_results["missing_apis"][:5]:
            logger.warning(f"  - {missing['api_id']}")
        if len(validation_results["missing_apis"]) > 5:
            logger.warning(f"  ... and {len(validation_results['missing_apis']) - 5} more")

    if validation_results["errors"]:
        logger.error(f"Validation errors found:")
        for error in validation_results["errors"]:
            logger.error(f"  - {error}")

    # Validation passes if all APIs are documented and no errors
    passes = (
        validation_results["documented_apis"] == validation_results["total_apis"]
        and len(validation_results["errors"]) == 0
    )

    if passes:
        logger.info("Validation PASSED")
    else:
        logger.error("Validation FAILED")

    return passes


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Generate KIS OpenAPI documentation"
    )
    parser.add_argument(
        "--phase",
        type=int,
        choices=[1, 2],
        help="Generation phase: 1 = priority APIs (~100), 2 = remaining APIs"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate existing documentation without generating"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    try:
        # Validation mode
        if args.validate:
            success = validate_docs()
            sys.exit(0 if success else 1)

        # Generation mode
        logger.info("=" * 60)
        logger.info("KIS OpenAPI Documentation Generation")
        logger.info("=" * 60)

        # Load data
        tr_id_mapping = load_tr_id_mapping()
        categories_info = load_categories()
        categorized_apis = categorize_apis(tr_id_mapping)

        # Generate documentation
        generation_stats = generate_api_docs(
            categorized_apis,
            categories_info,
            phase=args.phase
        )

        # Generate main index
        generate_main_index(categorized_apis, categories_info)

        # Generate API summary
        generate_api_summary(categorized_apis, generation_stats)

        # Validate generated docs
        logger.info("")
        logger.info("=" * 60)
        logger.info("Validating generated documentation...")
        logger.info("=" * 60)
        validate_docs()

        logger.info("")
        logger.info("=" * 60)
        logger.info("SUCCESS: Documentation generation completed!")
        logger.info("=" * 60)
        logger.info(f"Generated {generation_stats['total_apis']} API documents")
        logger.info(f"Generated {generation_stats['total_categories']} category indices")
        logger.info(f"Documentation directory: {API_DOCS_DIR}")

    except Exception as e:
        logger.error(f"ERROR: {e}")
        raise


if __name__ == "__main__":
    main()
