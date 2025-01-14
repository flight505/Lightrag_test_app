import pytest
from pathlib import Path
from src.file_processor import FileProcessor
from src.config_manager import ConfigManager, PDFEngine
import json
import logging
from termcolor import colored

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='tests/metadata_extraction.log'
)

# Test data paths
arxiv_path = Path("tests/pdfs/Chen et al. - 2023 - TSMixer An All-MLP Architecture for Time Series Forecasting-annotated.pdf")
doi_path = Path("tests/pdfs/Choo et al. - 2023 - Deep-learning-based personalized prediction of absolute neutrophil count recovery and comparison with clinicians-annotated.pdf")

@pytest.fixture
def config_manager():
    """Create a ConfigManager instance for testing"""
    return ConfigManager(
        pdf_engine=PDFEngine.MARKER,
        enable_crossref=True,
        enable_scholarly=True,
        debug_mode=True
    )

@pytest.fixture
def file_processor(config_manager):
    """Create a FileProcessor instance for testing"""
    return FileProcessor(config_manager)

def test_arxiv_metadata_extraction(file_processor):
    """Test metadata extraction from arXiv paper including Anystyle references"""
    print(colored("\n=== Testing arXiv Paper Processing ===", "blue"))
    
    # Process the arXiv paper
    result = file_processor.process_file(str(arxiv_path))
    assert result is not None, "Processing failed"
    
    metadata = result.get('metadata')
    assert metadata is not None, "No metadata extracted"
    
    # Verify basic metadata
    assert metadata['title'] == "TSMixer: An All-MLP Architecture for Time Series Forecasting"
    assert len(metadata['authors']) == 5
    assert metadata['identifier_type'] == 'arxiv'
    
    # Verify Anystyle reference extraction
    print(colored("\n=== Verifying Anystyle Reference Extraction ===", "blue"))
    references = metadata.get('references', [])
    if references:
        print(colored(f"✓ Found {len(references)} references with Anystyle", "green"))
    else:
        print(colored("⚠️ No references found by Anystyle", "yellow"))
    
    # Save metadata for consolidation test
    metadata_file = arxiv_path.parent / f"{arxiv_path.stem}_metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)

def test_doi_metadata_extraction(file_processor):
    """Test metadata extraction from DOI paper including Anystyle references"""
    print(colored("\n=== Testing DOI Paper Processing ===", "blue"))
    
    # Process the DOI paper
    result = file_processor.process_file(str(doi_path))
    assert result is not None, "Processing failed"
    
    metadata = result.get('metadata')
    assert metadata is not None, "No metadata extracted"
    
    # Verify basic metadata
    assert metadata['identifier_type'] == 'doi'
    
    # Verify Anystyle reference extraction
    print(colored("\n=== Verifying Anystyle Reference Extraction ===", "blue"))
    references = metadata.get('references', [])
    if references:
        print(colored(f"✓ Found {len(references)} references with Anystyle", "green"))
    else:
        print(colored("⚠️ No references found by Anystyle", "yellow"))
    
    # Save metadata for consolidation test
    metadata_file = doi_path.parent / f"{doi_path.stem}_metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)

def test_metadata_consolidation():
    """Test loading and consolidating metadata from both papers"""
    print(colored("\n=== Testing Metadata Consolidation ===", "blue"))
    
    # Load metadata files
    arxiv_metadata_file = arxiv_path.parent / f"{arxiv_path.stem}_metadata.json"
    doi_metadata_file = doi_path.parent / f"{doi_path.stem}_metadata.json"
    
    assert arxiv_metadata_file.exists(), "arXiv metadata file not found"
    assert doi_metadata_file.exists(), "DOI metadata file not found"
    
    with open(arxiv_metadata_file, 'r', encoding='utf-8') as f:
        arxiv_metadata = json.load(f)
    with open(doi_metadata_file, 'r', encoding='utf-8') as f:
        doi_metadata = json.load(f)
    
    # Verify references exist in both
    arxiv_refs = arxiv_metadata.get('references', [])
    doi_refs = doi_metadata.get('references', [])
    
    print(colored(f"arXiv paper references: {len(arxiv_refs)}", "blue"))
    print(colored(f"DOI paper references: {len(doi_refs)}", "blue"))
    
    # Create consolidated metadata
    consolidated = {
        'papers': [arxiv_metadata, doi_metadata],
        'total_references': len(arxiv_refs) + len(doi_refs)
    }
    
    # Save consolidated metadata
    consolidated_file = arxiv_path.parent / "consolidated_metadata.json"
    with open(consolidated_file, 'w', encoding='utf-8') as f:
        json.dump(consolidated, f, indent=2)
    print(colored(f"✓ Saved consolidated metadata with {consolidated['total_references']} total references", "green")) 