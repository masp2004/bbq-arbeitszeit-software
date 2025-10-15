# Test Suite

Diese Test-Suite stellt die Qualität und Funktionalität der Arbeitszeit-Erfassungssoftware sicher.

## Übersicht

Die Tests decken folgende Bereiche ab:

### 1. Model-Tests (`test_modell.py`)
- **Mitarbeiter (Employee) Model**: 
  - Erstellung von Mitarbeitern
  - Eindeutigkeit von Namen
  - Standard-Werte für Ampel-Schwellenwerte
  
- **Zeiteintrag (Time Entry) Model**:
  - Erstellung von Zeiteinträgen
  - Mehrere Einträge am selben Tag
  
- **Abwesenheit (Absence) Model**:
  - Erstellung von Abwesenheitseinträgen
  - Verschiedene Abwesenheitstypen (Urlaub, Krankheit, Fortbildung, Sonstiges)
  
- **Benachrichtigungen (Notifications) Model**:
  - Erstellung von Benachrichtigungen
  - Unique Constraints
  - Fehlermeldungen für verschiedene Codes
  
- **CalculateTime Klasse**:
  - Zeitberechnung für gleiche Tage
  - Gesetzliche Pausen (30 Min nach 6h, 45 Min nach 9h)
  
- **ModellLogin Klasse**:
  - Benutzerregistrierung
  - Login-Funktionalität
  - Passwort-Validierung
  
- **ModellTrackTime Klasse**:
  - Benutzerinformationen abrufen
  - Ampel-Status (grün/gelb/rot)
  - Passwort-Änderung
  - Stempel hinzufügen
  - Zeiteinträge abrufen
  - Durchschnittliche Gleitzeit berechnen

### 2. Erweiterte Model-Tests (`test_modell_advanced.py`)
- **Arbeitstage-Prüfung**:
  - Fehlende Arbeitstage erkennen
  - Urlaubstage berücksichtigen
  
- **Stempel-Prüfung**:
  - Ungerade Anzahl von Stempeln erkennen
  - Gerade Anzahl validieren
  
- **Ruhezeiten-Prüfung**:
  - Verstöße gegen 11-Stunden-Ruhezeit
  - Korrekte Ruhezeiten
  
- **Maximale Arbeitszeit**:
  - Überschreitung von 10 Stunden erkennen
  
- **Durchschnittliche Arbeitszeit**:
  - Überschreitung von 8 Stunden im 6-Monats-Durchschnitt
  
- **Gleitzeit-Berechnung**:
  - Berechnung und Validierung von Zeiteinträgen
  
- **Abwesenheits-Eintragung**:
  - Urlaub eintragen
  - Krankheit eintragen
  
- **Nachrichten**:
  - Benachrichtigungen abrufen
  
- **Manuelle Stempel**:
  - Nachträgliches Hinzufügen von Stempeln

## Tests ausführen

### Voraussetzungen
```bash
pip install -r requirements.txt
```

### Alle Tests ausführen
```bash
pytest tests/
```

### Tests mit ausführlicher Ausgabe
```bash
pytest tests/ -v
```

### Tests mit Coverage-Bericht
```bash
pytest tests/ --cov=modell --cov-report=term-missing
```

### Nur bestimmte Tests ausführen
```bash
# Nur Model-Tests
pytest tests/test_modell.py

# Nur erweiterte Tests
pytest tests/test_modell_advanced.py

# Nur eine bestimmte Test-Klasse
pytest tests/test_modell.py::TestMitarbeiter

# Nur einen bestimmten Test
pytest tests/test_modell.py::TestMitarbeiter::test_create_mitarbeiter
```

## Test-Coverage

Aktuelle Test-Coverage: **82%**

Die Tests decken die wichtigsten Funktionalitäten ab:
- Datenbank-Modelle und ihre Beziehungen
- Geschäftslogik für Zeiterfassung
- ArbZG-Compliance-Prüfungen
- Benutzer-Management
- Gleitzeit-Berechnung

## Bekannte Probleme

Ein Test ist derzeit übersprungen (`SKIPPED`):
- `test_checke_max_arbeitszeit_violation`: Aufgrund eines bekannten Problems im Original-Code (tage dictionary wird mit int statt timedelta initialisiert)

## Test-Struktur

```
tests/
├── __init__.py                # Test-Package
├── conftest.py                # Shared fixtures und Setup
├── test_modell.py             # Basis Model-Tests
└── test_modell_advanced.py    # Erweiterte funktionale Tests
```

## Fixtures

Die Tests verwenden folgende Fixtures (definiert in `conftest.py`):

- `test_engine`: In-Memory SQLite Datenbank für jeden Test
- `test_session`: SQLAlchemy Session für Datenbankoperationen
- `sample_mitarbeiter`: Beispiel-Mitarbeiter für Tests
- `sample_zeiteintrag`: Beispiel-Zeiteintrag für Tests

## Continuous Integration

Die Tests sollten in der CI/CD-Pipeline automatisch ausgeführt werden. Siehe `.github/workflows/ci.yml` für die Konfiguration.

## Best Practices

1. **Isolation**: Jeder Test läuft mit einer frischen In-Memory-Datenbank
2. **Mocking**: Die globale Session wird durch eine Test-Session ersetzt (monkeypatch)
3. **Aussagekräftige Namen**: Test-Namen beschreiben klar, was getestet wird
4. **Dokumentation**: Jeder Test hat einen Docstring
5. **Assertions**: Klare Assertions mit aussagekräftigen Fehlermeldungen

## Weiterentwicklung

Mögliche Erweiterungen:
- Integration Tests für Controller
- UI Tests für View-Komponenten
- Performance Tests
- End-to-End Tests
- API Tests (falls Web-App entwickelt wird)
