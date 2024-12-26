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
if "search_mode" not in st.session_state:
    st.session_state["search_mode"] = "Auto (Fallback)"
if "mode_params" not in st.session_state:
    st.session_state["mode_params"] = {}
if "current_search_mode" not in st.session_state:
    st.session_state["current_search_mode"] = "Hybrid"


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


def check_lightrag_ready() -> tuple[bool, str]:
    """
    Check if LightRAG is properly initialized and ready for queries
    Returns: (is_ready, message)
    """
    if st.session_state["rag_manager"] is None:
        return False, "LightRAG not initialized. Click 'Initialize and Index Documents'"
        
    if not st.session_state["status_ready"]:
        return False, "Documents not indexed. Click 'Initialize and Index Documents'"
        
    if not st.session_state["active_store"]:
        return False, "No store selected. Please select a store in the sidebar"
        
    return True, "Ready"


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
        
        # List existing stores
        stores = [d for d in os.listdir(DB_ROOT) if os.path.isdir(os.path.join(DB_ROOT, d))]
        
        # File processor status
        if "file_processor" not in st.session_state:
            st.session_state["file_processor"] = None
            
        # Store selection
        selected_store = st.selectbox(
            "Select Store",
            ["Create New..."] + stores,
            index=0 if st.session_state["active_store"] is None else 
                  stores.index(st.session_state["active_store"]) + 1
        )
        
        if selected_store == "Create New...":
            new_store = st.text_input("Store Name")
            if st.form_submit_button("Create Store"):
                if new_store:
                    store_path = create_store_directory(new_store)
                    if store_path:
                        st.session_state["active_store"] = new_store
                        st.session_state["file_processor"] = FileProcessor(store_path)
                        
                        # Scan for PDFs and convert
                        with st.status("Converting PDFs to text...", expanded=True):
                            results = st.session_state["file_processor"].scan_and_convert_store()
                            if results:
                                st.write("Conversion Results:")
                                for filename, status in results.items():
                                    if status == "converted":
                                        st.success(f"✅ {filename}: Converted to text")
                                    elif status == "skipped":
                                        st.info(f"ℹ️ {filename}: Already processed")
                                    else:
                                        st.error(f"❌ {filename}: {status}")
                        
                        st.success(f"Created store: {new_store}")
                        st.rerun()
        else:
            store_path = os.path.join(DB_ROOT, selected_store)
            
            # Always reinitialize file processor when store changes
            if st.session_state["active_store"] != selected_store:
                st.session_state["file_processor"] = None  # Clear old instance
                st.session_state["active_store"] = selected_store
            
            # Initialize file processor if needed
            if st.session_state["file_processor"] is None:
                st.session_state["file_processor"] = FileProcessor(store_path)
            
            # Show store info
            files_in_store = list(Path(store_path).glob("*.pdf"))
            if files_in_store:
                st.write(f"📁 PDFs in store: {len(files_in_store)}")
                with st.expander("View Files"):
                    for file in files_in_store:
                        st.write(f"- {file.name}")
            
            # Add form submit buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Scan for New Files"):
                    if st.session_state["file_processor"]:
                        # Reinitialize processor to ensure latest methods
                        st.session_state["file_processor"] = FileProcessor(store_path)
                        with st.status("Scanning for new files...", expanded=True):
                            results = st.session_state["file_processor"].scan_and_convert_store()
                            if results:
                                st.write("Processing Results:")
                                for filename, status in results.items():
                                    if status == "converted":
                                        st.success(f"✅ {filename}: Converted to text")
                                    elif status == "skipped":
                                        st.info(f"ℹ️ {filename}: Already processed")
                                    else:
                                        st.error(f"❌ {filename}: {status}")
                            else:
                                st.info("No new files found to process")
            
            with col2:
                if st.form_submit_button("Cleanup Unused Files"):
                    if st.session_state["file_processor"]:
                        removed = st.session_state["file_processor"].cleanup_unused()
                        if removed:
                            st.info(f"Removed {len(removed)} unused files")
                        else:
                            st.info("No unused files found")

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
st.write(f"## :material/search: LightRAG {st.session_state['current_mode']}")
st.write(":material/subdirectory_arrow_left: Configure your search settings in the sidebar to get started.")

# Create two columns for the main interface
col1, col2 = st.columns([2, 1], vertical_alignment="bottom",)

with col1:
    # Mode selection above query container
    st.markdown("### Search Mode")
    
    # Replace radio with segmented control
    selected_mode = st.segmented_control(
        "Select mode",
        options=["Hybrid", "Naive", "Local", "Global"],
        key="mode_selector",
        help="* Hybrid: Best for most queries - combines local and global search\n"
             "* Naive: Direct LLM query with full context - best for simple questions\n"
             "* Local: Uses nearby context - best for specific details\n"
             "* Global: Searches entire knowledge base - best for broad themes\n",
        default="Hybrid"
    )
    
    # Update session state when mode changes
    if selected_mode != st.session_state.get("current_search_mode"):
        st.session_state["current_search_mode"] = selected_mode
        st.toast(f"Switched to {selected_mode} mode", icon="🔄")

    # Initialize mode parameters
    mode_params = {}
    
    # Mode-specific settings in small expander
    with st.expander("Mode Settings", expanded=False):
        if selected_mode == "Global":
            mode_params["top_k"] = st.slider(
                "Number of documents to retrieve",
                min_value=3,
                max_value=60,
                value=10,
                help="Higher values search more documents but take longer"
            )
        elif selected_mode == "Local":
            mode_params["max_token_for_local_context"] = st.slider(
                "Maximum context tokens",
                min_value=1000,
                max_value=4000,
                value=2000,
                help="Maximum tokens to consider from local context"
            )
        elif selected_mode == "Naive":
            mode_params["max_token_for_text_unit"] = st.slider(
                "Maximum tokens per text unit",
                min_value=1000,
                max_value=4000,
                value=2000,
                help="Maximum tokens to consider per text unit"
            )
        
        # Common parameters for all modes
        mode_params["only_need_context"] = st.checkbox(
            "Return only context",
            value=False,
            help="Return raw context without LLM processing"
        )

    # Save mode parameters to session state
    st.session_state["mode_params"] = mode_params

    # Query container below mode selection
    query_container = st.container()
    response_expander = st.expander("🔽 Response and Sources", expanded=True)
    key_points_expander = st.expander("🔑 Key Points")

with col2:
    # Sidebar information
    with st.expander(":material/info: **Session Info**", expanded=True):
        # Status with color and icon
        if st.session_state["status_ready"]:
            st.write("🟢 **System Status:** Ready and operational")
        else:
            st.write("🔴 **System Status:** Not initialized")
            
        st.divider()
        # System info with icons
        st.write("**Query Count:**", len(st.session_state["query_history"]) - 1)
        if st.session_state["rag_manager"]:
            st.write("**Model:**", st.session_state["rag_manager"].model_name)
            st.write("**Store:**", st.session_state["rag_manager"].input_dir)

    debug_expander = st.expander(":material/bug_report: Debug Information")

# Query input
with query_container:
    is_ready, status_msg = check_lightrag_ready()
    
    if not is_ready:
        st.warning(status_msg)
    else:
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
                    with st.status("Processing query...") as status:
                        result = st.session_state["rag_manager"].query(query)
                        logger.info(f"Query result: {result}")

                        if result and result.get("response"):
                            # Format response with sources
                            formatted_response = (
                                f"{result['response']}\n\n"
                                f"*Mode: {result.get('mode', 'unknown')}*\n"
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
                            
                            # Force streamlit to rerun and show the new message
                            st.rerun()
                        else:
                            logger.error("No valid response received")
                            st.error("Failed to get a response. Please try again.")

                except Exception as e:
                    logger.error(f"Error processing chat: {str(e)}", exc_info=True)
                    st.error(f"Error processing chat: {str(e)}")
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

# The query processing should only happen when:
# 1. rag_manager is initialized
# 2. User submits a query
if "query_submitted" in st.session_state and st.session_state["query_submitted"]:
    if st.session_state["rag_manager"] is None:
        st.error("Please initialize LightRAG first by clicking 'Initialize and Index Documents'")
    else:
        query = st.session_state["current_query"]
        if st.session_state["query_history"][-1] != query:
            st.session_state["query_history"].append(query)

            try:
                # Get mode with fallback
                mode = (selected_mode or "Hybrid").lower()
                logger.info(f"Processing query with mode: {mode}")
                
                # Create query parameters using QueryParam
                query_params = QueryParam(
                    mode=mode,
                    **st.session_state.get("mode_params", {})
                )

                with st.status(f"Processing query in {selected_mode} mode..."):
                    # Pass QueryParam object directly
                    result = st.session_state["rag_manager"].query(
                        query,
                        param=query_params  # Use param= to match the documentation
                    )
                    logger.info(f"Query completed in {selected_mode} mode")
                
                # Process and display result
                if result:
                    # Handle string response (which is the documented behavior)
                    formatted_result = {
                        "response": result,  # Result is a string
                        "mode": selected_mode,
                        "sources": []  # Sources not provided in basic response
                    }
                    
                    st.session_state["query_results"].append({query: formatted_result})
                    formatted_response = st.session_state["response_processor"].format_full_response(
                        query, formatted_result
                    )
                    st.session_state["responses"].append(formatted_response)
                else:
                    st.error("No response received")

            except Exception as e:
                st.error(f"Error processing query: {str(e)}")

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

# Update query processing to handle the mode correctly
def get_query_mode(selected_mode: str) -> str:
    """Convert UI mode selection to query mode"""
    mode_mapping = {
        "Auto (Fallback)": "auto",
        "Naive": "naive",
        "Local": "local",
        "Global": "global",
        "Hybrid": "hybrid"
    }
    return mode_mapping.get(selected_mode, "auto")
