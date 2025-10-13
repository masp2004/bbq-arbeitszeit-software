# Arbeitszeit-Erfassungssoftware für die BBQ GmbH

## Überblick

Dieses Repository dient der Planung und Entwicklung einer Arbeitszeit-Erfassungssoftware für die BBQ GmbH. Die Software unterstützt Mitarbeiter dabei, das deutsche Arbeitszeitgesetz (ArbZG) einzuhalten, Arbeitszeiten zu überwachen und drohende Verstöße zu erkennen. Sie wird in Python entwickelt, ist als ausführbare `.exe`-Datei oder Webapplikation für Windows 10/11 konzipiert und erfüllt die Anforderungen des 1. und 2. Semesters der DHBW. Der Source-Code ist Eigentum der BBQ GmbH und unterliegt keiner Veröffentlichungspflicht.

### Funktionale Anforderungen
- Einhaltung des deutschen Arbeitszeitgesetzes (ArbZG).
- Unterstützung für Wochenarbeitszeiten von 30/35/40 Stunden im Zeitrahmen von 6–22 Uhr.
- Anzeige von Gleitzeit (kumulierte Überstunden) pro Monat, Quartal und Jahr.
- Warnungen bei drohenden ArbZG-Verstößen und Hinweise zur Meldung an Vorgesetzte.
- Ampellogik zur Anzeige ausufernder Gleitzeit mit konfigurierbaren Grenzwerten.
- Passwortschutz mit individueller Änderung im Einstellungsmenü.

### Technische Anforderungen
- Entwicklung in Python ohne Lizenzkosten.
- Modulare Architektur für zukünftige Weiterentwicklung zu einer Mobile App.
- Automatisierte Tests mit `pytest` und PEP 8-Konformität mit `flake8` und `autopep8`.
- Source-Code-Management mit GitHub, einschließlich Branching-Strategie und Pull Requests.

## Branching-Strategie

Wir verwenden eine angepasste Gitflow-Strategie, um die Zusammenarbeit in einem geografisch verteilten Team zu unterstützen:

- **`main`**: Enthält produktionsreifen, stabilen Code. Geschützt durch Branch Protection Rules (2 Reviews, Status-Checks erforderlich).
- **`develop`**: Integrations-Branch für neue Features. Geschützt durch Branch Protection Rules (1 Review, Status-Checks erforderlich).
- **Feature-Branches** (`feature/<beschreibung>`): Für die Entwicklung neuer Funktionen, z. B. `feature/gleitzeit-anzeige`.
- **Hotfix-Branches** (`hotfix/<beschreibung>`): Für dringende Fehlerbehebungen im `main`-Branch.
- **Release-Branches** (`release/<version>`): Für die Vorbereitung von Releases.

### Branch Protection Rules
- **main**: Erfordert 2 Reviews, Status-Checks (`lint`, `test`) und keine direkten Pushes.
- **develop**: Erfordert 1 Review, Status-Checks (`lint`, `test`) und keine direkten Pushes.

## Pull-Request-Prozess

Detaillierte Anleitungen finden Sie im GitHub-Wiki des Repositories.

## Issues und Discussions

- **Issues**: Verwenden Sie Issues für die Planung von Aufgaben, Fehlerberichte und Feature-Vorschläge.
  - Erstellen Sie Issues mit klaren Titeln und Beschreibungen, z. B. „Implementierung der Ampellogik für Gleitzeit“.
  - Weisen Sie Issues Teammitgliedern zu und verknüpfen Sie sie mit Pull Requests.
- **Discussions**: Nutzen Sie Discussions für allgemeine Fragen, Brainstorming und Abstimmungen, z. B. zur Architektur oder zukünftigen Mobile-App-Features.
  - Beispiele: „Vorschlag für GUI-Framework: Tkinter vs. Flask“ oder „Diskussion über ArbZG-Validierungslogik“.

## Dokumentation

Die vollständige Dokumentation befindet sich im GitHub-Wiki und umfasst:
- **Source-Code-Dokumentation**: Inline-Kommentare und Docstrings in allen Python-Dateien.
- **Klassendiagramm**: Beschreibt die Klassenstruktur der Software (z. B. `Arbeitszeit`, `PasswortManager`).
- **Sequenzdiagramme**: Für zentrale Funktionen wie Gleitzeitberechnung und ArbZG-Überprüfung.
- **Teststrategie**: Beschreibung der automatisierten Tests und PEP 8-Formatierung (siehe `docs/test_strategy.md`).
- **Pull-Request-Anleitung**: Schritt-für-Schritt-Anleitung im Wiki.

## Entwicklungsumgebung einrichten

1. Klonen Sie das Repository:
   ```bash
   git clone https://github.com/masp2004/bbq-arbeitszeit-software.git
   cd bbq-arbeitszeit-software
   ```
2. Installieren Sie Python 3.10 (kompatibel mit Windows 10/11).
3. Erstellen Sie eine virtuelle Umgebung:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   .\venv\Scripts\activate     # Windows
   ```
4. Installieren Sie Abhängigkeiten:
   ```bash
   pip install -r requirements.txt
   ```
5. Installieren Sie Pre-Commit-Hooks:
   ```bash
   pip install pre-commit
   pre-commit install
   ```
6. Führen Sie Tests und Linting lokal aus:
   ```bash
   pytest tests/
   flake8 src/ tests/
   ```

## Automatisierte Tests und PEP 8

- **Tests**: Unit-, Integrations- und Systemtests werden mit `pytest` ausgeführt. Die Testabdeckung wird mit `pytest-cov` gemessen.
- **PEP 8**: Code wird mit `flake8` auf PEP 8-Konformität geprüft und mit `autopep8` formatiert. Pre-Commit-Hooks stellen sicher, dass Commits den Stilrichtlinien entsprechen.
- **CI-Pipeline**: GitHub Actions führt Tests und Linting bei jedem Push/Pull Request auf `main` und `develop` aus (siehe `.github/workflows/ci.yml`).

## Kontakt

Für Fragen wenden Sie sich an das Entwicklungsteam über GitHub Discussions oder kontaktieren Sie den Projektleiter Aurelia oder Stellvertrender Projektleiter Mika. Für technische Details oder Zugriffsanfragen wenden Sie sich an den Repository-Administrator Marvin.
