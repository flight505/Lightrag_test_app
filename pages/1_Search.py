import asyncio
import json
import logging
import os
import pickle
import time
from datetime import datetime
from io import BytesIO
from typing import Dict, List

import streamlit as st
from docx import Document
from termcolor import colored

from src.lightrag_helpers import ResponseProcessor
from src.lightrag_init import DEFAULT_MODEL, SUPPORTED_MODELS, LightRAGManager
from src.file_manager import create_store_directory, DB_ROOT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(page_title="LightRAG Search", page_icon="🔍", layout="wide")

# Initialize session states
if "rag_manager" not in st.session_state:
    st.session_state["rag_manager"] = None
if "response_processor" not in st.session_state:
    st.session_state["response_processor"] = ResponseProcessor()
if "query_history" not in st.session_state:
    st.session_state["query_history"] = ["..."]
if "query_results" not in st.session_state:
    st.session_state["query_results"] = []
if "responses" not in st.session_state:
    st.session_state["responses"] = ["..."]
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "current_mode" not in st.session_state:
    st.session_state["current_mode"] = "Search"
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
if "response_type" not in st.session_state:
    st.session_state["response_type"] = "detailed paragraph"
if "status_ready" not in st.session_state:
    st.session_state["status_ready"] = False
if "active_store" not in st.session_state:
    st.session_state["active_store"] = None
if "api_key_shown" not in st.session_state:
    st.session_state["api_key_shown"] = False


# Helper functions
def get_docx(text: str) -> bytes:
    """Convert text to docx format"""
    document = Document()
    document.add_paragraph(text)
    byte_io = BytesIO()
    document.save(byte_io)
    return byte_io.getvalue()


async def process_query_with_progress(query: str, progress_bar) -> dict:
    """Process query with progress bar updates"""
    start_time = time.time()
    estimated_time = 20  # Estimated processing time in seconds

    # Create query task
    query_task = asyncio.create_task(
        asyncio.to_thread(
            st.session_state["rag_manager"].query,
            query,
            st.session_state["response_type"],
        )
    )

    # Update progress while processing
    while not query_task.done():
        elapsed = time.time() - start_time
        progress = min(elapsed / estimated_time * 100, 99)
        progress_bar.progress(int(progress), "Processing query...")
        await asyncio.sleep(0.1)

    # Get result and complete progress
    result = await query_task
    progress_bar.progress(100, "Complete!")
    return result


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
    st.session_state["query_history"] = ["..."]
    st.session_state["query_results"] = []
    st.session_state["responses"] = ["..."]
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
        summary_result = await process_query_with_progress(
            summary_prompt,
            st.empty(),  # Create temporary progress bar
        )

        return summary_result["response"]

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


# Sidebar configuration
with st.sidebar:
    # Mode selection
    st.radio(
        "Select Mode",
        ["Search", "Chat"],
        key="current_mode",
        help="Search: Single query mode\nChat: Interactive conversation mode",
    )

    # Separate the directory form from the configuration form
    with st.form("directory_form"):
        st.markdown("**Create and Manage Document Store:**")
        
        # List existing stores from DB directory
        if not os.path.exists(DB_ROOT):
            os.makedirs(DB_ROOT)
            st.info(f"Created root directory: {DB_ROOT}")
            
        existing_stores = [
            d for d in os.listdir(DB_ROOT) 
            if os.path.isdir(os.path.join(DB_ROOT, d))
        ]

        # Handle store selection
        if existing_stores:
            selected_store = st.selectbox("Select existing store", options=existing_stores)
            if selected_store != st.session_state["active_store"]:
                st.session_state["active_store"] = selected_store
                st.toast(f"Using store: {selected_store}")
        else:
            st.warning("No existing stores found. Please create a new store.")
            selected_store = None

        # Input for new store name
        new_store_name = st.text_input("New store name", value="")

        # Button to create or manage store
        create_store = st.form_submit_button("Create and Manage Store")
        if create_store:
            if new_store_name:
                store_path = create_store_directory(new_store_name)
                if store_path:
                    if os.path.exists(os.path.join(DB_ROOT, new_store_name)):
                        st.session_state["active_store"] = new_store_name
                        st.toast(f"Created new store: {new_store_name}")
                    else:
                        st.error("Failed to create store in DB directory")
                else:
                    st.error("Failed to create store")
            elif not selected_store:
                st.warning("Please enter a new store name or select an existing store.")

    # Configuration form
    with st.form("configuration_form"):
        st.markdown("**Configure your search:**")
        
        # Get API key from environment variable first
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            api_key = st.text_input("Your API key", type="password")
        elif not st.session_state["api_key_shown"]:
            st.toast("Using API key from environment variable")
            st.session_state["api_key_shown"] = True

        # Store validation without redundant toast
        if not st.session_state["active_store"]:
            st.warning("Please create or select a store before initializing")
            store_ready = False
        else:
            store_ready = True
            active_store = st.session_state["active_store"]

        model = st.selectbox(
            "Select your query model",
            options=SUPPORTED_MODELS,
            index=SUPPORTED_MODELS.index(DEFAULT_MODEL),
        )
        
        response_type = st.text_input(
            "Response type",
            key="response_type",
            help="Format for the response (e.g., detailed paragraph, bullet points, table)",
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

        config_submitted = st.form_submit_button("Initialize and Index Documents")

        if config_submitted:
            if not store_ready:
                st.error("Please create or select a store first")
            elif not api_key:
                st.error("API key is required")
            else:
                try:
                    status_placeholder = st.empty()
                    status = status_placeholder.status("Initializing LightRAG...")
                    
                    # Initialize LightRAG manager
                    st.session_state["rag_manager"] = LightRAGManager(
                        api_key=api_key,
                        input_dir=active_store,
                        model_name=model,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                    )
                    
                    status.write("Loading documents...")
                    st.session_state["rag_manager"].load_documents()
                    
                    status.update(label="Search configured successfully!", state="complete")
                    st.session_state["status_ready"] = True
                    status_placeholder.empty() # Clear the status after success


                except Exception as e:
                    st.error(f"Configuration error: {str(e)}")

    # Add clear history button outside the form
    if st.button("Clear History", type="secondary"):
        clear_chat_history()
        st.success("History cleared!")

    # Add chat settings when in Chat mode
    if st.session_state["current_mode"] == "Chat":
        with st.expander("💬 Chat Settings"):
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
            st.subheader("Summarization", divider=True)
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

# Main interface
st.write(f"## 🔍 LightRAG {st.session_state['current_mode']}")
st.write("👈 Configure your search settings in the sidebar to get started.")

# Create two columns for the main interface
col1, col2 = st.columns([2, 1])

with col1:
    # Main query interface
    query_container = st.container()
    response_expander = st.expander("🔽 Response and Sources", expanded=True)
    key_points_expander = st.expander("🔑 Key Points")
    st.session_state

with col2:
    # Sidebar information
    with st.expander("ℹ️ Session Info", expanded=True):
        if st.session_state["status_ready"]:
            st.write("**Status:** Ready")
        st.write("**Query Count:**", len(st.session_state["query_history"]) - 1)
        if st.session_state["rag_manager"]:
            st.write("**Model:**", st.session_state["rag_manager"].model_name)
            st.write("**Store:**", st.session_state["rag_manager"].input_dir)


    debug_expander = st.expander("⚠️ Debug Information")

# Query input
with query_container:
    if st.session_state["current_mode"] == "Chat":
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
        for i, message in enumerate(st.session_state["chat_history"]):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

                # Add message controls
                if message["role"] == "assistant":
                    msg_col1, msg_col2 = st.columns([1, 4])
                    with msg_col1:
                        if st.button("📋", key=f"copy_{i}", help="Copy response"):
                            st.write("Copied to clipboard!")
                            message["content"]

        # Chat input
        if prompt := st.chat_input(
            "Type your message here...",
            key="chat_input",
            max_chars=1000,
        ):
            # Add user message to chat history
            st.session_state["chat_history"].append({"role": "user", "content": prompt})

            # Get conversation context
            context = get_conversation_context()

            # Prepare query with context
            query = f"{context}\nCurrent query: {prompt}" if context else prompt
            query_submitted = True
    else:
        # Standard search input
        with st.form("query_form", clear_on_submit=True):
            query = st.text_area(
                "Enter your query:",
                label_visibility="collapsed",
                placeholder="Type your query here...",
                key="query_input",
            )
            submitted = st.form_submit_button("Submit Query")

            if submitted and query:
                logger.info(f"Query submitted: {query}")
                st.session_state["query_submitted"] = True
                st.session_state["current_query"] = query

# Move the query processing outside the form
if "query_submitted" in st.session_state and st.session_state["query_submitted"]:
    query = st.session_state["current_query"]
    if st.session_state["query_history"][-1] != query:
        st.session_state["query_history"].append(query)

        # Initialize progress bar
        progress_bar = query_container.progress(0)

        try:
            # Check if conversation needs summarization
            if (
                st.session_state["current_mode"] == "Chat"
                and should_summarize_conversation()
            ):
                with st.status("Summarizing conversation..."):
                    # Use asyncio.run for summarization
                    summary = asyncio.run(summarize_conversation())
                    update_conversation_with_summary(summary)
                    st.success("Conversation summarized!")

            # Process query
            result = asyncio.run(process_query_with_progress(query, progress_bar))

            # Store results
            st.session_state["query_results"].append({query: result})

            # Format and store response using ResponseProcessor
            formatted_response = st.session_state[
                "response_processor"
            ].format_full_response(query, result)
            st.session_state["responses"].append(formatted_response)

            if st.session_state["current_mode"] == "Chat":
                # Update conversation context
                manage_conversation_context(query, result["response"])

                # Add assistant response to chat history with enhanced formatting
                formatted_chat_response = (
                    f"{result['response']}\n\n"
                    f"*Sources:*\n"
                    f"{st.session_state['response_processor'].format_sources(result.get('sources', []))}"
                )
                st.session_state["chat_history"].append(
                    {"role": "assistant", "content": formatted_chat_response}
                )

            # Extract key points
            response_text, _ = st.session_state["response_processor"].process_response(
                result
            )
            key_points = st.session_state["response_processor"].extract_key_points(
                response_text
            )

            # Clear progress bar
            progress_bar.empty()

            # Save response history
            try:
                st.session_state["response_processor"].save_response_history(
                    query, result, "responses"
                )
            except Exception as e:
                st.warning(f"Could not save response history: {str(e)}")

            # Trigger rerun to update display
            st.rerun()

        except Exception as e:
            st.error(f"Error processing query: {str(e)}")
            progress_bar.empty()

    # Reset the submission flag
    st.session_state["query_submitted"] = False

# Display response
with response_expander:
    st.markdown(st.session_state["responses"][-1])

    if st.session_state["responses"][-1] != "...":
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "Download Response",
                data=get_docx(st.session_state["responses"][-1]),
                file_name=f"LightRAG_Search_Response_{current_time}.docx",
                mime="docx",
            )
        with col2:
            if st.button("Copy to Clipboard"):
                st.write("Response copied! (Use Ctrl+V to paste)")
                st.session_state["responses"][-1]

# Display key points
with key_points_expander:
    if st.session_state["query_results"] and st.session_state["query_results"][-1]:
        latest_query = list(st.session_state["query_results"][-1].keys())[0]
        latest_result = st.session_state["query_results"][-1][latest_query]
        response_text, _ = st.session_state["response_processor"].process_response(
            latest_result
        )
        key_points = st.session_state["response_processor"].extract_key_points(
            response_text
        )
        st.markdown("\n".join(key_points))

# Debug information
with debug_expander:
    if st.session_state["query_results"] and st.session_state["query_results"][-1]:
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        st.download_button(
            "Download Raw Result",
            data=pickle.dumps(st.session_state["query_results"][-1]),
            file_name=f"LightRAG_Search_Debug_{current_time}.pickle",
        )
