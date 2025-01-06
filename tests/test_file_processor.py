import pytest
from pathlib import Path
import json
from src.file_processor import FileProcessor
from src.config_manager import ConfigManager
from unittest.mock import Mock, patch
import fitz
from PyPDF2 import PdfReader

@pytest.fixture
def config_manager():
    return ConfigManager()

@pytest.fixture
def file_processor(config_manager):
    return FileProcessor(config_manager)

@pytest.fixture
def sample_pdf(test_dir):
    # Create a sample PDF for testing
    pdf_path = test_dir / "test.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Test Title\nAuthor: John Doe\nAbstract: Test abstract")
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path

def test_doi_extraction(file_processor, sample_pdf):
    """Test DOI-based metadata extraction"""
    with patch('pdf2doi.pdf2doi') as mock_pdf2doi:
        mock_pdf2doi.return_value = "10.1234/test"
        with patch('crossref.restful.Works.doi') as mock_doi:
            mock_doi.return_value = {
                'title': ['Test Paper'],
                'author': [{'given': 'John', 'family': 'Doe'}],
                'published-print': {'date-parts': [[2023]]},
                'container-title': ['Test Journal']
            }
            
            metadata = file_processor._extract_metadata_with_doi(str(sample_pdf))
            
            assert metadata is not None
            assert metadata['title'] == 'Test Paper'
            assert metadata['authors'][0]['given'] == 'John'
            assert metadata['year'] == 2023

def test_fallback_metadata_extraction(file_processor, sample_pdf):
    """Test fallback metadata extraction chain"""
    with patch('scholarly.search_pubs') as mock_search:
        mock_search.return_value = iter([{
            'bib': {
                'title': 'Test Title',
                'author': 'John Doe',
                'year': '2023',
                'journal': 'Test Journal',
                'abstract': 'Test abstract'
            }
        }])
        
        metadata = file_processor._extract_metadata_fallback(str(sample_pdf), "Test content")
        
        assert metadata is not None
        assert 'title' in metadata
        assert 'authors' in metadata
        assert 'year' in metadata

def test_marker_text_extraction(file_processor, sample_pdf):
    """Test Marker text extraction with fallback"""
    text = file_processor._convert_pdf_with_marker(str(sample_pdf))
    assert text is not None
    assert "Test Title" in text

def test_complete_file_processing(file_processor, sample_pdf):
    """Test complete file processing workflow"""
    result = file_processor.process_file(str(sample_pdf))
    
    assert result is not None
    assert 'text' in result
    assert 'metadata' in result
    assert 'academic_metadata' in result
    assert result['text'] is not None

def test_error_handling(file_processor):
    """Test error handling for invalid files"""
    result = file_processor.process_file("nonexistent.pdf")
    assert 'error' in result

def test_progress_callback(file_processor, sample_pdf):
    """Test progress callback functionality"""
    progress_updates = []
    def progress_callback(msg):
        progress_updates.append(msg)
    
    file_processor.process_file(str(sample_pdf), progress_callback=progress_callback)
    
    assert len(progress_updates) > 0
    assert "Converting PDF..." in progress_updates
    assert "Extracting metadata..." in progress_updates 

def test_reference_extraction(file_processor, sample_pdf):
    """Test reference extraction with Anystyle"""
    # Create a PDF with references
    pdf_path = sample_pdf.parent / "test_refs.pdf"
    doc = fitz.open()
    page = doc.new_page()
    
    # Add some test content with references
    content = """
    Test Title
    Author: John Doe
    
    Abstract: Test abstract
    
    References:
    Smith, J. (2020). Test paper. Journal of Testing, 1(1), 1-10.
    Doe, J. (2021). Another paper. Testing Review, 2(2), 20-30.
    """
    page.insert_text((50, 50), content)
    doc.save(str(pdf_path))
    doc.close()
    
    # Process the file
    result = file_processor.process_file(str(pdf_path))
    
    # Check results
    assert result is not None
    assert 'academic_metadata' in result
    assert 'references' in result['academic_metadata']
    refs = result['academic_metadata']['references']
    assert len(refs) > 0
    
    # Check reference structure
    ref = refs[0]
    assert 'authors' in ref
    assert 'title' in ref
    assert 'year' in ref
    assert 'journal' in ref
    assert 'raw' in ref  # Original text should be preserved 