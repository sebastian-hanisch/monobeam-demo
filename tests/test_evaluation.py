import math
from dataclasses import replace

import mono_constants as C
import mono_evaluation as EV


def test_analyse_grid_and_hand_built_networks_run_and_agree_with_the_optimum():
    for network in ("grid", "cuckoo", "stop", "detour"):
        a = EV.analyse(EV.Settings(network=network, side=8, obstacle_pct=20, seed=1, width=24))
        assert not a.mono.failed and not a.beam.failed
        assert a.mono.cost >= a.ucs.cost - 1e-9 and a.beam.cost >= a.ucs.cost - 1e-9
    assert EV.analyse(EV.Settings(network="cuckoo")).astar is None and EV.analyse(EV.Settings(network="grid")).astar is not None


def test_a_failed_run_is_flagged_and_has_no_gap_or_ratio():
    a = EV.analyse(EV.Settings(seed=200042, width=4))
    assert a.mono.failed and not a.beam.failed
    assert math.isnan(a.mono_gap) and math.isnan(a.mono_expansion_ratio) and math.isnan(a.mono_beam_expansion_ratio)
    assert not a.mono_optimal and a.beam_optimal and a.verdict is None


def test_verdict_classifies_better_same_worse():
    a = EV.analyse(EV.Settings(network="cuckoo", width=2))
    assert a.verdict == "besser"                                    # Beam 8, Monobeam 7
    assert EV.analyse(EV.Settings(network="cuckoo", width=1)).verdict == "gleich"
    assert EV.analyse(EV.Settings(seed=200007, width=2)).verdict == "besser"


def test_run_config_reports_failure_and_optimal_shares_over_all_runs_and_medians_with_ranges():
    out = EV.run_config(EV.Settings(), width=2)
    assert out["n_runs"] == 5 and out["mono_failed_share"] == 20.0 and out["beam_failed_share"] == 0.0
    assert out["mono_gap_lo"] <= out["mono_gap"] <= out["mono_gap_hi"]
    assert out["n_both_solved"] == 4 and out["mono_besser"] + out["mono_gleich"] + out["mono_schlechter"] == 4
    wide = EV.run_config(EV.Settings(), width=24)
    assert wide["mono_failed_share"] == 0.0 and wide["mono_optimal_share"] == 100.0 and wide["beam_optimal_share"] == 100.0


def test_sweep_returns_one_row_per_value():
    assert [r["value"] for r in EV.sweep("width", EV.Settings(side=8))] == list(C.WIDTHS)
    assert [r["value"] for r in EV.sweep("obstacle_pct", EV.Settings(side=8))] == list(C.OBSTACLE_SWEEP)
    assert [r["value"] for r in EV.sweep("side", EV.Settings(), values=(6, 8))] == [6, 8]


def test_analyse_is_deterministic():
    a1 = EV.analyse(EV.Settings(side=9, obstacle_pct=25, seed=7))
    a2 = EV.analyse(EV.Settings(side=9, obstacle_pct=25, seed=7))
    assert a1.mono.path == a2.mono.path and a1.mono.expansions == a2.mono.expansions and a1.beam.path == a2.beam.path


def test_ablation_switches_reach_the_monobeam_run():
    base = EV.Settings(seed=200019, width=2)
    assert not EV.analyse(base).mono.failed
    assert EV.analyse(replace(base, dedup="full")).mono.failed
    stop = EV.Settings(network="stop", width=2)
    assert EV.analyse(stop).mono.cost == 6.0 and EV.analyse(replace(stop, continue_after_goal=False)).mono.cost == 9.0


def test_is_non_monotone_classifies_the_three_cases():
    inf = float("inf")
    assert EV.is_non_monotone([5.0, 4.0, 3.0, 3.0]) == (False, False, False)
    assert EV.is_non_monotone([inf, 5.0, inf, 4.0]) == (True, True, False)
    assert EV.is_non_monotone([5.0, 4.0, 4.5, 4.0]) == (True, False, True)
    assert EV.is_non_monotone([inf, inf, 4.0]) == (False, False, False)


def test_cost_curves_match_costs_by_width_and_honor_the_ablation_switches():
    s = EV.Settings(seed=200019)
    beam, mono = EV.cost_curves(s, widths=(1, 2, 3))
    assert beam == EV.costs_by_width(s, "beam", widths=(1, 2, 3)) and mono == EV.costs_by_width(s, "mono", widths=(1, 2, 3))
    _, full = EV.cost_curves(replace(s, dedup="full"), widths=(1, 2, 3))
    assert full == EV.costs_by_width(s, "mono_full", widths=(1, 2, 3)) and full[1] == float("inf")


def test_monotonicity_result_structure_and_consistency():
    s = EV.Settings(side=8, obstacle_pct=15)
    m = EV.monotonicity(s, seeds=(1, 2, 3, 4), widths=(1, 2, 3, 4))
    assert set(m) == set(EV.VARIANTS)
    for variant, res in m.items():
        assert res["n"] == 4 and 0.0 <= res["non_monotone_share"] <= 100.0
        assert res["wider_fails_share"] <= res["non_monotone_share"] and res["wider_costlier_share"] <= res["non_monotone_share"]
    assert m["mono"]["non_monotone_share"] == 0.0
