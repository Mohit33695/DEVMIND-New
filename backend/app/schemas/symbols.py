"""
Pydantic schemas for code symbol extraction and code intelligence.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class SymbolKind(str, Enum):
    """Enumeration of supported code symbol types."""

    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    IMPORT = "import"


class SymbolItem(BaseModel):
    """Represents an individual code symbol extracted from a source file."""

    name: str = Field(..., description="Name of the code symbol (e.g. function or class name)")
    kind: SymbolKind = Field(..., description="Kind of symbol (function, class, method, import)")
    file_path: str = Field(..., description="Relative file path within repository")
    line_start: int = Field(..., description="1-indexed line start number")
    line_end: int = Field(..., description="1-indexed line end number")
    signature: Optional[str] = Field(None, description="Signature or declaration string")
    docstring: Optional[str] = Field(None, description="Extracted docstring if present")
    parent_symbol: Optional[str] = Field(None, description="Name of enclosing class, struct, or scope")
    parameters: Optional[List[str]] = Field(None, description="List of formal parameter names")
    return_type: Optional[str] = Field(None, description="Declared return type annotation if available")
    visibility: Optional[str] = Field(None, description="Access visibility modifier (e.g. public, private, export)")


class FileSymbols(BaseModel):
    """Collection of code symbols extracted from a single source file."""

    file_path: str = Field(..., description="Relative file path within repository")
    language: str = Field(default="Python", description="Programming language of the file")
    symbols: List[SymbolItem] = Field(
        default_factory=list, description="List of symbols extracted from this file"
    )


class RepositorySymbolsResponse(BaseModel):
    """API response model for repository code intelligence symbols."""

    repo_id: str = Field(..., description="Repository unique identifier")
    total_symbols: int = Field(..., description="Total count of extracted symbols across repository")
    file_symbols: List[FileSymbols] = Field(
        default_factory=list, description="Extracted symbol lists grouped by file"
    )
