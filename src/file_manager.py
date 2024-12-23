import os
from pathlib import Path
from typing import Optional
import logging
import shutil

# Constants
DB_ROOT = "DB"
GITIGNORE_PATH = ".gitignore"

def create_store_directory(store_name: str) -> Optional[str]:
    """
    Create a store directory directly in DB folder.
    
    Args:
        store_name: Name of the store to create
    
    Returns:
        str: Path to created directory or None if failed
    """
    try:
        # Ensure DB root exists
        if not os.path.exists(DB_ROOT):
            os.makedirs(DB_ROOT)
            
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
            
        # Create new store in DB
        if not os.path.exists(store_path):
            os.makedirs(store_path)
            update_gitignore(store_path)
            logging.info(f"Created store directory: {store_path}")
            return store_path
        else:
            logging.warning(f"Store directory already exists: {store_path}")
            return store_path
        
    except Exception as e:
        logging.error(f"Failed to create store directory: {str(e)}")
        return None

def update_gitignore(store_path: str) -> None:
    """
    Update .gitignore with store directory path.
    
    Args:
        store_path: Path to store directory
    """
    try:
        # Convert to relative path if absolute
        rel_path = os.path.relpath(store_path)
        
        with open(GITIGNORE_PATH, "a+", encoding="utf-8") as f:
            f.seek(0)
            content = f.read()
            if rel_path not in content:
                if content and not content.endswith("\n"):
                    f.write("\n")
                f.write(f"{rel_path}/\n")
                logging.info(f"Added {rel_path}/ to .gitignore")
                
    except Exception as e:
        logging.error(f"Failed to update .gitignore: {str(e)}")