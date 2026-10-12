import json
import os
import subprocess
import sys

from legal_kg.cli import main


def test_build_and_inspect_without_neo4j(tmp_path, capsys):
    source = tmp_path / "chunks.jsonl"
    source.write_text(json.dumps({
        "chunk_id": "c1", "document_id": "doc", "title": "Luật", "document_number": "01",
        "document_type": "luật", "source_file": "a.docx", "text": "Nội dung",
        "chunk_type": "article", "article": {"number": "1", "title": "Đầu tiên"},
        "paragraph_start": 1, "paragraph_end": 2,
        "article_chunk_index": 1, "chunk_index": 1,
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    output = tmp_path / "graph.json"
    assert main(["build", "--input", str(source), "--output", str(output)]) == 0
    assert output.exists()
    capsys.readouterr()
    assert main(["inspect", "--input", str(output), "--chunk-id", "c1"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["chunk"]["id"] == "c1"
    assert [n["label"] for n in result["path"]] == ["LegalDocument", "Article"]
    assert main(["inspect", "--input", str(output), "--chunk-id", "missing"]) != 0


def test_invalid_input_does_not_replace_existing_output(tmp_path):
    source = tmp_path / "bad.jsonl"
    source.write_text("not json\n", encoding="utf-8")
    output = tmp_path / "graph.json"
    output.write_text("previous", encoding="utf-8")
    assert main(["build", "--input", str(source), "--output", str(output)]) != 0
    assert output.read_text(encoding="utf-8") == "previous"


def test_windows_legacy_console_can_print_vietnamese_context(tmp_path):
    from legal_kg.build import build_graph
    from test_kg_build import row

    graph = tmp_path / "graph.json"
    graph.write_text(json.dumps(build_graph([row()]).to_dict(), ensure_ascii=False), encoding="utf-8")
    process = subprocess.run([sys.executable, "-m", "legal_kg.cli", "inspect", "--input", str(graph),
                              "--chunk-id", "c1"], capture_output=True,
                             env={**os.environ, "PYTHONIOENCODING": "cp1252"})
    assert process.returncode == 0, process.stderr.decode("utf-8", errors="replace")
    result = json.loads(process.stdout.decode("utf-8"))
    assert result["chunk"]["properties"]["text"] == "Nội dung nguồn"
