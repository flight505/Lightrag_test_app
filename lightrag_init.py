import logging
import os
from typing import Optional

from lightrag import LightRAG
from lightrag.embeddings import OpenAIEmbeddings
from lightrag.llm import gpt_4o_mini_complete
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

            # Initialize embeddings
            self.embeddings = OpenAIEmbeddings(api_key=self.api_key)

            print(colored(f"Initializing LightRAG with {model_name}...", "cyan"))

            # Initialize LightRAG
            self.rag = LightRAG(
                llm=gpt_4o_mini_complete,
                embeddings=self.embeddings,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
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
            self.rag.load_dir(self.input_dir)
            print(colored("Documents loaded successfully!", "green"))

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

            # Execute query
            response = self.rag.query(formatted_query)

            print(colored("Query processed successfully!", "green"))
            return response

        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            print(colored(error_msg, "red"))
            logger.error(error_msg)
            raise

    def get_relevant_sources(self, query_result: dict) -> list:
        """Extract relevant sources from query result"""
        try:
            return self.rag.get_sources(query_result)
        except Exception as e:
            error_msg = f"Error retrieving sources: {str(e)}"
            print(colored(error_msg, "red"))
            logger.error(error_msg)
            raise
