"""Neo4j database client with connection pooling and query helpers."""

from __future__ import annotations

import logging
from typing import Optional, Any

from neo4j import GraphDatabase, Driver, Session

from app.config import get_settings

logger = logging.getLogger("graph-service")
settings = get_settings()

_driver: Optional[Driver] = None


def get_driver() -> Driver:
    """Get or create the Neo4j driver (connection pool)."""
    global _driver
    if _driver is None:
        try:
            _driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_username, settings.neo4j_password),
                max_connection_pool_size=20,
            )
            # Verify connectivity
            _driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {settings.neo4j_uri}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    return _driver


def close_driver() -> None:
    """Close the Neo4j driver."""
    global _driver
    if _driver:
        _driver.close()
        _driver = None
        logger.info("Neo4j driver closed")


def run_query(query: str, parameters: Optional[dict] = None) -> list[dict]:
    """Execute a Cypher query and return results as dicts."""
    driver = get_driver()
    with driver.session(database=settings.neo4j_database) as session:
        result = session.run(query, parameters or {})
        return [record.data() for record in result]


def run_write(query: str, parameters: Optional[dict] = None) -> Any:
    """Execute a write Cypher query within a transaction."""
    driver = get_driver()
    with driver.session(database=settings.neo4j_database) as session:
        result = session.execute_write(
            lambda tx: tx.run(query, parameters or {}).consume()
        )
        return result


def init_schema() -> None:
    """Create indexes and constraints for the graph schema.

    Node types:
    - (:File {path, repo_id, language})
    - (:Function {name, file_path, repo_id, start_line, end_line})
    - (:Class {name, file_path, repo_id})
    - (:Module {name, repo_id})

    Edge types:
    - (:File)-[:IMPORTS]->(:File)
    - (:Function)-[:CALLS]->(:Function)
    - (:File)-[:CONTAINS]->(:Function)
    - (:File)-[:CONTAINS]->(:Class)
    - (:Class)-[:HAS_METHOD]->(:Function)
    - (:Class)-[:EXTENDS]->(:Class)
    """
    constraints = [
        "CREATE INDEX file_path IF NOT EXISTS FOR (f:File) ON (f.path, f.repo_id)",
        "CREATE INDEX func_name IF NOT EXISTS FOR (fn:Function) ON (fn.name, fn.repo_id)",
        "CREATE INDEX class_name IF NOT EXISTS FOR (c:Class) ON (c.name, c.repo_id)",
        "CREATE INDEX module_name IF NOT EXISTS FOR (m:Module) ON (m.name, m.repo_id)",
    ]

    for query in constraints:
        try:
            run_write(query)
        except Exception as e:
            logger.debug(f"Schema init (may already exist): {e}")

    logger.info("Neo4j schema initialized")
