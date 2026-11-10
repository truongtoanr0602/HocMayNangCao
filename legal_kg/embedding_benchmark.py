"""Offline development benchmark of node text embeddings; no Neo4j writes."""
from __future__ import annotations

import argparse
from collections import Counter
import importlib.metadata
import json
from pathlib import Path
import sys
import time

import numpy as np

from .models import fingerprint
# Scoring lives in retrieval_eval so every pipeline is scored by the same code.
from .retrieval_eval import evaluate, per_question_values, read_jsonl, write_json

# key: (Hugging Face model ID, document prefix, query prefix). Prefixes follow each model card:
# E5 needs passage:/query:, BGE-M3 and its Vietnamese fine-tune take raw text.
MODELS = {
    'minilm': ('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', '', ''),
    'e5-small': ('intfloat/multilingual-e5-small', 'passage: ', 'query: '),
    'e5-base': ('intfloat/multilingual-e5-base', 'passage: ', 'query: '),
    'bge-m3': ('BAAI/bge-m3', '', ''),
    'vn-embedding': ('AITeamVN/Vietnamese_Embedding', '', ''),
}
# BAAI/bge-m3 publishes only pytorch_model.bin on its main branch (safetensors exist only in
# third-party PRs). It is allowed as an exception: pinned to the resolved commit and loaded by
# transformers through torch.load(weights_only=True), which refuses arbitrary pickled objects.
PICKLE_WEIGHTS_ALLOWED = {'bge-m3'}
MAX_TOKENS = 8192
POLICY = 'full-text-token-windows-weighted-normalized-mean-v1'
BATCHING = 'length-sorted-token-budget-v1'


def plan_batches(lengths, batch_size, max_batch_tokens):
    """Group window indices by length so padding and peak memory stay bounded.

    A batch never exceeds batch_size items or max_batch_tokens padded tokens; a single
    window longer than the token budget still forms its own batch. Order is deterministic,
    which keeps checkpoint resumption valid.
    """
    if batch_size < 1 or max_batch_tokens < 1:
        raise ValueError('Invalid batch configuration')
    batches, current, longest = [], [], 0
    for index in sorted(range(len(lengths)), key=lambda i: (lengths[i], i)):
        widest = max(longest, lengths[index])
        if current and (len(current) >= batch_size or widest * (len(current) + 1) > max_batch_tokens):
            batches.append(current)
            current, widest = [], lengths[index]
        current.append(index)
        longest = widest
    if current:
        batches.append(current)
    return batches


def window_features(tokenizer, ids):
    # Both supported BERT/XLM-R tokenizers use one opening and one closing token.
    # Transformers 5 no longer exposes prepare_for_model on TokenizersBackend.
    special = tokenizer.encode('', add_special_tokens=True)
    if len(special) != 2 or tokenizer.num_special_tokens_to_add(pair=False) != 2:
        raise ValueError('Unsupported special-token template')
    wrapped = [special[0], *ids, special[1]]
    result = {'input_ids': wrapped, 'attention_mask': [1]*len(wrapped)}
    if 'token_type_ids' in tokenizer.model_input_names:
        result['token_type_ids'] = [0]*len(wrapped)
    return result


def token_windows(ids, budget, overlap):
    if budget <= 0 or not 0 <= overlap < budget or not ids:
        raise ValueError('Invalid token window configuration or empty input')
    windows = []
    start = 0
    covered = 0
    while start < len(ids):
        end = min(start + budget, len(ids))
        windows.append((ids[start:end], end - covered))
        covered = end
        if end == len(ids):
            break
        start = end - overlap
    return windows


def pool_vectors(vectors, weights):
    result = np.average(vectors, axis=0, weights=weights)
    norm = np.linalg.norm(result)
    if not np.isfinite(norm) or norm <= 0:
        raise ValueError('Invalid pooled embedding')
    return result / norm


def peak_rss_mb():
    """Peak resident memory of this process in MB, or None when the platform hides it."""
    try:
        if sys.platform == 'win32':
            import ctypes
            from ctypes import wintypes

            class Counters(ctypes.Structure):
                _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD),
                            ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
                            ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
                            ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                            ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                            ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t)]
            counters = Counters()
            counters.cb = ctypes.sizeof(Counters)
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            # Declare types: the default int return would truncate the 64-bit process handle.
            kernel32.GetCurrentProcess.restype = wintypes.HANDLE
            kernel32.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
            kernel32.K32GetProcessMemoryInfo.restype = wintypes.BOOL
            if not kernel32.K32GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
                return None
            return counters.PeakWorkingSetSize / 2**20
        import resource
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return peak / 2**20 if sys.platform == 'darwin' else peak / 2**10
    except Exception:
        return None


def check_frozen(path, questions, model):
    """Test scoring is allowed only through a configuration frozen on dev (see evaluation/README)."""
    if path is None or not Path(path).exists():
        raise ValueError('Test split needs --frozen-config written after dev selection')
    frozen = json.loads(Path(path).read_text(encoding='utf-8'))
    if frozen.get('test_question_hash') != fingerprint(questions):
        raise ValueError('Test questions differ from the frozen configuration')
    if model not in frozen.get('models', []):
        raise ValueError(f'Model {model} is not part of the frozen configuration')
    return frozen


def record_test_run(base, model):
    """Count test runs per model so the report can state how often test was touched."""
    log_path = base / 'test_runs.json'
    log = json.loads(log_path.read_text(encoding='utf-8')) if log_path.exists() else {}
    log[model] = log.get(model, 0) + 1
    write_json(log_path, log)
    return log[model]


def run(args):
    import torch
    from sentence_transformers import SentenceTransformer
    from huggingface_hub import snapshot_download

    torch.set_num_threads(args.threads)
    if args.device == 'cuda' and not torch.cuda.is_available():
        raise ValueError('--device cuda requested but no CUDA GPU is available')
    # Full float32 on every device so CPU and GPU runs differ only by kernel rounding.
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.manual_seed(0)
    records = read_jsonl(args.corpus)
    questions = read_jsonl(args.questions)
    splits = {q['split'] for q in questions}
    if not questions or len(splits) != 1 or not splits <= {'dev', 'test'}:
        raise ValueError('Question file must hold exactly one split: dev or test')
    split = splits.pop()
    pinned_revision = None
    if split == 'test' and not args.pool_only:
        # Raises unless the configuration was frozen on dev for exactly this test file and model.
        frozen = check_frozen(args.frozen_config, questions, args.model)
        # Test must use the exact weights chosen on dev, even if the hub has moved on since.
        pinned_revision = frozen.get('revisions', {}).get(args.model, {}).get('revision')
    if len({q['question_id'] for q in questions}) != len(questions):
        raise ValueError('Duplicate question IDs')
    ids = [r['node_id'] for r in records]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate candidate IDs')
    if len({(r['snapshot_id'], r['graph_hash']) for r in records}) != 1:
        raise ValueError('Mixed graph snapshots')
    for r in records:
        if fingerprint(r['embedding_text']) != r['embedding_text_hash']:
            raise ValueError('Corpus text hash mismatch')
    for q in questions:
        if (q['snapshot_id'],q['graph_hash']) != (records[0]['snapshot_id'],records[0]['graph_hash']):
            raise ValueError('Question/corpus snapshot mismatch')
        for g in q['evidence_groups']:
            if not set(g['acceptable_node_ids']) <= set(ids):
                raise ValueError('Missing evidence node')

    model_id, doc_prefix, query_prefix = MODELS[args.model]
    started = time.perf_counter()
    # Resolve and pin the downloaded revision; do not execute remote model code.
    patterns = ['*.json', '*.safetensors', '*.txt', 'tokenizer.model', 'sentencepiece.bpe.model']
    if args.model in PICKLE_WEIGHTS_ALLOWED:
        if tuple(int(x) for x in torch.__version__.split('+')[0].split('.')[:2]) < (2, 6):
            raise ValueError('Loading .bin weights needs torch>=2.6 (weights_only loading)')
        patterns.append('pytorch_model.bin')
    model_path = snapshot_download(model_id, revision=pinned_revision, allow_patterns=patterns,
                                   ignore_patterns=['onnx/*', 'openvino/*', '*.py'])
    revision = Path(model_path).name
    if pinned_revision and revision != pinned_revision:
        raise ValueError(f'Resolved revision {revision} differs from frozen {pinned_revision}')
    weights_format = ('safetensors' if any(Path(model_path).glob('*.safetensors'))
                      else 'pytorch_model.bin (weights_only)')
    model = SentenceTransformer(model_path, device=args.device, trust_remote_code=False)
    model.eval()
    load_seconds = time.perf_counter()-started
    # sentence-transformers renamed this method in 5.x; support both names.
    dimension = (getattr(model, 'get_embedding_dimension', None) or model.get_sentence_embedding_dimension)()
    tokenizer = model.tokenizer
    prefix_ids = tokenizer.encode(doc_prefix, add_special_tokens=False) if doc_prefix else []
    # Native window of each model (from its sentence-transformers config), capped at 8192 tokens.
    limit = min(int(model.max_seq_length), args.max_seq or MAX_TOKENS, MAX_TOKENS)
    budget = limit - tokenizer.num_special_tokens_to_add(pair=False) - len(prefix_ids)
    overlap = min(args.overlap, budget-1)
    config = {'model_id': model_id, 'revision': revision, 'weights_format': weights_format,
              'max_seq_length': limit,
              'payload_budget': budget, 'overlap': overlap, 'doc_prefix': doc_prefix,
              'query_prefix': query_prefix, 'policy': POLICY, 'batching': BATCHING,
              'embedding_version': records[0].get('embedding_version'), 'candidate_ids': ids,
              'content_hashes': [r['embedding_text_hash'] for r in records],
              'graph_hash': records[0]['graph_hash'], 'snapshot_id': records[0]['snapshot_id'],
              'device': args.device, 'gpu': torch.cuda.get_device_name(0) if args.device == 'cuda' else None,
              'threads': args.threads, 'batch_size': args.batch_size,
              'versions': {p: importlib.metadata.version(p) for p in ['torch','transformers','sentence-transformers','numpy']}}
    cache_key = fingerprint(config)
    destination = args.output / args.model
    destination.mkdir(parents=True, exist_ok=True)
    vector_path = destination / 'node_vectors.npy'
    manifest_path = destination / 'manifest.json'
    cache_hit = (vector_path.exists() and manifest_path.exists()
                 and json.loads(manifest_path.read_text(encoding='utf-8'))['cache_key'] == cache_key)
    if args.require_cache and not cache_hit:
        # Explain which settings differ so the environment can be fixed before anything is encoded.
        stored = (json.loads(manifest_path.read_text(encoding='utf-8')).get('config', {})
                  if manifest_path.exists() else {})
        differing = sorted(k for k in set(config) | set(stored) if config.get(k) != stored.get(k))
        raise ValueError(f'--require-cache: no cached node vectors for this configuration; differing: {differing}')
    if cache_hit:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        vectors = np.load(vector_path, allow_pickle=False)
        if vectors.shape != (len(ids), dimension) or not np.isfinite(vectors).all():
            raise ValueError('Invalid cached embeddings')
        if not np.allclose(np.linalg.norm(vectors,axis=1),1,atol=1e-4):
            raise ValueError('Cached vectors are not normalized')
        print('Using validated node cache', flush=True)
    else:
        work = []
        counts, lengths = [], []
        for i, r in enumerate(records):
            tokens = tokenizer.encode(r['embedding_text'], add_special_tokens=False, truncation=False, verbose=False)
            windows = token_windows(tokens, budget, overlap)
            counts.append(len(windows)); lengths.append(len(tokens))
            for chunk, weight in windows:
                features = window_features(tokenizer, prefix_ids+chunk)
                if len(features['input_ids']) > limit:
                    raise ValueError('Window exceeds model token limit')
                work.append((i, weight, features))
        print(f'{args.model}: {len(ids)} nodes, {len(work)} windows, max={max(lengths)} tokens; encoding on CPU', flush=True)
        sums = np.zeros((len(ids),dimension),dtype=np.float32)
        batches = plan_batches([len(x[2]['input_ids']) for x in work], args.batch_size, args.max_batch_tokens)
        start_batch = 0
        checkpoint_path = destination / 'checkpoint.npz'
        if checkpoint_path.exists():
            with np.load(checkpoint_path,allow_pickle=False) as checkpoint:
                # Only resume a checkpoint made with the same config and the same batch plan.
                if (str(checkpoint['cache_key']) == cache_key and 'next_batch' in checkpoint
                        and int(checkpoint['batch_count']) == len(batches)):
                    sums = checkpoint['sums'].copy(); start_batch=int(checkpoint['next_batch'])
        begin = time.perf_counter()
        windows_done = sum(len(b) for b in batches[:start_batch])
        last_report = time.perf_counter()
        for number in range(start_batch, len(batches)):
            batch = [work[j] for j in batches[number]]
            features = tokenizer.pad([x[2] for x in batch], padding=True, return_tensors='pt')
            features = {k: v.to(args.device) for k, v in features.items()}
            with torch.inference_mode():
                encoded = model(features)['sentence_embedding']
                encoded = torch.nn.functional.normalize(encoded,p=2,dim=1).cpu().numpy()
            if not np.isfinite(encoded).all():
                raise ValueError('Model returned nonfinite vectors')
            for (i,weight,_),vector in zip(batch,encoded):
                sums[i] += vector*weight
            windows_done += len(batch)
            if number == start_batch or time.perf_counter()-last_report > 60 or number == len(batches)-1:
                last_report = time.perf_counter()
                print(f'{args.model}: {windows_done}/{len(work)} windows, batch {number+1}/{len(batches)}; '
                      f'{time.perf_counter()-begin:.0f}s this session; peak RSS {peak_rss_mb() or 0:.0f} MB',flush=True)
                temp = checkpoint_path.with_suffix('.tmp')
                with temp.open('wb') as f:
                    np.savez(f,sums=sums,next_batch=number+1,batch_count=len(batches),cache_key=cache_key)
                temp.replace(checkpoint_path)
        start_index = start_batch
        norms = np.linalg.norm(sums,axis=1,keepdims=True)
        if not np.isfinite(norms).all() or np.any(norms<=0):
            raise ValueError('Invalid node pooling output')
        vectors = sums/norms
        with vector_path.with_suffix('.tmp').open('wb') as f:
            np.save(f,vectors,allow_pickle=False)
        vector_path.with_suffix('.tmp').replace(vector_path)
        manifest = {'cache_key':cache_key,'config':config,'dimension':vectors.shape[1],
                    'window_count':len(work),'multiwindow_nodes':sum(c>1 for c in counts),
                    'max_content_tokens':max(lengths),'node_window_counts':counts,
                    'encode_seconds_this_session':time.perf_counter()-begin,
                    'resumed_from_batch':start_index,'batch_count':len(batches),
                    'max_batch_tokens':args.max_batch_tokens}
        write_json(manifest_path,manifest)

    query_texts = [query_prefix+q['question'] for q in questions]
    if any(len(tokenizer.encode(text,add_special_tokens=True,truncation=False,verbose=False))>limit for text in query_texts):
        raise ValueError('Question exceeds token limit; refusing silent truncation')
    begin = time.perf_counter()
    query_vectors = model.encode(query_texts,batch_size=args.batch_size,normalize_embeddings=True,
                                 convert_to_numpy=True,show_progress_bar=False)
    if query_vectors.shape != (len(questions),vectors.shape[1]) or not np.isfinite(query_vectors).all():
        raise ValueError('Invalid query embeddings')
    query_seconds = time.perf_counter()-begin
    # Dev results sit next to the node cache; test and pooling outputs get their own folders.
    if args.pool_only:
        result_dir = args.output / 'pool' / split / args.model
    elif split == 'test':
        result_dir = args.output / 'test' / args.model
    else:
        result_dir = destination
    result_dir.mkdir(parents=True, exist_ok=True)
    begin = time.perf_counter()
    scores = query_vectors @ vectors.T
    rankings = {}
    predictions = []
    for q, row in zip(questions,scores):
        order = np.argsort(-row,kind='stable')[:args.depth]
        rankings[q['question_id']] = [ids[i] for i in order]
        predictions.append({'question_id':q['question_id'],'question':q['question'],
                            'top_nodes':[{'node_id':ids[i],'score':float(row[i])} for i in order],
                            'answerable_gold':q['answerable'], 'abstention_decision':None})
    search_seconds = time.perf_counter()-begin
    if args.pool_only:
        # Blind pooling input: top-10 node IDs in alphabetical order, no scores, ranks or metrics.
        write_json(result_dir/'pool.json', {'question_set_hash': fingerprint(questions), 'split': split,
                                            'nodes': {qid: sorted(r[:10]) for qid, r in rankings.items()}})
        print(f'Wrote blind pool for {len(questions)} {split} questions to {result_dir}', flush=True)
        return
    # Saved for the Neo4j ANN parity check; question order is stored alongside.
    with (result_dir/'query_vectors.tmp').open('wb') as f:
        np.save(f,query_vectors.astype(np.float32),allow_pickle=False)
    (result_dir/'query_vectors.tmp').replace(result_dir/'query_vectors.npy')
    write_json(result_dir/'query_ids.json',[q['question_id'] for q in questions])
    metrics = evaluate(questions,rankings)
    metrics['by_type'] = {kind:evaluate([q for q in questions if q['type']==kind],rankings)
                          for kind in sorted({q['type'] for q in questions if q['answerable']})}
    manifest['peak_rss_mb'] = peak_rss_mb()
    if args.device == 'cuda':
        manifest['peak_gpu_mb'] = torch.cuda.max_memory_allocated() / 2**20
    version = records[0].get('embedding_version') or 'node-text-v1'
    report = {'name':args.model if version == 'node-text-v1' else f'{args.model}/{version}',
              'model':args.model,'cache_hit':cache_hit,'cache_key':cache_key,
              'question_set_hash':fingerprint(questions),'candidate_count':len(ids),
              'snapshot_id':records[0]['snapshot_id'],'graph_hash':records[0]['graph_hash'],
              'embedding_version':version,
              'split':split,'question_count':len(questions),'metrics':metrics,
              'per_question_group_recall_at_5':per_question_values(questions,rankings),
              'ranking_depth':args.depth,
              'load_seconds':load_seconds,'query_encode_seconds':query_seconds,'search_seconds':search_seconds,
              'manifest':manifest,'unanswerable_policy':'threshold chosen on dev by legal_kg.retrieval_eval',
              'notes':['Labels are reviewed by the project team, not legal experts.',
                       'Exact cosine offline, not Neo4j ANN.',
                       'Native window limits differ; compare complete configurations.']}
    if split == 'test':
        report['test_run_number'] = record_test_run(args.output / 'test', args.model)
    write_json(result_dir/'results.json',report)
    write_json(result_dir/'predictions.json',predictions)
    print(json.dumps({'model':args.model,'split':split,'metrics':metrics['by_k'],
                      'mrr':metrics['single_group_mrr_at_max_k']},indent=2),flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',choices=MODELS,required=True)
    parser.add_argument('--corpus',type=Path,default=Path('output/kg/embedding_text/node_texts.jsonl'))
    parser.add_argument('--questions',type=Path,default=Path('evaluation/dev.jsonl'))
    parser.add_argument('--output',type=Path,default=Path('output/kg/embedding_benchmark'))
    parser.add_argument('--batch-size',type=int,default=16)
    parser.add_argument('--threads',type=int,default=4)
    parser.add_argument('--device',choices=['cpu','cuda'],default='cpu',
                        help='cuda for a GPU (e.g. Colab); vectors stay float32 and the device is part of the cache key')
    parser.add_argument('--overlap',type=int,default=24)
    parser.add_argument('--depth',type=int,default=20,help='Ranked nodes saved per question (>=10)')
    parser.add_argument('--max-batch-tokens',type=int,default=8192,
                        help='Padded tokens per batch; bounds RAM for long-context models')
    parser.add_argument('--pool-only',action='store_true',
                        help='Write blind top-10 node IDs (no scores/metrics) for label pooling; any split')
    parser.add_argument('--require-cache',action='store_true',
                        help='Fail instead of re-encoding nodes when the cached vectors do not match')
    parser.add_argument('--frozen-config',type=Path,default=Path('evaluation/frozen_config.json'),
                        help='Required to score the test split')
    parser.add_argument('--max-seq',type=int,default=None,
                        help=f'Lower the window below the model limit (never above {MAX_TOKENS})')
    args = parser.parse_args()
    if (args.batch_size<1 or args.threads<1 or args.overlap<0 or args.depth<10 or args.max_batch_tokens<1
            or (args.max_seq is not None and args.max_seq<16)):
        parser.error('Invalid numeric options')
    run(args)


if __name__=='__main__':
    main()
