"""Presets: Vollständigkeit, gültige Werte, der Median der Monobeam-Lücke bleibt bei den Raster-Presets in der gemessenen
Spannweite über die 5 festen Sweep-Instanzen (vollständig deterministisch), und jedes Preset zeigt, was sein Name und sein
Hilfetext sagen."""

import pytest

import mono_constants as C
import mono_evaluation as ev
import mono_presets as P


def _settings(p, seed=None):
    return ev.Settings(network=p["network"], side=p["side"], obstacle_pct=p["obstacle_pct"], seed=p["seed"] if seed is None else seed,
                       width=p["width"], dedup=p["dedup"], continue_after_goal=p["stop"] == "continue")


def _analyse(name):
    return ev.analyse(_settings(C.PRESETS[name]))


def test_every_preset_has_help_and_the_grid_presets_a_band():
    assert set(C.PRESETS) == set(C.PRESET_HELP)
    assert len(C.PRESETS) == 7
    for name, p in C.PRESETS.items():
        assert set(p) == set(P.PRESET_KEYS) and C.PRESET_HELP[name]
    assert set(C.PRESET_EXPECTED_BANDS) == {n for n, p in C.PRESETS.items() if p["network"] == "grid"}


def test_preset_values_are_valid():
    for p in C.PRESETS.values():
        assert p["network"] in C.NETWORKS and p["width"] in C.WIDTHS and p["dedup"] in C.DEDUPS and p["stop"] in C.STOPS
        assert C.SIDE_MIN <= p["side"] <= C.SIDE_MAX and C.OBSTACLE_MIN <= p["obstacle_pct"] <= C.OBSTACLE_MAX


def test_default_preset_equals_the_default_settings():
    assert _settings(C.PRESETS["Standardfall (Voreinstellung)"]) == ev.Settings()


@pytest.mark.parametrize("name", list(C.PRESET_EXPECTED_BANDS))
def test_grid_preset_median_gap_stays_in_its_measured_band(name):
    lo, hi = C.PRESET_EXPECTED_BANDS[name]
    row = ev.run_config(_settings(C.PRESETS[name]))
    assert lo <= row["mono_gap"] <= hi, row["mono_gap"]


def test_standard_preset_instance_is_optimal_for_both():
    a = _analyse("Standardfall (Voreinstellung)")
    assert a.beam_optimal and a.mono_optimal and a.beam.cost == pytest.approx(175.9, abs=0.05)


def test_cuckoo_preset_beam_is_worse_at_width_two_than_at_width_one_and_monobeam_is_not():
    a = _analyse("Kuckuck-Falle (Breite 2)")
    assert (a.beam.cost, a.mono.cost, a.ucs.cost) == (8.0, 7.0, 7.0)
    one = ev.analyse(ev.Settings(network="cuckoo", width=1))
    assert one.beam.cost == 7.0 and a.beam.cost > one.beam.cost


def test_stop_preset_with_the_rule_off_finds_nine_and_the_paper_rule_six():
    p = C.PRESETS["Stopp-Falle (Regel aus)"]
    assert p["stop"] == "level" and _analyse("Stopp-Falle (Regel aus)").mono.cost == 9.0
    assert ev.analyse(ev.Settings(network="stop", width=2)).mono.cost == 6.0
    assert ev.analyse(ev.Settings(network="stop", width=1, continue_after_goal=False)).mono.cost == 6.0


def test_beam_gets_worse_preset_numbers_from_the_help_text():
    a = _analyse("Beam wird schlechter")
    one = ev.analyse(ev.Settings(seed=200007, width=1))
    assert one.beam.cost == pytest.approx(194.5, abs=0.05) and a.beam.cost == pytest.approx(198.0, abs=0.05)
    assert a.mono.cost == pytest.approx(194.5, abs=0.05) and a.beam.cost > one.beam.cost


def test_naive_duplicates_preset_fails_while_the_paper_rule_finds_a_path():
    a = _analyse("Naive Duplikate (Breite 2)")
    assert a.mono.failed and ev.analyse(ev.Settings(seed=200019, width=1, dedup="full")).mono.cost < float("inf")
    slot = ev.analyse(ev.Settings(seed=200019, width=2))
    assert slot.mono.cost == pytest.approx(204.8, abs=0.05)


def test_price_preset_beam_optimal_at_width_four_monobeam_fails_until_width_eleven():
    a = _analyse("Preis der Monotonie (Breite 4)")
    assert a.beam.cost == pytest.approx(190.3, abs=0.05) and a.mono.failed
    costs = ev.costs_by_width(ev.Settings(seed=200042), "mono", widths=range(1, 15))
    assert all(c == float("inf") for c in costs[:11]) and costs[11] == pytest.approx(202.2, abs=0.05) and costs[12] == pytest.approx(190.3, abs=0.05)


def test_detour_preset_beam_takes_the_direct_edge_and_monobeam_the_detour():
    a = _analyse("Umweg-Falle (Breite 2)")
    assert (a.beam.cost, a.mono.cost, a.ucs.cost) == (10.0, 3.0, 3.0)


def test_bounds_and_permalink_constants():
    assert P.bounds("side_slider") == (C.SIDE_MIN, C.SIDE_MAX) and P.bounds("seed_input") == (0, C.SEED_MAX)
    assert len({spec.url_param for spec in P.SETTING_SPECS.values()}) == len(P.SETTING_SPECS)
    assert C.DEFAULT_WIDTH in C.WIDTHS


def test_network_width_dedup_and_stop_permalink_casters():
    assert P._network_from_str("cuckoo") == "cuckoo"
    with pytest.raises(ValueError):
        P._network_from_str("trap")
    assert P.SETTING_SPECS["width_select"].caster("8") == 8
    with pytest.raises(ValueError):
        P.SETTING_SPECS["width_select"].caster("7")
    assert P.SETTING_SPECS["dedup_select"].caster("full") == "full" and P.SETTING_SPECS["stop_select"].caster("level") == "level"
    with pytest.raises(ValueError):
        P.SETTING_SPECS["dedup_select"].caster("none")
    with pytest.raises(ValueError):
        P.SETTING_SPECS["stop_select"].caster("x")
