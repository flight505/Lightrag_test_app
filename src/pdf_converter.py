from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pymupdf
from PyPDF2 import PdfReader
from termcolor import colored
import logging
import os
from .config_manager import PDFEngine, ConfigManager
from pathlib import Path

# Disable tokenizers warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

logger = logging.getLogger(__name__)

class PDFConverter(ABC):
    """Abstract base class for PDF converters"""
    
    @abstractmethod
    def extract_text(self, file_path: str) -> str:
        """Extract text content from PDF"""
        pass
        
    @abstractmethod
    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from PDF"""
        pass

class MarkerConverter(PDFConverter):
    """PDF converter using Marker"""
    
    def __init__(self):
        """Initialize Marker converter"""
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict
        from marker.config.parser import ConfigParser
        
        # Configure Marker settings with enhanced equation detection
        config = {
            "output_format": "markdown",
            "layout_analysis": True,
            "detect_equations": True,
            "equation_detection_confidence": 0.3,
            "detect_inline_equations": True,
            "detect_tables": True,
            "detect_lists": True,
            "detect_code_blocks": True,
            "detect_footnotes": True,
            "equation_output": "latex",
            "preserve_math": True,
            "equation_detection_mode": "aggressive",
            "equation_context_window": 3,
            "equation_pattern_matching": True,
            "equation_symbol_extraction": True,
            
            # Enhanced header handling
            "header_detection": {
                "enabled": True,
                "style": "atx",  # Use # style headers
                "levels": {
                    "title": 1,    # Title uses single #
                    "section": 2,   # Sections use ##
                    "subsection": 3 # Subsections use ###
                },
                "remove_duplicate_markers": True
            },
            
            # Enhanced list handling
            "list_detection": {
                "enabled": True,
                "unordered_marker": "-",  # Use - for unordered lists
                "ordered_marker": "1.",   # Use 1. for ordered lists
                "preserve_numbers": True,  # Keep original list numbers
                "indent_spaces": 2        # Use 2 spaces for indentation
            },
            
            # Layout and formatting
            "layout": {
                "paragraph_breaks": True,
                "line_spacing": 2,
                "remove_redundant_whitespace": True,
                "preserve_line_breaks": True,
                "preserve_blank_lines": True
            },
            
            # Content preservation
            "preserve": {
                "links": True,
                "tables": True,
                "images": True,
                "footnotes": True,
                "formatting": True,
                "lists": True,
                "headers": True
            },
            
            # Output settings
            "output": {
                "format": "markdown",
                "save_markdown": True,
                "save_text": True,
                "markdown_ext": ".md",
                "text_ext": ".txt"
            }
        }
        
        config_parser = ConfigParser(config)
        
        # Initialize converter with config
        self._converter = PdfConverter(
            config=config_parser.generate_config_dict(),
            artifact_dict=create_model_dict(),
            processor_list=config_parser.get_processors(),
            renderer=config_parser.get_renderer()
        )
        
        logger.info("Marker initialized with optimized settings")
    
    def extract_text(self, file_path: str) -> str:
        """Extract text with semantic structure preservation"""
        # Process PDF with Marker
        rendered = self._converter(file_path)
        
        # Save markdown file
        markdown_path = str(Path(file_path).with_suffix('.md'))
        
        # Extract text from rendered output
        if hasattr(rendered, 'markdown'):
            text = rendered.markdown
            # Save markdown content
            try:
                with open(markdown_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                print(colored(f"✓ Markdown saved to {markdown_path}", "green"))
            except Exception as e:
                print(colored(f"⚠️ Error saving markdown: {str(e)}", "yellow"))
        else:
            # For JSON output, extract text from blocks
            text = self._extract_text_from_blocks(rendered.children)
            try:
                with open(markdown_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                print(colored(f"✓ Markdown saved to {markdown_path}", "green"))
            except Exception as e:
                print(colored(f"⚠️ Error saving markdown: {str(e)}", "yellow"))
        
        if not text:
            raise ValueError("No text extracted by Marker")
            
        logger.info("Text extracted successfully with Marker")
        print(colored("✓ Text extracted with semantic structure preserved", "green"))
        return text
            
    def _extract_text_from_blocks(self, blocks) -> str:
        """Extract text from JSON block structure"""
        text = []
        for block in blocks:
            if hasattr(block, 'html'):
                text.append(block.html)
            if hasattr(block, 'children') and block.children:
                text.append(self._extract_text_from_blocks(block.children))
        return "\n".join(text)
    
    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata using proven extraction chain"""
        metadata = {}
        
        try:
            # Try to extract DOI and use CrossRef if available
            if 'doi' in metadata:
                try:
                    crossref_data = self._get_crossref_metadata(metadata['doi'])
                    if crossref_data:
                        metadata.update(crossref_data)
                        print(colored("✓ Using CrossRef API metadata", "green"))
                except Exception as e:
                    logger.warning(f"CrossRef enhancement failed: {str(e)}")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Metadata extraction error: {str(e)}")
            print(colored(f"⚠️ Metadata extraction error: {str(e)}", "yellow"))
            return {}
            
    def _get_crossref_metadata(self, doi: str) -> Optional[Dict[str, Any]]:
        """Get metadata from CrossRef API using DOI"""
        try:
            import requests
            url = f"https://api.crossref.org/works/{doi}"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                return {
                    'title': data['message'].get('title', [None])[0],
                    'authors': [
                        {
                            'given': author.get('given', ''),
                            'family': author.get('family', '')
                        }
                        for author in data['message'].get('author', [])
                    ],
                    'published': data['message'].get('published-print', {}).get('date-parts', [[None]])[0][0],
                    'publisher': data['message'].get('publisher'),
                    'type': data['message'].get('type'),
                    'container-title': data['message'].get('container-title', [None])[0],
                    'crossref_data': True
                }
        except Exception as e:
            logger.warning(f"CrossRef API lookup failed: {str(e)}")
        return None

class PyMuPDFConverter(PDFConverter):
    """PDF converter using PyMuPDF (fitz)"""
    
    def extract_text(self, file_path: str) -> str:
        try:
            doc = pymupdf.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            logger.info("Text extracted successfully with PyMuPDF")
            print(colored("✓ Text extracted with PyMuPDF", "green"))
            return text
        except Exception as e:
            logger.error(f"PyMuPDF text extraction error: {str(e)}")
            print(colored(f"⚠️ PyMuPDF text extraction error: {str(e)}", "yellow"))
            return ""
    
    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        try:
            doc = pymupdf.open(file_path)
            metadata = doc.metadata
            doc.close()
            logger.info("Metadata extracted successfully with PyMuPDF")
            print(colored("✓ Metadata extracted with PyMuPDF", "green"))
            return metadata
        except Exception as e:
            logger.error(f"PyMuPDF metadata extraction error: {str(e)}")
            print(colored(f"⚠️ PyMuPDF metadata extraction error: {str(e)}", "yellow"))
            return {}

class PyPDF2Converter(PDFConverter):
    """PDF converter using PyPDF2"""
    
    def extract_text(self, file_path: str) -> str:
        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            logger.info("Text extracted successfully with PyPDF2")
            print(colored("✓ Text extracted with PyPDF2", "green"))
            return text
        except Exception as e:
            logger.error(f"PyPDF2 text extraction error: {str(e)}")
            print(colored(f"⚠️ PyPDF2 text extraction error: {str(e)}", "yellow"))
            return ""
    
    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        try:
            reader = PdfReader(file_path)
            metadata = reader.metadata
            if metadata:
                # Convert PyPDF2 metadata format to match PyMuPDF
                converted = {}
                for key, value in metadata.items():
                    if key.startswith('/'):
                        converted[key[1:].lower()] = value
                logger.info("Metadata extracted successfully with PyPDF2")
                print(colored("✓ Metadata extracted with PyPDF2", "green"))
                return converted
            return {}
        except Exception as e:
            logger.error(f"PyPDF2 metadata extraction error: {str(e)}")
            print(colored(f"⚠️ PyPDF2 metadata extraction error: {str(e)}", "yellow"))
            return {}

class PDFConverterFactory:
    """Factory for creating PDF converters"""
    
    @staticmethod
    def create_converter(config_manager: ConfigManager) -> PDFConverter:
        engine = config_manager.get_config().pdf_engine
        logger.info(f"Creating PDF converter with engine: {engine}")
        
        if engine == PDFEngine.MARKER:
            logger.info("Using Marker converter")
            return MarkerConverter()
        elif engine == PDFEngine.PYMUPDF:
            logger.info("Using PyMuPDF converter")
            return PyMuPDFConverter()
        elif engine == PDFEngine.PYPDF2:
            logger.info("Using PyPDF2 converter")
            return PyPDF2Converter()
        else:  # AUTO - use Marker
            logger.info("AUTO mode: Using Marker")
            return MarkerConverter() 