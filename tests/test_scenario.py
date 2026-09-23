import numpy as np
import pytest

import mono_graph as G
import mono_scenario as S


@pytest.mark.parametrize("seed", range(30))
def test_start_and_goal_are_always_connected(seed):
    inst = S.grid_instance(side=10, obstacle_pct=35, seed=seed)
    assert _bfs_connected(inst.graph, inst.start, inst.goal)


def _bfs_connected(graph, start, goal):
    seen = {start}
    stack = [start]
    while stack:
        u = stack.pop()
        if u == goal:
            return True
        for v in graph.neighbors[u]:
            if v not in seen:
                seen.add(v)
                stack.append(v)
    return goal in seen


@pytest.mark.parametrize("seed", range(10))
def test_edge_weights_match_euclidean_distance_between_endpoints(seed):
    inst = S.grid_instance(side=10, obstacle_pct=20, seed=seed)
    xy = inst.graph.xy
    for u in range(inst.graph.n):
        for v, w in zip(inst.graph.neighbors[u], inst.graph.weights[u]):
            expected = float(np.hypot(*(xy[u] - xy[v])))
            assert w == pytest.approx(expected, abs=1e-9)


def test_higher_obstacle_percent_blocks_more_cells_on_average():
    low = [len(S.grid_instance(side=14, obstacle_pct=5, seed=s).blocked_xy) for s in range(10)]
    high = [len(S.grid_instance(side=14, obstacle_pct=35, seed=s).blocked_xy) for s in range(10)]
    assert np.mean(high) > np.mean(low)


def test_zero_obstacle_percent_leaves_every_cell_open():
    inst = S.grid_instance(side=10, obstacle_pct=0, seed=1)
    assert len(inst.blocked_xy) == 0
    assert inst.graph.n == 100


def test_no_isolated_edges_shorter_than_zero():
    inst = S.grid_instance(side=12, obstacle_pct=30, seed=7)
    for u in range(inst.graph.n):
        for w in inst.graph.weights[u]:
            assert w > 0


@pytest.mark.parametrize("name,n", [("cuckoo", 8), ("stop", 9), ("detour", 4)])
def test_hand_built_instances_have_the_expected_shape(name, n):
    inst = S.HAND_BUILT[name]()
    assert inst.graph.n == n and len(inst.labels) == n and inst.labels[0] == "S" and inst.labels[-1] == "Z"
    assert inst.start == 0 and inst.goal == n - 1 and _bfs_connected(inst.graph, inst.start, inst.goal)
    assert len(inst.blocked_xy) == 0
    assert (inst.h is None) == (name == "detour") and (inst.h is None or len(inst.h) == n)


def test_the_grid_instance_has_no_explicit_heuristic_or_labels():
    inst = S.grid_instance(side=6, obstacle_pct=10, seed=1)
    assert inst.h is None and inst.labels is None


def test_path_cost_matches_a_hand_walked_path_on_the_detour_instance():
    inst = S.detour_instance()
    assert G.path_cost(inst.graph, [0, 1, 2, 3]) == pytest.approx(3.0) and G.path_cost(inst.graph, [0, 3]) == pytest.approx(10.0)
