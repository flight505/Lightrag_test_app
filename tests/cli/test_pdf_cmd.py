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
from cli.core.errors import StoreError
from datetime import datetime

@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()

@pytest.fixture
def test_env(tmp_path, request):
    """Setup test environment with sample PDFs and store."""
    # Create unique store name for each test
    store_name = f"test_store_{request.node.name}"
    
    # Setup test store
    config = ConfigManager()
    config.config_dir = tmp_path  # Override config dir for testing
    store_manager = StoreManager(config_dir=tmp_path)
    
    # Create store with proper structure
    try:
        store_path = store_manager.create_store(store_name)
        print(f"Created store at {store_path}")
        
        # Create required directories
        required_dirs = ["documents", "metadata", "converted", "cache", "exports"]
        for dir_name in required_dirs:
            (store_path / dir_name).mkdir(exist_ok=True)
        
        # Create required files
        metadata = {
            "name": store_name,
            "created": datetime.now().isoformat(),
            "files": {},
            "last_updated": None,
            "document_count": 0,
            "size": 0,
            "documents": []
        }
        with open(store_path / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
            
        consolidated = {
            "store_info": {
                "name": store_name,
                "created": datetime.now().isoformat(),
                "last_updated": None,
                "version": "1.0.0"
            },
            "nodes": {
                "papers": [],
                "equations": [],
                "citations": [],
                "authors": [],
                "contexts": []
            },
            "relationships": [],
            "global_stats": {
                "total_papers": 0,
                "total_equations": 0,
                "total_citations": 0,
                "total_authors": 0,
                "total_relationships": 0
            }
        }
        with open(store_path / "consolidated.json", "w", encoding="utf-8") as f:
            json.dump(consolidated, f, indent=2)
        
        # Verify store structure
        assert store_path.exists(), "Store directory not created"
        assert (store_path / "documents").exists(), "Documents directory not created"
        assert (store_path / "metadata").exists(), "Metadata directory not created"
        assert (store_path / "converted").exists(), "Converted directory not created"
        assert (store_path / "cache").exists(), "Cache directory not created"
        assert (store_path / "exports").exists(), "Exports directory not created"
        assert (store_path / "metadata.json").exists(), "Metadata file not created"
        assert (store_path / "consolidated.json").exists(), "Consolidated file not created"
    except StoreError as e:
        pytest.fail(f"Failed to create store: {e}")
    
    # Setup test PDF
    source_pdf = Path("tests/pdfs/Chen et al. - 2023 - TSMixer An All-MLP Architecture for Time Series Forecasting-annotated.pdf")
    assert source_pdf.exists(), "Test PDF not found"
    
    # Copy PDF to temp directory
    test_pdf = tmp_path / source_pdf.name
    shutil.copy2(source_pdf, test_pdf)
    
    # Create test environment dict
    env = {
        "tmp_path": tmp_path,
        "config": config,
        "store_manager": store_manager,
        "store_name": store_name,
        "arxiv_pdf": test_pdf
    }
    
    yield env
    
    # Cleanup after test
    try:
        store_path = tmp_path / "stores" / store_name
        if store_path.exists():
            shutil.rmtree(store_path)
            print(f"Cleaned up store at {store_path}")
        
        # Clean up any temporary files
        for temp_file in tmp_path.glob("*.pdf"):
            temp_file.unlink()
            print(f"Cleaned up temporary file {temp_file}")
            
    except Exception as e:
        print(f"Cleanup warning: {e}")

def test_process_pdf(runner, test_env):
    """Test processing a PDF file."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        # Process PDF
        result = runner.invoke(pdf, ['process', str(test_env["arxiv_pdf"]), test_env["store_name"]], obj=test_env["config"])
        
        # Validate result
        assert result.exit_code == 0, f"Command failed with error: {result.output}"
        assert "Processing PDF" in result.output
        assert "Completed successfully" in result.output
        
        # Verify file was processed
        store_path = test_env["tmp_path"] / "stores" / test_env["store_name"]
        assert (store_path / "metadata").exists()
        assert any((store_path / "metadata").glob("*.json"))
        assert (store_path / "documents").exists()
        assert any((store_path / "documents").glob("*.pdf"))

def test_list_pdfs(runner, test_env):
    """Test listing PDFs in a store."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        # First process a PDF
        runner.invoke(pdf, ['process', str(test_env["arxiv_pdf"]), test_env["store_name"]], obj=test_env["config"])
        
        # List PDFs
        result = runner.invoke(pdf, ['list', test_env["store_name"]], obj=test_env["config"])
        
        # Validate output
        assert result.exit_code == 0
        assert "TSMixer" in result.output
        assert "Time Series Forecasting" in result.output
        assert "Chen et al." in result.output

def test_convert_pdf(runner, test_env):
    """Test PDF conversion."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(pdf, ['convert', str(test_env["arxiv_pdf"]), test_env["store_name"]], obj=test_env["config"])
        
        # Validate result
        assert result.exit_code == 0, f"Command failed with error: {result.output}"
        assert "Converting PDF" in result.output
        assert "Conversion complete" in result.output
        
        # Verify conversion output
        store_path = test_env["tmp_path"] / "stores" / test_env["store_name"]
        assert (store_path / "converted").exists()
        assert any((store_path / "converted").glob("*.txt"))

def test_pdf_info(runner, test_env):
    """Test getting PDF information."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        # First process the PDF
        runner.invoke(pdf, ['process', str(test_env["arxiv_pdf"]), test_env["store_name"]], obj=test_env["config"])
        
        # Get info
        result = runner.invoke(pdf, ['info', str(test_env["arxiv_pdf"]), test_env["store_name"]], obj=test_env["config"])
        
        # Validate output
        assert result.exit_code == 0
        assert "Title:" in result.output
        assert "Authors:" in result.output
        assert "TSMixer" in result.output

def test_pdf_info_nonexistent(runner, test_env):
    """Test getting info for nonexistent PDF."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(pdf, ['info', 'nonexistent.pdf', test_env["store_name"]], obj=test_env["config"])
        assert result.exit_code == 1
        assert "Error" in result.output

def test_process_nonexistent_pdf(runner, test_env):
    """Test processing nonexistent PDF."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(pdf, ['process', 'nonexistent.pdf', test_env["store_name"]], obj=test_env["config"])
        assert result.exit_code == 1
        assert "Error" in result.output

def test_process_nonexistent_store(runner, test_env):
    """Test processing PDF to nonexistent store."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(pdf, ['process', str(test_env["arxiv_pdf"]), 'nonexistent_store'], obj=test_env["config"])
        assert result.exit_code == 1
        assert "Error" in result.output

def test_list_empty_store(runner, test_env):
    """Test listing PDFs in empty store."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(pdf, ['list', test_env["store_name"]], obj=test_env["config"])
        assert result.exit_code == 0
        assert "No PDFs found" in result.output 