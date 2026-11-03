"""Prepare source-backed node texts; does not generate vectors or modify Neo4j."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from urllib.parse import quote

from .models import GraphPayload, fingerprint

VERSION = "node-text-v1"
TYPES = {"Article", "Clause", "Point"}


def merged_spans(spans):
    result = []
    for block, start, end in sorted(set(spans)):
        if result and result[-1][0] == block and start <= result[-1][2]:
            result[-1] = (block, result[-1][1], max(end, result[-1][2]))
        else:
            result.append((block, start, end))
    return result


def reconstruct(blocks, spans):
    spans = list(spans)
    for block, start, end in spans:
        if block not in blocks or not 0 <= start <= end <= len(blocks[block]):
            raise ValueError(f"Invalid source span: {block}/{start}/{end}")
    return "\n".join(blocks[b][s:e] for b, s, e in merged_spans(spans))


def prepare_records(graph, rows, blocks):
    graph_hash = graph.graph_hash
    nodes = {n.id: n for n in graph.nodes}
    mapped = defaultdict(list)
    paths = {}
    if {r['chunk_id'] for r in rows} != {n.id for n in graph.nodes if n.label == 'Chunk'}:
        raise ValueError("Graph/chunk corpus mismatch")
    if len({r['chunk_id'] for r in rows}) != len(rows):
        raise ValueError("Duplicate chunk IDs")
    for row in rows:
        if nodes[row['chunk_id']].properties['text'] != row['text']:
            raise ValueError(f"Graph/chunk text mismatch: {row['chunk_id']}")
        doc = row["document_id"]
        for sp in row["source_spans"]:
            b, s, e = sp["block_number"], sp["start"], sp["end"]
            source = reconstruct(blocks[doc], [(b, s, e)])
            if source != row["text"][sp["chunk_start"]:sp["chunk_end"]]:
                raise ValueError(f"Source mismatch: {row['chunk_id']}")
        cursor = doc
        path = []
        for ref in row["structure_path"]:
            cursor += f"/{ref['type']}-{quote(ref['number'], safe='')}"
            path.append(cursor)
            if cursor not in nodes or nodes[cursor].properties.get("title") != ref["title"]:
                raise ValueError(f"Graph/metadata mismatch: {cursor}")
            if nodes[cursor].label in TYPES:
                mapped[cursor].append(row)
                paths[cursor] = list(path)
    expected = {n.id for n in graph.nodes if n.label in TYPES}
    if set(mapped) != expected:
        raise ValueError("Missing node source rows")
    bodies = {}
    spans_by_node = {}
    for nid, linked in mapped.items():
        doc = nodes[nid].properties["document_id"]
        spans = [(s["block_number"], s["start"], s["end"])
                 for r in linked for s in r["source_spans"]]
        spans_by_node[nid] = merged_spans(spans)
        recovered = reconstruct(blocks[doc], spans)
        body = recovered if nodes[nid].label == "Article" else nodes[nid].properties["title"]
        if not body.strip() or body not in recovered:
            raise ValueError(f"Node body missing from source: {nid}")
        bodies[nid] = body

    direct_children = defaultdict(list)
    for child in mapped:
        direct_children[child.rsplit("/", 1)[0]].append(child)

    def introduction(nid, child_label):
        body = bodies[nid]
        starts = []
        for child in direct_children[nid]:
            if nodes[child].label == child_label:
                position = body.find(bodies[child].splitlines()[0])
                if position >= 0:
                    starts.append(position)
        return body[:min(starts)].strip() if starts else ""

    records = []
    for nid in sorted(mapped):
        node = nodes[nid]
        doc = node.properties["document_id"]
        path = paths[nid]
        article = next(p for p in path if nodes[p].label == "Article")
        context = []
        if node.label != "Article":
            # Remove the article heading: it is already represented in the address.
            intro = introduction(article, "Clause") or introduction(article, "Point")
            if intro:
                context.extend(intro.splitlines()[1:])
        if node.label == "Point":
            clause = next((p for p in path if nodes[p].label == "Clause"), None)
            if clause:
                prefix = introduction(clause, "Point")
                if prefix:
                    context.append(prefix)
        names = {"Part": "Phần", "Chapter": "Chương", "Section": "Mục",
                 "Article": "Điều", "Clause": "Khoản", "Point": "Điểm"}
        address = []
        for p in path:
            ancestor = nodes[p]
            text = f"{names.get(ancestor.label, ancestor.label)} {ancestor.properties['number']}"
            if ancestor.label in {"Part", "Chapter", "Section", "Article"}:
                text += ": " + ancestor.properties["title"]
            address.append(text)
        context_text = "\n".join(context).strip()
        body = bodies[nid]
        text = (f"Văn bản: {nodes[doc].properties['title']}\n"
                f"Số hiệu: {nodes[doc].properties['document_number']}\n"
                f"Địa chỉ: {' > '.join(address)}\n")
        if context_text:
            text += f"Phần dẫn: {context_text}\n"
        text += f"Nội dung:\n{body}"
        records.append({
            "node_id": nid, "label": node.label, "number": node.properties["number"],
            "document_id": doc, "source_file": nodes[doc].properties["source_file"],
            "snapshot_id": graph.source_hash, "graph_hash": graph_hash,
            "embedding_version": VERSION, "embedding_text": text,
            "embedding_text_hash": fingerprint(text), "char_count": len(text),
            "needs_tokenizer_check": True, "over_6000_chars": len(text) > 6000,
            "body_text": body, "context_text": context_text, "path_node_ids": path,
            "source_chunk_ids": sorted({r['chunk_id'] for r in mapped[nid]}),
            # Spans cover the source context used to validate this record, not just body_text.
            "source_spans": [{"block_number": b, "start": s, "end": e}
                             for b, s, e in spans_by_node[nid]],
            "warnings": (["clause_title_excludes_table_rows_if_not_present_in_title"]
                         if node.label == "Clause" else []),
        })
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=Path("output/kg/structural_graph.json"))
    parser.add_argument("--chunks", type=Path, default=Path("output/preprocessed/legal_chunks.jsonl"))
    parser.add_argument("--blocks", type=Path, default=Path("output/preprocessed/intermediate"))
    parser.add_argument("--output", type=Path, default=Path("output/kg/embedding_text"))
    args = parser.parse_args()
    if args.output.resolve() in {args.graph.resolve(), args.chunks.resolve(), args.blocks.resolve()}:
        raise ValueError("Output must be separate from inputs")
    graph = GraphPayload.from_dict(json.loads(args.graph.read_text(encoding="utf-8")))
    rows = [json.loads(line) for line in args.chunks.read_text(encoding="utf-8").splitlines() if line.strip()]
    blocks = {p.name.split('.')[0]: {b['block_number']: b['text'] for b in
              json.loads(p.read_text(encoding="utf-8"))['clean_blocks']}
              for p in args.blocks.glob("*.blocks.json")}
    records = prepare_records(graph, rows, blocks)
    args.output.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
    destination = args.output / "node_texts.jsonl"
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(destination)
    samples = []
    for label in sorted(TYPES):
        candidates = [r for r in records if r['label'] == label]
        selected = [min(candidates, key=lambda r: r['char_count']), max(candidates, key=lambda r: r['char_count'])]
        selected += [next(r for r in candidates if r['document_id'] == doc)
                     for doc in sorted({r['document_id'] for r in candidates})]
        for r in selected:
            if r['node_id'] not in {x['node_id'] for x in samples}:
                samples.append(r)
    (args.output / "samples.json").write_text(json.dumps(samples, ensure_ascii=False, indent=2), encoding="utf-8")
    report = {"snapshot_id": graph.source_hash, "version": VERSION,
              "counts": dict(Counter(r['label'] for r in records)),
              "total": len(records), "empty_texts": sum(not r['embedding_text'].strip() for r in records),
              "over_6000_chars": sum(r['over_6000_chars'] for r in records),
              "max_chars": max(r['char_count'] for r in records), "sample_count": len(samples),
              "vectors_generated": False, "neo4j_modified": False}
    (args.output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
