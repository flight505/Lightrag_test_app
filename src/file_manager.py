"""File management utilities."""
import os
from pathlib import Path
from typing import Optional
import logging
import shutil
from datetime import datetime
from termcolor import colored

# Constants
DB_ROOT = "DB"
STORE_STRUCTURE = {
    "documents": "Original PDF documents",
    "metadata": "Document metadata files",
    "converted": "Converted text files",
    "cache": "Search cache and embeddings",
    "exports": "Exported data and reports"
}

logger = logging.getLogger(__name__)

def ensure_db_exists() -> None:
    """Ensure DB directory exists with proper permissions"""
    try:
        # Create DB directory if it doesn't exist
        if not os.path.exists(DB_ROOT):
            os.makedirs(DB_ROOT, mode=0o755, exist_ok=True)
            print(colored(f"✓ Created DB directory at {DB_ROOT}", "green"))
        
        # Ensure directory has proper permissions
        os.chmod(DB_ROOT, 0o755)
        
        # Create .gitignore if it doesn't exist
        gitignore_path = ".gitignore"
        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r", encoding="utf-8") as f:
                content = f.read()
            if "DB/" not in content:
                with open(gitignore_path, "a", encoding="utf-8") as f:
                    f.write("\nDB/\n")
        else:
            with open(gitignore_path, "w", encoding="utf-8") as f:
                f.write("DB/\n")
        
        print(colored("✓ DB directory ready", "green"))
        
    except Exception as e:
        logger.error(f"Failed to ensure DB directory: {str(e)}")
        print(colored(f"⚠️ Failed to ensure DB directory: {str(e)}", "red"))
        raise

def create_store_directory(store_name: str) -> Optional[str]:
    """
    Create a store directory with required structure and metadata files.
    
    Args:
        store_name: Name of the store to create
    
    Returns:
        str: Path to created directory or None if failed
    """
    try:
        # Ensure DB exists first
        ensure_db_exists()
        
        # Create store directory
        store_path = os.path.join(DB_ROOT, store_name)
        if not os.path.exists(store_path):
            os.makedirs(store_path, mode=0o755, exist_ok=True)
            print(colored(f"✓ Created store directory at {store_path}", "green"))
            
            # Create required subdirectories with descriptions
            for subdir, description in STORE_STRUCTURE.items():
                subdir_path = os.path.join(store_path, subdir)
                os.makedirs(subdir_path, exist_ok=True)
                print(colored(f"✓ Created {subdir} directory: {description}", "green"))
            
            # Initialize metadata file
            metadata_path = os.path.join(store_path, "metadata.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                import json
                json.dump({
                    "name": store_name,
                    "created": datetime.now().isoformat(),
                    "files": {},
                    "last_updated": None,
                    "document_count": 0,
                    "size": 0,
                    "documents": []
                }, f, indent=2)
            
            # Initialize consolidated metadata
            consolidated_path = os.path.join(store_path, "consolidated.json")
            with open(consolidated_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "store_info": {
                        "name": store_name,
                        "created": datetime.now().isoformat(),
                        "last_updated": None,
                        "version": "1.0.0"
                    },
                    "nodes": {
                        "papers": [],
                        "equations": [],
                        "citations": [],
                        "authors": [],
                        "contexts": []
                    },
                    "relationships": [],
                    "global_stats": {
                        "total_papers": 0,
                        "total_equations": 0,
                        "total_citations": 0,
                        "total_authors": 0,
                        "total_relationships": 0
                    }
                }, f, indent=2)
            print(colored("✓ Initialized metadata files", "green"))
            
            logging.info(f"Created store directory with structure: {store_path}")
            return store_path
        else:
            print(colored(f"ℹ️ Store directory already exists at {store_path}", "blue"))
            return store_path
        
    except Exception as e:
        logger.error(f"Failed to create store directory: {str(e)}")
        print(colored(f"⚠️ Failed to create store directory: {str(e)}", "red"))
        raise

def validate_store_structure(store_path: str) -> bool:
    """
    Validate if a store has the correct directory structure.
    
    Args:
        store_path: Path to the store directory
    
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        # Check if store exists and is a directory
        if not os.path.exists(store_path) or not os.path.isdir(store_path):
            return False
            
        # Check required subdirectories
        for subdir in STORE_STRUCTURE.keys():
            if not os.path.exists(os.path.join(store_path, subdir)):
                return False
                
        # Check required metadata files
        required_files = ["metadata.json", "consolidated.json"]
        for file in required_files:
            if not os.path.exists(os.path.join(store_path, file)):
                return False
                
        return True
        
    except Exception as e:
        logger.error(f"Error validating store structure: {str(e)}")
        return False