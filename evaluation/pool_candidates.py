"""Collect blind pooling candidates for label review. No model calls, no scores.

Input: pool.json files written by `python -m legal_kg.embedding_benchmark --pool-only`
(top-10 node IDs per question, alphabetical, one file per model and split). Output:
evaluation/pooling_review.jsonl (one row per question/node not yet labelled) and a
Markdown sheet for reviewers. Rows never say which model proposed a node; order is
shuffled with a fixed seed. Existing decisions are kept when the script is re-run.

Reviewers fill `decision` ("relevant" / "not_relevant") and, for relevant nodes, the
`group_index` it answers and an `evidence_quote` copied verbatim from the node text.
"""
import argparse
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from legal_kg.models import fingerprint  # noqa: E402

REVIEW = ROOT / 'evaluation' / 'pooling_review.jsonl'
EXCERPT = 1500


def read_jsonl(path):
    return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines() if s.strip()]


def collect(questions, pools, nodes, existing):
    """Rows for every pooled node outside acceptable_node_ids; keeps earlier decisions."""
    by_question = {}
    for pool in pools:
        for qid, node_ids in pool['nodes'].items():
            by_question.setdefault(qid, set()).update(node_ids)
    rows = []
    for q in questions:
        labelled = {n for g in q['evidence_groups'] for n in g['acceptable_node_ids']}
        candidates = sorted(by_question.get(q['question_id'], set()) - labelled)
        random.Random(fingerprint([q['question_id'], candidates])).shuffle(candidates)
        for node_id in candidates:
            previous = existing.get((q['question_id'], node_id), {})
            node = nodes[node_id]
            rows.append({'question_id': q['question_id'], 'split': q['split'], 'type': q['type'],
                         'question': q['question'], 'node_id': node_id, 'label': node['label'],
                         'node_text': node['body_text'][:EXCERPT],
                         'node_text_truncated': len(node['body_text']) > EXCERPT,
                         'decision': previous.get('decision'), 'group_index': previous.get('group_index'),
                         'evidence_quote': previous.get('evidence_quote'),
                         'reviewer_note': previous.get('reviewer_note')})
    return rows


def render(rows, questions):
    by_id = {q['question_id']: q for q in questions}
    lines = ['# Duyệt pooling mù', '',
             'Mỗi dòng là một node do ít nhất một model đưa vào top 10 nhưng chưa có trong nhãn. '
             'Không ghi model hay điểm. Ghi quyết định vào `pooling_review.jsonl` '
             '(`decision`: `relevant`/`not_relevant`; với `relevant` cần `group_index` và '
             '`evidence_quote` chép nguyên văn từ nội dung node).', '']
    current = None
    for row in rows:
        if row['question_id'] != current:
            current = row['question_id']
            q = by_id[current]
            lines += [f"## {current} — {q['split']} — {q['type']}", '', q['question'], '']
            for index, group in enumerate(q['evidence_groups']):
                lines += [f"Nhóm {index} (nhãn hiện tại): `{group['primary_node_id']}`", '']
        status = row['decision'] or 'chưa duyệt'
        lines += [f"- [{status}] `{row['node_id']}` ({row['label']})", '',
                  '  > ' + row['node_text'].replace('\n', '\n  > ') + (' …' if row['node_text_truncated'] else ''), '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('pools', type=Path, nargs='+', help='pool.json files from --pool-only runs')
    parser.add_argument('--corpus', type=Path, default=ROOT / 'output/kg/embedding_text/node_texts.jsonl')
    parser.add_argument('--questions', type=Path, default=ROOT / 'evaluation/questions.jsonl')
    args = parser.parse_args()
    questions = read_jsonl(args.questions)
    nodes = {r['node_id']: r for r in read_jsonl(args.corpus)}
    pools = [json.loads(p.read_text(encoding='utf-8')) for p in args.pools]
    by_split = {}
    for q in questions:
        by_split.setdefault(q['split'], []).append(q)
    for pool in pools:
        if pool['question_set_hash'] != fingerprint(by_split[pool['split']]):
            raise SystemExit(f"Pool for split {pool['split']} was made from different questions")
    existing = {(r['question_id'], r['node_id']): r for r in read_jsonl(REVIEW)} if REVIEW.exists() else {}
    rows = collect(questions, pools, nodes, existing)
    REVIEW.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')
    (ROOT / 'evaluation' / 'pooling_review.md').write_text(render(rows, questions), encoding='utf-8')
    pending = sum(r['decision'] is None for r in rows)
    print(json.dumps({'rows': len(rows), 'pending': pending, 'pools': len(pools)}, indent=2))


if __name__ == '__main__':
    main()
