import json
from dataclasses import replace

import pytest

from legal_kg.build import build_graph, inspect_chunk
from legal_kg.models import GraphPayload
from test_leaf_chunks import SPEC, make_chunks


DECREE = replace(SPEC, document_id="decree", title="Nghị định 02/2026/NĐ-CP", document_number="02/2026/NĐ-CP",
                 document_type="nghị định", source_file="decree.docx")


def graph_for(text):
    law = make_chunks("Điều 1. Phạm vi", "1. Các trường hợp:", "a) A", "b) B")
    decree = make_chunks("Điều 1. Hướng dẫn", text, spec=DECREE)
    return build_graph([c.to_dict() for c in law + decree]), decree[0].chunk_id


def semantic(graph):
    return [e for e in graph.edges if e.type not in {"CONTAINS", "HAS_CHUNK"}]


def test_cross_document_details_have_provision_document_links_and_evidence():
    text = "Quy định chi tiết điểm a khoản 1 Điều 1 của Luật mẫu 2026."
    graph, chunk_id = graph_for(text)
    links = {(e.source, e.target, e.type): e for e in semantic(graph)}
    edge = links[("decree/article-1", "law/article-1/clause-1/point-a", "DETAILS")]
    assert ("decree", "law", "DETAILS") in links
    evidence = json.loads(edge.properties["evidence_json"])
    assert evidence[0]["chunk_id"] == chunk_id and text in evidence[0]["quote"]
    assert GraphPayload.from_dict(graph.to_dict()).to_dict() == graph.to_dict()
    context = inspect_chunk(graph, chunk_id)
    assert [n["label"] for n in context["path"]] == ["LegalDocument", "Article"]
    assert any(e["type"] == "DETAILS" for e in context["relations"])


def test_passive_guidance_reverses_direction():
    graph, _ = graph_for("Được hướng dẫn tại Điều 1 của Luật mẫu 2026.")
    assert ("law/article-1", "decree/article-1", "GUIDES") in {(e.source, e.target, e.type) for e in semantic(graph)}


def test_plain_reference_does_not_become_guidance_from_article_heading():
    graph, _ = graph_for("Thực hiện theo Điều 1 của Luật mẫu 2026.")
    assert {e.type for e in semantic(graph)} == {"REFERS_TO"}


@pytest.mark.parametrize("reference", ["Luật mẫu năm 2014", "Luật mẫu số 99/2014/QH13", "Luật mẫu ngày 01 tháng 01 năm 2014"])
def test_different_version_does_not_resolve_to_available_law(reference):
    graph, _ = graph_for(f"Quy định chi tiết Điều 1 của {reference}.")
    assert not semantic(graph)
    assert graph.warnings


def test_missing_provision_warns_without_inventing_node_or_document_guidance():
    graph, _ = graph_for("Quy định chi tiết Điều 999 của Luật mẫu 2026.")
    assert not semantic(graph)
    assert any("999" in w for w in graph.warnings)


def test_list_of_clauses_and_inherited_document_scope():
    law = make_chunks("Điều 1. Phạm vi", "1. A", "2. B", "3. C")
    decree = make_chunks("Điều 1. Phạm vi", "Nghị định này quy định chi tiết các khoản sau của Luật mẫu 2026:",
                         "1. Nội dung theo khoản 1, 2 và 3 Điều 1.", spec=DECREE)
    graph = build_graph([c.to_dict() for c in law + decree])
    targets = {e.target for e in semantic(graph) if e.type == "DETAILS"}
    assert {f"law/article-1/clause-{i}" for i in (1, 2, 3)} <= targets


def test_graph_order_and_evidence_are_deterministic():
    chunks = make_chunks("Điều 1. Phạm vi", "Nội dung") + make_chunks(
        "Điều 1. Phạm vi", "Quy định chi tiết Điều 1 của Luật mẫu 2026.", spec=DECREE)
    rows = [c.to_dict() for c in chunks]
    assert build_graph(rows).to_dict() == build_graph(list(reversed(rows))).to_dict()


def test_trailing_detail_directive_does_not_link_cited_articles_to_each_other():
    law = make_chunks("Điều 1. Một", "A", "Điều 2. Hai", "B")
    decree = make_chunks("Điều 1. Nội dung", "Thực hiện theo Điều 1 và Điều 2 của Luật mẫu 2026 và được quy định chi tiết như sau:", spec=DECREE)
    graph = build_graph([c.to_dict() for c in law + decree])
    links = {(e.source, e.target, e.type) for e in semantic(graph)}
    assert ("decree/article-1", "law/article-1", "DETAILS") in links
    assert ("decree/article-1", "law/article-2", "DETAILS") in links
    assert not any(a.startswith("law/") and b.startswith("law/") for a, b, _ in links)


def test_two_explicit_provisions_bind_the_passive_subject():
    law = make_chunks("Điều 1. Một", "A")
    decree = make_chunks("Điều 1. Giới thiệu", "Điều 1 của Luật mẫu 2026 được hướng dẫn tại Điều 2 của Nghị định này.",
                         "Điều 2. Chi tiết", "B", spec=DECREE)
    graph = build_graph([c.to_dict() for c in law + decree])
    links = {(e.source, e.target, e.type) for e in semantic(graph)}
    assert ("decree/article-2", "law/article-1", "GUIDES") in links
    assert ("decree/article-2", "decree/article-1", "GUIDES") not in links


def test_explicit_metadata_is_resolved_and_invalid_evidence_is_rejected():
    chunks = make_chunks("Điều 1. Phạm vi", "A") + make_chunks("Điều 1. Phạm vi", "Nội dung có dẫn chứng.", spec=DECREE)
    rows = [c.to_dict() for c in chunks]
    rows[-1]["references"] = [{"target": {"document_id": "law", "article": "1"},
                               "type": "GUIDES", "evidence": "Nội dung có dẫn chứng."}]
    assert any(e.type == "GUIDES" for e in build_graph(rows).edges)
    rows[-1]["references"][0]["evidence"] = "Không có trong nguồn"
    with pytest.raises(ValueError, match="evidence"):
        build_graph(rows)


def test_unknown_document_is_not_replaced_by_a_later_known_document():
    graph, _ = graph_for("Thực hiện theo Điều 1 của Luật khác và Điều 1 của Luật mẫu 2026.")
    assert graph.warnings
    assert len([e for e in semantic(graph) if e.target == "law/article-1"]) == 1


def test_negated_guidance_is_only_a_reference():
    graph, _ = graph_for("Điều này không hướng dẫn Điều 1 của Luật mẫu 2026.")
    assert {e.type for e in semantic(graph)} == {"REFERS_TO"}


def test_multiline_document_title_resolves_and_evidence_stays_verbatim():
    graph, _ = graph_for("Quy định chi tiết Điều 1 của Luật\nmẫu 2026.")
    assert any(e.type == "DETAILS" and e.target == "law/article-1" for e in semantic(graph))


def test_tampered_semantic_evidence_cannot_be_loaded_even_with_a_new_hash():
    graph, _ = graph_for("Quy định chi tiết Điều 1 của Luật mẫu 2026.")
    edges = tuple(replace(e, properties={"evidence_json": '[{"chunk_id":"missing","quote":"A","method":"rule"}]'})
                  if e.type == "DETAILS" else e for e in graph.edges)
    with pytest.raises(ValueError, match="evidence"):
        GraphPayload.from_dict(replace(graph, edges=edges).to_dict())


def test_reference_to_other_guiding_documents_is_not_itself_guidance():
    graph, _ = graph_for("Thực hiện theo Luật mẫu 2026 và các văn bản quy định chi tiết và hướng dẫn thi hành Luật mẫu 2026.")
    assert {e.type for e in semantic(graph)} == {"REFERS_TO"}


def test_reference_in_third_document_can_describe_two_other_documents():
    law = make_chunks("Điều 1. Nội dung", "A")
    decree = make_chunks("Điều 1. Nội dung", "B", spec=DECREE)
    circular = make_chunks("Điều 1. Nội dung", "Điều 1 của Luật mẫu 2026 được hướng dẫn tại Điều 1 của Nghị định 02/2026/NĐ-CP.",
                           spec=replace(DECREE, document_id="circular", title="Thông tư 03/2026/TT", document_number="03/2026/TT"))
    graph = build_graph([c.to_dict() for c in law + decree + circular])
    assert ("decree/article-1", "law/article-1", "GUIDES") in {(e.source, e.target, e.type) for e in semantic(graph)}


def test_provision_reference_is_rolled_up_to_documents_with_the_same_evidence():
    graph, chunk_id = graph_for("Thực hiện theo điểm a khoản 1 Điều 1 của Luật mẫu 2026.")
    links = {(e.source, e.target, e.type): e for e in semantic(graph)}
    provision = links[("decree/article-1", "law/article-1/clause-1/point-a", "REFERS_TO")]
    document = links[("decree", "law", "REFERS_TO")]
    assert document.properties == provision.properties
    assert json.loads(document.properties["evidence_json"])[0]["chunk_id"] == chunk_id
    assert not any(e.type in {"GUIDES", "DETAILS"} for e in semantic(graph))


def test_unqualified_law_name_does_not_resolve_to_a_newer_version_than_its_source():
    law = make_chunks("Điều 1. Phạm vi", "A")
    old_spec = replace(DECREE, title="Nghị định 02/2020/NĐ-CP", document_number="02/2020/NĐ-CP")
    decree = make_chunks("Điều 1. Nội dung", "Theo Điều 1 của Luật mẫu.", spec=old_spec)
    graph = build_graph([c.to_dict() for c in law + decree])
    assert not semantic(graph)
    assert graph.warnings


def test_explicit_version_in_a_quote_is_not_overridden_by_source_year_heuristic():
    law = make_chunks("Điều 1. Phạm vi", "A")
    old_spec = replace(DECREE, title="Nghị định 02/2020/NĐ-CP", document_number="02/2020/NĐ-CP")
    decree = make_chunks("Điều 1. Nội dung", "Theo Điều 1 của Luật mẫu 2026.", spec=old_spec)
    graph = build_graph([c.to_dict() for c in law + decree])
    assert ("decree", "law", "REFERS_TO") in {(e.source, e.target, e.type) for e in semantic(graph)}
