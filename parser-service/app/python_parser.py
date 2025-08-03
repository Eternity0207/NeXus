"""Python AST parser — extracts functions, classes, and imports from Python source."""

from __future__ import annotations

import ast
import logging
from typing import Optional

from app.base import BaseParser, ParseResult, FunctionDef, ClassDef

logger = logging.getLogger("parser-service")


class PythonParser(BaseParser):
    """Parser for Python source files using the built-in ast module."""

    @property
    def language(self) -> str:
        return "python"

    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse Python source into structured components."""
        result = ParseResult(
            file_path=file_path,
            language=self.language,
            raw_content=content,
        )

        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
            result.error = f"SyntaxError: {e}"
            return result

        # Extract imports
        result.imports = self._extract_imports(tree)

        # Extract top-level functions and classes
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                result.functions.append(self._extract_function(node))

            elif isinstance(node, ast.ClassDef):
                class_def = self._extract_class(node)
                result.classes.append(class_def)

                # Extract methods from the class
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        func = self._extract_function(item, class_name=node.name)
                        result.functions.append(func)

        return result

    def _extract_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        class_name: Optional[str] = None,
    ) -> FunctionDef:
        """Extract metadata from a function/method node."""
        params = []
        for arg in node.args.args:
            if arg.arg != "self" and arg.arg != "cls":
                params.append(arg.arg)

        decorators = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
            elif isinstance(dec, ast.Attribute):
                decorators.append(f"{self._get_attr_name(dec)}")
            elif isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Name):
                    decorators.append(dec.func.id)
                elif isinstance(dec.func, ast.Attribute):
                    decorators.append(self._get_attr_name(dec.func))

        return FunctionDef(
            name=node.name,
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            params=params,
            docstring=ast.get_docstring(node),
            decorators=decorators,
            is_method=class_name is not None,
            class_name=class_name,
        )

    def _extract_class(self, node: ast.ClassDef) -> ClassDef:
        """Extract metadata from a class node."""
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(self._get_attr_name(base))

        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(item.name)

        return ClassDef(
            name=node.name,
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            methods=methods,
            bases=bases,
            docstring=ast.get_docstring(node),
        )

    def _extract_imports(self, tree: ast.Module) -> list[str]:
        """Extract all import statements."""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}" if module else alias.name)
        return imports

    @staticmethod
    def _get_attr_name(node: ast.Attribute) -> str:
        """Recursively get dotted attribute name."""
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
