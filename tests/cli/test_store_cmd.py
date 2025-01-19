"""Tests for store management commands."""
import json
import os
import shutil
from pathlib import Path
import pytest
from click.testing import CliRunner

from cli.commands.store_cmd import store
from cli.core.store_manager import StoreManager
from cli.core.config import ConfigManager

@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()

@pytest.fixture
def test_env(tmp_path):
    """Create test environment."""
    # Set up config directory
    config_dir = tmp_path / ".lightrag"
    config_dir.mkdir(exist_ok=True)
    os.environ["LIGHTRAG_CONFIG_DIR"] = str(config_dir)
    
    # Set up config
    config = ConfigManager(config_dir=config_dir)
    store_root = config_dir / "stores"
    store_root.mkdir(exist_ok=True)
    
    # Set up store manager
    store_manager = StoreManager(config_dir=config_dir)
    
    # Copy test PDFs to temp directory
    pdf_dir = Path("tests/pdfs")
    temp_pdf_dir = tmp_path / "pdfs"
    temp_pdf_dir.mkdir(exist_ok=True)
    
    arxiv_pdf = pdf_dir / "Chen et al. - 2023 - TSMixer An All-MLP Architecture for Time Series Forecasting-annotated.pdf"
    metadata_file = pdf_dir / "Chen et al. - 2023 - TSMixer An All-MLP Architecture for Time Series Forecasting-annotated_metadata.json"
    
    temp_arxiv_pdf = temp_pdf_dir / arxiv_pdf.name
    temp_metadata_file = temp_pdf_dir / metadata_file.name
    
    shutil.copy2(arxiv_pdf, temp_arxiv_pdf)
    shutil.copy2(metadata_file, temp_metadata_file)
    
    with open(metadata_file, encoding="utf-8") as f:
        arxiv_metadata = json.load(f)
    
    return {
        "tmp_path": tmp_path,
        "config": config,
        "store_manager": store_manager,
        "arxiv_pdf": temp_arxiv_pdf,
        "metadata": arxiv_metadata
    }

def test_create_store(runner, test_env):
    """Test store creation."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(store, ['create', 'test_store'])
        assert result.exit_code == 0
        assert "Store created successfully" in result.output
        
        store_path = test_env["config"].config_dir / "stores" / "test_store"
        assert store_path.exists()
        assert (store_path / "converted").exists()
        assert (store_path / "cache").exists()
        assert (store_path / "metadata.json").exists()

def test_create_existing_store(runner, test_env):
    """Test creating a store that already exists."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        # Create store first
        runner.invoke(store, ['create', 'test_store'])
        
        # Try to create again
        result = runner.invoke(store, ['create', 'test_store'])
        assert result.exit_code != 0
        assert "already exists" in result.output

def test_delete_store(runner, test_env):
    """Test store deletion."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        # Create a test store first
        result = runner.invoke(store, ['create', 'test_store'])
        assert result.exit_code == 0
        
        store_path = test_env["config"].config_dir / "stores" / "test_store"
        
        # Copy test PDF to store
        shutil.copy2(test_env["arxiv_pdf"], store_path)
        
        # Update store metadata
        metadata = test_env["store_manager"].get_store_info("test_store")
        metadata["document_count"] = 1
        metadata["size"] = os.path.getsize(test_env["arxiv_pdf"])
        metadata["documents"] = [test_env["arxiv_pdf"].name]
        test_env["store_manager"].update_store_metadata("test_store", metadata)
        
        result = runner.invoke(store, ['delete', 'test_store', '--force'])
        assert result.exit_code == 0
        assert "Store deleted successfully" in result.output
        assert not store_path.exists()

def test_delete_nonexistent_store(runner, test_env):
    """Test deleting a store that doesn't exist."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(store, ['delete', 'nonexistent', '--force'])
        assert result.exit_code != 0
        assert "not found" in result.output

def test_list_stores(runner, test_env):
    """Test listing stores."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        # Create a test store first
        result = runner.invoke(store, ['create', 'test_store'])
        assert result.exit_code == 0
        
        result = runner.invoke(store, ['list'])
        assert result.exit_code == 0
        assert "test_store" in result.output

def test_list_empty_stores(runner, test_env):
    """Test listing stores when none exist."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(store, ['list'])
        assert result.exit_code == 0
        assert "No stores found" in result.output

def test_store_info(runner, test_env):
    """Test getting store information."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        # Create store with real PDF
        result = runner.invoke(store, ['create', 'test_store'])
        assert result.exit_code == 0
        
        store_path = test_env["config"].config_dir / "stores" / "test_store"
        
        # Copy test PDF to store
        shutil.copy2(test_env["arxiv_pdf"], store_path)
        
        # Update store metadata
        metadata = test_env["store_manager"].get_store_info("test_store")
        metadata["document_count"] = 1
        metadata["size"] = os.path.getsize(test_env["arxiv_pdf"])
        metadata["documents"] = [test_env["arxiv_pdf"].name]
        test_env["store_manager"].update_store_metadata("test_store", metadata)
        
        result = runner.invoke(store, ['info', 'test_store'])
        assert result.exit_code == 0
        assert "test_store" in result.output
        assert "Documents: 1" in result.output

def test_show_store(runner, test_env):
    """Test showing store details."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        # Create a test store first
        result = runner.invoke(store, ['create', 'test_store'])
        assert result.exit_code == 0
        
        store_path = test_env["config"].config_dir / "stores" / "test_store"
        
        # Copy test PDF to store
        shutil.copy2(test_env["arxiv_pdf"], store_path)
        
        # Update store metadata
        metadata = test_env["store_manager"].get_store_info("test_store")
        metadata["document_count"] = 1
        metadata["size"] = os.path.getsize(test_env["arxiv_pdf"])
        metadata["documents"] = [test_env["arxiv_pdf"].name]
        test_env["store_manager"].update_store_metadata("test_store", metadata)
        
        result = runner.invoke(store, ['info', 'test_store'])
        assert result.exit_code == 0
        assert "test_store" in result.output
        assert "Documents: 1" in result.output 