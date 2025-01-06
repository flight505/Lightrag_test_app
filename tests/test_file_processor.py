import pytest
from unittest.mock import Mock
from src.file_processor import FileProcessor
from src.config_manager import ConfigManager
from src.academic_metadata import AcademicMetadata

@pytest.fixture
def mock_config():
    """Create a mock configuration manager"""
    config = Mock(spec=ConfigManager)
    config.validate_file.return_value = None
    config.get_config.return_value.debug_mode = False
    return config

@pytest.fixture
def mock_pdf():
    """Create a mock PDF file"""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Test content")
    page.insert_text((50, 100), "Author: John Doe")
    page.insert_text((50, 150), "Abstract: This is a test document")
    doc.save("test.pdf")
    yield "test.pdf"
    import os
    os.remove("test.pdf")

def test_file_processor_initialization(mock_config):
    """Test FileProcessor initialization"""
    processor = FileProcessor(mock_config)
    assert processor.config_manager == mock_config
    assert processor.pdf_converter is not None
    assert processor.metadata_extractor is not None

def test_process_valid_file(mock_config, mock_pdf):
    """Test processing a valid PDF file"""
    processor = FileProcessor(mock_config)
    
    result = processor.process_file(mock_pdf)
    
    assert "error" not in result
    assert "text" in result
    assert "metadata" in result
    assert "academic_metadata" in result
    assert isinstance(result["academic_metadata"], AcademicMetadata)
    assert "Test content" in result["text"]

def test_process_invalid_file(mock_config):
    """Test processing an invalid file"""
    mock_config.validate_file.return_value = "Invalid file"
    processor = FileProcessor(mock_config)
    
    result = processor.process_file("invalid.pdf")
    
    assert "error" in result
    assert result["error"] == "Invalid file"

def test_process_file_with_extraction_error(mock_config, mock_pdf):
    """Test handling of extraction errors"""
    processor = FileProcessor(mock_config)
    
    # Mock PDF converter to raise an exception
    processor.pdf_converter.extract_text.side_effect = Exception("Extraction error")
    
    result = processor.process_file(mock_pdf)
    assert "error" in result
    assert "Extraction error" in result["error"]

def test_supported_file_types():
    """Test file type support checking"""
    processor = FileProcessor()
    
    assert processor.is_supported_file("test.pdf")
    assert processor.is_supported_file("test.PDF")
    assert not processor.is_supported_file("test.doc")
    assert not processor.is_supported_file("test.txt") 