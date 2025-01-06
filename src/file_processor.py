from typing import Optional, Dict, Any
import os
from termcolor import colored
from .config_manager import ConfigManager
from .pdf_converter import PDFConverterFactory
from .academic_metadata import MetadataExtractor

class FileProcessor:
    """Handles file processing and conversion with configurable settings"""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or ConfigManager()
        self.pdf_converter = PDFConverterFactory.create_converter(self.config_manager)
        self.metadata_extractor = MetadataExtractor(debug=self.config_manager.get_config().debug_mode)
    
    def process_file(self, file_path: str) -> Dict[str, Any]:
        """Process a file and extract its content and metadata"""
        try:
            # Validate file
            error = self.config_manager.validate_file(file_path)
            if error:
                print(colored(f"⚠️ File validation failed: {error}", "red"))
                return {"error": error}
            
            # Extract text and metadata
            text = self.pdf_converter.extract_text(file_path)
            metadata = self.pdf_converter.extract_metadata(file_path)
            
            # Extract academic metadata
            academic_metadata = self.metadata_extractor.extract_metadata(
                text=text,
                doc_id=os.path.basename(file_path),
                pdf_path=file_path
            )
            
            return {
                "text": text,
                "metadata": metadata,
                "academic_metadata": academic_metadata
            }
            
        except Exception as e:
            error_msg = f"Error processing file: {str(e)}"
            print(colored(f"⚠️ {error_msg}", "red"))
            return {"error": error_msg}
    
    def is_supported_file(self, file_path: str) -> bool:
        """Check if the file type is supported"""
        return file_path.lower().endswith('.pdf')