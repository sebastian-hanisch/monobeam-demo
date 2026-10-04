# Monobeam – kann mehr Breite je schaden? Nicht mehr. Aber zu welchem Preis? – Streamlit-Demo

**[→ Demo live ausprobieren](https://sebastianhanisch-monobeam-demo.streamlit.app/)**

Fünftes Stück der **Heuristische-Baumsuche-Linie** der "Konzepte"-Reihe für die Website "Sebastian Hanisch – Operations Research und Machine Learning" - die Fortsetzung von [beam-search-demo](../beam-search-demo): dort wurde gemessen, dass ein breiterer Strahl bei 2 bis 14 % der Instanzen **schlechter** ist als ein schmalerer (höhere Kosten, oder er scheitert trotz Erfolg eines schmaleren). Ursache laut Paper: **Kuckucksknoten** - Kinder aus späteren Strahlplätzen verdrängen Kandidaten, die ein schmalerer Strahl gewählt hätte. **Monobeam** (Lemons, Linares López, Holte & Ruml, ICAPS 2022) füllt die Plätze des Strahls **nacheinander** aus einem **gemeinsamen Kandidatenpool**: Platz c sieht nur Kinder der Plätze 1..c. Ein schmalerer Strahl ist damit ein Präfix eines breiteren, und die Kosten steigen mit der Breite nie.

**Einordnung in die Linie:** derselbe Graph, dieselben Instanzen und dieselben 50 festen Vergleichsinstanzen wie in [beam-search-demo](../beam-search-demo) (das dortige `beam_search` ist wortgleich kopiert und reproduziert dessen Zahlen, als Test hinterlegt); Beam Search mit f-Rang (das Beam des Papers), A\* und Uniform-Cost dienen als Vergleichsgrößen. Neu ist `monobeam_search` mit Pathmax, Weitersuchen bis f ≥ Inkumbent, Inkumbent-Pruning und plätze-bewusster Duplikaterkennung.

```
Greedy Best-First Search (Wurzel)                                                          [gebaut]
 ├─ Beam Search → {Diverse Beam Search, Monobeam}          [gebaut; Monobeam = DIESES STÜCK]
 ├─ A* → Iterative Deepening A* (IDA*)                                                     [gebaut]
 └─ Monte Carlo Tree Search (MCTS)                                                         [gebaut]
Beam Search + A* → Beam Stack Search (Konvergenzpunkt)                                     [gebaut]
```

Ergebnis in Kürze: **Die Garantie hält, ohne Ausnahme** - über 50 feste Instanzen und die Breiten 1-24 ist bei Beam bei 8 / 2 / 10 / 10 % der Instanzen (Größe 12 mit 15 % Hindernissen / 0 % / 40 % / Größe 20) irgendein breiterer Lauf schlechter, bei Monobeam bei **0 %** in allen vier Einstellungen. **Aber sie ist teuer:** bei gleicher Breite war Monobeam auf den 5 festen Sweep-Instanzen **nie besser** als Beam, es scheitert bei Breite 2-5 in 1 von 5 Läufen (Beam ab Breite 2 nie), und alle 5 Instanzen sind erst bei **Breite 24** optimal (Beam: Breite 8). Zuverlässig optimal kostet Monobeam ~**3x die Expansionen von A\***, Beam ~1.2x. Die Vorab-Hypothese "Monobeam beseitigt die Nicht-Monotonie" ist bestätigt, die stillschweigende Zusatzannahme "zu einem kleinen Preis" **widerlegt**.

| Frage | Ergebnis (Rastergröße 12, Hindernisdichte 15 %, Beam = f-Rang, sofern nicht anders angegeben; **Median** über 5 feste Instanzen, Seeds 100000–100004; vollständig deterministisch; Lücke nur über gelöste Läufe) |
|---|---|
| **Beseitigt Monobeam die Nicht-Monotonie?** | ✅ ja: 50 Instanzen (Seeds 200000–200049) x Breiten 1–24: Beam **8/2/10/10 %** (12/15 %, 12/0 %, 12/40 %, 20/15 %), Monobeam **0/0/0/0 %** - auch "Scheitern nach Erfolg" kommt nicht vor. Direkt geprüft: das Präfix-Lemma (Strahlinhalt der Plätze 1..a bei Breite a und b > a identisch) und die Monotonie, dazu über **1500 zufällige kleine Graphen** mit nicht konsistenter Heuristik |
| **Was kostet die Garantie? (Scheitern)** | ⚠️ Scheiter-Quote Beam / Monobeam bei Breite 1/2/3/4/5/6/8/12/16/24: **40/0/0/0/0/0/0/0/0/0 %** gegen **40/20/20/20/20/0/0/0/0/0 %** |
| **... (Lücke)** | ⚠️ Lücke im Median bei Breite 2/3/4/5/6/8: Beam 4.5/0.35/0/0/0/0 %, Monobeam **5.2/3.2/1.8/0.6/0.44/0.35 %**; Monobeam war bei gleicher Breite auf den 5 Instanzen **nie besser** als Beam (bei Breite 2-8 in 3-4 von 4-5 verglichenen Läufen schlechter) |
| **... (alle optimal)** | ⚠️ Optimal-Anteil aller Läufe: Beam 0/0/40/60/60/60/100/100/100/100 %, Monobeam 0/0/0/0/0/20/40/80/80/100 % - **Beam ab Breite 8, Monobeam erst bei Breite 24** |
| **... (Expansionen)** | ⚠️ Expansionen gegen A\* bei Breite 1/2/3/4/5/6/8/12/16/24: Monobeam **0.25/0.44/0.68/0.87/1.06/1.22/1.54/2.13/2.60/2.96**, Beam 0.25/0.47/0.65/0.84/0.97/1.08/1.23/1.25/1.25/1.25 (Monobeam / Beam bis **2.1** bei Breite 24, weil es nach dem ersten Zielfund bis f ≥ Inkumbent weitersucht) |
| **Extrembeispiel** | ⚠️ Seed 200042: Beam findet ab Breite 4 den optimalen Pfad (190.3 km); Monobeam findet bis Breite 11 **gar keinen** Pfad, bei 12 einen mit 202.2 km, ab 13 den optimalen |
| **Welcher Baustein trägt die Garantie?** | **Duplikatregel: ja** - mit naiven Full-Beam-Duplikaten verletzen **6/0/6/10 %** der Instanzen die Monotonie, immer als Scheitern eines breiteren Laufs (bei Größe 20 zusätzlich 2 % mit höheren Kosten; Paper-Abb. 3). **Stoppregel: auf dem Raster nein** (0/0/0/0 %), auf der handgebauten Stopp-Falle ja |
| **Unbegrenzte Breite?** | ✅ Monobeam war bei Breite 2000 (weit über jeder Kandidatenzahl einer Ebene) auf **allen 120** Rasterinstanzen (Seeds 300000–300039, 0/15/40 % Hindernisse) optimal; auf der Umweg-Falle (Direktkante 10 gegen Umweg 3) liefert Beam bei **jeder** Breite 10, Monobeam 3 |
| **Handgebaute Fälle** | Kuckuck-Falle: Beam Breite 1/2/3 = **7/8/7**, Monobeam 7/7/7. Stopp-Falle: mit der Stoppregel "nach der ersten Lösungs-Schicht" Breite 1/2/3 = **6/9/8**, Monobeam mit Paper-Regel 6/6/6 |

## Was die Demo zeigt

1. **Monobeam in Aktion** (Schritt-Slider): **Instanz** → **Strahl je Ebene** (Ebenen-Slider; links Beam, rechts Monobeam mit Platznummern; orange Ring = nur Beam wählt den Knoten, blauer Ring = nur Monobeam - genau dort trennen sich die Verfahren) → **Ergebnis** (Beam, Monobeam und Optimum überlagert; ein gescheiterter Lauf behauptet keinen Pfad).
2. **🎯 Kosten über die Breite** (Analogon zu Abb. 1 des Papers): Pfadkosten der aktuellen Instanz für Breite 1–24, Beam zickzackt (x = gescheitert), Monobeam fällt nie.
3. **Beam gegen Monobeam bei der gewählten Breite:** Lücke beider, Expansionen Mono / Beam, Vergleich (besser / gleich / schlechter).
4. **📐 Sweeps** über Breite, Hindernisdichte und Rastergröße (Median, Min-Max-Band, beide Verfahren), wählbare Kennzahl (Lücke / Expansionen gegen A\* / Optimal- und Scheiter-Anteil), 5 feste Instanzen ab Seed 100000.
5. **🔬 Experiment:** Nicht-Monotonie-Rate über 50 feste Instanzen für Beam, Monobeam und die beiden Ablationen (naive Duplikate, Stopp nach der ersten Lösungs-Schicht).
6. **🚧 Grenzen:** Tabelle "Annahme – was passiert – wer setzt an".

Regler: Instanz (Raster / **Kuckuck-Falle** / **Stopp-Falle** / **Umweg-Falle**, die drei handgebauten Graphen mit expliziter Heuristik zeigen je EINEN Mechanismus), Rastergröße (5–25), Hindernisdichte (0–40 %), Seed der Instanz (+ 🎲), **Breite** (1 bis 24), **Duplikate** (plätze-bewusst / naiv) und **Stoppregel** (weitersuchen / nach der ersten Lösungs-Schicht) - die beiden Ablations-Schalter wirken auf die Monobeam-Kurve und die Metriken. Kein Zufall im Kern, kein Ketten-Seed, kein Bewertungsbudget - vollständig deterministisch.

## Messwerte der Presets

| Preset | Instanz | Ergebnis |
|---|---|---|
| Standardfall (Voreinstellung) | Seed 35, Breite 4 | für beide optimal (175.9 km); 80 Expansionen Beam, 82 Monobeam, 82 A\* (im Median über die 5 festen Instanzen: Monobeam 1.8 % Lücke, 1 von 5 gescheitert, Beam 60 % optimal) |
| Kuckuck-Falle (Breite 2) | handgebaut | Beam 8, Monobeam 7 (Optimum 7) |
| Stopp-Falle (Regel aus) | handgebaut, Stoppregel "nach 1. Lösungs-Schicht" | Monobeam 9 (mit der Paper-Regel 6) |
| Beam wird schlechter | Seed 200007, Breite 2 | Beam Breite 1: 194.5 km, Breite 2: 198.0 km; Monobeam 194.5 km |
| Naive Duplikate (Breite 2) | Seed 200019, naive Duplikate | Breite 1 findet einen Pfad, Breite 2 scheitert; mit den plätze-bewussten Duplikaten findet Monobeam einen (204.8 km, Optimum 189.2 km) |
| Preis der Monotonie (Breite 4) | Seed 200042 | Beam optimal (190.3 km), Monobeam findet keinen Pfad (erst ab Breite 12) |
| Umweg-Falle (Breite 2) | handgebaut | Beam 10 (wenigste Kanten), Monobeam 3 (Optimum) |

Die einzelne Instanz weicht von den Sweep-Medianen ab - die Mediane oben sind die belastbaren Zahlen; die Raster-Presets prüfen sich zusätzlich über die 5 festen Sweep-Instanzen gegen eine gemessene Spannweite, die Aussagen der Presets (Kuckuck, Stopp, Beam wird schlechter, naive Duplikate, Preis, Umweg) sind als eigene Tests hinterlegt (`tests/test_presets.py`).

## Modell und Verfahren

- **Instanz und Graph** (`mono_scenario.py`, `mono_graph.py`): das gestörte Raster mit Hindernissen aus [beam-search-demo](../beam-search-demo) (Kantengewicht = echter euklidischer Abstand); statt der dortigen Sackgassen-Falle **drei handgebaute Graphen mit expliziter, zulässiger, aber nicht konsistenter Heuristik** `h`, per Skriptsuche über Gewichte und h konstruiert, dann festgeschrieben und getestet (Kuckuck-, Stopp- und Umweg-Falle).
- **Suchkern** (`mono_algorithm.py`): `_search`, `greedy_best_first`, `uniform_cost_search`, `a_star`, `beam_search` aus der Beam-Search-Demo; NEU `monobeam_search`: der Strahl ist eine Folge fester Länge (Platz → Knoten oder leer); je Ebene expandiert Platz c seinen Knoten, legt die Kinder (Pathmax: f = max(g + h, f des Elternknotens)) in einen Pool (heapq nach f, Tie-Break kleines h) und nimmt **sofort** das beste Pool-Element, das die Duplikatregel besteht, als Knoten der nächsten Ebene, bevor Platz c+1 dran ist. Zielkinder legen einen Inkumbent fest (kein Pool-Eintrag); die Suche läuft, solange ein Platz f < Inkumbent hat, Strahlknoten mit f ≥ Inkumbent fallen weg. `dedup`, `continue_after_goal`, `prune`, `pathmax` sind Ablations-Schalter (Standard = Paper).
- **Duplikatregel (Alg. 3, in eigener Formulierung):** Der Volltext-Pseudocode des Papers war beim Auslesen nicht eindeutig lesbar; die Regel ist deshalb aus der Beschreibung im Text hergeleitet und **nicht abgeschrieben, sondern durch die Tests abgesichert** (Präfix-Lemma, Monotonie-Satz, Optimalität bei unbegrenzter Breite). Closed-Eintrag (Platz d, f) je Zustand; Knoten für Platz c: neuer Zustand oder c < d → annehmen, Eintrag auf (c, f) (auch bei schlechterem f); sonst Duplikat, falls f ≥ f_d; ein besserer Weg (f < f_d) wird angenommen, der Eintrag nur bei c = d aktualisiert. **Folge:** ein Zustand kann in einer Ebene auf zwei Plätzen stehen, wenn ein höherer Platz einen besseren Weg findet (der schmalere Lauf sieht diesen Platz nie) - gewollt, nötig für Präfix-Lemma und Optimalität.
- **Auswertung** (`mono_evaluation.py`): Lücke ggü. Uniform-Cost **nur über gelöste Läufe**, daneben stets Scheiter-Quote und Optimal-Anteil (Anteil ALLER Läufe mit Lücke 0); Expansions-Verhältnisse gegen A\* und Monobeam / Beam; Paarvergleich besser / gleich / schlechter; `monotonicity` = Anteil der Instanzen, bei denen ein breiterer Lauf schlechter ist, für Beam, Monobeam und die Ablationen.

## Was nicht funktioniert hat / Grenzen

- **Vorab-Hypothese "Monobeam beseitigt die Nicht-Monotonie" - bestätigt; die Zusatzannahme "zu kleinem Preis" - WIDERLEGT.** Bei gleicher Breite war Monobeam nie besser als Beam, scheitert bei mittleren Breiten häufiger, braucht Breite 24 statt 8 für 5 von 5 optimal und ~3x A\* statt ~1.2x Expansionen. Das Paper nennt diesen Nachteil selbst ("Monotonie begrenzt den Pool", Platz c sieht nur Kinder der Plätze 1..c) - hier gemessen: auf dem Raster ist er groß. Warum genau er auf dem Raster so groß ausfällt, wird nicht isoliert untersucht.
- **Monotonie ist nicht Vollständigkeit.** Monobeam scheitert bei schmaler Breite (Standardfall, Breite 4: 1 von 5 Läufen); die Garantie heißt nur "nicht steigende Kosten in der Breite, Scheitern nach Erfolg kommt nicht vor". Beam Search + Backtracking ist **Beam Stack Search** (Zhou & Hansen 2005) - eigene Demo ([beam-stack-demo](../beam-stack-demo)).
- **Jeder Baustein nötig?** Duplikatregel: ja (gemessen). Stoppregel: auf dem Raster nicht (0 %), auf der handgebauten Stopp-Falle ja. Pathmax feuert nur bei nicht konsistenter Heuristik (handgebaute Instanzen), auf dem Raster nie; ohne Pathmax bleiben die Kosten dort identisch (Test).
- **Unbegrenzte Breite:** Monobeam ist dort optimal (Raster und Umweg-Falle), Beam liefert den Pfad mit den wenigsten Kanten.
- **Nicht gebaut:** der zweite Beitrag des Papers (Distanz-bis-Ziel-Schätzer für nicht einheitliche Kosten), Bead/Monobead, "Trading Monotonicity for Cost", Stochastic Beam Search.
- **Synthetische Instanzen:** ein Raster mit Jitter, Vierer-Nachbarschaft, keine Zeitfenster, keine gerichteten Kanten, dazu drei handgebaute Graphen. Andere Graphstrukturen wurden nicht gemessen.

## Praxis im Portfolio

- **[freight_demo](../freight_demo)** (Containerkonsolidierung): `monobeam_construction` wurde dort implementiert und mit einem eigenen Ensemble-Ansatz (unabhängige Konstruktionen, Minimum - ebenfalls monoton) verglichen: beide monoton, Monobeam etwa 4.3x langsamer, Lösungsqualität nah beieinander, keiner dominiert. Später wurde es als Startpunkt wieder entfernt, weil die LNS-Politur den kleinen Restbeitrag vollständig absorbierte (0 von 40 Fällen).
- **[linehaul-demo](../linehaul-demo)** (Hauptlauf-Netzwerkdesign): Monobeam wurde erwogen; die dortige Greedy-Suche ist eine lokale Verbesserung über einer vollständigen Lösung, keine sequenzielle Konstruktion, dem Monobeam-Mechanismus fehlte das Fundament. Eine einfache Grenzkosten-Konstruktion brachte den Zusatznutzen ohne den vollen Monobeam-Apparat.

Beides passt zum Ergebnis dieser Demo: eine Monotonie-Garantie in der Beam-Breite ist nützlich, wenn man die Breite "so groß wie möglich" wählen will, ohne Verschlechterung befürchten zu müssen - sie kauft aber keine bessere Lösung bei kleiner Breite.

## Verifikation

- **Gültiger Pfad** (zusammenhängend, Start bis Ziel, ohne Wiederholung, Kosten gegen unabhängige Neuberechnung) für beide Duplikatregeln und beide Stoppregeln; **Kosten nie unter dem Optimum** (gegen vollständige Enumeration aller einfachen Pfade auf kleinen Instanzen); Determinismus; ein nicht erreichbares Ziel scheitert immer.
- **Präfix-Lemma direkt** (Lemma 1/2 des Papers, mit `prune=False`): Strahlinhalt je Ebene bei Breite a == erste a Plätze bei Breite b > a, über 36 Rasterinstanzen und die drei handgebauten Graphen.
- **Monotonie-Satz direkt** (Satz 1-3): Kosten nicht steigend über die Breiten 1–24, inf zählt (kein Scheitern nach Erfolg) - über 75 Rasterinstanzen (0/15/40 % Hindernisse), die handgebauten Graphen und **1500 zufällige kleine Graphen mit nicht konsistenter Heuristik**.
- **Unbegrenzte Breite == UCS-Optimum** auf 120 Rasterinstanzen und der Umweg-Falle (Beam: 10, Monobeam: 3).
- **Inkumbent-Pruning** (Alg. 2, Lemma 4): gleiche Kosten mit und ohne, Expansionen mit ≤ ohne. **Pathmax:** feuert auf den nicht konsistenten Instanzen, nie auf dem Raster, Abschalten ändert dort nichts.
- **Buchführung:** je Ebene genau Breite Plätze, Expansionen == Summe der belegten Plätze, Pfad gültig, nie an die Sicherheits-Obergrenze gestoßen; **Kopie treu:** `beam_search` reproduziert die Zahlen aus beam-search-demo.
- **Ablationen und Fixtures als Tests:** Kuckuck-Falle (Beam 7/8/7/7, Monobeam 7/7/7/7), Stopp-Falle (6/9/8/8 gegen 6/6/6/6), Seed 200019 mit naiven Duplikaten (Breite 2 scheitert nach Erfolg mit Breite 1).
- **Alle Zahlen der App-Texte sind als Tests hinterlegt**, über dieselben Auswertungsfunktionen wie die App selbst (`ev.run_config`/`ev.sweep`/`ev.monotonicity`), NIE über ein Ad-hoc-Skript; AppTest-Rauchtests (Voreinstellung, jedes Preset, jeder Schritt, jede Ebene, alle vier Instanz-Typen, gescheiterte Läufe in jedem Schritt, Extremwerte, Ablations-Schalter, Würfel, Permalink-Grenzen, Instanzwechsel, ausgeblendete Regler bei den handgebauten Graphen, Sweeps und Experiment auf Abruf, Footer). 587 Tests.

Literatur: Lemons, S., Linares López, C., Holte, R. C., & Ruml, W. (2022). *Beam Search: Faster and Monotonic.* Proceedings of the International Conference on Automated Planning and Scheduling, 32(1), 222-230. Kontext: Zhou, R., & Hansen, E. A. (2005). *Beam-Stack Search: Integrating Backtracking with Beam Search.* ICAPS 2005.

## Dateistruktur

| Datei | Zweck |
|---|---|
| `app.py` | Streamlit-App: Instanz-Umschalter, Schritte (mit Ebenen-Slider), Held-Diagramm, Vergleich, 📐 Sweeps, 🔬 Experiment, 🚧 Grenzen, Mathe |
| `mono_algorithm.py` | Suchkerne und `beam_search` (Kopie aus der Beam-Search-Demo) + `monobeam_search` |
| `mono_graph.py`, `mono_scenario.py` | Graph, Rasterinstanz (Kopie) und die drei handgebauten Instanzen |
| `mono_constants.py` | Konstanten, Presets, gemessene Werte |
| `mono_evaluation.py` | Lücke, Scheiter-Quote, Verhältnisse, Paarvergleich, Sweeps, Nicht-Monotonie für alle Varianten |
| `mono_presets.py`, `mono_visualization.py` | Permalink/Presets, Plotly-Figuren (Kosten über Breite, Ebenen-Karten, Sweeps, Nicht-Monotonie-Balken) |
| `tests/` | Zentrale Korrektheitskette (Präfix-Lemma, Monotonie-Satz), Szenario/Auswertung, Aussagen der App, Presets, AppTest |

## Lokal ausführen

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

## Tests ausführen

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zur Reihe: [Heuristische Baumsuche: Greedy bis MCTS](https://sebastianhanisch.net/konzepte-heuristische-baumsuche.html).
