"""Store management for LightRAG CLI."""
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import shutil
from datetime import datetime

from .config import ConfigManager
from .errors import StoreError

class StoreManager:
    """Manages document stores for LightRAG CLI."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize store manager.
        
        Args:
            config_dir: Optional path to config directory. If not provided, uses ~/.lightrag
        """
        self.config = ConfigManager(config_dir)
        self.store_root = self.config.get_store_root()
        
    def create_store(self, name: str) -> Path:
        """Create a new document store.
        
        Args:
            name: Name of the store to create
            
        Returns:
            Path to the created store
            
        Raises:
            StoreError: If store already exists or creation fails
        """
        store_path = self.store_root / name
        if store_path.exists():
            raise StoreError(f"Store '{name}' already exists")
            
        try:
            # Create store directory structure
            store_path.mkdir(parents=True)
            (store_path / "converted").mkdir()
            (store_path / "cache").mkdir()
            (store_path / "cache" / "embeddings").mkdir()
            (store_path / "cache" / "api_responses").mkdir()
            
            # Initialize metadata file
            with open(store_path / "metadata.json", 'w', encoding='utf-8') as f:
                json.dump({
                    "name": name,
                    "created": datetime.now().isoformat(),
                    "updated": datetime.now().isoformat(),
                    "documents": []
                }, f, indent=2)
                
            return store_path
            
        except Exception as e:
            if store_path.exists():
                shutil.rmtree(store_path)
            raise StoreError(f"Failed to create store: {str(e)}")
            
    def list_stores(self) -> List[str]:
        """List all available document stores.
        
        Returns:
            List of store names
        """
        if not self.store_root.exists():
            return []
            
        return [p.name for p in self.store_root.iterdir() 
                if p.is_dir() and self.validate_store_path(p)]
                
    def get_store(self, name: str) -> Path:
        """Get path to a specific store.
        
        Args:
            name: Name of the store
            
        Returns:
            Path to the store
            
        Raises:
            StoreError: If store doesn't exist or is invalid
        """
        store_path = self.store_root / name
        if not self.validate_store_path(store_path):
            raise StoreError(f"Store '{name}' not found or invalid")
        return store_path
        
    def delete_store(self, name: str) -> None:
        """Delete a document store.
        
        Args:
            name: Name of the store to delete
            
        Raises:
            StoreError: If store doesn't exist or deletion fails
        """
        store_path = self.store_root / name
        if not store_path.exists():
            raise StoreError(f"Store '{name}' not found")
            
        try:
            shutil.rmtree(store_path)
        except Exception as e:
            raise StoreError(f"Failed to delete store: {str(e)}")
            
    def get_store_info(self, name: str) -> Dict[str, Any]:
        """Get information about a store.
        
        Args:
            name: Name of the store
            
        Returns:
            Dictionary containing store information
            
        Raises:
            StoreError: If store doesn't exist or is invalid
        """
        store_path = self.get_store(name)
        try:
            with open(store_path / "metadata.json", 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                
            # Calculate store size
            size = sum(f.stat().st_size for f in store_path.rglob('*') if f.is_file())
            
            return {
                "name": name,
                "path": str(store_path),
                "document_count": len(metadata.get("documents", [])),
                "size": size,
                "created": metadata.get("created", ""),
                "updated": metadata.get("updated", "")
            }
        except Exception as e:
            raise StoreError(f"Failed to get store info: {str(e)}")
            
    def validate_store_path(self, store_path: Path) -> bool:
        """Validate if a store path exists and is properly structured.
        
        Args:
            store_path: Path to validate
            
        Returns:
            True if path is a valid store, False otherwise
        """
        if not store_path.exists() or not store_path.is_dir():
            return False
            
        # Check required subdirectories
        if not all((store_path / d).exists() for d in ["converted", "cache"]):
            return False
            
        # Check metadata file
        metadata_path = store_path / "metadata.json"
        if not metadata_path.exists():
            return False
            
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                return all(k in metadata for k in ["name", "created", "updated", "documents"])
        except:
            return False
            
    def update_store_metadata(self, name: str, metadata: dict) -> None:
        """Update store metadata.
        
        Args:
            name: Name of the store
            metadata: Updated metadata dictionary
            
        Raises:
            StoreError: If store doesn't exist or update fails
        """
        store_path = self.get_store(name)
        metadata["updated"] = datetime.now().isoformat()
        
        try:
            with open(store_path / "metadata.json", 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            raise StoreError(f"Failed to update store metadata: {str(e)}") 