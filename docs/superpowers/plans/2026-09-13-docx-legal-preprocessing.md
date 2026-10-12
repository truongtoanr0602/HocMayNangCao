# DOCX Legal Preprocessing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace PDF/OCR preprocessing with deterministic DOCX extraction for the eight required Vietnamese legal documents while preserving legal hierarchy and chunk output compatibility.

**Architecture:** A DOCX extractor emits ordered `SourceBlock` values for body paragraphs and table rows. Cleaning, parsing, and chunking carry block locations through to JSONL as `paragraph_start`/`paragraph_end`, while legacy page fields remain present as `null`; the manifest and QA enforce DOCX-only inputs.

**Tech Stack:** Python 3.11, `python-docx`, dataclasses, pytest, JSON/JSONL

**Spec:** `docs/superpowers/specs/2026-09-13-docx-legal-preprocessing-design.md`

## Global Constraints

- Process exactly `doc-01` through `doc-08`; never scan or include `data/tuychon/`.
- Runtime inputs are `.docx` only; `.doc`, PDF extraction, and OCR are outside the main pipeline.
- `page_start` and `page_end` remain in every chunk and are `null` for DOCX.
- `paragraph_start` and `paragraph_end` are one-based ordered body-block positions and include table rows.
- Table cells are joined with ` | ` and table content must not be duplicated.
- Output writes remain atomic.

---

### Task 1: Introduce DOCX source-location models

**Files:**
- Modify: `legal_preprocessing/models.py`
- Modify: `tests/test_chunk.py`
- Modify: `legal_preprocessing/chunk.py`

**Interfaces:**
- Produces: `SourceBlock(block_number: int, block_type: str, raw_text: str, lines: tuple[str, ...])`.
- Produces: `SourceLine(block_number: int, text: str)`.
- Produces: nullable `Chunk.page_start`, `Chunk.page_end` plus integer `Chunk.paragraph_start`, `Chunk.paragraph_end`.
- Consumes: existing `LegalUnit`, `DocumentSpec`, and chunk splitting behavior.

- [ ] **Step 1: Write a failing chunk-location test**

Update the test helper to construct source lines by block number and add:

```python
def test_docx_chunk_uses_block_range_and_null_pages():
    lines = (
        SourceLine(7, "Điều 1. Phạm vi"),
        SourceLine(9, "1. Nội dung"),
    )
    unit = LegalUnit("article", lines, 7, 9, article=StructureRef("1", "Phạm vi"))
    chunk = chunk_units(SPEC, [unit])[0]
    assert chunk.page_start is None
    assert chunk.page_end is None
    assert chunk.paragraph_start == 7
    assert chunk.paragraph_end == 9
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `python -m pytest tests/test_chunk.py::test_docx_chunk_uses_block_range_and_null_pages -q`

Expected: FAIL because `Chunk` does not expose paragraph locations and still writes page numbers.

- [ ] **Step 3: Implement the minimal model and chunk changes**

Add `SourceBlock`, rename the source coordinate in `SourceLine`, and extend `Chunk`:

```python
@dataclass(frozen=True)
class SourceBlock:
    block_number: int
    block_type: str
    raw_text: str
    lines: tuple[str, ...]

@dataclass(frozen=True)
class SourceLine:
    block_number: int
    text: str
```

Change `LegalUnit.page_start/page_end` to `paragraph_start/paragraph_end`. Define
`Chunk.page_start: int | None`, `Chunk.page_end: int | None`, followed by
`paragraph_start: int` and `paragraph_end: int`. In `chunk_units`, emit `None,
None` for pages and calculate the paragraph range from `line.block_number`.

- [ ] **Step 4: Run model and chunk tests and verify GREEN**

Run: `python -m pytest tests/test_chunk.py -q`

Expected: all chunk tests PASS.

### Task 2: Extract ordered paragraphs and table rows from DOCX

**Files:**
- Modify: `requirements.txt`
- Replace: `legal_preprocessing/extract.py`
- Replace: `tests/test_extract.py`

**Interfaces:**
- Consumes: `pathlib.Path` to an existing `.docx`.
- Produces: `extract_docx(path: Path) -> list[SourceBlock]`.
- Produces: `DocxExtractionError(RuntimeError)` for unsupported, corrupt, or effectively empty documents.

- [ ] **Step 1: Add the dependency and write failing paragraph-order tests**

Add `python-docx>=1.1,<2` to `requirements.txt`. Create DOCX fixtures in `tmp_path`
with `docx.Document`, then assert:

```python
def test_extract_docx_preserves_body_paragraph_order(tmp_path):
    path = tmp_path / "law.docx"
    document = Document()
    document.add_paragraph("Điều 1. Phạm vi")
    document.add_paragraph("1. Nội dung")
    document.save(path)

    blocks = extract_docx(path)

    assert [(b.block_number, b.block_type, b.raw_text) for b in blocks] == [
        (1, "paragraph", "Điều 1. Phạm vi"),
        (2, "paragraph", "1. Nội dung"),
    ]
```

Also create a header and footer and assert their strings do not occur in
`blocks`.

- [ ] **Step 2: Run paragraph tests and verify RED**

Run: `python -m pytest tests/test_extract.py -q`

Expected: collection/import FAIL because `extract_docx` and `SourceBlock` are not yet implemented.

- [ ] **Step 3: Implement paragraph extraction**

Open `Document(path)`, iterate only `document.element.body.iterchildren()`, map
`CT_P` to `Paragraph(element, document)` and append non-empty paragraph text as
`SourceBlock`. Normalize CRLF to LF but do not perform legal-text cleanup here.
Catch package/open errors and raise:

```python
raise DocxExtractionError(f"Cannot extract {path}: {exc}") from exc
```

Reject sources with fewer than 20 non-whitespace characters using:

```python
raise DocxExtractionError(f"Insufficient text in {path}")
```

- [ ] **Step 4: Write and run a failing table-order test**

Insert a two-column table between two paragraphs. Assert the output order is
paragraph, table row, paragraph; assert the row text is `"Ô A | Ô B"` and each
cell value appears exactly once.

Run: `python -m pytest tests/test_extract.py::test_extract_docx_preserves_table_position_without_duplication -q`

Expected: FAIL because `CT_Tbl` is not handled.

- [ ] **Step 5: Implement table-row extraction**

Map `CT_Tbl` to `Table(element, document)`. For each row, join normalized,
non-empty cell texts with ` | ` and emit one `SourceBlock` with
`block_type="table_row"`. Increment `block_number` only for emitted blocks.

- [ ] **Step 6: Verify the DOCX extractor**

Run: `python -m pytest tests/test_extract.py -q`

Expected: all extractor tests PASS, including corrupt/empty DOCX failures and
header/footer exclusion.

### Task 3: Adapt cleaning and legal parsing to source blocks

**Files:**
- Modify: `legal_preprocessing/clean.py`
- Modify: `legal_preprocessing/parse.py`
- Replace: `tests/test_clean.py`
- Modify: `tests/test_parse.py`

**Interfaces:**
- Consumes: `list[SourceBlock]`.
- Produces: `CleanResult(blocks: tuple[SourceBlock, ...], removed_blocks: tuple[RemovedBlock, ...], warnings: tuple[str, ...])`.
- Produces: `parse_legal_units(blocks: list[SourceBlock] | tuple[SourceBlock, ...]) -> ParseResult`.

- [ ] **Step 1: Write failing block-cleaning tests**

Add tests asserting normalization preserves legal numbers and punctuation,
empty/control-only blocks are recorded as removed, and table rows keep the
` | ` cell separator. Use exact expected values:

```python
assert normalize_text("Điều  12 .  Mức  5,5% ") == "Điều 12. Mức 5,5%"
assert clean_blocks([SourceBlock(4, "table_row", "Mức | 5,5%", ("Mức | 5,5%",))]).blocks[0].block_number == 4
```

- [ ] **Step 2: Run cleaning tests and verify RED**

Run: `python -m pytest tests/test_clean.py -q`

Expected: FAIL because `clean_blocks` and block-based result fields do not exist.

- [ ] **Step 3: Implement `clean_blocks`**

Replace repeated page-margin inference with a single pass. Normalize each line,
drop blocks with no remaining text as `RemovedBlock(block_number,
"empty_after_normalization", raw_text)`, and preserve block type and original
block number on retained blocks.

- [ ] **Step 4: Write a failing parser location test**

Construct three `SourceBlock` values for a chapter heading, article heading, and
clause. Assert the article unit has `paragraph_start == 2`,
`paragraph_end == 3`, and every source line retains its originating block number.

- [ ] **Step 5: Run the parser location test and verify RED**

Run: `python -m pytest tests/test_parse.py -q`

Expected: FAIL where parsing still accesses `PageText.page_number`.

- [ ] **Step 6: Adapt the parser minimally**

Iterate `block.lines`, construct `SourceLine(block.block_number, text)`, and set
unit start/end from the first/last source line block number. Keep all existing
hierarchy regexes, sequence checks, warnings, and article association behavior.

- [ ] **Step 7: Verify cleaning and parsing**

Run: `python -m pytest tests/test_clean.py tests/test_parse.py -q`

Expected: all cleaning and parser tests PASS.

### Task 4: Switch manifest, pipeline, intermediate output, and QA to DOCX

**Files:**
- Modify: `legal_preprocessing/manifest.py`
- Modify: `legal_preprocessing/pipeline.py`
- Modify: `legal_preprocessing/qa.py`
- Modify: `tests/test_manifest.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_qa.py`
- Modify: `tests/test_real_output.py`

**Interfaces:**
- Pipeline default extractor: `extract_docx`.
- Intermediate file: `intermediate/doc-XX.blocks.json`.
- QA metrics: `block_count`, `paragraph_count`, `table_row_count`, raw/clean character counts, article/chunk counts, warnings.

- [ ] **Step 1: Write failing manifest tests**

Assert all eight `source_file` values end in `.docx`, none contains `tuychon`, and
the exact `doc-07` source is `data/07_ND135-2020_Tuoi_nghi_huu.docx`.

- [ ] **Step 2: Run manifest tests and verify RED**

Run: `python -m pytest tests/test_manifest.py -q`

Expected: FAIL because manifest entries still end in `.pdf`.

- [ ] **Step 3: Update the manifest**

Change only the eight extensions to `.docx`; preserve document IDs, titles,
numbers, types, ordering, and explicit source enumeration.

- [ ] **Step 4: Write failing pipeline and QA tests**

Use a fake extractor returning paragraph and table-row `SourceBlock` objects.
Assert `doc-01.blocks.json` exists, `doc-01.pages.json` is not created in a fresh
output directory, every row has null page fields and integer paragraph ranges,
and QA rejects rows whose source is not DOCX or whose paragraph range is invalid.

- [ ] **Step 5: Run pipeline and QA tests and verify RED**

Run: `python -m pytest tests/test_pipeline.py tests/test_qa.py -q`

Expected: FAIL because the pipeline calls PDF extraction, emits pages JSON, and
does not validate DOCX locations.

- [ ] **Step 6: Implement the DOCX pipeline**

Import `extract_docx` and `clean_blocks`. Write intermediate JSON with:

```json
{
  "raw_blocks": [{"block_number": 1, "block_type": "paragraph", "text": "..."}],
  "clean_blocks": [{"block_number": 1, "block_type": "paragraph", "text": "..."}],
  "removed_blocks": []
}
```

Update `document_metrics` and Markdown headings from pages to blocks. Extend
`validate_chunks` with `docx_sources` and `valid_paragraph_ranges`; a valid range
has integer endpoints satisfying `1 <= paragraph_start <= paragraph_end`.

- [ ] **Step 7: Verify pipeline-level behavior**

Run: `python -m pytest tests/test_manifest.py tests/test_pipeline.py tests/test_qa.py -q`

Expected: all focused tests PASS.

### Task 5: Convert document 07 and regenerate all real outputs

**Files:**
- Create: `data/07_ND135-2020_Tuoi_nghi_huu.docx`
- Regenerate: `output/preprocessed/legal_chunks.jsonl`
- Regenerate: `output/preprocessed/by_document/doc-01.jsonl` through `doc-08.jsonl`
- Regenerate: `output/preprocessed/intermediate/doc-01.blocks.json` through `doc-08.blocks.json`
- Regenerate: `output/preprocessed/qa_report.json`
- Regenerate: `output/preprocessed/qa_report.md`
- Modify: `README-preprocessing.md`

**Interfaces:**
- Consumes: eight manifest DOCX sources.
- Produces: complete validated training/RAG preprocessing artifacts.

- [ ] **Step 1: Convert the legacy `.doc` once**

Use Microsoft Word “Save As DOCX” or LibreOffice conversion to create the exact
manifest path. Do not delete the `.doc` or PDF. Verify the converted file opens:

Run: `python -c "from docx import Document; d=Document(r'data/07_ND135-2020_Tuoi_nghi_huu.docx'); print(len(d.paragraphs))"`

Expected: exit code 0 and a positive paragraph count.

- [ ] **Step 2: Update README commands and output descriptions**

Document `python-docx`, DOCX-only manifest behavior, nullable page fields,
paragraph ranges, `blocks.json`, and the unchanged command:

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
python -m legal_preprocessing.cli --output output/preprocessed --max-chars 6000
```

- [ ] **Step 3: Run the entire unit/integration suite**

Run: `python -m pytest -q`

Expected: all tests PASS before regeneration.

- [ ] **Step 4: Regenerate the complete output**

Run: `python -m legal_preprocessing.cli --output output/preprocessed --max-chars 6000`

Expected: `Completed: <positive count> chunks / 8 documents` and exit code 0.

- [ ] **Step 5: Run real-output acceptance tests**

Run: `python -m pytest tests/test_real_output.py -q`

Expected: all real-output tests PASS; all eight document IDs occur, article
numbers are contiguous per document, sources end in DOCX, pages are null, and
paragraph ranges are valid.

- [ ] **Step 6: Remove superseded page intermediates**

After the successful regeneration and real-output tests, remove only the eight
files matching `output/preprocessed/intermediate/doc-0[1-8].pages.json`. They are
generated artifacts superseded by the verified `.blocks.json` files; all source
PDF and DOCX files remain untouched.

- [ ] **Step 7: Inspect QA and source coverage**

Run:

```powershell
$report = Get-Content -Raw -Encoding utf8 output/preprocessed/qa_report.json | ConvertFrom-Json
$report.global.status
$report.documents | Select-Object document_id,source_file,block_count,article_count,chunk_count
```

Expected: global status `passed`, eight rows, only `.docx` sources, and positive
block/article/chunk counts for each document.

### Task 6: Final regression and stale-artifact audit

**Files:**
- Inspect: `legal_preprocessing/`
- Inspect: `tests/`
- Inspect: `output/preprocessed/`

**Interfaces:**
- Produces: verified DOCX-only pipeline with no active PDF/OCR dependency.

- [ ] **Step 1: Search for stale active PDF assumptions**

Run: `rg -n "extract_pdf|clean_pages|PageText|page_count|\.pages\.json|\.pdf" legal_preprocessing tests README-preprocessing.md`

Expected: no active preprocessing references; test fixture strings may mention
PDF only when explicitly verifying rejection.

- [ ] **Step 2: Run fresh full verification**

Run: `python -m pytest -q`

Expected: zero failures.

- [ ] **Step 3: Validate JSONL independently**

Run: `python -c "from pathlib import Path; from legal_preprocessing.serialize import read_and_validate_jsonl; rows=read_and_validate_jsonl(Path('output/preprocessed/legal_chunks.jsonl')); assert rows and len({r['document_id'] for r in rows}) == 8; print(len(rows))"`

Expected: prints a positive chunk count and exits 0.

- [ ] **Step 4: Record the handoff constraint**

Report that this workspace has no Git repository, so no commits were created.
List the generated outputs, test count, QA status, and any legal-text anomalies
that remain in the Word sources without silently correcting their wording.
