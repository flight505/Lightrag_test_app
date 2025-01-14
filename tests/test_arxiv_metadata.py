import pytest
from pathlib import Path
from src.file_processor import FileProcessor
from src.config_manager import ConfigManager, PDFEngine
import json
import logging
import subprocess
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
    
    # Wait for metadata file to be saved
    metadata_file = arxiv_path.parent / f"{arxiv_path.stem}_metadata.json"
    assert metadata_file.exists(), "Metadata file not saved"
    
    # Load metadata from file
    with open(metadata_file, 'r', encoding='utf-8') as f:
        saved_metadata = json.load(f)
    
    # Verify Anystyle reference extraction
    print(colored("\n=== Verifying Anystyle Reference Extraction ===", "blue"))
    references = saved_metadata.get('references', [])
    assert len(references) > 0, "No references extracted from arXiv paper"
    
    # Verify reference structure
    first_ref = references[0]
    assert isinstance(first_ref, dict), "Reference not properly structured"
    assert 'raw_text' in first_ref, "Reference missing raw_text"
    assert 'title' in first_ref, "Reference missing title"
    assert 'authors' in first_ref, "Reference missing authors"
    
    print(colored(f"✓ Found {len(references)} references with Anystyle", "green"))

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
    
    # Wait for metadata file to be saved
    metadata_file = doi_path.parent / f"{doi_path.stem}_metadata.json"
    assert metadata_file.exists(), "Metadata file not saved"
    
    # Load metadata from file
    with open(metadata_file, 'r', encoding='utf-8') as f:
        saved_metadata = json.load(f)
    
    # Verify Anystyle reference extraction
    print(colored("\n=== Verifying Anystyle Reference Extraction ===", "blue"))
    references = saved_metadata.get('references', [])
    assert len(references) > 0, "No references extracted from DOI paper"
    
    # Verify reference structure
    first_ref = references[0]
    assert isinstance(first_ref, dict), "Reference not properly structured"
    assert 'raw_text' in first_ref, "Reference missing raw_text"
    assert 'title' in first_ref, "Reference missing title"
    assert 'authors' in first_ref, "Reference missing authors"
    
    print(colored(f"✓ Found {len(references)} references with Anystyle", "green"))

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

def test_anystyle_availability():
    """Test Anystyle CLI availability and version"""
    print(colored("\n=== Testing Anystyle Availability ===", "blue"))
    result = subprocess.run(['anystyle', '--version'], capture_output=True, text=True)
    assert result.returncode == 0, "Anystyle command failed"
    assert "anystyle version 1.5.0" in result.stdout, "Unexpected Anystyle version"
    print(colored(f"✓ Anystyle version: {result.stdout.strip()}", "green")) 