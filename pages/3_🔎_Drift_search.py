import streamlit as st
import networkx as nx
import plotly.graph_objects as go
from termcolor import colored
import logging
from typing import List, Dict, Any
import os
import sys

# Add the root directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from drift_helper_functions import (
    initialize_drift_search,
    perform_drift_search,
    analyze_drift_patterns,
    visualize_drift_path,
)
from global_helper_functions import load_graph_rag

# Page configuration
st.set_page_config(page_title="Drift Search", page_icon="🔎", layout="wide")

# Title and description
st.title("🔎 Drift Search")
st.markdown("""
This page implements drift search functionality using Microsoft's GraphRAG.
Drift search allows for exploring semantic connections between concepts by 'drifting'
through the knowledge graph, discovering related but not directly connected information.
""")


def create_network_graph(graph: nx.Graph) -> go.Figure:
    """Create a Plotly figure for network visualization."""
    pos = nx.spring_layout(graph)

    edge_trace = go.Scatter(
        x=[], y=[], line=dict(width=0.5, color="#888"), hoverinfo="none", mode="lines"
    )

    node_trace = go.Scatter(
        x=[],
        y=[],
        mode="markers+text",
        hoverinfo="text",
        marker=dict(
            showscale=True,
            colorscale="YlGnBu",
            size=10,
        ),
        text=[],
        textposition="top center",
    )

    for edge in graph.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_trace["x"] += (x0, x1, None)
        edge_trace["y"] += (y0, y1, None)

    for node in graph.nodes():
        x, y = pos[node]
        node_trace["x"] += (x,)
        node_trace["y"] += (y,)
        node_trace["text"] += (str(node),)

    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            showlegend=False,
            hovermode="closest",
            margin=dict(b=0, l=0, r=0, t=0),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        ),
    )
    return fig


def main():
    try:
        # Load GraphRAG
        graph_rag = load_graph_rag()
        if graph_rag is None:
            st.error("Failed to load GraphRAG. Please check your configuration.")
            return

        # Initialize DriftSearch
        drift_search = initialize_drift_search(graph_rag)

        # Search parameters
        with st.sidebar:
            st.header("Search Parameters")
            query = st.text_area("Enter your query:", height=100)
            num_results = st.slider(
                "Number of results:", min_value=1, max_value=20, value=5
            )
            drift_steps = st.slider(
                "Number of drift steps:", min_value=1, max_value=5, value=2
            )
            temperature = st.slider(
                "Temperature:", min_value=0.0, max_value=1.0, value=0.7, step=0.1
            )

        # Search button
        if st.button("Perform Drift Search", type="primary"):
            if not query:
                st.warning("Please enter a query.")
                return

            with st.spinner("Performing drift search..."):
                # Perform search
                results = perform_drift_search(
                    drift_search, query, num_results, drift_steps, temperature
                )

                # Analyze patterns
                patterns = analyze_drift_patterns(results)

                # Display results
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.subheader("Search Results")
                    for idx, result in enumerate(results, 1):
                        with st.expander(
                            f"Result {idx} (Score: {result['score']:.4f})"
                        ):
                            st.markdown(result["content"])
                            st.markdown("**Drift Path:**")
                            st.write(" → ".join(result["drift_path"]))

                            # Visualize drift path
                            path_graph = visualize_drift_path(
                                result["drift_path"], graph_rag
                            )
                            fig = create_network_graph(path_graph)
                            st.plotly_chart(fig, use_container_width=True)

                with col2:
                    st.subheader("Pattern Analysis")
                    st.metric("Average Score", f"{patterns['avg_score']:.4f}")
                    st.metric("Maximum Score", f"{patterns['max_score']:.4f}")
                    st.metric("Minimum Score", f"{patterns['min_score']:.4f}")
                    st.metric("Unique Paths", patterns["unique_paths"])
                    st.metric(
                        "Average Path Length",
                        f"{sum(patterns['path_lengths']) / len(patterns['path_lengths']):.1f}",
                    )

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        logging.error(colored(f"Error in Drift Search page: {str(e)}", "red"))


if __name__ == "__main__":
    main()
