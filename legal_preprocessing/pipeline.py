from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from . import __version__
from .chunk import chunk_units
from .clean import clean_blocks
from .extract import extract_docx
from .manifest import DOCUMENTS, validate_manifest
from .parse import parse_legal_units
from .qa import document_metrics, render_markdown, validate_chunks
from .serialize import write_jsonl_atomic


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def run_pipeline(root: Path, output_dir: Path, max_chars: int = 6000, *, extractor=extract_docx,
                 validate_sources: bool = True) -> dict:
    specs = validate_manifest(root) if validate_sources else DOCUMENTS
    output_dir.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict] = []
    metrics = []
    for spec in specs:
        raw_blocks = extractor(root / spec.source_file)
        cleaned = clean_blocks(raw_blocks)
        parsed = parse_legal_units(cleaned.blocks)
        chunks = chunk_units(spec, parsed.units, max_chars)
        if not chunks:
            raise ValueError(f"No chunks generated for {spec.document_id}")
        rows = [chunk.to_dict() for chunk in chunks]
        write_jsonl_atomic(output_dir / "by_document" / f"{spec.document_id}.jsonl", rows)
        _write_json(output_dir / "intermediate" / f"{spec.document_id}.blocks.json", {
            "raw_blocks": [{"block_number": block.block_number, "block_type": block.block_type,
                            "text": block.raw_text} for block in raw_blocks],
            "clean_blocks": [{"block_number": block.block_number, "block_type": block.block_type,
                              "text": block.raw_text} for block in cleaned.blocks],
            "removed_blocks": [item.__dict__ for item in cleaned.removed_blocks],
        })
        all_rows.extend(rows)
        metrics.append(document_metrics(spec, raw_blocks, cleaned, parsed, chunks))
    checks = validate_chunks(all_rows, len(specs))
    report = {
        "processing_version": __version__, "generated_at": datetime.now(timezone.utc).isoformat(),
        "max_chars": max_chars, "documents": metrics,
        "global": {"document_count": len(specs), "chunk_count": len(all_rows), "checks": checks,
                   "status": "passed" if all(checks.values()) else "failed"},
    }
    if not all(checks.values()):
        raise ValueError(f"Global QA failed: {checks}")
    write_jsonl_atomic(output_dir / "legal_chunks.jsonl", all_rows)
    _write_json(output_dir / "qa_report.json", report)
    (output_dir / "qa_report.md").write_text(render_markdown(report), encoding="utf-8")
    return report
