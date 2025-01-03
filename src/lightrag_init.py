import logging
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
import time
import re
from concurrent import futures

from lightrag import LightRAG, QueryParam
from lightrag.llm import gpt_4o_complete, gpt_4o_mini_complete, openai_embedding
from lightrag.utils import EmbeddingFunc
from termcolor import colored
from src.file_manager import DB_ROOT
from src.document_validator import DocumentValidator
from src.academic_response_processor import AcademicResponseProcessor
from src.file_processor import FileProcessor, ChunkingConfig, BatchInserter

# Constants
DEFAULT_MODEL = "gpt-4o-mini"
SUPPORTED_MODELS = ["gpt-4o-mini", "gpt-4o", "o1-mini", "o1"]
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50
SUPPORTED_MODES = ["naive", "local", "global", "hybrid", "mix"]
MAX_WORKERS = 4  # Maximum number of parallel workers for file processing

# Configure logging
logging.basicConfig(
    filename="lightrag.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class LightRAGManager:
    """Manager class for LightRAG initialization and configuration"""

    def __init__(
        self,
        api_key: str,
        input_dir: str,
        model_name: str = DEFAULT_MODEL,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        temperature: float = 0.0,
        chunk_strategy: str = "sentence"
    ):
        """Initialize LightRAG with enhanced configuration"""
        print(colored("Initializing LightRAG...", "cyan"))
        
        self.input_dir = input_dir
        self.model_name = model_name
        self.chunking_config = ChunkingConfig(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            chunk_strategy=chunk_strategy
        )
        
        # Initialize components
        self.validator = DocumentValidator(input_dir)
        self.file_processor = FileProcessor(input_dir, self.chunking_config)
        self.response_processor = AcademicResponseProcessor()
        
        # Configure LightRAG
        self._configure_rag(api_key, temperature)
        logger.info("LightRAG manager initialized successfully")

    def _configure_rag(self, api_key: str, temperature: float) -> None:
        """Configure LightRAG with model and embedding settings"""
        os.environ["OPENAI_API_KEY"] = api_key
        
        # Select model function based on model name
        if self.model_name == "gpt-4o":
            llm_func = gpt_4o_complete
        else:
            llm_func = gpt_4o_mini_complete
            
        # Initialize RAG with configuration
        self.rag = LightRAG(
            working_dir=self.input_dir,
            llm_model_func=llm_func,
            embedding_func=EmbeddingFunc(
                embedding_dim=1536,  # OpenAI embedding dimension
                max_token_size=8192,
                func=openai_embedding
            )
        )
        
        # Store temperature for use in queries
        self.temperature = temperature

    def load_documents(self, file_paths: Optional[List[str]] = None) -> None:
        """Load and index documents following LightRAG's documentation"""
        try:
            print(colored("\nIndexing documents...", "cyan"))
            
            # Get files to process
            if file_paths is None:
                store_validation = self.validator.validate_store(self.input_dir)
                file_paths = store_validation.get('valid_files', [])
                
                if store_validation.get('errors'):
                    for error in store_validation['errors']:
                        logger.warning(error)
            else:
                # Validate provided files
                validation_results = self.validator.validate_files(file_paths)
                file_paths = validation_results.get('valid_files', [])
                
                if validation_results.get('errors'):
                    for error in validation_results['errors']:
                        logger.warning(error)
            
            if not file_paths:
                raise Exception("No valid documents found to load")
            
            # Process and index documents
            total = len(file_paths)
            print(colored(f"\nProcessing and indexing {total} documents...", "cyan"))
            
            for idx, file_path in enumerate(file_paths, 1):
                try:
                    # Read and validate content
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    is_valid, error = self.validator.validate_content(content)
                    if not is_valid:
                        logger.warning(f"Skipping {file_path}: {error}")
                        continue
                    
                    # Add source information
                    file_info = f"[Source: {os.path.basename(file_path)}]\n\n"
                    content_with_source = file_info + content
                    
                    # Insert into LightRAG with progress indicator
                    print(f"\rProcessing document {idx}/{total}: {os.path.basename(file_path)}", end='')
                    self.rag.insert(content_with_source)
                    
                except Exception as e:
                    print(colored(f"\n✗ Error processing {file_path}: {str(e)}", "red"))
                    logger.error(f"Error processing {file_path}: {str(e)}")
                    continue
            
            print(colored("\n\nIndexing complete! ✓", "green"))
            print(f"Successfully processed and indexed {total} files")
                    
        except Exception as e:
            logger.error(f"Error loading documents: {str(e)}")
            print(colored(f"\nError loading documents: {str(e)}", "red"))
            raise

    def query(
        self,
        query: str,
        mode: str = "hybrid",
        only_context: bool = False,
        temperature: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Enhanced query processing with academic formatting"""
        try:
            # Convert mode to lowercase first
            mode = str(mode).lower()
            
            # Then check if it's supported
            if mode not in SUPPORTED_MODES:
                raise ValueError(f"Unsupported mode: {mode}. Use one of {SUPPORTED_MODES}")
            
            # Create query parameters according to LightRAG's QueryParam spec
            param_kwargs = {}
            
            # Handle temperature setting through llm_model_kwargs
            if temperature is not None:
                param_kwargs["llm_model_kwargs"] = {"temperature": temperature}
            elif self.temperature != 0.0:
                param_kwargs["llm_model_kwargs"] = {"temperature": self.temperature}
            
            # Add any additional kwargs that match QueryParam's parameters
            valid_param_keys = [
                "top_k", 
                "max_token_for_text_unit",
                "max_token_for_global_context", 
                "max_token_for_local_context",
                "response_type"
            ]
            for key in valid_param_keys:
                if key in kwargs:
                    param_kwargs[key] = kwargs[key]
            
            # Create query parameters
            param = QueryParam(
                mode=mode,
                only_need_context=only_context,
                **param_kwargs
            )
            
            # Process query - LightRAG returns a string
            response = self.rag.query(query, param=param)
            
            # Process response for academic formatting if needed
            if not only_context:
                response = self.response_processor.process_response(response)
            
            # Return response in our standard format
            return {
                "response": response,
                "mode": mode,
                "timestamp": datetime.now().isoformat(),
                "model": self.model_name,
                "temperature": temperature if temperature is not None else self.temperature
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            print(colored(f"Error processing query: {str(e)}", "red"))
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the loaded documents and index"""
        try:
            return {
                "total_documents": len(self.file_processor.metadata["files"]),
                "last_updated": self.file_processor.metadata["last_updated"],
                "model": self.model_name,
                "chunk_config": self.chunking_config.__dict__,
                "store_size": self._get_store_size()
            }
        except Exception as e:
            logger.error(f"Error getting stats: {str(e)}")
            return {"error": str(e)}

    def _get_store_size(self) -> int:
        """Calculate total size of stored documents"""
        total_size = 0
        for file_info in self.file_processor.metadata["files"].values():
            total_size += file_info.get("size", 0)
        return total_size
