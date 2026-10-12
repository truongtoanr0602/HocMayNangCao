from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json


LABELS = {"LegalDocument", "Part", "Chapter", "Section", "Article", "Appendix", "Table", "Chunk"}
EDGE_TYPES = {"CONTAINS", "HAS_CHUNK"}
SCHEMA_VERSION = "structural-kg-v1"
CHILD_LABELS = {
    "LegalDocument": LABELS - {"LegalDocument", "Chunk"},
    "Part": {"Chapter", "Section", "Article", "Table"},
    "Chapter": {"Section", "Article", "Table"},
    "Section": {"Article", "Table"},
    "Article": {"Table"}, "Appendix": {"Table"}, "Table": set(),
}


def _validate_properties(node: Node) -> None:
    props = node.properties
    required = {"document_id"}
    if node.label == "LegalDocument":
        required |= {"title", "document_number", "document_type", "source_file"}
    elif node.label == "Chunk":
        required |= {"text", "source_file", "chunk_type", "processing_version"}
        if props.get("metadata_mode") not in {"legacy", "explicit_path"}:
            raise ValueError("Invalid or missing metadata_mode")
        start, end = props.get("paragraph_start"), props.get("paragraph_end")
        if type(start) is not int or type(end) is not int or not 1 <= start <= end:
            raise ValueError("Invalid chunk source block range")
        for key in ("chunk_index", "article_chunk_index", "page_start", "page_end"):
            value = props.get(key)
            if value is not None and (type(value) is not int or value < 1):
                raise ValueError(f"Invalid {key}")
        for key in ("clause_ids", "point_ids"):
            values = props.get(key)
            if not isinstance(values, list) or not all(isinstance(v, str) and v for v in values):
                raise ValueError(f"Invalid {key}")
    else:
        required |= {"number"}
        if not isinstance(props.get("title"), str):
            raise ValueError("Missing structure title")
    for key in required:
        if not isinstance(props.get(key), str) or not props[key].strip():
            raise ValueError(f"Missing or empty {key} in {node.label}")


def fingerprint(value) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Node:
    id: str
    label: str
    properties: dict


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    type: str


@dataclass(frozen=True)
class GraphPayload:
    source_hash: str
    nodes: tuple[Node, ...]
    edges: tuple[Edge, ...]
    warnings: tuple[str, ...] = ()
    schema_version: str = SCHEMA_VERSION

    @property
    def graph_hash(self) -> str:
        return fingerprint(self._body())

    def _body(self) -> dict:
        return asdict(self)

    def to_dict(self) -> dict:
        return json.loads(json.dumps({**self._body(), "graph_hash": self.graph_hash}, ensure_ascii=False))

    @classmethod
    def from_dict(cls, value: dict) -> GraphPayload:
        try:
            graph = cls(
                source_hash=value["source_hash"],
                nodes=tuple(Node(**n) for n in value["nodes"]),
                edges=tuple(Edge(**e) for e in value["edges"]),
                warnings=tuple(value["warnings"]), schema_version=value["schema_version"],
            )
            graph.validate()
            if value["graph_hash"] != graph.graph_hash:
                raise ValueError("Graph integrity check failed; rebuild from source JSONL")
            return graph
        except (KeyError, TypeError, AttributeError) as exc:
            raise ValueError("Invalid graph payload") from exc

    def validate(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("Unsupported graph schema version")
        if not isinstance(self.source_hash, str) or len(self.source_hash) != 64 or any(
            c not in "0123456789abcdef" for c in self.source_hash
        ):
            raise ValueError("Invalid source hash")
        if not self.nodes or not all(isinstance(w, str) for w in self.warnings):
            raise ValueError("Empty graph or invalid warnings")
        nodes = {}
        for node in self.nodes:
            if not isinstance(node.id, str) or not node.id or node.id in nodes or node.label not in LABELS:
                raise ValueError("Duplicate/invalid node ID or label")
            if not isinstance(node.properties, dict):
                raise ValueError("Node properties must be an object")
            _validate_properties(node)
            for key, item in node.properties.items():
                if key in {"id", "snapshot_id"} or not isinstance(key, str):
                    raise ValueError("Reserved or invalid property key")
                scalar = lambda x: x is None or type(x) in (str, int, float, bool)
                if not scalar(item) and not (
                    isinstance(item, list) and all(type(x) is str for x in item)
                ):
                    raise ValueError(f"Unsupported Neo4j property: {key}")
            nodes[node.id] = node
        parents = {}
        seen_edges = set()
        for edge in self.edges:
            key = (edge.source, edge.target, edge.type)
            if key in seen_edges or edge.source not in nodes or edge.target not in nodes or edge.type not in EDGE_TYPES:
                raise ValueError("Duplicate edge, missing endpoint or invalid relationship type")
            seen_edges.add(key)
            source, target = nodes[edge.source], nodes[edge.target]
            if source.label == "Chunk" or target.label == "LegalDocument":
                raise ValueError("Invalid structure relationship")
            if (edge.type == "HAS_CHUNK") != (target.label == "Chunk"):
                raise ValueError("Relationship domain/range mismatch")
            if edge.type == "CONTAINS" and target.label not in CHILD_LABELS[source.label]:
                raise ValueError("Invalid structure hierarchy")
            if edge.target in parents:
                raise ValueError("Node has more than one parent")
            parents[edge.target] = edge.source
        for node in self.nodes:
            visited = set()
            current = node.id
            while nodes[current].label != "LegalDocument":
                if current in visited or current not in parents:
                    raise ValueError("Cycle or orphan in graph")
                visited.add(current)
                current = parents[current]
            if node.properties["document_id"] != current or nodes[current].properties["document_id"] != current:
                raise ValueError("Node document_id does not match its document root")
            if node.label == "Chunk" and node.properties["source_file"] != nodes[current].properties["source_file"]:
                raise ValueError("Chunk source_file does not match its document root")
        # Also checks non-finite numbers and serializability.
        fingerprint(self._body())
