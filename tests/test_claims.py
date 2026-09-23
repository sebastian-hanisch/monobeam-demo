"""Jede Zahl in den Hilfetexten, Presets, Tabellen und Grenzen der App ist hier über die fünf festen Sweep-Instanzen belegt
(Nicht-Monotonie: über 50 feste Instanzen), mit denselben Auswertungsfunktionen wie die App selbst
(`ev.run_config`/`ev.sweep`/`ev.monotonicity`) - NIE über ein Ad-hoc-Skript. Positive UND negative Aussagen: die Monotonie-
Garantie hält (positiv) - aber bei gleicher Breite ist Monobeam nie besser als Beam, scheitert häufiger und braucht für
zuverlässige Optimalität ~3x A* statt ~1.2x (negativ, die zentralen ehrlichen Befunde). Werte sind MEDIANE über gelöste Läufe;
Scheiter-Quote und Optimal-Anteil beziehen sich auf ALLE Läufe."""

from dataclasses import replace
from functools import lru_cache

import pytest

import mono_constants as C
import mono_evaluation as ev


@lru_cache(maxsize=None)
def _cfg(items):
    return ev.run_config(ev.Settings(), **dict(items))


def cfg(**kw):
    return _cfg(tuple(sorted(kw.items())))


@lru_cache(maxsize=None)
def _mono(items):
    return ev.monotonicity(ev.Settings(), **dict(items))


def mono(**kw):
    return _mono(tuple(sorted(kw.items())))


def near(value, expected, tol):
    assert abs(value - expected) <= tol, f"{value:.3f} statt {expected}"


# --- Frage 1: die Monotonie-Garantie hält ---------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("side,obstacle,beam_total", [(12, 15, 8), (12, 0, 2), (12, 40, 10), (20, 15, 10)])
def test_beam_is_non_monotone_on_some_instances_and_monobeam_on_none(side, obstacle, beam_total):
    m = mono(side=side, obstacle_pct=obstacle)
    assert m["beam"]["n"] == 50
    near(m["beam"]["non_monotone_share"], beam_total, 4)
    assert m["beam"]["non_monotone_share"] > 0
    for key in ("non_monotone_share", "wider_fails_share", "wider_costlier_share"):
        assert m["mono"][key] == 0.0                                          # auch Scheitern nach Erfolg kommt nicht vor


@pytest.mark.parametrize("side,obstacle,total", [(12, 15, 6), (12, 0, 0), (12, 40, 6), (20, 15, 10)])
def test_naive_full_beam_duplicates_break_the_guarantee_as_wider_failures(side, obstacle, total):
    m = mono(side=side, obstacle_pct=obstacle)["mono_full"]
    near(m["non_monotone_share"], total, 4)
    if total:
        assert m["wider_fails_share"] >= m["non_monotone_share"] - 4 and m["wider_fails_share"] > 0


def test_naive_duplicates_cause_only_failures_on_size_twelve_and_a_few_costlier_cases_on_size_twenty():
    for obstacle in (0, 15, 40):
        assert mono(side=12, obstacle_pct=obstacle)["mono_full"]["wider_costlier_share"] == 0.0
    near(mono(side=20, obstacle_pct=15)["mono_full"]["wider_costlier_share"], 2, 4)


@pytest.mark.parametrize("side,obstacle", [(12, 15), (12, 0), (12, 40), (20, 15)])
def test_the_stop_rule_is_not_needed_for_monotonicity_on_the_grid(side, obstacle):
    assert mono(side=side, obstacle_pct=obstacle)["mono_level"]["non_monotone_share"] == 0.0


def test_example_seeds_for_naive_duplicates_include_the_preset_seed():
    assert 200019 in mono(side=12, obstacle_pct=15)["mono_full"]["example_seeds"]
    assert 200007 in mono(side=12, obstacle_pct=15)["beam"]["example_seeds"]


# --- Frage 2: was kostet die Garantie? -----------------------------------------------------------------------------------------------------


def test_default_numbers_at_width_four():
    row = cfg()
    assert row["beam_optimal_share"] == 60.0 and row["beam_failed_share"] == 0.0 and row["mono_failed_share"] == 20.0
    near(row["mono_gap"], 1.84, 0.3)
    near(row["mono_beam_expansion_ratio"], 1.03, 0.06)


def test_monobeam_is_never_better_than_beam_at_the_same_width_on_the_sweep_instances():
    for k in C.WIDTHS:
        assert cfg(width=k)["mono_besser"] == 0


def test_monobeam_is_worse_than_beam_at_most_widths_between_two_and_eight():
    for k in (2, 3, 4, 5, 6, 8):
        assert cfg(width=k)["mono_schlechter"] >= 3


def test_failure_share_beam_versus_monobeam_by_width():
    beam = [cfg(width=k)["beam_failed_share"] for k in C.WIDTHS]
    mono_ = [cfg(width=k)["mono_failed_share"] for k in C.WIDTHS]
    assert beam == [40.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    assert mono_ == [40.0, 20.0, 20.0, 20.0, 20.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    assert all(m >= b for m, b in zip(mono_, beam))


def test_gap_medians_beam_versus_monobeam():
    for k, gap in ((2, 4.5), (3, 0.35), (4, 0.0), (5, 0.0), (6, 0.0), (8, 0.0)):
        near(cfg(width=k)["beam_gap"], gap, 0.3)
    for k, gap in ((2, 5.2), (3, 3.2), (4, 1.84), (5, 0.6), (6, 0.44), (8, 0.35)):
        near(cfg(width=k)["mono_gap"], gap, 0.4)
    assert all(cfg(width=k)["mono_gap"] >= cfg(width=k)["beam_gap"] - 1e-9 for k in (2, 3, 4, 5, 6, 8))


def test_optimal_share_by_width_and_the_first_width_with_all_five_optimal():
    assert [cfg(width=k)["beam_optimal_share"] for k in C.WIDTHS] == [0.0, 0.0, 40.0, 60.0, 60.0, 60.0, 100.0, 100.0, 100.0, 100.0]
    assert [cfg(width=k)["mono_optimal_share"] for k in C.WIDTHS] == [0.0, 0.0, 0.0, 0.0, 0.0, 20.0, 40.0, 80.0, 80.0, 100.0]
    assert min(k for k in C.WIDTHS if cfg(width=k)["beam_optimal_share"] == 100.0) == 8
    assert min(k for k in C.WIDTHS if cfg(width=k)["mono_optimal_share"] == 100.0) == 24


def test_expansions_against_a_star_by_width():
    for k, ratio in zip(C.WIDTHS, (0.25, 0.44, 0.68, 0.87, 1.06, 1.22, 1.54, 2.13, 2.60, 2.96)):
        near(cfg(width=k)["mono_expansion_ratio"], ratio, 0.08)
    for k, ratio in zip(C.WIDTHS, (0.25, 0.47, 0.65, 0.84, 0.97, 1.08, 1.23, 1.25, 1.25, 1.25)):
        near(cfg(width=k)["beam_expansion_ratio"], ratio, 0.06)
    near(cfg(width=24)["mono_beam_expansion_ratio"], 2.13, 0.1)


def test_reliably_optimal_monobeam_costs_about_three_times_a_star_and_beam_about_one_point_two():
    near(cfg(width=24)["mono_expansion_ratio"], 2.96, 0.15)
    near(cfg(width=8)["beam_expansion_ratio"], 1.23, 0.06)


# --- Hindernisdichte und Rastergröße (Breite 4; Hilfetexte der Seitenleiste) ------------------------------------------------------------------


def test_obstacle_sweep_at_width_four():
    rows = ev.sweep("obstacle_pct", replace(ev.Settings(), width=4))
    assert [r["mono_failed_share"] for r in rows] == [0.0, 0.0, 0.0, 20.0, 20.0]
    assert [r["beam_failed_share"] for r in rows] == [0.0, 0.0, 20.0, 0.0, 0.0]


def test_size_sweep_at_width_four_monobeam_fails_on_the_larger_grids_beam_never():
    rows = ev.sweep("side", replace(ev.Settings(), width=4))
    assert [r["mono_failed_share"] for r in rows] == [0.0, 0.0, 0.0, 20.0, 40.0]
    assert all(r["beam_failed_share"] == 0.0 for r in rows)


# --- Extrembeispiel und Standardfall-Instanz -------------------------------------------------------------------------------------------------


def test_extreme_instance_beam_needs_width_four_monobeam_width_twelve_or_more():
    s = ev.Settings(seed=200042)
    beam = ev.costs_by_width(s, "beam", widths=range(1, 15))
    mono_ = ev.costs_by_width(s, "mono", widths=range(1, 15))
    inf = float("inf")
    assert beam[2] == inf and beam[3] < inf                                   # Beam: Breite 3 scheitert (Nicht-Monotonie), ab 4 optimal
    assert all(c == inf for c in mono_[:11]) and mono_[11] > mono_[12] and mono_[12] == pytest.approx(beam[3], abs=1e-6)
