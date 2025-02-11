"""Tests for metadata extraction from academic papers."""
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import pytest
import requests
from termcolor import colored

from src.academic_metadata import AcademicMetadata
from src.base_metadata import Author, Reference
from src.citation_metadata import CitationProcessor
from src.config_manager import ConfigManager, PDFEngine
from src.equation_metadata import Equation, EquationExtractor
from src.file_processor import FileProcessor
from src.metadata_extractor import MetadataExtractor
from src.metadata_consolidator import MetadataConsolidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='tests/metadata_extraction.log'
)

# Test data paths
arxiv_path = Path("tests/pdfs/Chen et al. - 2023 - TSMixer An All-MLP Architecture for Time Series Forecasting-annotated.pdf")
doi_path = Path("tests/pdfs/Choo et al. - 2023 - Deep-learning-based personalized prediction of absolute neutrophil count recovery and comparison with clinicians-annotated.pdf")

@pytest.fixture(scope="session")
def config_manager():
    """Create a ConfigManager instance for testing"""
    return ConfigManager(
        pdf_engine=PDFEngine.MARKER,
        enable_crossref=True,
        enable_scholarly=True,
        debug_mode=True
    )

@pytest.fixture(scope="session")
def file_processor(config_manager):
    """Create a FileProcessor instance for testing"""
    return FileProcessor(config_manager)

@pytest.fixture(scope="session")
def processed_files(file_processor):
    """Process PDFs once at the start of test session"""
    print(colored("\n=== Processing PDFs with Marker ===", "blue"))
    arxiv_result = file_processor.process_file(str(arxiv_path))
    doi_result = file_processor.process_file(str(doi_path))
    return {
        'arxiv': arxiv_result,
        'doi': doi_result
    }

def test_citation_extraction(processed_files):
    """Test citation extraction using pre-processed markdown files"""
    print(colored("\n=== Testing Citation Extraction ===", "blue"))
    
    # Get metadata with references
    arxiv_metadata = processed_files['arxiv']['metadata']
    doi_metadata = processed_files['doi']['metadata']
    
    # Load markdown content
    arxiv_md = arxiv_path.parent / f"{arxiv_path.stem}.md"
    doi_md = doi_path.parent / f"{doi_path.stem}.md"
    
    with open(arxiv_md, 'r', encoding='utf-8') as f:
        arxiv_text = f.read()
    with open(doi_md, 'r', encoding='utf-8') as f:
        doi_text = f.read()
        
    # Process citations with references
    arxiv_processor = CitationProcessor(references=arxiv_metadata.references)
    doi_processor = CitationProcessor(references=doi_metadata.references)
    
    arxiv_citations = arxiv_processor.process_citations(arxiv_text)
    doi_citations = doi_processor.process_citations(doi_text)
    
    # Verify citations were found
    assert len(arxiv_citations) > 0, "No citations found in arXiv paper"
    assert len(doi_citations) > 0, "No citations found in DOI paper"
    
    # Save citation analysis
    citation_analysis = {
        'arxiv_citations': len(arxiv_citations),
        'doi_citations': len(doi_citations),
        'total_citations': len(arxiv_citations) + len(doi_citations)
    }
    
    analysis_file = arxiv_path.parent / "citation_analysis.json"
    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump(citation_analysis, f, indent=2)
    print(colored(f"✓ Saved citation analysis with {citation_analysis['total_citations']} total citations", "green"))

def test_arxiv_metadata_extraction(processed_files):
    """Test metadata extraction using pre-processed results"""
    print(colored("\n=== Testing arXiv Paper Processing ===", "blue"))
    
    result = processed_files['arxiv']
    assert result is not None, "Processing failed"
    
    metadata = result['metadata']
    assert isinstance(metadata, AcademicMetadata), "Metadata should be an AcademicMetadata instance"
    assert metadata.title, "No title found"
    assert metadata.authors, "No authors found"
    assert metadata.references, "No references found"
    assert metadata.equations, "No equations found"
    
    print(colored(f"✓ Found {len(metadata.references)} references", "green"))
    print(colored(f"✓ Found {len(metadata.equations)} equations", "green"))

def test_doi_metadata_extraction(processed_files):
    """Test metadata extraction using pre-processed results"""
    print(colored("\n=== Testing DOI Paper Processing ===", "blue"))
    
    result = processed_files['doi']
    assert result is not None, "Processing failed"
    
    metadata = result['metadata']
    assert isinstance(metadata, AcademicMetadata), "Metadata should be an AcademicMetadata instance"
    assert metadata.title, "No title found"
    assert metadata.authors, "No authors found"
    assert metadata.references, "No references found"
    assert metadata.equations, "No equations found"
    
    print(colored(f"✓ Found {len(metadata.references)} references", "green"))
    print(colored(f"✓ Found {len(metadata.equations)} equations", "green"))

def test_equation_extraction(processed_files):
    """Test equation extraction from both papers"""
    print(colored("\n=== Testing Equation Extraction ===", "blue"))
    
    arxiv_result = processed_files['arxiv']
    doi_result = processed_files['doi']
    
    assert arxiv_result is not None, "arXiv processing failed"
    assert doi_result is not None, "DOI processing failed"
    
    arxiv_metadata = arxiv_result['metadata']
    doi_metadata = doi_result['metadata']
    
    assert isinstance(arxiv_metadata, AcademicMetadata), "arXiv metadata should be an AcademicMetadata instance"
    assert isinstance(doi_metadata, AcademicMetadata), "DOI metadata should be an AcademicMetadata instance"
    
    assert arxiv_metadata.equations, "No equations found in arXiv paper"
    assert doi_metadata.equations, "No equations found in DOI paper"
    
    print(colored(f"✓ Found {len(arxiv_metadata.equations)} equations in arXiv paper", "green"))
    print(colored(f"✓ Found {len(doi_metadata.equations)} equations in DOI paper", "green")) 

def test_complete_pipeline(processed_files):
    """Test the complete metadata extraction pipeline as used in the application."""
    print(colored("\n=== Testing Complete Pipeline ===", "blue"))
    
    # Test arXiv paper
    arxiv_result = processed_files['arxiv']
    assert arxiv_result is not None, "arXiv processing failed"
    
    arxiv_metadata = arxiv_result['metadata']
    assert isinstance(arxiv_metadata, AcademicMetadata), "Metadata should be an AcademicMetadata instance"
    
    # Verify all components are present
    assert arxiv_metadata.title, "No title found"
    assert arxiv_metadata.authors, "No authors found"
    assert arxiv_metadata.abstract, "No abstract found"
    assert arxiv_metadata.references, "No references found"
    assert arxiv_metadata.citations, "No citations found"
    assert arxiv_metadata.equations, "No equations found"
    assert arxiv_metadata.identifier, "No identifier found"
    assert arxiv_metadata.identifier_type == "arxiv", "Wrong identifier type"
    
    # Verify relationships
    assert len(arxiv_metadata.citations) <= len(arxiv_metadata.references), "More citations than references"
    for citation in arxiv_metadata.citations:
        assert citation.references, "Citation without linked references"
        
    # Test DOI paper
    doi_result = processed_files['doi']
    assert doi_result is not None, "DOI processing failed"
    
    doi_metadata = doi_result['metadata']
    assert isinstance(doi_metadata, AcademicMetadata), "Metadata should be an AcademicMetadata instance"
    
    # Verify all components are present
    assert doi_metadata.title, "No title found"
    assert doi_metadata.authors, "No authors found"
    assert doi_metadata.abstract, "No abstract found"
    assert doi_metadata.references, "No references found"
    assert doi_metadata.citations, "No citations found"
    assert doi_metadata.equations, "No equations found"
    assert doi_metadata.identifier, "No identifier found"
    assert doi_metadata.identifier_type == "doi", "Wrong identifier type"
    assert doi_metadata.journal, "No journal found"
    
    # Verify relationships - only check that citations have valid references
    for citation in doi_metadata.citations:
        assert citation.references, "Citation without linked references"
    
    # Verify file outputs
    assert arxiv_result['metadata_path'].endswith('_metadata.json'), "Wrong metadata file extension"
    assert arxiv_result['text_path'].endswith('.txt'), "Wrong text file extension"
    assert doi_result['metadata_path'].endswith('_metadata.json'), "Wrong metadata file extension"
    assert doi_result['text_path'].endswith('.txt'), "Wrong text file extension"
    
    print(colored("✓ Complete pipeline test passed", "green")) 

def test_consolidated_metadata(processed_files, tmp_path):
    """Test consolidated metadata generation and updates with KG structure"""
    print(colored("\n=== Testing Consolidated Metadata ===", "blue"))
    
    # Setup test store
    store_path = tmp_path / "test_store"
    store_path.mkdir()
    
    # Initialize consolidator
    consolidator = MetadataConsolidator(store_path)
    consolidator.initialize_consolidated_json()
    
    # Verify initial state
    consolidated = consolidator._load_json(consolidator.consolidated_path)
    assert consolidated["store_info"]["name"] == "test_store"
    assert consolidated["store_info"]["version"] == "2.0.0"
    assert len(consolidated["nodes"]["papers"]) == 0
    assert len(consolidated["nodes"]["equations"]) == 0
    assert len(consolidated["nodes"]["citations"]) == 0
    assert len(consolidated["nodes"]["authors"]) == 0
    assert len(consolidated["relationships"]) == 0
    
    # Add test documents
    for doc_type, result in processed_files.items():
        if result and 'metadata' in result:
            consolidator.update_document_metadata(
                doc_type,
                result['metadata']
            )
    
    # Verify consolidated metadata
    consolidated = consolidator._load_json(consolidator.consolidated_path)
    
    # Verify nodes
    assert len(consolidated["nodes"]["papers"]) == len(processed_files)
    assert len(consolidated["nodes"]["equations"]) > 0
    assert len(consolidated["nodes"]["citations"]) > 0
    assert len(consolidated["nodes"]["authors"]) > 0
    
    # Verify relationships
    relationships = consolidated["relationships"]
    assert len(relationships) > 0
    
    # Verify relationship types
    relationship_types = {rel["type"] for rel in relationships}
    assert "written_by" in relationship_types
    assert "contains_equation" in relationship_types
    assert "contains_citation" in relationship_types
    assert "cites_paper" in relationship_types
    
    # Verify paper nodes structure
    for paper in consolidated["nodes"]["papers"]:
        assert "id" in paper
        assert "type" in paper
        assert paper["type"] == "paper"
        assert "title" in paper
        assert "metadata" in paper
        assert "authors" in paper["metadata"]
        assert "year" in paper["metadata"]
        assert "venue" in paper["metadata"]
    
    # Verify equation nodes structure
    for equation in consolidated["nodes"]["equations"]:
        assert "id" in equation
        assert "type" in equation
        assert equation["type"] == "equation"
        assert "raw_text" in equation
        assert "metadata" in equation
        assert "symbols" in equation["metadata"]
        assert "equation_type" in equation["metadata"]
        assert "context" in equation["metadata"]
    
    # Verify citation nodes structure
    for citation in consolidated["nodes"]["citations"]:
        assert "id" in citation
        assert "type" in citation
        assert citation["type"] == "citation"
        assert "text" in citation
        assert "metadata" in citation
        assert "context" in citation["metadata"]
        assert "references" in citation["metadata"]
    
    # Verify relationship structure
    for rel in relationships:
        assert "source" in rel
        assert "target" in rel
        assert "type" in rel
        assert "metadata" in rel
        if rel["type"] == "written_by":
            assert rel["target"].startswith("author_")
        elif rel["type"] == "contains_equation":
            assert "_eq_" in rel["target"]
        elif rel["type"] == "contains_citation":
            assert "_cite_" in rel["target"]
    
    # Verify global stats
    stats = consolidated["global_stats"]
    assert stats["total_documents"] == len(consolidated["nodes"]["papers"])
    assert stats["total_equations"] == len(consolidated["nodes"]["equations"])
    assert stats["total_citations"] == len(consolidated["nodes"]["citations"])
    assert stats["total_relationships"] == len(consolidated["relationships"])
    
    # Test document removal
    consolidator.remove_document_metadata("arxiv")
    consolidated = consolidator._load_json(consolidator.consolidated_path)
    
    # Verify node removal
    assert len([p for p in consolidated["nodes"]["papers"] if p["id"] == "arxiv"]) == 0
    assert len([e for e in consolidated["nodes"]["equations"] if e["id"].startswith("arxiv_eq_")]) == 0
    assert len([c for c in consolidated["nodes"]["citations"] if c["id"].startswith("arxiv_cite_")]) == 0
    
    # Verify relationship removal
    assert not any(
        rel["source"] == "arxiv" or 
        rel["source"].startswith("arxiv_") or
        rel["target"] == "arxiv" or
        rel["target"].startswith("arxiv_")
        for rel in consolidated["relationships"]
    )
    
    print(colored("✓ Consolidated metadata test passed", "green")) 