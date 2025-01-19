"""Tests for PDF processing commands."""
import os
import json
import shutil
from pathlib import Path
import pytest
from click.testing import CliRunner
from cli.commands.pdf_cmd import pdf
from cli.core.config import ConfigManager
from cli.core.store_manager import StoreManager

@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()

@pytest.fixture
def test_env(tmp_path):
    """Create test environment."""
    # Set up config
    config = ConfigManager()
    config.store_root = tmp_path
    
    # Set up store manager
    store_manager = StoreManager(config)
    
    # Copy test PDFs
    pdf_dir = Path("tests/pdfs")
    arxiv_pdf = pdf_dir / "Chen et al. - 2023 - TSMixer An All-MLP Architecture for Time Series Forecasting-annotated.pdf"
    metadata_file = pdf_dir / "Chen et al. - 2023 - TSMixer An All-MLP Architecture for Time Series Forecasting-annotated_metadata.json"
    
    with open(metadata_file, encoding="utf-8") as f:
        arxiv_metadata = json.load(f)
    
    # Create test store
    store_path = config.get_store_root() / "test_store"
    store_path.mkdir(parents=True, exist_ok=True)
    (store_path / "converted").mkdir(exist_ok=True)
    (store_path / "cache").mkdir(exist_ok=True)
    
    # Copy PDF to store
    shutil.copy(arxiv_pdf, store_path)
    
    # Create metadata
    metadata = {
        "documents": {
            arxiv_pdf.name: arxiv_metadata
        }
    }
    with open(store_path / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f)
    
    return {
        "tmp_path": tmp_path,
        "config": config,
        "store_manager": store_manager,
        "arxiv_pdf": arxiv_pdf,
        "metadata": arxiv_metadata,
        "store_path": store_path
    }

def test_process_pdf(runner, test_env):
    """Test processing a PDF file."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(pdf, ['process', str(test_env["arxiv_pdf"]), 'test_store'])
        assert result.exit_code == 0
        assert "Successfully processed" in result.output
        assert "TSMixer: An All-MLP Architecture for Time Series Forecasting" in result.output

def test_process_nonexistent_pdf(runner, test_env):
    """Test processing a nonexistent PDF file."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(pdf, ['process', 'nonexistent.pdf', 'test_store'])
        assert result.exit_code != 0
        assert "Error" in result.output

def test_process_nonexistent_store(runner, test_env):
    """Test processing a PDF into a nonexistent store."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(pdf, ['process', str(test_env["arxiv_pdf"]), 'nonexistent'])
        assert result.exit_code != 0
        assert "not found" in result.output

def test_list_pdfs(runner, test_env):
    """Test listing PDFs in a store."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(pdf, ['list', 'test_store'])
        assert result.exit_code == 0
        assert "TSMixer: An All-MLP Architecture for Time Series Forecasting" in result.output
        assert "Real-world time-series datasets" in result.output

def test_list_empty_store(runner, test_env):
    """Test listing PDFs in an empty store."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        # Create empty store
        empty_store = "empty_store"
        test_env["store_manager"].create_store(empty_store)
        result = runner.invoke(pdf, ['list', empty_store])
        assert result.exit_code == 0
        assert "No documents found" in result.output

def test_pdf_info(runner, test_env):
    """Test getting PDF information."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(pdf, ['info', 'test_store', test_env["arxiv_pdf"].name])
        assert result.exit_code == 0
        assert "TSMixer: An All-MLP Architecture for Time Series Forecasting" in result.output
        assert "Real-world time-series datasets" in result.output
        assert "Equations:" in result.output

def test_pdf_info_nonexistent(runner, test_env):
    """Test getting info for a nonexistent PDF."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(pdf, ['info', 'test_store', 'nonexistent.pdf'])
        assert result.exit_code != 0
        assert "not found" in result.output

def test_extract_metadata(runner, test_env):
    """Test metadata extraction."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(pdf, ['extract', str(test_env["arxiv_pdf"]), 'test_store'])
        assert result.exit_code == 0
        assert "Metadata extracted successfully" in result.output
        
        # Verify metadata was saved
        metadata_file = test_env["store_path"] / "metadata.json"
        assert metadata_file.exists()
        
        with open(metadata_file, encoding="utf-8") as f:
            metadata = json.load(f)
            doc_metadata = metadata["documents"][test_env["arxiv_pdf"].name]
            assert doc_metadata["title"] == "TSMixer: An All-MLP Architecture for Time Series Forecasting"
            assert len(doc_metadata["authors"]) > 0
            assert len(doc_metadata["references"]) > 0
            assert len(doc_metadata["equations"]) > 0

def test_show_metadata(runner, test_env):
    """Test showing metadata."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(pdf, ['show', str(test_env["arxiv_pdf"]), 'test_store'])
        assert result.exit_code == 0
        assert "Document Metadata" in result.output
        assert "TSMixer" in result.output
        assert "Authors" in result.output
        assert "References" in result.output
        assert "Equations" in result.output

def test_convert_pdf(runner, test_env):
    """Test PDF conversion."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(pdf, ['convert', str(test_env["arxiv_pdf"]), 'test_store'])
        assert result.exit_code == 0
        assert "PDF converted successfully" in result.output
        
        # Verify converted file exists
        converted_file = test_env["store_path"] / "converted" / f"{test_env['arxiv_pdf'].stem}.txt"
        assert converted_file.exists()
        
        # Check content
        with open(converted_file, encoding="utf-8") as f:
            content = f.read()
            assert "TSMixer" in content
            assert "time series forecasting" in content 