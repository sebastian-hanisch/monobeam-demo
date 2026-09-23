"""Die Instanz dieser Demo: ein gestörtes Raster (Lagerhaus-/Straßennetz) mit einem Hindernis-Anteil, Start unten
links, Ziel oben rechts - Vierer-Nachbarschaft (hoch/runter/links/rechts), Kantengewicht = tatsächlicher
euklidischer Abstand der (leicht verschobenen) Zellmittelpunkte. Start und Ziel bleiben IMMER verbunden (wie
`dijkstra-demo`s Labyrinth: bei Bedarf werden einzelne Wände geöffnet, bis eine Verbindung existiert) - ohne diese
Garantie wäre "kein Pfad" der Normalfall bei hoher Hindernisdichte, nicht die Ausnahme, die dieses Stück zeigen
will.

Kantengewicht = echter euklidischer Abstand ⇒ die geradlinige Heuristik ist AUTOMATISCH zulässig (die
Dreiecksungleichung gilt für jeden Pfad zwischen zwei Punkten in der Ebene) - unabhängig von Hindernissen oder
Rasterform. Das Stück muss die Heuristik deshalb nicht künstlich verzerren, um Greedy Best-First Search zum
Scheitern zu bringen: die Hindernisse allein reichen (siehe `mono_algorithm.py`, Verifikation)."""

from dataclasses import dataclass

import numpy as np

import mono_constants as C
from mono_graph import Graph, adjacency

NEIGHBOR_OFFSETS = ((1, 0), (-1, 0), (0, 1), (0, -1))


@dataclass(frozen=True)
class Instance:
    graph: Graph
    start: int
    goal: int
    side: int
    obstacle_pct: int
    seed: int
    blocked_xy: np.ndarray      # (k, 2) Koordinaten der gesperrten Zellen, nur für die Darstellung
    h: object = None            # expliziter Heuristik-Vektor (handgebaute Instanzen); None = euklidischer Abstand zum Ziel
    labels: object = None       # Knotennamen (handgebaute Instanzen), None beim Raster


def _components(open_, side):
    label = -np.ones((side, side), dtype=int)
    count = 0
    for i in range(side):
        for j in range(side):
            if open_[i, j] and label[i, j] < 0:
                label[i, j] = count
                stack = [(i, j)]
                while stack:
                    a, b = stack.pop()
                    for da, db in NEIGHBOR_OFFSETS:
                        a2, b2 = a + da, b + db
                        if 0 <= a2 < side and 0 <= b2 < side and open_[a2, b2] and label[a2, b2] < 0:
                            label[a2, b2] = count
                            stack.append((a2, b2))
                count += 1
    return label


def _ensure_start_goal_connected(open_, side, rng):
    """Öffnet bei Bedarf einzelne gesperrte Zellen (bevorzugt solche, die zwei verschiedene Gebiete berühren),
    bis Start (0,0) und Ziel (side-1,side-1) im selben Gebiet liegen - wie `dijkstra-demo`s Labyrinth-Generator."""
    while True:
        label = _components(open_, side)
        if label[0, 0] == label[side - 1, side - 1]:
            return
        candidates, near_start = [], []
        for i in range(side):
            for j in range(side):
                if open_[i, j]:
                    continue
                labs = {label[a, b] for da, db in NEIGHBOR_OFFSETS
                        if 0 <= (a := i + da) < side and 0 <= (b := j + db) < side and label[a, b] >= 0}
                if len(labs) >= 2:
                    candidates.append((i, j))
                if label[0, 0] in labs:
                    near_start.append((i, j))
        pool = candidates or near_start
        i, j = pool[int(rng.integers(len(pool)))]
        open_[i, j] = True


def build_grid(side, obstacle_pct, seed):
    rng = np.random.default_rng([int(seed), 707])
    spacing = C.AREA / max(1, side - 1)
    open_ = rng.random((side, side)) >= obstacle_pct / 100.0
    open_[0, 0] = open_[side - 1, side - 1] = True
    _ensure_start_goal_connected(open_, side, rng)

    node = -np.ones((side, side), dtype=int)
    cells = np.argwhere(open_)
    node[open_] = np.arange(len(cells))
    ii, jj = cells[:, 0].astype(float), cells[:, 1].astype(float)
    xy = np.stack([jj, ii], axis=1) * spacing + rng.uniform(-C.JITTER, C.JITTER, (len(cells), 2)) * spacing

    edges = []
    for idx, (i, j) in enumerate(cells):
        for da, db in ((1, 0), (0, 1)):                          # jede Kante nur einmal aufnehmen
            i2, j2 = i + da, j + db
            if i2 < side and j2 < side and open_[i2, j2]:
                v = node[i2, j2]
                w = float(np.hypot(*(xy[idx] - xy[v])))
                edges.append((idx, v, w))

    graph = Graph(xy, *adjacency(len(cells), edges))
    start, goal = int(node[0, 0]), int(node[side - 1, side - 1])
    blocked_ij = np.argwhere(~open_)
    blocked_xy = (np.stack([blocked_ij[:, 1], blocked_ij[:, 0]], axis=1).astype(float) * spacing) if len(blocked_ij) else np.zeros((0, 2))
    return graph, start, goal, blocked_xy


def grid_instance(side=C.DEFAULT_SIDE, obstacle_pct=C.DEFAULT_OBSTACLE, seed=C.DEFAULT_SEED):
    graph, start, goal, blocked_xy = build_grid(int(side), int(obstacle_pct), int(seed))
    return Instance(graph, start, goal, int(side), int(obstacle_pct), int(seed), blocked_xy)


# --- Handgebaute Instanzen -------------------------------------------------------------------------------------------------------------------
#
# Drei kleine Graphen mit EXPLIZITER, zulässiger (aber nicht konsistenter) Heuristik `h`, jeweils so gebaut (per
# Skriptsuche über Gewichte und h, dann festgeschrieben und getestet), dass GENAU EIN Mechanismus sichtbar wird:
# - Kuckuck-Falle: Beam (f-Rang) findet mit Breite 1 den optimalen Pfad, mit Breite 2 einen schlechteren, weil Kinder
#   aus Platz 2 einen guten Kandidaten aus dem Strahl verdrängen ("Kuckucksknoten"); Monobeam bleibt bei 7.
# - Stopp-Falle: bricht die Suche nach der ersten Ebene mit Lösung ab (Beam, oder Monobeam mit dieser Stoppregel), findet
#   Breite 2 eine schlechtere Lösung als Breite 1 - Weitersuchen bis f >= Inkumbent behebt es.
# - Umweg-Falle: Direktkante 10 gegen Umweg 3: Beam liefert bei JEDER Breite den Pfad mit den wenigsten Kanten (10),
#   Monobeam ab Breite 1 den optimalen (3). Heuristik: euklidisch auf einer Geraden.

CUCKOO_EDGES = [(0, 1, 5.0), (0, 2, 2.0), (0, 3, 1.0), (1, 4, 4.0), (1, 6, 3.0), (2, 4, 2.0), (3, 5, 4.0), (3, 6, 3.0),
                (4, 7, 3.0), (5, 7, 4.0), (6, 7, 4.0)]
CUCKOO_H = [2.0, 6.0, 3.0, 6.0, 2.0, 0.0, 1.0, 0.0]
CUCKOO_XY = [(0, 5), (10, 9), (10, 5), (10, 1), (20, 8), (20, 1), (20, 4.5), (30, 5)]

STOP_EDGES = [(0, 1, 5.0), (0, 2, 1.0), (1, 3, 1.0), (1, 4, 1.0), (2, 4, 1.0), (2, 5, 3.0), (3, 6, 1.0), (4, 7, 5.0),
              (5, 6, 4.0), (6, 8, 1.0), (7, 8, 3.0)]
STOP_H = [1.0, 1.0, 3.0, 1.0, 3.0, 2.0, 0.0, 1.0, 0.0]
STOP_XY = [(0, 4), (10, 8), (10, 1), (20, 8), (20, 4.5), (20, 0), (30, 6), (30, 2), (40, 4)]

DETOUR_EDGES = [(0, 3, 10.0), (0, 1, 1.0), (1, 2, 1.0), (2, 3, 1.0)]
DETOUR_XY = [(0, 0), (1, 0), (2, 0), (3, 0)]


def _letters(n):
    names = ["S"] + [chr(ord("A") + i) for i in range(n - 2)] + ["Z"]
    return tuple(names)


def _hand_instance(n, xy, edges, h):
    xy = np.array(xy, dtype=float)
    graph = Graph(xy, *adjacency(n, edges))
    return Instance(graph, 0, n - 1, 0, 0, 0, np.zeros((0, 2)), None if h is None else np.array(h, dtype=float), _letters(n))


def cuckoo_instance():
    return _hand_instance(8, CUCKOO_XY, CUCKOO_EDGES, CUCKOO_H)


def stop_instance():
    return _hand_instance(9, STOP_XY, STOP_EDGES, STOP_H)


def detour_instance():
    return _hand_instance(4, DETOUR_XY, DETOUR_EDGES, None)


HAND_BUILT = {"cuckoo": cuckoo_instance, "stop": stop_instance, "detour": detour_instance}
