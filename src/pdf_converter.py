from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import fitz
from PyPDF2 import PdfReader
from termcolor import colored
import logging
import os
from .config_manager import PDFEngine, ConfigManager

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
    """PDF converter using Marker with optimized settings"""
    
    def __init__(self):
        """Initialize Marker with optimized settings"""
        try:
            from marker.converters.pdf import PdfConverter
            from marker.models import create_model_dict
            from marker.config.parser import ConfigParser
            
            # Configure Marker settings with enhanced equation detection
            config = {
                "output_format": "markdown",
                "layout_analysis": True,
                "detect_equations": True,
                "equation_detection_confidence": 0.3,  # Lower threshold for equation detection
                "detect_inline_equations": True,  # Also detect inline equations
                "detect_tables": True,
                "detect_lists": True,
                "detect_code_blocks": True,
                "detect_footnotes": True,
                "equation_output": "latex",  # Ensure LaTeX output for equations
                "preserve_math": True,  # Preserve mathematical content
                "equation_detection_mode": "aggressive",  # More aggressive equation detection
                "equation_context_window": 3,  # Larger context window for equations
                "equation_pattern_matching": True,  # Enable pattern matching for equations
                "equation_symbol_extraction": True  # Extract mathematical symbols
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
            
        except Exception as e:
            logger.error(f"Failed to initialize Marker: {str(e)}")
            self._converter = None
            raise
            
        self._initialize_fallback_extractors()
    
    def _initialize_fallback_extractors(self):
        """Initialize fallback metadata extractors"""
        self.pymupdf_converter = PyMuPDFConverter()
        self.pypdf2_converter = PyPDF2Converter()
    
    def extract_text(self, file_path: str) -> str:
        """Extract text with semantic structure preservation"""
        try:
            if self._converter is None:
                raise ValueError("Marker not initialized")
                
            # Process PDF with Marker
            rendered = self._converter(file_path)
            
            # Extract text from rendered output
            if hasattr(rendered, 'markdown'):
                text = rendered.markdown
            else:
                # For JSON output, extract text from blocks
                text = self._extract_text_from_blocks(rendered.children)
            
            if not text:
                raise ValueError("No text extracted by Marker")
                
            logger.info("Text extracted successfully with Marker")
            print(colored("✓ Text extracted with semantic structure preserved", "green"))
            return text
            
        except Exception as e:
            logger.error(f"Marker text extraction error: {str(e)}")
            print(colored(f"⚠️ Marker text extraction error: {str(e)}", "yellow"))
            raise  # Let FileProcessor handle fallback
            
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
            # 1. Try PyMuPDF metadata first
            logger.info("Attempting PyMuPDF metadata extraction")
            metadata = self.pymupdf_converter.extract_metadata(file_path)
            if metadata:
                print(colored("✓ Metadata extracted with PyMuPDF", "green"))
                
                # 2. Try to enhance with DOI and CrossRef if available
                if 'doi' in metadata:
                    try:
                        crossref_data = self._get_crossref_metadata(metadata['doi'])
                        if crossref_data:
                            metadata.update(crossref_data)
                            print(colored("✓ Using CrossRef API metadata", "green"))
                    except Exception as e:
                        logger.warning(f"CrossRef enhancement failed: {str(e)}")
                
                return metadata
            
            # 3. Try PyPDF2 as fallback
            logger.info("Attempting PyPDF2 metadata extraction")
            metadata = self.pypdf2_converter.extract_metadata(file_path)
            if metadata:
                print(colored("✓ Metadata extracted with PyPDF2", "green"))
                return metadata
            
            logger.warning("All PDF metadata extraction methods failed")
            return {}
            
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
            doc = fitz.open(file_path)
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
            doc = fitz.open(file_path)
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
        else:  # AUTO - try Marker first, then PyMuPDF, fallback to PyPDF2
            logger.info("AUTO mode: Attempting to use Marker first")
            try:
                converter = MarkerConverter()
                logger.info("Successfully initialized Marker converter")
                return converter
            except Exception as e:
                logger.warning(f"Marker initialization failed: {str(e)}, trying PyMuPDF")
                print(colored("⚠️ Marker failed, trying PyMuPDF", "yellow"))
                try:
                    converter = PyMuPDFConverter()
                    # Test if PyMuPDF is working
                    fitz.open  # Just check if the module is available
                    logger.info("Successfully initialized PyMuPDF converter")
                    return converter
                except Exception as e2:
                    logger.warning(f"PyMuPDF initialization failed: {str(e2)}, falling back to PyPDF2")
                    print(colored("⚠️ Falling back to PyPDF2", "yellow"))
                    return PyPDF2Converter() 