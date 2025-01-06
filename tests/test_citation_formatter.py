import pytest
from src.citation_formatter import (
    CitationFormatterFactory,
    APAFormatter,
    MLAFormatter,
    ChicagoFormatter
)
from src.academic_metadata import Reference, Author, CitationStyle

@pytest.fixture
def sample_reference():
    """Create a sample reference for testing"""
    return Reference(
        raw_text="Smith, J., & Doe, J. (2020). Test paper. Journal of Testing.",
        title="Test paper",
        authors=[
            Author(
                full_name="John Smith",
                first_name="John",
                last_name="Smith"
            ),
            Author(
                full_name="Jane Doe",
                first_name="Jane",
                last_name="Doe"
            )
        ],
        year=2020,
        venue="Journal of Testing",
        doi="10.1234/test"
    )

@pytest.fixture
def sample_references():
    """Create a list of sample references"""
    return [
        Reference(
            raw_text="Smith, J. (2020). First paper. Journal of Testing.",
            title="First paper",
            authors=[
                Author(
                    full_name="John Smith",
                    first_name="John",
                    last_name="Smith"
                )
            ],
            year=2020,
            venue="Journal of Testing"
        ),
        Reference(
            raw_text="Doe, J. (2021). Second paper. Journal of Testing.",
            title="Second paper",
            authors=[
                Author(
                    full_name="Jane Doe",
                    first_name="Jane",
                    last_name="Doe"
                )
            ],
            year=2021,
            venue="Journal of Testing",
            doi="10.1234/test2"
        )
    ]

def test_apa_citation(sample_reference):
    """Test APA citation formatting"""
    formatter = APAFormatter()
    citation = formatter.format_citation(sample_reference)
    assert citation == "(Smith and Doe, 2020)"

def test_apa_bibliography(sample_references):
    """Test APA bibliography formatting"""
    formatter = APAFormatter()
    bibliography = formatter.format_bibliography(sample_references)
    assert "Doe, Jane (2021)" in bibliography
    assert "Smith, John (2020)" in bibliography
    assert "https://doi.org/10.1234/test2" in bibliography

def test_mla_citation(sample_reference):
    """Test MLA citation formatting"""
    formatter = MLAFormatter()
    citation = formatter.format_citation(sample_reference)
    assert "Smith and Doe" in citation
    assert "n.p." in citation

def test_mla_bibliography(sample_references):
    """Test MLA bibliography formatting"""
    formatter = MLAFormatter()
    bibliography = formatter.format_bibliography(sample_references)
    assert '"First paper"' in bibliography
    assert '"Second paper"' in bibliography
    assert "Journal of Testing" in bibliography

def test_chicago_citation(sample_reference):
    """Test Chicago citation formatting"""
    formatter = ChicagoFormatter()
    citation = formatter.format_citation(sample_reference)
    assert citation == "(Smith and Doe 2020)"

def test_chicago_bibliography(sample_references):
    """Test Chicago bibliography formatting"""
    formatter = ChicagoFormatter()
    bibliography = formatter.format_bibliography(sample_references)
    assert "Smith, John. 2020" in bibliography
    assert "Doe, Jane. 2021" in bibliography
    assert "https://doi.org/10.1234/test2" in bibliography

def test_formatter_factory():
    """Test citation formatter factory"""
    apa = CitationFormatterFactory.create_formatter(CitationStyle.APA)
    mla = CitationFormatterFactory.create_formatter(CitationStyle.MLA)
    chicago = CitationFormatterFactory.create_formatter(CitationStyle.CHICAGO)
    
    assert isinstance(apa, APAFormatter)
    assert isinstance(mla, MLAFormatter)
    assert isinstance(chicago, ChicagoFormatter)

def test_error_handling(sample_reference):
    """Test error handling in formatters"""
    # Create a reference with missing data
    bad_ref = Reference(
        raw_text="Bad reference",
        title=None,
        authors=[],
        year=None,
        venue=None
    )
    
    formatters = [
        APAFormatter(),
        MLAFormatter(),
        ChicagoFormatter()
    ]
    
    for formatter in formatters:
        # Should not raise exceptions
        citation = formatter.format_citation(bad_ref)
        bibliography = formatter.format_bibliography([bad_ref])
        
        assert citation
        assert bibliography
        assert "Unknown Author" in citation or "Bad reference" in citation 