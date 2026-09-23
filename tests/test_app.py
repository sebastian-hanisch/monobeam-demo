"""AppTest-Rauchtests: Voreinstellung, jedes Preset, jeder Schritt und jede Ebene, alle vier Instanz-Typen, gescheiterte Läufe,
Randwerte, Würfel-Knopf, Permalink-Grenzen, Instanzwechsel, Ablations-Schalter, Sweeps und Experiment auf Abruf, Footer."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import mono_constants as C

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def _run(step=1, **state):
    at = AppTest.from_file(APP, default_timeout=180)
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    if step != 1:
        at.select_slider(key="mono_step").set_value(step).run()
    return at


def _ok(at):
    assert not at.exception, [e.value for e in at.exception]


def _metric(at, label):
    return next(m.value for m in at.metric if m.label == label)


def test_default_run_has_no_exception_and_shows_four_metrics():
    at = _run()
    _ok(at)
    assert {"Beam: Lücke", "Monobeam: Lücke", "Exp. Mono / Beam", "Vergleich"} <= {m.label for m in at.metric}
    assert _metric(at, "Beam: Lücke") == "0.00 %" and _metric(at, "Monobeam: Lücke") == "0.00 %"


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_button_runs(name):
    at = _run()
    next(b for b in at.button if b.key == f"preset_{name}").click().run()
    _ok(at)
    p = C.PRESETS[name]
    assert at.session_state["network_select"] == p["network"] and at.session_state["width_select"] == p["width"]
    assert at.session_state["dedup_select"] == p["dedup"] and at.session_state["stop_select"] == p["stop"]
    assert at.metric


@pytest.mark.parametrize("step", [1, 2, 3])
def test_every_step_runs_for_every_network(step):
    for network in C.NETWORKS:
        at = _run(network_select=network, step=step)
        _ok(at)
        assert at.get("plotly_chart") and at.session_state["mono_step"] == step


@pytest.mark.parametrize("step", [1, 2, 3])
def test_failed_monobeam_runs_render_in_every_step_and_are_flagged(step):
    at = _run(seed_input=200042, width_select=4, step=step)
    _ok(at)
    assert _metric(at, "Monobeam: Lücke") == "kein Pfad" and _metric(at, "Vergleich") == "-"
    if step == 3:
        assert any("gescheitert" in w.value for w in at.warning)


def test_level_slider_walks_through_all_levels_and_survives_an_instance_change():
    at = _run(step=2, width_select=3)
    _ok(at)
    slider = at.slider(key="mono_level")
    slider.set_value(slider.max).run()
    _ok(at)
    assert at.session_state["mono_level"] == slider.max
    at.session_state["network_select"] = "cuckoo"                # weniger Ebenen: gespeicherter Wert wird geklemmt
    at.run()
    _ok(at)
    assert at.session_state["mono_level"] <= 6


@pytest.mark.parametrize("kw", [
    dict(side_slider=C.SIDE_MIN), dict(side_slider=C.SIDE_MAX), dict(obstacle_slider=C.OBSTACLE_MIN), dict(obstacle_slider=C.OBSTACLE_MAX),
    dict(width_select=C.WIDTHS[0]), dict(width_select=C.WIDTHS[-1], side_slider=C.SIDE_MAX), dict(dedup_select="full"), dict(stop_select="level"),
])
def test_extreme_settings_run(kw):
    _ok(_run(**kw))
    _ok(_run(step=2, **kw))


def test_ablation_switches_change_the_result_on_the_matching_presets():
    naive = _run(seed_input=200019, width_select=2, dedup_select="full")
    _ok(naive)
    assert _metric(naive, "Monobeam: Lücke") == "kein Pfad"
    paper = _run(seed_input=200019, width_select=2)
    assert _metric(paper, "Monobeam: Lücke") != "kein Pfad"
    stop = _run(network_select="stop", width_select=2, stop_select="level")
    assert _metric(stop, "Monobeam: Lücke") == "50.00 %" and _metric(_run(network_select="stop", width_select=2), "Monobeam: Lücke") == "0.00 %"


def test_dice_button_changes_the_seed():
    at = _run()
    old = at.session_state["seed_input"]
    next(b for b in at.button if b.label == "🎲 Neue Instanz generieren").click().run()
    _ok(at)
    assert at.session_state["seed_input"] != old


def test_permalink_values_are_clamped_and_invalid_choices_fall_back_to_the_default():
    at = AppTest.from_file(APP, default_timeout=180)
    at.query_params["side"] = "9999"
    at.query_params["obstacle"] = "9999"
    at.query_params["width"] = "7"
    at.query_params["dedup"] = "zzz"
    at.query_params["stop"] = "zzz"
    at.query_params["network"] = "trap"
    at.run()
    _ok(at)
    assert at.session_state["side_slider"] == C.SIDE_MAX and at.session_state["obstacle_slider"] == C.OBSTACLE_MAX
    assert at.session_state["width_select"] == C.DEFAULT_WIDTH and at.session_state["dedup_select"] == "slot"
    assert at.session_state["stop_select"] == "continue" and at.session_state["network_select"] == "grid"


def test_sidebar_hides_grid_only_controls_for_the_hand_built_networks_but_keeps_width_and_switches():
    for network in ("cuckoo", "stop", "detour"):
        at = _run(network_select=network)
        _ok(at)
        assert not any(s.key == "side_slider" for s in at.slider)
        assert any(s.key == "width_select" for s in at.select_slider)
        assert any(r.key == "dedup_select" for r in at.radio) and any(r.key == "stop_select" for r in at.radio)


def test_changing_the_instance_while_on_step_two_does_not_crash():
    at = _run(step=2, side_slider=12)
    _ok(at)
    at.session_state["side_slider"] = C.SIDE_MIN
    at.run()
    _ok(at)
    at.session_state["network_select"] = "detour"
    at.run()
    _ok(at)


@pytest.mark.parametrize("param", ["width", "obstacle_pct", "side"])
@pytest.mark.parametrize("metric", ["gap", "expansion_ratio", "shares"])
def test_sweeps_run_on_demand_for_every_metric(param, metric):
    at = _run(side_slider=8, sweep_metric=metric)
    at.selectbox(key="sweep_select").set_value(param).run()
    next(b for b in at.button if b.key == "sweep_start").click().run()
    _ok(at)
    assert at.get("plotly_chart")


def test_monotonicity_experiment_runs_on_demand_and_shows_one_metric_per_variant():
    at = _run(side_slider=8)
    next(b for b in at.button if b.key == "mono_start").click().run()
    _ok(at)
    labels = {m.label for m in at.metric}
    assert {"Beam Search (f)", "Monobeam (Paper)", "Monobeam, naive Duplikate", "Monobeam, Stopp nach 1. Lösung"} <= labels


def test_footer_limits_and_literature_are_present():
    at = _run()
    assert any("Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net)" in c.value for c in at.caption)
    assert any("Wo die Annahmen enden" in s.value for s in at.subheader)
    assert any("Beam Stack Search" in m.value and "Kuckucksknoten" not in m.value and "Die Garantie ist umsonst" in m.value for m in at.markdown)
