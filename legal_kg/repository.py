from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
import math
import re

from .models import GraphPayload
from .titles import normalize_title

EMBEDDED_LABELS = ("Article", "Clause", "Point")
_MODEL_KEY = re.compile(r"[a-z0-9][a-z0-9-]{0,39}")


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
        for name, field in (("kg_query_title", "query_title_key"), ("kg_original_title", "title_key"),
                            ("kg_document_number", "document_number")):
            session.run(f"CREATE INDEX {name} IF NOT EXISTS FOR (n:LegalDocument) "
                        f"ON (n.snapshot_id, n.{field})").consume()
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
                    f"MERGE (a)-[r:{edge_type}]->(b) SET r += row.properties RETURN count(r) AS written",
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
    """Return ancestry, siblings and evidenced relations from one ready snapshot."""
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
            result = dict(record)
            path_ids = [n["id"] for n in result["path"]]
            records = tx.run("""
                MATCH (n:KGNode {snapshot_id: $snapshot_id})-[r:REFERS_TO|GUIDES|DETAILS]-
                      (other:KGNode {snapshot_id: $snapshot_id})
                WHERE n.id IN $node_ids
                RETURN DISTINCT startNode(r).id AS source, endNode(r).id AS target,
                       type(r) AS type, properties(r) AS properties,
                       other{.*, labels: labels(other)} AS related
                """, snapshot_id=snapshot_id, node_ids=path_ids)
            relations, related = {}, {}
            for item in records:
                key = (item["source"], item["target"], item["type"])
                relations[key] = {k: item[k] for k in ("source", "target", "type", "properties")}
                if item["related"]["id"] not in path_ids:
                    related[item["related"]["id"]] = item["related"]
            result["relations"] = [relations[k] for k in sorted(relations)]
            result["related_nodes"] = [related[k] for k in sorted(related)]
            return result
        return session.execute_read(read)


def fetch_by_title(driver, snapshot_id: str, title: str, *, database: str = "neo4j") -> list[dict]:
    """Use exact composite indexes for aliases and original titles in one snapshot."""
    query = """
    MATCH (:KGSnapshot {id: $snapshot_id, state: 'ready'})
    MATCH (d:LegalDocument {snapshot_id: $snapshot_id, query_title_key: $key})
    RETURN d{.*} AS document
    UNION
    MATCH (:KGSnapshot {id: $snapshot_id, state: 'ready'})
    MATCH (d:LegalDocument {snapshot_id: $snapshot_id, title_key: $key})
    RETURN d{.*} AS document
    UNION
    MATCH (:KGSnapshot {id: $snapshot_id, state: 'ready'})
    MATCH (d:LegalDocument {snapshot_id: $snapshot_id, document_number: $number})
    RETURN d{.*} AS document
    """
    with driver.session(database=database) as session:
        return session.execute_read(lambda tx: sorted(
            [dict(record["document"]) for record in tx.run(query, snapshot_id=snapshot_id,
                                                          key=normalize_title(title), number=title.strip().upper())],
            key=lambda item: item["id"]))


def embedding_property(model_key: str) -> str:
    """Per-model node property, e.g. 'e5-small' -> 'embedding_e5_small'.

    Model keys come from a fixed pattern, so the result is safe to place in Cypher text.
    """
    if not isinstance(model_key, str) or not _MODEL_KEY.fullmatch(model_key):
        raise ValueError(f"Invalid embedding model key: {model_key!r}")
    return "embedding_" + model_key.replace("-", "_")


def vector_index_name(model_key: str) -> str:
    return "kg_node_" + embedding_property(model_key)


def _validated_vectors(node_ids, vectors) -> tuple[list[str], list[list[float]], int]:
    ids, rows = list(node_ids), [list(map(float, v)) for v in vectors]
    if not ids or len(ids) != len(rows) or len(set(ids)) != len(ids):
        raise ValueError("Node IDs and vectors must be non-empty, unique and the same length")
    dimension = len(rows[0])
    for row in rows:
        if len(row) != dimension or not all(math.isfinite(x) for x in row) or not any(row):
            raise ValueError("Vectors must share one dimension and be finite and non-zero")
    return ids, rows, dimension


def load_embeddings(driver, snapshot_id: str, node_ids, vectors, *, model_key: str, model_id: str,
                    revision: str, text_version: str, database: str = "neo4j",
                    batch_size: int = 500) -> dict:
    """Write one model's vectors onto Article/Clause/Point nodes of a ready snapshot.

    Re-running overwrites the same property, so loads are idempotent. The vector index
    (cosine) spans every snapshot; queries filter by snapshot_id.
    """
    if type(batch_size) is not int or batch_size < 1:
        raise ValueError("batch_size must be a positive integer")
    ids, rows, dimension = _validated_vectors(node_ids, vectors)
    prop, index = embedding_property(model_key), vector_index_name(model_key)
    with driver.session(database=database) as session:
        existing = session.run("SHOW VECTOR INDEXES YIELD name, options WHERE name = $name RETURN options",
                               name=index).single()
        if existing is not None:
            config = existing["options"]["indexConfig"]
            if config.get("vector.dimensions") != dimension:
                raise LoadError(f"Index {index} has dimension {config.get('vector.dimensions')}, not {dimension}")
        else:
            # Dimension is a validated int and names come from embedding_property; OPTIONS needs literals.
            session.run(f"CREATE VECTOR INDEX {index} IF NOT EXISTS FOR (n:KGNode) ON (n.{prop}) "
                        f"OPTIONS {{indexConfig: {{`vector.dimensions`: {dimension}, "
                        "`vector.similarity_function`: 'cosine'}}").consume()

        def write(tx):
            ready = tx.run("MATCH (s:KGSnapshot {id: $id, state: 'ready'}) RETURN s.id AS id", id=snapshot_id).single()
            if ready is None:
                raise LoadError(f"Snapshot is not loaded and ready: {snapshot_id}")
            for offset in range(0, len(ids), batch_size):
                batch = [{"id": i, "vector": v} for i, v in zip(ids[offset:offset + batch_size],
                                                                 rows[offset:offset + batch_size])]
                record = tx.run(
                    "UNWIND $rows AS row MATCH (n:KGNode {snapshot_id: $snapshot_id, id: row.id}) "
                    "WHERE n:Article OR n:Clause OR n:Point "
                    f"SET n.{prop} = row.vector, n.{prop}_model = $model_id, n.{prop}_revision = $revision, "
                    f"n.{prop}_text_version = $text_version RETURN count(n) AS written",
                    rows=batch, snapshot_id=snapshot_id, model_id=model_id, revision=revision,
                    text_version=text_version).single()
                if record is None or record["written"] != len(batch):
                    raise LoadError(f"Some embedding targets are missing or not Article/Clause/Point "
                                    f"(batch at {offset})")
            tx.run(f"MATCH (s:KGSnapshot {{id: $id}}) SET s.{prop}_info = $value", id=snapshot_id,
                   value=f"{model_id}@{revision};{text_version};dim={dimension}").consume()

        session.execute_write(write)
        session.run("CALL db.awaitIndex($name, 300)", name=index).consume()
    return {"snapshot_id": snapshot_id, "model_key": model_key, "property": prop, "index": index,
            "dimension": dimension, "nodes": len(ids)}


def vector_search(driver, snapshot_id: str, model_key: str, vector, k: int = 10, *,
                  database: str = "neo4j", overfetch: int = 10) -> list[dict]:
    """Approximate top-k within one snapshot.

    The index covers all snapshots, so it is queried for more neighbours than needed and
    filtered; the fetch grows until k nodes of this snapshot are found or nothing is left.
    Neo4j reports cosine scores rescaled to [0, 1] as (1 + cos) / 2. overfetch=10 measured
    0.975 mean top-10 overlap with exact cosine for vn-embedding on dev (0.94 at 4).
    """
    if type(k) is not int or k < 1:
        raise ValueError("k must be a positive integer")
    query = ("CALL db.index.vector.queryNodes($index, $fetch, $vector) YIELD node, score "
             "WHERE node.snapshot_id = $snapshot_id RETURN node.id AS id, score ORDER BY score DESC, id")
    index, values = vector_index_name(model_key), [float(x) for x in vector]
    fetch = k * overfetch
    with driver.session(database=database) as session:
        total = session.run(f"MATCH (n:KGNode) WHERE n.{embedding_property(model_key)} IS NOT NULL "
                            "RETURN count(n) AS c").single()["c"]
        while True:
            hits = session.run(query, index=index, fetch=fetch, vector=values, snapshot_id=snapshot_id).data()
            if len(hits) >= k or fetch >= total:
                return hits[:k]
            fetch = min(fetch * 4, total)
