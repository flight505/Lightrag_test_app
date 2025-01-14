from typing import Set

class Equation:
    """Represents a mathematical equation with its raw text and symbols."""
    def __init__(self, raw_text: str, symbols: Set[str]):
        self.raw_text = raw_text
        self.symbols = symbols

    def __str__(self) -> str:
        """Convert equation to string format."""
        return self.raw_text

    def __repr__(self) -> str:
        """Detailed string representation including symbols."""
        return f"Equation(raw_text='{self.raw_text}', symbols={self.symbols})" 