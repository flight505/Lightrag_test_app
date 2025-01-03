import os
import logging
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
from src.file_manager import DB_ROOT

logger = logging.getLogger(__name__)

class DocumentValidator:
    """Validates documents before processing in LightRAG"""
    
    def __init__(self, working_dir: str):
        self.working_dir = working_dir
        logger.info(f"Validator initialized with working dir: {working_dir}")
        
    def validate_file(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validates a single file
        Returns: (is_valid, error_message)
        """
        try:
            path = Path(file_path)
            
            # Check file exists
            if not path.exists():
                return False, f"File not found: {file_path}"
                
            # Check extension
            if path.suffix != '.txt':
                return False, f"Invalid file type: {path.suffix}. Only .txt files are supported"
                
            # Check file is not empty
            if path.stat().st_size == 0:
                return False, f"File is empty: {file_path}"
                
            # Check file is readable
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read(1024)  # Read first 1KB to test
                    if not content.strip():
                        return False, f"File contains no text content: {file_path}"
            except UnicodeDecodeError:
                return False, f"File is not valid UTF-8 encoded: {file_path}"
                
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating file {file_path}: {str(e)}")
            return False, str(e)
            
    def validate_store(self, store_path: str) -> Dict[str, Any]:
        """
        Validate all files in a store directory
        
        Args:
            store_path: Path to the store directory
            
        Returns:
            Dict containing validation results
        """
        logger.info(f"Validating store at path: {store_path}")
        
        # Get all txt files in the store
        txt_files = [
            os.path.join(store_path, f) 
            for f in os.listdir(store_path) 
            if f.endswith('.txt')
        ]
        
        logger.info(f"All files found in store: {[os.path.basename(f) for f in txt_files]}")
        
        # Validate all files
        return self.validate_files(txt_files)

    def validate_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """
        Validate multiple files and return validation results
        
        Args:
            file_paths: List of file paths to validate
            
        Returns:
            Dict containing valid_files list and invalid_files dict with error messages
        """
        valid_files = []
        invalid_files = {}
        
        for file_path in file_paths:
            is_valid, error_msg = self.validate_file(file_path)
            if is_valid:
                valid_files.append(file_path)
            else:
                invalid_files[file_path] = error_msg
                logger.warning(f"Invalid file {file_path}: {error_msg}")
        
        return {
            "valid_files": valid_files,
            "invalid_files": invalid_files,
            "errors": [f"Invalid file {f}: {err}" for f, err in invalid_files.items()] if invalid_files else []
        }

    def validate_content(self, content: str) -> Tuple[bool, Optional[str]]:
        """
        Validates text content before insertion
        Returns: (is_valid, error_message)
        """
        if not content:
            return False, "Content is empty"
            
        if not content.strip():
            return False, "Content contains only whitespace"
            
        # Add more content validation as needed
        # Example: Check minimum length
        if len(content.split()) < 10:
            return False, "Content too short (minimum 10 words)"
            
        return True, None 