import argparse
from pathlib import Path

from .pipeline import run_pipeline


def completion_message(chunk_count: int, document_count: int) -> str:
    return f"Completed: {chunk_count} chunks / {document_count} documents"


def main() -> int:
    parser = argparse.ArgumentParser(description="Tiền xử lý 8 văn bản pháp luật thành JSONL")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=Path("output/preprocessed"))
    parser.add_argument("--max-chars", type=int, default=6000)
    args = parser.parse_args()
    report = run_pipeline(args.root.resolve(), args.output.resolve(), args.max_chars)
    print(completion_message(report["global"]["chunk_count"], report["global"]["document_count"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
