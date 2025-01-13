import os
import json
import pytest
import re
from pathlib import Path
from termcolor import colored
import logging

from src.academic_metadata import MetadataExtractor, PDFMetadataExtractor
from src.file_processor import FileProcessor
from src.config_manager import ConfigManager

# Configure logging
logging.basicConfig(
    filename="tests/metadata_extraction.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Test data paths
TEST_DIR = Path("tests/pdfs")
ARXIV_PDF = "Chen et al. - 2023 - TSMixer An All-MLP Architecture for Time Series Forecasting-annotated.pdf"
DOI_PDF = "Choo et al. - 2023 - Deep-learning-based personalized prediction of absolute neutrophil count recovery and comparison with clinicians-annotated.pdf"

def extract_arxiv_id(text: str) -> str:
    """Extract arXiv ID from text"""
    arxiv_pattern = r'arXiv:(\d{4}\.\d{5})'
    match = re.search(arxiv_pattern, text)
    if match:
        return match.group(1)
    return None

def test_arxiv_metadata_extraction():
    """Test metadata extraction from arXiv paper"""
    try:
        # Initialize components
        config = ConfigManager()
        processor = FileProcessor(config)
        metadata_extractor = MetadataExtractor()

        # Process arXiv paper
        arxiv_path = TEST_DIR / ARXIV_PDF
        assert arxiv_path.exists(), f"Test file not found: {arxiv_path}"

        print(colored("\nProcessing arXiv paper...", "cyan"))

        # First process the PDF and get metadata
        result = processor.process_file(str(arxiv_path))
        if "error" in result:
            raise Exception(f"PDF processing failed: {result['error']}")

        # Extract metadata from processor result
        metadata = result.get('metadata', {})
        assert metadata, "No metadata returned from processor"
        assert metadata.get('title'), "No title in metadata"
        assert metadata.get('authors'), "No authors in metadata"
        assert metadata.get('abstract'), "No abstract in metadata"
        assert metadata.get('arxiv_id'), "No arXiv ID in metadata"

        # Save test metadata
        output_path = arxiv_path.with_suffix('.test_metadata.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        print(colored(f"✓ Saved test metadata to {output_path}", "green"))

        return metadata

    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

def test_metadata_consolidation():
    """Test consolidation of metadata from multiple documents"""
    try:
        # Process both papers
        arxiv_metadata = test_arxiv_metadata_extraction()
        assert arxiv_metadata, "Failed to extract arXiv metadata"

        # Save consolidated metadata
        consolidated_path = TEST_DIR / "consolidated_metadata.json"
        with open(consolidated_path, 'w', encoding='utf-8') as f:
            json.dump({
                "arxiv_paper": arxiv_metadata
            }, f, indent=2)
        print(colored(f"✓ Saved consolidated metadata to {consolidated_path}", "green"))

    except Exception as e:
        logger.error(f"Consolidation failed: {str(e)}")
        raise

if __name__ == "__main__":
    test_metadata_consolidation() 