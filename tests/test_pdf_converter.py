import pytest
from unittest.mock import Mock, patch
from src.pdf_converter import PDFConverterFactory, PyMuPDFConverter, PyPDF2Converter
from src.config_manager import PDFEngine

@pytest.fixture
def sample_pdf():
    """Create a sample PDF file for testing"""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Test content")
    doc.save("test.pdf")
    yield "test.pdf"
    import os
    os.remove("test.pdf")

def test_pymupdf_converter(sample_pdf):
    """Test PyMuPDF converter functionality"""
    converter = PyMuPDFConverter()
    
    # Test text extraction
    text = converter.extract_text(sample_pdf)
    assert "Test content" in text
    
    # Test metadata extraction
    metadata = converter.extract_metadata(sample_pdf)
    assert isinstance(metadata, dict)

def test_pypdf2_converter(sample_pdf):
    """Test PyPDF2 converter functionality"""
    converter = PyPDF2Converter()
    
    # Test text extraction
    text = converter.extract_text(sample_pdf)
    assert "Test content" in text
    
    # Test metadata extraction
    metadata = converter.extract_metadata(sample_pdf)
    assert isinstance(metadata, dict)

def test_converter_factory():
    """Test PDF converter factory"""
    # Test PyMuPDF selection
    config = Mock()
    config.get_config.return_value.pdf_engine = PDFEngine.PYMUPDF
    converter = PDFConverterFactory.create_converter(config)
    assert isinstance(converter, PyMuPDFConverter)
    
    # Test PyPDF2 selection
    config.get_config.return_value.pdf_engine = PDFEngine.PYPDF2
    converter = PDFConverterFactory.create_converter(config)
    assert isinstance(converter, PyPDF2Converter)
    
    # Test auto selection
    config.get_config.return_value.pdf_engine = PDFEngine.AUTO
    with patch('src.pdf_converter.PyMuPDFConverter.extract_metadata') as mock_extract:
        # Test successful PyMuPDF
        converter = PDFConverterFactory.create_converter(config)
        assert isinstance(converter, PyMuPDFConverter)
        
        # Test fallback to PyPDF2
        mock_extract.side_effect = Exception("PyMuPDF error")
        converter = PDFConverterFactory.create_converter(config)
        assert isinstance(converter, PyPDF2Converter)

def test_converter_error_handling(sample_pdf):
    """Test error handling in converters"""
    # Test PyMuPDF error handling
    with patch('fitz.open', side_effect=Exception("Test error")):
        converter = PyMuPDFConverter()
        text = converter.extract_text(sample_pdf)
        assert text == ""
        metadata = converter.extract_metadata(sample_pdf)
        assert metadata == {}
    
    # Test PyPDF2 error handling
    with patch('PyPDF2.PdfReader', side_effect=Exception("Test error")):
        converter = PyPDF2Converter()
        text = converter.extract_text(sample_pdf)
        assert text == ""
        metadata = converter.extract_metadata(sample_pdf)
        assert metadata == {} 