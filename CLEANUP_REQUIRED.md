# Git-Historie bereinigen - Anleitung

## Anfrage
Die 16 Commits (außer .gitignore und README.md vom Initial Commit) sollen aus der Historie gelöscht werden.

## Antwort
**Ja, das ist möglich**, erfordert aber Force-Push-Berechtigung auf das Repository.

## Aktueller Stand
- **Gesamt-Commits**: 16 Commits von Initial Commit (318ff07) bis zum letzten Merge (602b203)
- **Initial Commit** (318ff07) enthält:
  - `.gitignore` (Python Gitignore Template mit 207 Zeilen)
  - `README.md` (mit Inhalt "# Fallstudie")

## Was muss getan werden?

### Schritt 1: Repository auf Initial Commit zurücksetzen

```bash
# Main Branch auschecken
git checkout main

# Auf Initial Commit zurücksetzen (VORSICHT: Löscht alle Commits danach!)
git reset --hard 318ff07

# Force Push zum Remote Repository (benötigt Admin-Rechte)
git push --force origin main
```

### Schritt 2: Develop Branch ebenfalls zurücksetzen (falls vorhanden)

```bash
git checkout develop
git reset --hard 318ff07
git push --force origin develop
```

## Wichtige Hinweise

### ⚠️ Warnung
- **Diese Operation kann nicht rückgängig gemacht werden** (außer über Backups)
- **Alle Team-Mitglieder müssen benachrichtigt werden**
- **Branch Protection Rules müssen temporär deaktiviert werden**

### Vor der Durchführung
1. **Backup erstellen**:
   ```bash
   git branch backup-$(date +%Y%m%d)
   git push origin backup-$(date +%Y%m%d)
   ```

2. **Branch Protection Rules deaktivieren**:
   - Gehe zu: Repository Settings → Branches → Branch protection rules
   - Deaktiviere temporär die Rules für `main` und `develop`

3. **Team benachrichtigen**:
   - Alle offenen Pull Requests werden ungültig
   - Lokale Branches müssen neu erstellt werden
   - Alle Entwickler müssen ihren lokalen `main` Branch neu synchronisieren

### Nach der Durchführung

Alle Team-Mitglieder müssen folgende Schritte ausführen:

```bash
# Lokales Repository aktualisieren
git fetch origin

# Main Branch hart zurücksetzen
git checkout main
git reset --hard origin/main

# Optional: Alte Feature-Branches löschen (da sie auf alter Historie basieren)
git branch -D feature/alter-branch

# Branch Protection Rules wieder aktivieren
```

## Alternativen

### Option 1: Neues Repository erstellen
- Erstelle ein komplett neues Repository
- Kopiere nur .gitignore und README.md
- Archive das alte Repository
- **Vorteil**: Sauberster Schnitt, keine Force-Push Probleme
- **Nachteil**: Neue Repository-URL

### Option 2: Nur Dateien aufräumen (Historie behalten)
Falls das Löschen der Historie nicht zwingend erforderlich ist:
```bash
# Alle Dateien außer .gitignore und README.md löschen
# Und README.md auf ursprünglichen Inhalt zurücksetzen
git checkout main
git add .
git commit -m "Clean up repository, keep only .gitignore and README.md"
git push origin main
```
- **Vorteil**: Keine Force-Push erforderlich, Historie bleibt erhalten
- **Nachteil**: Alte Commits bleiben in der Historie sichtbar

## Was wird entfernt?

Folgende Commits werden aus der Historie gelöscht:
1. `90c83dc` - Enhance README with project details
2. `dfc70aa` - Add initial test.py file  
3. `c40e365` - Merge pull request #1
4. `e950735` - Simplify pull request process instructions
5. `6012483` - README.md aktualisieren
6. `ba2eb7f` - Remove test.py file
7. `9ed3c2f` - Merge pull request #2
8. `5192a22` - Add basic CI workflow
9. `1734fa8` - Merge pull request #4
10. `0ea7c18` - Initial plan
11. `a4b1a69` - Configure multi-language CI workflow
12. `b190437` - Merge pull request #6
13. `aada653` - Merge pull request #5
14. `bac0fae` - Delete .github/workflows directory
15. `602b203` - Merge pull request #17

## Was bleibt übrig?

Nach der Bereinigung enthält das Repository nur noch:
- **Ein Commit**: Initial commit (318ff07)
- **Zwei Dateien**: 
  - `.gitignore` (Python Template)
  - `README.md` (Inhalt: "# Fallstudie")

## Wer kann das durchführen?

Diese Operation erfordert:
- **Admin-Rechte** auf dem Repository
- **Force-Push-Berechtigung** für main und develop Branches  
- Oder: Temporäres Deaktivieren der Branch Protection Rules

→ **Kontakt**: Repository-Administrator Marvin (@masp2004)

## Nächste Schritte

1. Entscheidung treffen: Historie löschen oder Alternative wählen?
2. Team-Meeting: Alle Beteiligten informieren
3. Backup erstellen
4. Branch Protection Rules deaktivieren
5. Force Push durchführen
6. Branch Protection Rules reaktivieren
7. Team-Mitglieder über Synchronisierung informieren
