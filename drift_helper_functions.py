import os
from typing import List, Dict, Any, Tuple
import networkx as nx
from termcolor import colored
import logging
from datetime import datetime
import json
import numpy as np
from graphrag import GraphRAG
from graphrag.query import DriftSearch

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def initialize_drift_search(graph_rag: GraphRAG) -> DriftSearch:
    """
    Initialize the DriftSearch object with the given GraphRAG.

    Args:
        graph_rag (GraphRAG): The GraphRAG object to use for drift search

    Returns:
        DriftSearch: Initialized DriftSearch object
    """
    try:
        drift_search = DriftSearch(graph_rag)
        logging.info(colored("DriftSearch initialized successfully", "green"))
        return drift_search
    except Exception as e:
        logging.error(colored(f"Error initializing DriftSearch: {str(e)}", "red"))
        raise


def perform_drift_search(
    drift_search: DriftSearch,
    query_text: str,
    num_results: int = 5,
    drift_steps: int = 2,
    temperature: float = 0.7,
) -> List[Dict[str, Any]]:
    """
    Perform drift search on the graph using the provided query.

    Args:
        drift_search (DriftSearch): Initialized DriftSearch object
        query_text (str): The query text to search for
        num_results (int): Number of results to return
        drift_steps (int): Number of drift steps to take
        temperature (float): Temperature parameter for controlling randomness

    Returns:
        List[Dict[str, Any]]: List of search results with their metadata
    """
    try:
        results = drift_search.search(
            query=query_text,
            n_results=num_results,
            n_drift_steps=drift_steps,
            temperature=temperature,
        )

        formatted_results = []
        for result in results:
            formatted_result = {
                "content": result.content,
                "score": result.score,
                "metadata": result.metadata,
                "drift_path": result.drift_path,
            }
            formatted_results.append(formatted_result)

        logging.info(
            colored(f"Found {len(formatted_results)} drift search results", "green")
        )
        return formatted_results
    except Exception as e:
        logging.error(colored(f"Error in drift search: {str(e)}", "red"))
        raise


def analyze_drift_patterns(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze the drift patterns in the search results.

    Args:
        results (List[Dict[str, Any]]): List of drift search results

    Returns:
        Dict[str, Any]: Analysis of drift patterns
    """
    try:
        pattern_analysis = {
            "avg_score": np.mean([r["score"] for r in results]),
            "max_score": max([r["score"] for r in results]),
            "min_score": min([r["score"] for r in results]),
            "unique_paths": len(set([tuple(r["drift_path"]) for r in results])),
            "path_lengths": [len(r["drift_path"]) for r in results],
        }

        logging.info(colored("Drift pattern analysis completed", "green"))
        return pattern_analysis
    except Exception as e:
        logging.error(colored(f"Error analyzing drift patterns: {str(e)}", "red"))
        raise


def visualize_drift_path(drift_path: List[str], graph_rag: GraphRAG) -> nx.Graph:
    """
    Create a visualization of the drift path.

    Args:
        drift_path (List[str]): List of node IDs in the drift path
        graph_rag (GraphRAG): The GraphRAG object containing the graph

    Returns:
        nx.Graph: NetworkX graph object for visualization
    """
    try:
        # Create a subgraph of the drift path
        path_graph = nx.Graph()

        for i in range(len(drift_path) - 1):
            current_node = drift_path[i]
            next_node = drift_path[i + 1]

            # Add nodes with their attributes
            path_graph.add_node(
                current_node, **graph_rag.get_node_attributes(current_node)
            )
            path_graph.add_node(next_node, **graph_rag.get_node_attributes(next_node))

            # Add edge between consecutive nodes
            path_graph.add_edge(current_node, next_node)

        logging.info(colored("Drift path visualization created", "green"))
        return path_graph
    except Exception as e:
        logging.error(colored(f"Error visualizing drift path: {str(e)}", "red"))
        raise
