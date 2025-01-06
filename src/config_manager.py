from dataclasses import dataclass
from enum import Enum
from typing import Optional
import os
from termcolor import colored

class PDFEngine(str, Enum):
    PYMUPDF = "pymupdf"
    PYPDF2 = "pypdf2"
    AUTO = "auto"

@dataclass
class ProcessingConfig:
    """Configuration settings for file processing"""
    pdf_engine: PDFEngine = PDFEngine.AUTO
    enable_crossref: bool = True
    enable_scholarly: bool = True
    debug_mode: bool = False
    max_file_size_mb: int = 50
    timeout_seconds: int = 30

class ConfigManager:
    """Manages configuration settings for file processing"""
    
    def __init__(self):
        try:
            self.config = ProcessingConfig(
                pdf_engine=PDFEngine(os.getenv("PDF_ENGINE", PDFEngine.AUTO)),
                enable_crossref=os.getenv("ENABLE_CROSSREF", "1") == "1",
                enable_scholarly=os.getenv("ENABLE_SCHOLARLY", "1") == "1",
                debug_mode=os.getenv("DEBUG_MODE", "0") == "1",
                max_file_size_mb=int(os.getenv("MAX_FILE_SIZE_MB", "50")),
                timeout_seconds=int(os.getenv("TIMEOUT_SECONDS", "30"))
            )
            print(colored("✓ Configuration loaded successfully", "green"))
        except Exception as e:
            print(colored(f"⚠️ Error loading configuration: {str(e)}", "yellow"))
            self.config = ProcessingConfig()
    
    def get_config(self) -> ProcessingConfig:
        """Get current configuration settings"""
        return self.config
    
    def validate_file(self, file_path: str) -> Optional[str]:
        """Validate file against configuration settings"""
        try:
            if not os.path.exists(file_path):
                return "File does not exist"
                
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if size_mb > self.config.max_file_size_mb:
                return f"File size ({size_mb:.1f}MB) exceeds limit ({self.config.max_file_size_mb}MB)"
            
            return None
        except Exception as e:
            return f"Error validating file: {str(e)}" 