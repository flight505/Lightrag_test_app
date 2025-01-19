"""Store management for LightRAG CLI."""
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import shutil
from datetime import datetime

from rich.console import Console
from rich.table import Table

from .config import ConfigManager
from .errors import StoreError

console = Console()

class StoreManager:
    """Manages document stores for LightRAG CLI."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize store manager.
        
        Args:
            config_dir: Path to config directory. If not provided, uses ~/.lightrag
        """
        self.config = ConfigManager(config_dir)
        self.store_root = self.config.config_dir / "stores"
        self.store_root.mkdir(exist_ok=True)
        
    def store_exists(self, store_name: str) -> bool:
        """Check if a store exists.
        
        Args:
            store_name: Name of the store to check
            
        Returns:
            bool: True if store exists, False otherwise
        """
        store_path = self.store_root / store_name
        return store_path.exists() and store_path.is_dir()
        
    def create_store(self, store_name: str) -> None:
        """Create a new document store.
        
        Args:
            store_name: Name of the store to create
            
        Raises:
            StoreError: If store already exists or creation fails
        """
        store_path = self.store_root / store_name
        if store_path.exists():
            raise StoreError(f"Store '{store_name}' already exists")
            
        try:
            # Create store directory
            store_path.mkdir()
            
            # Create subdirectories
            (store_path / "documents").mkdir()
            (store_path / "metadata").mkdir()
            (store_path / "text").mkdir()
            
            # Initialize metadata file
            metadata = {
                "name": store_name,
                "created": str(datetime.now()),
                "last_updated": str(datetime.now()),
                "version": "1.0.0",
                "documents": []
            }
            with open(store_path / "metadata.json", "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
                
            # Initialize consolidated metadata
            consolidated = {
                "store_info": {
                    "name": store_name,
                    "created": str(datetime.now()),
                    "last_updated": str(datetime.now()),
                    "version": "2.0.0"
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
                    "total_documents": 0,
                    "total_equations": 0,
                    "total_citations": 0,
                    "total_authors": 0,
                    "total_relationships": 0
                }
            }
            with open(store_path / "consolidated.json", "w", encoding="utf-8") as f:
                json.dump(consolidated, f, indent=2)
                
            console.print(f"✓ Created store '{store_name}'", style="green")
            
        except Exception as e:
            if store_path.exists():
                shutil.rmtree(store_path)
            raise StoreError(f"Failed to create store: {str(e)}")
            
    def list_stores(self) -> List[Dict]:
        """List all document stores.
        
        Returns:
            list: List of store metadata dictionaries
        """
        stores = []
        for store_path in self.store_root.iterdir():
            if store_path.is_dir():
                try:
                    with open(store_path / "metadata.json", "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                        stores.append(metadata)
                except:
                    # Skip stores with invalid metadata
                    continue
        return stores
        
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
        
    def delete_store(self, store_name: str) -> None:
        """Delete a document store.
        
        Args:
            store_name: Name of the store to delete
            
        Raises:
            StoreError: If store doesn't exist or deletion fails
        """
        store_path = self.store_root / store_name
        if not store_path.exists():
            raise StoreError(f"Store '{store_name}' not found")
            
        try:
            shutil.rmtree(store_path)
            console.print(f"✓ Deleted store '{store_name}'", style="green")
        except Exception as e:
            raise StoreError(f"Failed to delete store: {str(e)}")
            
    def get_store_info(self, store_name: str) -> Dict:
        """Get information about a store.
        
        Args:
            store_name: Name of the store
            
        Returns:
            dict: Store metadata
            
        Raises:
            StoreError: If store doesn't exist or metadata is invalid
        """
        store_path = self.store_root / store_name
        if not store_path.exists():
            raise StoreError(f"Store '{store_name}' not found")
            
        try:
            with open(store_path / "metadata.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise StoreError(f"Failed to read store metadata: {str(e)}")
            
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