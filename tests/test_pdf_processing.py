import pytest
from pathlib import Path
from termcolor import colored
from src.file_processor import FileProcessor
from src.config_manager import ConfigManager
from src.academic_metadata import MetadataExtractor, PDFMetadataExtractor

# Test PDF path
TEST_PDF = Path("store/pdfs/Pharmacokinetic–pharmacodynamic modeling of maintenance therapy for childhood acute lymphoblastic leukemia.pdf")

@pytest.fixture
def file_processor():
    """Initialize FileProcessor with configuration"""
    config = ConfigManager()
    return FileProcessor(config)

@pytest.mark.skipif(not TEST_PDF.exists(), reason="Test PDF not found")
def test_pdf_metadata_extraction():
    """Test PDF metadata extraction"""
    extractor = PDFMetadataExtractor(debug=True)
    
    # Extract metadata from PDF
    metadata = extractor.extract_from_pdf(str(TEST_PDF))
    assert metadata is not None, "Metadata extraction failed"
    
    title, authors, abstract, doi = metadata
    
    # Verify metadata components
    assert title, "Title should not be empty"
    assert authors, "Authors should not be empty"
    print(colored(f"✓ Found title: {title}", "green"))
    print(colored(f"✓ Found {len(authors)} authors", "green"))
    if doi:
        print(colored(f"✓ Found DOI: {doi}", "green"))
    if abstract:
        print(colored(f"✓ Found abstract ({len(abstract)} chars)", "green"))

@pytest.mark.skipif(not TEST_PDF.exists(), reason="Test PDF not found")
def test_academic_metadata_processing(file_processor):
    """Test academic metadata processing"""
    # Process the PDF file
    result = file_processor.process_file(str(TEST_PDF))
    assert "error" not in result, f"Processing failed: {result.get('error')}"
    
    # Verify academic metadata
    academic_metadata = result["academic_metadata"]
    assert academic_metadata, "Academic metadata should not be empty"
    
    # Check essential components
    assert academic_metadata["title"], "Title should be present"
    assert academic_metadata["authors"], f"Authors should be present, found: {academic_metadata['authors']}"
    assert academic_metadata["references"], "References should be present"
    
    # Print findings
    print(colored("\nAcademic Metadata Results:", "cyan"))
    print(colored(f"✓ Title: {academic_metadata['title']}", "green"))
    print(colored(f"✓ Authors: {len(academic_metadata['authors'])}", "green"))
    print(colored(f"✓ References: {len(academic_metadata['references'])}", "green"))
    print(colored(f"✓ Citations: {len(academic_metadata['citations'])}", "green"))
    print(colored(f"✓ Equations: {len(academic_metadata['equations'])}", "green"))

@pytest.mark.skipif(not TEST_PDF.exists(), reason="Test PDF not found")
def test_text_extraction(file_processor):
    """Test text extraction and conversion"""
    result = file_processor.process_file(str(TEST_PDF))
    assert "error" not in result, f"Processing failed: {result.get('error')}"
    
    # Verify text extraction
    text = result["text"]
    assert text, "Extracted text should not be empty"
    assert len(text) > 1000, "Extracted text seems too short"
    
    # Check for common academic paper sections
    common_sections = ["abstract", "introduction", "methods", "results", "discussion", "conclusion", "references"]
    found_sections = [section for section in common_sections if section.lower() in text.lower()]
    
    print(colored("\nText Extraction Results:", "cyan"))
    print(colored(f"✓ Extracted {len(text)} characters", "green"))
    print(colored(f"✓ Found sections: {', '.join(found_sections)}", "green"))

if __name__ == "__main__":
    print(colored("\nRunning PDF processing tests...\n", "cyan"))
    pytest.main([__file__, "-v"]) 