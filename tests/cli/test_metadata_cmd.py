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
    os.environ["LIGHTRAG_CONFIG_DIR"] = str(tmp_path / "config")
    
    config = ConfigManager()
    store_manager = StoreManager(config_dir=config.config_dir)
    
    store_path = config.get_store_root() / "test_store"
    store_path.mkdir(parents=True, exist_ok=True)
    (store_path / "documents").mkdir(exist_ok=True)
    (store_path / "metadata").mkdir(exist_ok=True)
    
    # Copy test PDFs from tests/pdfs to store
    pdf_dir = Path("tests/pdfs")
    arxiv_pdf = pdf_dir / "Chen et al. - 2023 - TSMixer An All-MLP Architecture for Time Series Forecasting-annotated.pdf"
    doi_pdf = pdf_dir / "Choo et al. - 2023 - Deep-learning-based personalized prediction of absolute neutrophil count recovery and comparison with clinicians-annotated.pdf"
    
    # Copy PDFs to store
    shutil.copy2(arxiv_pdf, store_path / "documents" / arxiv_pdf.name)
    shutil.copy2(doi_pdf, store_path / "documents" / doi_pdf.name)
    
    # Load existing metadata for mocking
    arxiv_metadata_path = pdf_dir / f"{arxiv_pdf.stem}_metadata.json"
    with open(arxiv_metadata_path, 'r', encoding='utf-8') as f:
        arxiv_metadata = json.load(f)
    
    # Create mock extractor that returns real metadata
    mock_extractor = MagicMock()
    mock_extractor.extract_metadata.return_value = AcademicMetadata(**arxiv_metadata)
    
    # Create mock consolidator with real data
    mock_consolidator = MagicMock()
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
    mock_consolidator._load_json.return_value = consolidated
    mock_consolidator.initialize_consolidated_json.return_value = None
    
    return {
        "tmp_path": tmp_path,
        "config": config,
        "store_manager": store_manager,
        "metadata": arxiv_metadata,
        "consolidated": consolidated,
        "mock_extractor": mock_extractor,
        "mock_consolidator": mock_consolidator,
        "arxiv_pdf": arxiv_pdf,
        "doi_pdf": doi_pdf
    }

@patch("cli.commands.metadata_cmd.MetadataExtractor")
def test_show_metadata(mock_extractor_cls, test_env):
    """Test showing metadata for a document"""
    mock_extractor_cls.return_value = test_env["mock_extractor"]
    
    runner = CliRunner()
    result = runner.invoke(metadata, ["show", "test_store", test_env["arxiv_pdf"].name])
    
    assert result.exit_code == 0
    assert "TSMixer: An All-MLP Architecture for Time Series Forecasting" in result.output
    assert "Real-world time-series datasets" in result.output

def test_extract_metadata(test_env):
    """Test extracting metadata from a document."""
    runner = CliRunner()
    with patch("src.metadata_extractor.MetadataExtractor", return_value=test_env["mock_extractor"]):
        with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
            result = runner.invoke(metadata, ["extract", "test_store", test_env["arxiv_pdf"].name])
            assert result.exit_code == 0
            assert "Metadata extracted successfully" in result.output

@patch("cli.commands.metadata_cmd.MetadataConsolidator")
def test_stats_command(mock_consolidator_cls, test_env):
    """Test showing metadata statistics for a store"""
    mock_consolidator_cls.return_value = test_env["mock_consolidator"]
    
    runner = CliRunner()
    result = runner.invoke(metadata, ["stats", "test_store"])
    
    assert result.exit_code == 0
    assert "Store Statistics" in result.output
    assert "Total Papers" in result.output
    assert "Total Equations" in result.output
    assert "Total Citations" in result.output

def test_show_nonexistent_store(runner, test_env):
    """Test showing metadata from nonexistent store."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(metadata, ['show', 'nonexistent', test_env["arxiv_pdf"]])
        assert result.exit_code == 1
        assert "not found" in result.output

def test_show_nonexistent_document(runner, test_env):
    """Test showing metadata for nonexistent document."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(metadata, ['show', 'test_store', 'nonexistent.pdf'])
        assert result.exit_code == 1
        assert "No metadata found" in result.output

def test_extract_nonexistent_store(runner, test_env):
    """Test extracting metadata from nonexistent store."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(metadata, ['extract', 'nonexistent', test_env["arxiv_pdf"]])
        assert result.exit_code == 1
        assert "not found" in result.output

def test_extract_nonexistent_document(runner, test_env):
    """Test extracting metadata from nonexistent document."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(metadata, ['extract', 'test_store', 'nonexistent.pdf'])
        assert result.exit_code == 1
        assert "not found" in result.output

def test_consolidate_metadata(test_env):
    """Test consolidating metadata in a store."""
    runner = CliRunner()
    with patch("cli.commands.metadata_cmd.MetadataConsolidator", return_value=test_env["mock_consolidator"]):
        with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
            result = runner.invoke(metadata, ['consolidate', 'test_store'])
            assert result.exit_code == 0
            assert "Successfully consolidated metadata" in result.output

def test_consolidate_nonexistent_store(runner, test_env):
    """Test consolidating metadata in nonexistent store."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(metadata, ['consolidate', 'nonexistent'])
        assert result.exit_code == 1
        assert "not found" in result.output 