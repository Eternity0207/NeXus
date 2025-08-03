"""Parser interface and registry for language-specific parsers."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("parser-service")


@dataclass
class FunctionDef:
    """Extracted function definition."""
    name: str
    start_line: int
    end_line: int
    params: list[str] = field(default_factory=list)
    docstring: Optional[str] = None
    decorators: list[str] = field(default_factory=list)
    is_method: bool = False
    class_name: Optional[str] = None


@dataclass
class ClassDef:
    """Extracted class definition."""
    name: str
    start_line: int
    end_line: int
    methods: list[str] = field(default_factory=list)
    bases: list[str] = field(default_factory=list)
    docstring: Optional[str] = None


@dataclass
class ParseResult:
    """Result of parsing a single source file."""
    file_path: str
    language: str
    functions: list[FunctionDef] = field(default_factory=list)
    classes: list[ClassDef] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    raw_content: str = ""
    error: Optional[str] = None


class BaseParser(ABC):
    """Abstract base class for language-specific parsers."""

    @abstractmethod
    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse source code and extract structure.

        Args:
            content: Raw source code string.
            file_path: Path to the file (for error reporting).

        Returns:
            ParseResult with extracted functions, classes, and imports.
        """
        ...

    @property
    @abstractmethod
    def language(self) -> str:
        """Language identifier string."""
        ...


# ─── Parser Registry ────────────────────────────────────────────────────────

_registry: dict[str, BaseParser] = {}


def register_parser(parser: BaseParser) -> None:
    """Register a parser for a language."""
    _registry[parser.language] = parser
    logger.info(f"Registered parser: {parser.language}")


def get_parser(language: str) -> Optional[BaseParser]:
    """Get the parser for a language."""
    return _registry.get(language)


def get_supported_languages() -> list[str]:
    """List all languages with registered parsers."""
    return list(_registry.keys())
