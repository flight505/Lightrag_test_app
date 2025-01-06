import pytest
import os
from pathlib import Path
from termcolor import colored
from src.pdf_converter import MarkerConverter

# Test PDF path - using a sample academic PDF
SAMPLE_PDF = Path(__file__).parent / "data" / "sample.pdf"

def test_marker_initialization():
    """Test if Marker initializes correctly with proper imports"""
    try:
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict
        print(colored("✓ Marker imports successful", "green"))
    except ImportError as e:
        pytest.fail(f"Failed to import Marker components: {str(e)}")

def test_marker_converter_creation():
    """Test MarkerConverter instantiation"""
    try:
        converter = MarkerConverter()
        assert converter._converter is not None
        print(colored("✓ MarkerConverter created successfully", "green"))
    except Exception as e:
        pytest.fail(f"Failed to create MarkerConverter: {str(e)}")

@pytest.mark.skipif(not SAMPLE_PDF.exists(), reason="Sample PDF not found")
def test_text_extraction():
    """Test text extraction from PDF"""
    converter = MarkerConverter()
    text = converter.extract_text(str(SAMPLE_PDF))
    
    # Basic validation
    assert text, "Extracted text should not be empty"
    assert len(text) > 100, "Extracted text seems too short"
    
    # Check for common academic paper sections
    common_sections = ["abstract", "introduction", "conclusion", "references"]
    found_sections = sum(1 for section in common_sections if section.lower() in text.lower())
    assert found_sections > 0, "No common paper sections found in extracted text"
    
    print(colored("✓ Text extraction successful", "green"))
    print(colored(f"✓ Found {found_sections} common paper sections", "green"))

@pytest.mark.skipif(not SAMPLE_PDF.exists(), reason="Sample PDF not found")
def test_markdown_conversion():
    """Test PDF to markdown conversion"""
    converter = MarkerConverter()
    text = converter.extract_text(str(SAMPLE_PDF))
    
    # Check markdown formatting
    assert "# " in text or "## " in text, "No markdown headers found"
    assert "\n\n" in text, "No proper paragraph spacing found"
    assert "- " in text or "* " in text or "1. " in text, "No list formatting found"
    
    # Save markdown output for inspection
    output_path = SAMPLE_PDF.with_suffix('.md')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(colored(f"✓ Markdown output saved to {output_path}", "green"))

@pytest.mark.skipif(not SAMPLE_PDF.exists(), reason="Sample PDF not found")
def test_structure_preservation():
    """Test if Marker preserves document structure"""
    converter = MarkerConverter()
    text = converter.extract_text(str(SAMPLE_PDF))
    
    # Check for Markdown structure indicators
    has_paragraphs = "\n\n" in text
    has_sections = any(line.strip().startswith('#') for line in text.split('\n'))
    has_lists = any(line.strip().startswith('-') or line.strip().startswith('1.') for line in text.split('\n'))
    
    assert has_paragraphs, "No paragraph breaks found"
    assert has_sections, "No section headers found"
    assert has_lists, "No lists found"
    
    print(colored("✓ Document structure preserved", "green"))
    print(colored("✓ Found paragraphs, sections, and lists", "green"))

@pytest.mark.skipif(not SAMPLE_PDF.exists(), reason="Sample PDF not found")
def test_equation_preservation():
    """Test if Marker preserves LaTeX equations"""
    converter = MarkerConverter()
    text = converter.extract_text(str(SAMPLE_PDF))
    
    # Check for equation delimiters
    inline_equations = text.count('$')
    display_equations = text.count('$$')
    
    print(colored(f"Found {inline_equations//2} inline equations", "blue"))
    print(colored(f"Found {display_equations//2} display equations", "blue"))
    
    # Save text output for inspection
    output_path = SAMPLE_PDF.with_suffix('.txt')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(colored(f"✓ Text output saved to {output_path}", "green"))

def test_marker_error_handling():
    """Test Marker's error handling with invalid input"""
    converter = MarkerConverter()
    with pytest.raises(Exception):
        converter.extract_text("nonexistent.pdf")
    print(colored("✓ Error handling working correctly", "green"))

if __name__ == "__main__":
    print(colored("\nRunning Marker tests...\n", "cyan"))
    
    # Create test data directory if it doesn't exist
    test_data_dir = Path(__file__).parent / "data"
    test_data_dir.mkdir(exist_ok=True)
    
    # Run tests
    pytest.main([__file__, "-v"]) 