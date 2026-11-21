import pytest

from osler.adaptive_planning import incidence_weights


DAY = '2026-10-15'
PARENT = ['Área', 'Tema']


def dataset(rows, institution='A', dataset_id=1):
    return {'id': dataset_id, 'institutions': [institution], 'unit': 'questoes', 'observed_date': DAY,
            'rows': [{'path': path, 'value': count, 'band': 'baixa'} for path, count in rows]}


@pytest.mark.parametrize(('left', 'right', 'expected'), [
    (90, 10, [.9, .1]), (1, 99, [.01, .99]), (0, None, [.5, .5]),
])
def test_parent_mass_is_conserved_and_distributed_by_bank_size(left, right, expected):
    topics = [{'topic_id': key, 'path': PARENT + [key], 'total': count}
              for key, count in zip(('a', 'b'), (left, right))]
    result = incidence_weights(topics, [dataset([(PARENT, 10)])], {}, DAY)
    assert list(result['weights'].values()) == pytest.approx(expected)
    assert sum(result['weights'].values()) == pytest.approx(1)
    assert result['theme_weights'] == {'a': 1, 'b': 1}


def test_theme_ranking_normalizes_sources_and_keeps_exploration_separate():
    nodes = [PARENT, ['Área', 'Outro tema'], ['Área', 'Sem fonte']]
    topics = [{'topic_id': key, 'path': node + ['Subtema'], 'theme_path': node, 'total': 20}
              for key, node in zip(('a', 'b', 'c'), nodes)]
    tables = [dataset([(PARENT, 10), (topics[0]['path'], 4), (nodes[1], 30)]),
              dataset([(PARENT, 900), (nodes[1], 100)], institution='B', dataset_id=2)]
    result = incidence_weights(topics, tables, {'A': 1, 'B': 3}, DAY)
    assert result['theme_weights'] == pytest.approx({'a': .25*.25 + .75*.9, 'b': .25*.75 + .75*.1, 'c': 0})
    assert result['weights']['c'] > 0


def test_fragment_group_conserves_member_mass_instead_of_reclaiming_whole_parent():
    members = [{'topic_id': str(i), 'path': PARENT + [str(i)], 'total': 2} for i in range(5)]
    major = {'topic_id': 'large', 'path': PARENT + ['Principal'], 'total': 90}
    group = {'topic_id': 'group', 'path': PARENT + ['Subtemas menores'], 'total': 10,
             'theme_path': PARENT, 'group_member_topics': members, 'rollup': True}
    tables = [dataset([(PARENT, 36), (members[0]['path'], 9)])]
    separate = incidence_weights([major, *members], tables, {}, DAY)
    grouped = incidence_weights([major, group], tables, {}, DAY)
    assert grouped['weights']['group'] == pytest.approx(sum(separate['weights'][m['topic_id']] for m in members))
    assert grouped['weights']['large'] == pytest.approx(separate['weights']['large'])
    assert sum(grouped['weights'].values()) == pytest.approx(1.)
