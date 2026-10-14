# Verformungsdarstellung

Für eine Darstellung der berechneten Verschiebung in 1:1:

- `Scale deformation` = **1**
- `Deflected / original` = **0 %**

Der effektive Darstellungsfaktor ist
`Scale deformation × (1 − Deflected / original / 100)`.
Bei den Standardwerten 10 und 50 % beträgt er somit 5.
100 % im zweiten Regler zeigt die unverformte Geometrie.
1:1 bezieht sich auf das berechnete Lastmodell einschließlich eingestellter
Last-/Materialfaktoren, nicht automatisch auf einen realen Versuch.

Blender-Weltkoordinaten werden für PyNite mit 100 in Zentimeter umgerechnet;
Verschiebungen werden mit 0,01 zurück in Meter umgerechnet. Y und Z werden
zwischen beiden Koordinatensystemen vertauscht. Der historische Faktor 10
war eine zusätzliche Vergrößerung der Darstellung, keine notwendige
Einheitenumrechnung.

Neue Stab- und Flächenergebnisse speichern physische Verformungen mit
`deflection_scale[frame] = 1`. Die Anzeige skaliert diese Verschiebungen.
Ältere Stabergebnisse verwenden den gespeicherten Faktor (ohne Eintrag: 10).
Ältere Flächenergebnisse ohne Eintrag wurden mit 0,1 statt 0,01 umgerechnet
und werden bei der Darstellung entsprechend durch 10 geteilt.

Stabenden werden unmittelbar aus den Verschiebungen des gemeinsamen
PyNite-Knotens gebildet. Das gilt auch für inaktive Zug-/Druckstäbe,
bei denen PyNites `deflection()` null liefert. Inaktive Stäbe werden als gerade Verbindung ihrer verschobenen Knoten dargestellt.
Bei aktiven Stäben wird eine Abweichung zwischen ausgegebener Stabkurve und
Knotenposition über die gesamte Kurve linear korrigiert. Dies erhält die
Krümmung der ausgegebenen Kurve und verhindert einen künstlichen Knick am Ende.
Das ist eine Korrektur der Darstellung, keine Reparatur der PyNite-Berechnung
nach Theorie II. Ordnung und kein zusätzlicher Nachweis ihrer Genauigkeit.
Nach dem Update vorhandene Modelle neu berechnen, um die korrigierten
Endpunkte in den gespeicherten Ergebnissen zu erhalten.

Prüfung: `python -m unittest discover -s tests -p 'test_deformation.py'`.
Die Prüfungen verwenden den lokalen PyNite-Code mit räumlich gedrehten,
verbundenen Stäben und prüfen Einheiten, Endpunkte, Unabhängigkeit der
Berechnung vom Anzeigefaktor sowie alte und neue Flächenergebnisse.
