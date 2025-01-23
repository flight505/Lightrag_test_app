# Composer Agent Task

You are tasked with implementing a CLI version of LightRAG, transforming it from a web application while preserving its core academic paper processing capabilities.

## Task Context
- Source: Existing LightRAG codebase with web dependencies
- Target: Clean CLI implementation using Click and Rich
- Guides: Follow CLI_ONLY_GUIDE.md for implementation and REFACTORING.md for code cleanup

## State Management Transition
Current Streamlit state in `pages/` (to be replaced):
1. `st.session_state` in Search.py for conversation history
2. `st.cache_data` in file_processor.py for PDF processing
3. Session-based store selection in Manage.py
4. UI state for progress bars and status updates

Replace with CLI-appropriate state:
```python
# 1. Replace session_state with file-based storage
# Before (Search.py):
if 'conversation' not in st.session_state:
    st.session_state.conversation = []

# After (cli/commands/search_cmd.py):
class ConversationManager:
    def __init__(self, store_path: Path):
        self.history_file = store_path / "conversation_history.json"
        
    def load_history(self) -> List[Dict]:
        if self.history_file.exists():
            return json.loads(self.history_file.read_text())
        return []

# 2. Replace cache_data with lru_cache
# Before (file_processor.py):
@st.cache_data
def process_file(self, file_path: str):
    pass

# After (src/processing/document.py):
@lru_cache(maxsize=32)
def process_file(self, file_path: str):
    pass

# 3. Replace session-based store selection with Click context
@click.group()
@click.pass_context
def cli(ctx):
    ctx.ensure_object(dict)
    ctx.obj['config'] = load_config()
    ctx.obj['store'] = None

# 4. Replace UI progress with Rich progress
# Before (Manage.py):
with st.progress("Processing..."):
    processor.process()

# After (cli/commands/pdf_cmd.py):
with Progress() as progress:
    task = progress.add_task("Processing", total=100)
    processor.process(on_progress=lambda x: progress.update(task, completed=x))
```

## Implementation Rules
1. DO NOT modify:
   - Working PDF processing pipeline
   - Store structure
   - Test assertions
   - Error handling patterns

2. DO:
   - Read test files before implementation
   - Remove web framework dependencies
   - Use Click for CLI and Rich for output
   - Maintain processing chain
   - Check Focus.md for project updates

## Starting Point
1. Begin with store operations:
   - Implement `cli/commands/store_cmd.py`
   - Write tests in `tests/cli/test_store_cmd.py`
   - Ensure store structure matches specification

## Code Style
- Use Click decorators for commands
- Implement Rich progress bars
- Add comprehensive error handling
- Include detailed help text
- Follow type hints

## Success Metrics
1. Commands work without web dependencies
2. Tests pass with proper coverage
3. Error handling is consistent
4. Progress reporting works
5. Documentation is complete

Start with implementing the store commands. I will review and provide feedback on your implementation. 