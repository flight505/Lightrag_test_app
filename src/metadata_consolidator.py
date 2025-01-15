"""Manages consolidated metadata and citation analysis across document stores."""
import json
import logging
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Dict, Any, Optional

from termcolor import colored

from .academic_metadata import AcademicMetadata
from .base_metadata import Author, Reference

logger = logging.getLogger(__name__)

class MetadataConsolidator:
    """Manages consolidated metadata and citation analysis across a store"""
    
    def __init__(self, store_path: Path):
        """Initialize consolidator with store path"""
        self.store_path = Path(store_path)
        self.consolidated_path = self.store_path / "consolidated_metadata.json"
        self.citation_analysis_path = self.store_path / "citation_analysis.json"
        self.lock = RLock()  # Thread-safe operations
        
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
        """Creates initial consolidated metadata structure"""
        base_structure = {
            "store_info": {
                "name": self.store_path.name,
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
        }
        self._save_json(self.consolidated_path, base_structure)
        
    def update_document_metadata(self, doc_id: str, metadata: AcademicMetadata) -> None:
        """Updates consolidated metadata with new document information"""
        with self.lock:
            consolidated = self._load_json(self.consolidated_path)
            
            # Update document entry
            consolidated["documents"][doc_id] = {
                "title": metadata.title,
                "authors": [author.model_dump() for author in metadata.authors],
                "references_count": len(metadata.references),
                "citations_count": len(metadata.citations),
                "equations_count": len(metadata.equations),
                "last_updated": datetime.now().isoformat()
            }
            
            # Update global stats
            self._update_global_stats(consolidated)
            
            # Update relationships
            self._update_relationships(consolidated, doc_id, metadata)
            
            # Save updated data
            consolidated["store_info"]["last_updated"] = datetime.now().isoformat()
            self._save_json(self.consolidated_path, consolidated)
            
            # Update citation analysis
            self._update_citation_analysis(doc_id, metadata)
            
    def _update_global_stats(self, consolidated: Dict[str, Any]) -> None:
        """Update global statistics in consolidated metadata"""
        stats = consolidated["global_stats"]
        stats["total_documents"] = len(consolidated["documents"])
        stats["total_references"] = sum(doc["references_count"] for doc in consolidated["documents"].values())
        stats["total_citations"] = sum(doc["citations_count"] for doc in consolidated["documents"].values())
        stats["total_equations"] = sum(doc["equations_count"] for doc in consolidated["documents"].values())
        
    def _update_relationships(self, consolidated: Dict[str, Any], doc_id: str, metadata: AcademicMetadata) -> None:
        """Update relationship graphs in consolidated metadata"""
        relationships = consolidated["relationships"]
        
        # Clear existing relationships for this document
        relationships["citation_network"] = [
            rel for rel in relationships["citation_network"]
            if rel["source"] != doc_id and rel["target"] != doc_id
        ]
        
        # Add citation relationships
        for citation in metadata.citations:
            for ref in citation.references:
                relationships["citation_network"].append({
                    "source": doc_id,
                    "target": ref.title or ref.raw_text,
                    "context": citation.context
                })
                
        # Update equation references
        relationships["equation_references"] = [
            rel for rel in relationships["equation_references"]
            if rel["document_id"] != doc_id
        ]
        for eq in metadata.equations:
            relationships["equation_references"].append({
                "document_id": doc_id,
                "equation": eq.raw_text,
                "context": eq.context
            })
            
    def _update_citation_analysis(self, doc_id: str, metadata: AcademicMetadata) -> None:
        """Update citation analysis JSON"""
        with self.lock:
            analysis = self._load_json(self.citation_analysis_path)
            
            # Update document citations
            analysis[doc_id] = {
                "citations_count": len(metadata.citations),
                "references_count": len(metadata.references),
                "citation_contexts": [
                    {"text": cit.text, "context": cit.context}
                    for cit in metadata.citations
                ]
            }
            
            # Update global stats
            total_citations = 0
            total_references = 0
            for doc in analysis.values():
                if isinstance(doc, dict) and "global_stats" not in doc:
                    total_citations += len(doc.get("citation_contexts", []))
                    total_references += doc.get("references_count", 0)
            
            analysis["global_stats"] = {
                "total_citations": total_citations,
                "total_references": total_references,
                "last_updated": datetime.now().isoformat()
            }
            
            self._save_json(self.citation_analysis_path, analysis)
            
    def remove_document_metadata(self, doc_id: str) -> None:
        """Removes document from consolidated metadata"""
        with self.lock:
            # Update consolidated metadata
            consolidated = self._load_json(self.consolidated_path)
            if doc_id in consolidated["documents"]:
                del consolidated["documents"][doc_id]
                self._update_global_stats(consolidated)
                self._clean_relationships(consolidated, doc_id)
                consolidated["store_info"]["last_updated"] = datetime.now().isoformat()
                self._save_json(self.consolidated_path, consolidated)
            
            # Update citation analysis
            analysis = self._load_json(self.citation_analysis_path)
            if doc_id in analysis:
                del analysis[doc_id]
                if "global_stats" in analysis:
                    analysis["global_stats"]["last_updated"] = datetime.now().isoformat()
                self._save_json(self.citation_analysis_path, analysis)
                
    def _clean_relationships(self, consolidated: Dict[str, Any], doc_id: str) -> None:
        """Remove all relationships involving the specified document"""
        relationships = consolidated["relationships"]
        
        # Clean citation network
        relationships["citation_network"] = [
            rel for rel in relationships["citation_network"]
            if rel["source"] != doc_id and rel["target"] != doc_id
        ]
        
        # Clean equation references
        relationships["equation_references"] = [
            rel for rel in relationships["equation_references"]
            if rel["document_id"] != doc_id
        ] 