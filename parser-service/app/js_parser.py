"""JavaScript/TypeScript parser — regex-based extraction for JS/TS source files."""

from __future__ import annotations

import logging
import re
from typing import Optional

from app.base import BaseParser, ParseResult, FunctionDef, ClassDef

logger = logging.getLogger("parser-service")

# ─── Regex Patterns ──────────────────────────────────────────────────────────

# function declarations: function name(params) {
RE_FUNCTION = re.compile(
    r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)",
    re.MULTILINE,
)

# arrow / const functions: const name = (params) => or const name = function(params)
RE_CONST_FUNC = re.compile(
    r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|(\w+))\s*=>",
    re.MULTILINE,
)

# class declarations: class Name extends Base {
RE_CLASS = re.compile(
    r"^(?:export\s+)?(?:default\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?",
    re.MULTILINE,
)

# class methods: name(params) { or async name(params) {
RE_METHOD = re.compile(
    r"^\s+(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{",
    re.MULTILINE,
)

# imports: import ... from '...' or require('...')
RE_IMPORT_FROM = re.compile(
    r"""(?:import\s+.*?\s+from\s+['"]([^'"]+)['"]|require\s*\(\s*['"]([^'"]+)['"]\s*\))""",
    re.MULTILINE,
)

# import side-effect: import '...'
RE_IMPORT_SIDE = re.compile(
    r"""^import\s+['"]([^'"]+)['"]""",
    re.MULTILINE,
)


class JavaScriptParser(BaseParser):
    """Regex-based parser for JavaScript and TypeScript files.
    
    Uses pattern matching to extract functions, classes, and imports.
    Not as accurate as tree-sitter but works without native dependencies.
    """

    def __init__(self, lang: str = "javascript"):
        self._lang = lang

    @property
    def language(self) -> str:
        return self._lang

    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse JS/TS source into structured components."""
        result = ParseResult(
            file_path=file_path,
            language=self.language,
            raw_content=content,
        )

        lines = content.split("\n")

        try:
            result.functions = self._extract_functions(content, lines)
            result.classes = self._extract_classes(content, lines)
            result.imports = self._extract_imports(content)
        except Exception as e:
            logger.warning(f"Parse error in {file_path}: {e}")
            result.error = str(e)

        return result

    def _extract_functions(self, content: str, lines: list[str]) -> list[FunctionDef]:
        """Extract function declarations and arrow functions."""
        functions = []

        # Standard function declarations
        for match in RE_FUNCTION.finditer(content):
            name = match.group(1)
            params_str = match.group(2).strip()
            params = [p.strip().split(":")[0].strip() for p in params_str.split(",") if p.strip()]
            line_num = content[:match.start()].count("\n") + 1

            functions.append(FunctionDef(
                name=name,
                start_line=line_num,
                end_line=self._find_block_end(lines, line_num - 1),
                params=params,
            ))

        # Const/arrow functions
        for match in RE_CONST_FUNC.finditer(content):
            name = match.group(1)
            line_num = content[:match.start()].count("\n") + 1

            functions.append(FunctionDef(
                name=name,
                start_line=line_num,
                end_line=self._find_block_end(lines, line_num - 1),
                params=[],
            ))

        return functions

    def _extract_classes(self, content: str, lines: list[str]) -> list[ClassDef]:
        """Extract class declarations with methods."""
        classes = []

        for match in RE_CLASS.finditer(content):
            name = match.group(1)
            base = match.group(2)
            line_num = content[:match.start()].count("\n") + 1
            end_line = self._find_block_end(lines, line_num - 1)

            # Find methods within the class body
            class_body = "\n".join(lines[line_num:end_line])
            methods = [m.group(1) for m in RE_METHOD.finditer(class_body)
                       if m.group(1) != "constructor"]

            classes.append(ClassDef(
                name=name,
                start_line=line_num,
                end_line=end_line,
                methods=["constructor"] + methods if "constructor" in class_body else methods,
                bases=[base] if base else [],
            ))

        return classes

    def _extract_imports(self, content: str) -> list[str]:
        """Extract import/require statements."""
        imports = set()

        for match in RE_IMPORT_FROM.finditer(content):
            imp = match.group(1) or match.group(2)
            if imp:
                imports.add(imp)

        for match in RE_IMPORT_SIDE.finditer(content):
            imports.add(match.group(1))

        return sorted(imports)

    @staticmethod
    def _find_block_end(lines: list[str], start_idx: int) -> int:
        """Find the end of a brace-delimited block (rough heuristic)."""
        depth = 0
        started = False

        for i in range(start_idx, min(start_idx + 500, len(lines))):
            for char in lines[i]:
                if char == "{":
                    depth += 1
                    started = True
                elif char == "}":
                    depth -= 1

            if started and depth <= 0:
                return i + 1  # 1-indexed

        return min(start_idx + 20, len(lines))
