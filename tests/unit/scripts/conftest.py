"""
pytest configuration for scripts tests
"""
import sys
import tempfile
from pathlib import Path

import pytest

# Add scripts directory to path for coverage
scripts_dir = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


@pytest.fixture
def temp_docs_dir():
    """Create temporary documentation directory structure"""
    with tempfile.TemporaryDirectory() as tmpdir:
        docs_dir = Path(tmpdir) / "api"
        docs_dir.mkdir(parents=True, exist_ok=True)

        # Create category directory
        oauth_dir = docs_dir / "oauth"
        oauth_dir.mkdir(parents=True, exist_ok=True)

        # Create valid API doc
        api_file = oauth_dir / "인증-001.md"
        valid_content = """
# API Documentation

## API Overview

API ID: `인증-001`

## TR_ID Information

TR_ID info here.

## Endpoint

Endpoint info here.

## Request Headers

Headers here.

## Response

Response here.

## Error Handling

Error handling here.

## Example Usage

```python
def example():
    pass
```
"""
        api_file.write_text(valid_content, encoding='utf-8')

        # Create category index
        index_file = oauth_dir / "index.md"
        index_file.write_text("# OAuth\n\nAPIs here", encoding='utf-8')

        yield docs_dir


@pytest.fixture
def sample_apis():
    """Sample API data"""
    return [
        {
            "id": "인증-001",
            "api_id": "인증-001",
            "name": "접근토큰발급(P)",
            "url": "/oauth2/tokenP",
            "http_method": "POST",
            "real_tr_id": "",
            "category": "OAuth인증"
        }
    ]
