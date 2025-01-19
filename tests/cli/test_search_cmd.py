"""Tests for search commands."""
import os
import json
import pytest
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from cli.commands.search_cmd import search
from cli.core.config import ConfigManager
from cli.core.store_manager import StoreManager

@pytest.fixture
def test_env(tmp_path):
    """Create test environment."""
    # Set up config and store manager
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    os.environ["LIGHTRAG_CONFIG_DIR"] = str(config_dir)
    os.environ["OPENAI_API_KEY"] = "test-api-key"  # Mock API key
    
    config = ConfigManager()
    store_manager = StoreManager(config_dir=config.config_dir)
    
    # Create test store
    store_name = "test_store"
    store_path = store_manager.store_root / store_name
    store_manager.create_store(store_name)
    
    # Create test document
    docs_dir = store_path / "documents"
    docs_dir.mkdir(exist_ok=True)
    test_pdf = docs_dir / "test.pdf"
    
    # Create a PDF with content
    with open(test_pdf, "wb") as f:
        f.write(b"%PDF-1.4\n")
        f.write(b"1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n")
        f.write(b"2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n")
        f.write(b"3 0 obj\n<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<<>>/Contents 4 0 R>>\nendobj\n")
        f.write(b"4 0 obj\n<</Length 100>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Test Document Title) Tj\n0 -20 Td\n(Author: John Doe) Tj\n0 -20 Td\n(Abstract: This is a test document.) Tj\nET\nendstream\nendobj\n")
        f.write(b"xref\n0 5\n0000000000 65535 f\n0000000010 00000 n\n0000000056 00000 n\n0000000111 00000 n\n0000000212 00000 n\ntrailer\n<</Size 5/Root 1 0 R>>\nstartxref\n408\n%%EOF\n")
    
    # Create metadata
    metadata_dir = store_path / "metadata"
    metadata_dir.mkdir(exist_ok=True)
    
    doc_metadata = {
        "title": "Test Document",
        "authors": ["John Doe"],
        "abstract": "This is a test document.",
        "doi": "10.1234/test",
        "citations": [],
        "equations": [],
        "text": "Test Document Title\nAuthor: John Doe\nAbstract: This is a test document."
    }
    
    with open(metadata_dir / "test_metadata.json", "w", encoding="utf-8") as f:
        json.dump(doc_metadata, f, indent=2)
    
    # Update store metadata
    store_metadata = {
        "name": store_name,
        "created": "2024-01-19T00:00:00",
        "last_updated": "2024-01-19T00:00:00",
        "documents": ["test.pdf"]
    }
    
    with open(store_path / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(store_metadata, f, indent=2)
    
    # Create consolidated metadata
    consolidated = {
        "store_info": {
            "name": store_name,
            "created": "2024-01-19T00:00:00",
            "last_updated": "2024-01-19T00:00:00",
            "version": "1.0.0"
        },
        "nodes": {
            "papers": [doc_metadata],
            "equations": [],
            "citations": [],
            "authors": [{"name": "John Doe", "papers": ["test.pdf"]}],
            "contexts": []
        },
        "relationships": [],
        "global_stats": {
            "total_documents": 1,
            "total_citations": 0,
            "total_equations": 0,
            "total_authors": 1,
            "total_relationships": 0,
            "embedding_stats": {
                "total_embeddings": 1,
                "average_embedding_time": 0.5
            }
        }
    }
    
    with open(store_path / "consolidated.json", "w", encoding="utf-8") as f:
        json.dump(consolidated, f, indent=2)
    
    return {
        "tmp_path": tmp_path,
        "config": config,
        "store_manager": store_manager,
        "store_path": store_path,
        "test_pdf": test_pdf
    }

@pytest.fixture(autouse=True)
def mock_components():
    """Mock LightRAG components."""
    with patch('src.lightrag_init.LightRAGManager') as mock_manager, \
         patch('src.document_validator.DocumentValidator') as mock_validator, \
         patch('src.file_processor.FileProcessor') as mock_processor, \
         patch('src.lightrag_init.LightRAG') as mock_lightrag:
        
        # Create mock instances
        mock_manager_instance = MagicMock()
        mock_validator_instance = MagicMock()
        mock_processor_instance = MagicMock()
        mock_lightrag_instance = MagicMock()
        
        # Configure validator mock
        mock_validator_instance.validate_store.return_value = {
            'valid_files': ['test.pdf'],
            'errors': []
        }
        mock_validator_instance.validate_files.return_value = {
            'valid_files': ['test.pdf'],
            'errors': []
        }
        mock_validator_instance.validate_content.return_value = (True, None)
        
        # Configure processor mock
        mock_processor_instance.process_file.return_value = {
            'title': 'Test Document',
            'authors': ['John Doe'],
            'abstract': 'This is a test document.',
            'doi': '10.1234/test',
            'citations': [],
            'equations': []
        }
        
        # Configure lightrag mock
        mock_lightrag_instance.files = ['test.pdf']
        mock_lightrag_instance.insert.return_value = None
        mock_lightrag_instance.query.return_value = "This is a test document."
        mock_lightrag_instance.get_citation_graph.return_value = MagicMock(
            save_html=lambda x: None
        )
        
        # Configure manager mock
        mock_manager_instance.load_documents.return_value = None
        mock_manager_instance.query.return_value = [{
            "document": "test.pdf",
            "score": 0.95,
            "context": "This is a test document."
        }]
        
        mock_manager_instance.get_citation_graph.return_value = MagicMock(
            save_html=lambda x: None
        )
        
        mock_manager_instance.get_equation_graph.return_value = MagicMock(
            save_html=lambda x: None
        )
        
        mock_manager_instance.get_author_graph.return_value = MagicMock(
            save_html=lambda x: None
        )
        
        mock_manager_instance.get_stats.return_value = {
            "total_documents": 1,
            "total_citations": 0,
            "total_equations": 0,
            "total_authors": 1,
            "total_relationships": 0,
            "embedding_stats": {
                "total_embeddings": 1,
                "average_embedding_time": 0.5
            }
        }
        
        # Configure the mock manager to return our mock instance
        def mock_init(api_key=None, input_dir=None, *args, **kwargs):
            mock_manager_instance.api_key = api_key
            mock_manager_instance.input_dir = input_dir
            mock_manager_instance.validator = mock_validator_instance
            mock_manager_instance.file_processor = mock_processor_instance
            mock_manager_instance.rag = mock_lightrag_instance
            return mock_manager_instance
        
        mock_manager.side_effect = mock_init
        mock_validator.return_value = mock_validator_instance
        mock_processor.return_value = mock_processor_instance
        mock_lightrag.return_value = mock_lightrag_instance
        
        yield {
            'manager': mock_manager,
            'validator': mock_validator,
            'processor': mock_processor,
            'lightrag': mock_lightrag
        }

@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()

def test_query_command(runner, test_env):
    """Test basic search query."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(search, ['query', 'test document', 'test_store'])
        assert result.exit_code == 0
        assert "Search Results" in result.output

def test_query_nonexistent_store(runner, test_env):
    """Test querying a nonexistent store."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(search, ['query', 'test', 'nonexistent'])
        assert result.exit_code == 1
        assert "not found" in result.output

def test_query_with_graph(runner, test_env):
    """Test search query with knowledge graph."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(search, ['query', 'test', 'test_store', '--show-graph'])
        assert result.exit_code == 0
        assert "Knowledge Graph" in result.output
        assert "knowledge_graph.html" in result.output

def test_graph_command(runner, test_env):
    """Test graph generation."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(search, ['graph', 'test_store'])
        assert result.exit_code == 0
        assert "citations_graph.html" in result.output

def test_graph_nonexistent_store(runner, test_env):
    """Test graph generation for nonexistent store."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(search, ['graph', 'nonexistent'])
        assert result.exit_code == 1
        assert "not found" in result.output

def test_stats_command(runner, test_env):
    """Test search statistics."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(search, ['stats', 'test_store'])
        assert result.exit_code == 0
        assert "Store Statistics" in result.output
        assert "Total Documents" in result.output

def test_stats_nonexistent_store(runner, test_env):
    """Test statistics for nonexistent store."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(search, ['stats', 'nonexistent'])
        assert result.exit_code == 1
        assert "not found" in result.output 