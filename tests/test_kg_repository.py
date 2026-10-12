import copy

import pytest

from legal_kg.build import build_graph
from legal_kg.repository import LoadError, load_graph
from test_kg_build import row


class Result:
    def __init__(self, records=()):
        self.records = records

    def consume(self):
        return None

    def single(self):
        return self.records[0] if self.records else None


class Driver:
    """Transaction double: stages state and commits only if callback succeeds."""
    def __init__(self, fail_edges=False):
        self.nodes = {}
        self.edges = set()
        self.snapshots = {}
        self.fail_edges = fail_edges

    def session(self, **kwargs):
        return Session(self)


class Session:
    def __init__(self, driver):
        self.driver = driver

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def run(self, query, **params):
        assert query.startswith("CREATE CONSTRAINT")
        return Result()

    def execute_write(self, callback, *args):
        staged = copy.deepcopy(self.driver)
        value = callback(Transaction(staged), *args)
        self.driver.nodes, self.driver.edges, self.driver.snapshots = staged.nodes, staged.edges, staged.snapshots
        return value


class Transaction:
    def __init__(self, driver):
        self.driver = driver

    def run(self, query, **params):
        snapshot = params.get("snapshot_id")
        if "MERGE (s:KGSnapshot" in query:
            record = self.driver.snapshots.setdefault(snapshot, {"graph_hash": params["graph_hash"], "state": "loading"})
            return Result([record])
        if "SET s.state = 'ready'" in query:
            self.driver.snapshots[snapshot]["state"] = "ready"
        elif "UNWIND $nodes" in query:
            # Parameters carry text; source text must not be interpolated into Cypher.
            for n in params["nodes"]:
                assert n["properties"]["document_id"] not in query
                self.driver.nodes[(snapshot, n["id"])] = n
        elif "UNWIND $edges" in query:
            if self.driver.fail_edges:
                raise RuntimeError("Database failure")
            for e in params["edges"]:
                assert (snapshot, e["source"]) in self.driver.nodes
                assert (snapshot, e["target"]) in self.driver.nodes
                self.driver.edges.add((snapshot, e["source"], e["target"], params["edge_type"]))
            return Result([{"written": len(params["edges"])}])
        else:
            raise AssertionError(query)
        return Result()


def test_loading_twice_is_idempotent_and_preserves_chunk_ids():
    graph = build_graph([row(structure_path=[])])
    driver = Driver()
    result = load_graph(graph, driver, batch_size=1)
    load_graph(graph, driver, batch_size=1)
    assert result.chunk_count == 1
    assert len(driver.nodes) == 2
    assert len(driver.edges) == 1
    assert (graph.source_hash, "c1") in driver.nodes
    assert driver.snapshots[graph.source_hash]["state"] == "ready"


def test_transaction_failure_rolls_back_entire_graph():
    graph = build_graph([row(structure_path=[])])
    driver = Driver(fail_edges=True)
    with pytest.raises(LoadError, match="c1"):
        load_graph(graph, driver)
    assert not driver.nodes and not driver.edges and not driver.snapshots


def test_new_snapshot_is_isolated_from_old_snapshot():
    driver = Driver()
    first = build_graph([row(structure_path=[])])
    second = build_graph([row(structure_path=[], text="Nội dung mới")])
    load_graph(first, driver)
    load_graph(second, driver)
    assert len(driver.nodes) == 4
    assert driver.nodes[(first.source_hash, "c1")]["properties"]["text"] == "Nội dung nguồn"
    assert driver.nodes[(second.source_hash, "c1")]["properties"]["text"] == "Nội dung mới"


def test_legacy_requires_explicit_acknowledgement_before_writing():
    graph = build_graph([row()])
    driver = Driver()
    with pytest.raises(ValueError, match="legacy"):
        load_graph(graph, driver)
    assert not driver.nodes
    assert load_graph(graph, driver, allow_legacy_metadata=True).chunk_count == 1


def test_same_snapshot_cannot_be_overwritten_with_different_graph():
    graph = build_graph([row(structure_path=[])])
    driver = Driver()
    driver.snapshots[graph.source_hash] = {"graph_hash": "different", "state": "ready"}
    with pytest.raises(LoadError, match="different graph"):
        load_graph(graph, driver)
    assert not driver.nodes


def test_invalid_batch_size_is_rejected():
    with pytest.raises(ValueError, match="batch_size"):
        load_graph(build_graph([row(structure_path=[])]), Driver(), batch_size=0)
