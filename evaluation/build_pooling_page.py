"""Build the shared pooling-review page from pooling_review.jsonl (issue #4).

Embeds questions, current labels, the blind candidate rows (in their shuffled order) and the
full body text of every candidate node into evaluation/pooling_review_page/index.html. Nothing
about models, scores or ranks is embedded, so review stays blind. Publish the output as an
Artifact with capabilities {db, user, downloads, sample}; decisions live in its `decisions`
collection, Claude-drafted suggestions in `drafts` (one document per question, never labels on
their own), and decisions come back with evaluation/import_pooling_decisions.py.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from legal_kg.models import fingerprint  # noqa: E402

PAGE_DIR = ROOT / 'evaluation' / 'pooling_review_page'
ALLOWED_ROW_FIELDS = {'q', 'n'}


def read_jsonl(path):
    return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines() if s.strip()]


def doc_id(question_id, node_id):
    """db document id for one (question, node) pair; reversible, valid db path segment."""
    return question_id + '~' + node_id.replace('/', ':').replace('%', '+')


def parse_doc_id(value):
    question_id, _, node = value.partition('~')
    if not question_id or not node:
        raise ValueError(f'Not a pooling decision id: {value!r}')
    return question_id, node.replace(':', '/').replace('+', '%')


def _header(embedding_text, prefix):
    line = next((s for s in embedding_text.splitlines() if s.startswith(prefix)), '')
    return line[len(prefix):].strip()


def page_data(questions, rows, nodes):
    """Everything the page needs, and nothing that would reveal which model proposed a node."""
    wanted = {r['node_id'] for r in rows}
    missing = wanted - set(nodes)
    if missing:
        raise ValueError(f'Candidate nodes missing from node_texts: {sorted(missing)[:3]}')
    by_id = {q['question_id']: q for q in questions}
    unknown = {r['question_id'] for r in rows} - set(by_id)
    if unknown:
        raise ValueError(f'Pooling rows name unknown questions: {sorted(unknown)[:3]}')
    data = {
        'source_hash': fingerprint(rows),
        'questions': [{
            'id': q['question_id'], 'split': q['split'], 'type': q['type'], 'question': q['question'],
            'rubric': q['answer_rubric'], 'answerable': q['answerable'],
            'groups': [{'primary': g['primary_node_id'], 'quote': g['evidence_quote'],
                        'short': nodes[g['primary_node_id']]['label'] + ' ' + _header(
                            nodes[g['primary_node_id']]['embedding_text'], 'Địa chỉ:').split(' > ')[-1]}
                       for g in q['evidence_groups']],
        } for q in questions],
        'rows': [{'q': r['question_id'], 'n': r['node_id']} for r in rows],
        'nodes': {n: {'label': nodes[n]['label'], 'text': nodes[n]['body_text'],
                      'document': _header(nodes[n]['embedding_text'], 'Văn bản:'),
                      'address': _header(nodes[n]['embedding_text'], 'Địa chỉ:')} for n in sorted(wanted)},
    }
    return data


def render(data, template, draft_js=''):
    # '</' inside a JSON script block would end it early; '<\/' is the same JSON string.
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    if template.count('__DATA__') != 1:
        raise ValueError('Template must contain exactly one __DATA__ placeholder')
    if '</script' in draft_js.lower():
        raise ValueError('draft.js must not contain a closing script tag')
    html = template.replace('__DATA__', payload)
    return html.replace('__DRAFT_JS__', draft_js) if '__DRAFT_JS__' in template else html


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--review', type=Path, default=ROOT / 'evaluation/pooling_review.jsonl')
    parser.add_argument('--questions', type=Path, default=ROOT / 'evaluation/questions.jsonl')
    parser.add_argument('--corpus', type=Path, default=ROOT / 'output/kg/embedding_text/node_texts.jsonl')
    parser.add_argument('--output', type=Path, default=PAGE_DIR / 'index.html')
    args = parser.parse_args(argv)
    nodes = {r['node_id']: r for r in read_jsonl(args.corpus)}
    data = page_data(read_jsonl(args.questions), read_jsonl(args.review), nodes)
    html = render(data, (PAGE_DIR / 'template.html').read_text(encoding='utf-8'),
                  (PAGE_DIR / 'draft.js').read_text(encoding='utf-8'))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding='utf-8', newline='\n')
    print(json.dumps({'output': str(args.output), 'rows': len(data['rows']), 'nodes': len(data['nodes']),
                      'questions': len(data['questions']), 'mb': round(len(html.encode()) / 2**20, 2)}, indent=2))


if __name__ == '__main__':
    main()
