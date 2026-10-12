from __future__ import annotations

from urllib.parse import quote

from .models import Edge, GraphPayload, Node, fingerprint


LEVELS = {"part": "Part", "chapter": "Chapter", "section": "Section", "article": "Article",
          "appendix": "Appendix", "table": "Table"}
LEGACY_WARNING = (
    "Legacy metadata: structure_path is absent. Appendix/table boundaries and clause/point parentage "
    "are not verified; the graph reflects existing metadata, including possible attachment to the last Article."
)


def _text(value, field: str, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise ValueError(f"Invalid {field}: expected {'a string' if empty else 'a nonempty string'}")
    return value


def _path(row: dict) -> list[dict]:
    explicit = "structure_path" in row
    if explicit:
        path = row["structure_path"]
    else:
        path = []
        for kind in ("part", "chapter", "section", "article"):
            ref = row.get(kind)
            if ref is None:
                continue
            if not isinstance(ref, dict):
                raise ValueError(f"Invalid {kind}: expected a structure object or null")
            path.append({**ref, "type": kind})
    if not isinstance(path, list):
        raise ValueError("structure_path must be a list")
    prior = -1
    appendix = False
    for ref in path:
        if not isinstance(ref, dict) or ref.get("type") not in LEVELS:
            raise ValueError("Invalid structure_path element")
        kind = ref["type"]
        number = _text(ref.get("number"), "structure number")
        if number != number.strip():
            raise ValueError("Structure numbers must not have surrounding whitespace")
        _text(ref.get("title", ""), "structure title", empty=True)
        rank = list(LEVELS).index(kind)
        if rank <= prior or (kind == "appendix" and prior >= 0) or (appendix and kind != "table"):
            raise ValueError("Invalid structure hierarchy; appendix must start a separate document branch")
        prior = rank
        appendix = appendix or kind == "appendix"
    return path


def build_graph(rows: list[dict]) -> GraphPayload:
    """Build from metadata only. Input order does not change IDs or hashes."""
    if not isinstance(rows, list) or not rows or not all(isinstance(r, dict) for r in rows):
        raise ValueError("Expected a nonempty list of chunk objects")
    nodes: dict[str, Node] = {}
    edges: set[tuple[str, str, str]] = set()
    chunks = set()
    warnings = set()

    def add(node: Node) -> None:
        existing = nodes.get(node.id)
        if existing and existing != node:
            raise ValueError(f"Conflicting metadata for {node.id}")
        nodes[node.id] = node

    for row in rows:
        chunk_id = _text(row.get("chunk_id"), "chunk_id")
        if chunk_id in chunks:
            raise ValueError(f"Duplicate chunk_id: {chunk_id}")
        chunks.add(chunk_id)
        document_id = _text(row.get("document_id"), "document_id")
        if document_id != quote(document_id, safe="-_."):
            raise ValueError("document_id must use URL-safe ASCII characters")
        kind = _text(row.get("chunk_type"), "chunk_type")
        text = _text(row.get("text"), "text")
        start, end = row.get("paragraph_start"), row.get("paragraph_end")
        if type(start) is not int or type(end) is not int or not 1 <= start <= end:
            raise ValueError(f"Invalid source block range for {chunk_id}")
        path = _path(row)
        if "structure_path" not in row:
            warnings.add(LEGACY_WARNING)
            if kind in {"article", "clause_group"} and not row.get("article"):
                raise ValueError(f"Article chunk missing article metadata: {chunk_id}")
        if len(text) > 6000:
            warnings.add(f"Chunk {chunk_id} has {len(text)} characters (>6000); review source/chunk boundaries.")
        doc_properties = {key: _text(row.get(key), key) for key in
                          ("title", "document_number", "document_type", "source_file")}
        doc_properties["document_id"] = document_id
        add(Node(document_id, "LegalDocument", doc_properties))
        parent = document_id
        for ref in path:
            node_id = f"{parent}/{ref['type']}-{quote(ref['number'], safe='')}"
            add(Node(node_id, LEVELS[ref["type"]], {
                "number": ref["number"], "title": ref.get("title", ""), "document_id": document_id,
            }))
            edges.add((parent, node_id, "CONTAINS"))
            parent = node_id
        props = {"text": text, "document_id": document_id, "source_file": doc_properties["source_file"],
                 "chunk_type": kind, "paragraph_start": start, "paragraph_end": end,
                 "metadata_mode": "explicit_path" if "structure_path" in row else "legacy"}
        for key in ("chunk_index", "article_chunk_index", "page_start", "page_end"):
            item = row.get(key)
            if item is not None and (type(item) is not int or item < 1):
                raise ValueError(f"Invalid {key} for {chunk_id}")
            props[key] = item
        for key in ("clause_ids", "point_ids"):
            item = row.get(key, [])
            if not isinstance(item, list) or not all(isinstance(x, str) and x for x in item):
                raise ValueError(f"Invalid {key} for {chunk_id}")
            props[key] = list(item)
        props["processing_version"] = _text(row.get("processing_version", "unknown"), "processing_version")
        add(Node(chunk_id, "Chunk", props))
        edges.add((parent, chunk_id, "HAS_CHUNK"))
    graph = GraphPayload(
        source_hash=fingerprint(sorted(rows, key=lambda r: r["chunk_id"])),
        nodes=tuple(sorted(nodes.values(), key=lambda n: n.id)),
        edges=tuple(Edge(*e) for e in sorted(edges)), warnings=tuple(sorted(warnings)),
    )
    graph.validate()
    return graph


def inspect_chunk(graph: GraphPayload, chunk_id: str) -> dict:
    graph.validate()
    nodes = {n.id: n for n in graph.nodes}
    if chunk_id not in nodes or nodes[chunk_id].label != "Chunk":
        raise ValueError(f"Chunk not found: {chunk_id}")
    parents = {e.target: e.source for e in graph.edges}
    path = []
    current = parents[chunk_id]
    while True:
        path.append(nodes[current])
        if current not in parents:
            break
        current = parents[current]
    sibling_ids = {e.target for e in graph.edges if e.type == "HAS_CHUNK" and e.source == parents[chunk_id]}
    siblings = sorted((nodes[n] for n in sibling_ids), key=lambda n: (
        n.properties.get("article_chunk_index") or n.properties.get("chunk_index") or 0, n.id,
    ))
    encode = lambda n: {"id": n.id, "label": n.label, "properties": n.properties}
    return {"source_hash": graph.source_hash, "warnings": list(graph.warnings),
            "chunk": encode(nodes[chunk_id]), "path": [encode(n) for n in reversed(path)],
            "siblings": [encode(n) for n in siblings]}
