"""Progress reporting utilities for LightRAG CLI."""
from typing import Protocol, Optional, Callable
from rich.progress import Progress, TaskID

class ProgressCallback(Protocol):
    """Protocol for progress callbacks."""
    def __call__(self, current: int, total: int) -> None: ...

class ProgressManager:
    """Manages progress reporting for CLI operations."""
    
    def __init__(self, description: str = "Processing"):
        self.progress = Progress()
        self.description = description
        self.task_id: Optional[TaskID] = None
        
    def __enter__(self) -> 'ProgressManager':
        self.progress.start()
        self.task_id = self.progress.add_task(self.description, total=100)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.progress.stop()
        
    def update(self, current: int, total: int) -> None:
        """Update progress based on current and total values."""
        if self.task_id is not None:
            percentage = int((current / total) * 100)
            self.progress.update(self.task_id, completed=percentage)
            
    def get_callback(self) -> ProgressCallback:
        """Get a callback function for progress updates."""
        return self.update 