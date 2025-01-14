import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Set

from termcolor import colored

logger = logging.getLogger(__name__)

class EquationType(str, Enum):
    INLINE = "inline"
    DISPLAY = "display"
    DEFINITION = "definition"
    THEOREM = "theorem"

@dataclass
class Equation:
    """Represents a mathematical equation with context and metadata."""
    raw_text: str
    equation_id: str
    context: str = ""
    equation_type: EquationType = EquationType.INLINE
    symbols: Set[str] = field(default_factory=set)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'raw_text': self.raw_text,
            'equation_id': self.equation_id,
            'context': self.context,
            'equation_type': self.equation_type.value,
            'symbols': list(self.symbols)
        }

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
                                equation_id=f"eq{eq_id}",
                                context=context,
                                equation_type=eq_type,
                                symbols=symbols
                            ))
                            eq_id += 1
                            
                            if self.debug:
                                self._debug_print(f"Found equation: {eq_text}")
                                
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