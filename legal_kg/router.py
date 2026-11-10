"""Route explicit legal addresses ("điểm b khoản 1 Điều 112 BLLĐ 2019") straight to KG nodes.

Rule-based and offline: document names come from the same title/alias/number keys as
TitleIndex, the address is parsed with regular expressions and resolved along CONTAINS
edges. Anything ambiguous or unresolved returns an empty list so the caller falls back
to dense retrieval; the router never guesses a document.
"""
from __future__ import annotations

from collections import defaultdict
import re
import unicodedata

from .models import GraphPayload
from .titles import normalize_title, title_properties

_UNIT = re.compile(r"(?P<kind>[đd]ieu|khoan|[đd]iem)\s+(?P<number>\d+[a-z]?|[a-zđ])(?![\w])")


def _strip_marks_keep_d(text: str) -> str:
    """Casefold and drop accents but keep 'đ', which numbers points (điểm đ ≠ điểm d)."""
    text = unicodedata.normalize("NFD", text.casefold())
    return unicodedata.normalize("NFC", "".join(c for c in text if unicodedata.category(c) != "Mn"))


def _bounded(key: str) -> re.Pattern:
    return re.compile(r"(?<![\w/])" + re.escape(key) + r"(?![\w/])")


class DirectRouter:
    def __init__(self, graph: GraphPayload):
        graph.validate()
        self.labels = {n.id: n.label for n in graph.nodes}
        self.numbers = {n.id: n.properties.get("number") for n in graph.nodes}
        self.children = defaultdict(list)
        for edge in graph.edges:
            if edge.type == "CONTAINS":
                self.children[edge.source].append(edge.target)
        self.articles = {}
        documents = [n for n in graph.nodes if n.label == "LegalDocument"]
        for node in graph.nodes:
            if node.label == "Article":
                self.articles[(node.properties["document_id"], node.properties["number"])] = node.id
        keys = defaultdict(set)
        for doc in documents:
            for key in title_properties(doc.properties)["search_title_keys"]:
                keys[key].add(doc.id)
            number = normalize_title(doc.properties["document_number"])
            core = "/".join(number.split("/")[:2])  # 145/2020/nd-cp -> 145/2020
            keys[core].add(doc.id)
            bare = re.sub(r"\s+\d{4}$", "", normalize_title(doc.properties["title"]))
            keys[bare].add(doc.id)
            if doc.properties.get("short_title"):
                keys[re.sub(r"\s+\d{4}$", "", normalize_title(doc.properties["short_title"]))].add(doc.id)
        # Keys naming several documents (e.g. a bare law name shared by two versions) are unusable.
        self.document_keys = sorted(((k, next(iter(v))) for k, v in keys.items() if len(v) == 1 and k),
                                    key=lambda item: -len(item[0]))
        self._patterns = {k: _bounded(k) for k, _ in self.document_keys}

    def document(self, question: str) -> str | None:
        text = normalize_title(question)
        found = {doc for key, doc in self.document_keys if self._patterns[key].search(text)}
        return next(iter(found)) if len(found) == 1 else None

    def _child(self, parent: str, label: str, number: str) -> str | None:
        matches = [c for c in self.children[parent] if self.labels[c] == label and self.numbers[c] == number]
        return matches[0] if len(matches) == 1 else None

    def route(self, question: str) -> list[str]:
        """Node IDs for every explicit address in the question; [] when unsure."""
        document = self.document(question)
        if document is None:
            return []
        units = defaultdict(list)
        for match in _UNIT.finditer(_strip_marks_keep_d(question)):
            kind = match["kind"].replace("đ", "d")
            units[kind].append(match["number"])
        articles = list(dict.fromkeys(units["dieu"]))
        if not articles:
            return []
        if len(articles) > 1:
            # Several articles: return each article; clause/point attachment would be a guess.
            found = [self.articles.get((document, number)) for number in articles]
            return [node for node in found if node]
        article = self.articles.get((document, articles[0]))
        if article is None:
            return []
        clauses, points = list(dict.fromkeys(units["khoan"])), list(dict.fromkeys(units["diem"]))
        if len(clauses) != 1:
            return [article]
        clause = self._child(article, "Clause", clauses[0])
        if clause is None:
            return [article]
        if len(points) != 1:
            return [clause]
        return [self._child(clause, "Point", points[0]) or clause]
