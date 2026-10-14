# Vendored PyNiteFEA

Version: **3.2.0**, übernommen am 14.10.2026.
Quelle: offizielles PyPI-Wheel `pynitefea-3.2.0-py3-none-any.whl`.

- Release: https://pypi.org/project/PyNiteFEA/3.2.0/
- Upstream: https://github.com/JWock82/Pynite
- SHA256 des Wheels: `3e2d0e8e294ac1b328c756349131596b39c4c4dfce3663ec3b53cbf16f6aa99b`
- Lizenz: [LICENSE](LICENSE), MIT. README aus der Wheel-METADATA.

## Lokale Integrationsanpassungen

Die numerischen Solver-Algorithmen wurden unverändert übernommen.
Drei Dateien unterscheiden sich bewusst vom offiziellen Wheel:

1. `__init__.py`: `__version__ = "3.2.0"`, da Phaenotyp das Paket einbettet
   und keine installierte PyNiteFEA-Distribution voraussetzen kann.
2. `FEModel3D.py`: Fehlendes SciPy verhindert den Import nicht. Der bisherige
   Phaenotyp-Rechenweg `sparse=False` bleibt nutzbar. Fehlende Unterabhängigkeiten
   einer vorhandenen SciPy-Installation werden nicht verschluckt.
3. `ShearWall.py`: Matplotlib und PrettyTable werden erst in den betreffenden
   Zeichen-/Tabellenmethoden importiert. Phaenotyps Stab-/Flächenberechnung
   benötigt diese Ausgabe-Bibliotheken nicht.

Die alten lokalen P-Delta-Patches wurden nicht auf den neuen Code übertragen.
Die korrigierten Partitionierungsaufrufe und NumPy-Matrixdimensionen sind im
aktuellen Upstream-Code bereits enthalten.

## Abhängigkeiten und Prüfgrenzen

Upstream verlangt Python >= 3.11, NumPy >= 2.4, SciPy, Matplotlib und PrettyTable;
zusätzliche Pakete für die optionalen Upstream-Renderer und Reports siehe PyPI.
Diese Pakete wurden nicht global installiert oder in Phaenotyp eingebettet.

Geprüft wurde die Phaenotyp-Integration mit:

- Python 3.14, NumPy 2.5.4 und SciPy 1.18.1 in einem isolierten Testpfad:
  neun Tests bestanden, einschließlich dichter und dünnbesetzter Berechnung.
- Blender 5.2.0, Python 3.13.13, eingebautem NumPy 2.3.4, ohne SciPy,
  Matplotlib und PrettyTable: Add-on-Registrierung sowie lineare und
  P-Delta-Kragarmberechnung bestanden.

Blenders eingebautes NumPy liegt damit unter der offiziellen Upstream-Anforderung.
Die Prüfungen belegen die getesteten Phaenotyp-Rechenwege, keine vollständige
Kompatibilität aller PyNite-Funktionen/Renderer mit dieser NumPy-Version.
SciPy bleibt für den dünnbesetzten Solver und die Modalanalyse erforderlich.

Nach einem Update Blender neu starten und Modelle neu berechnen.
Pickle-Dateien enthalten versionsabhängige Klassen und sind keine dauerhaft
kompatiblen Austauschdateien; vorhandene Export-/Rückgabedateien neu erzeugen.
