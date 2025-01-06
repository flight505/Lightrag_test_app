from abc import ABC, abstractmethod
from typing import Dict, Any
import fitz
from PyPDF2 import PdfReader
from termcolor import colored
from .config_manager import PDFEngine, ConfigManager

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

class PyMuPDFConverter(PDFConverter):
    """PDF converter using PyMuPDF (fitz)"""
    
    def extract_text(self, file_path: str) -> str:
        try:
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            print(colored("✓ Text extracted with PyMuPDF", "green"))
            return text
        except Exception as e:
            print(colored(f"⚠️ PyMuPDF text extraction error: {str(e)}", "yellow"))
            return ""
    
    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        try:
            doc = fitz.open(file_path)
            metadata = doc.metadata
            doc.close()
            print(colored("✓ Metadata extracted with PyMuPDF", "green"))
            return metadata
        except Exception as e:
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
            print(colored("✓ Text extracted with PyPDF2", "green"))
            return text
        except Exception as e:
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
                print(colored("✓ Metadata extracted with PyPDF2", "green"))
                return converted
            return {}
        except Exception as e:
            print(colored(f"⚠️ PyPDF2 metadata extraction error: {str(e)}", "yellow"))
            return {}

class PDFConverterFactory:
    """Factory for creating PDF converters"""
    
    @staticmethod
    def create_converter(config_manager: ConfigManager) -> PDFConverter:
        engine = config_manager.get_config().pdf_engine
        
        if engine == PDFEngine.PYMUPDF:
            return PyMuPDFConverter()
        elif engine == PDFEngine.PYPDF2:
            return PyPDF2Converter()
        else:  # AUTO - try PyMuPDF first, fallback to PyPDF2
            try:
                converter = PyMuPDFConverter()
                # Test if PyMuPDF is working
                converter.extract_metadata({})
                return converter
            except Exception:
                print(colored("⚠️ Falling back to PyPDF2", "yellow"))
                return PyPDF2Converter() 