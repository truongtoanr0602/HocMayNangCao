import pytest

from legal_kg.build import build_graph
from legal_kg.kg_expansion import Neighbourhood, apply_budget, expand
from legal_kg.router import DirectRouter
from test_kg_build import row

POINT = "doc-01/article-10/clause-1/point-%C4%91"
CLAUSE_10 = "doc-01/article-10/clause-1"
ARTICLE_10 = "doc-01/article-10"
CLAUSE_11 = "doc-01/article-11/clause-2"
ARTICLE_11 = "doc-01/article-11"
OTHER = "doc-02/article-10"


def path(*parts):
    return [dict(zip(("type", "number", "title"), part)) for part in parts]


@pytest.fixture(scope="module")
def graph():
    article_10, article_11 = ("article", "10", "Điều mười"), ("article", "11", "Điều mười một")
    return build_graph([
        row("c1", text="đ) Điểm đ", structure_path=path(article_10, ("clause", "1", "1. Khoản một"),
                                                        ("point", "đ", "đ) Điểm đ"))),
        row("c2", chunk_index=2, text="Khoản hai theo quy định tại Điều 10 của Văn bản này.",
            structure_path=path(article_11, ("clause", "2", "2. Khoản hai")),
            references=[{"type": "REFERS_TO", "target": {"document_id": "doc-01", "article": "10"},
                         "evidence": "quy định tại Điều 10"}]),
        row("d2", document_id="doc-02", title="Nghị định khác 2026", document_number="02/2026/NĐ-CP",
            short_title="NĐ 02/2026", text="x", structure_path=path(("article", "10", "Điều mười"))),
    ])


def test_expansions_add_parent_article_then_semantic_neighbours_in_both_directions(graph):
    hood = Neighbourhood(graph)
    assert hood.article(POINT) == ARTICLE_10
    assert hood.expansions(CLAUSE_11) == [ARTICLE_11, ARTICLE_10]  # outgoing REFERS_TO
    assert hood.expansions(ARTICLE_10) == [CLAUSE_11]  # incoming edge, no parent for an Article


def test_expand_puts_expansions_after_seeds_and_deduplicates(graph):
    hood = Neighbourhood(graph)
    candidates = {POINT, CLAUSE_10, ARTICLE_10, CLAUSE_11, ARTICLE_11, OTHER}
    dense = [(CLAUSE_11, .9), (POINT, .8), (OTHER, .7), (ARTICLE_10, .6)]
    ranked = expand(dense, hood, seeds=2, decay=.5, candidates=candidates)
    # Seeds, then ARTICLE_11/ARTICLE_10 (.45, seed 0) before nothing new from POINT, then dense tail.
    assert [n for n, _ in ranked] == [CLAUSE_11, POINT, ARTICLE_11, ARTICLE_10, OTHER]
    assert dict(ranked)[ARTICLE_11] == pytest.approx(.45)
    assert expand(dense, hood, seeds=2, decay=.5, candidates={CLAUSE_11, POINT, OTHER}) == [
        (CLAUSE_11, .9), (POINT, .8), (OTHER, .7), (ARTICLE_10, .6)]


def test_budget_limits_nodes_and_characters_and_skips_oversized_nodes():
    ranked = [("a", 1.), ("big", .9), ("b", .8), ("a", .7), ("c", .6), ("d", .5)]
    chars = {"a": 4, "big": 100, "b": 4, "c": 4, "d": 1}
    assert [n for n, _ in apply_budget(ranked, chars, max_nodes=3, max_chars=10)] == ["a", "b", "d"]
    assert [n for n, _ in apply_budget(ranked, chars, max_nodes=2, max_chars=1000)] == ["a", "big"]


@pytest.mark.parametrize("question,expected", [
    ("Điểm đ khoản 1 Điều 10 Văn bản quy định gì?", [POINT]),
    ("điem đ khoan 1 dieu 10 van ban", [POINT]),
    ("Khoản 1 Điều 10 01/2026 nói gì?", [CLAUSE_10]),
    ("Điều 10 NĐ 02/2026 quy định gì?", [OTHER]),
    ("Điều 10 Nghị định khác quy định gì?", [OTHER]),
    ("Khoản 9 Điều 10 Văn bản", [ARTICLE_10]),
    ("Điều 10 và Điều 11 Văn bản", [ARTICLE_10, ARTICLE_11]),
])
def test_router_resolves_explicit_addresses(graph, question, expected):
    assert DirectRouter(graph).route(question) == expected


@pytest.mark.parametrize("question", [
    "Điều 10 quy định gì?",                       # no document named
    "Điều 99 Văn bản",                            # article missing
    "Điều 10 Văn bản và NĐ 02/2026",              # two documents
    "Người lao động được nghỉ mấy ngày?",         # no address
])
def test_router_returns_nothing_when_unsure(graph, question):
    assert DirectRouter(graph).route(question) == []
