"""Plotly-Abbildungen: Instanz (Raster oder handgebauter Graph mit Knotennamen, Kantengewichten und Heuristik), Held-Diagramm
"Kosten über Breite" (Beam gegen Monobeam), Strahl je Ebene nebeneinander (Beam links, Monobeam rechts mit Platznummern),
Pfad-Überlagerung, Sweeps mit beiden Verfahren, Optimal-/Scheiter-Anteile, Nicht-Monotonie-Balken. Achsen sind gesperrt
(fixedrange), damit Touch-Geräte beim Scrollen nicht zoomen."""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

NODE_COLOR = "#4c78a8"
BLOCKED_COLOR = "#9d755d"
OPT_COLOR = "#4c78a8"
BEAM_COLOR = "#e45756"
MONO_COLOR = "#7b3fbf"
GREY = "rgba(120,120,120,0.55)"
INF = float("inf")


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height, legend_y=-0.1):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=legend_y), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def _hand(inst):
    return inst.labels is not None


def _label(inst, node):
    if not _hand(inst):
        return str(node)
    return inst.labels[node] + (f" (h={inst.h[node]:g})" if inst.h is not None else "")


def _add(fig, trace, row=None, col=None):
    if row is None:
        fig.add_trace(trace)
    else:
        fig.add_trace(trace, row=row, col=col)


def _panel_base(fig, inst, row=None, col=None, node_alpha=0.3):
    """Hintergrund einer Karte: bei handgebauten Graphen Kanten mit Gewicht, sonst Raster-Zellen und Hindernisse."""
    xy = inst.graph.xy
    if _hand(inst):
        ex, ey, mx, my, mt = [], [], [], [], []
        for u in range(inst.graph.n):
            for v, w in zip(inst.graph.neighbors[u], inst.graph.weights[u]):
                if u < v:
                    ex += [xy[u, 0], xy[v, 0], None]
                    ey += [xy[u, 1], xy[v, 1], None]
                    mx.append((xy[u, 0] + xy[v, 0]) / 2)
                    my.append((xy[u, 1] + xy[v, 1]) / 2)
                    mt.append(f"{w:g}")
        _add(fig, go.Scatter(x=ex, y=ey, mode="lines", line=dict(color="rgba(120,120,120,0.5)", width=1.5), hoverinfo="skip", showlegend=False), row, col)
        _add(fig, go.Scatter(x=mx, y=my, mode="text", text=mt, textfont=dict(size=10, color="#777"), hoverinfo="skip", showlegend=False), row, col)
    else:
        _add(fig, go.Scatter(x=xy[:, 0], y=xy[:, 1], mode="markers", marker=dict(size=5, color=f"rgba(76,120,168,{node_alpha})"), name="Noch nicht berührt", hoverinfo="skip", showlegend=False), row, col)
        if len(inst.blocked_xy):
            _add(fig, go.Scatter(x=inst.blocked_xy[:, 0], y=inst.blocked_xy[:, 1], mode="markers", marker=dict(size=6, symbol="square", color=BLOCKED_COLOR), name="Hindernis", showlegend=False), row, col)


def _nodes_trace(inst, nodes, name, color, size, symbol="circle", showlegend=True, texts=None, line_color="white", ring=False):
    xy = inst.graph.xy
    nodes = list(nodes)
    marker = dict(size=size, symbol=symbol, color="rgba(0,0,0,0)" if ring else color, line=dict(width=2 if ring else 1, color=color if ring else line_color))
    if _hand(inst):
        text = texts if texts is not None else [inst.labels[n] for n in nodes]
        return go.Scatter(x=xy[nodes, 0] if nodes else [], y=xy[nodes, 1] if nodes else [], mode="markers+text", text=text, textposition="top center",
                          marker=marker, name=name, showlegend=showlegend, hoverinfo="skip")
    return go.Scatter(x=xy[nodes, 0] if nodes else [], y=xy[nodes, 1] if nodes else [], mode="markers+text" if texts else "markers", text=texts,
                      textposition="middle center", textfont=dict(size=8, color="white"), marker=marker, name=name, showlegend=showlegend, hoverinfo="skip")


def _start_goal(inst, row=None, col=None, showlegend=True):
    xy = inst.graph.xy
    return [
        (go.Scatter(x=[xy[inst.start, 0]], y=[xy[inst.start, 1]], mode="markers", marker=dict(size=16, symbol="star", color="#2ca02c", line=dict(width=1, color="white")), name="Start", showlegend=showlegend, hoverinfo="skip"), row, col),
        (go.Scatter(x=[xy[inst.goal, 0]], y=[xy[inst.goal, 1]], mode="markers", marker=dict(size=16, symbol="star", color="#d62728", line=dict(width=1, color="white")), name="Ziel", showlegend=showlegend, hoverinfo="skip"), row, col),
    ]


def _map_axes(fig, height, hand):
    fig.update_xaxes(showgrid=False, zeroline=False, showticklabels=False)
    fig.update_yaxes(showgrid=False, zeroline=False, showticklabels=False)
    if not hand:
        fig.update_xaxes(scaleanchor="y", scaleratio=1)
    return _base(fig, height)


def build_instance(inst):
    fig = go.Figure()
    _panel_base(fig, inst, node_alpha=0.9)
    if _hand(inst):
        all_nodes = [n for n in range(inst.graph.n) if n not in (inst.start, inst.goal)]
        fig.add_trace(_nodes_trace(inst, all_nodes, "Knoten", NODE_COLOR, 16, showlegend=False,
                                   texts=[_label(inst, n) for n in all_nodes]))
        for t, r, c in _start_goal(inst):
            fig.add_trace(t)
        return _map_axes(fig, 340, True)
    xy = inst.graph.xy
    fig.add_trace(go.Scatter(x=xy[:, 0], y=xy[:, 1], mode="markers", marker=dict(size=6, color=NODE_COLOR, line=dict(width=1, color="white")), name="Offene Zellen"))
    for t, r, c in _start_goal(inst):
        fig.add_trace(t)
    return _map_axes(fig, 460, False)


def build_level_maps(inst, beam_layers, mono_levels, level):
    """Ebene `level` (0-basiert) nebeneinander: links Beam (Strahl der Ebene), rechts Monobeam (Platznummer im Knoten).
    Orange Ring links = Kandidat, den nur Beam wählt; blauer Ring rechts = Knoten, den nur Monobeam wählt (Kuckucks-Wirkung)."""
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Beam Search (f)", "Monobeam"), horizontal_spacing=0.04)
    beam_nodes = list(beam_layers[level][0]) if level < len(beam_layers) else []
    slots = list(mono_levels[level]) if level < len(mono_levels) else []
    mono_nodes = [n for n in slots if n is not None]
    for col in (1, 2):
        _panel_base(fig, inst, 1, col)
    earlier_b = sorted({n for beam, _d in beam_layers[:level] for n in beam})
    earlier_m = sorted({n for lv in mono_levels[:level] for n in lv if n is not None})
    if earlier_b:
        fig.add_trace(_nodes_trace(inst, earlier_b, "Früher expandiert", GREY, 8, showlegend=True), row=1, col=1)
    if earlier_m:
        fig.add_trace(_nodes_trace(inst, earlier_m, "Früher expandiert", GREY, 8, showlegend=False), row=1, col=2)
    only_beam = [n for n in beam_nodes if n not in set(mono_nodes)]
    only_mono = [n for n in mono_nodes if n not in set(beam_nodes)]
    if beam_nodes:
        fig.add_trace(_nodes_trace(inst, beam_nodes, "Strahl (Beam)", BEAM_COLOR, 13), row=1, col=1)
    if slots:
        idx = [n for n in slots if n is not None]
        slot_texts = [(f"{inst.labels[n]} ({i + 1})" if _hand(inst) else str(i + 1)) for i, n in enumerate(slots) if n is not None]
        fig.add_trace(_nodes_trace(inst, idx, "Strahl (Monobeam, Zahl = Platz)", MONO_COLOR, 15, texts=slot_texts), row=1, col=2)
    if only_beam:
        fig.add_trace(_nodes_trace(inst, only_beam, "nur Beam wählt", "#f58518", 22, ring=True), row=1, col=1)
    if only_mono:
        fig.add_trace(_nodes_trace(inst, only_mono, "nur Monobeam wählt", "#2b8cbe", 22, ring=True), row=1, col=2)
    for t, r, c in _start_goal(inst, 1, 1, showlegend=True):
        fig.add_trace(t, row=1, col=1)
    for t, r, c in _start_goal(inst, 1, 2, showlegend=False):
        fig.add_trace(t, row=1, col=2)
    fig.update_xaxes(showgrid=False, zeroline=False, showticklabels=False)
    fig.update_yaxes(showgrid=False, zeroline=False, showticklabels=False)
    if not _hand(inst):
        fig.update_layout(xaxis=dict(scaleanchor="y", scaleratio=1), xaxis2=dict(scaleanchor="y2", scaleratio=1))
    _base(fig, 400 if _hand(inst) else 450, legend_y=-0.12)
    fig.update_layout(margin=dict(l=10, r=10, t=34, b=10))
    return fig


def build_paths(inst, opt_path, beam_path, mono_path):
    fig = go.Figure()
    _panel_base(fig, inst)
    xy = inst.graph.xy
    if _hand(inst):
        rest = [n for n in range(inst.graph.n) if n not in (inst.start, inst.goal)]
        fig.add_trace(_nodes_trace(inst, rest, "Knoten", NODE_COLOR, 12, showlegend=False, texts=[_label(inst, n) for n in rest]))
    if opt_path:
        p = xy[opt_path]
        fig.add_trace(go.Scatter(x=p[:, 0], y=p[:, 1], mode="lines", line=dict(color="rgba(76,120,168,0.5)", width=11), name="Optimum (Uniform-Cost)"))
    if beam_path:
        p = xy[beam_path]
        fig.add_trace(go.Scatter(x=p[:, 0], y=p[:, 1], mode="lines+markers", line=dict(color=BEAM_COLOR, width=3, dash="dot"), marker=dict(size=5, color=BEAM_COLOR), name="Beam Search (f)"))
    if mono_path:
        p = xy[mono_path]
        fig.add_trace(go.Scatter(x=p[:, 0], y=p[:, 1], mode="lines", line=dict(color=MONO_COLOR, width=2.5, dash="dash"), name="Monobeam"))
    for t, r, c in _start_goal(inst):
        fig.add_trace(t)
    return _map_axes(fig, 340 if _hand(inst) else 460, _hand(inst))


def _add_cost_series(fig, widths, costs, name, color, dash, top):
    ok = [(w, c) for w, c in zip(widths, costs) if c != INF]
    if ok:
        fig.add_trace(go.Scatter(x=[w for w, _ in ok], y=[c for _, c in ok], mode="lines+markers", line=dict(color=color, width=2.5, dash=dash), name=name))
    failed = [w for w, c in zip(widths, costs) if c == INF]
    if failed:
        fig.add_trace(go.Scatter(x=failed, y=[top] * len(failed), mode="markers", marker=dict(size=10, symbol="x", color=color, line=dict(width=2, color=color)), name=f"{name}: gescheitert"))


def build_cost_by_width(widths, beam_costs, mono_costs, optimum, mono_name="Monobeam"):
    """Held-Diagramm (Analogon zu Abb. 1 des Papers): Pfadkosten über die Breite für EINE Instanz. Beam zickzackt, Monobeam
    fällt nie; gescheiterte Läufe als x oberhalb der Kurven; gestrichelt das Optimum."""
    finite = [c for c in list(beam_costs) + list(mono_costs) if c != INF]
    top = (max(finite) if finite else optimum) * 1.05
    fig = go.Figure()
    _add_cost_series(fig, widths, beam_costs, "Beam Search (f)", BEAM_COLOR, "solid", top)
    _add_cost_series(fig, widths, mono_costs, mono_name, MONO_COLOR, "solid", top * 1.03)
    fig.add_hline(y=optimum, line=dict(color=OPT_COLOR, dash="dash", width=1.5), annotation_text="Optimum", annotation_position="bottom right")
    fig.update_xaxes(title_text="Breite k", dtick=1)
    fig.update_yaxes(title_text="Pfadkosten")
    return _base(fig, 360, legend_y=-0.3)


def build_sweep(rows, param_label, key_beam, key_mono, y_label, ref_line=None, ref_label=None):
    """Median als Linie, Minimum bis Maximum als Band (`<key>_lo`/`<key>_hi`), Beam und Monobeam gemeinsam."""
    xs = [r["value"] for r in rows]
    fig = go.Figure()
    for key, name, color in ((key_beam, "Beam Search (f)", BEAM_COLOR), (key_mono, "Monobeam", MONO_COLOR)):
        ys = [r[key] for r in rows]
        lo = [r[f"{key}_lo"] for r in rows]
        hi = [r[f"{key}_hi"] for r in rows]
        rgb = tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
        fig.add_trace(go.Scatter(x=xs + xs[::-1], y=hi + lo[::-1], mode="lines", fill="toself", fillcolor=f"rgba({rgb[0]},{rgb[1]},{rgb[2]},0.13)", line=dict(width=0), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers", line=dict(color=color, width=2.5), name=name))
    if ref_line is not None:
        fig.add_hline(y=ref_line, line=dict(color="#888", dash="dash", width=1.5), annotation_text=ref_label, annotation_position="top left")
    fig.update_xaxes(title_text=param_label, type="category")
    fig.update_yaxes(title_text=y_label)
    return _base(fig, 360, legend_y=-0.3)


def build_share_bars(rows, param_label):
    """Anteil ALLER Läufe: optimal (links) und gescheitert (rechts), Beam gegen Monobeam."""
    xs = [r["value"] for r in rows]
    fig = make_subplots(rows=1, cols=2, subplot_titles=("optimal (Lücke 0)", "gescheitert (kein Pfad)"), horizontal_spacing=0.08)
    for col, kind in ((1, "optimal"), (2, "failed")):
        fig.add_trace(go.Bar(x=xs, y=[r[f"beam_{kind}_share"] for r in rows], name="Beam Search (f)", marker_color=BEAM_COLOR, showlegend=col == 1), row=1, col=col)
        fig.add_trace(go.Bar(x=xs, y=[r[f"mono_{kind}_share"] for r in rows], name="Monobeam", marker_color=MONO_COLOR, showlegend=col == 1), row=1, col=col)
    fig.update_layout(barmode="group")
    fig.update_xaxes(title_text=param_label, type="category")
    fig.update_yaxes(title_text="Anteil der Läufe (%)", range=[0, 100])
    return _base(fig, 330, legend_y=-0.3)


def build_monotonicity_bars(result, labels):
    """Nicht-Monotonie-Rate je Variante: unten Scheitern trotz Erfolg eines schmaleren Laufs, oben höhere Kosten."""
    names = [labels[v] for v in result]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=names, y=[result[v]["wider_fails_share"] for v in result], name="breiter scheitert", marker_color="#9d755d"))
    fig.add_trace(go.Bar(x=names, y=[result[v]["wider_costlier_share"] for v in result], name="breiter kostet mehr", marker_color=BEAM_COLOR))
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title_text="Instanzen mit schlechterem breiteren Lauf (%)")
    return _base(fig, 340, legend_y=-0.35)
