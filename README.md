# Arbeitszeit-Erfassungssoftware für die BBQ GmbH

## Überblick

Dieses Repository dient der Planung und Entwicklung einer Arbeitszeit-Erfassungssoftware für die BBQ GmbH. Die Software unterstützt Mitarbeiter dabei, das deutsche Arbeitszeitgesetz (ArbZG) einzuhalten, Arbeitszeiten zu überwachen und drohende Verstöße zu erkennen. Sie wird in Python entwickelt, ist als ausführbare `.exe`-Datei oder Webapplikation für Windows 10/11 konzipiert und erfüllt die Anforderungen des 1. und 2. Semesters der DHBW. 

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
- **main**: Erfordert 2 Reviews, Status-Checks und keine direkten Pushes.
- **develop**: Erfordert 1 Review, Status-Checks  und keine direkten Pushes.


## Issues und Discussions

- **Issues**: Verwenden Sie Issues für die Planung von Aufgaben, Fehlerberichte und Feature-Vorschläge.
  - Erstellen Sie Issues mit klaren Titeln und Beschreibungen, z. B. „Implementierung der Ampellogik für Gleitzeit“.
  - Weisen Sie Issues Teammitgliedern zu und verknüpfen Sie sie mit Pull Requests.
- **Discussions**: Nutzen Sie Discussions für allgemeine Fragen, Brainstorming und Abstimmungen, z. B. zur Architektur oder zukünftigen Mobile-App-Features.
  - Beispiele: „Vorschlag für GUI-Framework: Tkinter vs. Flask“ oder „Diskussion über ArbZG-Validierungslogik“.


## Kontakt

Für Fragen wenden Sie sich an das Entwicklungsteam über GitHub Discussions oder kontaktieren Sie den Projektleiter Aurelia oder Stellvertrender Projektleiter Mika. Für technische Details oder Zugriffsanfragen wenden Sie sich an den Repository-Administrator Marvin.
