from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import tempfile

from .build import build_graph, inspect_chunk
from .models import GraphPayload
from .repository import LoadError, fetch_by_title, fetch_context, load_graph
from .titles import TitleIndex


def _write_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=path.parent, suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _read_graph(path: Path) -> GraphPayload:
    return GraphPayload.from_dict(json.loads(path.read_text(encoding="utf-8-sig")))


def _connect(args):
    password = os.environ.get("NEO4J_PASSWORD", "")
    if not password:
        raise ValueError("Set NEO4J_PASSWORD in the process environment before connecting")
    try:
        from neo4j import GraphDatabase
    except ImportError as exc:
        raise ValueError("Install the Neo4j driver: python -m pip install -r requirements.txt") from exc
    driver = GraphDatabase.driver(args.uri, auth=(args.user, password), connection_timeout=10,
                                 max_transaction_retry_time=10)
    try:
        driver.verify_connectivity()
    except Exception:
        driver.close()
        raise
    return driver


def main(argv: list[str] | None = None) -> int:
    # Windows redirected streams can default to cp1252, which cannot encode legal Vietnamese.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Build/inspect/load structural legal KG without an LLM")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="Build graph JSON without Neo4j")
    build.add_argument("--input", type=Path, default=Path("output/preprocessed/legal_chunks.jsonl"))
    build.add_argument("--output", type=Path, default=Path("output/kg/structural_graph.json"))
    inspect = commands.add_parser("inspect", help="Inspect ancestry and sibling chunks offline")
    inspect.add_argument("--input", type=Path, default=Path("output/kg/structural_graph.json"))
    inspect.add_argument("--chunk-id", required=True)
    search = commands.add_parser("search", help="Look up original title, short title or document number offline")
    search.add_argument("--input", type=Path, default=Path("output/kg/structural_graph.json"))
    search.add_argument("--title", required=True)
    load = commands.add_parser("load", help="Load one graph snapshot atomically into Neo4j")
    load.add_argument("--input", type=Path, default=Path("output/kg/structural_graph.json"))
    load.add_argument("--batch-size", type=int, default=500)
    load.add_argument("--allow-legacy-metadata", action="store_true")
    lookup = commands.add_parser("lookup", help="Fetch context from a ready Neo4j snapshot")
    lookup.add_argument("--snapshot", required=True)
    lookup.add_argument("--chunk-id", required=True)
    search_db = commands.add_parser("search-db", help="Use Neo4j title indexes in a ready snapshot")
    search_db.add_argument("--snapshot", required=True)
    search_db.add_argument("--title", required=True)
    for command in (load, lookup, search_db):
        command.add_argument("--uri", default=os.environ.get("NEO4J_URI", "bolt://localhost:7687"))
        command.add_argument("--user", default=os.environ.get("NEO4J_USER", "neo4j"))
        command.add_argument("--database", default=os.environ.get("NEO4J_DATABASE", "neo4j"))
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            if args.input.resolve() == args.output.resolve():
                raise ValueError("Input and output must be different files")
            rows = []
            with args.input.open(encoding="utf-8-sig") as handle:
                for number, line in enumerate(handle, 1):
                    if not line.strip():
                        continue
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"Invalid JSON at {args.input}:{number}") from exc
            graph = build_graph(rows)
            _write_atomic(args.output, graph.to_dict())
            result = {"output": str(args.output), "source_hash": graph.source_hash,
                      "node_count": len(graph.nodes), "edge_count": len(graph.edges),
                      "chunk_count": sum(n.label == "Chunk" for n in graph.nodes), "warnings": list(graph.warnings)}
        elif args.command == "inspect":
            result = inspect_chunk(_read_graph(args.input), args.chunk_id)
        elif args.command == "search":
            result = TitleIndex(_read_graph(args.input)).lookup(args.title)
        elif args.command == "search-db":
            with _connect(args) as driver:
                result = fetch_by_title(driver, args.snapshot, args.title, database=args.database)
        elif args.command == "load":
            graph = _read_graph(args.input)
            # Fail before connecting if input has not been reviewed.
            if not args.allow_legacy_metadata and any(n.properties.get("metadata_mode") == "legacy" for n in graph.nodes):
                raise ValueError("Source uses legacy metadata; inspect graph warnings before using --allow-legacy-metadata")
            with _connect(args) as driver:
                result = asdict(load_graph(graph, driver, database=args.database, batch_size=args.batch_size,
                                           allow_legacy_metadata=args.allow_legacy_metadata))
        else:
            with _connect(args) as driver:
                result = fetch_context(driver, args.snapshot, args.chunk_id, database=args.database)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, LoadError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Neo4j operation failed ({type(exc).__name__}); check URI, credentials and database availability", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
