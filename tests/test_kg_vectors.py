import pytest

from legal_kg.repository import _validated_vectors, embedding_property, vector_index_name


def test_model_keys_map_to_safe_property_and_index_names():
    assert embedding_property("e5-small") == "embedding_e5_small"
    assert vector_index_name("bge-m3") == "kg_node_embedding_bge_m3"
    for bad in ["", "E5", "x y", "a;DROP", "-lead", "a" * 41, None]:
        with pytest.raises(ValueError):
            embedding_property(bad)


@pytest.mark.parametrize("ids,vectors", [
    ([], []), (["a", "a"], [[1.0], [1.0]]), (["a"], [[1.0], [1.0]]),
    (["a", "b"], [[1.0, 0.0], [1.0]]), (["a"], [[float("nan")]]), (["a"], [[0.0, 0.0]]),
])
def test_vector_validation_rejects_bad_batches(ids, vectors):
    with pytest.raises(ValueError):
        _validated_vectors(ids, vectors)


def test_vector_validation_returns_dimension():
    assert _validated_vectors(["a", "b"], [[1, 0], [0, 1]]) == (["a", "b"], [[1.0, 0.0], [0.0, 1.0]], 2)
