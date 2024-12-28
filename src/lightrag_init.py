import logging
import os
from typing import Optional, Dict, Any
from datetime import datetime
import time

from lightrag import LightRAG, QueryParam
from lightrag.llm import gpt_4o_complete, gpt_4o_mini_complete, openai_embedding
from lightrag.utils import EmbeddingFunc
from termcolor import colored
from src.file_manager import DB_ROOT
from src.document_validator import DocumentValidator

# Configure logging
logging.basicConfig(
    filename="lightrag.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Define major constants
DEFAULT_MODEL = "gpt-4o-mini"
SUPPORTED_MODELS = ["gpt-4o-mini", "gpt-4o", "o1-mini", "o1"]
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50


class LightRAGManager:
    """Manager class for LightRAG initialization and configuration"""

    def __init__(
        self,
        api_key: str,
        input_dir: str,
        model_name: str = DEFAULT_MODEL,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ):
        """Initialize LightRAG with configuration parameters"""
        try:
            self.api_key = api_key
            self.input_dir = input_dir
            self.model_name = model_name
            self.chunk_size = chunk_size
            self.chunk_overlap = chunk_overlap

            print(colored(f"Initializing LightRAG with {model_name}...", "cyan"))

            # Initialize LightRAG with OpenAI configuration
            llm_func = (
                gpt_4o_mini_complete if model_name == "gpt-4o-mini" else gpt_4o_complete
            )

            # Initialize LightRAG with full path
            full_working_dir = os.path.join(DB_ROOT, self.input_dir)
            logger.info(f"Working directory: {full_working_dir}")
            
            # Create directory if it doesn't exist
            os.makedirs(full_working_dir, exist_ok=True)

            # Initialize validator (working_dir doesn't matter since we use DB_ROOT directly)
            self.validator = DocumentValidator(working_dir=full_working_dir)

            # Initialize LightRAG after validator
            self.rag = LightRAG(
                working_dir=full_working_dir,
                llm_model_func=llm_func,
                llm_model_kwargs={
                    "api_key": self.api_key,
                },
                embedding_func=EmbeddingFunc(
                    embedding_dim=1536,
                    max_token_size=8192,
                    func=lambda texts: openai_embedding(
                        texts=texts,
                        api_key=self.api_key,
                    ),
                ),
            )

            print(colored("LightRAG initialization successful!", "green"))

        except Exception as e:
            error_msg = f"Error initializing LightRAG: {str(e)}"
            print(colored(error_msg, "red"))
            logger.error(error_msg)
            raise

    def load_documents(self) -> None:
        """Load documents from input directory"""
        try:
            print(colored("Loading documents...", "cyan"))
            
            # Construct full path using DB_ROOT
            full_input_dir = os.path.join(DB_ROOT, self.input_dir)
            logger.info(f"Loading documents from: {full_input_dir}")
            
            # Check if directory exists
            if not os.path.exists(full_input_dir):
                raise FileNotFoundError(f"Directory not found: {full_input_dir}")

            # Validate store first
            validation_results = self.validator.validate_store(self.input_dir)
            
            if validation_results['errors']:
                for error in validation_results['errors']:
                    logger.warning(f"Validation error: {error}")
                    print(colored(f"Warning: {error}", "yellow"))
                    
            if not validation_results['valid_files']:
                raise Exception("No valid documents found to load")
                
            # Load only valid files
            loaded_files = []
            total_size = 0
            
            for file_path in validation_results['valid_files']:
                try:
                    logger.info(f"Processing file: {file_path}")
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        is_valid, error = self.validator.validate_content(content)
                        
                        if is_valid:
                            # Add debug logging for content
                            logger.debug(f"Content length: {len(content)} characters")
                            logger.debug(f"Content preview: {content[:200]}...")
                            
                            # Insert with error handling
                            try:
                                self.rag.insert(content)
                                loaded_files.append(os.path.basename(file_path))
                                total_size += len(content)
                                logger.info(f"Successfully inserted content from: {file_path}")
                            except Exception as e:
                                logger.error(f"Error inserting content from {file_path}: {str(e)}")
                                raise
                        else:
                            logger.error(f"Invalid content in {file_path}: {error}")
                            raise ValueError(f"Invalid content in {file_path}: {error}")
                            
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {str(e)}")
                    raise

            # Log successful loading
            if loaded_files:
                print(colored("Documents loaded successfully!", "green"))
                print("Loaded", len(loaded_files), "files:")
                for file in loaded_files:
                    print(f"- {file}")
                print(f"Total content size: {total_size/1024:.2f}KB")
                
                # Verify after loading
                if not self.verify_documents():
                    raise Exception("Document verification failed after loading")
                
            else:
                raise Exception("No documents were loaded")

        except Exception as e:
            error_msg = f"Error loading documents: {str(e)}"
            print(colored(error_msg, "red"))
            logger.error(error_msg)
            raise

    def query(self, query_text: str, mode: str = "hybrid", **kwargs) -> dict:
        """Execute query using LightRAG"""
        try:
            logger.info(f"Processing query in {mode} mode: {query_text}")
            
            # Create basic QueryParam - only pass mode as it's the only guaranteed parameter
            param = QueryParam(mode=mode)
            
            # Execute query
            result = self.rag.query(query_text, param=param)
            
            # Process result - it might be a string or dict
            if isinstance(result, dict):
                response_text = result.get('response', str(result))
                sources = result.get('sources', [])
            else:
                response_text = str(result)
                sources = []
            
            return {
                "response": response_text,
                "mode": mode,
                "sources": sources,
                "time": datetime.now().isoformat(),
                "token_usage": None,
            }

        except Exception as e:
            logger.error(f"Query failed in {mode} mode: {str(e)}")
            raise

    def get_relevant_sources(self, query_result: dict) -> list:
        """Extract relevant sources from query result"""
        try:
            # Extract sources from the query result
            sources = query_result.get("sources", [])
            return sources
        except Exception as e:
            error_msg = f"Error retrieving sources: {str(e)}"
            print(colored(error_msg, "red"))
            logger.error(error_msg)
            raise

    def verify_documents(self, max_retries: int = 3, delay: float = 1.0) -> bool:
        """Verify documents were loaded correctly with retries"""
        for attempt in range(max_retries):
            try:
                logger.info(f"Verification attempt {attempt + 1} of {max_retries}")
                
                test_query = "Give me a one word response if you can access the document: YES or NO"
                param = QueryParam(mode="naive")
                
                test_response = self.rag.query(test_query, param=param)
                logger.info(f"Verification response: {test_response}")
                
                if test_response:
                    if isinstance(test_response, str):
                        positive_indicators = ['yes', 'true', 'accessible', 'available', 'loaded']
                        response_lower = test_response.lower()
                        is_positive = any(indicator in response_lower for indicator in positive_indicators)
                        
                        if is_positive:
                            logger.info("Document verification successful!")
                            print(colored("Document verification successful!", "green"))
                            return True
                
                logger.warning(f"Verification attempt {attempt + 1} failed")
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    continue
                    
            except Exception as e:
                logger.error(f"Error during verification attempt {attempt + 1}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    continue
                else:
                    raise
        
        print(colored("Document verification failed - no content accessible", "red"))
        logger.error("All verification attempts failed")
        return False

    def _query_with_fallback(self, query_text: str, param: QueryParam) -> dict:
        """Fallback logic for query execution"""
        logger.info("Starting fallback query process")
        
        modes = ["naive", "local", "global", "hybrid"]
        for mode in modes:
            try:
                logger.info(f"Attempting {mode} mode for query: {query_text}")
                param.mode = mode
                result = self.rag.query(query_text, param=param)
                logger.debug(f"Raw result from {mode} mode: {result}")
                
                if isinstance(result, dict) and result.get('response'):
                    logger.info(f"Successful response from {mode} mode")
                    return self._format_response(result, mode)
                else:
                    logger.warning(f"{mode} mode returned invalid response format")
                    
            except Exception as e:
                logger.error(f"Error in {mode} mode: {str(e)}", exc_info=True)
                continue
        
        # If all modes fail, try hybrid one last time
        logger.warning("All modes failed, final hybrid attempt")
        try:
            param.mode = "hybrid"
            result = self.rag.query(query_text, param=param)
            return self._format_response(result, "hybrid")
        except Exception as e:
            logger.error("Final hybrid attempt failed", exc_info=True)
            raise

    def _format_response(self, result: Any, mode: str) -> dict:
        """Format query result into standard response"""
        logger.debug(f"Formatting response for mode {mode}")
        try:
            if isinstance(result, dict):
                formatted = {
                    "response": result.get('response', ''),
                    "mode": mode,
                    "sources": result.get('sources', []),
                    "time": datetime.now().isoformat(),
                    "token_usage": None,
                }
            else:
                formatted = {
                    "response": str(result),
                    "mode": mode,
                    "sources": [],
                    "time": datetime.now().isoformat(),
                    "token_usage": None,
                }
            logger.debug(f"Formatted response: {formatted}")
            return formatted
        except Exception as e:
            logger.error(f"Error formatting response: {str(e)}", exc_info=True)
            raise
