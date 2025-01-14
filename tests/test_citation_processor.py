import pytest

from src.base_metadata import Author, Reference
from src.citation_metadata import CitationLink, CitationProcessor


@pytest.fixture
def sample_references():
    """Create sample references for testing."""
    return [
        Reference(
            raw_text="Smith et al. Deep Learning Review",
            title="Deep Learning Review",
            authors=[Author(full_name="John Smith", first_name="John", last_name="Smith")],
            year=2023
        ),
        Reference(
            raw_text="Jones and Brown. Machine Learning",
            title="Machine Learning",
            authors=[
                Author(full_name="Alice Jones", first_name="Alice", last_name="Jones"),
                Author(full_name="Bob Brown", first_name="Bob", last_name="Brown")
            ],
            year=2022
        ),
        Reference(
            raw_text="Wilson et al. Neural Networks",
            title="Neural Networks",
            authors=[Author(full_name="Tom Wilson", first_name="Tom", last_name="Wilson")],
            year=2023
        )
    ]

def test_numeric_citation_processing(sample_references):
    """Test processing of numeric citations."""
    processor = CitationProcessor(sample_references)
    text = """
    This is a test paragraph [1]. Multiple citations [1,2] are supported.
    Range citations [1-3] work too. Invalid citations [4] are ignored.
    """
    
    citations = processor.process_citations(text)
    
    assert len(citations) == 3  # [1], [1,2], [1-3]
    assert all(isinstance(c, CitationLink) for c in citations)
    assert citations[0].citation_text == "[1]"
    assert citations[0].reference.title == "Deep Learning Review"
    assert "test paragraph" in citations[0].context

def test_author_year_citation_processing(sample_references):
    """Test processing of author-year citations."""
    processor = CitationProcessor(sample_references)
    text = """
    According to Smith et al. (2023), deep learning has advanced significantly.
    Wilson et al. (2023) provide a comprehensive overview.
    """
    
    citations = processor.process_citations(text)
    
    assert len(citations) == 2
    assert citations[0].reference.authors[0].last_name == "Smith"
    assert citations[1].reference.authors[0].last_name == "Wilson"

def test_cross_reference_citation_processing():
    """Test processing of cross-reference citations."""
    text = """
    Deep learning methods have evolved cf. Smith et al. (2023).
    For more details, cf. Wilson et al. (2023).
    """
    
    references = [
        Reference(
            title="Deep Learning Review",
            authors=[Author(first_name="John", last_name="Smith", full_name="John Smith")],
            year=2023,
            raw_text="Smith et al. (2023) Deep Learning Review"
        ),
        Reference(
            title="Advanced Methods",
            authors=[Author(first_name="Bob", last_name="Wilson", full_name="Bob Wilson")],
            year=2023,
            raw_text="Wilson et al. (2023) Advanced Methods"
        )
    ]
    
    processor = CitationProcessor(references)
    citations = processor.process_citations(text)
    
    # Debug print
    print("\nFound citations:")
    for i, citation in enumerate(citations):
        print(f"{i+1}. {citation.citation_text} -> {citation.reference.title}")
    
    assert len(citations) == 2, "Should find two cross-reference citations"
    
    # Check first citation
    assert citations[0].citation_text == "cf. Smith et al. (2023)", "First citation should match exactly"
    assert citations[0].reference.year == 2023, "Year should be 2023"
    assert citations[0].reference.authors[0].last_name == "Smith", "Author should be Smith"
    
    # Check second citation
    assert citations[1].citation_text == "cf. Wilson et al. (2023)", "Second citation should match exactly"
    assert citations[1].reference.year == 2023, "Year should be 2023"
    assert citations[1].reference.authors[0].last_name == "Wilson", "Author should be Wilson"

def test_citation_context_extraction(sample_references):
    """Test extraction of citation contexts."""
    processor = CitationProcessor(sample_references)
    text = """
    This is a very specific context about deep learning [1]
    that should be captured properly.
    """
    
    citations = processor.process_citations(text)
    
    assert len(citations) == 1
    assert "specific context" in citations[0].context
    assert "deep learning" in citations[0].context
    assert len(citations[0].context) <= 200  # Context length limit

def test_citation_graph_generation(sample_references):
    """Test generation of citation graph."""
    processor = CitationProcessor(sample_references)
    text = """
    Deep learning has evolved [1]. Some say [1] it's important.
    Others [2] disagree. Multiple views exist [1,2].
    """
    
    processor.process_citations(text)
    graph = processor.get_citation_graph()
    
    assert len(graph) == 2  # Two unique references
    assert len(graph["Deep Learning Review"]) >= 2  # Cited multiple times
    assert len(graph["Machine Learning"]) >= 1  # Cited at least once

def test_citation_validation(sample_references):
    """Test citation validation."""
    processor = CitationProcessor(sample_references)
    text = """
    Valid citation [1]. Invalid citation [4].
    Valid author Smith et al. (2023).
    Invalid author Unknown et al. (2023).
    """
    
    processor.process_citations(text)
    issues = processor.validate_citations()
    
    assert len(issues) == 0  # Currently only tracking unresolved citations
    # Future: Add more validation rules and test them

def test_mixed_citation_styles(sample_references):
    """Test processing of mixed citation styles in the same text."""
    processor = CitationProcessor(sample_references)
    text = """
    Numeric citations [1] can be mixed with author-year citations (Smith et al. (2023)).
    Cross-references (cf. Wilson et al. (2023)) can appear with standard citations [2].
    Multiple styles: [1,2], Jones and Brown (2022), cf. Smith et al. (2023).
    """
    
    citations = processor.process_citations(text)
    
    assert len(citations) >= 6  # All citation types should be found
    styles = set(c.citation_text for c in citations)
    assert any("[" in s for s in styles)  # Numeric
    assert any("et al." in s for s in styles)  # Author-year
    assert any("cf." in s for s in styles)  # Cross-reference 