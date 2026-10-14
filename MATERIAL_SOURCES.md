# Neue Materialvorgaben: Acryl, PLA, GFK und Bambus

Stand: 14.10.2026. Die Vorgaben stehen für Stäbe und Flächenelemente zur Auswahl.
Alle E-, G- und Spannungswerte in `material.py` sind in kN/cm², Dichten in g/cm³.
Umrechnung: 1 kN/cm² = 10 MPa; 1 GPa = 100 kN/cm².

| Vorgabe | E | G | Dichte | zul. Normalspannung | zul. Schub/Torsion | zul. Vergleichsspannung | ν für Flächen |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Acryl (PMMA, Testing) | 310 | 115 | 1,19 | 5 | 3 / 3 | 5 | 0,347826 |
| PLA (geschätzt) | 360 | 133,333333 | 1,24 | 2 | 1 / 1 | 2 | 0,35 |
| GFK (längs, geschätzt) | 1700 | 300 | 1,70 | 7 | 1 / 1 | 7 | 0,30 |
| Bambus (längs, geschätzt) | 1500 | 100 | 0,56 | 1,5 | 0,1 / 0,1 | 1,5 | 0,30 |

## Herkunft und Schätzungen

### Acryl

Primärquelle im Projekt: [Testing/Acrylstab.blend](Testing/Acrylstab.blend),
Scene → `<Phaenotyp>` → `members` (alle vier Stäbe).
E = 310, G = 115, Dichte = 1,19, Normalspannung = 5, Schub = 3,
Torsion = 3 und die vollständige 25-Punkte-Knickkurve wurden übernommen.
Die gespeicherte Dichte 1,190000057 wurde auf 1,19 gerundet.
Eine Vergleichsspannungsgrenze ist dort nicht gespeichert: 5 wurde ergänzend
angenommen. ν wurde mit E/(2G) − 1 abgeleitet.

Plausibilitätsquelle: Röhm, [PLEXIGLAS Tubes and Rods, Ref. 211-12,
S. 6](https://www.plexiglas.de/files/plexiglas-content/pdf/technische-informationen/211-12-EN-PLEXIGLAS-rods-and-tubes.pdf).
Nennt Dichte 1,19 g/cm³, Kurzzeit-E 3300 MPa und Zugfestigkeit 80 MPa bei 23 °C.
Die Testwerte werden bewusst beibehalten. Die dort ebenfalls genannte zulässige
Materialspannung 5–10 MPa ist deutlich niedriger als die Testgrenze 50 MPa:
Das Acryl-Preset bildet den bestehenden Kurzzeittest ab, keine Dauerlastbemessung.

### PLA

NatureWorks, [Ingeo 4043D, Technical Data Sheet, 3D Printing Monofilament,
S. 1](https://www.natureworksllc.com/~/media/files/natureworks/technical-documents/technical-data-sheets/technicaldatasheet_4043d_3d-monofilament_pdf.pdf?la=en).
Dichte 1,24 g/cm³ und E ≈ 3,6 GPa übernommen. Die Tabelle hat beim E-Modul
eine uneindeutige MPa-Beschriftung; 524000 psi entsprechen ca. 3,61 GPa.
ν = 0,35 ist eine Annahme, G = E/[2(1+ν)] daraus abgeleitet.
Normal-/Vergleichsspannung 20 MPa und Schub-/Torsionsspannung 10 MPa sind
Projektannahmen, keine Herstellerfreigaben (Bruchzugfestigkeit im Datenblatt: 53 MPa).
Angenommen wird massives, ungefülltes PLA bei Raumtemperatur. Druckrichtung,
Schichthaftung und Infill werden nicht abgebildet.

### GFK

Strongwell, [Introduction to EXTREN, S. 3 und 7](https://www.strongwell.com/wp-content/uploads/2015/05/Introduction-To-Extren.pdf).
Bezugsfall: pultrudierte EXTREN-Profile 500/525 längs zur Faser.
2,5 Millionen psi Zugmodul entsprechen ca. 17,24 GPa; gerundet 17 GPa.
Dichte aus spezifischem Gewicht 1,7. G = 3 GPa und ν = 0,30 sind Schätzungen.
Die Grenzspannungen 70 MPa normal und 10 MPa Schub/Torsion sind frei gewählte
reduzierte Modellgrenzen, keine normativen Bemessungswerte. Die Vergleichsgrenze
ist gleich der Normalgrenze gesetzt. Die Quelle beschreibt explizit Anisotropie;
der generische Eintrag ist keine Gleichsetzung aller GFK-Laminate mit EXTREN.

### Bambus

Rizky Oulia O P L / Universitas Gadjah Mada (2019),
[Sifat Mekanika dan Fisika Bambu Wulung (Studi Kasus: Bambu Daerah Seyegan),
Abstract](https://etd.repository.ugm.ac.id/penelitian/detail/180185).
Versuche an Wulung-Bambus aus Seyegan: Dichte 0,558 g/cm³ bei ca. 13 % Feuchte,
Biege-E 15392 MPa; gerundet 0,56 und 15 GPa.
G = 1 GPa und ν = 0,30 sind Schätzungen. Normal-/Vergleichsgrenze 15 MPa und
Schub-/Torsionsgrenze 1 MPa sind Projektannahmen, reduziert gegenüber den
berichteten Druck- (53,4 MPa mit Knoten) und Schubfestigkeiten (3,2–4,4 MPa).
Gilt als Näherung für trockenen Bambus längs zur Faser, nicht quer zur Faser
oder pauschal für andere Arten, Feuchtegrade und Bambusprodukte.

## Knicken und Flächenelemente

Acryl verwendet unverändert die Knickkurve aus der Testdatei.
PLA, GFK und Bambus verwenden eine geschätzte Kurve:
`min(zulässige Normalspannung, π² E / λ²)` für λ = 10, 20, …, 250,
gerundet auf sechs Nachkommastellen. Euler-Formel als Hintergrund:
[Maschinenbau-Wissen: Knicken nach Euler](https://www.maschinenbau-wissen.de/skript3/mechanik/festigkeitslehre/134-knicken-euler).
Die Kurven sind keine Knicklinien nach ÖNORM B 4600; Imperfektionen,
Kriechen und lokale Instabilität sind darin nicht gesondert berücksichtigt.

Das vorhandene Flächenmodell hat nur einen E-Modul und eine Querdehnzahl.
GFK und Bambus werden dort als isotrope Ersatzmaterialien behandelt; der
Stab-G-Modul ist kein konsistenter isotroper G-Modul zu E und ν dieser Flächen.
Die Flächensteifigkeit kann daher insbesondere quer zur Faser deutlich abweichen.
Auch die Vergleichsspannungsgrenzen sind vereinfachte Modellparameter und
kein werkstoffspezifischer Versagensnachweis für diese anisotropen Materialien.
Die Dropdown-Hinweise kennzeichnen die Annahmen und verweisen auf diese Datei.
