import pytest

np = pytest.importorskip('numpy')

from legal_kg.embedding_benchmark import token_windows, pool_vectors, evaluate, window_features


def test_window_features_add_special_tokens_without_reencoding_content():
    class Tokenizer:
        model_input_names = ['input_ids', 'attention_mask', 'token_type_ids']
        def encode(self, text, add_special_tokens):
            assert text == '' and add_special_tokens
            return [101, 102]
        def num_special_tokens_to_add(self, pair):
            return 2
    result = window_features(Tokenizer(), [20, 30, 40])
    assert result == {'input_ids': [101, 20, 30, 40, 102],
                      'attention_mask': [1]*5, 'token_type_ids': [0]*5}


def test_token_windows_cover_tail_with_correct_unique_weights():
    ids = list(range(23))
    windows = token_windows(ids, 8, 2)
    assert set(x for chunk, _ in windows for x in chunk) == set(ids)
    assert sum(weight for _, weight in windows) == len(ids)
    assert windows[-1][0][-1] == 22
    assert all(len(chunk) <= 8 for chunk, _ in windows)
    with pytest.raises(ValueError):
        token_windows(ids, 8, 8)


def test_pooling_normalizes_and_accounts_for_short_tail():
    vector = pool_vectors(np.array([[1., 0.], [0., 1.]]), [3, 1])
    assert np.allclose(vector, np.array([3., 1.]) / np.sqrt(10))
    with pytest.raises(ValueError):
        pool_vectors(np.zeros((1, 2)), [1])


def test_metrics_distinguish_primary_and_all_required_groups():
    questions = [
        {'question_id': 'one', 'answerable': True, 'evidence_groups': [
            {'primary_node_id': 'a', 'acceptable_node_ids': ['a', 'parent']}]},
        {'question_id': 'two', 'answerable': True, 'evidence_groups': [
            {'primary_node_id': 'b', 'acceptable_node_ids': ['b']},
            {'primary_node_id': 'c', 'acceptable_node_ids': ['c']}]},
        {'question_id': 'none', 'answerable': False, 'evidence_groups': []},
    ]
    result = evaluate(questions, {'one': ['parent', 'a'], 'two': ['b', 'c'], 'none': ['a']}, ks=(1, 2))
    assert result['answerable_questions'] == 2
    assert result['by_k']['1']['group_recall_macro'] == .75
    assert result['by_k']['1']['all_groups_hit_rate'] == .5
    assert result['by_k']['1']['primary_group_recall_macro'] == .25
    assert result['by_k']['2']['all_groups_hit_rate'] == 1
    assert result['single_group_mrr_at_max_k'] == 1
