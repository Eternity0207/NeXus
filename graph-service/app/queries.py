"""Graph query APIs — read operations against the Neo4j graph."""

from __future__ import annotations

import logging
from typing import Optional

from app.neo4j_client import run_query

logger = logging.getLogger("graph-service")


def get_repo_graph(
    repo_id: str,
    depth: int = 2,
    node_type: str = "all",
) -> dict:
    """Get the dependency graph for a repository.

    Args:
        repo_id: Repository identifier.
        depth: Max traversal depth for relationships.
        node_type: Filter by node type (file, function, class, all).

    Returns:
        Graph data with nodes and edges arrays.
    """
    # Build label filter
    label_filter = ""
    if node_type == "file":
        label_filter = "AND (n:File)"
    elif node_type == "function":
        label_filter = "AND (n:Function)"
    elif node_type == "class":
        label_filter = "AND (n:Class)"

    # Get nodes
    nodes = run_query(
        f"""
        MATCH (n)
        WHERE n.repo_id = $repo_id {label_filter}
        RETURN 
            elementId(n) as id,
            labels(n) as labels,
            properties(n) as properties
        LIMIT 500
        """,
        {"repo_id": repo_id},
    )

    # Get edges
    edges = run_query(
        """
        MATCH (a)-[r]->(b)
        WHERE a.repo_id = $repo_id AND b.repo_id = $repo_id
        RETURN 
            elementId(a) as source,
            elementId(b) as target,
            type(r) as relationship
        LIMIT 1000
        """,
        {"repo_id": repo_id},
    )

    return {
        "repo_id": repo_id,
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
    }


def get_node_details(repo_id: str, node_id: str) -> Optional[dict]:
    """Get details for a specific node including its neighbors."""
    results = run_query(
        """
        MATCH (n)
        WHERE elementId(n) = $node_id AND n.repo_id = $repo_id
        OPTIONAL MATCH (n)-[r]-(neighbor)
        RETURN 
            elementId(n) as id,
            labels(n) as labels,
            properties(n) as properties,
            collect(DISTINCT {
                id: elementId(neighbor),
                labels: labels(neighbor),
                name: neighbor.name,
                relationship: type(r)
            }) as neighbors
        """,
        {"repo_id": repo_id, "node_id": node_id},
    )

    return results[0] if results else None


def get_file_dependencies(repo_id: str, file_path: str) -> dict:
    """Get what a file imports and what imports it."""
    imports = run_query(
        """
        MATCH (f:File {path: $path, repo_id: $repo_id})-[:IMPORTS]->(m)
        RETURN m.name as module_name, labels(m) as labels
        """,
        {"path": file_path, "repo_id": repo_id},
    )

    # A file is "imported by" another when the other's IMPORTS edge targets a
    # Module node whose name resolves (roughly) to this file's path. We match
    # on the path stem (drop extension + leading dirs) since import syntax
    # across languages rarely encodes the full repo-relative path.
    from pathlib import PurePosixPath
    stem = PurePosixPath(file_path).with_suffix("").as_posix()
    module_candidates = {
        file_path,
        stem,
        stem.replace("/", "."),
        PurePosixPath(file_path).name,
        PurePosixPath(file_path).stem,
    }

    imported_by = run_query(
        """
        MATCH (other:File)-[:IMPORTS]->(m:Module {repo_id: $repo_id})
        WHERE other.path <> $path AND m.name IN $candidates
        RETURN DISTINCT other.path as file_path
        """,
        {"path": file_path, "candidates": list(module_candidates), "repo_id": repo_id},
    )

    return {
        "file_path": file_path,
        "imports": [r["module_name"] for r in imports],
        "imported_by": [r["file_path"] for r in imported_by],
    }


def get_repo_stats(repo_id: str) -> dict:
    """Get aggregate statistics for a repository's graph."""
    stats = run_query(
        """
        MATCH (n {repo_id: $repo_id})
        WITH labels(n) as node_labels
        UNWIND node_labels as label
        RETURN label, count(*) as count
        ORDER BY count DESC
        """,
        {"repo_id": repo_id},
    )

    edge_stats = run_query(
        """
        MATCH (a {repo_id: $repo_id})-[r]->(b {repo_id: $repo_id})
        RETURN type(r) as type, count(*) as count
        ORDER BY count DESC
        """,
        {"repo_id": repo_id},
    )

    return {
        "repo_id": repo_id,
        "node_counts": {r["label"]: r["count"] for r in stats},
        "edge_counts": {r["type"]: r["count"] for r in edge_stats},
    }
