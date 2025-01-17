import os
from pathlib import Path
from typing import Optional
import logging
import shutil
from datetime import datetime
from termcolor import colored

# Constants
DB_ROOT = "DB"
GITIGNORE_PATH = ".gitignore"

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
            
            # Create required subdirectories
            os.makedirs(os.path.join(store_path, "converted"), exist_ok=True)  # For converted documents
            os.makedirs(os.path.join(store_path, "cache"), exist_ok=True)      # For embeddings cache
            
            # Initialize metadata file
            metadata_path = os.path.join(store_path, "metadata.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                import json
                json.dump({
                    "name": store_name,
                    "created": datetime.now().isoformat(),
                    "files": {},
                    "last_updated": None
                }, f, indent=2)
            
            # Initialize consolidated metadata
            consolidated_path = os.path.join(store_path, "consolidated.json")
            with open(consolidated_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "store_info": {
                        "name": store_name,
                        "created": datetime.now().isoformat(),
                        "last_updated": None
                    },
                    "documents": {},
                    "global_stats": {
                        "total_documents": 0,
                        "total_references": 0,
                        "total_citations": 0,
                        "total_equations": 0
                    },
                    "relationships": {
                        "citation_network": [],
                        "equation_references": [],
                        "cross_references": []
                    }
                }, f, indent=2)
            print(colored("✓ Initialized consolidated metadata", "green"))
            
            logging.info(f"Created store directory with structure: {store_path}")
            return store_path
        else:
            print(colored(f"ℹ️ Store directory already exists at {store_path}", "blue"))
            return store_path
        
    except Exception as e:
        logger.error(f"Failed to create store directory: {str(e)}")
        print(colored(f"⚠️ Failed to create store directory: {str(e)}", "red"))
        raise