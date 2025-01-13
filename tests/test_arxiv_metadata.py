import pytest
from pathlib import Path
import json
import logging
from src.file_processor import FileProcessor
from src.config_manager import ConfigManager, PDFEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='tests/metadata_extraction.log'
)

# Test data paths
ARXIV_PATH = Path("tests/pdfs/Chen et al. - 2023 - TSMixer An All-MLP Architecture for Time Series Forecasting-annotated.pdf")
DOI_PATH = Path("tests/pdfs/Choo et al. - 2023 - Deep-learning-based personalized prediction of absolute neutrophil count recovery and comparison with clinicians-annotated.pdf")

@pytest.fixture
def config_manager():
    """Create a ConfigManager instance for testing"""
    return ConfigManager(
        pdf_engine=PDFEngine.MARKER,
        enable_crossref=True,
        enable_scholarly=True,
        debug_mode=True,
        max_file_size_mb=10  # Set reasonable file size limit for tests
    )

@pytest.fixture
def file_processor(config_manager):
    """Create a FileProcessor instance for testing"""
    return FileProcessor(config_manager)

def test_arxiv_metadata_extraction(file_processor):
    """Test metadata extraction from arXiv paper"""
    print("\n=== Testing arXiv Paper Metadata Extraction ===")
    assert ARXIV_PATH.exists(), f"Test file not found: {ARXIV_PATH}"
    
    # Process the arXiv paper
    result = file_processor.process_file(str(ARXIV_PATH))
    assert result is not None, "File processing failed"
    
    metadata = result.get('metadata')
    assert metadata is not None, "No metadata extracted"
    
    # Verify basic metadata
    assert metadata.get('title'), "Title not extracted"
    assert metadata.get('authors'), "Authors not extracted"
    assert metadata.get('abstract'), "Abstract not extracted"
    assert metadata.get('arxiv_id'), "arXiv ID not extracted"
    
    # Save metadata for consolidation test
    metadata_file = ARXIV_PATH.parent / f"{ARXIV_PATH.stem}_metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    print(f"✓ Saved arXiv metadata to {metadata_file}")

def test_doi_metadata_extraction(file_processor):
    """Test metadata extraction from DOI paper"""
    print("\n=== Testing DOI Paper Metadata Extraction ===")
    assert DOI_PATH.exists(), f"Test file not found: {DOI_PATH}"
    
    # Process the DOI paper
    result = file_processor.process_file(str(DOI_PATH))
    assert result is not None, "File processing failed"
    
    metadata = result.get('metadata')
    assert metadata is not None, "No metadata extracted"
    
    # Verify basic metadata
    assert metadata.get('title'), "Title not extracted"
    assert metadata.get('authors'), "Authors not extracted"
    assert metadata.get('identifier'), "DOI not extracted"
    
    # Save metadata for consolidation test
    metadata_file = DOI_PATH.parent / f"{DOI_PATH.stem}_metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    print(f"✓ Saved DOI metadata to {metadata_file}")

def test_metadata_consolidation():
    """Test consolidation of metadata from both papers"""
    print("\n=== Testing Metadata Consolidation ===")
    
    # Load metadata files
    arxiv_metadata_file = ARXIV_PATH.parent / f"{ARXIV_PATH.stem}_metadata.json"
    doi_metadata_file = DOI_PATH.parent / f"{DOI_PATH.stem}_metadata.json"
    
    assert arxiv_metadata_file.exists(), f"arXiv metadata file not found: {arxiv_metadata_file}"
    assert doi_metadata_file.exists(), f"DOI metadata file not found: {doi_metadata_file}"
    
    with open(arxiv_metadata_file, 'r', encoding='utf-8') as f:
        arxiv_metadata = json.load(f)
    with open(doi_metadata_file, 'r', encoding='utf-8') as f:
        doi_metadata = json.load(f)
    
    # Create consolidated metadata
    consolidated = {
        'papers': [arxiv_metadata, doi_metadata],
        'total_papers': 2,
        'timestamp': str(Path(arxiv_metadata_file).stat().st_mtime)
    }
    
    # Save consolidated metadata
    consolidated_file = ARXIV_PATH.parent / "consolidated_metadata.json"
    with open(consolidated_file, 'w', encoding='utf-8') as f:
        json.dump(consolidated, f, indent=2)
    print(f"✓ Saved consolidated metadata to {consolidated_file}") 