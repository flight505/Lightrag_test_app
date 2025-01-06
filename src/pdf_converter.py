from abc import ABC, abstractmethod
from typing import Dict, Any
import fitz
from PyPDF2 import PdfReader
from termcolor import colored
import logging
import os
from .config_manager import PDFEngine, ConfigManager

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
    """PDF converter using Marker with optimized settings for M3 Max"""
    
    def __init__(self):
        self._marker = None
        self._text_from_rendered = None
        self._initialize_fallback_extractors()
    
    def _initialize_fallback_extractors(self):
        """Initialize fallback metadata extractors"""
        self.pymupdf_converter = PyMuPDFConverter()
        self.pypdf2_converter = PyPDF2Converter()
    
    def _ensure_marker_initialized(self):
        """Lazy initialization of Marker only when needed"""
        if self._marker is not None:
            return
            
        try:
            # Disable tokenizers warning
            os.environ["TOKENIZERS_PARALLELISM"] = "false"
            
            # Set GOOGLE_API_KEY from GEMINI_API_KEY for Marker compatibility
            gemini_key = os.getenv("GEMINI_API_KEY")
            if gemini_key:
                os.environ["GOOGLE_API_KEY"] = gemini_key
                logger.info("Set GOOGLE_API_KEY from GEMINI_API_KEY")
            
            from marker.converters.pdf import PdfConverter
            from marker.models import create_model_dict
            from marker.output import text_from_rendered
            from marker.config.parser import ConfigParser
            
            logger.info("Initializing Marker with optimized M3 Max config")
            
            # Configure marker with optimizations for M3 Max
            config = {
                "output_format": "markdown",
                "force_ocr": False,  # Only use OCR when needed
                "extract_images": True,  # Enable image extraction for LLM descriptions
                "batch_multiplier": 12,  # Larger batches for M3 Max
                "num_workers": 8,  # Parallel workers
                "langs": ["English"],  # Optimize for English
                "device": "mps",  # Use MPS for M3 Max
                "model_precision": "float16",  # Use half precision
                "max_batch_size": 16,  # Larger batch size
                
                # Layout detection settings - adjusted for better section header detection
                "layout_coverage_min_lines": 1,  # Reduced to catch single-line headers
                "layout_coverage_threshold": 0.3,  # Reduced to be more lenient
                "document_ocr_threshold": 0.7,
                "error_model_segment_length": 1024,
                "min_line_height": 6,  # Minimum line height to consider
                "min_block_height": 8,  # Minimum block height for sections
                
                # OCR settings
                "detection_batch_size": 8,
                "recognition_batch_size": 8,
                
                # LLM settings
                "use_llm": True,  # Enable LLM for image descriptions
                "google_api_key": os.getenv("GOOGLE_API_KEY"),  # Use the key we set earlier
                "model_name": "gemini-1.5-flash",  # Fast Gemini model
                "max_retries": 3,
                "max_concurrency": 3,
                "timeout": 60,
                "confidence_threshold": 0.75,
                
                # Additional layout settings
                "ignore_page_numbers": True,  # Don't treat page numbers as sections
                "merge_small_blocks": True,  # Merge small text blocks
                "layout_tolerance": 3.0,  # More tolerant layout analysis
            }
            
            if not os.getenv("GOOGLE_API_KEY"):
                logger.warning("No Google API key found, LLM features will be limited")
                config["use_llm"] = False
            else:
                logger.info("LLM features enabled for image descriptions")
            
            # Get custom processor list without problematic section header processor
            processor_list = [
                "marker.processors.blockquote.BlockquoteProcessor",
                "marker.processors.code.CodeProcessor",
                "marker.processors.document_toc.DocumentTOCProcessor",
                "marker.processors.equation.EquationProcessor",
                "marker.processors.footnote.FootnoteProcessor",
                "marker.processors.ignoretext.IgnoreTextProcessor",
                "marker.processors.line_numbers.LineNumbersProcessor",
                "marker.processors.list.ListProcessor",
                "marker.processors.page_header.PageHeaderProcessor",
                "marker.processors.table.TableProcessor",
                "marker.processors.llm.llm_table.LLMTableProcessor",
                "marker.processors.llm.llm_form.LLMFormProcessor",
                "marker.processors.text.TextProcessor",
                "marker.processors.llm.llm_text.LLMTextProcessor",
                "marker.processors.llm.llm_complex.LLMComplexRegionProcessor",
                "marker.processors.llm.llm_image_description.LLMImageDescriptionProcessor",
                "marker.processors.debug.DebugProcessor",
            ]
            
            logger.info("Creating ConfigParser")
            config_parser = ConfigParser(config)
            
            # Initialize the converter with custom processor list
            logger.info("Initializing PdfConverter")
            self._marker = PdfConverter(
                artifact_dict=create_model_dict(),
                config=config_parser.generate_config_dict(),
                processor_list=processor_list,  # Use our custom processor list
                renderer=config_parser.get_renderer()
            )
            
            # Store text_from_rendered function for later use
            self._text_from_rendered = text_from_rendered
            
            # Enable LLM if configured
            if config["use_llm"]:
                logger.info("Enabling LLM support for image descriptions")
                self._marker.use_llm = True
            
            logger.info("Initialized Marker PDF converter with M3 Max optimized configuration")
            print(colored("✓ Initialized Marker PDF converter", "green"))
            
        except Exception as e:
            logger.error(f"Failed to initialize Marker: {str(e)}")
            print(colored(f"⚠️ Failed to initialize Marker: {str(e)}", "red"))
            raise
    
    def extract_text(self, file_path: str) -> str:
        try:
            # Only initialize Marker when actually converting
            self._ensure_marker_initialized()
            
            logger.info(f"Converting PDF with Marker: {file_path}")
            # Use marker as callable and text_from_rendered to extract text
            rendered = self._marker(file_path)
            logger.info("PDF rendered successfully")
            
            text, _, _ = self._text_from_rendered(rendered)
            logger.info("Text extracted from rendered output")
            
            print(colored("✓ Text extracted with Marker", "green"))
            return text
            
        except Exception as e:
            logger.error(f"Marker text extraction error: {str(e)}", exc_info=True)
            print(colored(f"⚠️ Marker text extraction error: {str(e)}", "yellow"))
            # Fall back to PyMuPDF for text extraction
            return self.pymupdf_converter.extract_text(file_path)
    
    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata using proven extraction chain"""
        metadata = {}
        
        # 1. Try PyMuPDF metadata (primary source)
        try:
            metadata = self.pymupdf_converter.extract_metadata(file_path)
            if metadata:
                logger.info("Metadata extracted with PyMuPDF")
                print(colored("✓ Metadata extracted with PyMuPDF", "green"))
                return metadata
        except Exception as e:
            logger.warning(f"PyMuPDF metadata extraction failed: {str(e)}")
            print(colored("⚠️ PyMuPDF metadata extraction failed", "yellow"))
        
        # 2. Try PyPDF2 metadata as fallback
        try:
            metadata = self.pypdf2_converter.extract_metadata(file_path)
            if metadata:
                logger.info("Metadata extracted with PyPDF2")
                print(colored("✓ Metadata extracted with PyPDF2", "green"))
                return metadata
        except Exception as e:
            logger.warning(f"PyPDF2 metadata extraction failed: {str(e)}")
            print(colored("⚠️ PyPDF2 metadata extraction failed", "yellow"))
        
        # 3. If all else fails, try to extract from text
        try:
            text = self.extract_text(file_path)
            if text:
                # Note: This will be handled by academic_metadata.py which has the 
                # DOI extraction and CrossRef lookup logic
                logger.info("Metadata will be extracted from text")
                print(colored("ℹ️ Metadata will be extracted from text", "blue"))
            return {}
        except Exception as e:
            logger.error(f"Text-based metadata extraction failed: {str(e)}")
            print(colored("⚠️ Text-based metadata extraction failed", "yellow"))
            return {}

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