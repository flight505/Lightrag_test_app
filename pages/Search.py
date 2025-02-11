import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, List

import streamlit as st

try:
    from docx import Document
except ImportError:
    st.error("Could not import python-docx. Please install it with: pip install python-docx")
    Document = None
import networkx as nx

try:
    import xxhash
except ImportError:
    st.error("Could not import xxhash. Please install it with: pip install xxhash")
    xxhash = None

from src.file_manager import DB_ROOT, create_store_directory
from src.lightrag_helpers import ResponseProcessor
from src.lightrag_init import DEFAULT_MODEL, SUPPORTED_MODELS, LightRAGManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
file_handler = logging.FileHandler('chat.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

def show_search():
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
    if "openai_api_key" not in st.session_state:
        st.session_state["openai_api_key"] = os.getenv("OPENAI_API_KEY", "")

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


    def rewrite_prompt(prompt: str) -> str:
        """Rewrite the user prompt into a templated format using OpenAI."""
        try:
            from openai import OpenAI
            
            # Use API key from session state
            if not st.session_state.get("openai_api_key"):
                st.error("OpenAI API key not found in session state")
                return prompt
                
            client = OpenAI(api_key=st.session_state["openai_api_key"])
            
            system_instruction = """
            You are a prompt engineering assistant. Your task is to rewrite user prompts into a templated format.
            The template should follow this structure:

            <START_OF_SYSTEM_PROMPT>
            You are an academic research assistant. Your task is to help answer questions about academic papers
            and research documents. You should:
            1. Think step by step
            2. Cite specific sources and quotes
            3. Be precise and academic in tone
            4. Acknowledge uncertainty when present
            5. Focus on factual information from the sources
            </START_OF_SYSTEM_PROMPT>

            <START_OF_USER>
            {input_str}
            </END_OF_USER>

            Keep the original intent but make it more specific and detailed.
            You will answer a reasoning question. Think step by step. The last two lines of your response should be of the following format: 
            - '> Answer: $VALUE' where VALUE is concise and to the point.
            - '> Sources: $SOURCE1, $SOURCE2, ...' where SOURCE1, SOURCE2, etc. are the sources you used to justify your answer.
            """

            response = client.chat.completions.create(
                model="gpt-4",  # Using GPT-4 for better prompt engineering
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": f"Rewrite this prompt: {prompt}"}
                ],
                temperature=0.7
            )
            
            rewritten = response.choices[0].message.content
            logger.info(f"Prompt rewritten ({len(prompt)} → {len(rewritten)} chars)")
            return rewritten
            
        except Exception as e:
            logger.error(f"Error rewriting prompt: {str(e)}")
            st.warning(f"Could not rewrite prompt: {str(e)}")
            # Return original prompt if rewrite fails
            return prompt

    st.divider()
    
    # Main interface
    st.write("### 💬 LightRAG Chat")

    # Configuration form
    with st.form("configuration_form"):
        st.markdown("**Configure your chat:**")
        
        # API key handling
        if not st.session_state["openai_api_key"]:
            api_key = st.text_input("Your API key", type="password")
            if not api_key:
                st.warning("Please enter your OpenAI API key or set OPENAI_API_KEY environment variable")
        else:
            api_key = st.session_state["openai_api_key"]
            if not st.session_state.get("api_key_shown"):
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
                        # Create store directory if it doesn't exist
                        store_path = os.path.join(DB_ROOT, st.session_state["active_store"])
                        if not os.path.exists(store_path):
                            create_store_directory(st.session_state["active_store"])
                            st.toast(f"Created new store: {st.session_state['active_store']}")
                        
                        # Store API key in session state
                        st.session_state["openai_api_key"] = api_key
                        
                        # Initialize LightRAG manager with correct parameters
                        st.session_state["rag_manager"] = LightRAGManager(
                            api_key=st.session_state["openai_api_key"],
                            input_dir=store_path,
                            model_name=model,
                            chunk_size=chunk_size,
                            chunk_overlap=chunk_overlap,
                            temperature=temperature
                        )
                        
                        # Validate store using DocumentValidator
                        validation_results = st.session_state["rag_manager"].validator.validate_store(store_path)
                        
                        if validation_results['errors']:
                            for error in validation_results['errors']:
                                st.warning(f"Validation warning: {error}")
                        
                        if validation_results['valid_files']:
                            with st.status("Indexing documents..."):
                                st.session_state["rag_manager"].load_documents(validation_results['valid_files'])
                                st.toast("Documents indexed successfully!")
                                st.session_state["status_ready"] = True
                        else:
                            st.info("No valid files found. Please add documents in the Manage Documents page.")
                            st.session_state["status_ready"] = True

                        # Force rerun to update UI
                        st.rerun()
                except Exception as e:
                    st.error(f"Configuration error: {str(e)}")
                    logger.error(f"Configuration error: {str(e)}", exc_info=True)

    st.divider()

    # Create two columns for the main interface
    col1, col2 = st.columns([3, 1])

    with col1:
        # Chat interface
        chat_container = st.container()
        st.write(st.session_state["rag_manager"])
        
        with chat_container:
            is_ready, status_msg = check_lightrag_ready()
            
            if not is_ready:
                st.warning(status_msg)
            else:
                # Mode and rewrite selections in columns
                mode_col, rewrite_col = st.columns([3, 2])
                
                with mode_col:
                    # Mode selection
                    mode = st.segmented_control(
                        "Search Mode",
                        options=["Mix", "Hybrid", "Local", "Global"],
                        default="Mix",
                        help="""
                        **Mix**: Combines knowledge graph and vector search for comprehensive results
                        **Hybrid**: Balances local and global context
                        **Local**: Focuses on specific document context
                        **Global**: Explores broader relationships across documents
                        """
                    )
                    st.session_state["search_mode"] = mode
                    logger.info(f"Search mode selected: {mode}")
                
                with rewrite_col:
                    # Prompt rewrite selection
                    rewrite = st.segmented_control(
                        "Prompt Style",
                        options=["Direct", "Rewrite"],
                        default="Direct",
                        help="""
                        **Direct**: Use the prompt as entered
                        **Rewrite**: Enhance the prompt with academic style and structure
                        """
                    )
                    st.session_state["rewrite_prompt"] = (rewrite == "Rewrite")

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
                        
                        # Rewrite prompt if enabled
                        if st.session_state.get("rewrite_prompt", False):
                            with st.status("Rewriting prompt..."):
                                query = rewrite_prompt(query)
                                logger.info(f"Rewritten query: {query}")

                        # Process query with progress indicator
                        with st.status("Processing...") as status:
                            # Get the search mode
                            mode = st.session_state["search_mode"].lower()
                            logger.info(f"Using search mode: {mode}")
                            
                            # Execute query with mode
                            result = st.session_state["rag_manager"].query(
                                query,
                                mode=mode
                            )
                            logger.info(f"Query result: {result}")

                            if result and result.get("response"):
                                # Format response with sources
                                formatted_response = (
                                    f"{result['response']}\n\n"
                                    f"*Sources:*\n"
                                )
                                
                                # Add sources if available
                                if result.get("sources"):
                                    sources_text = "\n".join([f"- {source}" for source in result["sources"]])
                                    formatted_response += sources_text
                                
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

    # Add Knowledge Graph section at the bottom
    if "show_graph" in st.session_state and st.session_state["show_graph"]:
        st.divider()
        with st.container():
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
                        # Load and analyze graph
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
                            import random

                            from pyvis.network import Network
                            
                            with st.spinner("Generating interactive network visualization..."):
                                net = Network(
                                    height="600px", 
                                    width="100%", 
                                    bgcolor="#ffffff",
                                    font_color="#333333",
                                    directed=True
                                )
                                
                                net.from_nx(graph)
                                
                                for node in net.nodes:
                                    node.update({
                                        "color": "#{:06x}".format(random.randint(0, 0xFFFFFF)),
                                        "size": 25,
                                        "font": {"size": 12},
                                        "borderWidth": 2,
                                        "borderWidthSelected": 4
                                    })
                                
                                html_path = os.path.join(store_path, "graph_visualization.html")
                                net.save_graph(html_path)
                                
                                with open(html_path, 'r', encoding='utf-8') as f:
                                    html_content = f.read()
                                    html_content = html_content.replace(
                                        '</head>',
                                        '''<style>
                                        .vis-network {
                                            border: 1px solid #ddd;
                                            border-radius: 4px;
                                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                                        }
                                        </style>
                                        </head>'''
                                    )
                                st.components.v1.html(html_content, height=600)
                        
                        except ImportError:
                            st.error("⚠️ Please install pyvis to enable graph visualization: `pip install pyvis`")
                        except Exception as e:
                            st.error(f"❌ Error generating visualization: {str(e)}")
            
            except Exception as e:
                st.error(f"❌ Error analyzing graph: {str(e)}")
                logger.error(f"Graph analysis error: {str(e)}")
            
            # Add button to hide graph with proper styling
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("Hide Knowledge Graph", type="secondary"):
                    st.session_state["show_graph"] = False
                    st.rerun()
        
