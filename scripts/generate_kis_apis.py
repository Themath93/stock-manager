#!/usr/bin/env python3
"""
Generate KIS Domestic Stock API Functions from Markdown Documentation

This script reads KIS OpenAPI markdown documentation files and generates
Python function stubs with Google-style docstrings.
"""

import re
from pathlib import Path
from typing import Dict, Optional


def parse_markdown_file(file_path: Path) -> Optional[Dict]:
    """Parse a KIS API markdown file and extract API information.

    Args:
        file_path: Path to the markdown file.

    Returns:
        Dictionary containing parsed API information or None if parsing fails.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

    # Extract API ID
    api_id_match = re.search(r'\*\*API ID\*\*:\s*`([^`]+)`', content)
    api_id = api_id_match.group(1) if api_id_match else ""

    # Extract title (first heading)
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else ""

    # Extract URL
    url_match = re.search(r'\*\*URL\*\*:\s*`([^`]+)`', content)
    url = url_match.group(1) if url_match else ""

    # Extract HTTP method
    method_match = re.search(r'\*\*HTTP Method\*\*:\s*(\w+)', content)
    method = method_match.group(1) if method_match else "GET"

    # Extract TR_IDs
    real_tr_id_match = re.search(
        r'\|\s*Real Trading\s*\|\s*`([^`]+)`\s*\|', content
    )
    paper_tr_id_match = re.search(
        r'\|\s*Paper Trading\s*\|\s*`([^`]+)`\s*\|', content
    )

    real_tr_id = real_tr_id_match.group(1) if real_tr_id_match else ""
    paper_tr_id = (
        paper_tr_id_match.group(1)
        if paper_tr_id_match and paper_tr_id_match.group(1) != "N/A"
        else "Not Supported"
    )

    # Extract category
    category_match = re.search(r'\*\*Category\*\*:\s*\[([^\]]+)\]', content)
    category = category_match.group(1) if category_match else ""

    # Extract communication type
    comm_type_match = re.search(r'\*\*Communication Type\*\*:\s*(\w+)', content)
    comm_type = comm_type_match.group(1) if comm_type_match else "REST"

    return {
        "api_id": api_id,
        "title": title,
        "url": url,
        "method": method,
        "real_tr_id": real_tr_id,
        "paper_tr_id": paper_tr_id,
        "category": category,
        "comm_type": comm_type,
        "file_path": str(file_path),
    }


def generate_function_name(title: str, url: str) -> str:
    """Generate a Python function name from API title or URL.

    Args:
        title: Korean title of the API.
        url: API endpoint URL.

    Returns:
        Snake_case function name.
    """
    # Extract meaningful part from URL
    url_parts = url.strip("/").split("/")
    if len(url_parts) > 0:
        last_part = url_parts[-1]
        # Convert to snake_case
        name = re.sub(r"[-/]", "_", last_part)
        name = re.sub(r"[^a-zA-Z0-9_]", "", name)
        if name:
            return f"get_{name}" if not name.startswith("get") else name

    # Fallback: generate from URL structure
    name = url.replace("/", "_").replace("-", "_")
    name = re.sub(r"^_+", "", name)
    name = re.sub(r"_+$", "", name)
    return f"get_{name}" if not name.startswith("get") else name


def generate_python_function(api_info: Dict) -> str:
    """Generate a Python function with docstring from API information.

    Args:
        api_info: Dictionary containing parsed API information.

    Returns:
        Python function code as string.
    """
    func_name = generate_function_name(api_info["title"], api_info["url"])

    # Build docstring
    docstring_lines = [
        f'{api_info["title"]}',
        "",
        f"API ID: {api_info['api_id']}",
        f"Category: {api_info['category']}",
        "",
        f"This API provides {api_info['title'].lower()} for",
        f"{api_info['category']}.",
        "",
        "Args:",
        "    is_paper_trading: If True, use paper trading TR_ID.",
    ]

    if api_info["paper_tr_id"] == "Not Supported":
        docstring_lines.append("                         Note: Paper trading is not supported for this API.")

    docstring_lines.extend([
        "    params: Optional dictionary of additional query parameters.",
        "",
        "Returns:",
        f"    Dict[str, Any]: API response containing {api_info['title'].lower()} data.",
    ])

    if api_info["paper_tr_id"] == "Not Supported":
        docstring_lines.append("    Raises ValueError: If paper trading is requested.")

    docstring_lines.extend([
        "",
        "Examples:",
        f'    >>> # {("Real" if not api_info["paper_tr_id"] == "Not Supported" else "Paper trading only")} trading example',
        f'    >>> response = {func_name}(is_paper_trading={api_info["paper_tr_id"] != "Not Supported"})',
        '    >>> if response.get("rt_cd") == "0":',
        '    ...     print("Success:", response.get("output"))',
        "",
    ])

    if api_info["paper_tr_id"] == "Not Supported":
        docstring_lines.extend([
            "Note:",
            "    Paper trading is not supported for this API.",
            "    Only real trading is available.",
        ])

    docstring_lines.extend([
        "",
        "TR_ID:",
        f'    Real Trading: {api_info["real_tr_id"]}',
        f'    Paper Trading: {api_info["paper_tr_id"]}',
    ])

    docstring = '    """\n' + "\n".join(docstring_lines) + '\n    """'

    # Build function
    func_lines = [
        "",
        f"def {func_name}(",
        "    is_paper_trading: bool = False,",
        "    params: Optional[Dict[str, Any]] = None,",
        ") -> Dict[str, Any]:",
        docstring,
        "    raise NotImplementedError(",
        "        \"This function requires KISRestClient implementation\"",
        "    )",
        "",
    ]

    return "\n".join(func_lines)


def generate_module_header(category_name: str, api_count: int) -> str:
    """Generate the module header with docstring.

    Args:
        category_name: Name of the API category.
        api_count: Number of APIs in this module.

    Returns:
        Module header as string.
    """
    return f'''"""
Domestic Stock {category_name} API Functions

This module provides functions for interacting with KIS OpenAPI
domestic stock {category_name.lower()} endpoints.

Total APIs: {api_count}
"""

from typing import Any, Dict, Optional

'''


def process_category(
    docs_dir: Path,
    output_file: Path,
    category_name: str
) -> int:
    """Process all markdown files in a category and generate Python module.

    Args:
        docs_dir: Directory containing markdown documentation files.
        output_file: Path to output Python file.
        category_name: Name of the category for documentation.

    Returns:
        Number of APIs processed.
    """
    # Find all markdown files (excluding index.md)
    md_files = sorted(docs_dir.glob("*.md"))
    md_files = [f for f in md_files if f.name != "index.md"]

    if not md_files:
        print(f"  No markdown files found in {docs_dir}")
        return 0

    # Parse all files
    api_infos = []
    for md_file in md_files:
        api_info = parse_markdown_file(md_file)
        if api_info and api_info["url"]:  # Only include if URL exists
            api_infos.append(api_info)

    if not api_infos:
        print(f"  No valid API information found in {docs_dir}")
        return 0

    # Generate module
    lines = [generate_module_header(category_name, len(api_infos))]

    for api_info in sorted(api_infos, key=lambda x: x["api_id"]):
        func_code = generate_python_function(api_info)
        lines.append(func_code)

    # Write to file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("\n".join(lines), encoding="utf-8")

    print(f"  Generated {len(api_infos)} API functions for {category_name}")
    return len(api_infos)


def main():
    """Main function to generate all API modules."""
    # Define paths
    base_dir = Path("/Users/byungwoyoon/Desktop/Projects/stock-manager")
    docs_base = base_dir / "docs/kis-openapi/api"
    output_base = (
        base_dir / "stock_manager/adapters/broker/kis/apis/domestic_stock"
    )

    # Define categories
    categories = [
        ("domestic-stock-analysis", "elw", "Analysis"),
        ("domestic-stock-elw", "elw", "ELW"),
        ("domestic-stock-info", "info", "Info"),
        ("domestic-stock-ranking", "ranking", "Ranking"),
        ("domestic-stock-sector", "sector", "Sector"),
        ("domestic-stock-realtime", "realtime", "Realtime"),
    ]

    total_apis = 0

    print("Generating KIS Domestic Stock API modules...")
    print()

    for docs_subdir, output_file, category_name in categories:
        docs_dir = docs_base / docs_subdir
        output_path = output_base / f"{output_file}.py"

        print(f"Processing {category_name}...")
        count = process_category(docs_dir, output_path, category_name)
        total_apis += count

    print()
    print(f"Complete! Generated {total_apis} API functions across 6 modules.")
    print(f"Output directory: {output_base}")


if __name__ == "__main__":
    main()
