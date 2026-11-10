"""Merge pooling decisions from the shared review page back into pooling_review.jsonl (issue #4).

Accepts any mix of: the page's export (pooling_review_export.json, {"rows": [...]}), a JSON list
or JSONL of decision documents (as read from the artifact's `decisions` collection, with or
without an `id` field). Every decision is validated with the same rules build_questions applies
(verbatim quote, valid group, no relevant node for an unanswerable question) before the file
is rewritten. "flag_question" decisions are not labels: the row stays pending and the
question is reported so its SEED can be fixed. Later updates win when sources overlap.
Claude drafts (the page's `drafts` collection) are never read here: only decisions a person
made or confirmed become labels, and each keeps `label_source` (human / draft_confirmed).
"""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'evaluation' / 'pooling_review.jsonl'
FLAG_NOTE = '[CẦN SỬA CÂU HỎI] '


def _module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'evaluation' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_records(path):
    """Whole-file JSON (export object or list) first, otherwise JSONL."""
    text = path.read_text(encoding='utf-8-sig').strip()
    if not text:
        return []
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        value = [json.loads(s) for s in text.splitlines() if s.strip()]
    if isinstance(value, dict):
        value = value.get('rows', value.get('documents', value.get('docs', [value])))
    # Store dumps may wrap each body as {"id": ..., "data": {...}}.
    return [{**r['data'], 'id': r.get('id')} if isinstance(r.get('data'), dict) else r for r in value]


def normalise(record, parse_doc_id):
    """One decision as {question_id, node_id, decision, group_index, evidence_quote, reviewer_note, updated_at}."""
    question_id, node_id = record.get('question_id'), record.get('node_id')
    if (not question_id or not node_id) and record.get('id'):
        question_id, node_id = parse_doc_id(record['id'])
    if not question_id or not node_id:
        raise ValueError(f'Decision without question/node: {record}')
    source = record.get('source') or 'human'
    if source not in {'human', 'draft_confirmed'}:
        raise ValueError(f'Unknown decision source {source!r} for {question_id} / {node_id}')
    return {'question_id': question_id, 'node_id': node_id, 'decision': record.get('decision'),
            'group_index': record.get('group_index'), 'evidence_quote': record.get('evidence_quote'),
            'reviewer_note': record.get('reviewer_note'), 'updated_at': record.get('updated_at') or '',
            'source': source, 'draft_suggestion': record.get('draft_suggestion')}


def merge(rows, decisions):
    """Overlay decisions on review rows; returns (rows, flagged question ids, unknown pairs)."""
    by_key = {(r['question_id'], r['node_id']): r for r in rows}
    latest = {}
    for d in decisions:
        key = (d['question_id'], d['node_id'])
        if key not in latest or (d['updated_at'] or '') >= (latest[key]['updated_at'] or ''):
            latest[key] = d
    flagged, unknown = set(), []
    merged = copy.deepcopy(rows)
    index = {(r['question_id'], r['node_id']): r for r in merged}
    for key, d in latest.items():
        if key not in by_key:
            unknown.append(key)
            continue
        row = index[key]
        note = d['reviewer_note']
        # Where the label came from: a person's own call, or a person confirming a Claude draft.
        row.update({'label_source': (d.get('source') or 'human') if d['decision'] else None,
                    'draft_suggestion': d.get('draft_suggestion')})
        if d['decision'] == 'flag_question':
            flagged.add(key[0])
            row.update({'decision': None, 'group_index': None, 'evidence_quote': None,
                        'reviewer_note': FLAG_NOTE + (note or '')})
        elif d['decision'] in (None, 'relevant', 'not_relevant'):
            row.update({'decision': d['decision'], 'reviewer_note': note,
                        'group_index': d['group_index'] if d['decision'] == 'relevant' else None,
                        'evidence_quote': d['evidence_quote'] if d['decision'] == 'relevant' else None})
        else:
            raise ValueError(f"Unknown decision {d['decision']!r} for {key}")
    return merged, sorted(flagged), unknown


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('sources', type=Path, nargs='+', help='Exports or decision dumps to merge')
    parser.add_argument('--dry-run', action='store_true', help='Validate and report without writing')
    args = parser.parse_args(argv)
    page = _module('build_pooling_page')
    build = _module('build_questions')
    rows = page.read_jsonl(REVIEW)
    decisions = [normalise(r, page.parse_doc_id) for path in args.sources for r in read_records(path)]
    merged, flagged, unknown = merge(rows, decisions)
    questions = page.read_jsonl(ROOT / 'evaluation' / 'questions.jsonl')
    nodes = {r['node_id']: r for r in page.read_jsonl(ROOT / 'output/kg/embedding_text/node_texts.jsonl')}
    # Same checks the question build applies; raises on any invalid decision.
    label_version, pending = build.apply_pooling(copy.deepcopy(questions), nodes, merged)
    if not args.dry_run:
        REVIEW.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in merged),
                          encoding='utf-8', newline='\n')
    print(json.dumps({'decisions_read': len(decisions), 'rows': len(merged), 'pending': pending,
                      'label_version_if_built': label_version, 'flagged_questions': flagged,
                      'unknown_pairs': [list(k) for k in unknown][:10], 'written': not args.dry_run},
                     ensure_ascii=False, indent=2))
    if flagged:
        print('Câu được báo cần sửa: sửa SEEDS trong build_questions.py rồi chạy lại pool_candidates.py.')


if __name__ == '__main__':
    main()
