"""Pack what the single Colab test run needs (ticket #11) into colab_test_bundle.zip.

The bundle carries the cached dev node vectors and their manifests, so the test run only
encodes the 20 test questions and reuses exactly the node vectors scored on dev
(`--require-cache` refuses to re-encode). Run after `evaluation/freeze_config.py`.
"""
import argparse
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from legal_kg.models import fingerprint  # noqa: E402

BENCHMARK = Path('output/kg/embedding_benchmark')
CORPORA = {BENCHMARK: Path('output/kg/embedding_text/node_texts.jsonl'),
           BENCHMARK / 'text-v2': Path('output/kg/embedding_text_v2/node_texts.jsonl')}


def bundle_files(frozen: dict) -> list[Path]:
    files = sorted(p.relative_to(ROOT) for p in (ROOT / 'legal_kg').glob('*.py'))
    files += [Path('evaluation/test.jsonl'), Path('evaluation/frozen_config.json'), *CORPORA.values()]
    for model in frozen['models']:
        for base in CORPORA:
            manifest = json.loads((ROOT / base / model / 'manifest.json').read_text(encoding='utf-8'))
            if manifest['config'].get('device') != 'cuda':
                raise SystemExit(f'{base / model} was not encoded on the shared GPU environment')
            if manifest['config']['revision'] != frozen['revisions'][model]['revision']:
                raise SystemExit(f'{base / model} revision differs from the frozen configuration')
            files += [base / model / 'manifest.json', base / model / 'node_vectors.npy']
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--output', type=Path, default=ROOT / 'colab_test_bundle.zip')
    args = parser.parse_args(argv)
    frozen = json.loads((ROOT / 'evaluation/frozen_config.json').read_text(encoding='utf-8'))
    test = [json.loads(s) for s in (ROOT / 'evaluation/test.jsonl').read_text(encoding='utf-8').splitlines() if s.strip()]
    if fingerprint(test) != frozen['test_question_hash']:
        raise SystemExit('evaluation/test.jsonl does not match the frozen configuration')
    temporary = args.output.with_suffix('.tmp')
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in bundle_files(frozen):
            archive.write(ROOT / path, path.as_posix())
    temporary.replace(args.output)
    print(f'{args.output} ({args.output.stat().st_size / 2**20:.1f} MB)')


if __name__ == '__main__':
    main()
