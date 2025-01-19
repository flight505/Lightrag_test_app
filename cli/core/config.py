"""Configuration management for LightRAG CLI."""
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional
import json
import os

class PDFEngine(str, Enum):
    """Available PDF processing engines."""
    AUTO = "auto"
    MARKER = "marker"
    PYMUPDF = "pymupdf"
    PYPDF2 = "pypdf2"

@dataclass
class ProcessingConfig:
    """Configuration for document processing."""
    pdf_engine: PDFEngine = PDFEngine.AUTO
    enable_crossref: bool = True
    enable_scholarly: bool = True
    debug_mode: bool = False
    max_file_size_mb: int = 50
    timeout_seconds: int = 30
    chunk_size: int = 500
    chunk_overlap: int = 50
    chunk_strategy: str = "sentence"

class ConfigManager:
    """Manages CLI configuration."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize configuration manager.
        
        Args:
            config_dir: Optional path to config directory. If not provided, uses ~/.lightrag
        """
        self.config_dir = config_dir or Path.home() / ".lightrag"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "config.json"
        self._load_config()
        
    def _load_config(self) -> None:
        """Load configuration from file."""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                self.processing_config = ProcessingConfig(**{k: v for k, v in config_data.items() if hasattr(ProcessingConfig, k)})
        else:
            self.processing_config = ProcessingConfig()
            self._save_config()
            
    def _save_config(self) -> None:
        """Save configuration to file."""
        config_data = {
            'pdf_engine': self.processing_config.pdf_engine,
            'enable_crossref': self.processing_config.enable_crossref,
            'enable_scholarly': self.processing_config.enable_scholarly,
            'debug_mode': self.processing_config.debug_mode,
            'max_file_size_mb': self.processing_config.max_file_size_mb,
            'timeout_seconds': self.processing_config.timeout_seconds,
            'chunk_size': self.processing_config.chunk_size,
            'chunk_overlap': self.processing_config.chunk_overlap,
            'chunk_strategy': self.processing_config.chunk_strategy
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2)
        
    def get_store_root(self) -> Path:
        """Get the root directory for document stores."""
        store_root = self.config_dir / "stores"
        store_root.mkdir(parents=True, exist_ok=True)
        return store_root
        
    def get_processing_config(self) -> ProcessingConfig:
        """Get the current processing configuration."""
        return self.processing_config
        
    def validate_store_path(self, store_path: Path) -> bool:
        """Validate if a store path exists and is properly structured."""
        if not store_path.exists():
            return False
        if not (store_path / "metadata.json").exists():
            return False
        if not (store_path / "converted").exists():
            return False
        return True 