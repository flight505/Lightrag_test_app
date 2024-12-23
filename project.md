You are an AI assistant specialized in developing and maintaining a Streamlit-based LightRAG application.

## Project Overview
The LightRAG application is designed to serve as a comprehensive tool for academic research, providing a user-friendly interface for querying and visualizing graph-based data. It leverages a knowledge graph and retrieval-augmented generation (RAG) system to handle large datasets and complex queries efficiently. Key features include:

- **Multi-Mode Search**: Supports local, global, hybrid, and naive search functionalities.
- **File Handling**: Converts various document formats (docx, text, pdf) to .txt and organizes them into a "converted" subfolder.
- **User Interface**: Streamlit-based interface for easy configuration and query submission.
- **Source Tracking**: Maintains references to original documents for academic integrity.

- **Search Functionality**:
**Implementation**: Located in `pages/1_Search.py`, this module provides various search functionalities: 
   Local Search: Searches within a specific dataset or context. 
   Global Search: Searches across multiple datasets or the entire application. 
   Hybrid Search: Combines local and global search strategies for comprehensive results. 
   Naive Search: A straightforward search approach without advanced algorithms.

- **Preprocessing**: Script for converting files to .txt format located in `scr/preprocessing_functions.py`.
- **Session Management**: Utilizes Streamlit session state to manage user interactions and query history.
- **Error Handling**: Comprehensive try-except blocks with logging for debugging.
- **Usability Improvements**:Refine the user interface to make configuration options more intuitive. Add tooltips and help sections for new users.
- **Performance Optimization**: Optimize query processing to reduce response time. Implement caching mechanisms for frequently accessed data.
- **Testing and Validation**: Conduct thorough testing of all functionalities, especially edge cases. Suggestion: Use automated testing frameworks to ensure reliability.

## Main files:

1. `src/file_manager.py`: Contains functions for creating document directories and updating the `.gitignore` file to manage file storage and exclusion.

2. `pages/1_Search.py`: Implements the Streamlit interface for search and chat modes, managing session states and processing queries with progress updates.

3. `src/preprocessing_functions.py`: Provides functions to convert various document formats (docx, pptx, xlsx) to text files and manage indexed files.

4. `src/lightrag_helpers.py`: Includes helper functions for processing LightRAG responses, managing sources, and formatting responses.

5. `src/global_helper_functions.py`: Contains functions for mapping generated responses to source documents and creating traceability tables.

6. `src/Graph_query.py`: Sets up the Streamlit page configuration for querying the knowledge base using LightRAG.

7. `src/lightrag_init.py`: Manages the initialization and configuration of LightRAG, including document loading and query execution.

8. `src/local_helper_functions.py`: Provides functions for local search post-processing, mapping responses to source documents, and creating traceability tables.

## Helper Functions

1. **Global Helpers**:
   - **Purpose**: Manage the mapping of generated responses to source documents, ensuring traceability and context.
   - **Key Functions**:
     - `retrieve_single_report_ids`: Extracts unique report IDs from responses.
     - `map_text_unit_ids`: Merges entity and relationship data to establish traceability.
     - `map_text_unit_content`: Associates text content with traceability data.
     - `map_titles`: Maps document titles to traceability data.
     - `most_frequent_sources`: Identifies frequently referenced source documents.

2. **Local Helpers**:
   - **Purpose**: Handle data specific to local contexts, focusing on entity and relationship extraction.
   - **Key Functions**:
     - `map_reports_entities_relationships`: Extracts and maps entity and relationship IDs.
     - `combine_query_response_sources`: Formats query responses with source references.
     - `retrieve_text_units`: Retrieves text units related to specific queries.

## Coding Standards
- **Language**: Python 3.10+
- **Style Guide**: 
  - Follow PEP 8 conventions
  - Use termcolor for console output
  - Define major constants in UPPERCASE
  - Implement clear error handling with try-except blocks
  - Use logging for debugging purposes

## File Organization
- **Pages**: Store Streamlit pages in the /pages directory
- **Preprocessing**: preprocessing, global and local helper functions scripts in src/

## Best Practices
1. **Code Structure**:
   - Implement modular, reusable components
   - Maintain clear separation between global and local functionalities
   - Use descriptive variable names and comments

2. **Error Handling**:
   - Use try-except blocks with specific error messages
   - Implement logging for debugging purposes
   - Handle file operations with proper encoding (utf-8)

3. **Configuration**:
   - Use environment variables for sensitive data
   - Maintain an up-to-date requirements.txt
   - Avoid hardcoding configuration values

## Testing
- **Manual Testing**: Test both global and local search functionalities
- **Error Cases**: Verify proper handling of edge cases
- **UI Testing**: Ensure Streamlit interface remains responsive
