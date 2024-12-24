import os
import logging
from typing import List, Dict, Optional, Tuple
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
            
    def validate_store(self, store_name: str) -> Dict[str, List[str]]:
        """
        Validates all documents in a store
        Returns: {
            'valid_files': [...],
            'invalid_files': [...],
            'errors': [...]
        }
        """
        store_path = os.path.join(DB_ROOT, store_name)
        logger.info(f"Validating store at path: {store_path}")
        
        results = {
            'valid_files': [],
            'invalid_files': [],
            'errors': []
        }
        
        if not os.path.exists(store_path):
            error_msg = f"Store not found at: {store_path}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            return results
            
        # Debug: List all files in directory
        all_files = []
        for root, _, files in os.walk(store_path):
            for file in files:
                file_path = os.path.join(root, file)
                all_files.append(file_path)
        logger.info(f"All files found in store: {all_files}")
        
        # Check if any .txt files exist
        txt_files = [f for f in all_files if f.endswith('.txt')]
        if not txt_files:
            error_msg = f"No .txt files found in {store_path}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            return results
            
        # Validate each .txt file
        for file_path in txt_files:
            logger.info(f"Validating file: {file_path}")
            is_valid, error = self.validate_file(file_path)
            
            if is_valid:
                results['valid_files'].append(file_path)
                logger.info(f"Valid file found: {file_path}")
            else:
                results['invalid_files'].append(file_path)
                if error:
                    results['errors'].append(f"{os.path.basename(file_path)}: {error}")
                    logger.warning(f"Invalid file: {file_path} - {error}")
        
        logger.info(f"Validation results: {results}")
        return results

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