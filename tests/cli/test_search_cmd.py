"""Tests for search commands."""
import os
import pytest
from pathlib import Path
from click.testing import CliRunner
from cli.commands.search_cmd import search
from cli.core.config import ConfigManager
from cli.core.store_manager import StoreManager

@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()

@pytest.fixture
def test_env(tmp_path):
    """Create test environment with config and store manager."""
    # Set up test config directory
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    os.environ["LIGHTRAG_CONFIG_DIR"] = str(config_dir)
    
    # Initialize managers
    config = ConfigManager()
    store_manager = StoreManager(config_dir=config.config_dir)
    
    # Create test store
    store_manager.create_store("test_store")
    
    # Create test document with content
    store_path = store_manager.store_root / "test_store"
    doc_path = store_path / "documents" / "test.pdf"
    doc_path.parent.mkdir(exist_ok=True)
    
    with open(doc_path, "wb") as f:
        # Create a PDF with text content
        f.write(b"%PDF-1.4\n")
        # Catalog
        f.write(b"1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n")
        # Pages
        f.write(b"2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n")
        # Page
        f.write(b"3 0 obj\n<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>\nendobj\n")
        # Font
        f.write(b"4 0 obj\n<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>\nendobj\n")
        # Content stream with actual text
        content = b"BT\n/F1 12 Tf\n72 700 Td\n(Test Document Title) Tj\n0 -20 Td\n(Author: John Doe) Tj\n0 -20 Td\n(Abstract: This is a test document for LightRAG search testing.) Tj\nET"
        f.write(f"5 0 obj\n<</Length {len(content)}>>\nstream\n{content}\nendstream\nendobj\n".encode())
        # Cross-reference table
        f.write(b"xref\n0 6\n0000000000 65535 f\n0000000009 00000 n\n0000000056 00000 n\n0000000111 00000 n\n0000000212 00000 n\n0000000277 00000 n\n")
        # Trailer
        f.write(b"trailer\n<</Size 6/Root 1 0 R>>\nstartxref\n408\n%%EOF\n")
    
    return {
        "tmp_path": tmp_path,
        "config": config,
        "store_manager": store_manager,
        "test_doc": doc_path
    }

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
        assert result.exit_code != 0
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
        assert result.exit_code != 0
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
        assert result.exit_code != 0
        assert "not found" in result.output 