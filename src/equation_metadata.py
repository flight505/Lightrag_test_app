"""Equation metadata and processing classes."""
import logging
import re
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field
from termcolor import colored

logger = logging.getLogger(__name__)


class EquationType(str, Enum):
    """Type of equation in the document."""
    INLINE = "inline"
    DISPLAY = "display"
    DEFINITION = "definition"
    THEOREM = "theorem"


class Equation(BaseModel):
    """Represents a mathematical equation."""
    raw_text: str = Field(description="The raw text of the equation")
    symbols: Set[str] = Field(default_factory=set, description="Set of mathematical symbols in the equation")
    equation_type: EquationType = Field(default=EquationType.INLINE, description="Type of equation")
    context: Optional[str] = Field(default=None, description="The surrounding text context of the equation")

    model_config = {
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "json_encoders": {
                set: list
            }
        }
    }

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Convert equation to dictionary format for serialization."""
        data = super().model_dump(**kwargs)
        data['symbols'] = list(data['symbols'])  # Convert set to list
        return data


class EquationExtractor:
    """Handles extraction and classification of mathematical equations"""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
    
    def _debug_print(self, message: str, color: str = "blue") -> None:
        """Print debug message if debug mode is enabled."""
        if self.debug:
            print(colored(f"[DEBUG] {message}", color))
    
    def extract_equations(self, text: str) -> List[Equation]:
        """Extract equations from text with enhanced pattern matching."""
        equations = []
        eq_id = 1
        
        try:
            # Equation patterns
            patterns = [
                (r'\$\$(.*?)\$\$', EquationType.DISPLAY),  # Display equations
                (r'\$(.*?)\$', EquationType.INLINE),  # Inline equations
                (r'\\begin\{equation\}(.*?)\\end\{equation\}', EquationType.DISPLAY),  # Numbered equations
                (r'\\[(.*?)\\]', EquationType.DISPLAY),  # Alternative display equations
                (r'\\begin\{align\*?\}(.*?)\\end\{align\*?\}', EquationType.DISPLAY),  # Align environments
                (r'\\begin\{eqnarray\*?\}(.*?)\\end\{eqnarray\*?\}', EquationType.DISPLAY),  # Eqnarray environments
                (r'\\\[(.*?)\\\]', EquationType.DISPLAY),  # LaTeX display equations
                (r'\\\((.*?)\\\)', EquationType.INLINE)  # LaTeX inline equations
            ]
            
            lines = text.split('\n')
            for i, line in enumerate(lines):
                for pattern, eq_type in patterns:
                    matches = re.finditer(pattern, line, re.DOTALL | re.MULTILINE)
                    for match in matches:
                        try:
                            # Get equation content
                            eq_text = match.group(1).strip()
                            if not eq_text:
                                continue
                                
                            # Get context (surrounding lines)
                            start = max(0, i-2)
                            end = min(len(lines), i+3)
                            context = '\n'.join(lines[start:end])
                            
                            # Extract symbols
                            symbols = self._extract_symbols(eq_text)
                            
                            equations.append(Equation(
                                raw_text=eq_text,
                                symbols=symbols,
                                equation_type=eq_type,
                                context=context
                            ))
                            
                            if self.debug:
                                self._debug_print(f"Found {eq_type} equation: {eq_text}")
                                
                        except Exception as e:
                            self._debug_print(f"Error processing equation match: {str(e)}", "yellow")
                            continue
            
            if equations:
                print(colored(f"✓ Found {len(equations)} equations", "green"))
            else:
                print(colored("⚠️ No equations found", "yellow"))
                
            return equations
            
        except Exception as e:
            self._debug_print(f"Error extracting equations: {str(e)}", "red")
            return []
    
    def _extract_symbols(self, equation: str) -> Set[str]:
        """Extract mathematical symbols from equation."""
        symbols = set()
        
        # Common mathematical symbols
        symbol_patterns = [
            r'\\alpha', r'\\beta', r'\\gamma', r'\\delta', r'\\epsilon',
            r'\\theta', r'\\lambda', r'\\mu', r'\\pi', r'\\sigma',
            r'\\sum', r'\\prod', r'\\int', r'\\partial', r'\\infty',
            r'\\frac', r'\\sqrt', r'\\left', r'\\right', r'\\cdot',
            r'\\mathcal', r'\\mathbf', r'\\mathrm', r'\\text'
        ]
        
        try:
            # Extract LaTeX commands
            for pattern in symbol_patterns:
                if re.search(pattern, equation):
                    symbols.add(pattern.replace('\\', ''))
            
            # Extract variable names (single letters)
            var_matches = re.findall(r'(?<=[^\\])[a-zA-Z](?![a-zA-Z])', equation)
            symbols.update(var_matches)
            
            # Extract subscripts
            subscripts = re.findall(r'_\{([^}]+)\}', equation)
            symbols.update(subscripts)
            
            return symbols
            
        except Exception as e:
            logger.warning(f"Error extracting symbols: {str(e)}")
            return set() 