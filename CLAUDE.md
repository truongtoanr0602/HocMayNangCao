# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Hybrid KG–RAG assistant for Vietnamese labour law. Two Python packages exist today:
`legal_preprocessing` (DOCX → structured JSONL chunks) and `legal_kg` (chunks → structural graph with
citation edges, optional Neo4j load, node-embedding benchmark). Neither one calls an LLM: all extraction
is rule-based and deterministic. Retrieval uses only the KG plus node embeddings (no BM25, no chunk
embeddings, by project decision); the conversational answer layer is not implemented yet.
READMEs, specs and plans are written in Vietnamese. Legal hierarchy terms: Phần (part), Chương (chapter),
Mục (section), Điều (article), Khoản (clause), Điểm (point), Phụ lục (appendix).

## Commands

Run everything from the repo root (CLI default paths are relative to it). The dev shell is Windows PowerShell.

```powershell
python -m pip install -r requirements.txt            # core: python-docx, pytest, neo4j
python -m pip install -r requirements-embedding.txt  # optional: torch, sentence-transformers

python -m pytest -q                                   # full suite, no Neo4j/Docker needed
python -m pytest tests/test_chunk.py -q               # one file
python -m pytest tests/test_chunk.py -k "limit" -q    # one test by name

# Pipeline, in order
python -m legal_preprocessing.cli --output output/preprocessed --max-chars 6000
python -m legal_kg.cli build                          # -> output/kg/structural_graph.json
python -m legal_kg.cli inspect --chunk-id 00e7045e70338c40ac64
python -m legal_kg.cli search --title "BLLĐ 2019"
python -m legal_kg.embedding_text                     # -> output/kg/embedding_text/node_texts.jsonl
python -m legal_kg.embedding_benchmark --model e5-small   # e5-base, bge-m3, vn-embedding, minilm; dev only
python -m legal_kg.retrieval_eval                     # rescore saved runs -> comparison.md (bootstrap CI, thresholds)
python -m legal_kg.kg_expansion --run output/kg/embedding_benchmark/e5-small   # P1-budget / P2 / router-P2 runs
python evaluation/build_questions.py                  # regenerates evaluation/*.jsonl from SEEDS (+ pooling review)
# Full evaluation protocol (pooling, freeze, single test run): evaluation/README.md

# Neo4j (needs NEO4J_PASSWORD in the *process* env; the Python CLI does not read .env)
powershell -NoProfile -File scripts/start-neo4j.ps1 -OpenBrowser   # local Windows install
docker compose up -d neo4j                                          # or Docker (separate database)
python -m legal_kg.cli load
python -m legal_kg.cli lookup --snapshot <source_hash> --chunk-id <id>
python -m legal_kg.cli search-db --snapshot <source_hash> --title "BLLĐ 2019"
python -m legal_kg.cli load-embeddings --run output/kg/embedding_benchmark/<model>   # vectors + cosine index
python -m legal_kg.cli check-ann --run output/kg/embedding_benchmark/<model>         # ANN vs offline top-10

# Real-Neo4j integration test, opt-in
$env:LEGAL_KG_INTEGRATION = '1'; python -m pytest tests/test_kg_integration.py -q
```

## Architecture

**Data flow:** `data/01..08_*.docx` → `legal_preprocessing` → `output/preprocessed/legal_chunks.jsonl`
(+ `by_document/`, `intermediate/*.blocks.json`, `qa_report.*`) → `legal_kg build` →
`output/kg/structural_graph.json` → (optional) Neo4j / embedding text → embedding benchmark.
`output/` is committed, and tests read it: `tests/test_real_output.py` checks the real JSONL. When you change
chunking or metadata, regenerate the output and then rerun `legal_kg.cli build`.

**Preprocessing** (`pipeline.run_pipeline`): `extract` (python-docx blocks; a block is a paragraph or a table
row with cells joined by ` | `) → `clean` → `parse` (builds the Điều/Khoản/Điểm/Phụ lục unit tree) →
`chunk` → `qa.validate_chunks`. The run raises an error and writes no merged output when global QA fails.
- The corpus is fixed to exactly 8 documents in `legal_preprocessing/manifest.py` (`DOCUMENTS`). Document IDs
  `doc-01..08`, titles and `short_title` aliases live there. `data/tuychon` and the PDFs are never used.
  Only `.docx` files are read, and there is no OCR.
- Chunking always splits at the smallest structural level (an article with no clauses stays one chunk,
  a clause with no points stays one chunk, and each point gets its own chunk). The parent's lead-in text
  goes with each child. Only after this structural split does the `--max-chars` limit (6000) apply:
  over-long units are split further and every piece keeps the same legal path. Two sibling units are never
  merged into one chunk.
- Appendices and tables become separate branches/chunks. Tables keep empty columns and merged-cell origins.
- Every chunk carries `structure_path` (a list of `{type, number, title}`, which `legal_kg` consumes directly)
  and `source_spans`, which are Python char offsets into the *cleaned* block text. `page_start`/`page_end`
  are always `null` because DOCX has no stable pagination.

**KG** (`legal_kg`):
- `build.build_graph` turns rows into `GraphPayload` (`models.py`). Node IDs are full paths such as
  `doc-01/chapter-VII/section-2/article-111/clause-1/point-a`. Chunk IDs come from the JSONL.
  Structural edges: `CONTAINS` and `HAS_CHUNK`.
- `references.resolve_references` adds `REFERS_TO`/`GUIDES`/`DETAILS` edges between units, and rolls them up
  between `LegalDocument` nodes. It runs only after the whole corpus is built. Every edge needs
  `evidence_json` entries whose `quote` appears verbatim in the source chunk. Unresolved targets become
  warnings, never placeholder nodes. Version matching is strict: a citation of the 2014 social-insurance law
  must not link to the 2024 law. Rows can also carry explicit `references` metadata for patterns the rules
  miss.
- Snapshots: `source_hash` is computed from the schema version (`SCHEMA_VERSION = "legal-kg-v2"`; the
  `structural-kg-v1` artifacts can still be read), the reference-rule version and the source rows.
  Neo4j keys every node on `(snapshot_id, id)`. Snapshots coexist and are never auto-deleted, so every
  query must filter by `snapshot_id`. `repository.py` validates labels and relationship types against an
  allowlist, then loads the whole graph in a single transaction.
- `titles.TitleIndex` does exact lookup on normalized (accent- and case-insensitive) title, alias or document
  number.
- `embedding_text.py` rebuilds full per-node body text from the cleaned blocks and spans (`--article-mode v2`
  embeds only heading + lead-in for Articles that have Clauses). `embedding_benchmark.py` embeds that text with
  token windows and weighted-mean pooling (one vector per node), caches vectors per model and writes a *run*:
  `predictions.json` (ranked `top_nodes` per question) + `results.json`. Every pipeline writes this run format,
  and `retrieval_eval.py` is the single scorer (metrics, paired bootstrap CI, abstention threshold).
  `kg_expansion.py` (P2: seeds + parent Article + one-hop REFERS_TO/GUIDES/DETAILS under a fixed node/char
  budget) and `router.py` (explicit "Điều/Khoản/Điểm + document" addresses) consume dense runs.
- Test split discipline: the benchmark and scorer refuse `evaluation/test.jsonl` unless
  `evaluation/frozen_config.json` (written by `evaluation/freeze_config.py` after dev decisions) matches its hash;
  question-file hashes are checked everywhere, so editing questions invalidates old runs.
  Benchmark `.npy`/`.npz` files are gitignored. `BAAI/bge-m3` is the one model loaded from `pytorch_model.bin`
  (weights_only); all others must have safetensors.

**Legacy data:** `json_KG/` and `output/preprocessed/extraction_results*.jsonl` hold old LLM semantic
extractions. The structural KG does not use them. `--allow-legacy-metadata` exists only for loading old
snapshots.

## Conventions

- Writes are atomic: write a `.tmp` file, then replace the target.
- `.gitattributes` forces LF line endings on `.py/.md/.json/.jsonl/.yaml`.
- Embeddings and any retrieval must use the same chunk set and `source_hash` snapshot as the graph.
- On Python 3.15, `pyyaml` (a transformers dependency) has no wheel; install it first with
  `PYYAML_FORCE_LIBYAML=0 python -m pip install pyyaml`, then `requirements-embedding.txt`.

## Agent skills

### Issue tracker

Issues live in GitHub Issues on truongtoanr0602/HocMayNangCao, via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: root `GLOSSARY.md` + `docs/adr/` (created lazily). See `docs/agents/domain.md`.
