"""
Unit tests for generate_api_docs.py script

Tests for API documentation generation functionality including:
- Filename sanitization
- TR_ID mapping loading
- API categorization
- Template rendering
- Index generation
- Summary generation
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Import functions from the script
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts"))

import generate_api_docs

sanitize_filename = generate_api_docs.sanitize_filename
load_tr_id_mapping = generate_api_docs.load_tr_id_mapping
load_categories = generate_api_docs.load_categories
categorize_apis = generate_api_docs.categorize_apis
generate_category_index = generate_api_docs.generate_category_index
generate_api_docs_func = generate_api_docs.generate_api_docs
generate_main_index = generate_api_docs.generate_main_index
generate_api_summary = generate_api_docs.generate_api_summary
validate_docs = generate_api_docs.validate_docs
PROJECT_ROOT = generate_api_docs.PROJECT_ROOT


class TestSanitizeFilename:
    """Tests for sanitize_filename function"""

    def test_sanitize_simple_alphanumeric(self):
        """Test sanitization of simple alphanumeric API ID"""
        result = sanitize_filename("API001")
        assert result == "API001"

    def test_sanitize_with_special_chars(self):
        """Test sanitization with special characters"""
        result = sanitize_filename("국내주식-001")
        assert result == "국내주식-001"

    def test_sanitize_with_spaces(self):
        """Test sanitization with spaces"""
        result = sanitize_filename("API with spaces")
        assert result == "API-with-spaces"

    def test_sanitize_with_multiple_special_chars(self):
        """Test sanitization with multiple special characters"""
        result = sanitize_filename("API/@#$%^&*()Test")
        assert result == "API-Test"

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

    def test_sanitize_complex_real_api_id(self):
        """Test sanitization of real KIS API IDs"""
        test_cases = [
            ("인증-001", "인증-001"),
            ("국내주식-008", "국내주식-008"),
            ("해외주식-211", "해외주식-211"),
        ]
        for input_id, expected in test_cases:
            result = sanitize_filename(input_id)
            assert result == expected

    def test_sanitize_empty_string(self):
        """Test sanitization of empty string"""
        result = sanitize_filename("")
        assert result == ""

    def test_sanitize_only_special_chars(self):
        """Test sanitization of string with only special characters"""
        result = sanitize_filename("@#$%")
        assert result == ""


class TestLoadTRIdMapping:
    """Tests for load_tr_id_mapping function"""

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
        with patch.object(generate_api_docs, 'TR_ID_MAPPING_FILE', temp_mapping_file):
            mapping = load_tr_id_mapping()

            assert len(mapping) == 2
            assert "인증-001" in mapping
            assert "국내주식-008" in mapping
            assert mapping["인증-001"]["category"] == "OAuth인증"

    def test_load_tr_id_mapping_file_not_found(self):
        """Test FileNotFoundError when mapping file doesn't exist"""
        non_existent_file = PROJECT_ROOT / "nonexistent_tr_id_mapping.json"

        with patch.object(generate_api_docs, 'TR_ID_MAPPING_FILE', non_existent_file):
            with pytest.raises(FileNotFoundError) as exc_info:
                load_tr_id_mapping()

            assert "TR_ID mapping file not found" in str(exc_info.value)

    def test_load_tr_id_mapping_empty_file(self, temp_mapping_file):
        """Test loading empty mapping file"""
        # Write empty JSON
        with open(temp_mapping_file, 'w', encoding='utf-8') as f:
            json.dump({}, f)

        with patch.object(generate_api_docs, 'TR_ID_MAPPING_FILE', temp_mapping_file):
            mapping = load_tr_id_mapping()

            assert mapping == {}


class TestLoadCategories:
    """Tests for load_categories function"""

    @pytest.fixture
    def temp_categories_file(self):
        """Create temporary categories file"""
        categories_data = {
            "categories": [
                {
                    "id": "oauth",
                    "name": "OAuth Authentication",
                    "description": "OAuth 2.0 authentication APIs"
                },
                {
                    "id": "domestic-stock-orders",
                    "name": "Domestic Stock Orders",
                    "description": "Order management for domestic stocks"
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(categories_data, f, ensure_ascii=False)
            temp_file = Path(f.name)

        yield temp_file

        # Cleanup
        temp_file.unlink(missing_ok=True)

    def test_load_categories_success(self, temp_categories_file):
        """Test successful loading of categories"""
        with patch.object(generate_api_docs, 'CATEGORIES_FILE', temp_categories_file):
            categories = load_categories()

            assert len(categories["categories"]) == 2
            assert categories["categories"][0]["id"] == "oauth"

    def test_load_categories_file_not_found(self):
        """Test loading when categories file doesn't exist"""
        non_existent_file = PROJECT_ROOT / "nonexistent_categories.json"

        with patch.object(generate_api_docs, 'CATEGORIES_FILE', non_existent_file):
            categories = load_categories()

            # Should return empty categories
            assert categories == {"categories": []}

    def test_load_categories_empty_categories(self, temp_categories_file):
        """Test loading file with empty categories list"""
        # Write empty categories
        with open(temp_categories_file, 'w', encoding='utf-8') as f:
            json.dump({"categories": []}, f)

        with patch.object(generate_api_docs, 'CATEGORIES_FILE', temp_categories_file):
            categories = load_categories()

            assert categories == {"categories": []}


class TestCategorizeApis:
    """Tests for categorize_apis function"""

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
            "국내주식-211": {
                "name": "기간별계좌권리현황조회",
                "real_tr_id": "CTRGA011R",
                "paper_tr_id": "모의투자 미지원",
                "category": "[국내주식] 주문/계좌",
                "http_method": "GET",
                "url": "/uapi/domestic-stock/v1/trading/period-rights",
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

        # Check categories exist
        assert "oauth" in categorized
        assert "domestic-stock-orders" in categorized
        assert "overseas-stock-orders" in categorized

        # Check category counts
        assert len(categorized["oauth"]) == 1
        assert len(categorized["domestic-stock-orders"]) == 2
        assert len(categorized["overseas-stock-orders"]) == 1

        # Check API data structure
        oauth_api = categorized["oauth"][0]
        assert oauth_api["api_id"] == "인증-001"
        assert oauth_api["id"] == "인증-001"
        assert oauth_api["category_slug"] == "oauth"
        assert "name" in oauth_api

    def test_categorize_apis_unknown_category(self, sample_tr_id_mapping):
        """Test categorization with unknown category"""
        # Add API with unknown category
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
        assert len(categorized["other"]) == 1
        assert categorized["other"][0]["api_id"] == "UNKNOWN-001"

    def test_categorize_apis_empty_mapping(self):
        """Test categorization with empty mapping"""
        categorized = categorize_apis({})

        assert categorized == {}

    def test_categorize_apis_all_categories(self, sample_tr_id_mapping):
        """Test that all categories are properly mapped"""
        categorized = categorize_apis(sample_tr_id_mapping)

        # Verify slug mapping
        assert categorized["oauth"][0]["category"] == "OAuth인증"
        assert categorized["domestic-stock-orders"][0]["category"] == "[국내주식] 주문/계좌"


class TestGenerateCategoryIndex:
    """Tests for generate_category_index function"""

    def test_generate_category_index_basic(self):
        """Test basic category index generation"""
        apis = [
            {
                "id": "api-001",
                "api_id": "API-001",
                "name": "First API"
            },
            {
                "id": "api-002",
                "api_id": "API-002",
                "name": "Second API"
            }
        ]

        category_info = {
            "name": "Test Category",
            "description": "Test category description"
        }

        result = generate_category_index("test-category", apis, category_info)

        assert "# Test Category" in result
        assert "Test category description" in result
        assert "**Total APIs**: 2" in result
        assert "[First API](api-001.md)" in result
        assert "[Second API](api-002.md)" in result
        assert "`API-001`" in result
        assert "`API-002`" in result

    def test_generate_category_index_without_description(self):
        """Test category index without description"""
        apis = [{"id": "api-001", "api_id": "API-001", "name": "Test API"}]
        category_info = {}

        result = generate_category_index("test-category", apis, category_info)

        assert "# Test Category" in result
        assert "**Total APIs**: 1" in result

    def test_generate_category_index_sorted_apis(self):
        """Test that APIs are sorted alphabetically"""
        apis = [
            {"id": "api-003", "api_id": "API-003", "name": "Zebra API"},
            {"id": "api-001", "api_id": "API-001", "name": "Apple API"},
            {"id": "api-002", "api_id": "API-002", "name": "Middle API"}
        ]

        result = generate_category_index("test", apis, {})

        # Check ordering in result
        zebra_pos = result.find("Zebra API")
        apple_pos = result.find("Apple API")

        # Apple should come before Zebra
        assert apple_pos < zebra_pos

    def test_generate_category_index_back_link(self):
        """Test back to index link"""
        apis = []
        result = generate_category_index("test", apis, {})

        assert "[Back to API Documentation Index](../index.md)" in result


class TestGenerateApiSummary:
    """Tests for generate_api_summary function"""

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def sample_categorized_apis(self):
        """Sample categorized APIs"""
        return {
            "oauth": [
                {
                    "api_id": "인증-001",
                    "http_method": "POST",
                    "communication_type": "REST",
                    "name": "접근토큰발급(P)"
                }
            ],
            "domestic-stock-orders": [
                {
                    "api_id": "국내주식-008",
                    "http_method": "GET",
                    "communication_type": "REST",
                    "name": "주식잔고조회"
                },
                {
                    "api_id": "국내주식-211",
                    "http_method": "POST",
                    "communication_type": "REST",
                    "name": "주식주문"
                }
            ]
        }

    @pytest.fixture
    def sample_generation_stats(self):
        """Sample generation statistics"""
        return {
            "total_apis": 3,
            "total_categories": 2,
            "categories": {
                "oauth": {
                    "name": "OAuth Authentication",
                    "api_count": 1,
                    "index_file": "docs/kis-openapi/api/oauth/index.md"
                },
                "domestic-stock-orders": {
                    "name": "Domestic Stock Orders",
                    "api_count": 2,
                    "index_file": "docs/kis-openapi/api/domestic-stock-orders/index.md"
                }
            },
            "generated_files": []
        }

    def test_generate_api_summary_success(self, temp_output_dir, sample_categorized_apis, sample_generation_stats):
        """Test successful API summary generation"""
        with patch.object(generate_api_docs, 'API_SUMMARY_FILE', temp_output_dir / "api_summary.json"):
            generate_api_summary(sample_categorized_apis, sample_generation_stats)

            summary_file = temp_output_dir / "api_summary.json"
            assert summary_file.exists()

            with open(summary_file, 'r', encoding='utf-8') as f:
                summary = json.load(f)

            assert summary["total_apis"] == 3
            assert summary["total_categories"] == 2
            assert summary["version"] == "1.0.0"
            assert "generated_at" in summary
            assert len(summary["categories"]) == 2

            # Check category data
            oauth_cat = next(c for c in summary["categories"] if c["id"] == "oauth")
            assert oauth_cat["api_count"] == 1
            assert oauth_cat["http_methods"]["POST"] == 1
            assert oauth_cat["communication_types"]["REST"] == 1

            orders_cat = next(c for c in summary["categories"] if c["id"] == "domestic-stock-orders")
            assert orders_cat["api_count"] == 2
            assert orders_cat["http_methods"]["GET"] == 1
            assert orders_cat["http_methods"]["POST"] == 1

    def test_generate_api_summary_creates_directory(self, sample_categorized_apis, sample_generation_stats):
        """Test that summary generation creates parent directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            summary_file = Path(tmpdir) / "nested" / "dir" / "api_summary.json"

            with patch.object(generate_api_docs, 'API_SUMMARY_FILE', summary_file):
                generate_api_summary(sample_categorized_apis, sample_generation_stats)

                assert summary_file.exists()
                assert summary_file.parent.is_dir()


class TestValidateDocs:
    """Tests for validate_docs function"""

    @pytest.fixture
    def temp_docs_dir(self):
        """Create temporary documentation directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir) / "api"
            docs_dir.mkdir(parents=True, exist_ok=True)

            # Create sample API doc
            oauth_dir = docs_dir / "oauth"
            oauth_dir.mkdir(parents=True, exist_ok=True)

            api_file = oauth_dir / "인증-001.md"
            api_file.write_text("# Test API Doc\n\nContent here", encoding='utf-8')

            # Create index
            index_file = oauth_dir / "index.md"
            index_file.write_text("# OAuth Category\n\nAPIs here", encoding='utf-8')

            yield docs_dir

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
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(mapping_data, f, ensure_ascii=False)
            temp_file = Path(f.name)

        yield temp_file

        # Cleanup
        temp_file.unlink(missing_ok=True)

    def test_validate_docs_all_present(self, temp_docs_dir, temp_mapping_file):
        """Test validation with all documentation present"""
        with patch.object(generate_api_docs, 'API_DOCS_DIR', temp_docs_dir):
            with patch.object(generate_api_docs, 'TR_ID_MAPPING_FILE', temp_mapping_file):
                result = validate_docs()

                assert result is True

    def test_validate_docs_missing_file(self, temp_docs_dir, temp_mapping_file):
        """Test validation with missing documentation file"""
        # Remove the API doc file
        api_file = temp_docs_dir / "oauth" / "인증-001.md"
        api_file.unlink()

        with patch.object(generate_api_docs, 'API_DOCS_DIR', temp_docs_dir):
            with patch.object(generate_api_docs, 'TR_ID_MAPPING_FILE', temp_mapping_file):
                result = validate_docs()

                assert result is False

    def test_validate_docs_missing_index(self, temp_docs_dir, temp_mapping_file):
        """Test validation with missing category index"""
        # Remove the index file
        index_file = temp_docs_dir / "oauth" / "index.md"
        index_file.unlink()

        with patch.object(generate_api_docs, 'API_DOCS_DIR', temp_docs_dir):
            with patch.object(generate_api_docs, 'TR_ID_MAPPING_FILE', temp_mapping_file):
                result = validate_docs()

                assert result is False

    def test_validate_docs_empty_file(self, temp_docs_dir, temp_mapping_file):
        """Test validation with empty documentation file"""
        # Make the file empty
        api_file = temp_docs_dir / "oauth" / "인증-001.md"
        api_file.write_text("", encoding='utf-8')

        with patch.object(generate_api_docs, 'API_DOCS_DIR', temp_docs_dir):
            with patch.object(generate_api_docs, 'TR_ID_MAPPING_FILE', temp_mapping_file):
                result = validate_docs()

                assert result is False

    def test_generate_api_docs_phase_2(self, temp_mapping_file):
        """Test Phase 2 (remaining categories) generation"""
        # Create docs directory structure
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir)
            api_docs_dir = docs_dir / "api"
            api_docs_dir.mkdir(parents=True, exist_ok=True)

            # Create categories file
            categories_file = docs_dir / "categories.json"
            categories_file.write_text('{"categories": []}', encoding='utf-8')

            # Create template file
            template_file = docs_dir / "template.md.j2"
            template_file.write_text("# {{ api_name }}", encoding='utf-8')

            with patch.object(generate_api_docs, 'API_DOCS_DIR', api_docs_dir):
                with patch.object(generate_api_docs, 'CATEGORIES_FILE', categories_file):
                    with patch.object(generate_api_docs, 'TR_ID_MAPPING_FILE', temp_mapping_file):
                        with patch.object(generate_api_docs, 'TEMPLATE_FILE', template_file):
                            # Mock load_template to avoid template loading
                            with patch('generate_api_docs.load_template') as mock_template:
                                from jinja2 import Template
                                mock_template.return_value = Template("# {{ api_name }}")

                                tr_id_mapping = load_tr_id_mapping()
                                categories_info = load_categories()
                                categorized_apis = categorize_apis(tr_id_mapping)

                                # Phase 2: non-priority categories
                                stats = generate_api_docs_func(categorized_apis, categories_info, phase=2)

                                # OAuth is priority, so it should be excluded in phase 2
                                assert stats["total_apis"] == 0


class TestGenerateMainIndex:
    """Tests for generate_main_index function"""

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def sample_categorized_apis(self):
        """Sample categorized APIs"""
        return {
            "oauth": [
                {"name": "접근토큰발급(P)"}
            ],
            "domestic-stock-orders": [
                {"name": "주식잔고조회"},
                {"name": "주식주문"}
            ]
        }

    @pytest.fixture
    def sample_categories_info(self):
        """Sample categories info"""
        return {
            "categories": [
                {
                    "id": "oauth",
                    "name": "OAuth Authentication",
                    "description": "OAuth 2.0 authentication APIs"
                },
                {
                    "id": "domestic-stock-orders",
                    "name": "Domestic Stock Orders",
                    "description": "Order management for domestic stocks"
                }
            ]
        }

    def test_generate_main_index_success(self, temp_output_dir, sample_categorized_apis, sample_categories_info):
        """Test successful main index generation"""
        api_docs_dir = temp_output_dir / "api"
        api_docs_dir.mkdir(parents=True, exist_ok=True)

        with patch.object(generate_api_docs, 'API_DOCS_DIR', api_docs_dir):
            generate_main_index(sample_categorized_apis, sample_categories_info)

            index_file = temp_output_dir / "index.md"
            assert index_file.exists()

            content = index_file.read_text(encoding='utf-8')

            assert "# KIS OpenAPI Documentation" in content
            assert "**Total APIs**: 3" in content
            assert "## Categories" in content
            assert "[OAuth Authentication](api/oauth/index.md)" in content
            assert "[Domestic Stock Orders](api/domestic-stock-orders/index.md)" in content
            assert "## Quick Links" in content

    def test_generate_main_index_without_category_info(self, temp_output_dir, sample_categorized_apis):
        """Test main index generation without category info"""
        api_docs_dir = temp_output_dir / "api"
        api_docs_dir.mkdir(parents=True, exist_ok=True)

        categories_info = {"categories": []}

        with patch.object(generate_api_docs, 'API_DOCS_DIR', api_docs_dir):
            generate_main_index(sample_categorized_apis, categories_info)

            index_file = temp_output_dir / "index.md"
            content = index_file.read_text(encoding='utf-8')

            # Should use slug-based names
            assert "Oauth" in content or "oauth" in content.lower()
            assert "Domestic Stock Orders" in content


class TestIntegration:
    """Integration tests for generate_api_docs.py"""

    @pytest.fixture
    def temp_project_root(self):
        """Create temporary project root structure"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create directory structure
            (root / "docs" / "kis-openapi" / "_data").mkdir(parents=True, exist_ok=True)
            (root / "docs_raw").mkdir(parents=True, exist_ok=True)
            (root / "templates").mkdir(parents=True, exist_ok=True)

            # Create TR_ID mapping file
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
            with open(root / "docs" / "kis-openapi" / "_data" / "tr_id_mapping.json", 'w', encoding='utf-8') as f:
                json.dump(mapping_data, f, ensure_ascii=False)

            # Create categories file
            categories_data = {"categories": []}
            with open(root / "docs_raw" / "categories.json", 'w', encoding='utf-8') as f:
                json.dump(categories_data, f, ensure_ascii=False)

            # Create template file
            template_content = "# {{ api_name }}\n\n## API Overview\n\nAPI ID: `{{ api_id }}`"
            with open(root / "templates" / "api_doc_template.md.j2", 'w', encoding='utf-8') as f:
                f.write(template_content)

            yield root

    def test_full_generation_flow(self, temp_project_root):
        """Test complete documentation generation flow"""
        with patch.object(generate_api_docs, 'PROJECT_ROOT', temp_project_root):
            # Reconfigure paths
            tr_id_mapping_file = temp_project_root / "docs" / "kis-openapi" / "_data" / "tr_id_mapping.json"
            categories_file = temp_project_root / "docs_raw" / "categories.json"
            template_file = temp_project_root / "templates" / "api_doc_template.md.j2"
            api_docs_dir = temp_project_root / "docs" / "kis-openapi" / "api"
            api_summary_file = temp_project_root / "docs" / "kis-openapi" / "_data" / "api_summary.json"

            with patch.object(generate_api_docs, 'TR_ID_MAPPING_FILE', tr_id_mapping_file):
                with patch.object(generate_api_docs, 'CATEGORIES_FILE', categories_file):
                    with patch.object(generate_api_docs, 'TEMPLATE_FILE', template_file):
                        with patch.object(generate_api_docs, 'API_DOCS_DIR', api_docs_dir):
                            with patch.object(generate_api_docs, 'API_SUMMARY_FILE', api_summary_file):
                                # Load and categorize
                                tr_id_mapping = load_tr_id_mapping()
                                categories_info = load_categories()
                                categorized_apis = categorize_apis(tr_id_mapping)

                                # Generate docs
                                stats = generate_api_docs_func(categorized_apis, categories_info)

                                # Verify stats
                                assert stats["total_apis"] == 1
                                assert stats["total_categories"] == 1

                                # Verify files created
                                api_file = api_docs_dir / "oauth" / "인증-001.md"
                                assert api_file.exists()

                                index_file = api_docs_dir / "oauth" / "index.md"
                                assert index_file.exists()

    def test_phase_1_generation(self, temp_project_root):
        """Test Phase 1 (priority categories) generation"""
        # Add more APIs for testing phase filtering
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
            "국내주식-001": {
                "name": "잔고조회",
                "real_tr_id": "TTTC8001R",
                "paper_tr_id": "TTTC8001R",
                "category": "[국내주식] 기본시세",
                "http_method": "GET",
                "url": "/uapi/domestic-stock/v1/quotations",
                "communication_type": "REST"
            }
        }

        with open(temp_project_root / "docs" / "kis-openapi" / "_data" / "tr_id_mapping.json", 'w', encoding='utf-8') as f:
            json.dump(mapping_data, f, ensure_ascii=False)

        with patch.object(generate_api_docs, 'PROJECT_ROOT', temp_project_root):
            # Configure paths
            tr_id_mapping_file = temp_project_root / "docs" / "kis-openapi" / "_data" / "tr_id_mapping.json"
            categories_file = temp_project_root / "docs_raw" / "categories.json"
            template_file = temp_project_root / "templates" / "api_doc_template.md.j2"
            api_docs_dir = temp_project_root / "docs" / "kis-openapi" / "api"
            api_summary_file = temp_project_root / "docs" / "kis-openapi" / "_data" / "api_summary.json"

            with patch.object(generate_api_docs, 'TR_ID_MAPPING_FILE', tr_id_mapping_file):
                with patch.object(generate_api_docs, 'CATEGORIES_FILE', categories_file):
                    with patch.object(generate_api_docs, 'TEMPLATE_FILE', template_file):
                        with patch.object(generate_api_docs, 'API_DOCS_DIR', api_docs_dir):
                            with patch.object(generate_api_docs, 'API_SUMMARY_FILE', api_summary_file):
                                tr_id_mapping = load_tr_id_mapping()
                                categories_info = load_categories()
                                categorized_apis = categorize_apis(tr_id_mapping)

                                # Phase 1: priority categories only
                                stats = generate_api_docs_func(categorized_apis, categories_info, phase=1)

                                # oauth and domestic-stock-basic are both priority
                                assert stats["total_categories"] == 2


class TestMainFunction:
    """Tests for main function and CLI argument handling"""

    @pytest.fixture
    def temp_project_root(self):
        """Create temporary project root for main() testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create directory structure
            (root / "docs" / "kis-openapi" / "_data").mkdir(parents=True, exist_ok=True)
            (root / "docs_raw").mkdir(parents=True, exist_ok=True)
            (root / "templates").mkdir(parents=True, exist_ok=True)
            (root / "docs" / "kis-openapi" / "api").mkdir(parents=True, exist_ok=True)

            # Create TR_ID mapping file
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
            with open(root / "docs" / "kis-openapi" / "_data" / "tr_id_mapping.json", 'w', encoding='utf-8') as f:
                json.dump(mapping_data, f, ensure_ascii=False)

            # Create categories file
            categories_data = {"categories": []}
            with open(root / "docs_raw" / "categories.json", 'w', encoding='utf-8') as f:
                json.dump(categories_data, f, ensure_ascii=False)

            # Create template file
            template_content = "# {{ api_name }}\n\n## API Overview\n\nAPI ID: `{{ api_id }}`"
            with open(root / "templates" / "api_doc_template.md.j2", 'w', encoding='utf-8') as f:
                f.write(template_content)

            yield root

    def test_main_validate_mode_success(self, temp_project_root, caplog):
        """Test main() in validate mode with all docs present"""
        import logging
        from unittest.mock import patch

        # Create the required API doc file
        oauth_dir = temp_project_root / "docs" / "kis-openapi" / "api" / "oauth"
        oauth_dir.mkdir(parents=True, exist_ok=True)
        (oauth_dir / "인증-001.md").write_text("# API Doc\n\nContent", encoding='utf-8')
        (oauth_dir / "index.md").write_text("# OAuth", encoding='utf-8')

        with patch.object(generate_api_docs, 'PROJECT_ROOT', temp_project_root):
            with patch('sys.argv', ['generate_api_docs.py', '--validate']):
                with caplog.at_level(logging.INFO):
                    try:
                        generate_api_docs.main()
                    except SystemExit as e:
                        assert e.code == 0

        # Check that validation was logged
        assert any("Validating documentation" in record.message for record in caplog.records)

    def test_main_validate_mode_missing_docs(self, temp_project_root, caplog):
        """Test main() in validate mode with missing docs"""
        import logging
        from unittest.mock import patch

        # Don't create the docs, so validation should fail
        # Create empty API docs directory to force missing doc detection
        api_docs_dir = temp_project_root / "docs" / "kis-openapi" / "api"
        api_docs_dir.mkdir(parents=True, exist_ok=True)

        with patch.object(generate_api_docs, 'PROJECT_ROOT', temp_project_root):
            with patch.object(generate_api_docs, 'API_DOCS_DIR', api_docs_dir):
                with patch('sys.argv', ['generate_api_docs.py', '--validate']):
                    with caplog.at_level(logging.INFO):
                        try:
                            generate_api_docs.main()
                        except SystemExit as e:
                            assert e.code == 1

    def test_main_generation_mode_phase_1(self, temp_project_root, caplog):
        """Test main() in generation mode with phase 1"""
        import logging
        from unittest.mock import patch

        api_docs_dir = temp_project_root / "docs" / "kis-openapi" / "api"
        api_docs_dir.mkdir(parents=True, exist_ok=True)

        with patch.object(generate_api_docs, 'PROJECT_ROOT', temp_project_root):
            with patch.object(generate_api_docs, 'API_DOCS_DIR', api_docs_dir):
                with patch('sys.argv', ['generate_api_docs.py', '--phase', '1']):
                    with caplog.at_level(logging.INFO):
                        try:
                            generate_api_docs.main()
                        except SystemExit:
                            # Generation mode doesn't exit, it just completes
                            pass

        # Check files were created
        assert (temp_project_root / "docs" / "kis-openapi" / "api" / "oauth" / "인증-001.md").exists()

    def test_main_verbose_mode(self, temp_project_root, caplog):
        """Test main() with verbose logging enabled"""
        import logging
        from unittest.mock import patch

        with patch.object(generate_api_docs, 'PROJECT_ROOT', temp_project_root):
            with patch('sys.argv', ['generate_api_docs.py', '--validate', '--verbose']):
                with caplog.at_level(logging.DEBUG):
                    try:
                        generate_api_docs.main()
                    except SystemExit:
                        pass
