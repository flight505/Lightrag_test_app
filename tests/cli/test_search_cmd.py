"""Tests for search commands."""
import os
import json
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from cli.commands.search_cmd import search
from cli.core.config import ConfigManager
from cli.core.store_manager import StoreManager
from src.lightrag_init import LightRAGManager

@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()

@pytest.fixture
def test_env(tmp_path):
    """Create a test environment with mocked components."""
    # Set up config and store manager
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config = ConfigManager(config_dir=config_dir)
    store_manager = StoreManager(config_dir=config_dir)
    
    # Create test store
    store_path = config.config_dir / "stores" / "test_store"
    store_path.mkdir(parents=True)
    (store_path / "documents").mkdir()
    (store_path / "metadata").mkdir()
    
    # Create test PDF
    test_pdf = store_path / "documents" / "test.pdf"
    test_pdf.write_bytes(b"Test PDF content")
    
    # Create metadata
    metadata = {
        "name": "test_store",
        "created": "2024-01-19",
        "documents": ["test.pdf"],
        "version": "1.0.0"
    }
    with open(store_path / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f)
        
    # Create mock graph
    mock_graph = MagicMock()
    mock_graph.save_html = MagicMock()
        
    # Mock LightRAGManager
    mock_manager = MagicMock()
    mock_manager.files = ["test.pdf"]
    mock_manager.load_documents = MagicMock()
    mock_manager.query.return_value = [
        {
            "document": "test.pdf",
            "score": 0.95,
            "context": "This is a test document context."
        }
    ]
    mock_manager.get_stats.return_value = {
        "total_documents": 1,
        "total_citations": 2,
        "total_equations": 3,
        "total_authors": 4,
        "total_relationships": 5,
        "embedding_stats": {
            "dimensions": 1536,
            "total_embeddings": 10
        }
    }
    mock_manager.get_citation_graph = MagicMock(return_value=mock_graph)
    mock_manager.get_equation_graph = MagicMock(return_value=mock_graph)
    mock_manager.get_author_graph = MagicMock(return_value=mock_graph)
    
    # Mock environment variable
    os.environ["OPENAI_API_KEY"] = "test-key"
    
    # Patch LightRAGManager
    with patch("cli.commands.search_cmd.LightRAGManager", return_value=mock_manager):
        yield {
            "tmp_path": tmp_path,
            "config": config,
            "store_manager": store_manager,
            "test_pdf": test_pdf,
            "mock_manager": mock_manager
        }
    
    # Cleanup
    os.environ.pop("OPENAI_API_KEY", None)

def test_query_command(runner, test_env):
    """Test basic search query."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(search, ['query', 'test document', 'test_store'])
        assert result.exit_code == 0
        assert "Search Results" in result.output
        assert "test.pdf" in result.output
        assert "0.95" in result.output

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
        assert "Total Documents: 1" in result.output

def test_stats_nonexistent_store(runner, test_env):
    """Test statistics for nonexistent store."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(search, ['stats', 'nonexistent'])
        assert result.exit_code == 1
        assert "not found" in result.output 