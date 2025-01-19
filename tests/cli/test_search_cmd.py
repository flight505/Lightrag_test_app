"""Tests for search commands."""
import os
import json
import shutil
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
    config_dir.mkdir(exist_ok=True)
    config = ConfigManager(config_dir=config_dir)
    store_manager = StoreManager(config_dir=config_dir)
    
    # Create test store
    store_path = config.get_store_root() / "test_store"
    store_path.mkdir(parents=True, exist_ok=True)
    (store_path / "documents").mkdir(exist_ok=True)
    (store_path / "metadata").mkdir(exist_ok=True)
    (store_path / "converted").mkdir(exist_ok=True)
    (store_path / "cache").mkdir(exist_ok=True)
    
    # Copy test PDFs from tests/pdfs
    pdf_dir = Path("tests/pdfs")
    arxiv_pdf = pdf_dir / "Chen et al. - 2023 - TSMixer An All-MLP Architecture for Time Series Forecasting-annotated.pdf"
    doi_pdf = pdf_dir / "Choo et al. - 2023 - Deep-learning-based personalized prediction of absolute neutrophil count recovery and comparison with clinicians-annotated.pdf"
    
    # Copy PDFs and their metadata
    shutil.copy2(arxiv_pdf, store_path / "documents" / arxiv_pdf.name)
    shutil.copy2(doi_pdf, store_path / "documents" / doi_pdf.name)
    
    # Load existing metadata
    arxiv_metadata_path = pdf_dir / f"{arxiv_pdf.stem}_metadata.json"
    with open(arxiv_metadata_path, 'r', encoding='utf-8') as f:
        arxiv_metadata = json.load(f)
    
    # Create store metadata
    store_metadata = {
        "name": "test_store",
        "created": "2024-01-19",
        "updated": "2024-01-19",
        "documents": [
            {
                "file": arxiv_pdf.name,
                "metadata": arxiv_metadata
            }
        ]
    }
    with open(store_path / "metadata.json", "w", encoding='utf-8') as f:
        json.dump(store_metadata, f, indent=2)
    
    # Mock LightRAGManager
    mock_manager = MagicMock()
    mock_manager.files = [arxiv_pdf.name]
    mock_manager.load_documents = MagicMock()
    mock_manager.query.return_value = [
        {
            "document": arxiv_pdf.name,
            "score": 0.95,
            "context": "TSMixer is an all-MLP architecture for time series forecasting. Real-world time-series datasets are often multivariate with complex dynamics."
        }
    ]
    mock_manager.get_stats.return_value = {
        "total_documents": 1,
        "total_citations": len(arxiv_metadata.get("references", [])),
        "total_equations": len(arxiv_metadata.get("equations", [])),
        "total_authors": len(arxiv_metadata.get("authors", [])),
        "total_relationships": len(arxiv_metadata.get("references", [])),
        "embedding_stats": {
            "dimensions": 1536,
            "total_embeddings": len(arxiv_metadata.get("equations", [])) + len(arxiv_metadata.get("references", []))
        }
    }
    
    # Create mock graph
    mock_graph = MagicMock()
    mock_graph.save_html = MagicMock()
    mock_manager.get_citation_graph = MagicMock(return_value=mock_graph)
    mock_manager.get_equation_graph = MagicMock(return_value=mock_graph)
    mock_manager.get_author_graph = MagicMock(return_value=mock_graph)
    
    # Mock environment variable
    os.environ["OPENAI_API_KEY"] = "test-key"
    
    return {
        "tmp_path": tmp_path,
        "config": config,
        "store_manager": store_manager,
        "arxiv_pdf": arxiv_pdf,
        "metadata": arxiv_metadata,
        "mock_manager": mock_manager
    }

@patch("cli.commands.search_cmd.LightRAGManager")
def test_query_command(mock_manager_cls, runner, test_env):
    """Test basic search query."""
    mock_manager_cls.return_value = test_env["mock_manager"]
    
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(search, ['query', 'time series', 'test_store'])
        assert result.exit_code == 0
        assert "Search Results" in result.output
        assert "TSMixer" in result.output
        assert "Real-world time-series datasets" in result.output
        assert "0.95" in result.output

def test_query_nonexistent_store(runner, test_env):
    """Test querying a nonexistent store."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(search, ['query', 'test', 'nonexistent'])
        assert result.exit_code != 0
        assert "not found" in result.output

@patch("cli.commands.search_cmd.LightRAGManager")
def test_query_with_graph(mock_manager_cls, runner, test_env):
    """Test search query with knowledge graph."""
    mock_manager_cls.return_value = test_env["mock_manager"]
    
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(search, ['query', 'test', 'test_store', '--show-graph'])
        assert result.exit_code == 0
        assert "Knowledge Graph" in result.output
        assert "knowledge_graph.html" in result.output

@patch("cli.commands.search_cmd.LightRAGManager")
def test_graph_command(mock_manager_cls, runner, test_env):
    """Test graph generation."""
    mock_manager_cls.return_value = test_env["mock_manager"]
    
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(search, ['graph', 'test_store'])
        assert result.exit_code == 0
        assert "citations_graph.html" in result.output

def test_graph_nonexistent_store(runner, test_env):
    """Test graph generation for nonexistent store."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(search, ['graph', 'nonexistent'])
        assert result.exit_code != 0
        assert "not found" in result.output

@patch("cli.commands.search_cmd.LightRAGManager")
def test_stats_command(mock_manager_cls, runner, test_env):
    """Test search statistics."""
    mock_manager_cls.return_value = test_env["mock_manager"]
    
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(search, ['stats', 'test_store'])
        assert result.exit_code == 0
        assert "Store Statistics" in result.output
        assert "Total Documents: 1" in result.output

def test_stats_nonexistent_store(runner, test_env):
    """Test statistics for nonexistent store."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(search, ['stats', 'nonexistent'])
        assert result.exit_code != 0
        assert "not found" in result.output 