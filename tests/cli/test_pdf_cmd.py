"""Tests for PDF processing commands."""
import os
import pytest
from pathlib import Path
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
    """Create test environment with config and store manager."""
    # Set up test config directory
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    os.environ["LIGHTRAG_CONFIG_DIR"] = str(config_dir)
    
    # Create test PDF file with content
    test_pdf = tmp_path / "test.pdf"
    with open(test_pdf, "wb") as f:
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
        content = b"BT\n/F1 12 Tf\n72 700 Td\n(Test Document Title) Tj\n0 -20 Td\n(Author: John Doe) Tj\n0 -20 Td\n(Abstract: This is a test document for LightRAG.) Tj\nET"
        f.write(f"5 0 obj\n<</Length {len(content)}>>\nstream\n{content}\nendstream\nendobj\n".encode())
        # Cross-reference table
        f.write(b"xref\n0 6\n0000000000 65535 f\n0000000009 00000 n\n0000000056 00000 n\n0000000111 00000 n\n0000000212 00000 n\n0000000277 00000 n\n")
        # Trailer
        f.write(b"trailer\n<</Size 6/Root 1 0 R>>\nstartxref\n408\n%%EOF\n")
    
    # Initialize managers
    config = ConfigManager()
    store_manager = StoreManager(config_dir=config.config_dir)
    
    # Create test store
    store_manager.create_store("test_store")
    
    return {
        "tmp_path": tmp_path,
        "config": config,
        "store_manager": store_manager,
        "test_pdf": test_pdf
    }

def test_process_pdf(runner, test_env):
    """Test processing a PDF file."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(pdf, ['process', str(test_env["test_pdf"]), 'test_store'])
        assert result.exit_code == 0
        assert "Successfully processed test.pdf" in result.output

def test_process_nonexistent_pdf(runner, test_env):
    """Test processing a nonexistent PDF file."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(pdf, ['process', 'nonexistent.pdf', 'test_store'])
        assert result.exit_code != 0
        assert "Error" in result.output

def test_process_nonexistent_store(runner, test_env):
    """Test processing a PDF into a nonexistent store."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(pdf, ['process', str(test_env["test_pdf"]), 'nonexistent'])
        assert result.exit_code != 0
        assert "not found" in result.output

def test_list_pdfs(runner, test_env):
    """Test listing PDFs in a store."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        # First process a PDF
        runner.invoke(pdf, ['process', str(test_env["test_pdf"]), 'test_store'])
        
        # Then list PDFs
        result = runner.invoke(pdf, ['list', 'test_store'])
        assert result.exit_code == 0
        assert "test.pdf" in result.output

def test_list_empty_store(runner, test_env):
    """Test listing PDFs in an empty store."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(pdf, ['list', 'test_store'])
        assert result.exit_code == 0
        assert "No documents found" in result.output

def test_pdf_info(runner, test_env):
    """Test getting PDF information."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        # First process a PDF
        runner.invoke(pdf, ['process', str(test_env["test_pdf"]), 'test_store'])
        
        # Then get info
        result = runner.invoke(pdf, ['info', 'test_store', 'test.pdf'])
        assert result.exit_code == 0
        assert "Document: test.pdf" in result.output

def test_pdf_info_nonexistent(runner, test_env):
    """Test getting info for a nonexistent PDF."""
    with runner.isolated_filesystem(temp_dir=test_env["tmp_path"]):
        result = runner.invoke(pdf, ['info', 'test_store', 'nonexistent.pdf'])
        assert result.exit_code != 0
        assert "not found" in result.output 