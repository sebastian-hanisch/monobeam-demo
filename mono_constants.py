"""Konstanten der Monobeam-Demo: Raster-Geometrie (wortgleich zur Beam-Search-Demo), Regler, gemessene Werte, Presets."""

AREA = 100.0                     # Kantenlänge des Gebiets in km
JITTER = 0.35                    # Lageabweichung je Zelle, Anteil des Zellenabstands

SIDE_MIN, SIDE_MAX, DEFAULT_SIDE, SIDE_STEP = 5, 25, 12, 1     # Rastergröße (Zellen je Kante)
OBSTACLE_MIN, OBSTACLE_MAX, DEFAULT_OBSTACLE, OBSTACLE_STEP = 0, 40, 15, 5   # Prozent gesperrte Zellen
SEED_MAX = 999999
DEFAULT_SEED = 35

WIDTHS = (1, 2, 3, 4, 5, 6, 8, 12, 16, 24)     # Breiten des Reglers und des Breiten-Sweeps
DEFAULT_WIDTH = 4                              # MUSS Mitglied von WIDTHS sein (st.select_slider snappt sonst still)
NETWORKS = ("grid", "cuckoo", "stop", "detour")
NETWORK_LABELS = {"grid": "Raster", "cuckoo": "Kuckuck-Falle (handgebaut)", "stop": "Stopp-Falle (handgebaut)", "detour": "Umweg-Falle (handgebaut)"}
DEDUPS = ("slot", "full")
DEDUP_LABELS = {"slot": "Plätze-bewusst (Paper)", "full": "naiv (Full-Beam)"}
STOPS = ("continue", "level")
STOP_LABELS = {"continue": "weitersuchen (Paper)", "level": "nach 1. Lösungs-Schicht"}

SWEEP_SEEDS = tuple(range(100000, 100005))
SCALING_SIDES = (6, 10, 14, 18, 22)
OBSTACLE_SWEEP = (0, 10, 20, 30, 40)
MONO_SEEDS = tuple(range(200000, 200050))      # 50 feste Instanzen für die Nicht-Monotonie-Rate (wie beam-search-demo)
MONO_WIDTHS = tuple(range(1, 25))

# --- Gemessene Werte (MEDIAN über 5 feste Sweep-Instanzen, Seeds 100000-100004; Rastergröße 12, Hindernisdichte 15 %;
# --- 2026-09-23, alle Werte über ev.run_config/ev.sweep/ev.monotonicity nachgerechnet, s. tests/test_claims.py).
# --- Beam = beam_search mit f-Rang (das Beam des Papers). Lücke nur über GELÖSTE Läufe; Scheiter-Quote und Optimal-Anteil
# --- (Anteil ALLER Läufe mit Lücke 0) daneben. ---
# ZENTRALE FRAGE 1 - beseitigt Monobeam die Nicht-Monotonie? JA, ohne Ausnahme. Über 50 feste Instanzen (Seeds
#   200000-200049) und die Breiten 1-24 ist bei Beam bei 8 % (Größe 12, 15 % Hindernisse), 2 % (0 %), 10 % (40 %) und
#   10 % (Größe 20) irgendein breiterer Lauf schlechter; bei Monobeam bei 0 % in allen vier Einstellungen (auch Scheitern
#   nach Erfolg kommt nicht vor). Das Präfix-Lemma (Strahlinhalt der Plätze 1..a ist bei Breite a und b > a gleich) und
#   die Monotonie sind im Test direkt geprüft, ebenso über 1500 zufällige kleine Graphen mit nicht konsistenter Heuristik.
# ZENTRALE FRAGE 2 - was kostet die Garantie? VIEL, bei gleicher Breite: Monobeam war auf den 5 Sweep-Instanzen NIE besser
#   als Beam. Scheiter-Quote Beam/Monobeam bei Breite 1/2/3/4/5/6/8/12/16/24: 40/0/0/0/0/0/0/0/0/0 % gegen
#   40/20/20/20/20/0/0/0/0/0 %; Lücke im Median (Breite 2/3/4/5/6/8): Beam 4.5/0.35/0/0/0/0 %, Monobeam
#   5.2/3.2/1.8/0.6/0.44/0.35 %; alle 5 Instanzen optimal: Beam ab Breite 8, Monobeam erst bei Breite 24 (Optimal-Anteil
#   Monobeam 0/0/0/0/0/20/40/80/80/100 %). Expansionen gegen A*: Monobeam 0.25/0.44/0.68/0.87/1.06/1.22/1.54/2.13/2.60/2.96,
#   Beam 0.25/0.47/0.65/0.84/0.97/1.08/1.23/1.25/1.25/1.25 (Monobeam / Beam bis 2.1 bei Breite 24, weil es nach dem
#   ersten Zielfund bis f >= Inkumbent weitersucht). Zuverlässig optimal kostet Monobeam also ~3x A*, Beam ~1.2x A*.
#   Das Paper nennt diesen Nachteil selbst (Platz c sieht nur Kinder der Plätze 1..c) - hier gemessen: er ist auf dem
#   Raster groß. Extrembeispiel Seed 200042: Beam findet ab Breite 4 den optimalen Pfad (190.3 km), Monobeam findet bis
#   Breite 11 gar keinen Pfad, bei 12 einen mit 202.2 km, ab 13 den optimalen.
# ABLATIONEN (dieselben 50 Instanzen; Nicht-Monotonie-Rate 12/15 %, 12/0 %, 12/40 %, 20/15 %):
#   naive Full-Beam-Duplikate statt der plätze-bewussten: 6/0/6/10 % - immer als SCHEITERN eines breiteren Laufs trotz
#   Erfolg eines schmaleren (bei Größe 20 zusätzlich 2 % mit höheren Kosten) - die Duplikatregel ist nötig (Paper-Abb. 3).
#   Stopp nach der ersten Lösungs-Schicht statt Weitersuchen: 0/0/0/0 % - auf dem Raster NICHT nötig für die Monotonie
#   (das Paper begründet sie allgemein; die handgebaute Stopp-Falle zeigt, dass sie dort nötig ist).
# UNBEGRENZTE BREITE: Monobeam war bei Breite 2000 (weit über jeder Kandidatenzahl einer Ebene) auf allen 120 Rasterinstanzen (Seeds 300000-300039, 0/15/40 %
#   Hindernisse) optimal; auf der Umweg-Falle (Direktkante 10 gegen Umweg 3) liefert Beam bei JEDER Breite 10, Monobeam 3.
# HANDGEBAUTE INSTANZEN (explizite zulässige, nicht konsistente Heuristik; per Skriptsuche konstruiert und festgeschrieben):
#   Kuckuck-Falle: Beam Breite 1/2/3 = 7/8/7 (Breite 2 schlechter), Monobeam 7/7/7. Stopp-Falle: mit der Stoppregel "nach
#   der ersten Lösungs-Schicht" Breite 1/2/3 = 6/9/8, Monobeam mit Paper-Regel 6/6/6. Pathmax feuert dort (Kuckuck-Falle 3x
#   bei Breite 2), auf dem Raster (konsistente Heuristik) nie.

PRESETS = {
    "Standardfall (Voreinstellung)": {"network": "grid", "side": 12, "obstacle_pct": 15, "seed": 35, "width": 4, "dedup": "slot", "stop": "continue"},
    "Kuckuck-Falle (Breite 2)": {"network": "cuckoo", "side": 12, "obstacle_pct": 15, "seed": 35, "width": 2, "dedup": "slot", "stop": "continue"},
    "Stopp-Falle (Regel aus)": {"network": "stop", "side": 12, "obstacle_pct": 15, "seed": 35, "width": 2, "dedup": "slot", "stop": "level"},
    "Beam wird schlechter": {"network": "grid", "side": 12, "obstacle_pct": 15, "seed": 200007, "width": 2, "dedup": "slot", "stop": "continue"},
    "Naive Duplikate (Breite 2)": {"network": "grid", "side": 12, "obstacle_pct": 15, "seed": 200019, "width": 2, "dedup": "full", "stop": "continue"},
    "Preis der Monotonie (Breite 4)": {"network": "grid", "side": 12, "obstacle_pct": 15, "seed": 200042, "width": 4, "dedup": "slot", "stop": "continue"},
    "Umweg-Falle (Breite 2)": {"network": "detour", "side": 12, "obstacle_pct": 15, "seed": 35, "width": 2, "dedup": "slot", "stop": "continue"},
}
PRESET_HELP = {
    "Standardfall (Voreinstellung)": "Rastergröße 12, 15 % Hindernisse, Breite 4: Beam ist im Median optimal (Optimal-Anteil 60 %), Monobeam hat 1.8 % Lücke und scheitert in 1 von 5 Läufen. Diese Instanz (Seed 35) ist für beide optimal (175.9 km).",
    "Kuckuck-Falle (Breite 2)": "Handgebauter Graph mit expliziter Heuristik: Beam findet mit Breite 1 den optimalen Pfad (7), mit Breite 2 einen schlechteren (8), weil Kinder aus Platz 2 einen guten Kandidaten verdrängen (Kuckucksknoten). Monobeam bleibt bei 7.",
    "Stopp-Falle (Regel aus)": "Handgebauter Graph, Stoppregel \"nach der ersten Lösungs-Schicht\": Breite 1 findet 6, Breite 2 nur 9 - der breitere Lauf stoppt in der Schicht, in der er eine (schlechte) Lösung findet. Mit \"weitersuchen\" (Paper) findet Monobeam 6.",
    "Beam wird schlechter": "Seed 200007: Beam findet mit Breite 1 den optimalen Pfad (194.5 km), mit Breite 2 einen längeren (198.0 km). Monobeam bleibt bei 194.5 km - die Nicht-Monotonie ist verschwunden.",
    "Naive Duplikate (Breite 2)": "Seed 200019 mit naiven Full-Beam-Duplikaten: Breite 1 findet einen Pfad, Breite 2 scheitert. Mit den plätze-bewussten Duplikaten des Papers findet Monobeam bei Breite 2 einen Pfad (204.8 km).",
    "Preis der Monotonie (Breite 4)": "Seed 200042: Beam findet mit Breite 4 den optimalen Pfad (190.3 km), Monobeam bei gleicher Breite gar keinen - erst ab Breite 12 (202.2 km), optimal ab Breite 13. Der Preis der Garantie.",
    "Umweg-Falle (Breite 2)": "Direktkante 10 gegen Umweg 3: Beam findet bei jeder Breite den Pfad mit den wenigsten Kanten (10), Monobeam den optimalen (3).",
}
# Beobachtete Spannweite des MEDIANS der Monobeam-Lücke (%) über die 5 festen Sweep-Instanzen (mit Sicherheitsabstand),
# nur für die Raster-Presets (die handgebauten Instanzen sind feste Graphen, ihre Zahlen stehen als Tests).
PRESET_EXPECTED_BANDS = {
    "Standardfall (Voreinstellung)": (0.5, 4.0),
    "Beam wird schlechter": (3.0, 8.0),
    "Naive Duplikate (Breite 2)": (3.0, 8.0),
    "Preis der Monotonie (Breite 4)": (0.5, 4.0),
}
