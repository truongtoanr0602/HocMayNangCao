"""Opt in with LEGAL_KG_INTEGRATION=1 and a disposable Neo4j test database."""
import os
import uuid

import pytest

from legal_kg.build import build_graph
from legal_kg.repository import fetch_context, load_graph
from test_kg_build import row


@pytest.mark.skipif(os.environ.get("LEGAL_KG_INTEGRATION") != "1", reason="Neo4j integration is opt-in")
def test_real_neo4j_idempotence_isolation_and_lookup():
    from neo4j import GraphDatabase

    password = os.environ["NEO4J_PASSWORD"]
    database = os.environ.get("NEO4J_TEST_DATABASE", "neo4j")
    unique_doc = "test-" + uuid.uuid4().hex
    first = build_graph([row(document_id=unique_doc, structure_path=[]),
                         row("c2", document_id=unique_doc, structure_path=[], chunk_index=2)])
    second = build_graph([row(document_id=unique_doc, structure_path=[], text="Phiên bản mới")])
    snapshots = [first.source_hash, second.source_hash]
    with GraphDatabase.driver(os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
                              auth=(os.environ.get("NEO4J_USER", "neo4j"), password)) as driver:
        driver.verify_connectivity()
        try:
            load_graph(first, driver, database=database, batch_size=1)
            load_graph(first, driver, database=database, batch_size=1)
            load_graph(second, driver, database=database)
            context = fetch_context(driver, first.source_hash, "c1", database=database)
            assert context["chunk"]["text"] == "Nội dung nguồn"
            assert [n["id"] for n in context["siblings"]] == ["c1", "c2"]
            assert context["path"][0]["id"] == unique_doc
            with driver.session(database=database) as session:
                record = session.run("MATCH (n:KGNode {snapshot_id: $id}) RETURN count(n) AS count",
                                     id=first.source_hash).single()
                assert record["count"] == 3
                assert session.run("MATCH (:KGNode {snapshot_id: $id})-[r]->() RETURN count(r) AS count",
                                   id=first.source_hash).single()["count"] == 2
        finally:
            # Only UUID-scoped snapshots created by this test are deleted.
            with driver.session(database=database) as session:
                session.run("MATCH (n:KGNode) WHERE n.snapshot_id IN $ids DETACH DELETE n", ids=snapshots).consume()
                session.run("MATCH (s:KGSnapshot) WHERE s.id IN $ids DELETE s", ids=snapshots).consume()


@pytest.mark.skipif(os.environ.get("LEGAL_KG_INTEGRATION") != "1", reason="Neo4j integration is opt-in")
def test_real_neo4j_vectors_are_idempotent_and_snapshot_scoped():
    from neo4j import GraphDatabase
    from legal_kg.repository import load_embeddings, vector_index_name, vector_search

    password = os.environ["NEO4J_PASSWORD"]
    database = os.environ.get("NEO4J_TEST_DATABASE", "neo4j")
    unique_doc = "test-" + uuid.uuid4().hex
    model_key = "test-" + uuid.uuid4().hex[:8]
    path = [{"type": "article", "number": "1", "title": "Điều một"}]
    first = build_graph([row(document_id=unique_doc, structure_path=path)])
    second = build_graph([row(document_id=unique_doc, structure_path=path, text="Phiên bản mới")])
    article = f"{unique_doc}/article-1"
    snapshots = [first.source_hash, second.source_hash]
    with GraphDatabase.driver(os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
                              auth=(os.environ.get("NEO4J_USER", "neo4j"), password)) as driver:
        driver.verify_connectivity()
        try:
            load_graph(first, driver, database=database)
            load_graph(second, driver, database=database)
            common = dict(model_key=model_key, model_id="test/model", revision="r1",
                          text_version="node-text-v1", database=database)
            load_embeddings(driver, first.source_hash, [article], [[1.0, 0.0, 0.0]], **common)
            report = load_embeddings(driver, first.source_hash, [article], [[1.0, 0.0, 0.0]], **common)
            assert report["dimension"] == 3 and report["nodes"] == 1
            load_embeddings(driver, second.source_hash, [article], [[0.0, 1.0, 0.0]], **common)
            hits = vector_search(driver, first.source_hash, model_key, [1.0, 0.0, 0.0], k=5, database=database)
            assert [h["id"] for h in hits] == [article] and hits[0]["score"] == pytest.approx(1.0)
            with pytest.raises(Exception):
                load_embeddings(driver, first.source_hash, ["missing-node"], [[1.0, 0.0, 0.0]], **common)
        finally:
            with driver.session(database=database) as session:
                session.run(f"DROP INDEX {vector_index_name(model_key)} IF EXISTS").consume()
                session.run("MATCH (n:KGNode) WHERE n.snapshot_id IN $ids DETACH DELETE n", ids=snapshots).consume()
                session.run("MATCH (s:KGSnapshot) WHERE s.id IN $ids DELETE s", ids=snapshots).consume()
