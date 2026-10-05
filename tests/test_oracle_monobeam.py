"""Unabhängiges Orakel für Monobeam und das kopierte Beam: Beam gegen eine Neuimplementierung (Dict statt Strahlliste),
Monobeam gegen networkx-Dijkstra (Untergrenze, Pfadkosten über networkx-Gewichte), Monotonie in der Breite und Präfix-Lemma
auf zufälligen zyklischen Graphen mit zulässiger, NICHT konsistenter Heuristik, Optimalität bei unbegrenzter Breite bei
konsistenter Heuristik - und der Gegenfall von Hand gerechnet: mit Pathmax und f-basierter Duplikatregel kann die
unbegrenzte Breite das Optimum verfehlen."""

import math
import random

import numpy as np
import pytest

import mono_algorithm as A
import mono_graph as G
import mono_scenario as S

nx = pytest.importorskip("networkx")
INF = math.inf


def _nx(graph):
    g = nx.Graph()
    g.add_nodes_from(range(graph.n))
    for u in range(graph.n):
        for v, w in zip(graph.neighbors[u], graph.weights[u]):
            g.add_edge(u, v, weight=w)
    return g


def _random_graph(rnd, mode):
    n = rnd.randint(2, 9)
    edges = [(u, v, float(rnd.randint(1, 6))) for u, v in
             ((rnd.randrange(n), rnd.randrange(n)) for _ in range(rnd.randint(n - 1, 2 * n))) if u != v]
    graph = G.from_edges(n, [(0, 0)] * n, edges)
    g, t = _nx(graph), n - 1
    d = np.array([nx.dijkstra_path_length(g, v, t) if nx.has_path(g, v, t) else 0.0 for v in range(n)])
    if mode == "inconsistent":
        h = np.array([0.0 if v == t else math.floor(d[v] * rnd.uniform(0.0, 1.0)) for v in range(n)])
    else:
        h = 0.5 * d if mode == "half" else d
    return graph, 0, t, h, g


def _clean_beam(graph, s, t, width, h, rank):
    if s == t:
        return [s], 0.0
    beam, g, par, expanded = [s], {s: 0.0}, {s: None}, set()
    while True:
        expanded.update(beam)
        cand = {}
        for u in beam:
            for v, w in zip(graph.neighbors[u], graph.weights[u]):
                if v not in expanded and (v not in cand or g[u] + w < cand[v][0]):
                    cand[v] = (g[u] + w, u)
        if t in cand:
            path, cur = [t], cand[t][1]
            while cur is not None:
                path.append(cur)
                cur = par[cur]
            return path[::-1], cand[t][0]
        if not cand:
            return [], INF
        key = (lambda v: (h[v], v)) if rank == "h" else (lambda v: (cand[v][0] + h[v], v))
        ranked = sorted(cand, key=key)[:width]
        for v in ranked:
            g[v], par[v] = cand[v]
        beam = ranked


def test_beam_copy_matches_a_clean_reimplementation():
    rnd = random.Random(21)
    for _ in range(150):
        graph, s, t, h, _g = _random_graph(rnd, "inconsistent")
        for width in (1, 2, 3, 50):
            for rank in ("h", "f"):
                r = A.beam_search(graph, s, t, width, rank, h=h)
                assert (r.path, r.cost) == _clean_beam(graph, s, t, width, h, rank)
    for _ in range(15):
        inst = S.grid_instance(rnd.randint(3, 8), rnd.choice([0, 15, 40]), rnd.randint(0, 10**6))
        h = A.heuristic(inst.graph.xy, inst.goal)
        for width in (1, 3, 8):
            for rank in ("h", "f"):
                r = A.beam_search(inst.graph, inst.start, inst.goal, width, rank)
                assert (r.path, r.cost) == _clean_beam(inst.graph, inst.start, inst.goal, width, h, rank)


def test_monobeam_on_random_cyclic_graphs_is_valid_monotone_and_prefix_consistent():
    rnd = random.Random(5)
    for _ in range(250):
        graph, s, t, h, g = _random_graph(rnd, "inconsistent")
        opt = nx.dijkstra_path_length(g, s, t) if nx.has_path(g, s, t) else INF
        costs = []
        for width in (1, 2, 3, 4, 5, 7, 2000):
            r = A.monobeam_search(graph, s, t, width, h=h)
            assert not r.capped
            costs.append(r.cost)
            if r.failed:
                assert r.path == [] and r.cost == INF
            else:
                assert r.path[0] == s and r.path[-1] == t
                assert sum(g[u][v]["weight"] for u, v in zip(r.path[:-1], r.path[1:])) == pytest.approx(r.cost, abs=1e-9)
                assert r.cost >= opt - 1e-9
        assert all(costs[j] <= costs[i] + 1e-9 for i in range(len(costs)) for j in range(i + 1, len(costs)))
        runs = {w: A.monobeam_search(graph, s, t, w, prune=False, h=h) for w in (1, 2, 3, 5)}
        for a, b in ((1, 2), (2, 3), (3, 5)):
            for lvl in range(min(runs[a].levels, runs[b].levels)):
                assert runs[a].per_level[lvl][:a] == runs[b].per_level[lvl][:a]


@pytest.mark.parametrize("mode", ["half", "exact"])
def test_unlimited_width_is_optimal_with_a_consistent_heuristic(mode):
    rnd = random.Random(8)
    for _ in range(250):
        graph, s, t, h, g = _random_graph(rnd, mode)
        r = A.monobeam_search(graph, s, t, 2000, h=h)
        if nx.has_path(g, s, t):
            assert r.cost == pytest.approx(nx.dijkstra_path_length(g, s, t), abs=1e-9) and len(set(r.path)) == len(r.path)
        else:
            assert r.failed


def test_unlimited_width_can_miss_the_optimum_with_pathmax_and_an_inconsistent_heuristic():
    """Von Hand: Start 0 (h 1). Kinder 2 (g 5, f 5), 3 (g 2, f 5), 1 (f 7). Platz 1 nimmt 2, Platz 2 nimmt 3. Zielkind von 2: Inkumbent
    8. Knoten 3 hat das Kind 2 mit g = 3 (g + h = 3 < 5), Pathmax hebt f auf 5 = f des Closed-Eintrags von 2: f >= f_d, also
    Duplikat - der Weg 0-3-2-4 (Kosten 6) geht verloren. Ohne Pathmax ist f = 3 < 5 und der Weg wird gefunden."""
    graph = G.from_edges(5, [(0, 0)] * 5, [(0, 1, 1.0), (0, 2, 5.0), (0, 3, 2.0), (2, 3, 1.0), (2, 4, 3.0)])
    h = np.array([1.0, 6.0, 0.0, 3.0, 0.0])
    assert A.uniform_cost_search(graph, 0, 4).cost == 6.0
    with_pm = A.monobeam_search(graph, 0, 4, 2000, h=h)
    without = A.monobeam_search(graph, 0, 4, 2000, h=h, pathmax=False)
    assert with_pm.cost == 8.0 and with_pm.pathmax_fired > 0
    assert without.cost == 6.0 and without.path == [0, 3, 2, 4]
