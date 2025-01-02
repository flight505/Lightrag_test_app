import asyncio
import json
import logging
import os
import pickle
import time
from datetime import datetime
from io import BytesIO
from typing import Dict, List
from pathlib import Path

import streamlit as st
from docx import Document
import networkx as nx
import xxhash

from lightrag import QueryParam
from src.lightrag_helpers import ResponseProcessor
from src.lightrag_init import DEFAULT_MODEL, SUPPORTED_MODELS, LightRAGManager
from src.file_manager import create_store_directory, DB_ROOT
from src.file_processor import FileProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
file_handler = logging.FileHandler('chat.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Initialize session states
if "rag_manager" not in st.session_state:
    st.session_state["rag_manager"] = None
if "response_processor" not in st.session_state:
    st.session_state["response_processor"] = ResponseProcessor()
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "conversation_context" not in st.session_state:
    st.session_state["conversation_context"] = []
if "max_context_length" not in st.session_state:
    st.session_state["max_context_length"] = 5
if "chat_settings" not in st.session_state:
    st.session_state["chat_settings"] = {
        "memory_enabled": True,
        "context_length": 5,
        "summarize_enabled": True,
    }
if "status_ready" not in st.session_state:
    st.session_state["status_ready"] = False
if "active_store" not in st.session_state:
    st.session_state["active_store"] = None
if "api_key_shown" not in st.session_state:
    st.session_state["api_key_shown"] = False

# Helper functions
def manage_conversation_context(query: str, response: str):
    """Manage conversation context by adding new exchanges and maintaining context length"""
    if st.session_state["chat_settings"]["memory_enabled"]:
        st.session_state["conversation_context"].append(
            {"query": query, "response": response}
        )
        # Trim context if it exceeds max length
        if (
            len(st.session_state["conversation_context"])
            > st.session_state["max_context_length"]
        ):
            st.session_state["conversation_context"].pop(0)


def get_conversation_context() -> str:
    """Format conversation context for the LLM"""
    if not st.session_state["chat_settings"]["memory_enabled"]:
        return ""

    context = "Previous conversation:\n"
    for exchange in st.session_state["conversation_context"]:
        context += f"User: {exchange['query']}\nAssistant: {exchange['response']}\n\n"
    return context


def export_chat_history(chat_history: List[Dict]) -> str:
    """Export chat history to formatted text"""
    formatted_history = []
    for message in chat_history:
        role = message["role"].capitalize()
        content = message["content"]
        formatted_history.append(f"{role}: {content}\n")
    return "\n".join(formatted_history)


def clear_chat_history():
    """Clear chat history and reset session states"""
    st.session_state["chat_history"] = []
    st.session_state["conversation_context"] = []


def should_summarize_conversation() -> bool:
    """Check if conversation should be summarized based on settings and length"""
    if not st.session_state["chat_settings"]["summarize_enabled"]:
        return False

    # Check if conversation is long enough to warrant summarization
    message_count = len(st.session_state["chat_history"])
    return message_count > st.session_state["max_context_length"] * 2


async def summarize_conversation() -> str:
    """Summarize the current conversation using LightRAG"""
    try:
        # Prepare conversation for summarization
        conversation_text = export_chat_history(st.session_state["chat_history"])

        # Create summarization prompt
        summary_prompt = (
            "Please provide a concise summary of the following conversation, "
            "highlighting the main topics discussed and key conclusions:\n\n"
            f"{conversation_text}"
        )

        # Get summary using LightRAG
        result = st.session_state["rag_manager"].query(summary_prompt)
        return result["response"]

    except Exception as e:
        st.error(f"Error summarizing conversation: {str(e)}")
        return "Error generating summary"


def update_conversation_with_summary(summary: str):
    """Update conversation history with summary and reset context"""
    try:
        # Create summary message
        summary_message = {
            "role": "assistant",
            "content": (
                "**Conversation Summary:**\n\n"
                f"{summary}\n\n"
                "---\n"
                "*Previous messages have been summarized. Continuing conversation...*"
            ),
        }

        # Keep recent messages
        recent_messages = st.session_state["chat_history"][
            -st.session_state["max_context_length"] :
        ]

        # Update chat history with summary and recent messages
        st.session_state["chat_history"] = [summary_message] + recent_messages

        # Update conversation context
        st.session_state["conversation_context"] = []
        for msg in recent_messages:
            if msg["role"] == "assistant":
                manage_conversation_context(
                    recent_messages[recent_messages.index(msg) - 1]["content"],
                    msg["content"],
                )

    except Exception as e:
        st.error(f"Error updating conversation with summary: {str(e)}")


def check_lightrag_ready() -> tuple[bool, str]:
    """
    Check if LightRAG is properly initialized and ready for queries
    Returns: (is_ready, message)
    """
    if st.session_state["rag_manager"] is None:
        return False, "LightRAG not initialized. Click 'Initialize Chat'"
        
    if not st.session_state["status_ready"]:
        return False, "Documents not indexed. Click 'Initialize Chat'"
        
    if not st.session_state["active_store"]:
        return False, "No store selected. Please select a store in the sidebar"
        
    return True, "Ready"

# Page configuration
st.set_page_config(
    page_title="LightRAG Chat",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items=None  # This hides the burger menu
)

# Navigation menu
nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 1])
with nav_col1:
    if st.button("🏠 Home", use_container_width=True):
        st.switch_page("streamlit_app.py")
with nav_col2:
    if st.button("💬 Chat", use_container_width=True, type="primary"):
        st.switch_page("pages/Search.py")
with nav_col3:
    if st.button("📁 Manage Documents", use_container_width=True):
        st.switch_page("pages/Manage.py")

st.divider()

# Main interface
st.write("## 💬 LightRAG Chat")

# Store selection in main content
store_col1, store_col2 = st.columns([3, 1])
with store_col1:
    # List existing stores
    stores = [d for d in os.listdir(DB_ROOT) if os.path.isdir(os.path.join(DB_ROOT, d))]
    
    # Store selection
    selected_store = st.selectbox(
        "Select Document Store",
        ["Create New..."] + stores,
        index=0 if st.session_state["active_store"] is None else 
              stores.index(st.session_state["active_store"]) + 1,
        help="Choose an existing document store or create a new one"
    )

with store_col2:
    if selected_store == "Create New...":
        new_store = st.text_input("Store Name")
        if st.button("Create Store", type="primary", use_container_width=True):
            if new_store:
                store_path = create_store_directory(new_store)
                if store_path:
                    st.session_state["active_store"] = new_store
                    st.session_state["file_processor"] = FileProcessor(store_path)
                    st.success(f"Created store: {new_store}")
                    st.rerun()
    else:
        store_path = os.path.join(DB_ROOT, selected_store)
        if st.session_state["active_store"] != selected_store:
            st.session_state["file_processor"] = None
            st.session_state["active_store"] = selected_store
            st.session_state["file_processor"] = FileProcessor(store_path)
            st.rerun()

st.divider()

# Create two columns for the main interface
col1, col2 = st.columns([3, 1])

with col1:
    # Chat interface
    chat_container = st.container()
    
    with chat_container:
        is_ready, status_msg = check_lightrag_ready()
        
        if not is_ready:
            st.warning(status_msg)
        else:
            # Add chat controls
            chat_controls_col1, chat_controls_col2 = st.columns([2, 1])
            with chat_controls_col1:
                if st.session_state["chat_history"]:
                    if st.button("Export Chat"):
                        chat_export = export_chat_history(st.session_state["chat_history"])
                        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                        st.download_button(
                            "Download Chat History",
                            chat_export,
                            file_name=f"LightRAG_Chat_{current_time}.txt",
                        )
            with chat_controls_col2:
                if st.session_state["chat_history"]:
                    if st.button("Clear Chat"):
                        clear_chat_history()
                        st.rerun()

            # Display chat history with enhanced formatting
            for message in st.session_state["chat_history"]:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # Chat input
            if prompt := st.chat_input("Type your message here...", key="chat_input"):
                logger.info(f"Chat input received: {prompt}")
                
                # Add user message to chat history
                st.session_state["chat_history"].append({"role": "user", "content": prompt})

                try:
                    # Get conversation context
                    context = get_conversation_context()
                    logger.debug(f"Context retrieved: {context}")

                    # Prepare query with context
                    query = f"{context}\nCurrent query: {prompt}" if context else prompt
                    logger.info(f"Prepared query: {query}")

                    # Process query with progress indicator
                    with st.status("Processing...") as status:
                        result = st.session_state["rag_manager"].query(query)
                        logger.info(f"Query result: {result}")

                        if result and result.get("response"):
                            # Format response with sources
                            formatted_response = (
                                f"{result['response']}\n\n"
                                f"*Sources:*\n"
                                f"{st.session_state['response_processor'].format_sources(result.get('sources', []))}"
                            )
                            
                            # Add assistant response to chat history
                            st.session_state["chat_history"].append({
                                "role": "assistant",
                                "content": formatted_response
                            })
                            logger.info("Response added to chat history")
                            
                            # Update conversation context
                            manage_conversation_context(query, result["response"])
                            
                            # Check if conversation should be summarized
                            if should_summarize_conversation():
                                with st.status("Summarizing conversation..."):
                                    summary = asyncio.run(summarize_conversation())
                                    update_conversation_with_summary(summary)
                            
                            # Force streamlit to rerun and show the new message
                            st.rerun()
                        else:
                            logger.error("No valid response received")
                            st.error("Failed to get a response. Please try again.")

                except Exception as e:
                    logger.error(f"Error processing chat: {str(e)}", exc_info=True)
                    st.error(f"Error processing chat: {str(e)}")

with col2:
    # Session information
    with st.expander(":material/info: **Session Info**", expanded=True):
        # Status with color and icon
        if st.session_state["status_ready"]:
            st.write("🟢 **System Status:** Ready and operational")
            if st.button("📊 View Knowledge Graph", use_container_width=True):
                st.session_state["show_graph"] = True
        else:
            st.write("🔴 **System Status:** Not initialized")
            
        st.divider()
        # System info with icons
        st.write("**Messages:**", len(st.session_state["chat_history"]))
        if st.session_state["rag_manager"]:
            st.write("**Model:**", st.session_state["rag_manager"].model_name)
            st.write("**Store:**", st.session_state["rag_manager"].input_dir)

    # Chat settings
    with st.expander("💬 Chat Settings", expanded=False):
        st.session_state["chat_settings"]["memory_enabled"] = st.toggle(
            "Enable Conversation Memory",
            value=True,
            help="Keep track of conversation context",
        )
        if st.session_state["chat_settings"]["memory_enabled"]:
            st.session_state["max_context_length"] = st.slider(
                "Context Length",
                min_value=1,
                max_value=10,
                value=5,
                help="Number of previous exchanges to remember",
            )

        st.divider()

        # Summarization settings
        st.subheader("Summarization")
        st.session_state["chat_settings"]["summarize_enabled"] = st.toggle(
            "Auto-Summarize Long Conversations",
            value=True,
            help="Automatically summarize long conversations to maintain context",
        )

        if st.session_state["chat_settings"]["summarize_enabled"]:
            st.session_state["chat_settings"]["summarize_threshold"] = st.slider(
                "Summarization Threshold",
                min_value=5,
                max_value=20,
                value=10,
                help="Number of messages before triggering auto-summarization",
            )

            if st.button("Summarize Now", type="secondary"):
                if len(st.session_state["chat_history"]) > 2:
                    with st.status("Manually summarizing conversation..."):
                        summary = asyncio.run(summarize_conversation())
                        update_conversation_with_summary(summary)
                        st.success("Conversation summarized!")
                        st.rerun()
                else:
                    st.info("Not enough conversation history to summarize.")

    # Configuration form
    with st.form("configuration_form"):
        st.markdown("**Configure your chat:**")
        
        # Get API key from environment variable first
        api_key = os.getenv("OPENAI_API_KEY", "")
        
        # Only show API key input if not in environment
        if not api_key:
            api_key = st.text_input("Your API key", type="password")
            if not api_key:
                st.warning("Please enter your OpenAI API key or set OPENAI_API_KEY environment variable")
        elif not st.session_state.get("api_key_shown"):
            st.toast("Using API key from environment variable")
            st.session_state["api_key_shown"] = True

        model = st.selectbox(
            "Select your model",
            options=SUPPORTED_MODELS,
            index=SUPPORTED_MODELS.index(DEFAULT_MODEL),
        )

        with st.expander("Advanced Settings"):
            chunk_size = st.number_input(
                "Chunk size", value=500, help="Size of text chunks for processing"
            )
            chunk_overlap = st.number_input(
                "Chunk overlap", value=50, help="Overlap between text chunks"
            )
            temperature = st.slider(
                "Temperature",
                min_value=0.0,
                max_value=1.0,
                value=0.0,
                step=0.1,
                help="Controls response creativity (0: focused, 1: creative)",
            )

        config_submitted = st.form_submit_button("Initialize Chat")

        if config_submitted:
            if not st.session_state["active_store"]:
                st.error("Please select a store first")
            elif not api_key:
                st.error("API key is required")
            else:
                try:
                    with st.spinner("Initializing LightRAG..."):
                        # Get correct store path
                        store_path = os.path.join(DB_ROOT, st.session_state["active_store"])
                        
                        # Initialize LightRAG manager with correct parameters
                        st.session_state["rag_manager"] = LightRAGManager(
                            api_key=api_key,
                            input_dir=store_path,
                            model_name=model,
                            chunk_size=chunk_size,
                            chunk_overlap=chunk_overlap,
                            temperature=temperature
                        )
                        
                        # Load documents
                        st.session_state["rag_manager"].load_documents()
                        
                        # Set status to ready
                        st.session_state["status_ready"] = True
                        
                        # Force rerun to update UI
                        st.rerun()

                except Exception as e:
                    st.error(f"Configuration error: {str(e)}")
                    logger.error(f"Configuration error: {str(e)}", exc_info=True)

# Add Knowledge Graph section at the bottom
if "show_graph" in st.session_state and st.session_state["show_graph"]:
    st.divider()
    graph_container = st.container()
    with graph_container:
        st.markdown("## 📊 Knowledge Graph Analysis")
        
        # Create three columns for the metrics
        stats_col1, stats_col2, stats_col3 = st.columns(3)
        
        try:
            if not st.session_state.active_store:
                st.warning("Please select a store first")
            else:
                store_path = os.path.join(DB_ROOT, st.session_state.active_store)
                graph_path = os.path.join(store_path, "graph_chunk_entity_relation.graphml")
                
                if not os.path.exists(graph_path):
                    st.warning("⚠️ Knowledge Graph not found. Please initialize and index documents first.")
                else:
                    graph = nx.read_graphml(graph_path)
                    
                    # Basic stats in columns
                    with stats_col1:
                        st.metric("Total Nodes", graph.number_of_nodes())
                    with stats_col2:
                        st.metric("Total Edges", graph.number_of_edges())
                    with stats_col3:
                        avg_degree = round(sum(dict(graph.degree()).values()) / graph.number_of_nodes(), 2) if graph.number_of_nodes() > 0 else 0
                        st.metric("Average Degree", avg_degree)
                    
                    # Detailed analysis in two columns
                    analysis_col1, analysis_col2 = st.columns([1, 1])
                    
                    with analysis_col1:
                        st.markdown("### Graph Analysis")
                        if graph.number_of_nodes() > 0:
                            density = nx.density(graph)
                            components = nx.number_connected_components(graph.to_undirected())
                            
                            st.markdown(f"""
                            - **Graph Density:** {density:.4f}
                            - **Connected Components:** {components}
                            """)
                    
                    with analysis_col2:
                        st.markdown("### Most Connected Nodes")
                        if graph.number_of_nodes() > 0:
                            # Create table for top nodes
                            degrees = dict(graph.degree())
                            top_nodes = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:5]
                            
                            # Display top nodes in a DataFrame
                            top_nodes_data = []
                            for node, degree in top_nodes:
                                sha_hash = xxhash.xxh64(node.encode()).hexdigest()[:12]
                                top_nodes_data.append({
                                    "Node": node,
                                    "Hash": sha_hash,
                                    "Connections": degree
                                })
                            
                            st.dataframe(
                                top_nodes_data,
                                column_config={
                                    "Node": st.column_config.TextColumn("Node ID", width="medium"),
                                    "Hash": st.column_config.TextColumn("SHA-12", width="small"),
                                    "Connections": st.column_config.NumberColumn("Connections", width="small")
                                },
                                hide_index=True
                            )
                    
                    # Visualization section
                    st.markdown("### Interactive Graph Visualization")
                    try:
                        from pyvis.network import Network
                        import random
                        
                        with st.spinner("Generating interactive network visualization..."):
                            net = Network(height="600px", width="100%", notebook=True)
                            net.from_nx(graph)
                            
                            # Apply visual styling
                            for node in net.nodes:
                                node["color"] = "#{:06x}".format(random.randint(0, 0xFFFFFF))
                            
                            # Save and display
                            html_path = os.path.join(store_path, "graph_visualization.html")
                            net.save_graph(html_path)
                            
                            # Display the saved HTML
                            with open(html_path, 'r', encoding='utf-8') as f:
                                html_content = f.read()
                            st.components.v1.html(html_content, height=600)
                                
                    except ImportError:
                        st.error("⚠️ Please install pyvis to enable graph visualization: `pip install pyvis`")
                    except Exception as e:
                        st.error(f"❌ Error generating visualization: {str(e)}")
        
        except Exception as e:
            st.error(f"❌ Error getting graph stats: {str(e)}")
            
        # Add button to hide graph
        if st.button("Hide Knowledge Graph"):
            st.session_state["show_graph"] = False
            st.rerun()
