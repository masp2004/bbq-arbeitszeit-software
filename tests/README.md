# Test Suite

Diese vereinfachte Test-Suite konzentriert sich auf Kernbereiche der Geschäftslogik, die ohne eine vollständige SQLAlchemy-Installation überprüft werden können.

## Übersicht

### 1. Berechnungstests
- **`CalculateTime`**: Prüft die Berechnung der Arbeitszeit, die Behandlung von Tagen mit unterschiedlichen Daten und das automatische Abziehen gesetzlicher Pausen.

### 2. Benachrichtigungen
- **`Benachrichtigungen.create_fehlermeldung`**: Stellt sicher, dass Fehlermeldungen korrekt zusammengesetzt werden.

### 3. Passwortverwaltung
- **`ModellTrackTime.update_passwort`**: Validiert die Benutzerführung und die Fallback-Logik, wenn keine Datenbankverbindung vorhanden ist.

### 4. Ampelsystem
- **`ModellTrackTime.set_ampel_farbe`**: Überprüft die Zuordnung von Gleitzeitsaldo zu Ampel-Farben.

## Tests ausführen

```bash
pytest tests/
```

Die Tests erfordern keine SQLAlchemy-Installation. Notwendige Datenbankschnittstellen werden in den Tests simuliert.
