"""Monobeam - kann mehr Breite je schaden? Nicht mehr - aber zu welchem Preis? - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Fünftes Stück der Heuristische-Baumsuche-Linie der "Konzepte"-Reihe, Fortsetzung von Beam Search (beam-search-demo): dort
wurde gemessen, dass ein breiterer Strahl bei einem Teil der Instanzen SCHLECHTER ist. Monobeam (Lemons, Linares López,
Holte & Ruml, ICAPS 2022) füllt die Strahlplätze sequenziell aus einem gemeinsamen Kandidatenpool und garantiert damit
nicht steigende Kosten in der Breite. Was kostet die Garantie? Muss gemessen werden, nicht angenommen.

Lauffähig mit: streamlit run app.py
"""

from dataclasses import replace

import streamlit as st

import mono_constants as C
from mono_evaluation import SWEEP_LABELS, VARIANT_LABELS, Settings, analyse, cost_curves, monotonicity, sweep
from mono_presets import (
    apply_preset,
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    sync_query_params,
)
from mono_visualization import (
    build_cost_by_width,
    build_instance,
    build_level_maps,
    build_monotonicity_bars,
    build_paths,
    build_share_bars,
    build_sweep,
)

st.set_page_config(page_title="Monobeam – Sebastian Hanisch", layout="wide")


@st.cache_data(show_spinner=False)
def _analysis(settings):
    return analyse(settings)


@st.cache_data(show_spinner=False)
def _sweep(param, base):
    return sweep(param, base)


@st.cache_data(show_spinner=False)
def _curves(settings):
    return cost_curves(settings)


@st.cache_data(show_spinner=False)
def _monotonicity(base):
    return monotonicity(base)


def _fmt_cost(result):
    return "gescheitert" if result.failed else f"{result.cost:.2f}"


st.title("🪺 Monobeam – kann mehr Breite je schaden? Nicht mehr. Aber zu welchem Preis?")
st.markdown(
    """
**Fünftes Stück der Heuristische-Baumsuche-Linie** - die Fortsetzung von Beam Search. Dort wurde gemessen: ein breiterer
Strahl ist bei einem Teil der Instanzen **schlechter** als ein schmalerer (höhere Kosten, oder er scheitert sogar).
Die Ursache nennt das Paper **Kuckucksknoten**: Kinder aus späteren Strahlplätzen verdrängen Kandidaten, die ein
schmalerer Strahl gewählt hätte.

**Monobeam** (Lemons, Linares López, Holte & Ruml, ICAPS 2022) füllt die Plätze des Strahls **nacheinander** aus einem
**gemeinsamen Kandidatenpool**: Platz c sieht nur Kinder der Plätze 1..c. Ein schmalerer Strahl ist damit ein Präfix eines
breiteren, und die Kosten steigen mit der Breite **nie**. Hält die Garantie - und was kostet sie?
"""
)
st.caption(
    "Setzt auf [beam-search-demo](https://github.com/sebastian-hanisch/beam-search-demo) auf (derselbe Graph, dieselben "
    "Instanzen; Beam Search mit f-Rang als Vergleich). Noch nicht gebaute Geschwister: Diverse Beam Search, Monte Carlo "
    "Tree Search (MCTS), Beam Search + A\\* → Beam Stack Search."
)

with st.expander("So funktioniert Monobeam", expanded=True):
    st.markdown(
        """
1. **Ebenen und Plätze:** wie Beam Search Schicht für Schicht; der Strahl ist eine **geordnete Folge nummerierter Plätze**.
2. **Gemeinsamer Pool, sequenziell:** Platz 1 expandiert seinen Knoten, legt die Kinder in den Pool und nimmt **sofort** das
   beste Pool-Element (kleinstes f, Tie-Break kleines h) als Knoten der nächsten Ebene; erst dann ist Platz 2 dran usw.
   So hängt die Wahl von Platz c nicht von der Breite ab.
3. **Weitersuchen:** nach dem ersten Zielfund (Inkumbent) läuft die Suche, bis kein Platz mehr **f < Inkumbent** hat;
   Strahlknoten mit f ≥ Inkumbent fallen weg (Pruning). **Pathmax** hält f entlang eines Pfades nicht fallend.
4. **Duplikate plätze-bewusst:** der Closed-Eintrag merkt sich den Platz; ein Duplikat zählt nur für Plätze ≥ diesem Platz.
   Naive Full-Beam-Duplikate brechen die Garantie.
        """
    )

if C.PRESETS:
    st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
    preset_names = list(C.PRESETS.keys())
    for row in (preset_names[:4], preset_names[4:]):
        if not row:
            continue
        cols = st.columns(len(row))
        for col, name in zip(cols, row):
            with col:
                st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP.get(name, ""), key=f"preset_{name}")

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    network = st.radio("Instanz", options=list(C.NETWORKS), format_func=lambda n: C.NETWORK_LABELS[n], key="network_select",
                        help="Die drei handgebauten Graphen haben eine explizite Heuristik und zeigen je EINEN Mechanismus - Rastergröße/Hindernisdichte/Seed wirken dort nicht.")
    if network == "grid":
        side = st.slider("Rastergröße (Seitenlänge)", *bounds("side_slider"), key="side_slider",
                          help="Bei größeren Rastern braucht Monobeam noch mehr Breite: bei Breite 4 scheitert es bei Größe 22 in 2 von 5 Instanzen (Beam in keiner).")
        obstacle_pct = st.slider("Hindernisdichte [%]", *bounds("obstacle_slider"), key="obstacle_slider", step=C.OBSTACLE_STEP,
                                  help="Zeigt, wo ein schmaler Strahl das Ziel verliert - bei Monobeam früher als bei Beam.")
        seed = st.number_input("Zufalls-Seed der Instanz", *bounds("seed_input"), key="seed_input", step=1)
        st.button("🎲 Neue Instanz generieren", width="stretch", on_click=randomize_seed)
    else:
        side, obstacle_pct, seed = C.DEFAULT_SIDE, C.DEFAULT_OBSTACLE, C.DEFAULT_SEED
    width = st.select_slider("Breite k", options=list(C.WIDTHS), key="width_select",
                             help="Anzahl der Strahlplätze - für Beam UND Monobeam.")
    st.caption("Ablationen (nur Monobeam):")
    dedup = st.radio("Duplikate", options=list(C.DEDUPS), format_func=lambda d: C.DEDUP_LABELS[d], key="dedup_select",
                     help="Plätze-bewusst (Paper, Alg. 3) oder naiv (Full-Beam): naiv bricht die Monotonie - bei 6 % der Instanzen (Größe 12, 15 % Hindernisse) scheitert ein breiterer Lauf trotz Erfolg eines schmaleren.")
    stop = st.radio("Stoppregel", options=list(C.STOPS), format_func=lambda d: C.STOP_LABELS[d], key="stop_select",
                    help="Weitersuchen bis kein Platz mehr f < Inkumbent hat (Paper) oder Stopp nach der ersten Ebene mit Lösung. Auf dem Raster ändert das die Monotonie nicht (0 %), die handgebaute Stopp-Falle zeigt, dass die Regel dort nötig ist.")

sync_query_params({"network_select": network, "side_slider": int(side), "obstacle_slider": int(obstacle_pct), "seed_input": int(seed),
                   "width_select": int(width), "dedup_select": dedup, "stop_select": stop})

settings = Settings(network, int(side), int(obstacle_pct), int(seed), int(width), dedup, stop == "continue")
with st.spinner("Rechne..."):
    a = _analysis(settings)
beam, mono = a.beam, a.mono
hand = network != "grid"

# --- Monobeam in Aktion ------------------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Monobeam in Aktion")
STEP_LABELS = {1: "1 · Instanz", 2: "2 · Strahl je Ebene", 3: "3 · Ergebnis"}
step = st.select_slider("Schritt", options=list(STEP_LABELS), key="mono_step", format_func=lambda s: STEP_LABELS[s])

if step == 1:
    if hand:
        st.markdown(f"**{a.inst.graph.n} Knoten** (Start S, Ziel Z), Kantengewichte an den Kanten, Heuristik h(n) am Knoten" if a.inst.h is not None else f"**{a.inst.graph.n} Knoten** (Start S, Ziel Z), Kantengewichte an den Kanten, Heuristik = Luftlinie zum Ziel")
    else:
        st.markdown(f"**{a.inst.graph.n} Zellen** ({len(a.inst.blocked_xy)} Hindernisse), Start (grün) und Ziel (rot)")
    st.plotly_chart(build_instance(a.inst), width="stretch", key="s1_map")
elif step == 2:
    n_levels = max(len(beam.per_layer), len(mono.per_level))
    if n_levels > 1:
        if "mono_level" in st.session_state:
            st.session_state["mono_level"] = min(max(1, int(st.session_state["mono_level"])), n_levels)
        level = st.slider("Ebene", 1, n_levels, key="mono_level", help="Ebene = Kantenzahl vom Start. Links Beam, rechts Monobeam auf derselben Ebene.")
    else:
        level = 1
    b_nodes = beam.per_layer[level - 1][0] if level <= len(beam.per_layer) else []
    m_slots = mono.per_level[level - 1] if level <= len(mono.per_level) else []
    m_nodes = [n for n in m_slots if n is not None]
    only_b, only_m = len(set(b_nodes) - set(m_nodes)), len(set(m_nodes) - set(b_nodes))
    st.markdown(
        f"**Ebene {level} von {n_levels}:** Beam expandiert {len(b_nodes)} Knoten"
        + (" (Suche beendet)" if level > len(beam.per_layer) else "")
        + f", Monobeam belegt {len(m_nodes)} von {settings.width} Plätzen"
        + (" (Suche beendet)" if level > len(mono.per_level) else "")
        + f". **{only_b} nur bei Beam, {only_m} nur bei Monobeam** - an diesen Knoten trennen sich die Verfahren."
    )
    st.plotly_chart(build_level_maps(a.inst, beam.per_layer, mono.per_level, level - 1), width="stretch", key=f"s2_map_{level}")
    st.caption(
        f"Expansionen insgesamt: Beam {beam.expansions}, Monobeam {mono.expansions}"
        + (f", A\\* {a.astar.expansions}" if a.astar is not None else "")
        + ". Monobeam sucht nach dem ersten Zielfund weiter, bis kein Platz mehr f < Inkumbent hat."
    )
else:
    parts = [f"**Beam:** {_fmt_cost(beam)}", f"**Monobeam:** {_fmt_cost(mono)}", f"**Optimum:** {a.ucs.cost:.2f}"]
    if beam.failed or mono.failed:
        st.warning(" – ".join(parts) + " - ein gescheiterter Lauf behauptet keinen Pfad.")
    else:
        st.markdown(" – ".join(parts) + f" – Lücke Beam **{a.beam_gap:.2f} %**, Monobeam **{a.mono_gap:.2f} %**")
    st.plotly_chart(build_paths(a.inst, a.ucs.path, beam.path, mono.path), width="stretch", key="s3_map")

st.markdown("---")

# --- Held-Diagramm ------------------------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Kosten über die Breite")
st.caption(
    "Pfadkosten dieser Instanz für jede Breite von 1 bis 24 - das Analogon zu Abb. 1 des Papers. Beam zickzackt (wo die Kurve steigt "
    "oder ein x auftaucht, ist ein breiterer Strahl schlechter), Monobeam fällt nie. Die Ablations-Schalter in der Seitenleiste "
    "wirken auf die Monobeam-Kurve."
)
beam_costs, mono_costs = _curves(settings)
st.plotly_chart(build_cost_by_width(list(C.MONO_WIDTHS), beam_costs, mono_costs, a.ucs.cost, mono_name="Monobeam" if (dedup == "slot" and stop == "continue") else "Monobeam (Ablation)"),
                width="stretch", key="curves")

st.markdown("---")

# --- Ergebnis ----------------------------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Beam gegen Monobeam bei Breite " + str(settings.width))
st.caption(
    "**Lücke:** Kosten gegenüber dem Optimum (Uniform-Cost). **Exp. Mono / Beam:** Expansionen Monobeam / Beam, über 1 heißt, Monobeam expandiert mehr (nur wenn beide einen Pfad fanden). "
    "**Vergleich:** Monobeam gegen Beam bei gleicher Breite (nur wenn beide einen Pfad fanden)."
)
m1, m2, m3, m4 = st.columns(4)
m1.metric("Beam: Lücke", "kein Pfad" if beam.failed else f"{a.beam_gap:.2f} %", delta=f"{beam.expansions} Expansionen", delta_color="off")
m2.metric("Monobeam: Lücke", "kein Pfad" if mono.failed else f"{a.mono_gap:.2f} %", delta=f"{mono.expansions} Expansionen", delta_color="off")
m3.metric("Exp. Mono / Beam", "-" if (beam.failed or mono.failed) else f"{a.mono_beam_expansion_ratio:.2f}x",
          delta="beide nötig" if (beam.failed or mono.failed) else f"{mono.expansions} gegen {beam.expansions}", delta_color="off")
m4.metric("Vergleich", "-" if a.verdict is None else a.verdict, delta="Mono gegen Beam" if a.verdict is not None else "ohne Pfad", delta_color="off")

st.markdown("---")

# --- Sweeps ------------------------------------------------------------------------------------------------------------------------------------

if network == "grid":
    st.subheader("📐 Wie hängt der Preis von Breite, Hindernissen und Größe ab?")
    sweep_param = st.selectbox("Welcher Regler soll durchgefahren werden?", list(SWEEP_LABELS), format_func=lambda k: SWEEP_LABELS[k], key="sweep_select")
    metric = st.radio("Kennzahl", options=["gap", "expansion_ratio", "shares"],
                       format_func=lambda k: {"gap": "Lücke (%)", "expansion_ratio": "Expansionen / A*", "shares": "Optimal / gescheitert (%)"}[k],
                       key="sweep_metric", horizontal=True)
    base_sweep = replace(settings, seed=0)
    if st.button("Sweep über 5 feste Instanzen berechnen (kann einige Sekunden dauern)", key="sweep_start"):
        st.session_state["sweep_done"] = st.session_state.get("sweep_done", set()) | {(sweep_param, base_sweep)}
    if (sweep_param, base_sweep) in st.session_state.get("sweep_done", set()):
        with st.spinner("Rechne den Sweep über 5 feste Instanzen..."):
            rows_sweep = _sweep(sweep_param, base_sweep)
        if metric == "shares":
            st.plotly_chart(build_share_bars(rows_sweep, SWEEP_LABELS[sweep_param]), width="stretch", key="sweep_shares")
        elif metric == "gap":
            st.plotly_chart(build_sweep(rows_sweep, SWEEP_LABELS[sweep_param], "beam_gap", "mono_gap", "Lücke zum Optimum (%)"), width="stretch", key="sweep_gap")
        else:
            st.plotly_chart(build_sweep(rows_sweep, SWEEP_LABELS[sweep_param], "beam_expansion_ratio", "mono_expansion_ratio", "Expansionen / A*",
                                        ref_line=1.0, ref_label="so viel wie A*"), width="stretch", key="sweep_exp")
        st.caption(
            "Median über 5 feste Instanzen (Seeds 100000–100004), Band = Minimum bis Maximum. Lücke und Verhältnisse nur über gelöste "
            "Läufe - der Balken-Modus zeigt daneben, wie oft ein Verfahren optimal war und wie oft es scheiterte. Beam: f-Rang; "
            "Monobeam mit den Ablations-Einstellungen der Seitenleiste."
        )

    st.markdown("---")

    st.subheader("🔬 Wie oft ist ein breiterer Lauf schlechter - und welcher Baustein verhindert es?")
    st.caption(
        "Über 50 feste Instanzen (Seeds 200000–200049) und alle Breiten 1–24: Anteil der Instanzen, bei denen irgendein breiterer Lauf "
        "schlechter ist als ein schmalerer. Beam, Monobeam (Paper) und die beiden Ablationen (naive Duplikate, Stopp nach der ersten "
        "Lösungs-Schicht)."
    )
    key_mono = replace(settings, seed=0, width=C.DEFAULT_WIDTH, dedup="slot", continue_after_goal=True)
    if st.button("Nicht-Monotonie über 50 feste Instanzen messen", key="mono_start"):
        st.session_state["mono_done"] = st.session_state.get("mono_done", set()) | {key_mono}
    if key_mono in st.session_state.get("mono_done", set()):
        with st.spinner("Rechne 50 Instanzen x 24 Breiten x 4 Varianten..."):
            mono_res = _monotonicity(key_mono)
        st.plotly_chart(build_monotonicity_bars(mono_res, VARIANT_LABELS), width="stretch", key="mono_bars")
        cols = st.columns(len(mono_res))
        for col, (variant, res) in zip(cols, mono_res.items()):
            col.metric(VARIANT_LABELS[variant], f"{res['non_monotone_share']:.0f} %", delta=f"von {res['n']}", delta_color="off")
        seeds = mono_res["mono_full"]["example_seeds"][:6]
        if seeds:
            st.caption("Beispiel-Seeds für naive Duplikate (in die Seitenleiste eintragen, Duplikate auf naiv): " + ", ".join(str(s) for s in seeds))
        st.caption(f"Instanzen: Rastergröße {settings.side}, Hindernisdichte {settings.obstacle_pct} %.")

    st.markdown("---")

# --- Grenzen -----------------------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist | Wer setzt an |
|---|---|---|
| **Mehr Breite kann schaden** (Beam) | Bei Beam ja: bei 8 % (Größe 12, 15 % Hindernisse), 2 % (0 %), 10 % (40 %) und 10 % (Größe 20) der Instanzen ist irgendein breiterer Strahl schlechter. Bei Monobeam bei **0 %** in allen vier Einstellungen - die Garantie hält. | **Monobeam** (diese Demo) |
| **Die Garantie ist umsonst** | Nein. Bei gleicher Breite war Monobeam auf den 5 festen Instanzen nie besser als Beam; es scheitert bei Breite 2-5 in 1 von 5 Läufen (Beam ab Breite 2 nie), und alle 5 Instanzen sind erst bei Breite 24 optimal (Beam: Breite 8). Zuverlässig optimal kostet Monobeam ~3x die Expansionen von A\\*, Beam ~1.2x. Extrembeispiel Seed 200042: Beam findet ab Breite 4 den optimalen Pfad, Monobeam bis Breite 11 gar keinen. Das Paper nennt den Nachteil selbst: Platz c sieht nur Kinder der Plätze 1..c. | Diverse Beam Search / Stochastic Beam Search (andere Ansätze, hier nicht gebaut); im Paper: Monobeam mit Distanz-bis-Ziel-Schätzer (hier nicht gebaut) |
| **Jeder Baustein ist nötig** | Duplikatregel: ja - mit naiven Full-Beam-Duplikaten verletzen 6 % (Größe 12, 15 %), 6 % (40 %) und 10 % (Größe 20) der Instanzen die Monotonie, immer als Scheitern eines breiteren Laufs. Stoppregel: auf dem Raster nicht (0 %), auf der handgebauten Stopp-Falle ja. Pathmax feuert nur bei nicht konsistenter Heuristik (handgebaute Instanzen), auf dem Raster nie. | - |
| **Monotonie ist Vollständigkeit** | Nein. Monobeam scheitert bei schmaler Breite (Standardfall, Breite 4: 1 von 5 Läufen) - die Garantie heißt nur: nicht steigende Kosten in der Breite, Scheitern nach Erfolg kommt nicht vor. | **Beam Stack Search** (Zhou & Hansen 2005, hier nicht gebaut) |
| **Unbegrenzte Breite = optimal** | Für Monobeam ja (120 von 120 Rasterinstanzen bei Breite 2000; Umweg-Falle: Beam 10, Monobeam 3). Beam liefert dort den Pfad mit den wenigsten Kanten. | - |
| **Synthetische Instanzen** | Ein Raster mit Jitter, Vierer-Nachbarschaft, keine Zeitfenster, keine gerichteten Kanten, dazu drei handgebaute Graphen. Andere Graphstrukturen wurden nicht gemessen. | Echte Straßennetze (hier nicht gebaut) |
"""
)

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Plätze.** Der Strahl einer Ebene ist eine Folge $B = (b_1, \dots, b_k)$ (Plätze können leer sein). Für $c = 1, \dots, k$:
expandiere $b_c$, lege die Kinder in den Pool $P$ (Pathmax: $f(v) = \max\{g(v)+h(v),\ f(\text{Eltern})\}$), und setze
$b'_c$ = das Pool-Element mit kleinstem $f$ (Tie-Break kleines $h$), das die Duplikatregel besteht; es wird aus $P$ entfernt.

**Präfix-Lemma (Lemma 1/2).** $b'_c$ hängt nur von den Plätzen $1..c$ ab; die Strahlinhalte der Plätze $1..a$ sind bei Breite $a$ und
bei jeder Breite $b > a$ gleich. **Satz 1-3:** die Kosten sind bei zulässiger Heuristik in $k$ nicht steigend.

**Stopp.** Zielkinder werden nicht in den Pool gelegt, sondern setzen den Inkumbent $c^\* = \min(c^\*, g)$; die Suche endet,
sobald kein Platz mehr $f < c^\*$ hat. Pruning: Strahlknoten mit $f \ge c^\*$ fallen weg (Alg. 2).

**Duplikate (Alg. 3, hier in eigener Formulierung).** Closed-Eintrag (Platz $d$, $f_d$) je Zustand. Knoten für Platz $c$: neuer Zustand
oder $c < d$ - annehmen, Eintrag auf $(c, f)$ (auch bei schlechterem $f$); sonst Duplikat, falls $f \ge f_d$; besserer Weg
$f < f_d$ - annehmen, Eintrag nur bei $c = d$ aktualisieren.

**Nicht-Monotonie.** Eine Instanz heißt nicht-monoton, wenn es Breiten $k < k'$ mit $c(k') > c(k)$ gibt ($c = \infty$ bei Scheitern).

**Literatur.** Lemons, S., Linares López, C., Holte, R. C., & Ruml, W. (2022). *Beam Search: Faster and Monotonic.*
Proceedings of the International Conference on Automated Planning and Scheduling, 32(1), 222-230.

Implementiert in `mono_algorithm.py` (Suchkerne und `beam_search` aus der Beam-Search-Demo, `monobeam_search` neu),
`mono_graph.py`/`mono_scenario.py` (Graph, Raster und handgebaute Instanzen), `mono_evaluation.py` (Kennzahlen, Sweeps, Nicht-Monotonie).
        """
    )

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung für "
    "Ihr Unternehmen? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html)"
)
