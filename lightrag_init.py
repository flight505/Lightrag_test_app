import logging
import os
from typing import Optional

from lightrag import LightRAG, QueryParam
from lightrag.llm import gpt_4o_complete, gpt_4o_mini_complete, openai_embedding
from lightrag.utils import EmbeddingFunc
from termcolor import colored

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

            self.rag = LightRAG(
                working_dir=self.input_dir,
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

            # Check if directory exists
            if not os.path.exists(self.input_dir):
                raise FileNotFoundError(f"Directory not found: {self.input_dir}")

            # Track loaded documents
            loaded_files = []
            total_size = 0

            # Walk through the directory and load all text files
            for root, _, files in os.walk(self.input_dir):
                txt_files = [f for f in files if f.endswith(".txt")]

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
                    except Exception as e:
                        print(colored(f"Error loading file {file}: {str(e)}", "red"))

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
                    f"No text files found in {self.input_dir}. "
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
            print(colored("Processing query...", "cyan"))

            # Add response type to query if specified
            if response_type:
                formatted_query = (
                    f"Please provide a response in {response_type} format: {query_text}"
                )
            else:
                formatted_query = query_text

            # Execute query with different modes
            modes = ["naive", "local", "global", "hybrid"]
            responses = {}

            for mode in modes:
                try:
                    print(colored(f"Trying {mode} mode...", "cyan"))
                    response = self.rag.query(
                        formatted_query,
                        param=QueryParam(
                            mode=mode,
                            only_need_context=False,
                        ),
                    )
                    if response and not response.startswith("Sorry"):
                        # Format successful response
                        formatted_response = {
                            "response": response,
                            "mode": mode,
                            "sources": self.rag.get_context(),  # Get context/sources
                            "time": None,
                            "token_usage": None,
                        }
                        print(colored(f"{mode} mode successful!", "green"))
                        return formatted_response

                except Exception as mode_error:
                    print(colored(f"Error in {mode} mode: {str(mode_error)}", "yellow"))
                    continue

            # If no mode was successful, return the hybrid mode response
            print(colored("Falling back to hybrid mode...", "yellow"))
            response = self.rag.query(
                formatted_query,
                param=QueryParam(mode="hybrid"),
            )

            formatted_response = {
                "response": response,
                "mode": "hybrid",
                "sources": self.rag.get_context(),
                "time": None,
                "token_usage": None,
            }

            print(colored("Query processed successfully!", "green"))
            return formatted_response

        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            print(colored(error_msg, "red"))
            logger.error(error_msg)
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
