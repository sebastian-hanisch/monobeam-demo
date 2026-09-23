"""Suchkerne - `_search`, `greedy_best_first`, `uniform_cost_search`, `a_star` und `beam_search` wortgleich aus
`beam-search-demo` (dort korrektheitsgeprüft; Vergleichsgrößen dieses Stücks; nur `beam_search` bekommt einen optionalen
expliziten Heuristik-Vektor `h`) und NEU `monobeam_search`.

Monobeam (Lemons, Linares López, Holte & Ruml, ICAPS 2022): der Strahl ist eine GEORDNETE Folge nummerierter Plätze, die
SEQUENZIELL aus einem gemeinsamen Kandidatenpool gefüllt werden. Platz c expandiert seinen Knoten, legt die Kinder in den
Pool und nimmt SOFORT den besten verbliebenen Pool-Knoten als Knoten der nächsten Ebene - bevor Platz c+1 expandiert.
Platz c sieht damit nur Kinder der Plätze 1..c; seine Wahl ist von der Breite unabhängig, ein schmalerer Strahl ist ein
Präfix eines breiteren (Lemma 1/2), und die Kosten steigen mit der Breite nie (Satz 1-3). Dazu gehören:
- Rangfolge f = g + h (Tie-Break kleines h), **Pathmax** (f entlang eines Pfades nicht fallend);
- **Weitersuchen** nach dem ersten Zielfund, bis kein Platz mehr f < Inkumbent hat (Beam stoppt nach der Ebene mit Lösung);
- **Plätze-bewusste Duplikaterkennung**: der Closed-Eintrag merkt sich den Platz, aus dem ein Zustand stammt; ein
  Duplikat zählt nur für Plätze >= diesem Platz (naive "Full-Beam"-Duplikate brechen die Monotonie, Paper-Abb. 3);
  Folge dieser Regel: ein Zustand kann in EINER Ebene auf zwei Plätzen stehen, wenn ein höherer Platz einen besseren Weg
  zu ihm findet (der schmalere Lauf sieht diesen Platz nie) - gewollt, nötig für das Präfix-Lemma und die Optimalität.
- **Inkumbent-Pruning** (Alg. 2): Strahlknoten mit f >= Inkumbent fallen weg (nur Effizienz, Lemma 4).
`dedup`, `continue_after_goal`, `prune` und `pathmax` sind Ablations-Schalter (Standard = Paper). Deterministisch."""

import heapq
from dataclasses import dataclass, field

import numpy as np


def heuristic(xy, goal):
    """Euklidischer Abstand jedes Knotens zum Ziel - vektorisiert. Bei echten Kantengewichten (siehe
    `beam_scenario.py`) automatisch zulässig (Dreiecksungleichung)."""
    return np.hypot(*(xy - xy[goal]).T)


@dataclass
class SearchResult:
    path: list                  # Knotenfolge Start..Ziel, oder [] falls kein Pfad existiert
    cost: float                 # Summe der Kantengewichte entlang des Pfades
    expansions: int             # Zahl der expandierten Knoten (Effizienz-Kennzahl dieses Stücks)
    order: list = field(default_factory=list)     # Reihenfolge der expandierten Knoten (für die Schritt-Visualisierung)
    stored: int = 0             # Speicher-Kennzahl: gespeicherte Knoten am Ende (A*/UCS/GBFS: entdeckte Knoten; IDA*: max. Pfadtiefe)


def _search(graph, start, goal, priority_fn, relax=True):
    """`priority_fn(node, g_cost) -> float` bestimmt die Warteschlangen-Priorität. `g_cost` ist der bislang
    aufgelaufene Pfadwert zu `node` (für Uniform-Cost-Search gebraucht, von Greedy Best-First ignoriert).

    `relax`: ob ein noch nicht expandierter, aber schon entdeckter Knoten einen GÜNSTIGEREN Elternknoten
    bekommt, sobald ein billigerer Weg zu ihm gefunden wird (klassische Dijkstra-Relaxation - für
    Uniform-Cost-Search nötig, damit es tatsächlich optimal bleibt). Bei `relax=False` behält ein Knoten für
    immer den ERSTEN gefundenen Elternknoten (echtes "kein Backtracking" - der Kern der GBFS-Schwäche: eine
    Relaxation hier würde den gemessenen Qualitätsverlust künstlich kleinrechnen, da GBFS dann doch beiläufig
    von g(n) profitieren würde, obwohl es g(n) laut Definition komplett ignoriert)."""
    counter = 0
    frontier = [(priority_fn(start, 0.0), counter, start, 0.0)]
    came_from = {start: None}
    g_cost = {start: 0.0}
    visited = set()
    order = []

    while frontier:
        _priority, _c, node, g = heapq.heappop(frontier)
        if node in visited:
            continue
        visited.add(node)
        order.append(node)
        if node == goal:
            path = []
            cur = node
            while cur is not None:
                path.append(cur)
                cur = came_from[cur]
            path.reverse()
            return SearchResult(path, g, len(order), order, len(g_cost))
        for v, w in zip(graph.neighbors[node], graph.weights[node]):
            if v in visited:
                continue
            g_v = g + w
            is_new = v not in g_cost
            if is_new or (relax and g_v < g_cost[v]):
                g_cost[v] = g_v
                came_from[v] = node
                counter += 1
                heapq.heappush(frontier, (priority_fn(v, g_v), counter, v, g_v))

    return SearchResult([], float("inf"), len(order), order, len(g_cost))


def greedy_best_first(graph, start, goal):
    h = heuristic(graph.xy, goal)
    return _search(graph, start, goal, lambda node, g: h[node], relax=False)


def uniform_cost_search(graph, start, goal):
    return _search(graph, start, goal, lambda node, g: g, relax=True)


def a_star(graph, start, goal):
    h = heuristic(graph.xy, goal)
    return _search(graph, start, goal, lambda node, g: g + h[node], relax=True)


@dataclass
class BeamResult(SearchResult):
    failed: bool = False
    layers: int = 0
    per_layer: list = field(default_factory=list)    # [(Strahl, verworfene Kandidaten), ...] je Schicht
    peak_width: int = 0                              # größte Kandidatenzahl einer Schicht vor dem Beschneiden


def beam_search(graph, start, goal, width, rank="h", h=None):
    if width < 1:
        raise ValueError("width muss mindestens 1 sein")
    if rank not in ("h", "f"):
        raise ValueError("rank muss 'h' oder 'f' sein")
    if h is None:
        h = heuristic(graph.xy, goal)
    neighbors, weights = graph.neighbors, graph.weights
    beam = [start]
    g = {start: 0.0}
    parent = {start: None}
    expanded = set()
    discovered = {start}
    order = []
    per_layer = []
    peak = 1

    def build_path(node):
        path = []
        while node is not None:
            path.append(node)
            node = parent[node]
        path.reverse()
        return path

    if start == goal:
        return BeamResult([start], 0.0, 0, [], 1, False, 0, [], 1)

    while True:
        cand_g, cand_parent = {}, {}
        current = list(beam)
        for node in beam:
            expanded.add(node)
            order.append(node)
        for node in beam:
            for v, w in zip(neighbors[node], weights[node]):
                if v in expanded:
                    continue
                g_v = g[node] + w
                if v not in cand_g or g_v < cand_g[v]:
                    cand_g[v] = g_v
                    cand_parent[v] = node
        discovered.update(cand_g)
        peak = max(peak, len(cand_g))
        if goal in cand_g:
            parent[goal] = cand_parent[goal]
            per_layer.append((current, []))
            return BeamResult(build_path(goal), cand_g[goal], len(order), order, len(discovered), False, len(per_layer), per_layer, peak)
        if not cand_g:
            per_layer.append((current, []))
            return BeamResult([], float("inf"), len(order), order, len(discovered), True, len(per_layer), per_layer, peak)
        if rank == "h":
            ranked = sorted(cand_g, key=lambda v: (h[v], v))
        else:
            ranked = sorted(cand_g, key=lambda v: (cand_g[v] + h[v], v))
        beam, dropped = ranked[:width], ranked[width:]
        per_layer.append((current, dropped))
        for v in beam:
            g[v] = cand_g[v]
            parent[v] = cand_parent[v]


@dataclass
class MonobeamResult(SearchResult):
    failed: bool = False
    levels: int = 0
    per_level: list = field(default_factory=list)    # je Ebene: Zustand je Platz (None = leer), wie expandiert
    pathmax_fired: int = 0                           # wie oft Pathmax f eines Kindes anheben musste
    capped: bool = False                             # Sicherheits-Obergrenze erreicht (Endlichkeit, siehe unten)


def monobeam_search(graph, start, goal, width, dedup="slot", continue_after_goal=True, prune=True, pathmax=True, h=None, max_expansions=500_000):
    if width < 1:
        raise ValueError("width muss mindestens 1 sein")
    if dedup not in ("slot", "full"):
        raise ValueError("dedup muss 'slot' oder 'full' sein")
    if h is None:
        h = heuristic(graph.xy, goal)
    neighbors, weights = graph.neighbors, graph.weights
    if start == goal:
        return MonobeamResult([start], 0.0, 0, [], 1, False, 0, [], 0)

    nodes = [(start, 0.0, float(h[start]), -1)]          # (Zustand, g, f, Elternindex)
    beam = [0] + [None] * (width - 1)
    closed = {start: (0, float(h[start]))}               # Zustand -> (Platz, f)
    discovered = {start}
    incumbent, incumbent_node = float("inf"), None
    order, per_level, fired, counter = [], [], 0, 0
    capped = False

    def accept(node_idx, slot):
        state, _g, f, _p = nodes[node_idx]
        entry = closed.get(state)
        if entry is None:
            closed[state] = (slot, f)
            return True
        d, fd = entry
        if dedup == "full":
            if f >= fd:
                return False
            closed[state] = (slot, f)
            return True
        if slot < d:
            closed[state] = (slot, f)                    # niedrigerer Platz überschreibt, auch mit schlechterem f
            return True
        if f >= fd:
            return False                                 # Duplikat (Platz >= d, nicht besser)
        if slot == d:
            closed[state] = (slot, f)
        return True                                      # besserer Weg aus höherem Platz: annehmen, Eintrag bleibt

    while any(i is not None and nodes[i][2] < incumbent for i in beam):
        per_level.append([nodes[i][0] if i is not None else None for i in beam])
        pool, next_beam = [], [None] * width
        for slot in range(width):
            idx = beam[slot]
            if idx is not None:
                state, g, f, _p = nodes[idx]
                order.append(state)
                if len(order) > max_expansions:
                    capped = True
                    break
                for v, w in zip(neighbors[state], weights[state]):
                    g_v = g + w
                    f_v = g_v + float(h[v])
                    if pathmax and f_v < f:
                        f_v = f                          # Pathmax
                        fired += 1
                    nodes.append((v, g_v, f_v, idx))
                    discovered.add(v)
                    child = len(nodes) - 1
                    if v == goal:
                        if f_v < incumbent:
                            incumbent, incumbent_node = f_v, child
                    else:
                        counter += 1
                        heapq.heappush(pool, (f_v, float(h[v]), counter, child))
            while pool:
                _f, _h, _c, cand = heapq.heappop(pool)
                if accept(cand, slot):
                    next_beam[slot] = cand
                    break
        if capped:
            break
        if prune:
            next_beam = [None if (i is not None and nodes[i][2] >= incumbent) else i for i in next_beam]
        beam = next_beam
        if not continue_after_goal and incumbent_node is not None:
            break

    if incumbent_node is None:
        return MonobeamResult([], float("inf"), len(order), order, len(discovered), True, len(per_level), per_level, fired, capped)
    path, cur = [], incumbent_node
    while cur != -1:
        path.append(nodes[cur][0])
        cur = nodes[cur][3]
    path.reverse()
    return MonobeamResult(path, nodes[incumbent_node][1], len(order), order, len(discovered), False, len(per_level), per_level, fired, capped)
