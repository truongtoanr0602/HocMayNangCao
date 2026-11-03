"""Optional, curated title aliases. Build the index once and reuse it for lookups."""
from collections import defaultdict
import re
import unicodedata

from .models import GraphPayload


def normalize_title(title: str) -> str:
    title = unicodedata.normalize("NFD", title.casefold().replace("đ", "d"))
    title = "".join(c for c in title if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", title).strip()


def title_properties(row: dict) -> dict:
    short = row.get("short_title")
    if short is not None and not isinstance(short, str):
        raise ValueError("short_title must be a string or null")
    short = short.strip() or None if short is not None else None
    title = row["title"]
    query_title = short or title
    keys = {normalize_title(value) for value in (title, short, row.get("document_number")) if value}
    return {"short_title": short, "query_title": query_title, "title_key": normalize_title(title),
            "query_title_key": normalize_title(query_title), "search_title_keys": sorted(keys)}


class TitleIndex:
    """Exact title/alias/number lookup; ambiguous aliases return all matching documents."""

    def __init__(self, graph: GraphPayload):
        graph.validate()
        self._documents = defaultdict(list)
        self._chunks = defaultdict(list)
        for node in graph.nodes:
            if node.label == "LegalDocument":
                keys = title_properties(node.properties)["search_title_keys"]
                for key in keys:
                    self._documents[key].append(node)
            elif node.label == "Chunk":
                self._chunks[node.properties["document_id"]].append(node.id)

    def lookup(self, title: str) -> list[dict]:
        return [{"document_id": n.id, "title": n.properties["title"],
                 "short_title": n.properties.get("short_title"),
                 "query_title": n.properties.get("query_title", n.properties["title"]),
                 "chunk_ids": sorted(self._chunks[n.id])}
                for n in sorted(self._documents.get(normalize_title(title), []), key=lambda n: n.id)]
