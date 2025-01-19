"""Manages consolidated metadata and citation analysis across document stores."""
import json
import logging
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Dict, Any, Optional, Union

from termcolor import colored

from src.academic_metadata import AcademicMetadata
from cli.core.errors import MetadataError

logger = logging.getLogger(__name__)

class MetadataConsolidator:
    """Manages consolidated metadata and citation analysis across a store"""
    
    def __init__(self, store_path: Union[str, Path]):
        """Initialize the metadata consolidator with a store path."""
        self.store_path = Path(store_path)
        self.metadata_dir = self.store_path / "metadata"
        self.consolidated_file = self.store_path / "consolidated.json"
        self.citation_analysis_path = self.store_path / "citation_analysis.json"
        self.lock = RLock()  # Thread-safe operations
        self.logger = logging.getLogger(__name__)
        
    def _load_json(self, path: Path) -> Dict[str, Any]:
        """Load JSON file with error handling"""
        try:
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading JSON from {path}: {str(e)}")
            return {}
            
    def _save_json(self, path: Path, data: Dict[str, Any]) -> None:
        """Save JSON file with error handling"""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(colored(f"✓ Saved JSON to {path}", "green"))
        except Exception as e:
            logger.error(f"Error saving JSON to {path}: {str(e)}")
            print(colored(f"⚠️ Failed to save JSON to {path}: {str(e)}", "yellow"))

    def initialize_consolidated_json(self) -> None:
        """Creates initial consolidated metadata structure with KG format"""
        base_structure = {
            "store_info": {
                "name": self.store_path.name,
                "created": datetime.now().isoformat(),
                "last_updated": None,
                "version": "2.0.0"
            },
            "nodes": {
                "papers": [],      # Document nodes
                "equations": [],   # Mathematical nodes
                "citations": [],   # Citation nodes
                "authors": [],     # Person nodes
                "contexts": []     # Context nodes
            },
            "relationships": [],   # KG edges with types
            "global_stats": {
                "total_documents": 0,
                "total_references": 0,
                "total_citations": 0,
                "total_equations": 0,
                "total_relationships": 0
            }
        }
        self._save_json(self.consolidated_file, base_structure)
        
    def update_document_metadata(self, doc_id: str, metadata: AcademicMetadata) -> None:
        """Updates consolidated metadata with new document information using KG structure"""
        with self.lock:
            consolidated = self._load_json(self.consolidated_file)
            
            # Create paper node
            paper_node = {
                "id": doc_id,
                "type": "paper",
                "title": metadata.title,
                "metadata": {
                    "authors": [author.model_dump() for author in metadata.authors],
                    "year": metadata.year,
                    "venue": metadata.journal,
                    "identifier": metadata.identifier,
                    "identifier_type": metadata.identifier_type
                }
            }
            
            # Create author nodes and relationships
            for author in metadata.authors:
                author_node = {
                    "id": f"author_{author.full_name}",
                    "type": "author",
                    "name": author.full_name,
                    "metadata": author.model_dump()
                }
                consolidated["nodes"]["authors"].append(author_node)
                consolidated["relationships"].append({
                    "source": doc_id,
                    "target": f"author_{author.full_name}",
                    "type": "written_by",
                    "metadata": {"confidence": 1.0}
                })
            
            # Create equation nodes and relationships
            for idx, eq in enumerate(metadata.equations):
                eq_id = f"{doc_id}_eq_{idx}"
                eq_node = {
                    "id": eq_id,
                    "type": "equation",
                    "raw_text": eq.raw_text,
                    "metadata": {
                        "symbols": list(eq.symbols),
                        "equation_type": eq.equation_type,
                        "context": eq.context
                    }
                }
                consolidated["nodes"]["equations"].append(eq_node)
                consolidated["relationships"].append({
                    "source": doc_id,
                    "target": eq_id,
                    "type": "contains_equation",
                    "metadata": {"context": eq.context}
                })
            
            # Create citation nodes and relationships
            for idx, citation in enumerate(metadata.citations):
                cite_id = f"{doc_id}_cite_{idx}"
                cite_node = {
                    "id": cite_id,
                    "type": "citation",
                    "text": citation.text,
                    "metadata": {
                        "context": citation.context,
                        "references": [ref.to_dict() for ref in citation.references]
                    }
                }
                consolidated["nodes"]["citations"].append(cite_node)
                consolidated["relationships"].append({
                    "source": doc_id,
                    "target": cite_id,
                    "type": "contains_citation",
                    "metadata": {"context": citation.context}
                })
                
                # Add citation-reference relationships
                for ref in citation.references:
                    consolidated["relationships"].append({
                        "source": cite_id,
                        "target": ref.title or ref.raw_text,
                        "type": "cites_paper",
                        "metadata": {
                            "confidence": 1.0 if ref.title else 0.8,
                            "context": citation.context
                        }
                    })
            
            # Update paper nodes
            paper_exists = False
            for i, paper in enumerate(consolidated["nodes"]["papers"]):
                if paper["id"] == doc_id:
                    consolidated["nodes"]["papers"][i] = paper_node
                    paper_exists = True
                    break
            if not paper_exists:
                consolidated["nodes"]["papers"].append(paper_node)
            
            # Update global stats
            stats = consolidated["global_stats"]
            stats["total_documents"] = len(consolidated["nodes"]["papers"])
            stats["total_equations"] = len(consolidated["nodes"]["equations"])
            stats["total_citations"] = len(consolidated["nodes"]["citations"])
            stats["total_relationships"] = len(consolidated["relationships"])
            
            # Save updated data
            consolidated["store_info"]["last_updated"] = datetime.now().isoformat()
            self._save_json(self.consolidated_file, consolidated)
            
    def remove_document_metadata(self, doc_id: str) -> None:
        """Removes document and its relationships from consolidated metadata"""
        with self.lock:
            consolidated = self._load_json(self.consolidated_file)
            
            # Remove paper node
            consolidated["nodes"]["papers"] = [
                p for p in consolidated["nodes"]["papers"] 
                if p["id"] != doc_id
            ]
            
            # Remove related equations
            consolidated["nodes"]["equations"] = [
                eq for eq in consolidated["nodes"]["equations"]
                if not eq["id"].startswith(f"{doc_id}_eq_")
            ]
            
            # Remove related citations
            consolidated["nodes"]["citations"] = [
                cite for cite in consolidated["nodes"]["citations"]
                if not cite["id"].startswith(f"{doc_id}_cite_")
            ]
            
            # Remove relationships
            consolidated["relationships"] = [
                rel for rel in consolidated["relationships"]
                if not (rel["source"] == doc_id or 
                       rel["source"].startswith(f"{doc_id}_") or
                       rel["target"] == doc_id or
                       rel["target"].startswith(f"{doc_id}_"))
            ]
            
            # Update global stats
            stats = consolidated["global_stats"]
            stats["total_documents"] = len(consolidated["nodes"]["papers"])
            stats["total_equations"] = len(consolidated["nodes"]["equations"])
            stats["total_citations"] = len(consolidated["nodes"]["citations"])
            stats["total_relationships"] = len(consolidated["relationships"])
            
            # Save updated data
            consolidated["store_info"]["last_updated"] = datetime.now().isoformat()
            self._save_json(self.consolidated_file, consolidated)

    def consolidate_metadata(self) -> Dict[str, Any]:
        """Consolidate metadata from all documents in the store."""
        try:
            if not self.metadata_dir.exists():
                raise MetadataError(f"Metadata directory not found at {self.metadata_dir}")

            metadata_files = list(self.metadata_dir.glob("*.json"))
            if not metadata_files:
                raise MetadataError("No metadata files found in store")

            consolidated = {
                "document_count": len(metadata_files),
                "total_equations": 0,
                "total_references": 0,
                "documents": []
            }

            for metadata_file in metadata_files:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    doc_metadata = json.load(f)
                    consolidated["total_equations"] += len(doc_metadata.get("equations", []))
                    consolidated["total_references"] += len(doc_metadata.get("references", []))
                    consolidated["documents"].append({
                        "title": doc_metadata.get("title", "Unknown"),
                        "authors": [a.get("full_name", "Unknown") for a in doc_metadata.get("authors", [])],
                        "equations": len(doc_metadata.get("equations", [])),
                        "references": len(doc_metadata.get("references", []))
                    })

            with open(self.consolidated_file, "w", encoding="utf-8") as f:
                json.dump(consolidated, f, indent=2)

            return consolidated

        except Exception as e:
            self.logger.error(f"Error consolidating metadata: {str(e)}")
            raise MetadataError(f"Failed to consolidate metadata: {str(e)}") 