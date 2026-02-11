#!/usr/bin/env python
"""Fix script for GREEN phase: Add 'await' to domestic_stock API functions.

This script fixes the bug detected by test_domestic_stock_uses_await:
- Adds 'await' before all client.make_request() calls in domestic_stock modules
- Ensures consistency with overseas_stock (which correctly uses await)

TDD Cycle:
- RED: test_domestic_stock_uses_await FAILS (documents bug)
- GREEN: This script fixes the code to make tests PASS
- REFACTOR: Future improvements to async patterns

Usage:
    python scripts/fix_domestic_await.py
"""

import ast
import re
from pathlib import Path


def add_await_to_make_request(file_path: Path) -> bool:
    """Add 'await' keyword before client.make_request() calls.

    Args:
        file_path: Path to Python file to fix

    Returns:
        True if file was modified, False otherwise
    """
    try:
        content = file_path.read_text()
        original_content = content

        # Pattern: Find lines with client.make_request( or response = client.make_request(
        # but NOT already prefixed with await
        patterns = [
            # Pattern 1: data = client.make_request( -> data = await client.make_request(
            r'(\s+)(\w+\s*=\s*)client\.make_request\(',
            # Pattern 2: return client.make_request( -> return await client.make_request(
            r'(\s+)(return\s+)client\.make_request\(',
            # Pattern 3: response = client.make_request( -> response = await client.make_request(
            r'(\s+)(response\s*=\s*)client\.make_request\(',
        ]

        for pattern in patterns:
            # Check if line doesn't already have 'await' before it
            def replace_func(match):
                indent = match.group(1)
                prefix = match.group(2) if len(match.groups()) > 1 else ""
                # Only replace if 'await' is not already present
                full_line_start = content[max(0, match.start() - 50):match.start()]
                if 'await' not in full_line_start:
                    return f'{indent}{prefix}await client.make_request('
                return match.group(0)

            content = re.sub(pattern, replace_func, content)

        # More robust AST-based approach
        try:
            tree = ast.parse(content)
            lines = content.split('\n')
            modified_lines = []

            for line in lines:
                modified_lines.append(line)

            # Look for client.make_request calls in the AST
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        if node.func.attr == 'make_request':
                            line_no = node.lineno - 1
                            line = lines[line_no]

                            # Check if this call already has await
                            has_await = False
                            for parent in ast.walk(tree):
                                if isinstance(parent, ast.Await):
                                    if any(node is child for child in ast.walk(parent)):
                                        has_await = True
                                        break

                            # Add await if not present and not in a comment
                            if not has_await:
                                # Check if 'await' is already on this line
                                if 'await' not in line:
                                    # Add await before the call
                                    # Find the position of client.make_request
                                    call_start = line.find('client.make_request')
                                    if call_start > 0:
                                        # Add await before the call
                                        new_line = line[:call_start] + 'await ' + line[call_start:]
                                        lines[line_no] = new_line

            content = '\n'.join(lines)

        except (SyntaxError, Exception):
            # If AST parsing fails, use regex results
            pass

        if content != original_content:
            file_path.write_text(content)
            return True

        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main() -> None:
    """Main entry point."""
    # Find all domestic_stock API files
    kis_path = Path(__file__).parent.parent / "stock_manager" / "adapters" / "broker" / "kis" / "apis"
    domestic_path = kis_path / "domestic_stock"

    if not domestic_path.exists():
        print(f"Error: {domestic_path} not found")
        return

    # Process all .py files except __init__.py
    files = [f for f in domestic_path.glob("*.py") if f.name != "__init__.py"]

    print(f"GREEN PHASE: Fixing {len(files)} domestic_stock API files...")
    print("=" * 60)

    modified_count = 0
    for file_path in sorted(files):
        if add_await_to_make_request(file_path):
            print(f"✓ Fixed: {file_path.name}")
            modified_count += 1
        else:
            print(f"  (already correct): {file_path.name}")

    print("=" * 60)
    print(f"\nModified {modified_count} files")

    if modified_count > 0:
        print("\nNext steps:")
        print("1. Run tests: pytest tests/unit/test_async_consistency.py -v")
        print("2. All tests should now PASS (GREEN phase)")
        print("3. Review and commit changes")


if __name__ == "__main__":
    main()
