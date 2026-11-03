"""Offline development benchmark of node text embeddings; no Neo4j writes."""
from __future__ import annotations

import argparse
from collections import Counter
import importlib.metadata
import json
from pathlib import Path
import time

import numpy as np

from .models import fingerprint

MODELS = {
    'minilm': ('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', '', ''),
    'e5-small': ('intfloat/multilingual-e5-small', 'passage: ', 'query: '),
}
POLICY = 'full-text-token-windows-weighted-normalized-mean-v1'


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


def evaluate(questions, rankings, ks=(1, 3, 5, 10)):
    answerable = [q for q in questions if q['answerable']]
    if not answerable:
        raise ValueError('No answerable questions')
    output = {'answerable_questions': len(answerable), 'unanswerable_questions': len(questions)-len(answerable), 'by_k': {}}
    for k in ks:
        recalls, primaries, all_hits = [], [], []
        for q in answerable:
            top = set(rankings[q['question_id']][:k])
            groups = q['evidence_groups']
            hits = [bool(top & set(g['acceptable_node_ids'])) for g in groups]
            recalls.append(sum(hits)/len(groups))
            primaries.append(sum(g['primary_node_id'] in top for g in groups)/len(groups))
            all_hits.append(all(hits))
        output['by_k'][str(k)] = {
            'group_recall_macro': float(np.mean(recalls)),
            'primary_group_recall_macro': float(np.mean(primaries)),
            'all_groups_hit_rate': float(np.mean(all_hits)),
        }
    reciprocal = []
    for q in answerable:
        if len(q['evidence_groups']) == 1:
            acceptable = set(q['evidence_groups'][0]['acceptable_node_ids'])
            reciprocal.append(next((1/rank for rank, nid in enumerate(rankings[q['question_id']][:max(ks)],1)
                                    if nid in acceptable), 0.))
    output['single_group_mrr_at_max_k'] = float(np.mean(reciprocal)) if reciprocal else None
    return output


def read_jsonl(path):
    return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines() if s.strip()]


def write_json(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def run(args):
    import torch
    from sentence_transformers import SentenceTransformer
    from huggingface_hub import snapshot_download

    torch.set_num_threads(args.threads)
    torch.manual_seed(0)
    records = read_jsonl(args.corpus)
    questions = read_jsonl(args.questions)
    if not questions or any(q['split'] != 'dev' for q in questions):
        raise ValueError('This command accepts only development questions')
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
    model_path = snapshot_download(model_id, allow_patterns=['*.json', '*.safetensors', '*.txt',
                                    'tokenizer.model', 'sentencepiece.bpe.model'],
                                   ignore_patterns=['onnx/*', 'openvino/*'])
    revision = Path(model_path).name
    model = SentenceTransformer(model_path, device='cpu', trust_remote_code=False)
    model.eval()
    load_seconds = time.perf_counter()-started
    tokenizer = model.tokenizer
    prefix_ids = tokenizer.encode(doc_prefix, add_special_tokens=False) if doc_prefix else []
    limit = int(model.max_seq_length)
    budget = limit - tokenizer.num_special_tokens_to_add(pair=False) - len(prefix_ids)
    overlap = min(args.overlap, budget-1)
    config = {'model_id': model_id, 'revision': revision, 'max_seq_length': limit,
              'payload_budget': budget, 'overlap': overlap, 'doc_prefix': doc_prefix,
              'query_prefix': query_prefix, 'policy': POLICY, 'candidate_ids': ids,
              'content_hashes': [r['embedding_text_hash'] for r in records],
              'graph_hash': records[0]['graph_hash'], 'snapshot_id': records[0]['snapshot_id'],
              'threads': args.threads, 'batch_size': args.batch_size,
              'versions': {p: importlib.metadata.version(p) for p in ['torch','transformers','sentence-transformers','numpy']}}
    cache_key = fingerprint(config)
    destination = args.output / args.model
    destination.mkdir(parents=True, exist_ok=True)
    vector_path = destination / 'node_vectors.npy'
    manifest_path = destination / 'manifest.json'
    cache_hit = (vector_path.exists() and manifest_path.exists()
                 and json.loads(manifest_path.read_text(encoding='utf-8'))['cache_key'] == cache_key)
    if cache_hit:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        vectors = np.load(vector_path, allow_pickle=False)
        if vectors.shape != (len(ids), model.get_sentence_embedding_dimension()) or not np.isfinite(vectors).all():
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
        sums = np.zeros((len(ids),model.get_sentence_embedding_dimension()),dtype=np.float32)
        start_index = 0
        checkpoint_path = destination / 'checkpoint.npz'
        if checkpoint_path.exists():
            with np.load(checkpoint_path,allow_pickle=False) as checkpoint:
                if str(checkpoint['cache_key']) == cache_key:
                    sums = checkpoint['sums'].copy(); start_index=int(checkpoint['next_index'])
        begin = time.perf_counter()
        for start in range(start_index, len(work), args.batch_size):
            batch = work[start:start+args.batch_size]
            features = tokenizer.pad([x[2] for x in batch], padding=True, return_tensors='pt')
            with torch.inference_mode():
                encoded = model(features)['sentence_embedding']
                encoded = torch.nn.functional.normalize(encoded,p=2,dim=1).cpu().numpy()
            if not np.isfinite(encoded).all():
                raise ValueError('Model returned nonfinite vectors')
            for (i,weight,_),vector in zip(batch,encoded):
                sums[i] += vector*weight
            done = start+len(batch)
            if start == start_index or done % (args.batch_size*50) == 0 or done == len(work):
                print(f'{args.model}: {done}/{len(work)} windows; {time.perf_counter()-begin:.1f}s this session',flush=True)
                temp = checkpoint_path.with_suffix('.tmp')
                with temp.open('wb') as f:
                    np.savez(f,sums=sums,next_index=done,cache_key=cache_key)
                temp.replace(checkpoint_path)
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
                    'resumed_window_index':start_index}
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
    begin = time.perf_counter()
    scores = query_vectors @ vectors.T
    rankings = {}
    predictions = []
    for q, row in zip(questions,scores):
        order = np.argsort(-row,kind='stable')[:10]
        rankings[q['question_id']] = [ids[i] for i in order]
        predictions.append({'question_id':q['question_id'],'question':q['question'],
                            'top_nodes':[{'node_id':ids[i],'score':float(row[i])} for i in order],
                            'answerable_gold':q['answerable'], 'abstention_decision':None})
    search_seconds = time.perf_counter()-begin
    metrics = evaluate(questions,rankings)
    metrics['by_type'] = {kind:evaluate([q for q in questions if q['type']==kind],rankings)
                          for kind in sorted({q['type'] for q in questions if q['answerable']})}
    report = {'model':args.model,'cache_hit':cache_hit,'cache_key':cache_key,
              'question_set_hash':fingerprint(questions),'candidate_count':len(ids),
              'split':'dev','question_count':len(questions),'metrics':metrics,
              'load_seconds':load_seconds,'query_encode_seconds':query_seconds,'search_seconds':search_seconds,
              'manifest':manifest,'unanswerable_policy':'diagnostics_only_no_threshold_claim',
              'notes':['Draft labels require human review.','Exact cosine offline, not Neo4j ANN.',
                       'Native window limits differ; compare complete configurations.',
                       'No graph expansion, reranking, fine-tuning or test-set evaluation.']}
    write_json(destination/'results.json',report)
    write_json(destination/'predictions.json',predictions)
    print(json.dumps({'model':args.model,'metrics':metrics['by_k'],'mrr':metrics['single_group_mrr_at_max_k']},indent=2),flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',choices=MODELS,required=True)
    parser.add_argument('--corpus',type=Path,default=Path('output/kg/embedding_text/node_texts.jsonl'))
    parser.add_argument('--questions',type=Path,default=Path('evaluation/dev.jsonl'))
    parser.add_argument('--output',type=Path,default=Path('output/kg/embedding_benchmark'))
    parser.add_argument('--batch-size',type=int,default=16)
    parser.add_argument('--threads',type=int,default=4)
    parser.add_argument('--overlap',type=int,default=24)
    args = parser.parse_args()
    if args.batch_size<1 or args.threads<1 or args.overlap<0:
        parser.error('Invalid numeric options')
    run(args)


if __name__=='__main__':
    main()
