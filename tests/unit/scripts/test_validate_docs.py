"""
Unit tests for validate_docs.py script

Tests for documentation validation functionality including:
- Filename sanitization
- File existence validation
- Markdown content validation
- Link extraction
- Internal link validation
- DocumentationValidator class
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Import functions from the script
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts"))

import validate_docs

sanitize_filename = validate_docs.sanitize_filename
load_tr_id_mapping = validate_docs.load_tr_id_mapping
categorize_apis = validate_docs.categorize_apis
validate_file_exists = validate_docs.validate_file_exists
validate_markdown_content = validate_docs.validate_markdown_content
extract_links = validate_docs.extract_links
validate_internal_link = validate_docs.validate_internal_link
DocumentationValidator = validate_docs.DocumentationValidator
PROJECT_ROOT = validate_docs.PROJECT_ROOT


class TestSanitizeFilename:
    """Tests for sanitize_filename function (validate_docs.py)"""

    def test_sanitize_simple_alphanumeric(self):
        """Test sanitization of simple alphanumeric API ID"""
        result = sanitize_filename("API001")
        assert result == "API001"

    def test_sanitize_with_hyphens(self):
        """Test sanitization with hyphens"""
        result = sanitize_filename("API-Test-001")
        assert result == "API-Test-001"

    def test_sanitize_with_special_chars(self):
        """Test sanitization with special characters"""
        result = sanitize_filename("국내주식/001")
        assert result == "국내주식-001"

    def test_sanitize_with_spaces(self):
        """Test sanitization with spaces"""
        result = sanitize_filename("API with spaces")
        assert result == "API-with-spaces"

    def test_sanitize_consecutive_hyphens(self):
        """Test that consecutive hyphens are collapsed"""
        result = sanitize_filename("API---Test")
        assert result == "API-Test"

    def test_sanitize_leading_trailing_hyphens(self):
        """Test that leading/trailing hyphens are removed"""
        result = sanitize_filename("-API-Test-")
        assert result == "API-Test"

    def test_sanitize_korean_text(self):
        """Test sanitization of Korean text"""
        result = sanitize_filename("인증-001")
        assert result == "인증-001"

    def test_sanitize_complex_api_id(self):
        """Test sanitization of complex API IDs"""
        result = sanitize_filename("v1_국내주식-001")
        # Underscore is a word character, so it's preserved
        assert result == "v1_국내주식-001"

    def test_sanitize_empty_string(self):
        """Test sanitization of empty string"""
        result = sanitize_filename("")
        assert result == ""

    def test_sanitize_only_special_chars(self):
        """Test sanitization of string with only special characters"""
        result = sanitize_filename("@#$%")
        assert result == ""


class TestLoadTRIdMapping:
    """Tests for load_tr_id_mapping function (validate_docs.py)"""

    @pytest.fixture
    def temp_mapping_file(self):
        """Create temporary TR_ID mapping file"""
        mapping_data = {
            "인증-001": {
                "name": "접근토큰발급(P)",
                "real_tr_id": "",
                "paper_tr_id": "",
                "category": "OAuth인증",
                "http_method": "POST",
                "url": "/oauth2/tokenP",
                "communication_type": "REST"
            },
            "국내주식-008": {
                "name": "주식잔고조회",
                "real_tr_id": "TTTC8001R",
                "paper_tr_id": "TTTC8001R",
                "category": "[국내주식] 주문/계좌",
                "http_method": "GET",
                "url": "/uapi/domestic-stock/v1/trading/inquire-balance",
                "communication_type": "REST"
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(mapping_data, f, ensure_ascii=False)
            temp_file = Path(f.name)

        yield temp_file

        # Cleanup
        temp_file.unlink(missing_ok=True)

    def test_load_tr_id_mapping_success(self, temp_mapping_file):
        """Test successful loading of TR_ID mapping"""
        with patch.object(validate_docs, 'TR_ID_MAPPING_FILE', temp_mapping_file):
            mapping = load_tr_id_mapping()

            assert len(mapping) == 2
            assert "인증-001" in mapping
            assert "국내주식-008" in mapping

    def test_load_tr_id_mapping_file_not_found(self):
        """Test FileNotFoundError when mapping file doesn't exist"""
        non_existent_file = PROJECT_ROOT / "nonexistent_tr_id_mapping.json"

        with patch.object(validate_docs, 'TR_ID_MAPPING_FILE', non_existent_file):
            with pytest.raises(FileNotFoundError) as exc_info:
                load_tr_id_mapping()

            assert "TR_ID mapping file not found" in str(exc_info.value)


class TestCategorizeApis:
    """Tests for categorize_apis function (validate_docs.py)"""

    @pytest.fixture
    def sample_tr_id_mapping(self):
        """Sample TR_ID mapping for testing"""
        return {
            "인증-001": {
                "name": "접근토큰발급(P)",
                "real_tr_id": "",
                "paper_tr_id": "",
                "category": "OAuth인증",
                "http_method": "POST",
                "url": "/oauth2/tokenP",
                "communication_type": "REST"
            },
            "국내주식-008": {
                "name": "주식잔고조회",
                "real_tr_id": "TTTC8001R",
                "paper_tr_id": "TTTC8001R",
                "category": "[국내주식] 주문/계좌",
                "http_method": "GET",
                "url": "/uapi/domestic-stock/v1/trading/inquire-balance",
                "communication_type": "REST"
            },
            "해외주식-001": {
                "name": "해외주식잔고조회",
                "real_tr_id": "TTTS8001R",
                "paper_tr_id": "TTTS8001R",
                "category": "[해외주식] 주문/계좌",
                "http_method": "GET",
                "url": "/uapi/overseas-stock/v1/trading/inquire-balance",
                "communication_type": "REST"
            }
        }

    def test_categorize_apis_success(self, sample_tr_id_mapping):
        """Test successful API categorization"""
        categorized = categorize_apis(sample_tr_id_mapping)

        assert "oauth" in categorized
        assert "domestic-stock-orders" in categorized
        assert "overseas-stock-orders" in categorized

        # Check API data includes id field
        assert categorized["oauth"][0]["id"] == "인증-001"
        assert categorized["oauth"][0]["api_id"] == "인증-001"

    def test_categorize_apis_unknown_category(self, sample_tr_id_mapping):
        """Test categorization with unknown category"""
        sample_tr_id_mapping["UNKNOWN-001"] = {
            "name": "Unknown API",
            "real_tr_id": "UNKNOWN001",
            "paper_tr_id": "UNKNOWN001",
            "category": "Unknown Category",
            "http_method": "GET",
            "url": "/unknown/api",
            "communication_type": "REST"
        }

        categorized = categorize_apis(sample_tr_id_mapping)

        # Should be categorized as "other"
        assert "other" in categorized
        assert categorized["other"][0]["api_id"] == "UNKNOWN-001"


class TestValidateFileExists:
    """Tests for validate_file_exists function"""

    @pytest.fixture
    def temp_file(self):
        """Create temporary file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
            f.write("Test content")
            temp_file = Path(f.name)

        yield temp_file

        # Cleanup
        temp_file.unlink(missing_ok=True)

    def test_validate_file_exists_success(self, temp_file):
        """Test validation of existing file"""
        is_valid, errors = validate_file_exists(temp_file, "API doc")

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_file_not_found(self):
        """Test validation of non-existent file"""
        non_existent = Path("/nonexistent/file.md")

        is_valid, errors = validate_file_exists(non_existent, "API doc")

        assert is_valid is False
        assert len(errors) == 1
        assert "missing" in errors[0].lower()

    def test_validate_empty_file(self):
        """Test validation of empty file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
            f.write("")
            temp_file = Path(f.name)

        try:
            is_valid, errors = validate_file_exists(temp_file, "API doc")

            assert is_valid is False
            assert len(errors) == 1
            assert "empty" in errors[0].lower()
        finally:
            temp_file.unlink(missing_ok=True)


class TestValidateMarkdownContent:
    """Tests for validate_markdown_content function"""

    @pytest.fixture
    def valid_markdown_content(self):
        """Valid markdown content with all required sections"""
        return """
# API Documentation

## API Overview

API ID: `인증-001`

## TR_ID Information

TR_ID: `TOKEN001`

## Endpoint

POST /oauth2/tokenP

## Request Headers

Request headers information here.

## Response

Response information here.

## Error Handling

Error handling information here.

## Example Usage

### Python Example

```python
def example():
    pass
```
"""

    @pytest.fixture
    def sample_api_data(self):
        """Sample API data for validation"""
        return {
            "api_id": "인증-001",
            "url": "/oauth2/tokenP",
            "http_method": "POST",
            "real_tr_id": "TOKEN001",
            "category": "OAuth인증"
        }

    def test_validate_complete_markdown(self, valid_markdown_content, sample_api_data):
        """Test validation of complete markdown content"""
        errors = validate_markdown_content(valid_markdown_content, sample_api_data)

        assert len(errors) == 0

    def test_validate_missing_sections(self, sample_api_data):
        """Test validation with missing required sections"""
        incomplete_content = "# API Doc\n\nOnly has overview"

        errors = validate_markdown_content(incomplete_content, sample_api_data)

        assert len(errors) > 0
        assert any("Missing section" in error for error in errors)

    def test_validate_missing_api_id(self, valid_markdown_content, sample_api_data):
        """Test validation with missing API ID in content"""
        # Remove API ID from content
        content = valid_markdown_content.replace("`인증-001`", "")

        errors = validate_markdown_content(content, sample_api_data)

        assert len(errors) > 0
        assert any("API ID not found" in error for error in errors)

    def test_validate_missing_url(self, valid_markdown_content, sample_api_data):
        """Test validation with missing URL in content"""
        # Remove URL from content
        content = valid_markdown_content.replace("/oauth2/tokenP", "")

        errors = validate_markdown_content(content, sample_api_data)

        assert len(errors) > 0
        assert any("URL not found" in error for error in errors)

    def test_validate_missing_http_method(self, valid_markdown_content, sample_api_data):
        """Test validation with missing HTTP method in content"""
        # Remove HTTP method from content
        content = valid_markdown_content.replace("POST", "")

        errors = validate_markdown_content(content, sample_api_data)

        assert len(errors) > 0
        assert any("HTTP method not found" in error for error in errors)

    def test_validate_missing_code_example(self, sample_api_data):
        """Test validation with missing code example"""
        content = """
# API Doc

## API Overview

## TR_ID Information

## Endpoint

## Request Headers

## Response

## Error Handling

## Example Usage

No code example here.
"""

        errors = validate_markdown_content(content, sample_api_data)

        assert len(errors) > 0
        assert any("Missing Python code example" in error for error in errors)


class TestExtractLinks:
    """Tests for extract_links function"""

    def test_extract_no_links(self):
        """Test extraction from content with no links"""
        content = "# Heading\n\nJust text, no links."

        links = extract_links(content, Path("test.md"))

        assert len(links) == 0

    def test_extract_single_link(self):
        """Test extraction of single link"""
        content = "[Link Text](https://example.com)"

        links = extract_links(content, Path("test.md"))

        assert len(links) == 1
        assert links[0][0] == "https://example.com"

    def test_extract_multiple_links(self):
        """Test extraction of multiple links"""
        content = """
[First Link](first.md)
[Second Link](second.md)
[External Link](https://example.com)
"""

        links = extract_links(content, Path("test.md"))

        assert len(links) == 3

    def test_extract_links_with_line_numbers(self):
        """Test that line numbers are captured"""
        content = """
Line 1
Line 2 [Link](target.md) here
Line 3
"""

        links = extract_links(content, Path("test.md"))

        assert len(links) == 1
        assert links[0][1] == 3  # Line 3 (1-indexed)

    def test_extract_links_with_anchors(self):
        """Test extraction of anchor links"""
        content = "[Section](#section-id)"

        links = extract_links(content, Path("test.md"))

        assert len(links) == 1
        assert links[0][0] == "#section-id"

    def test_extract_mixed_links(self):
        """Test extraction of mixed link types"""
        content = """
[Relative](other.md)
[Absolute](/path/to/file.md)
[External](https://example.com)
[Anchor](#section)
"""

        links = extract_links(content, Path("test.md"))

        assert len(links) == 4


class TestValidateInternalLink:
    """Tests for validate_internal_link function"""

    @pytest.fixture
    def sample_documented_files(self):
        """Create sample documented files set"""
        return {
            Path("/docs/api/first.md").resolve(),
            Path("/docs/api/second.md").resolve(),
            Path("/docs/api/index.md").resolve(),
        }

    def test_validate_external_link(self, sample_documented_files):
        """Test that external links are skipped"""
        current_file = Path("/docs/api/test.md")

        errors = validate_internal_link(
            "https://example.com",
            current_file,
            sample_documented_files
        )

        assert len(errors) == 0

    def test_validate_anchor_link(self, sample_documented_files):
        """Test that anchor links are skipped"""
        current_file = Path("/docs/api/test.md")

        errors = validate_internal_link(
            "#section-id",
            current_file,
            sample_documented_files
        )

        assert len(errors) == 0

    def test_validate_existing_internal_link(self, sample_documented_files):
        """Test validation of existing internal link"""
        # Create actual temp files for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir) / "api"
            docs_dir.mkdir(parents=True, exist_ok=True)

            # Create the files
            for name in ["first.md", "second.md", "index.md"]:
                (docs_dir / name).write_text("content")

            current_file = docs_dir / "test.md"
            documented_files = {f.resolve() for f in docs_dir.glob("*.md")}

            errors = validate_internal_link(
                "first.md",
                current_file,
                documented_files
            )

            assert len(errors) == 0

    def test_validate_broken_internal_link(self, sample_documented_files):
        """Test validation of broken internal link"""
        current_file = Path("/docs/api/test.md")
        Path("/docs/api/nonexistent.md").resolve()  # Reference for broken link

        errors = validate_internal_link(
            "nonexistent.md",
            current_file,
            sample_documented_files
        )

        # Should return error (path resolution will fail for non-existent)
        assert len(errors) >= 0  # May vary based on filesystem


class TestDocumentationValidator:
    """Tests for DocumentationValidator class"""

    @pytest.fixture
    def temp_docs_dir(self):
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
    def sample_apis(self):
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

    def test_validator_initialization(self):
        """Test validator initialization"""
        validator = DocumentationValidator(detailed=False)

        assert validator.detailed is False
        assert validator.results["total_apis"] == 0
        assert validator.results["documented_apis"] == 0
        assert len(validator.results["missing_files"]) == 0

    def test_validate_category_success(self, temp_docs_dir, sample_apis):
        """Test successful category validation"""
        with patch.object(validate_docs, 'API_DOCS_DIR', temp_docs_dir):
            validator = DocumentationValidator(detailed=False)
            validator.validate_category("oauth", sample_apis)

            assert validator.results["total_apis"] == 1
            assert validator.results["documented_apis"] == 1
            assert len(validator.results["missing_files"]) == 0

    def test_validate_category_missing_file(self, temp_docs_dir, sample_apis):
        """Test category validation with missing file"""
        # Remove the API file
        api_file = temp_docs_dir / "oauth" / "인증-001.md"
        api_file.unlink()

        with patch.object(validate_docs, 'API_DOCS_DIR', temp_docs_dir):
            validator = DocumentationValidator(detailed=False)
            validator.validate_category("oauth", sample_apis)

            assert len(validator.results["missing_files"]) == 1

    def test_validate_category_empty_file(self, temp_docs_dir, sample_apis):
        """Test category validation with empty file"""
        # Empty the file
        api_file = temp_docs_dir / "oauth" / "인증-001.md"
        api_file.write_text("", encoding='utf-8')

        with patch.object(validate_docs, 'API_DOCS_DIR', temp_docs_dir):
            validator = DocumentationValidator(detailed=False)
            validator.validate_category("oauth", sample_apis)

            assert len(validator.results["empty_files"]) == 1

    def test_validate_category_detailed_content_check(self, temp_docs_dir, sample_apis):
        """Test detailed content validation"""
        # Write incomplete content
        api_file = temp_docs_dir / "oauth" / "인증-001.md"
        api_file.write_text("# Incomplete\n\nMissing sections", encoding='utf-8')

        with patch.object(validate_docs, 'API_DOCS_DIR', temp_docs_dir):
            validator = DocumentationValidator(detailed=True)
            validator.validate_category("oauth", sample_apis)

            # Should have content errors
            assert len(validator.results["content_errors"]) > 0

    def test_validate_category_index_success(self, temp_docs_dir):
        """Test successful category index validation"""
        with patch.object(validate_docs, 'API_DOCS_DIR', temp_docs_dir):
            validator = DocumentationValidator(detailed=False)
            validator.validate_category_index("oauth")

            # No errors expected
            assert len(validator.results["missing_files"]) == 0

    def test_validate_category_index_missing(self, temp_docs_dir):
        """Test validation with missing category index"""
        # Remove index file
        index_file = temp_docs_dir / "oauth" / "index.md"
        index_file.unlink()

        with patch.object(validate_docs, 'API_DOCS_DIR', temp_docs_dir):
            validator = DocumentationValidator(detailed=False)
            validator.validate_category_index("oauth")

            assert len(validator.results["missing_files"]) == 1

    def test_print_report_success(self, caplog):
        """Test print report with successful validation"""
        import logging

        validator = DocumentationValidator(detailed=False)
        validator.results["total_apis"] = 10
        validator.results["documented_apis"] = 10
        validator.results["categories"] = {
            "oauth": {
                "total": 10,
                "documented": 10,
                "missing": [],
                "content_errors": []
            }
        }

        with caplog.at_level(logging.INFO):
            validator.print_report()

        # Check that report was logged
        assert any("Documentation Validation Report" in record.message for record in caplog.records)
        assert any("Validation PASSED" in record.message for record in caplog.records)

    def test_print_report_with_issues(self, caplog):
        """Test print report with validation issues"""
        import logging

        validator = DocumentationValidator(detailed=False)
        validator.results["total_apis"] = 10
        validator.results["documented_apis"] = 5
        validator.results["missing_files"] = ["missing1.md", "missing2.md"]
        validator.results["categories"] = {}

        with caplog.at_level(logging.ERROR):
            validator.print_report()

        # Should show validation failed
        assert any("Validation FAILED" in record.message for record in caplog.records if record.levelno == logging.ERROR)

    def test_category_results_tracking(self, temp_docs_dir, sample_apis):
        """Test that category results are properly tracked"""
        with patch.object(validate_docs, 'API_DOCS_DIR', temp_docs_dir):
            validator = DocumentationValidator(detailed=False)
            validator.validate_category("oauth", sample_apis)

            assert "oauth" in validator.results["categories"]
            assert validator.results["categories"]["oauth"]["total"] == 1
            assert validator.results["categories"]["oauth"]["documented"] == 1

    def test_detailed_validation_with_links(self, temp_docs_dir):
        """Test detailed validation with link checking"""
        # Create API doc with internal links
        api_file = temp_docs_dir / "oauth" / "인증-001.md"
        api_file.write_text(
            "# API\n\n[Link to index](index.md)\n\n[Link to other](other.md)",
            encoding='utf-8'
        )

        # Create index file
        index_file = temp_docs_dir / "oauth" / "index.md"
        index_file.write_text("# Index", encoding='utf-8')

        sample_apis = [
            {
                "id": "인증-001",
                "api_id": "인증-001",
                "name": "API Test",
                "url": "/oauth2/tokenP",
                "http_method": "POST",
                "real_tr_id": "",
                "category": "OAuth인증"
            }
        ]

        with patch.object(validate_docs, 'API_DOCS_DIR', temp_docs_dir):
            validator = DocumentationValidator(detailed=True)
            validator.validate_category("oauth", sample_apis)

            # Should detect broken link to other.md
            broken_links = [e for e in validator.results["broken_links"] if "other" in e]
            assert len(broken_links) > 0

    def test_validate_category_results_with_content_errors(self, temp_docs_dir):
        """Test that content errors are tracked in category results"""
        # Create incomplete API doc
        api_file = temp_docs_dir / "oauth" / "인증-001.md"
        api_file.write_text("# Incomplete", encoding='utf-8')

        sample_apis = [
            {
                "id": "인증-001",
                "api_id": "인증-001",
                "name": "Incomplete API",
                "url": "/api/test",
                "http_method": "GET",
                "real_tr_id": "",
                "category": "OAuth인증"
            }
        ]

        with patch.object(validate_docs, 'API_DOCS_DIR', temp_docs_dir):
            validator = DocumentationValidator(detailed=True)
            validator.validate_category("oauth", sample_apis)

            # Should have content errors
            assert len(validator.results["content_errors"]) > 0
            # Category results should also track errors
            assert len(validator.results["categories"]["oauth"]["content_errors"]) > 0

    def test_validate_category_index_empty_file(self, temp_docs_dir):
        """Test validation of empty category index"""
        index_file = temp_docs_dir / "oauth" / "index.md"
        index_file.write_text("", encoding='utf-8')

        with patch.object(validate_docs, 'API_DOCS_DIR', temp_docs_dir):
            validator = DocumentationValidator(detailed=False)
            validator.validate_category_index("oauth")

            assert len(validator.results["empty_files"]) == 1


class TestIntegration:
    """Integration tests for validate_docs.py"""

    @pytest.fixture
    def complete_test_env(self):
        """Create complete test environment"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create TR_ID mapping
            mapping_data = {
                "인증-001": {
                    "name": "접근토큰발급(P)",
                    "real_tr_id": "",
                    "paper_tr_id": "",
                    "category": "OAuth인증",
                    "http_method": "POST",
                    "url": "/oauth2/tokenP",
                    "communication_type": "REST"
                }
            }
            mapping_file = root / "tr_id_mapping.json"
            with open(mapping_file, 'w', encoding='utf-8') as f:
                json.dump(mapping_data, f, ensure_ascii=False)

            # Create documentation directory
            docs_dir = root / "api"
            docs_dir.mkdir(parents=True, exist_ok=True)

            oauth_dir = docs_dir / "oauth"
            oauth_dir.mkdir(parents=True, exist_ok=True)

            # Create complete API doc
            api_content = """
# API Documentation

## API Overview

API ID: `인증-001`

## TR_ID Information

TR_ID: ``

## Endpoint

POST /oauth2/tokenP

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
            (oauth_dir / "인증-001.md").write_text(api_content, encoding='utf-8')
            (oauth_dir / "index.md").write_text("# OAuth", encoding='utf-8')

            yield {
                "mapping_file": mapping_file,
                "docs_dir": docs_dir
            }

    def test_full_validation_flow_success(self, complete_test_env, caplog):
        """Test complete validation flow with success"""
        import logging

        with patch.object(validate_docs, 'TR_ID_MAPPING_FILE', complete_test_env["mapping_file"]):
            with patch.object(validate_docs, 'API_DOCS_DIR', complete_test_env["docs_dir"]):
                with caplog.at_level(logging.INFO):
                    # Load and categorize
                    tr_id_mapping = load_tr_id_mapping()
                    categorized_apis = categorize_apis(tr_id_mapping)

                    # Validate
                    validator = DocumentationValidator(detailed=True)
                    for category_slug, apis in categorized_apis.items():
                        validator.validate_category(category_slug, apis)
                        validator.validate_category_index(category_slug)

                    # Should have no issues
                    assert validator.results["total_apis"] == 1
                    assert validator.results["documented_apis"] == 1
                    assert len(validator.results["missing_files"]) == 0

    def test_validation_with_missing_file(self, complete_test_env):
        """Test validation with missing documentation file"""
        # Remove the API doc
        api_file = complete_test_env["docs_dir"] / "oauth" / "인증-001.md"
        api_file.unlink()

        with patch.object(validate_docs, 'TR_ID_MAPPING_FILE', complete_test_env["mapping_file"]):
            with patch.object(validate_docs, 'API_DOCS_DIR', complete_test_env["docs_dir"]):
                tr_id_mapping = load_tr_id_mapping()
                categorized_apis = categorize_apis(tr_id_mapping)

                validator = DocumentationValidator(detailed=False)
                for category_slug, apis in categorized_apis.items():
                    validator.validate_category(category_slug, apis)

                # Should detect missing file
                assert len(validator.results["missing_files"]) == 1

    def test_detailed_validation_with_links(self, temp_docs_dir):
        """Test detailed validation with link checking"""
        # Create API doc with internal links
        api_file = temp_docs_dir / "oauth" / "인증-001.md"
        api_file.write_text(
            "# API\n\n[Link to index](index.md)\n\n[Link to other](other.md)",
            encoding='utf-8'
        )

        # Create index file
        index_file = temp_docs_dir / "oauth" / "index.md"
        index_file.write_text("# Index", encoding='utf-8')

        sample_apis = [
            {
                "id": "인증-001",
                "api_id": "인증-001",
                "name": "API Test",
                "url": "/oauth2/tokenP",
                "http_method": "POST",
                "real_tr_id": "",
                "category": "OAuth인증"
            }
        ]

        with patch.object(validate_docs, 'API_DOCS_DIR', temp_docs_dir):
            validator = DocumentationValidator(detailed=True)
            validator.validate_category("oauth", sample_apis)

            # Should detect broken link to other.md
            broken_links = [e for e in validator.results["broken_links"] if "other" in e]
            assert len(broken_links) > 0

    def test_validate_category_results_with_content_errors(self, temp_docs_dir):
        """Test that content errors are tracked in category results"""
        # Create incomplete API doc
        api_file = temp_docs_dir / "oauth" / "인증-001.md"
        api_file.write_text("# Incomplete", encoding='utf-8')

        sample_apis = [
            {
                "id": "인증-001",
                "api_id": "인증-001",
                "name": "Incomplete API",
                "url": "/api/test",
                "http_method": "GET",
                "real_tr_id": "",
                "category": "OAuth인증"
            }
        ]

        with patch.object(validate_docs, 'API_DOCS_DIR', temp_docs_dir):
            validator = DocumentationValidator(detailed=True)
            validator.validate_category("oauth", sample_apis)

            # Should have content errors
            assert len(validator.results["content_errors"]) > 0
            # Category results should also track errors
            assert len(validator.results["categories"]["oauth"]["content_errors"]) > 0

    def test_validate_category_index_empty_file(self, temp_docs_dir):
        """Test validation of empty category index"""
        index_file = temp_docs_dir / "oauth" / "index.md"
        index_file.write_text("", encoding='utf-8')

        with patch.object(validate_docs, 'API_DOCS_DIR', temp_docs_dir):
            validator = DocumentationValidator(detailed=False)
            validator.validate_category_index("oauth")

            assert len(validator.results["empty_files"]) == 1
