# Development node embedding benchmark

Goal: compare multilingual MiniLM and multilingual E5-small on the development questions and all 4534 candidate nodes; do not read test questions or write Neo4j.

Implementation: `legal_kg/embedding_benchmark.py`; unit tests for token coverage, node pooling and evidence-group scoring in `tests/test_embedding_benchmark.py`. Optional dependencies in `requirements-embedding.txt`. Artifacts in `output/kg/embedding_benchmark/`.

- Test token-window coverage, weighted normalized pooling, multiple required groups, primary-vs-ancestor matches and unanswerable exclusion.
- Implement model-specific prefixes, native token budgets, overlapping windows, single-node weighted-mean pooling, normalized cosine search and resumable node cache with corpus/model hashes.
- Run MiniLM and E5 sequentially on CPU with the same candidate set, questions, metrics and pooling rule. Native token budgets differ; report this as comparison of configurations, not isolated model weights.
- Record Recall@1/3/5/10 by evidence group, all-groups hit rate, primary-node group recall, MRR for single-group questions and separate diagnostics for unanswerable questions. Do not infer answerability from top-1 score alone.
- Publish per-question rankings, metrics, window/token statistics, revisions and timing. Retain test untouched; do not claim a production selection from the small draft development set.
