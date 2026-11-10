"""Summarize completed development experiments without opening test labels.

Kept for the documented command; scoring and the report live in legal_kg.retrieval_eval.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from legal_kg.retrieval_eval import main  # noqa: E402


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
