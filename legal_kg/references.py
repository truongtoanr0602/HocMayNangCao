"""Conservative, evidenced legal reference resolution against the loaded corpus.

Rules identify explicit citations, not legal equivalence or validity. Missing or
ambiguous targets remain warnings. Curated ``references`` metadata can supply
addresses for syntax not covered by the rules, with a verbatim source quote.
"""
from collections import defaultdict
from dataclasses import dataclass
import json
import re

from .models import Edge, SEMANTIC_EDGES


REFERENCE_RULES_VERSION = "2"

_NUMBER = re.compile(r"\b\d+/\d{4}/[\wĐđ-]+", re.I)
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_DOC = re.compile(r"(?<!pháp )\b(?:bộ luật|luật|nghị định|thông tư)\b", re.I)
_SELF_DOC = re.compile(r"\b(?:bộ luật|luật|nghị định|thông tư)\s+này\b", re.I)
_DIRECTIVE = re.compile(r"quy định chi tiết|hướng dẫn(?:\s+thi hành)?", re.I)
_HEADING = re.compile(r"^.{0,8}ĐI(?:ỀU|ÊU|ỀN|ỂU)\s+\d[^\n]*(?:\n|$)", re.I)
_NUM_LIST = r"\d+[a-zđ]?(?:\s*(?:,|và)\s*(?:Điều\s+)?\d+[a-zđ]?)*"
_POINT_LIST = r"[a-zđ](?:\s*(?:,|và)\s*[a-zđ])*"
_PROVISION = re.compile(
    rf"\b(?:(?:các\s+)?điểm\s+(?P<points>{_POINT_LIST})\s+)?"
    rf"(?:(?:các\s+)?khoản\s+(?P<clauses>{_NUM_LIST})\s+)?"
    rf"Điều\s+(?P<articles>{_NUM_LIST}|này)\b", re.I)


@dataclass(frozen=True)
class Mention:
    start: int
    end: int
    document: str | None


def _aliases(doc):
    props = doc.properties
    values = {props["title"], props["document_number"]}
    if props.get("short_title"):
        values.add(props["short_title"])
    # Only named laws may omit the year. "Nghị định" alone is never an identity.
    if props["document_type"].casefold() in {"luật", "bộ luật"}:
        values.add(re.sub(r"\s+(?:năm\s+)?(?:19|20)\d{2}$", "", props["title"], flags=re.I))
    return values


def _types(text):
    # An instruction to another authority is not evidence that this unit guides.
    if re.search(r"(?:Chính phủ|Bộ trưởng)\s+(?:quy định chi tiết|hướng dẫn)", text, re.I):
        return {"REFERS_TO"}
    if re.search(r"(?:không|chưa)\s+(?:quy định chi tiết|hướng dẫn)", text, re.I):
        return {"REFERS_TO"}
    if re.search(r"(?:các|những)\s+văn bản\s+(?:quy định chi tiết|hướng dẫn)", text, re.I):
        return {"REFERS_TO"}
    kinds = set()
    if re.search(r"quy định chi tiết", text, re.I):
        kinds.add("DETAILS")
    if re.search(r"hướng dẫn", text, re.I):
        kinds.add("GUIDES")
    return kinds or {"REFERS_TO"}


def resolve_references(rows, nodes, chunk_parents, structural_edges):
    documents = {n.id: n for n in nodes.values() if n.label == "LegalDocument"}
    document_years = {key: _YEAR.findall(node.properties["document_number"])
                      for key, node in documents.items()}
    parents = {target: source for source, target, kind in structural_edges if kind == "CONTAINS"}
    addresses = defaultdict(list)
    for node in nodes.values():
        if node.label not in {"Article", "Clause", "Point"}:
            continue
        coords = {}
        cursor = node
        while cursor.label != "LegalDocument":
            if cursor.label in {"Article", "Clause", "Point"}:
                coords[cursor.label.lower()] = cursor.properties["number"].casefold()
            cursor = nodes[parents[cursor.id]]
        addresses[(node.properties["document_id"], coords.get("article"),
                   coords.get("clause"), coords.get("point"))].append(node.id)
    aliases = defaultdict(set)
    for document in documents.values():
        for alias in _aliases(document):
            aliases[alias.casefold()].add(document.id)
    alias_pattern = re.compile(r"(?<!\w)(?:" + "|".join(
        re.escape(a).replace(r"\ ", r"\s+") for a in sorted(aliases, key=lambda a: (-len(a), a))) + r")(?!\w)", re.I)
    warnings = set()
    evidence = defaultdict(dict)

    def warn(row, message):
        warnings.add(f"Unresolved reference in {row['chunk_id']}: {message}")

    def mentions(text, row):
        found = []
        for match in alias_pattern.finditer(text):
            alias = re.sub(r"\s+", " ", match.group().casefold())
            candidates = set(aliases[alias])
            tail = text[match.end():]
            qualifier = re.match(r"\s+(?:(?:số\s+)?\d+/\d{4}/[\wĐđ-]+|"
                                 r"(?:năm\s+)?(?:19|20)\d{2}|ngày\s+\d+\s+tháng\s+\d+\s+năm\s+\d{4})", tail, re.I)
            identity = match.group() + (qualifier.group() if qualifier else "")
            number = _NUMBER.search(identity)
            years = set(_YEAR.findall(identity))
            if number:
                candidates = {d for d in candidates if documents[d].properties["document_number"].casefold() == number.group().casefold()}
            elif years:
                candidates = {d for d in candidates if years <= set(_YEAR.findall(documents[d].properties["document_number"]))}
            else:
                # A bare law name cannot establish a reference to a future version.
                # Explicit version citations remain authoritative (e.g. amended text).
                source_years = document_years[row["document_id"]]
                if source_years:
                    candidates = {d for d in candidates if not document_years[d]
                                  or int(document_years[d][0]) <= int(source_years[0])}
            document = next(iter(candidates)) if len(candidates) == 1 else None
            if document is None:
                warn(row, identity)
            found.append(Mention(match.start(), match.end() + (len(qualifier.group()) if qualifier else 0), document))
        # Unrecognized numbered documents must not silently bind to the current law.
        for match in _NUMBER.finditer(text):
            if not any(m.start <= match.start() < m.end for m in found):
                warn(row, match.group())
                found.append(Mention(match.start(), match.end(), None))
        return sorted(found, key=lambda m: m.start)

    def resolve(document, article, clause, point, row, citation):
        if document is None:
            return None
        if article is None:
            return document if document in documents else None
        key = (document, article.casefold(), clause.casefold() if clause else None, point.casefold() if point else None)
        candidates = addresses.get(key, [])
        if len(candidates) != 1:
            warn(row, f"{document}: {citation}")
            return None
        return candidates[0]

    def add(source, target, kind, row, quote, method="rule"):
        if source == target:
            return
        item = {"chunk_id": row["chunk_id"], "quote": quote, "method": method}
        evidence[(source, target, kind)][(row["chunk_id"], quote, method)] = item
        # References inside provisions also establish a document-level citation.
        # Preserve the type, orientation and exact evidence of the original edge.
        a, b = nodes[source].properties["document_id"], nodes[target].properties["document_id"]
        if a != b:
            evidence[(a, b, kind)][(row["chunk_id"], quote, method)] = item

    def explicit(row, source):
        references = row.get("references", [])
        if not isinstance(references, list):
            raise ValueError("references must be a list")
        for reference in references:
            if not isinstance(reference, dict) or reference.get("type") not in SEMANTIC_EDGES:
                raise ValueError("Invalid explicit reference type")
            quote = reference.get("evidence")
            if not isinstance(quote, str) or not quote.strip() or quote not in row["text"]:
                raise ValueError("Explicit reference evidence must occur in the chunk")
            endpoints = []
            for field in ("source", "target"):
                address = reference.get(field)
                if field == "source" and address is None:
                    endpoints.append(source)
                    continue
                if not isinstance(address, dict) or not isinstance(address.get("document_id"), str):
                    raise ValueError(f"Invalid reference {field} address")
                if any(address.get(k) is not None and not isinstance(address[k], str) for k in ("article", "clause", "point")):
                    raise ValueError("Reference coordinates must be strings")
                if (address.get("clause") or address.get("point")) and not address.get("article"):
                    raise ValueError("Reference clause/point requires an article")
                endpoint = resolve(address["document_id"], address.get("article"), address.get("clause"), address.get("point"), row, str(address))
                if endpoint is None:
                    warn(row, str(address))
                endpoints.append(endpoint)
            if all(endpoints):
                add(*endpoints, reference["type"], row, quote, "explicit")

    for row in sorted(rows, key=lambda r: r["chunk_id"]):
        source = chunk_parents[row["chunk_id"]]
        # Tables/forms can quote headings; do not treat them as primary provisions.
        if nodes[source].label not in {"LegalDocument", "Article", "Clause", "Point"}:
            continue
        explicit(row, source)
        body = _HEADING.sub("", row["text"], count=1)
        scope = None
        scope_kinds = {"REFERS_TO"}
        scope_quote = None
        for segment in re.split(r"(?<=[.;!?])\s+|(?<=:)\s*\n", body):
            if not segment.strip():
                continue
            refs = list(_PROVISION.finditer(segment))
            docs = mentions(segment, row)
            kinds = _types(segment)
            directive = _DIRECTIVE.search(segment)
            passive = bool(directive and re.search(r"được\s*$", segment[:directive.start()], re.I))
            resolved_refs = []
            for ref in refs:
                following = [m for m in docs if m.start >= ref.end()]
                first_doc = _DOC.search(segment, ref.end())
                unknown_before = False
                if first_doc and not _SELF_DOC.match(segment, first_doc.start()):
                    # A later known law cannot supply the identity of an earlier unknown one.
                    mention = following[0] if following else None
                    unknown_before = not mention or (first_doc.start() < mention.start and not re.fullmatch(
                        r"\s*(?:số\s+)?", segment[first_doc.end():mention.start], re.I))
                if ref["articles"].casefold() == "này":
                    document = row["document_id"]
                elif first_doc and _SELF_DOC.match(segment, first_doc.start()):
                    document = row["document_id"]
                elif unknown_before:
                    warn(row, segment)
                    document = None
                elif following:
                    document = following[0].document
                elif _SELF_DOC.search(segment[ref.end():]):
                    document = row["document_id"]
                elif docs:
                    unique = {m.document for m in docs}
                    document = next(iter(unique)) if len(unique) == 1 else None
                elif _DOC.search(segment[ref.end():]) and not _SELF_DOC.search(segment[ref.end():]):
                    warn(row, segment)
                    document = None
                else:
                    document = scope if scope_quote else row["document_id"]
                articles = re.findall(r"\d+[a-zđ]?", ref["articles"], re.I)
                if ref["articles"].casefold() == "này":
                    articles = [(row.get("article") or {}).get("number")]
                    document = row["document_id"]
                clauses = re.findall(r"\d+[a-zđ]?", ref["clauses"] or "", re.I) or [None]
                points = re.findall(r"\b[a-zđ]\b", ref["points"] or "", re.I) or [None]
                targets = []
                for article in articles:
                    for clause in clauses:
                        for point in points:
                            target = resolve(document, article, clause, point, row, ref.group())
                            if target:
                                targets.append(target)
                resolved_refs.append((ref, targets))
            # A named provision before the predicate is its explicit subject.
            subject = []
            has_object = directive and any(ref.start() > directive.start() for ref, _ in resolved_refs)
            trailing_detail = bool(passive and not has_object and re.search(r"như sau\s*:$", segment, re.I))
            if has_object:
                preceding = [(ref, targets) for ref, targets in resolved_refs if ref.end() <= directive.start()]
                if preceding:
                    subject = preceding[-1][1]
            quote = segment
            inherited = not directive and scope_quote is not None and not docs and not _SELF_DOC.search(segment)
            if inherited:
                kinds = scope_kinds
                # Include both scope and citation, as one verbatim source substring.
                start = row["text"].find(scope_quote)
                end = row["text"].find(segment, start) + len(segment)
                quote = row["text"][start:end]
            for ref, targets in resolved_refs:
                current_kinds = kinds if trailing_detail or not directive or ref.start() > directive.start() else {"REFERS_TO"}
                for target in targets:
                    for origin in (subject if current_kinds != {"REFERS_TO"} else []) or [source]:
                        for kind in current_kinds:
                            a, b = (target, origin) if passive and not trailing_detail and kind != "REFERS_TO" else (origin, target)
                            add(a, b, kind, row, quote)
            if not refs:
                for mention in docs:
                    if mention.document:
                        for kind in kinds:
                            a, b = (mention.document, source) if passive and kind != "REFERS_TO" else (source, mention.document)
                            add(a, b, kind, row, segment)
                if segment.rstrip().endswith(":") and len({m.document for m in docs}) == 1:
                    scope = docs[0].document
                    scope_kinds, scope_quote = kinds, segment
    relations = [Edge(*key, {"evidence_json": json.dumps([items[k] for k in sorted(items)], ensure_ascii=False, sort_keys=True)})
                 for key, items in sorted(evidence.items())]
    return relations, warnings
