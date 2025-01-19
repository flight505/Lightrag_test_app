"""Tests for store management commands."""
import json
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
    """Create a test environment with temporary directory."""
    config_dir = tmp_path / ".lightrag"
    config_dir.mkdir()
    config = ConfigManager(config_dir=config_dir)
    store_manager = StoreManager(config_dir=config_dir)
    return {"config": config, "store_manager": store_manager, "tmp_path": tmp_path}

def test_create_store(runner, test_env):
    """Test creating a new store."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(store, ['create', 'test_store'])
        assert result.exit_code == 0
        assert "Created store 'test_store'" in result.output
        
        # Verify store structure
        store_path = test_env["store_manager"].get_store("test_store")
        assert store_path.exists()
        assert (store_path / "metadata.json").exists()
        assert (store_path / "converted").exists()
        assert (store_path / "cache").exists()
        
        # Verify metadata
        with open(store_path / "metadata.json", 'r', encoding='utf-8') as f:
            metadata = json.load(f)
            assert metadata["name"] == "test_store"
            assert "created" in metadata
            assert "updated" in metadata
            assert metadata["documents"] == []

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
    """Test deleting a store."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        # Create store first
        runner.invoke(store, ['create', 'test_store'])
        
        # Delete with confirmation
        result = runner.invoke(store, ['delete', 'test_store'], input='y\n')
        assert result.exit_code == 0
        assert "Deleted store 'test_store'" in result.output
        
        # Verify store is gone
        store_path = test_env["store_manager"].store_root / "test_store"
        assert not store_path.exists()

def test_delete_nonexistent_store(runner, test_env):
    """Test deleting a store that doesn't exist."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(store, ['delete', 'nonexistent'])
        assert result.exit_code != 0
        assert "not found" in result.output

def test_list_stores(runner, test_env):
    """Test listing stores."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        # Create a couple of stores
        runner.invoke(store, ['create', 'store1'])
        runner.invoke(store, ['create', 'store2'])
        
        # List stores
        result = runner.invoke(store, ['list'])
        assert result.exit_code == 0
        assert "store1" in result.output
        assert "store2" in result.output

def test_list_empty_stores(runner, test_env):
    """Test listing stores when none exist."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(store, ['list'])
        assert result.exit_code == 0
        assert "No stores found" in result.output

def test_store_info(runner, test_env):
    """Test getting store information."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        # Create store
        runner.invoke(store, ['create', 'test_store'])
        
        # Get info
        result = runner.invoke(store, ['info', 'test_store'])
        assert result.exit_code == 0
        assert "Store: test_store" in result.output
        assert "Documents: 0" in result.output
        assert "MB" in result.output 