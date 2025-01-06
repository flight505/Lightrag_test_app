import os
from src.config_manager import ConfigManager, PDFEngine, ProcessingConfig

def test_default_config():
    """Test default configuration loading"""
    config_manager = ConfigManager()
    config = config_manager.get_config()
    
    assert isinstance(config, ProcessingConfig)
    assert config.pdf_engine == PDFEngine.AUTO
    assert config.enable_crossref is True
    assert config.enable_scholarly is True
    assert config.debug_mode is False
    assert config.max_file_size_mb == 50
    assert config.timeout_seconds == 30

def test_environment_config():
    """Test configuration loading from environment variables"""
    os.environ["PDF_ENGINE"] = "pymupdf"
    os.environ["ENABLE_CROSSREF"] = "0"
    os.environ["DEBUG_MODE"] = "1"
    os.environ["MAX_FILE_SIZE_MB"] = "100"
    
    config_manager = ConfigManager()
    config = config_manager.get_config()
    
    assert config.pdf_engine == PDFEngine.PYMUPDF
    assert config.enable_crossref is False
    assert config.debug_mode is True
    assert config.max_file_size_mb == 100

def test_file_validation():
    """Test file validation logic"""
    config_manager = ConfigManager()
    
    # Test non-existent file
    error = config_manager.validate_file("nonexistent.pdf")
    assert error == "File does not exist"
    
    # Create a temporary test file
    with open("test.pdf", "w") as f:
        f.write("x" * (51 * 1024 * 1024))  # Create a 51MB file
    
    try:
        error = config_manager.validate_file("test.pdf")
        assert "exceeds limit" in error
    finally:
        os.remove("test.pdf")

def test_invalid_config():
    """Test handling of invalid configuration"""
    os.environ["MAX_FILE_SIZE_MB"] = "invalid"
    
    config_manager = ConfigManager()
    config = config_manager.get_config()
    
    # Should fall back to default values
    assert config.max_file_size_mb == 50 