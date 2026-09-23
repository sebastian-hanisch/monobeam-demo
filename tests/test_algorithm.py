"""Die zentrale Korrektheits-Kette für Monobeam: gültiger Pfad, Kosten nie unter dem Optimum (gegen Brute-Force), das
Präfix-Lemma des Papers DIREKT (Strahlinhalt der Plätze 1..a ist bei Breite a und b > a gleich), der Monotonie-Satz (Kosten
nicht steigend in der Breite, inf zählt) auf Raster, handgebauten und 1500 zufälligen kleinen Graphen mit nicht konsistenter
Heuristik, Optimalität bei unbegrenzter Breite (wo Beam die wenigsten KANTEN liefert), Inkumbent-Pruning (nur Effizienz),
Pathmax, Buchführung, die drei handgebauten Instanzen und die gemessenen Ablationen (naive Duplikate, Stoppregel)."""

import numpy as np
import pytest

import mono_algorithm as A
import mono_graph as G
import mono_scenario as S

EPS = 1e-9
HUGE = 10 ** 6
UNLIMITED = 2000
INF = float("inf")
WIDTHS = list(range(1, 25))


def _brute_force_shortest_cost(graph, start, goal):
    best = None
    stack = [(start, [start], 0.0)]
    while stack:
        node, path, cost = stack.pop()
        if node == goal:
            if best is None or cost < best:
                best = cost
            continue
        for v, w in zip(graph.neighbors[node], graph.weights[node]):
            if v not in path:
                stack.append((v, path + [v], cost + w))
    return best


def _non_increasing(costs):
    return all(costs[j] <= costs[i] + 1e-9 for i in range(len(costs)) for j in range(i + 1, len(costs)))


def _random_layered_instance(seed):
    """Kleiner zufälliger Schichtgraph (<= 11 Knoten) mit ganzzahligen Gewichten und einer zulässigen, meist NICHT
    konsistenten Heuristik h = floor(Restweg * Faktor)."""
    rng = np.random.default_rng(seed)
    sizes = [1] + [int(rng.integers(1, 4)) for _ in range(int(rng.integers(2, 4)))] + [1]
    ids, k = [], 0
    for s in sizes:
        ids.append(list(range(k, k + s)))
        k += s
    edges = []
    for a, b in zip(ids[:-1], ids[1:]):
        has_out = set()
        for v in b:
            for u in rng.choice(a, size=int(rng.integers(1, min(2, len(a)) + 1)), replace=False):
                edges.append((int(u), int(v), float(rng.integers(1, 6))))
                has_out.add(int(u))
        for u in a:
            if u not in has_out:
                edges.append((int(u), int(rng.choice(b)), float(rng.integers(1, 6))))
    graph = G.from_edges(k, [(i, 0.0) for i in range(k)], edges)
    goal = k - 1
    d = np.array([A.uniform_cost_search(graph, v, goal).cost for v in range(k)])
    h = np.floor(d * rng.uniform(0.2, 1.0, k))
    h[goal] = 0
    return graph, 0, goal, h


# --- Gültigkeit und Untergrenze ---------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("dedup", ["slot", "full"])
@pytest.mark.parametrize("cont", [True, False])
@pytest.mark.parametrize("width", [1, 2, 3, 5, 8])
@pytest.mark.parametrize("seed", range(6))
def test_monobeam_returns_a_valid_simple_path_with_recomputed_cost(seed, width, cont, dedup):
    inst = S.grid_instance(side=6, obstacle_pct=20, seed=seed)
    result = A.monobeam_search(inst.graph, inst.start, inst.goal, width, dedup=dedup, continue_after_goal=cont)
    if result.failed:
        assert result.path == [] and result.cost == INF and not result.capped
        return
    assert result.path[0] == inst.start and result.path[-1] == inst.goal
    assert len(set(result.path)) == len(result.path)
    for u, v in zip(result.path[:-1], result.path[1:]):
        assert v in inst.graph.neighbors[u]
    assert G.path_cost(inst.graph, result.path) == pytest.approx(result.cost, abs=1e-6)


@pytest.mark.parametrize("width", [1, 2, 3, 5, 8])
@pytest.mark.parametrize("seed", range(12))
def test_monobeam_never_beats_the_brute_force_optimum(seed, width):
    inst = S.grid_instance(side=5, obstacle_pct=15, seed=seed)
    result = A.monobeam_search(inst.graph, inst.start, inst.goal, width)
    if not result.failed:
        assert result.cost >= _brute_force_shortest_cost(inst.graph, inst.start, inst.goal) - 1e-6


def test_monobeam_is_deterministic():
    inst = S.grid_instance(side=8, obstacle_pct=20, seed=3)
    r1 = A.monobeam_search(inst.graph, inst.start, inst.goal, 4)
    r2 = A.monobeam_search(inst.graph, inst.start, inst.goal, 4)
    assert r1.path == r2.path and r1.order == r2.order and r1.per_level == r2.per_level


def test_invalid_arguments_are_rejected():
    inst = S.grid_instance(side=5, obstacle_pct=0, seed=1)
    with pytest.raises(ValueError):
        A.monobeam_search(inst.graph, inst.start, inst.goal, 0)
    with pytest.raises(ValueError):
        A.monobeam_search(inst.graph, inst.start, inst.goal, 2, dedup="x")


def test_start_equals_goal_and_unreachable_goal():
    inst = S.grid_instance(side=5, obstacle_pct=0, seed=1)
    trivial = A.monobeam_search(inst.graph, inst.start, inst.start, 3)
    assert trivial.path == [inst.start] and trivial.cost == 0.0 and trivial.expansions == 0 and not trivial.failed
    graph = G.from_edges(4, [(0, 0), (1, 0), (2, 0), (3, 0)], [(0, 1, 1.0), (2, 3, 1.0)])
    for width in (1, 3, HUGE):
        result = A.monobeam_search(graph, 0, 3, width)
        assert result.failed and result.path == [] and result.cost == INF and not result.capped


@pytest.mark.parametrize("width", [1, 2, 5, HUGE])
def test_chain_graph_is_solved_by_every_width(width):
    n = 7
    graph = G.from_edges(n, [(i, 0) for i in range(n)], [(i, i + 1, 1.0) for i in range(n - 1)])
    result = A.monobeam_search(graph, 0, n - 1, width)
    assert result.path == list(range(n)) and result.cost == n - 1 and not result.failed


# --- Präfix-Lemma (Lemma 1/2) direkt --------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("obstacle", [0, 15, 40])
@pytest.mark.parametrize("seed", range(12))
def test_prefix_lemma_beam_of_width_a_is_a_prefix_of_the_beam_of_width_b(seed, obstacle):
    """Mit `prune=False` (kein Inkumbent-Einfluss): Strahlinhalt je Ebene bei Breite a == erste a Plätze bei Breite b > a."""
    inst = S.grid_instance(side=12, obstacle_pct=obstacle, seed=300000 + seed)
    runs = {k: A.monobeam_search(inst.graph, inst.start, inst.goal, k, prune=False) for k in (1, 2, 3, 5, 8)}
    ks = sorted(runs)
    compared = 0
    for a, b in zip(ks[:-1], ks[1:]):
        for lvl in range(min(runs[a].levels, runs[b].levels)):
            assert runs[a].per_level[lvl][:a] == runs[b].per_level[lvl][:a]
            compared += 1
    assert compared > 20


@pytest.mark.parametrize("name", list(S.HAND_BUILT))
def test_prefix_lemma_on_the_hand_built_instances(name):
    inst = S.HAND_BUILT[name]()
    runs = {k: A.monobeam_search(inst.graph, inst.start, inst.goal, k, prune=False, h=inst.h) for k in (1, 2, 3, 4)}
    for a, b in ((1, 2), (2, 3), (3, 4)):
        for lvl in range(min(runs[a].levels, runs[b].levels)):
            assert runs[a].per_level[lvl][:a] == runs[b].per_level[lvl][:a]


# --- Monotonie-Satz (Satz 1-3) --------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("obstacle", [0, 15, 40])
@pytest.mark.parametrize("seed", range(25))
def test_monobeam_cost_never_increases_with_width_on_grids(seed, obstacle):
    inst = S.grid_instance(side=10, obstacle_pct=obstacle, seed=200000 + seed)
    costs = [A.monobeam_search(inst.graph, inst.start, inst.goal, k).cost for k in WIDTHS]
    assert _non_increasing(costs), costs                                   # inf zählt: kein Scheitern nach Erfolg


@pytest.mark.parametrize("name", list(S.HAND_BUILT))
def test_monobeam_cost_never_increases_with_width_on_the_hand_built_instances(name):
    inst = S.HAND_BUILT[name]()
    costs = [A.monobeam_search(inst.graph, inst.start, inst.goal, k, h=inst.h).cost for k in range(1, 9)]
    assert _non_increasing(costs), costs


def test_monobeam_is_monotone_on_1500_random_small_graphs_with_an_inconsistent_heuristic():
    for seed in range(1500):
        graph, start, goal, h = _random_layered_instance(seed)
        costs = [A.monobeam_search(graph, start, goal, k, h=h).cost for k in range(1, 6)]
        assert _non_increasing(costs), (seed, costs)


# --- Unbegrenzte Breite: optimal (Beam: die wenigsten Kanten) ----------------------------------------------------------------------------


@pytest.mark.parametrize("obstacle", [0, 15, 40])
@pytest.mark.parametrize("seed", range(40))
def test_unlimited_width_monobeam_is_optimal_on_grids(seed, obstacle):
    inst = S.grid_instance(side=12, obstacle_pct=obstacle, seed=300000 + seed)
    result = A.monobeam_search(inst.graph, inst.start, inst.goal, UNLIMITED)                # weit über jeder Kandidatenzahl einer Ebene
    assert not result.failed and result.cost == pytest.approx(A.uniform_cost_search(inst.graph, inst.start, inst.goal).cost, abs=EPS)


def test_detour_instance_beam_returns_fewest_edges_but_monobeam_the_optimum():
    inst = S.detour_instance()
    assert A.uniform_cost_search(inst.graph, inst.start, inst.goal).cost == 3.0
    for width in (1, 2, 5, HUGE):
        assert A.beam_search(inst.graph, inst.start, inst.goal, width, "f").cost == 10.0
        assert A.monobeam_search(inst.graph, inst.start, inst.goal, width).cost == 3.0


# --- Inkumbent-Pruning (Alg. 2, Lemma 4) und Pathmax ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("width", [3, 8])
@pytest.mark.parametrize("seed", range(15))
def test_pruning_changes_only_the_effort_not_the_cost(seed, width):
    inst = S.grid_instance(side=12, obstacle_pct=15, seed=200000 + seed)
    on = A.monobeam_search(inst.graph, inst.start, inst.goal, width, prune=True)
    off = A.monobeam_search(inst.graph, inst.start, inst.goal, width, prune=False)
    assert on.cost == off.cost and on.failed == off.failed
    assert on.expansions <= off.expansions


@pytest.mark.parametrize("seed", range(15))
def test_pathmax_never_fires_on_the_grid_and_switching_it_off_changes_nothing(seed):
    inst = S.grid_instance(side=12, obstacle_pct=15, seed=200000 + seed)
    for width in (4, 12):
        with_pm = A.monobeam_search(inst.graph, inst.start, inst.goal, width)
        without = A.monobeam_search(inst.graph, inst.start, inst.goal, width, pathmax=False)
        assert with_pm.pathmax_fired == 0 and with_pm.cost == without.cost and with_pm.expansions == without.expansions


def test_pathmax_fires_on_the_instances_with_an_inconsistent_heuristic():
    for name, width in (("cuckoo", 2), ("stop", 2)):
        inst = S.HAND_BUILT[name]()
        assert A.monobeam_search(inst.graph, inst.start, inst.goal, width, h=inst.h).pathmax_fired > 0


# --- Buchführung -----------------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("width", [1, 3, 6])
@pytest.mark.parametrize("seed", range(10))
def test_level_bookkeeping_is_consistent(seed, width):
    inst = S.grid_instance(side=8, obstacle_pct=15, seed=seed)
    result = A.monobeam_search(inst.graph, inst.start, inst.goal, width)
    assert not result.capped
    assert all(len(level) == width for level in result.per_level)
    assert all(level[0] is not None or not any(level) for level in result.per_level[:1])      # Ebene 0: nur der Start auf Platz 1
    assert sum(s is not None for level in result.per_level for s in level) == result.expansions == len(result.order)
    assert result.levels == len(result.per_level) and result.stored <= inst.graph.n
    if not result.failed:
        assert result.levels >= len(result.path) - 1                        # Weitersuchen nach dem Zielfund kann die Ebenenzahl nur erhöhen


# --- Handgebaute Instanzen ------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["cuckoo", "stop"])
def test_hand_built_heuristics_are_admissible_but_not_consistent(name):
    inst = S.HAND_BUILT[name]()
    g, h = inst.graph, inst.h
    d = np.array([A.uniform_cost_search(g, v, inst.goal).cost for v in range(g.n)])
    assert np.all(h <= d + EPS) and h[inst.goal] == 0
    assert any(h[u] > w + h[v] + EPS for u in range(g.n) for v, w in zip(g.neighbors[u], g.weights[u]))


def test_cuckoo_instance_beam_gets_worse_with_width_two_and_monobeam_does_not():
    inst = S.cuckoo_instance()
    beam = [A.beam_search(inst.graph, inst.start, inst.goal, k, "f", h=inst.h).cost for k in (1, 2, 3, 4)]
    mono = [A.monobeam_search(inst.graph, inst.start, inst.goal, k, h=inst.h).cost for k in (1, 2, 3, 4)]
    assert beam == [7.0, 8.0, 7.0, 7.0] and mono == [7.0, 7.0, 7.0, 7.0]


def test_stop_instance_needs_the_continue_rule():
    inst = S.stop_instance()
    level = [A.monobeam_search(inst.graph, inst.start, inst.goal, k, continue_after_goal=False, h=inst.h).cost for k in (1, 2, 3, 4)]
    paper = [A.monobeam_search(inst.graph, inst.start, inst.goal, k, h=inst.h).cost for k in (1, 2, 3, 4)]
    assert level == [6.0, 9.0, 8.0, 8.0] and paper == [6.0, 6.0, 6.0, 6.0]


# --- Ablation: die plätze-bewusste Duplikatregel ist nötig (gemessen) ----------------------------------------------------------------------


def test_naive_full_beam_duplicates_make_a_wider_run_fail_where_a_narrower_one_succeeds():
    inst = S.grid_instance(side=12, obstacle_pct=15, seed=200019)
    full = [A.monobeam_search(inst.graph, inst.start, inst.goal, k, dedup="full").cost for k in (1, 2, 3)]
    slot = [A.monobeam_search(inst.graph, inst.start, inst.goal, k, dedup="slot").cost for k in (1, 2, 3)]
    assert full[0] < INF and full[1] == INF and full[2] < INF              # Breite 2 scheitert nach Erfolg mit Breite 1
    assert _non_increasing(slot) and slot[1] < INF


# --- Kopie treu und geerbte Eigenschaften -----------------------------------------------------------------------------------------------------


def test_beam_search_copy_reproduces_the_beam_search_demo_numbers():
    inst = S.grid_instance(side=12, obstacle_pct=15, seed=35)
    f3 = A.beam_search(inst.graph, inst.start, inst.goal, 3, "f")
    h8 = A.beam_search(inst.graph, inst.start, inst.goal, 8, "h")
    assert f3.cost == pytest.approx(175.90, abs=0.01) and f3.expansions == 63
    assert h8.cost == pytest.approx(175.90, abs=0.01) and h8.expansions == 118


def test_inherited_heuristic_is_admissible_and_a_star_is_optimal():
    for seed in range(10):
        inst = S.grid_instance(side=7, obstacle_pct=20, seed=seed)
        h = A.heuristic(inst.graph.xy, inst.goal)
        ucs = A.uniform_cost_search(inst.graph, inst.start, inst.goal)
        for node in range(inst.graph.n):
            assert h[node] <= A.uniform_cost_search(inst.graph, node, inst.goal).cost + EPS
        assert A.a_star(inst.graph, inst.start, inst.goal).cost == pytest.approx(ucs.cost, abs=EPS)
