from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass

from .models import GraphPayload


class LoadError(RuntimeError):
    pass


@dataclass(frozen=True)
class LoadReport:
    source_hash: str
    graph_hash: str
    node_count: int
    edge_count: int
    chunk_count: int


def load_graph(graph: GraphPayload, driver, *, database: str = "neo4j", batch_size: int = 500,
               allow_legacy_metadata: bool = False) -> LoadReport:
    """One atomic data transaction; batches limit query payload, not commit boundaries.

    IDs are unique within a snapshot. Old snapshots are retained and never deleted.
    Constraints are schema operations performed before the data transaction.
    """
    graph.validate()
    if type(batch_size) is not int or batch_size < 1:
        raise ValueError("batch_size must be a positive integer")
    if any(n.properties.get("metadata_mode") == "legacy" for n in graph.nodes) and not allow_legacy_metadata:
        raise ValueError("Source uses legacy metadata; review warnings then use --allow-legacy-metadata to load a prototype")
    with driver.session(database=database) as session:
        session.run("CREATE CONSTRAINT kg_node_identity IF NOT EXISTS "
                    "FOR (n:KGNode) REQUIRE (n.snapshot_id, n.id) IS UNIQUE").consume()
        session.run("CREATE CONSTRAINT kg_snapshot_identity IF NOT EXISTS "
                    "FOR (s:KGSnapshot) REQUIRE s.id IS UNIQUE").consume()
        return session.execute_write(_write_graph, graph, batch_size)


def _write_graph(tx, graph: GraphPayload, batch_size: int) -> LoadReport:
    phase, ids = "snapshot", []
    try:
        snapshot = tx.run(
            "MERGE (s:KGSnapshot {id: $snapshot_id}) "
            "ON CREATE SET s.graph_hash = $graph_hash, s.state = 'loading', s.schema_version = $schema_version "
            "SET s.lock_token = $graph_hash "
            "RETURN s.graph_hash AS graph_hash",
            snapshot_id=graph.source_hash, graph_hash=graph.graph_hash, schema_version=graph.schema_version,
        ).single()
        if snapshot is None or snapshot["graph_hash"] != graph.graph_hash:
            raise LoadError("Snapshot already contains a different graph; use a separate database")
        by_label = defaultdict(list)
        for node in graph.nodes:
            by_label[node.label].append(asdict(node))
        for label, nodes in sorted(by_label.items()):
            # label comes exclusively from the validated label allowlist.
            for offset in range(0, len(nodes), batch_size):
                batch = nodes[offset:offset + batch_size]
                phase, ids = f"nodes/{label}", [n["id"] for n in batch]
                tx.run(
                    f"UNWIND $nodes AS row MERGE (n:KGNode:{label} "
                    "{snapshot_id: $snapshot_id, id: row.id}) SET n += row.properties",
                    nodes=batch, snapshot_id=graph.source_hash,
                ).consume()
        by_type = defaultdict(list)
        for edge in graph.edges:
            by_type[edge.type].append(asdict(edge))
        for edge_type, edges in sorted(by_type.items()):
            for offset in range(0, len(edges), batch_size):
                batch = edges[offset:offset + batch_size]
                phase, ids = f"edges/{edge_type}", [e["target"] for e in batch]
                record = tx.run(
                    "UNWIND $edges AS row "
                    "MATCH (a:KGNode {snapshot_id: $snapshot_id, id: row.source}) "
                    "MATCH (b:KGNode {snapshot_id: $snapshot_id, id: row.target}) "
                    f"MERGE (a)-[r:{edge_type}]->(b) RETURN count(r) AS written",
                    edges=batch, snapshot_id=graph.source_hash, edge_type=edge_type,
                ).single()
                if record is None or record["written"] != len(batch):
                    raise LoadError(f"Missing relationship endpoints in {phase}: {ids}")
        tx.run("MATCH (s:KGSnapshot {id: $snapshot_id}) SET s.state = 'ready', "
               "s.node_count = $node_count, s.edge_count = $edge_count, s.warnings = $warnings",
               snapshot_id=graph.source_hash, node_count=len(graph.nodes), edge_count=len(graph.edges),
               warnings=list(graph.warnings)).consume()
        return LoadReport(graph.source_hash, graph.graph_hash, len(graph.nodes), len(graph.edges),
                          sum(n.label == "Chunk" for n in graph.nodes))
    except LoadError:
        raise
    except Exception as exc:
        raise LoadError(f"Load rolled back at {phase}; IDs: {ids}; cause: {type(exc).__name__}") from exc


def fetch_context(driver, snapshot_id: str, chunk_id: str, *, database: str = "neo4j") -> dict:
    """Return ancestry and sibling chunks only from an explicitly selected ready snapshot."""
    query = """
    MATCH (s:KGSnapshot {id: $snapshot_id, state: 'ready'})
    MATCH path=(d:LegalDocument)-[:CONTAINS*0..8]->(parent:KGNode)-[:HAS_CHUNK]->(c:Chunk)
    WHERE c.id = $chunk_id AND all(n IN nodes(path) WHERE n.snapshot_id = $snapshot_id)
    MATCH (parent)-[:HAS_CHUNK]->(sibling:Chunk {snapshot_id: $snapshot_id})
    WITH s, path, c, sibling
    ORDER BY coalesce(sibling.article_chunk_index, sibling.chunk_index, 0), sibling.id
    RETURN c{.*} AS chunk,
           [n IN nodes(path)[..-1] | n{.*, labels: labels(n)}] AS path,
           collect(sibling{.*}) AS siblings, s.warnings AS warnings
    """
    with driver.session(database=database) as session:
        def read(tx):
            record = tx.run(query, snapshot_id=snapshot_id, chunk_id=chunk_id).single()
            if record is None:
                raise ValueError(f"Chunk not found in ready snapshot: {chunk_id}")
            return dict(record)
        return session.execute_read(read)
