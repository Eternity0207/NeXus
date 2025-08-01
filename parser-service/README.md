# Parser Service

AST parsing and code structure extraction service.

## Responsibilities

- Parse source files into Abstract Syntax Trees
- Extract functions, classes, imports, and dependencies
- Support multiple languages (Python, JS, TS)
- Produce `file.parsed` events to Kafka

## Tech Stack

- Python 3.11+
- tree-sitter (multi-language AST parsing)
- Kafka (event consumption/production)

## Kafka

- **Consumes**: `repo.ingested`
- **Produces**: `file.parsed`

## Running

```bash
cd parser-service
pip install -r requirements.txt
python -m app.main
```
