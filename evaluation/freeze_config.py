"""Freeze the configuration chosen on dev before the single test run (ticket #11).

Reads the dev comparison report(s) for abstention thresholds, the question summary for
label/test hashes, and each run's manifest for the pinned model revision. Refuses to
overwrite an existing freeze unless --replace is given, and records that it was replaced.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from legal_kg.models import fingerprint  # noqa: E402

OUTPUT = ROOT / 'evaluation' / 'frozen_config.json'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--selected-model', required=True, help='Model M chosen on dev')
    parser.add_argument('--models', nargs='+', required=True, help='Every model reported on test')
    parser.add_argument('--text-version', required=True, choices=['node-text-v1', 'node-text-v2'])
    parser.add_argument('--pipeline', required=True, choices=['p1', 'p2', 'router-p2'])
    parser.add_argument('--comparisons', type=Path, nargs='+', required=True,
                        help='Dev comparison JSON files from legal_kg.retrieval_eval (thresholds)')
    parser.add_argument('--benchmark', type=Path, default=ROOT / 'output/kg/embedding_benchmark')
    parser.add_argument('--rationale', required=True, help='Why M, text version and pipeline were chosen')
    parser.add_argument('--replace', action='store_true')
    args = parser.parse_args(argv)
    if args.selected_model not in args.models:
        parser.error('--selected-model must be one of --models')
    previous = json.loads(OUTPUT.read_text(encoding='utf-8')) if OUTPUT.exists() else None
    if previous and not args.replace:
        raise SystemExit(f'{OUTPUT} already exists; pass --replace only if dev decisions really changed')
    summary = json.loads((ROOT / 'evaluation' / 'summary.json').read_text(encoding='utf-8'))
    if summary.get('label_version') != 'v2' or summary.get('pooling_pending'):
        raise SystemExit('Labels must be v2 (pooling fully reviewed) before freezing')
    test = [json.loads(s) for s in (ROOT / 'evaluation' / 'test.jsonl').read_text(encoding='utf-8').splitlines() if s.strip()]
    if fingerprint(test) != summary['test_question_hash']:
        raise SystemExit('evaluation/test.jsonl does not match summary.json; rebuild questions first')
    thresholds = {}
    for path in args.comparisons:
        report = json.loads(path.read_text(encoding='utf-8'))
        if report['question_set_hash'] != summary['dev_question_hash']:
            raise SystemExit(f'{path} was computed on different dev questions')
        thresholds.update({name: run['abstention']['threshold'] for name, run in report['runs'].items()})
    revisions = {}
    for model in args.models:
        manifest = json.loads((args.benchmark / model / 'manifest.json').read_text(encoding='utf-8'))
        revisions[model] = {'model_id': manifest['config']['model_id'], 'revision': manifest['config']['revision']}
    frozen = {'frozen_at': datetime.now(timezone.utc).isoformat(), 'selected_model': args.selected_model,
              'models': args.models, 'revisions': revisions, 'text_version': args.text_version,
              'pipeline': args.pipeline, 'abstention_thresholds': thresholds, 'rationale': args.rationale,
              'label_version': summary['label_version'], 'label_hash': summary['label_hash'],
              'dev_question_hash': summary['dev_question_hash'],
              'test_question_hash': summary['test_question_hash'],
              'replaced_previous_freeze': previous['frozen_at'] if previous else None}
    OUTPUT.write_text(json.dumps(frozen, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(OUTPUT)


if __name__ == '__main__':
    main()
