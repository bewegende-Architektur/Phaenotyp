# Releasenotes

## 14.10.2026 – aktueller Arbeitsstand (Phaenotyp 0.4.0)

### PyNite aktualisiert

- Den eingebundenen Ordner `Pynite` durch die aktuelle stabile Version
  **PyNiteFEA 3.2.0** aus dem offiziellen PyPI-Wheel ersetzt, inklusive MIT-Lizenz.
- Herkunft, Prüfsumme, Abhängigkeiten und die drei lokalen
  Integrationsanpassungen in [Pynite/VENDORED.md](Pynite/VENDORED.md) dokumentiert.
- Versionsangabe für das eingebettete Paket fest auf 3.2.0 gesetzt.
- Den bestehenden NumPy-Rechenweg ohne SciPy erhalten; optionale
  Zeichen-/Tabellenbibliotheken werden bei Bedarf geladen.
- Flächenergebnisse explizit als Skalare aus den PyNite-Spaltenvektoren gelesen;
  vermeidet die unter aktuellem NumPy unzulässige Umwandlung eindimensionaler
  Arrays mit `float()`.
- Die älteren lokalen P-Delta-Patches nicht erneut eingespielt: die betreffenden
  Korrekturen sind bereits im aktuellen Upstream enthalten.
- Upstream bringt unter anderem verbesserte Stabilitätserkennung,
  schnellere Matrixassemblierung, Modalanalyse und weitere Funktionen für
  Schubwände und Fundamente mit. Neue Upstream-Funktionen werden durch dieses
  Update nicht automatisch als Phaenotyp-Bedienelemente verfügbar.
- Quellen: [PyPI-Release 3.2.0](https://pypi.org/project/PyNiteFEA/3.2.0/),
  [Upstream](https://github.com/JWock82/Pynite).

### Materialdatenbank

- Acryl/PMMA, PLA, GFK und Bambus in die Materialauswahl für Stäbe und Flächen aufgenommen.
- Acrylwerte einschließlich Knickkurve aus `Testing/Acrylstab.blend` übernommen;
  fehlende Vergleichsspannungsgrenze ergänzt.
- PLA-, GFK- und Bambuswerte als vorläufige Schätzungen gekennzeichnet;
  Knickkurven mit Spannungsobergrenze und Euler-Ansatz ergänzt.
- Quellen, Einheiten, Annahmen, Faserrichtung und Grenzen isotroper
  Flächenersatzmodelle in [MATERIAL_SOURCES.md](MATERIAL_SOURCES.md) dokumentiert.
- Hinweis: Acryl bildet die höheren Kurzzeit-Testgrenzen ab, keine Dauerlastbemessung.

### Verformung: Speicherung und Skalierung

- Neue Stabergebnisse ohne eingebettete Vergrößerung gespeichert (`deflection_scale = 1`).
  Die Vergrößerung erfolgt bei der Darstellung.
- Flächenverschiebungen von PyNite-Zentimetern mit 0,01 in Blender-Meter umgerechnet;
  damit die zuvor eingebettete zehnfache Vergrößerung entfernt.
- Flächendarstellung an `Scale deformation` angebunden und alte zehnfach
  gespeicherte Flächenergebnisse bei der Anzeige berücksichtigt.
- Tooltip des Mischreglers erläutert: 0 % zeigt die volle Verformung,
  100 % die unverformte Lage. Faktor 1 und Mischung 0 % entfernen die
  Anzeigeskalierung; das allein bestätigt nicht die physikalische Richtigkeit.

### Verformung: Kurvenkorrektur und offene Einschränkung

- Zunächst nur die Endpunkte der dargestellten Stabkurve an die berechneten
  Knotenpositionen angepasst. Dieser Zwischenstand konnte künstliche Knicke erzeugen
  und wurde durch die folgende Korrektur ersetzt.
- Aktuell werden Abweichungen zwischen ausgegebener PyNite-Stabkurve und
  Knotenpositionen linear über die gesamte Kurve verteilt.
- Inaktive Zug-/Druckstäbe werden als gerade Verbindung ihrer verschobenen Knoten dargestellt.
- **Die Kurvenkorrektur ist eine nachträgliche Anpassung der ausgegebenen Geometrie,
  kein behobener Fehler im PyNite-Solver. Sie wird unter `member["deflection"]`
  gespeichert. Die berechneten Kräfte und Knotenverschiebungen werden dabei nicht verändert.**
- Eine Abweichung zwischen Stabkurve und Knotenverschiebung bei Theorie II. Ordnung
  wurde mit einem räumlichen Testmodell auch nach dem Bibliotheksupdate reproduziert.
  Ihre Ursache und die physikalische Genauigkeit der angepassten Kurve sind weiterhin offen.
- Bedienung und Einschränkungen: [Testing/DEFORMATION.md](Testing/DEFORMATION.md).

### Validierung und Anwendung

- Neun automatisierte Prüfungen mit aktuellen NumPy-/SciPy-Abhängigkeiten bestanden:
  Verformungsskalierung, verbundene Endpunkte, inaktive Stäbe, verteilte
  Kurvenkorrektur, alte/neue Flächendaten, analytischer Kragarm,
  Flächendruckgleichgewicht, Ergebnis-API, Pickle-Rundlauf und Solververgleich.
- Ohne SciPy: acht Prüfungen bestanden, ein Sparse-Solver-Test übersprungen.
- In Blender 5.2: Add-on registriert/abgemeldet sowie lineare und P-Delta-Berechnung geprüft.
  Blender nutzt NumPy 2.3.4 und liegt unter der offiziellen Upstream-Anforderung
  NumPy >= 2.4; die vollständige PyNite-Funktionalität wurde damit nicht geprüft.
- Nach dem Update Blender neu starten und Modelle neu berechnen;
  versionsabhängige PyNite-Pickle-Dateien neu erzeugen.
- Prüfaufruf: `python -m unittest discover -s tests`.

## 09.10.2026 – Acryl und Verformungsskalierung (bereits committed)

- Eingabeminima für benutzerdefinierte E-/G-Moduln auf 100 kN/cm² sowie
  Vergleichsspannungsgrenze auf 0,01 kN/cm² abgesenkt (`9030a81`).
- Zwei lokale Fehler im damaligen PyNite-P-Delta-Rechenweg korrigiert:
  fehlendes Modellargument bei der Matrixpartitionierung und falsche Form
  für die dichte geometrische Steifigkeitsmatrix (`f6f2904`).
- Acryl-Testdatei angelegt (`eb1a112`).
- Benutzerdefinierte Stabmaterialien anhand ihrer tatsächlichen E-, G- und
  Dichtewerte in PyNite registriert, statt die Stahlvorgabe für alle
  `custom`-Materialien zu verwenden; kann berechnete Verformungen verändern.
- Materialdichte an PyNite übergeben.
- `Scale deformation` eingeführt (Standardwert 10); bisherigen festen Faktor
  10 durch einen einstellbaren Faktor ersetzt.
- Beim Speichern verwendeten Stabfaktor je Frame hinterlegt und bei späterer
  Änderung der Anzeige berücksichtigt.
- `Deflected / original` auf exakt 0 % einstellbar gemacht.
