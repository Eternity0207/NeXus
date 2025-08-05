"""Graph builder — constructs dependency graphs from parsed file events."""

from __future__ import annotations

import logging
from typing import Optional

from app.neo4j_client import run_write, run_query

logger = logging.getLogger("graph-service")


def build_file_graph(event: dict) -> dict:
    """Build graph nodes and edges from a file.parsed event.

    Creates:
    - File node
    - Function nodes + CONTAINS edges
    - Class nodes + CONTAINS edges + HAS_METHOD edges
    - IMPORTS edges (file-to-file)
    - EXTENDS edges (class inheritance)

    Args:
        event: file.parsed Kafka event payload.

    Returns:
        Summary dict with counts of nodes/edges added.
    """
    repo_id = event.get("repo_id", "")
    file_path = event.get("file_path", "")
    language = event.get("language", "")
    functions = event.get("functions", [])
    classes = event.get("classes", [])
    imports = event.get("imports", [])

    nodes_added = 0
    edges_added = 0

    # ── Create File node ─────────────────────────────────────────────────
    run_write(
        """
        MERGE (f:File {path: $path, repo_id: $repo_id})
        SET f.language = $language,
            f.function_count = $func_count,
            f.class_count = $class_count,
            f.import_count = $import_count
        """,
        {
            "path": file_path,
            "repo_id": repo_id,
            "language": language,
            "func_count": len(functions),
            "class_count": len(classes),
            "import_count": len(imports),
        },
    )
    nodes_added += 1

    # ── Create Function nodes ────────────────────────────────────────────
    for func in functions:
        run_write(
            """
            MERGE (fn:Function {name: $name, file_path: $file_path, repo_id: $repo_id})
            SET fn.start_line = $start_line,
                fn.end_line = $end_line,
                fn.params = $params,
                fn.docstring = $docstring
            WITH fn
            MATCH (f:File {path: $file_path, repo_id: $repo_id})
            MERGE (f)-[:CONTAINS]->(fn)
            """,
            {
                "name": func.get("name", ""),
                "file_path": file_path,
                "repo_id": repo_id,
                "start_line": func.get("start_line", 0),
                "end_line": func.get("end_line", 0),
                "params": func.get("params", []),
                "docstring": func.get("docstring", ""),
            },
        )
        nodes_added += 1
        edges_added += 1  # CONTAINS edge

    # ── Create Class nodes ───────────────────────────────────────────────
    for cls in classes:
        class_name = cls.get("name", "")
        methods = cls.get("methods", [])
        bases = cls.get("bases", [])

        run_write(
            """
            MERGE (c:Class {name: $name, repo_id: $repo_id})
            SET c.file_path = $file_path,
                c.methods = $methods
            WITH c
            MATCH (f:File {path: $file_path, repo_id: $repo_id})
            MERGE (f)-[:CONTAINS]->(c)
            """,
            {
                "name": class_name,
                "file_path": file_path,
                "repo_id": repo_id,
                "methods": methods,
            },
        )
        nodes_added += 1
        edges_added += 1  # CONTAINS edge

        # Link methods to class
        for method_name in methods:
            run_write(
                """
                MATCH (c:Class {name: $class_name, repo_id: $repo_id})
                MATCH (fn:Function {name: $method_name, file_path: $file_path, repo_id: $repo_id})
                MERGE (c)-[:HAS_METHOD]->(fn)
                """,
                {
                    "class_name": class_name,
                    "method_name": method_name,
                    "file_path": file_path,
                    "repo_id": repo_id,
                },
            )
            edges_added += 1

        # Create EXTENDS edges for inheritance
        for base in bases:
            run_write(
                """
                MATCH (c:Class {name: $name, repo_id: $repo_id})
                MERGE (base:Class {name: $base_name, repo_id: $repo_id})
                MERGE (c)-[:EXTENDS]->(base)
                """,
                {
                    "name": class_name,
                    "base_name": base,
                    "repo_id": repo_id,
                },
            )
            edges_added += 1

    # ── Create IMPORTS edges ─────────────────────────────────────────────
    for imp in imports:
        # Convert import path to a file-level node reference
        module_path = _import_to_file_path(imp, language)

        run_write(
            """
            MATCH (f:File {path: $file_path, repo_id: $repo_id})
            MERGE (m:Module {name: $module_name, repo_id: $repo_id})
            MERGE (f)-[:IMPORTS]->(m)
            """,
            {
                "file_path": file_path,
                "repo_id": repo_id,
                "module_name": imp,
            },
        )
        edges_added += 1

    summary = {
        "nodes_added": nodes_added,
        "edges_added": edges_added,
        "node_types": {
            "File": 1,
            "Function": len(functions),
            "Class": len(classes),
        },
    }

    logger.info(
        f"Built graph for {file_path}: "
        f"{nodes_added} nodes, {edges_added} edges"
    )

    return summary


def _import_to_file_path(import_name: str, language: str) -> str:
    """Convert an import statement to an approximate file path.

    Examples:
        'os.path' → 'os/path.py'
        'react' → 'react'
        'app.models' → 'app/models.py'
    """
    if language == "python":
        return import_name.replace(".", "/") + ".py"
    return import_name
