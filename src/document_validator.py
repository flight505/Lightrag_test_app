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
            
    def validate_store(self, store_path: str) -> Dict:
        """Validate the document store directory"""
        logger.info(f"Validating store at path: {store_path}")
        
        # Initialize results
        results = {
            'valid_files': [],
            'errors': []
        }
        
        try:
            # Get all text files in the store
            txt_files = list(Path(store_path).glob("*.txt"))
            
            # Filter out system files
            system_files = ["graph_chunk_entity_relation.graphml", "graph_visualization.html", 
                          "kv_store_full_docs.json", "kv_store_llm_response_cache.json",
                          "kv_store_text_chunks.json", "metadata.json", "vdb_chunks.json",
                          "vdb_entities.json", "vdb_relationships.json"]
            
            txt_files = [f for f in txt_files if f.name not in system_files]
            
            logger.info(f"All files found in store: {[f.name for f in txt_files]}")
            
            if not txt_files:
                error_msg = f"No .txt files found in {store_path}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
                return results
            
            # Validate each file
            for file_path in txt_files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        is_valid, error = self.validate_content(content)
                        if is_valid:
                            results['valid_files'].append(file_path)
                        else:
                            results['errors'].append(f"Invalid content in {file_path}: {error}")
                except Exception as e:
                    results['errors'].append(f"Error reading {file_path}: {str(e)}")
            
            return results
            
        except Exception as e:
            error_msg = f"Error validating store: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
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