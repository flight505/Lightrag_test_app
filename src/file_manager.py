import os
from typing import Optional
import logging
import shutil
from datetime import datetime

# Constants
DB_ROOT = "DB"
GITIGNORE_PATH = ".gitignore"

def create_store_directory(store_name: str) -> Optional[str]:
    """
    Create a store directory with required structure and metadata files.
    
    Args:
        store_name: Name of the store to create
    
    Returns:
        str: Path to created directory or None if failed
    """
    try:
        # Ensure DB root exists and is in gitignore
        if not os.path.exists(DB_ROOT):
            os.makedirs(DB_ROOT)
            # Add DB_ROOT to gitignore if not already present
            try:
                with open(GITIGNORE_PATH, "a+", encoding="utf-8") as f:
                    f.seek(0)
                    content = f.read()
                    if DB_ROOT not in content:
                        if content and not content.endswith("\n"):
                            f.write("\n")
                        f.write(f"{DB_ROOT}/\n")
                        logging.info(f"Added {DB_ROOT}/ to .gitignore")
            except Exception as e:
                logging.warning(f"Failed to update .gitignore, but continuing: {str(e)}")
            
        # Create store path directly in DB
        store_path = os.path.join(DB_ROOT, store_name)
        
        # If store exists outside DB, move it into DB
        if os.path.exists(store_name):
            if not os.path.exists(store_path):
                shutil.move(store_name, store_path)
                logging.info(f"Moved existing store into DB: {store_path}")
            else:
                shutil.rmtree(store_name)  # Remove duplicate outside DB
                logging.warning(f"Removed duplicate store outside DB: {store_name}")
            return store_path
            
        # Create new store in DB with required structure
        if not os.path.exists(store_path):
            os.makedirs(store_path)
            
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
            
            logging.info(f"Created store directory with structure: {store_path}")
            return store_path
        else:
            logging.warning(f"Store directory already exists: {store_path}")
            return store_path
        
    except Exception as e:
        logging.error(f"Failed to create store directory: {str(e)}")
        return None