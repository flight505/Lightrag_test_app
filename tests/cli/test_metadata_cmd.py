"""Tests for metadata commands."""
import json
import os
import shutil
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from cli.commands.metadata_cmd import metadata
from cli.core.config import ConfigManager
from cli.core.store_manager import StoreManager
from src.academic_metadata import AcademicMetadata
from src.metadata_extractor import MetadataExtractor

@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()

@pytest.fixture
def test_env(tmp_path):
    """Create a test environment with a store and document."""
    # Set up config directory
    config_dir = tmp_path / ".lightrag"
    config_dir.mkdir(exist_ok=True)
    os.environ["LIGHTRAG_CONFIG_DIR"] = str(config_dir)
    
    # Set up config and store manager
    config = ConfigManager(config_dir=config_dir)
    store_manager = StoreManager(config_dir=config_dir)
    
    # Create test store
    store_manager.create_store("test_store")
    store_path = config.get_store_root() / "test_store"
    
    # Copy test PDFs from tests/pdfs to store
    pdf_dir = Path("tests/pdfs")
    arxiv_pdf = pdf_dir / "Chen et al. - 2023 - TSMixer An All-MLP Architecture for Time Series Forecasting-annotated.pdf"
    metadata_file = pdf_dir / "Chen et al. - 2023 - TSMixer An All-MLP Architecture for Time Series Forecasting-annotated_metadata.json"
    
    # Create temp directory for PDFs
    temp_pdf_dir = tmp_path / "pdfs"
    temp_pdf_dir.mkdir(exist_ok=True)
    
    # Copy files to temp directory
    temp_arxiv_pdf = temp_pdf_dir / arxiv_pdf.name
    temp_metadata_file = temp_pdf_dir / metadata_file.name
    shutil.copy2(arxiv_pdf, temp_arxiv_pdf)
    shutil.copy2(metadata_file, temp_metadata_file)
    
    # Copy PDF to store's documents directory
    shutil.copy2(temp_arxiv_pdf, store_path / "documents" / temp_arxiv_pdf.name)
    
    # Load and copy metadata
    with open(temp_metadata_file, encoding="utf-8") as f:
        arxiv_metadata = json.load(f)
    
    # Save metadata to store's metadata directory
    with open(store_path / "metadata" / f"{temp_arxiv_pdf.stem}_metadata.json", "w", encoding="utf-8") as f:
        json.dump(arxiv_metadata, f, indent=2)
    
    # Update store metadata
    store_metadata = store_manager.get_store_info("test_store")
    store_metadata["document_count"] = 1
    store_metadata["size"] = os.path.getsize(temp_arxiv_pdf)
    store_metadata["documents"].append(temp_arxiv_pdf.name)
    store_manager.update_store_metadata("test_store", store_metadata)
    
    # Update consolidated metadata
    consolidated = {
        "store_info": {
            "name": "test_store",
            "created": "2024-01-19",
            "last_updated": "2024-01-19",
            "version": "1.0.0"
        },
        "nodes": {
            "papers": [arxiv_metadata],
            "equations": arxiv_metadata.get("equations", []),
            "citations": arxiv_metadata.get("citations", []),
            "authors": arxiv_metadata.get("authors", []),
            "contexts": []
        },
        "relationships": [],
        "global_stats": {
            "total_papers": 1,
            "total_equations": len(arxiv_metadata.get("equations", [])),
            "total_citations": len(arxiv_metadata.get("citations", [])),
            "total_authors": len(arxiv_metadata.get("authors", [])),
            "total_relationships": 0
        }
    }
    
    with open(store_path / "consolidated.json", "w", encoding="utf-8") as f:
        json.dump(consolidated, f, indent=2)
    
    return {
        "tmp_path": tmp_path,
        "config": config,
        "store_manager": store_manager,
        "arxiv_pdf": temp_arxiv_pdf,
        "metadata": arxiv_metadata
    }

def test_show_metadata(runner, test_env):
    """Test showing metadata for a document"""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(metadata, ["show", "test_store", test_env["arxiv_pdf"].name])
        assert result.exit_code == 0
        assert "TSMixer: An All-MLP Architecture for Time Series Forecasting" in result.output
        assert "Real-world time-series datasets" in result.output

def test_extract_metadata(runner, test_env):
    """Test extracting metadata from a document."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(metadata, ["extract", "test_store", test_env["arxiv_pdf"].name, "--force"])
        assert result.exit_code == 0
        assert "Metadata extracted successfully" in result.output

def test_stats_command(runner, test_env):
    """Test showing metadata statistics for a store"""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(metadata, ["stats", "test_store"])
        assert result.exit_code == 0
        assert "Store Statistics" in result.output
        assert "Total Papers: 1" in result.output
        assert "Total Equations" in result.output
        assert "Total Citations" in result.output

def test_show_nonexistent_store(runner, test_env):
    """Test showing metadata from nonexistent store."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(metadata, ['show', 'nonexistent', test_env["arxiv_pdf"].name])
        assert result.exit_code != 0
        assert "not found" in result.output

def test_show_nonexistent_document(runner, test_env):
    """Test showing metadata for nonexistent document."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(metadata, ['show', 'test_store', 'nonexistent.pdf'])
        assert result.exit_code != 0
        assert "No metadata found" in result.output

def test_extract_nonexistent_store(runner, test_env):
    """Test extracting metadata from nonexistent store."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(metadata, ['extract', 'nonexistent', test_env["arxiv_pdf"].name])
        assert result.exit_code != 0
        assert "not found" in result.output

def test_extract_nonexistent_document(runner, test_env):
    """Test extracting metadata from nonexistent document."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(metadata, ['extract', 'test_store', 'nonexistent.pdf'])
        assert result.exit_code != 0
        assert "not found" in result.output

def test_consolidate_metadata(runner, test_env):
    """Test consolidating metadata in a store."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(metadata, ['consolidate', 'test_store'])
        assert result.exit_code == 0
        assert "Successfully consolidated metadata" in result.output

def test_consolidate_nonexistent_store(runner, test_env):
    """Test consolidating metadata in nonexistent store."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(metadata, ['consolidate', 'nonexistent'])
        assert result.exit_code != 0
        assert "not found" in result.output 