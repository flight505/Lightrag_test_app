# LightRAG: Advanced Academic Research Assistant 🎓

A sophisticated academic research tool combining knowledge graph capabilities with retrieval-augmented generation (RAG), optimized for academic paper analysis and research assistance.

## Architecture Overview 🏗️

<p align="center">
  <img src="https://github.com/user-attachments/assets/d59098dc-c84c-4c3d-b902-fb2215fa9f91" alt="LightRAG Architecture" width="100%">
</p>

Our system enhances the core LightRAG framework with specialized academic components:

### Academic Enhancement Layer
- **Academic Metadata Processor**: Handles author tracking, citation management, DOI extraction, and equation processing with robust validation
- **Enhanced File Processor**: Optimized for academic PDFs with LaTeX equation extraction and pattern recognition
- **Academic Response Processor**: Generates responses in academic style with proper citations and source attribution

### Core LightRAG Integration
The academic components seamlessly integrate with LightRAG's:
- Document ingestion pipeline for processing academic papers
- Multi-modal storage layer (Vector DB, Knowledge Graph, KV Store)
- Sophisticated retrieval pipeline with multiple query modes

## Key Features 🌟

- **Advanced PDF Processing**: Optimized PDF conversion on Apple Silicon and Marker
- **Academic Metadata Extraction**: Comprehensive tracking of authors, references, equations and citations
- **Multi-Mode Search**: Naive, Local, Global, Hybrid, and Mix search strategies
- **LaTeX Support**: Advanced equation extraction and processing with context preservation
- **Citation Management**: Multiple citation styles (APA, MLA, Chicago, IEEE)
- **Academic Response Generation**: Structured responses with source tracking

## Installation 🔧

1. Clone the repository:
```bash
git clone https://github.com/flight505/Lightrag_test_app.git
cd lightrag
```

2. Create and activate a Python virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

3. Set up environment variables:
```bash
export OPENAI_API_KEY="your-api-key"
```

3. Install dependencies using uv:
```bash
pip install uv
uv sync
```
3. A alternative to setting up environment is using temp uv env and running the streamlit app directly:
```bash
uv run streamlit_app.py && streamlit run streamlit_app.py
```

## Usage 🚀

1. Initialize the workspace:
```bash
python src/lightrag_init.py --init
```

2. Run the Streamlit interface:
```bash
streamlit run main.py
```

## Search Modes 🔍

- **Naive**: Basic document search
- **Local**: Context-aware document analysis
- **Global**: Broad knowledge base search
- **Hybrid**: Combined local and global search
- **Mix**: Adaptive search strategy

## Academic Features 📚

### Metadata Processing
- Multiple validation levels (Basic, Standard, Strict)
- Equation type classification
- Author affiliation tracking
- DOI and venue extraction
- Citation network analysis

### Document Processing
- LaTeX equation extraction
- Reference pattern matching
- Batch processing with progress tracking
- Source preservation and validation

## Configuration ⚙️

Default settings optimized for academic papers:
- Chunk size: 500
- Chunk overlap: 50
- Temperature: Configurable per use case
- Sentence-based chunking

## Models 🤖

Supported models:
- gpt-4o (recommended for complex analysis)
- gpt-4o-mini (default)
- o1-mini
- o1

## Error Handling and Logging 📝

- Comprehensive try-except blocks
- Color-coded terminal output
- Progress tracking
- Detailed error context

## Best Practices 💡

- UTF-8 encoding throughout
- Environment variable configuration
- Parallel processing where applicable
- Separation of concerns
- Comprehensive error handling

## Contributing 🤝

We welcome contributions! Please read our contributing guidelines and submit pull requests. Our academic enhancements focus on:

1. Improving academic metadata extraction
2. Enhancing LaTeX and equation handling
3. Expanding citation style support
4. Optimizing academic response generation

## License 📄

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments 🙏

- Built upon GraphRAG concepts
- Optimized for academic research
- Enhanced with advanced metadata processing
- Special thanks to the academic research community

---

For detailed documentation, visit our [Wiki](https://github.com/yourusername/lightrag/wiki).

Happy Researching! 📚✨