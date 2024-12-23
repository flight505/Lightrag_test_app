import os
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class DocumentValidator:
    """Validates documents before processing in LightRAG"""
    
    def __init__(self, working_dir: str):
        self.working_dir = working_dir
        
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
        store_path = os.path.join(self.working_dir, store_name)
        results = {
            'valid_files': [],
            'invalid_files': [],
            'errors': []
        }
        
        if not os.path.exists(store_path):
            results['errors'].append(f"Store not found: {store_name}")
            return results
            
        for root, _, files in os.walk(store_path):
            for file in files:
                if file.endswith('.txt'):
                    file_path = os.path.join(root, file)
                    is_valid, error = self.validate_file(file_path)
                    
                    if is_valid:
                        results['valid_files'].append(file_path)
                    else:
                        results['invalid_files'].append(file_path)
                        if error:
                            results['errors'].append(f"{file}: {error}")
                            
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