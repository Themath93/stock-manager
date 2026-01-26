#!/usr/bin/env python3
"""
KIS OpenAPI Documentation Validation Script

Validates generated API documentation for completeness and quality.

Usage:
    # Validate all documentation
    python scripts/validate_docs.py

    # Validate specific category
    python scripts/validate_docs.py --category domestic-stock-orders

    # Detailed validation with link checking
    python scripts/validate_docs.py --detailed

Output:
    Validation report with statistics and any issues found
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple

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
API_DOCS_DIR = PROJECT_ROOT / "docs" / "kis-openapi" / "api"

# Category slug mapping
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


def sanitize_filename(api_id: str) -> str:
    """Sanitize API ID for use as filename."""
    sanitized = re.sub(r'[^\w\-]', '-', api_id)
    sanitized = re.sub(r'-+', '-', sanitized)
    sanitized = sanitized.strip('-')
    return sanitized


def load_tr_id_mapping() -> Dict[str, Any]:
    """Load TR_ID mapping from JSON file."""
    if not TR_ID_MAPPING_FILE.exists():
        raise FileNotFoundError(f"TR_ID mapping file not found: {TR_ID_MAPPING_FILE}")

    with open(TR_ID_MAPPING_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def categorize_apis(tr_id_mapping: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Categorize APIs by their category slug."""
    categorized = {}

    for api_id, api_data in tr_id_mapping.items():
        category = api_data["category"]
        category_slug = CATEGORY_SLUGS.get(category, "other")

        if category_slug not in categorized:
            categorized[category_slug] = []

        categorized[category_slug].append({
            "id": sanitize_filename(api_id),
            "api_id": api_id,
            **api_data
        })

    return categorized


def validate_file_exists(
    file_path: Path,
    file_type: str
) -> Tuple[bool, List[str]]:
    """
    Validate that a file exists and is not empty.

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []

    if not file_path.exists():
        errors.append(f"{file_type} file missing: {file_path}")
        return False, errors

    if file_path.stat().st_size == 0:
        errors.append(f"{file_type} file is empty: {file_path}")
        return False, errors

    return True, errors


def validate_markdown_content(
    content: str,
    api_data: Dict[str, Any]
) -> List[str]:
    """
    Validate markdown content for required sections.

    Returns:
        List of validation errors
    """
    errors = []

    # Required sections
    required_sections = [
        ("## API Overview", "API Overview section"),
        ("## TR_ID Information", "TR_ID Information section"),
        ("## Endpoint", "Endpoint section"),
        ("## Request Headers", "Request Headers section"),
        ("## Response", "Response section"),
        ("## Error Handling", "Error Handling section"),
        ("## Example Usage", "Example Usage section"),
    ]

    for section_heading, section_name in required_sections:
        if section_heading not in content:
            errors.append(f"Missing section: {section_name}")

    # Validate API ID is present
    if f"`{api_data['api_id']}`" not in content:
        errors.append(f"API ID not found in content: {api_data['api_id']}")

    # Validate URL is present
    if api_data['url'] not in content:
        errors.append(f"URL not found in content: {api_data['url']}")

    # Validate HTTP method is present
    if api_data['http_method'] not in content:
        errors.append(f"HTTP method not found in content: {api_data['http_method']}")

    # Check for TR_ID values
    if api_data['real_tr_id']:
        if api_data['real_tr_id'] not in content and "N/A" not in content:
            errors.append(f"Real TR_ID not found in content: {api_data['real_tr_id']}")

    # Check for code examples
    if "```python" not in content.lower() and "```python" not in content:
        errors.append("Missing Python code example")

    return errors


def extract_links(content: str, file_path: Path) -> List[Tuple[str, int]]:
    """
    Extract markdown links from content.

    Returns:
        List of (link_url, line_number) tuples
    """
    links = []
    lines = content.split('\n')

    link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

    for line_num, line in enumerate(lines, start=1):
        for match in link_pattern.finditer(line):
            link_url = match.group(2)
            links.append((link_url, line_num))

    return links


def validate_internal_link(
    link: str,
    current_file: Path,
    documented_files: Set[Path]
) -> List[str]:
    """
    Validate an internal markdown link.

    Returns:
        List of error messages
    """
    errors = []

    # Skip external links
    if link.startswith('http://') or link.startswith('https://'):
        return errors

    # Skip anchor links
    if link.startswith('#'):
        return errors

    # Resolve relative path
    if link.startswith('../'):
        target_file = (current_file.parent / link).resolve()
    elif link.startswith('./'):
        target_file = (current_file.parent / link[2:]).resolve()
    else:
        # Same directory
        target_file = (current_file.parent / link).resolve()

    # Check if target file exists
    if target_file not in documented_files:
        errors.append(f"Broken link: {link} -> {target_file}")

    return errors


class DocumentationValidator:
    """Documentation validation handler."""

    def __init__(self, detailed: bool = False):
        self.detailed = detailed
        self.results = {
            "total_apis": 0,
            "documented_apis": 0,
            "missing_files": [],
            "empty_files": [],
            "content_errors": [],
            "broken_links": [],
            "categories": {}
        }

    def validate_category(
        self,
        category_slug: str,
        apis: List[Dict[str, Any]]
    ) -> None:
        """Validate all APIs in a category."""
        logger.info(f"Validating category: {category_slug}")

        category_results = {
            "total": len(apis),
            "documented": 0,
            "missing": [],
            "content_errors": []
        }

        for api in apis:
            doc_file = API_DOCS_DIR / category_slug / f"{api['id']}.md"
            self.results["total_apis"] += 1

            # Check file existence
            if not doc_file.exists():
                self.results["missing_files"].append(str(doc_file))
                category_results["missing"].append(api["api_id"])
                continue

            # Check file is not empty
            if doc_file.stat().st_size == 0:
                self.results["empty_files"].append(str(doc_file))
                continue

            # Read content
            try:
                with open(doc_file, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                self.results["content_errors"].append(
                    f"Failed to read {doc_file}: {e}"
                )
                continue

            # Validate content
            if self.detailed:
                content_errors = validate_markdown_content(content, api)
                if content_errors:
                    for error in content_errors:
                        self.results["content_errors"].append(
                            f"{doc_file}: {error}"
                        )
                        category_results["content_errors"].append(error)

                # Validate links
                if self.detailed:
                    links = extract_links(content, doc_file)
                    documented_files = {
                        (API_DOCS_DIR / category_slug / f"{a['id']}.md").resolve()
                        for a in apis
                    }
                    documented_files.add((API_DOCS_DIR / category_slug / "index.md").resolve())

                    for link, line_num in links:
                        link_errors = validate_internal_link(
                            link,
                            doc_file,
                            documented_files
                        )
                        for error in link_errors:
                            self.results["broken_links"].append(
                                f"{doc_file}:{line_num} - {error}"
                            )

            self.results["documented_apis"] += 1
            category_results["documented"] += 1

        self.results["categories"][category_slug] = category_results

    def validate_category_index(self, category_slug: str) -> None:
        """Validate category index file."""
        index_file = API_DOCS_DIR / category_slug / "index.md"

        if not index_file.exists():
            self.results["missing_files"].append(str(index_file))
            return

        if index_file.stat().st_size == 0:
            self.results["empty_files"].append(str(index_file))

    def print_report(self) -> None:
        """Print validation report."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("Documentation Validation Report")
        logger.info("=" * 60)

        # Overall statistics
        logger.info(f"\nOverall Statistics:")
        logger.info(f"  Total APIs: {self.results['total_apis']}")
        logger.info(f"  Documented APIs: {self.results['documented_apis']}")
        logger.info(f"  Coverage: {self.results['documented_apis'] / self.results['total_apis'] * 100:.1f}%")

        # Issues
        if self.results["missing_files"]:
            logger.error(f"\nMissing Files ({len(self.results['missing_files'])}):")
            for file in self.results["missing_files"][:10]:
                logger.error(f"  - {file}")
            if len(self.results["missing_files"]) > 10:
                logger.error(f"  ... and {len(self.results['missing_files']) - 10} more")

        if self.results["empty_files"]:
            logger.warning(f"\nEmpty Files ({len(self.results['empty_files'])}):")
            for file in self.results["empty_files"][:10]:
                logger.warning(f"  - {file}")
            if len(self.results["empty_files"]) > 10:
                logger.warning(f"  ... and {len(self.results['empty_files']) - 10} more")

        if self.results["content_errors"]:
            logger.warning(f"\nContent Errors ({len(self.results['content_errors'])}):")
            for error in self.results["content_errors"][:10]:
                logger.warning(f"  - {error}")
            if len(self.results["content_errors"]) > 10:
                logger.warning(f"  ... and {len(self.results['content_errors']) - 10} more")

        if self.results["broken_links"]:
            logger.warning(f"\nBroken Links ({len(self.results['broken_links'])}):")
            for link in self.results["broken_links"][:10]:
                logger.warning(f"  - {link}")
            if len(self.results["broken_links"]) > 10:
                logger.warning(f"  ... and {len(self.results['broken_links']) - 10} more")

        # Category breakdown
        if self.results["categories"]:
            logger.info(f"\nCategory Breakdown:")
            for category_slug, cat_results in sorted(self.results["categories"].items()):
                logger.info(f"  {category_slug}:")
                logger.info(f"    Documented: {cat_results['documented']}/{cat_results['total']}")
                if cat_results["missing"]:
                    logger.info(f"    Missing: {len(cat_results['missing'])}")
                if self.detailed and cat_results.get("content_errors"):
                    logger.info(f"    Content errors: {len(cat_results['content_errors'])}")

        # Final verdict
        total_issues = (
            len(self.results["missing_files"]) +
            len(self.results["empty_files"]) +
            len(self.results["content_errors"]) +
            len(self.results["broken_links"])
        )

        logger.info("")
        logger.info("=" * 60)

        if total_issues == 0:
            logger.info("Validation PASSED: All documentation is complete and valid")
        else:
            logger.error(f"Validation FAILED: {total_issues} issues found")

        logger.info("=" * 60)


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Validate KIS OpenAPI documentation"
    )
    parser.add_argument(
        "--category",
        type=str,
        help="Validate specific category only"
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Enable detailed validation (content checks, link validation)"
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
        # Load data
        tr_id_mapping = load_tr_id_mapping()
        categorized_apis = categorize_apis(tr_id_mapping)

        # Create validator
        validator = DocumentationValidator(detailed=args.detailed)

        # Validate categories
        if args.category:
            if args.category not in categorized_apis:
                logger.error(f"Category not found: {args.category}")
                logger.info(f"Available categories: {', '.join(categorized_apis.keys())}")
                sys.exit(1)

            validator.validate_category(args.category, categorized_apis[args.category])
            validator.validate_category_index(args.category)
        else:
            for category_slug, apis in categorized_apis.items():
                validator.validate_category(category_slug, apis)
                validator.validate_category_index(category_slug)

        # Print report
        validator.print_report()

        # Exit with appropriate code
        total_issues = (
            len(validator.results["missing_files"]) +
            len(validator.results["empty_files"]) +
            len(validator.results["content_errors"]) +
            len(validator.results["broken_links"])
        )

        sys.exit(0 if total_issues == 0 else 1)

    except Exception as e:
        logger.error(f"ERROR: {e}")
        raise


if __name__ == "__main__":
    main()
