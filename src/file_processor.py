import os
import logging
from typing import Dict, List, Optional, Tuple, Generator
from pathlib import Path
from datetime import datetime
import hashlib
import json
import re
from termcolor import colored
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import concurrent.futures

logger = logging.getLogger(__name__)

@dataclass
class ChunkingConfig:
    """Configuration for document chunking"""
    chunk_size: int = 500
    chunk_overlap: int = 50
    chunk_strategy: str = "sentence"  # "sentence", "paragraph", or "fixed"
    preserve_markdown: bool = True
    equation_handling: str = "preserve"

class BatchInserter:
    """Handles batch insertion of documents"""
    def __init__(self, rag, batch_size: int = 10):
        self.rag = rag
        self.batch_size = batch_size
        self.current_batch = []
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.flush()
        
    def add(self, document: Dict):
        self.current_batch.append(document)
        if len(self.current_batch) >= self.batch_size:
            self.flush()
            
    def flush(self):
        if self.current_batch:
            self.rag.insert_batch(self.current_batch)
            self.current_batch = []

class FileProcessor:
    """Handles file preprocessing and tracking with enhanced equation support"""
    
    def __init__(self, store_path: str, chunking_config: Optional[ChunkingConfig] = None):
        self.store_path = Path(store_path)
        self.metadata_file = self.store_path / "metadata.json"
        self.metadata = self._load_metadata()
        self.pdf_converter = None
        self.equation_pattern = re.compile(r'\$\$(.*?)\$\$', re.DOTALL)
        self.reference_pattern = re.compile(r'\[@(.*?)\]', re.DOTALL)
        self.chunking_config = chunking_config or ChunkingConfig()
        logger.info(f"FileProcessor initialized for store: {store_path}")

    def _extract_equations(self, text: str) -> List[Tuple[str, str]]:
        """Extract LaTeX equations and generate unique identifiers"""
        equations = []
        for idx, match in enumerate(self.equation_pattern.finditer(text)):
            equation = match.group(1).strip()
            equation_id = f"eq_{hashlib.md5(equation.encode()).hexdigest()[:8]}"
            equations.append((equation_id, equation))
        return equations

    def _extract_references(self, text: str) -> List[str]:
        """Extract academic references from the text"""
        return [ref.group(1) for ref in self.reference_pattern.finditer(text)]

    def process_document(self, file_path: str) -> Dict:
        """Process a single document with rich metadata"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            metadata = {
                "source": os.path.basename(file_path),
                "created": datetime.fromtimestamp(os.path.getctime(file_path)).isoformat(),
                "modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
                "file_type": Path(file_path).suffix[1:],
                "size": os.path.getsize(file_path),
                "equations": self._extract_equations(content),
                "references": self._extract_references(content),
                "chunks": self._get_chunk_info(content)
            }
            
            return {"content": content, "metadata": metadata}
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            raise

    def process_large_file(self, file_path: str, chunk_size: int = 1024*1024) -> Generator:
        """Process large files in chunks to manage memory"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield self._process_chunk(chunk, file_path)
        except Exception as e:
            logger.error(f"Error processing large file {file_path}: {str(e)}")
            raise

    def _process_chunk(self, chunk: str, file_path: str) -> Dict:
        """Process a single chunk of a large file"""
        metadata = {
            "source": os.path.basename(file_path),
            "chunk_hash": hashlib.md5(chunk.encode()).hexdigest(),
            "equations": self._extract_equations(chunk),
            "references": self._extract_references(chunk)
        }
        return {"content": chunk, "metadata": metadata}

    def _get_chunk_info(self, content: str) -> Dict:
        """Get information about how the content will be chunked"""
        if self.chunking_config.chunk_strategy == "sentence":
            chunks = self._split_into_sentences(content)
        elif self.chunking_config.chunk_strategy == "paragraph":
            chunks = content.split('\n\n')
        else:  # fixed size chunks
            chunks = [content[i:i + self.chunking_config.chunk_size] 
                     for i in range(0, len(content), self.chunking_config.chunk_size)]
        
        return {
            "total_chunks": len(chunks),
            "avg_chunk_size": sum(len(c) for c in chunks) / len(chunks) if chunks else 0,
            "strategy": self.chunking_config.chunk_strategy
        }

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences while preserving equations and markdown"""
        # Basic sentence splitting that preserves markdown and equations
        sentence_endings = r'(?<=[.!?])\s+(?=[A-Z])'
        if self.chunking_config.preserve_markdown:
            # Don't split inside markdown code blocks or equations
            text = re.sub(r'```.*?```', lambda m: m.group().replace('.', '∎'), text, flags=re.DOTALL)
            text = re.sub(r'\$\$.*?\$\$', lambda m: m.group().replace('.', '∎'), text, flags=re.DOTALL)
        
        sentences = re.split(sentence_endings, text)
        return [s.strip() for s in sentences if s.strip()]

    def batch_process_files(self, file_paths: List[str], rag, max_workers: int = 4) -> None:
        """Process multiple files in parallel with progress tracking"""
        total = len(file_paths)
        processed = 0
        
        print(colored(f"\nProcessing {total} files...", "cyan"))
        
        with BatchInserter(rag) as inserter:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {
                    executor.submit(self.process_document, file_path): file_path 
                    for file_path in file_paths
                }
                
                for future in concurrent.futures.as_completed(future_to_file):
                    file_path = future_to_file[future]
                    try:
                        doc = future.result()
                        inserter.add(doc)
                        processed += 1
                        self._update_progress(processed, total, file_path)
                    except Exception as e:
                        print(colored(f"\n✗ Error processing {file_path}: {str(e)}", "red"))

    def _update_progress(self, current: int, total: int, current_file: str) -> None:
        """Update the progress bar"""
        bar_length = 50
        progress = current / total
        filled = int(bar_length * progress)
        bar = '=' * filled + '-' * (bar_length - filled)
        print(f'\rProgress: [{bar}] {current}/{total} | Current: {os.path.basename(current_file)}', end='')
        if current == total:
            print(colored("\n\nProcessing complete! ✓", "green"))

    def _load_metadata(self) -> Dict:
        """Load metadata from file or create new if not exists"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"files": {}, "last_updated": None}

    def _save_metadata(self) -> None:
        """Save metadata to file"""
        self.metadata["last_updated"] = datetime.now().isoformat()
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2)