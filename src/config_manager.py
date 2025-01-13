from dataclasses import dataclass
from enum import Enum
from typing import Optional
import os
from pathlib import Path
from termcolor import colored
import logging

logger = logging.getLogger(__name__)

class PDFEngine(str, Enum):
    PYMUPDF = "pymupdf"
    PYPDF2 = "pypdf2"
    MARKER = "marker"
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
    chunk_size: int = 500
    chunk_overlap: int = 50
    chunk_strategy: str = "sentence"
    
    def validate_file(self, file_path: str) -> bool:
        """Validate file exists and meets size requirements"""
        try:
            path = Path(file_path)
            if not path.exists():
                print(colored(f"⚠️ File not found: {file_path}", "yellow"))
                return False
                
            if not path.is_file():
                print(colored(f"⚠️ Not a file: {file_path}", "yellow"))
                return False
                
            size_mb = path.stat().st_size / (1024 * 1024)
            if size_mb > self.max_file_size_mb:
                print(colored(f"⚠️ File too large: {size_mb:.1f}MB > {self.max_file_size_mb}MB", "yellow"))
                return False
                
            return True
            
        except Exception as e:
            print(colored(f"⚠️ Error validating file: {str(e)}", "yellow"))
            return False

class ConfigManager:
    """Manages configuration settings for file processing"""
    
    def __init__(self, **kwargs):
        try:
            # Initialize with environment variables first
            self.config = ProcessingConfig(
                pdf_engine=PDFEngine(os.getenv("PDF_ENGINE", PDFEngine.AUTO)),
                enable_crossref=os.getenv("ENABLE_CROSSREF", "1") == "1",
                enable_scholarly=os.getenv("ENABLE_SCHOLARLY", "1") == "1",
                debug_mode=os.getenv("DEBUG_MODE", "0") == "1",
                max_file_size_mb=int(os.getenv("MAX_FILE_SIZE_MB", "50")),
                timeout_seconds=int(os.getenv("TIMEOUT_SECONDS", "30")),
                chunk_size=int(os.getenv("CHUNK_SIZE", "500")),
                chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "50")),
                chunk_strategy=os.getenv("CHUNK_STRATEGY", "sentence")
            )
            
            # Override with any provided kwargs
            for key, value in kwargs.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
                    logger.info(f"Config override: {key}={value}")
            
            logger.info("Configuration loaded successfully")
            print(colored("✓ Configuration loaded successfully", "green"))
            
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            print(colored(f"⚠️ Error loading configuration: {str(e)}", "yellow"))
            self.config = ProcessingConfig()
    
    def get_config(self) -> ProcessingConfig:
        """Get current configuration settings"""
        return self.config
    
    def validate_file(self, file_path: str) -> Optional[str]:
        """Validate file against configuration settings"""
        try:
            if not os.path.exists(file_path):
                error = "File does not exist"
                logger.error(error)
                return error
                
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if size_mb > self.config.max_file_size_mb:
                error = f"File size ({size_mb:.1f}MB) exceeds limit ({self.config.max_file_size_mb}MB)"
                logger.error(error)
                return error
            
            logger.info(f"File validation passed for: {file_path}")
            return None
            
        except Exception as e:
            error = f"Error validating file: {str(e)}"
            logger.error(error)
            return error 