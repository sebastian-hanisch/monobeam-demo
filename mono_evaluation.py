"""Auswertung: was garantiert Monobeam, und was kostet die Garantie? Vergleich von Monobeam mit dem normalen Beam Search
(f-Rang, Stopp nach der Schicht mit Lösung - das Beam des Papers), A* (Expansions-Referenz, nur auf dem Raster mit
euklidischer Heuristik) und Uniform-Cost-Search (Optimum) auf demselben Graphen.

Kennzahlen (über die 5 festen Sweep-Instanzen, Seeds 100000-100004, deterministisch; Median mit Minimum/Maximum):

- **Lücke** = 100 * (Kosten - Kosten UCS) / Kosten UCS - nur über GELÖSTE Läufe; daneben stets **Scheiter-Quote** und
  **Optimal-Anteil** (Anteil ALLER Läufe mit Lücke 0, gescheiterte zählen als nicht optimal).
- **Expansions-Verhältnis** gegen A* (nur gelöste Läufe) und **Monobeam / Beam** (beide gelöst).
- **Paarvergleich** je Instanz: Monobeam besser / gleich / schlechter als Beam bei gleicher Breite (beide gelöst).
- **Nicht-Monotonie** (`monotonicity`): Anteil der Instanzen, bei denen irgendein BREITERER Lauf schlechter ist als ein
  schmalerer (höhere Kosten, oder Scheitern trotz Erfolg) - über die Breiten 1..24, für Beam, Monobeam und die Ablationen
  (naive Duplikate, Stopp nach der ersten Lösungs-Schicht)."""

from dataclasses import dataclass, replace
from functools import lru_cache

import numpy as np

import mono_algorithm as A
import mono_constants as C
import mono_scenario as S

INF = float("inf")


@dataclass(frozen=True)
class Settings:
    network: str = "grid"           # "grid", "cuckoo", "stop" oder "detour"
    side: int = C.DEFAULT_SIDE
    obstacle_pct: int = C.DEFAULT_OBSTACLE
    seed: int = C.DEFAULT_SEED
    width: int = C.DEFAULT_WIDTH
    dedup: str = "slot"             # Monobeam: "slot" (Paper, Alg. 3) oder "full" (naive Full-Beam-Duplikate)
    continue_after_goal: bool = True    # Monobeam: True = Paper (bis kein Platz f < Inkumbent hat), False = Stopp nach der Schicht mit Lösung


@lru_cache(maxsize=512)
def _grid(side, obstacle_pct, seed):
    return S.grid_instance(side, obstacle_pct, seed)


def instance_of(settings):
    if settings.network == "grid":
        return _grid(settings.side, settings.obstacle_pct, settings.seed)
    return S.HAND_BUILT[settings.network]()


# Varianten für die Nicht-Monotonie-Messung: Name -> Aufruf (graph, start, goal, width, h)
VARIANTS = {
    "beam": lambda g, s, t, k, h: A.beam_search(g, s, t, k, "f", h=h),
    "mono": lambda g, s, t, k, h: A.monobeam_search(g, s, t, k, h=h),
    "mono_full": lambda g, s, t, k, h: A.monobeam_search(g, s, t, k, dedup="full", h=h),
    "mono_level": lambda g, s, t, k, h: A.monobeam_search(g, s, t, k, continue_after_goal=False, h=h),
}
VARIANT_LABELS = {
    "beam": "Beam Search (f)",
    "mono": "Monobeam (Paper)",
    "mono_full": "Monobeam, naive Duplikate",
    "mono_level": "Monobeam, Stopp nach 1. Lösung",
}


@dataclass
class Analysis:
    settings: Settings
    inst: object
    beam: A.BeamResult
    mono: A.MonobeamResult
    astar: object               # SearchResult oder None (handgebaute Instanzen mit nicht konsistenter Heuristik)
    ucs: A.SearchResult

    @staticmethod
    def _gap(result, ucs):
        return float("nan") if result.failed else 100.0 * (result.cost - ucs.cost) / ucs.cost

    @property
    def beam_gap(self):
        return self._gap(self.beam, self.ucs)

    @property
    def mono_gap(self):
        return self._gap(self.mono, self.ucs)

    @property
    def beam_optimal(self):
        return (not self.beam.failed) and self.beam.cost <= self.ucs.cost + 1e-9

    @property
    def mono_optimal(self):
        return (not self.mono.failed) and self.mono.cost <= self.ucs.cost + 1e-9

    @property
    def verdict(self):
        """Monobeam gegen Beam bei gleicher Breite: "besser" / "gleich" / "schlechter"; None, wenn einer scheiterte."""
        if self.beam.failed or self.mono.failed:
            return None
        if self.mono.cost < self.beam.cost - 1e-9:
            return "besser"
        if self.mono.cost > self.beam.cost + 1e-9:
            return "schlechter"
        return "gleich"

    @property
    def mono_expansion_ratio(self):
        """Expansionen Monobeam / A*; NaN ohne A* oder bei gescheitertem Lauf."""
        return float("nan") if (self.astar is None or self.mono.failed) else self.mono.expansions / self.astar.expansions

    @property
    def beam_expansion_ratio(self):
        return float("nan") if (self.astar is None or self.beam.failed) else self.beam.expansions / self.astar.expansions

    @property
    def mono_beam_expansion_ratio(self):
        return float("nan") if (self.beam.failed or self.mono.failed) else self.mono.expansions / self.beam.expansions


def analyse(settings):
    inst = instance_of(settings)
    g, s, t, h = inst.graph, inst.start, inst.goal, inst.h
    beam = A.beam_search(g, s, t, settings.width, "f", h=h)
    mono = A.monobeam_search(g, s, t, settings.width, dedup=settings.dedup, continue_after_goal=settings.continue_after_goal, h=h)
    astar = A.a_star(g, s, t) if h is None else None
    ucs = A.uniform_cost_search(g, s, t)
    return Analysis(settings, inst, beam, mono, astar, ucs)


# --- Sweeps --------------------------------------------------------------------------------------------------------------------------------------


def _median_range(values):
    values = [v for v in values if not np.isnan(v)]
    if not values:
        return float("nan"), float("nan"), float("nan")
    return float(np.median(values)), float(np.min(values)), float(np.max(values))


def run_config(base, seeds=C.SWEEP_SEEDS, **changes):
    s0 = replace(base, **changes)
    rows = [analyse(replace(s0, seed=seed)) for seed in seeds]
    n = len(rows)
    out = {"n_runs": n}
    for name, get_failed, get_optimal in (
        ("beam", lambda r: r.beam.failed, lambda r: r.beam_optimal),
        ("mono", lambda r: r.mono.failed, lambda r: r.mono_optimal),
    ):
        out[f"{name}_n_solved"] = sum(not get_failed(r) for r in rows)
        out[f"{name}_failed_share"] = 100.0 * sum(get_failed(r) for r in rows) / n
        out[f"{name}_optimal_share"] = 100.0 * sum(get_optimal(r) for r in rows) / n
    for key, values in (
        ("beam_gap", [r.beam_gap for r in rows]),
        ("mono_gap", [r.mono_gap for r in rows]),
        ("beam_expansion_ratio", [r.beam_expansion_ratio for r in rows]),
        ("mono_expansion_ratio", [r.mono_expansion_ratio for r in rows]),
        ("mono_beam_expansion_ratio", [r.mono_beam_expansion_ratio for r in rows]),
    ):
        out[key], out[f"{key}_lo"], out[f"{key}_hi"] = _median_range(values)
    verdicts = [r.verdict for r in rows if r.verdict is not None]
    out["n_both_solved"] = len(verdicts)
    for v in ("besser", "gleich", "schlechter"):
        out[f"mono_{v}"] = sum(x == v for x in verdicts)
    out["astar_expansions"] = float(np.median([r.astar.expansions for r in rows])) if rows[0].astar is not None else float("nan")
    return out


SWEEP_VALUES = {"width": C.WIDTHS, "obstacle_pct": C.OBSTACLE_SWEEP, "side": C.SCALING_SIDES}
SWEEP_LABELS = {"width": "Breite k", "obstacle_pct": "Hindernisdichte (%)", "side": "Rastergröße (Seitenlänge)"}


def sweep(param, base=Settings(), values=None):
    values = SWEEP_VALUES[param] if values is None else values
    return [{"value": v, **run_config(base, **{param: v})} for v in values]


# --- Nicht-Monotonie -----------------------------------------------------------------------------------------------------------------------------


def costs_by_width(settings, variant, widths=C.MONO_WIDTHS):
    """Kosten (inf = gescheitert) der Variante für jede Breite auf der Instanz von `settings` (Breite/Schalter dort ignoriert)."""
    inst = instance_of(settings)
    fn = VARIANTS[variant]
    return [fn(inst.graph, inst.start, inst.goal, k, inst.h).cost for k in widths]


def cost_curves(settings, widths=C.MONO_WIDTHS):
    """(Beam-Kosten, Monobeam-Kosten) für jede Breite auf der Instanz von `settings`; Monobeam mit den Ablations-Schaltern
    (Duplikate, Stoppregel) aus `settings` - Grundlage des Held-Diagramms. inf = gescheitert."""
    inst = instance_of(settings)
    g, s, t, h = inst.graph, inst.start, inst.goal, inst.h
    beam = [A.beam_search(g, s, t, k, "f", h=h).cost for k in widths]
    mono = [A.monobeam_search(g, s, t, k, dedup=settings.dedup, continue_after_goal=settings.continue_after_goal, h=h).cost for k in widths]
    return beam, mono


def is_non_monotone(costs):
    """(irgendwo schlechter, davon: breiter SCHEITERT trotz Erfolg eines schmaleren, davon: breiter hat höhere endliche Kosten)."""
    worse = fail = cost = False
    for i in range(len(costs)):
        for j in range(i + 1, len(costs)):
            if costs[j] > costs[i] + 1e-9:
                worse = True
                if costs[j] == INF:
                    fail = True
                else:
                    cost = True
    return worse, fail, cost


def monotonicity(base, seeds=C.MONO_SEEDS, widths=C.MONO_WIDTHS, variants=tuple(VARIANTS), **changes):
    """Je Variante: Anteil (in %) der Instanzen, bei denen ein breiterer Lauf schlechter ist, davon Scheitern / höhere Kosten,
    plus die Seeds der betroffenen Instanzen."""
    s0 = replace(base, **changes)
    out = {}
    for v in variants:
        rows = []
        for seed in seeds:
            costs = costs_by_width(replace(s0, seed=seed), v, widths)
            rows.append((seed, costs, *is_non_monotone(costs)))
        n = len(rows)
        out[v] = {
            "n": n,
            "non_monotone_share": 100.0 * sum(r[2] for r in rows) / n,
            "wider_fails_share": 100.0 * sum(r[3] for r in rows) / n,
            "wider_costlier_share": 100.0 * sum(r[4] for r in rows) / n,
            "example_seeds": [r[0] for r in rows if r[2]],
        }
    return out
