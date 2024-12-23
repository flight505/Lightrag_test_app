import logging
import os
from typing import Optional
from datetime import datetime

from lightrag import LightRAG, QueryParam
from lightrag.llm import gpt_4o_complete, gpt_4o_mini_complete, openai_embedding
from lightrag.utils import EmbeddingFunc
from termcolor import colored
from src.file_manager import DB_ROOT

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
            
            # Create directory if it doesn't exist
            os.makedirs(full_working_dir, exist_ok=True)

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
            print(colored(f"Looking for files in: {full_input_dir}", "cyan"))  # Debug line

            # Check if directory exists
            if not os.path.exists(full_input_dir):
                raise FileNotFoundError(f"Directory not found: {full_input_dir}")

            # Track loaded documents
            loaded_files = []
            total_size = 0

            # Walk through the directory and load all text files
            for root, _, files in os.walk(full_input_dir):
                txt_files = [f for f in files if f.endswith(".txt")]
                print(colored(f"Found text files: {txt_files}", "cyan"))  # Debug line

                if not txt_files:
                    continue

                for file in txt_files:
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            size = len(content)
                            if size > 0:
                                self.rag.insert(content)
                                loaded_files.append(file)
                                total_size += size
                                print(colored(f"Successfully loaded: {file_path}", "green"))  # Debug line
                    except Exception as e:
                        print(colored(f"Error loading file {file_path}: {str(e)}", "red"))

            # Provide feedback about loaded documents
            if loaded_files:
                print(colored("Documents loaded successfully!", "green"))
                print(colored(f"Loaded {len(loaded_files)} files:", "cyan"))
                for file in loaded_files:
                    print(colored(f"- {file}", "cyan"))
                print(colored(f"Total content size: {total_size/1024:.2f}KB", "cyan"))

                # Verify documents were loaded correctly
                if not self.verify_documents():
                    raise Exception("Document verification failed")
            else:
                warning_msg = (
                    f"No text files found in {full_input_dir}. "  # Updated to show full path
                    "Please make sure your documents are in .txt format."
                )
                print(colored(warning_msg, "yellow"))
                logger.warning(warning_msg)

        except Exception as e:
            error_msg = f"Error loading documents: {str(e)}"
            print(colored(error_msg, "red"))
            logger.error(error_msg)
            raise

    def query(self, query_text: str, response_type: Optional[str] = None) -> dict:
        """Execute query using LightRAG"""
        try:
            logger.info(f"Processing query: {query_text}")
            print(colored("Processing query...", "cyan"))

            # Add response type to query if specified
            if response_type:
                formatted_query = f"Please provide a response in {response_type} format: {query_text}"
            else:
                formatted_query = query_text
            
            logger.debug(f"Formatted query: {formatted_query}")

            # Execute query with different modes
            modes = ["naive", "local", "global", "hybrid"]
            
            for mode in modes:
                try:
                    logger.info(f"Trying {mode} mode...")
                    print(colored(f"Trying {mode} mode...", "cyan"))
                    
                    result = self.rag.query(
                        formatted_query,
                        param=QueryParam(
                            mode=mode,
                            only_need_context=False,
                        ),
                    )
                    
                    logger.debug(f"Raw result from {mode} mode: {result}")
                    
                    # Check if we got a valid response
                    if isinstance(result, dict) and result.get('response'):
                        logger.info(f"{mode} mode successful")
                        print(colored(f"{mode} mode successful!", "green"))
                        return {
                            "response": result['response'],
                            "mode": mode,
                            "sources": result.get('sources', []),
                            "time": datetime.now().isoformat(),
                            "token_usage": None,
                        }
                    elif isinstance(result, str) and not result.startswith("Sorry"):
                        logger.info(f"{mode} mode successful (string response)")
                        print(colored(f"{mode} mode successful!", "green"))
                        return {
                            "response": result,
                            "mode": mode,
                            "sources": [],
                            "time": datetime.now().isoformat(),
                            "token_usage": None,
                        }

                except Exception as mode_error:
                    logger.warning(f"Error in {mode} mode: {str(mode_error)}")
                    print(colored(f"Error in {mode} mode: {str(mode_error)}", "yellow"))
                    continue

            # If no mode was successful, try hybrid mode one last time
            logger.info("Falling back to hybrid mode...")
            print(colored("Falling back to hybrid mode...", "yellow"))
            
            result = self.rag.query(
                formatted_query,
                param=QueryParam(mode="hybrid"),
            )
            
            logger.debug(f"Final hybrid mode result: {result}")

            # Format the final response
            if isinstance(result, dict):
                return {
                    "response": result.get('response', ''),
                    "mode": "hybrid",
                    "sources": result.get('sources', []),
                    "time": datetime.now().isoformat(),
                    "token_usage": None,
                }
            else:
                return {
                    "response": str(result),
                    "mode": "hybrid",
                    "sources": [],
                    "time": datetime.now().isoformat(),
                    "token_usage": None,
                }

        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            logger.error(error_msg, exc_info=True)
            print(colored(error_msg, "red"))
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

    def verify_documents(self) -> bool:
        """Verify documents were loaded correctly"""
        try:
            # Try a simple test query
            test_response = self.rag.query(
                "Give me a one word response if you can access the document: YES or NO",
                param=QueryParam(mode="naive"),
            )

            if test_response and "YES" in test_response.upper():
                print(colored("Document verification successful!", "green"))
                return True
            else:
                print(
                    colored(
                        "Document verification failed - no content accessible", "red"
                    )
                )
                return False

        except Exception as e:
            error_msg = f"Error verifying documents: {str(e)}"
            print(colored(error_msg, "red"))
            logger.error(error_msg)
            return False
