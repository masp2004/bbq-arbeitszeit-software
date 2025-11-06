"""
Test-Suite für ModellTrackTime (Minderjährige Mitarbeiter).

Dieses Modul testet die Geschäftslogik für Zeiterfassung und
Arbeitszeitschutz-Regelungen für minderjährige Mitarbeiter.

Haupttest-Bereiche:
- Historische Wochenstunden für Minderjährige
- Gleitzeit-Berechnung mit verschärften Pausenregelungen
- Arbeitszeitschutzgesetz-Validierung (Minderjährige):
  * 12h Ruhezeit zwischen Arbeitstagen
  * Max. 8h Arbeitszeit pro Tag
  * Max. 40h Arbeitszeit pro Woche
  * Max. 5 Arbeitstage pro Woche
  * Arbeitsfenster 6:00-20:00 Uhr
- Benachrichtigungssystem (Codes 7 und 8 für Minderjährige)
- Urlaubs- und Feiertagshandling

Test-Infrastruktur:
- Isolierte In-Memory-Datenbank pro Test
- Fixtures für minderjährigen Testbenutzer (17 Jahre)
- Modul-Reload für saubere SQLAlchemy-Mapper

Autor: Velqor
Version: 2.0
"""

import pytest
import importlib
from datetime import datetime, date, timedelta, time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import modell  # wichtig: Basisimport für reload


# ============================================================
#  FIXTURE: ISOLIERTE TESTDATENBANK
# ============================================================

@pytest.fixture(scope="function", autouse=True)
def isolated_db(monkeypatch):
    """
    Erstellt für jeden Test eine isolierte In-Memory-Datenbank.
    
    Lädt modell.py neu, um saubere SQLAlchemy-Mapper zu erzwingen
    und Cross-Test-Kontamination zu verhindern.
    
    Args:
        monkeypatch: Pytest fixture für Monkey-Patching
        
    Yields:
        Session: SQLAlchemy-Session für den Test
        
    Note:
        Wird automatisch vor jedem Test ausgeführt (autouse=True).
        Führt Rollback und Close nach jedem Test aus.
    """
    importlib.reload(modell)

    engine = create_engine("sqlite:///:memory:", echo=False)
    modell.Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    test_session = Session()

    # Globale Session in modell patchen
    monkeypatch.setattr(modell, "session", test_session)

    yield test_session

    test_session.rollback()
    test_session.close()

@pytest.fixture
def test_user(isolated_db):
    """
    Erzeugt einen minderjährigen Testnutzer (17 Jahre alt).
    
    Args:
        isolated_db: Test-Datenbank-Session
        
    Returns:
        mitarbeiter: Minderjähriger Testbenutzer
        
    Note:
        - Geburtsdatum: Heute vor 17 Jahren minus 10 Tage
        - Wochenstunden: 40h (maximal für Minderjährige)
        - Gleitzeit: 0h
        - Ampel: ±5h grün, ±5h rot
    """
    today = date.today()
    # Geburtsdatum so setzen, dass der Nutzer heute 17 ist
    birth_date = today.replace(year=today.year - 17) - timedelta(days=10)
    
    user = modell.mitarbeiter(
        name="MinorUser",
        password="1234",
        vertragliche_wochenstunden=40,
        geburtsdatum=birth_date,
        gleitzeit=0,
        letzter_login=date.today() - timedelta(days=30),
        ampel_grün=5,
        ampel_rot=-5,
    )
    isolated_db.add(user)
    isolated_db.commit()
    return user




@pytest.fixture
def model(test_user):
    """
    Initialisiert ein ModellTrackTime-Objekt mit aktivem minderjährigen Nutzer.
    
    Args:
        test_user: Minderjähriger Testbenutzer-Fixture
        
    Returns:
        ModellTrackTime: Konfigurierte Model-Instanz
        
    Note:
        Setzt alle relevanten Benutzer-Attribute im Model.
    """
    m = modell.ModellTrackTime()
    m.aktueller_nutzer_id = test_user.mitarbeiter_id
    m.aktueller_nutzer_vertragliche_wochenstunden = test_user.vertragliche_wochenstunden
    m.aktueller_nutzer_gleitzeit = test_user.gleitzeit
    m.aktueller_nutzer_ampel_rot = test_user.ampel_rot
    m.aktueller_nutzer_ampel_grün = test_user.ampel_grün
    return m


# ============================================================
#  HILFSFUNKTIONEN
# ============================================================

def add_stempel(session, mid, tag, start="08:00", ende="16:00"):
    """
    Hilfsfunktion zum Hinzufügen eines Ein-/Ausstempel-Paares.
    
    Args:
        session: SQLAlchemy-Session
        mid (int): Mitarbeiter-ID
        tag (date): Datum der Stempel
        start (str): Einstempel-Uhrzeit im Format "HH:MM"
        ende (str): Ausstempel-Uhrzeit im Format "HH:MM"
        
    Note:
        Committet die Stempel automatisch in die Datenbank.
    """
    s1 = modell.Zeiteintrag(mitarbeiter_id=mid, datum=tag, zeit=datetime.strptime(start, "%H:%M").time())
    s2 = modell.Zeiteintrag(mitarbeiter_id=mid, datum=tag, zeit=datetime.strptime(ende, "%H:%M").time())
    session.add_all([s1, s2])
    session.commit()


# ============================================================
#  TESTS: STANDARDFUNKTIONEN
# ============================================================

def test_urlaub_verhindert_gleitzeitabzug_minor(model, isolated_db, test_user):
    """
    Testet, dass Urlaubstage keinen Gleitzeit-Abzug verursachen.
    
    Legt für alle Tage vom letzten_login bis gestern Urlaubseinträge an.
    checke_arbeitstage() darf dann keine Gleitzeit abziehen und keine
    Code-1-Benachrichtigungen erzeugen.
    
    Validiert:
        - Urlaubstage zählen nicht als fehlende Arbeitstage
        - Keine Code-1-Benachrichtigungen bei Urlaub
        - Gleitzeit bleibt unverändert bei Urlaub
    """
    letzter_login = test_user.letzter_login
    gestern = date.today() - timedelta(days=1)

    # Erstelle für jeden Tag im Zeitraum (Mo–Fr relevant) einen genehmigten Urlaubseintrag
    tag = letzter_login
    inserted = []
    while tag <= gestern:
        if tag.weekday() < 5:  # nur Mo–Fr (Arbeitstage)
            abw = modell.Abwesenheit(
                mitarbeiter_id=test_user.mitarbeiter_id,
                datum=tag,
                typ="Urlaub",
                genehmigt=True
            )
            isolated_db.add(abw)
            inserted.append(tag)
        tag += timedelta(days=1)
    isolated_db.commit()

    alt_gleitzeit = test_user.gleitzeit
    model.checke_arbeitstage()
    isolated_db.refresh(test_user)

    # Gleitzeit darf unverändert bleiben
    assert test_user.gleitzeit == alt_gleitzeit, f"Gleitzeit wurde geändert (vorher={alt_gleitzeit}, jetzt={test_user.gleitzeit})"

    # Für alle eingefügten Tage darf es keine Code-1-Benachrichtigung geben
    for t in inserted:
        ben = isolated_db.query(modell.Benachrichtigungen).filter_by(
            mitarbeiter_id=test_user.mitarbeiter_id,
            benachrichtigungs_code=1,
            datum=t
        ).first()
        assert ben is None, f"Für {t} sollte keine Code-1-Benachrichtigung existieren"


def test_benachrichtigung_bei_fehlendem_stempel_minor(model, isolated_db, test_user):
    """Fehlende Arbeitstage sollen Benachrichtigungen (Code 1) erzeugen."""
    start_gz = test_user.gleitzeit
    model.checke_arbeitstage()
    isolated_db.refresh(test_user)

    ben = isolated_db.query(modell.Benachrichtigungen).filter_by(
        mitarbeiter_id=test_user.mitarbeiter_id, benachrichtigungs_code=1
    ).all()
    assert len(ben) >= 1
    assert test_user.gleitzeit < start_gz


def test_keine_doppelten_benachrichtigungen_minor(model, isolated_db, test_user):
    """Zweiter Lauf darf keine neuen Benachrichtigungen erzeugen."""
    model.checke_arbeitstage()
    erste = isolated_db.query(modell.Benachrichtigungen).count()
    model.checke_arbeitstage()
    zweite = isolated_db.query(modell.Benachrichtigungen).count()
    assert erste == zweite


def test_benachrichtigung_fehlt_stempel_minor(model, isolated_db, test_user):
    """Bei ungerader Stempelanzahl soll Code 2 entstehen."""
    tag = date.today() - timedelta(days=1)
    isolated_db.add(modell.Zeiteintrag(mitarbeiter_id=test_user.mitarbeiter_id, datum=tag, zeit=time(8, 0)))
    isolated_db.commit()

    fehlende = model.checke_stempel()
    assert tag in fehlende

    ben = isolated_db.query(modell.Benachrichtigungen).filter_by(
        mitarbeiter_id=test_user.mitarbeiter_id, benachrichtigungs_code=2
    ).first()
    assert ben is not None


def test_nachtraeglicher_stempel_an_gestempelten_tag_minor(model, isolated_db, test_user):
    """
    Testet, dass beim Nachtragen von Stempeln die Gleitzeit korrekt steigt.
    Voraussetzung: Es existiert bereits ein gültiger Zeiteintrag aus einem früheren Tag.
    """
    # Erste Einträge
    tag = date.today() - timedelta(days=2)
    s1 = modell.Zeiteintrag(mitarbeiter_id=test_user.mitarbeiter_id, datum=tag, zeit=time(8, 0))
    s2 = modell.Zeiteintrag(mitarbeiter_id=test_user.mitarbeiter_id, datum=tag, zeit=time(12, 0))
    isolated_db.add_all([s1, s2])
    isolated_db.commit()

    # Erster Gleitzeitlauf (verarbeitet existierende Stempel)
    model.berechne_gleitzeit()
    isolated_db.refresh(test_user)
    gleitzeit_nach_erster_berechnung = test_user.gleitzeit

    # Stempel werden nachgetragen
    s3 = modell.Zeiteintrag(mitarbeiter_id=test_user.mitarbeiter_id, datum=tag, zeit=time(13, 0))
    s4 = modell.Zeiteintrag(mitarbeiter_id=test_user.mitarbeiter_id, datum=tag, zeit=time(17, 0))
    isolated_db.add_all([s3, s4])
    isolated_db.commit()

    # Zweiter Gleitzeitlauf — sollte Gleitzeit korrekt erhöhen
    model.berechne_gleitzeit()
    isolated_db.refresh(test_user)

    assert test_user.gleitzeit > gleitzeit_nach_erster_berechnung, (
        f"Gleitzeit sollte nach dem Nachtragen steigen: "
        f"vorher={gleitzeit_nach_erster_berechnung}, jetzt={test_user.gleitzeit}"
    )

'''
def test_gleitzeit_an_urlaubstag_bleibt_gleich(model, isolated_db, test_user):
    """Urlaubstag soll bei Gleitzeitberechnung ignoriert werden."""
    urlaubstag = date.today() - timedelta(days=1)
    isolated_db.add(modell.Abwesenheit(
        mitarbeiter_id=test_user.mitarbeiter_id,
        datum=urlaubstag,
        typ="Urlaub",
        genehmigt=True,
    ))
    add_stempel(isolated_db, test_user.mitarbeiter_id, urlaubstag)
    isolated_db.commit()

    vor = test_user.gleitzeit
    model.berechne_gleitzeit()
    isolated_db.refresh(test_user)

    assert test_user.gleitzeit == vor
'''

# ============================================================
#  TESTS: RUHEZEITEN UND DURCHSCHNITTLICHE ARBEITSZEIT
# ============================================================




def test_checke_durchschnittliche_arbeitszeit_zu_lang_minor(model, isolated_db, test_user):
    """Durchschnittliche Arbeitszeit > 8h → Benachrichtigung Code 4."""
    start = date.today() - timedelta(days=10)
    for i in range(5):
        tag = start + timedelta(days=i)
        if tag.weekday() < 5:
            s1 = modell.Zeiteintrag(mitarbeiter_id=test_user.mitarbeiter_id, datum=tag, zeit=time(8, 0))
            s2 = modell.Zeiteintrag(mitarbeiter_id=test_user.mitarbeiter_id, datum=tag, zeit=time(17, 30))
            isolated_db.add_all([s1, s2])
    isolated_db.commit()

    model.checke_durchschnittliche_arbeitszeit()
    ben = isolated_db.query(modell.Benachrichtigungen).filter_by(
        mitarbeiter_id=test_user.mitarbeiter_id, benachrichtigungs_code=4
    ).first()
    assert ben is not None


def test_checke_durchschnittliche_arbeitszeit_ok_minor(model, isolated_db, test_user):
    """Durchschnitt ≤ 8h → keine Benachrichtigung."""
    start = date.today() - timedelta(days=10)
    for i in range(5):
        tag = start + timedelta(days=i)
        if tag.weekday() < 5:
            s1 = modell.Zeiteintrag(mitarbeiter_id=test_user.mitarbeiter_id, datum=tag, zeit=time(8, 0))
            s2 = modell.Zeiteintrag(mitarbeiter_id=test_user.mitarbeiter_id, datum=tag, zeit=time(15, 30))
            isolated_db.add_all([s1, s2])
    isolated_db.commit()

    model.checke_durchschnittliche_arbeitszeit()
    ben = isolated_db.query(modell.Benachrichtigungen).filter_by(
        mitarbeiter_id=test_user.mitarbeiter_id, benachrichtigungs_code=4
    ).first()
    assert ben is None


# ============================================================
#  TESTS: SONN- UND FEIERTAGE
# ============================================================

def test_arbeit_an_sonntag_erzeugt_benachrichtigung_minor(model, isolated_db, test_user):
    """Prüft, ob Arbeit an einem Sonntag eine Benachrichtigung (Code 6) erzeugt."""
    # Finde den letzten Sonntag
    heute = date.today()
    letzter_sonntag = heute - timedelta(days=(heute.weekday() + 1))

    # Stempel an diesem Sonntag hinzufügen
    add_stempel(isolated_db, test_user.mitarbeiter_id, letzter_sonntag)

    # Funktion ausführen
    model.checke_sonn_feiertage()

    # Prüfen, ob die Benachrichtigung erstellt wurde
    ben = isolated_db.query(modell.Benachrichtigungen).filter_by(
        mitarbeiter_id=test_user.mitarbeiter_id,
        benachrichtigungs_code=6,
        datum=letzter_sonntag
    ).first()

    assert ben is not None, "Für Arbeit an einem Sonntag wurde keine Benachrichtigung erstellt."


def test_arbeit_an_feiertag_erzeugt_benachrichtigung_minor(model, isolated_db, test_user):
    """Prüft, ob Arbeit an einem Feiertag eine Benachrichtigung (Code 6) erzeugt."""
    # Fester Feiertag (Tag der Deutschen Einheit) im letzten Jahr, um sicher im Zeitraum zu sein
    feiertag = date(date.today().year - 1, 10, 3)
    test_user.letzter_login = feiertag - timedelta(days=5)
    isolated_db.commit()

    # Stempel am Feiertag hinzufügen
    add_stempel(isolated_db, test_user.mitarbeiter_id, feiertag)

    # Funktion ausführen
    model.checke_sonn_feiertage()

    # Prüfen, ob die Benachrichtigung erstellt wurde
    ben = isolated_db.query(modell.Benachrichtigungen).filter_by(
        mitarbeiter_id=test_user.mitarbeiter_id,
        benachrichtigungs_code=6,
        datum=feiertag
    ).first()

    assert ben is not None, "Für Arbeit an einem Feiertag wurde keine Benachrichtigung erstellt."


def test_arbeit_an_werktag_erzeugt_keine_sonntags_benachrichtigung_minor(model, isolated_db, test_user):
    """Stellt sicher, dass an normalen Werktagen keine Code-6-Benachrichtigung erstellt wird."""
    # Finde den letzten Montag
    heute = date.today()
    letzter_montag = heute - timedelta(days=heute.weekday())

    # Stempel am Montag hinzufügen
    add_stempel(isolated_db, test_user.mitarbeiter_id, letzter_montag)

    # Funktion ausführen
    model.checke_sonn_feiertage()

    # Prüfen, dass KEINE Benachrichtigung erstellt wurde
    ben = isolated_db.query(modell.Benachrichtigungen).filter_by(
        mitarbeiter_id=test_user.mitarbeiter_id,
        benachrichtigungs_code=6
    ).first()

    assert ben is None, "Für Arbeit an einem normalen Werktag wurde fälschlicherweise eine Benachrichtigung erstellt."





def test_arbeitsfenster_edge_case(model, isolated_db, test_user):
    """
    Prüft zwei Dinge für steziellen fahl:
    1. Arbeitszeit außerhalb von 06:00-22:00 wird NICHT zur Gleitzeit gezählt.
    2. Die Stempel werden TROTZDEM für die Ruhezeitprüfung verwendet.
    """
    # --- SETUP ---
    # Wähle zwei aufeinanderfolgende Werktage
    heute = date.today()
    tag1 = heute - timedelta(days=(heute.weekday() + 5))  # Mittwoch letzte Woche
    tag2 = tag1 + timedelta(days=1)                      # Donnerstag letzte Woche

    # Szenario:
    # Tag 1: Arbeit von 3:00 bis 5:00.
    #   - Erwartete Arbeitszeit für Gleitzeit: 0 Stunden (alles außerhalb der Arbeitszeit).
 
    s1 = modell.Zeiteintrag(mitarbeiter_id=test_user.mitarbeiter_id, datum=tag1, zeit=time(3, 0))
    s2 = modell.Zeiteintrag(mitarbeiter_id=test_user.mitarbeiter_id, datum=tag1, zeit=time(5, 0))
  
    isolated_db.add_all([s1, s2])
    isolated_db.commit()

    # --- TEIL 1: GLEITZEITBERECHNUNG PRÜFEN ---
    
    # Gleitzeit vor der Berechnung speichern
    gleitzeit_vorher = test_user.gleitzeit
    
    # Funktion ausführen
    model.berechne_gleitzeit()
    isolated_db.refresh(test_user)
 
    # Erwartung berechnen:
    # Tag 1: 0h Arbeit (statt 2h) - 8h Soll = -8h
   
    erwartete_aenderung = -8.0
    erwartete_gleitzeit = gleitzeit_vorher + erwartete_aenderung
    
    assert test_user.gleitzeit == pytest.approx(erwartete_gleitzeit), \
        "Die Gleitzeit wurde falsch berechnet. Zeit außerhalb des Arbeitsfensters wurde mitgezählt."

    # --- TEIL 2:


    # Szenario:
    # Tag 2: Arbeit von 22:00 bis 23:30.
    #   - Erwartete Arbeitszeit für Gleitzeit: 0 Stunden (alles außerhalb der Arbeitszeit).
    s3 = modell.Zeiteintrag(mitarbeiter_id=test_user.mitarbeiter_id, datum=tag2, zeit=time(22, 0))
    s4 = modell.Zeiteintrag(mitarbeiter_id=test_user.mitarbeiter_id, datum=tag2, zeit=time(23, 30))

    isolated_db.add_all([s3, s4])
    isolated_db.commit()

    # Gleitzeit vor der Berechnung speichern
    gleitzeit_vorher = test_user.gleitzeit
    
    # Funktion ausführen
    model.berechne_gleitzeit()
    isolated_db.refresh(test_user)
 
    # Erwartung berechnen:
    # Tag 1: 0h Arbeit (statt 1,5h) - 8h Soll = -8h
   
    erwartete_aenderung = -8.0
    erwartete_gleitzeit = gleitzeit_vorher + erwartete_aenderung
    assert test_user.gleitzeit == pytest.approx(erwartete_gleitzeit), \
        "Die Gleitzeit wurde falsch berechnet. Zeit außerhalb des Arbeitsfensters wurde mitgezählt."



# ============================================================
#  TESTS: MINDERJÄHRIGE (MINORS)
# ============================================================

def test_minderjaehriger_pausen(model, isolated_db, test_user):

    tag = date.today() - timedelta(days=2)
    
    
    # Fall 1: > 4.5h -> 30min Pause
    add_stempel(isolated_db, test_user.mitarbeiter_id, tag, start="08:00", ende="13:00") # 5h Arbeit
    
    model.berechne_gleitzeit()
    isolated_db.refresh(test_user)
    
    # Erwartung: 5h Arbeit - 0.5h Pause - 8h Soll = -3.5h
    assert test_user.gleitzeit == pytest.approx(-3.5), "Falsche Pausenzeit bei >4.5h Arbeit für Minderjährige."

    # Reset für Fall 2
    test_user.gleitzeit = 0
    isolated_db.query(modell.Zeiteintrag).delete()
    isolated_db.commit()

    # Fall 2: > 6h -> 60min Pause
    add_stempel(isolated_db, test_user.mitarbeiter_id, tag, start="08:00", ende="15:00") # 7h Arbeit
    
    model.berechne_gleitzeit()
    isolated_db.refresh(test_user)

    # Erwartung: 7h Arbeit - 1h Pause - 8h Soll = -2h
    assert test_user.gleitzeit == pytest.approx(-2.0), "Falsche Pausenzeit bei >6h Arbeit für Minderjährige."


def test_minderjaehriger_arbeitsfenster(model, isolated_db, test_user):
    """Prüft das Arbeitsfenster für Minderjährige (06:00 - 20:00)."""

    tag = date.today() - timedelta(days=2)
    
    # Arbeit von 19:00 bis 21:00 -> nur 1h (19-20 Uhr) darf gezählt werden
    add_stempel(isolated_db, test_user.mitarbeiter_id, tag, start="19:00", ende="21:00")
    
    model.berechne_gleitzeit()
    isolated_db.refresh(test_user)

    # Erwartung: 1h Arbeit - 8h Soll = -7h
    assert test_user.gleitzeit == pytest.approx(-7.0), "Arbeitszeit außerhalb des 20:00-Fensters wurde für Minderjährige gezählt."


def test_minderjaehriger_ruhezeit(model, isolated_db, test_user):
    """Prüft die 12-Stunden-Ruhezeit für Minderjährige."""

    tag1 = date.today() - timedelta(days=3)
    tag2 = date.today() - timedelta(days=2)

    # Schichtende 20:00, Schichtbeginn 07:00 -> 11h Ruhezeit (Verstoß!)
    add_stempel(isolated_db, test_user.mitarbeiter_id, tag1, start="12:00", ende="20:00")
    add_stempel(isolated_db, test_user.mitarbeiter_id, tag2, start="07:00", ende="15:00")

    model.checke_ruhezeiten()
    
    ben = isolated_db.query(modell.Benachrichtigungen).filter_by(
        mitarbeiter_id=test_user.mitarbeiter_id, benachrichtigungs_code=3
    ).first()
    assert ben is not None, "Ruhezeitverstoß von <12h für Minderjährige wurde nicht erkannt."


def test_minderjaehriger_max_wochenstunden(model, isolated_db, test_user):
    """Prüft, ob >40h/Woche für Minderjährige eine Benachrichtigung (Code 7) erzeugt."""

    start_woche = date.today() - timedelta(days=10)
    start_woche -= timedelta(days=start_woche.weekday()) # Gehe zum Montag

    # 5 Tage x 9.5h -1h pause = 42.5h -> Verstoß
    for i in range(5):
        add_stempel(isolated_db, test_user.mitarbeiter_id, start_woche + timedelta(days=i), start="07:00", ende="16:30")

    model.checke_wochenstunden_minderjaehrige()

    ben = isolated_db.query(modell.Benachrichtigungen).filter_by(
        mitarbeiter_id=test_user.mitarbeiter_id, benachrichtigungs_code=7
    ).first()
    assert ben is not None, "Verstoß gegen 40h-Woche für Minderjährige wurde nicht erkannt."


def test_minderjaehriger_max_arbeitstage(model, isolated_db, test_user):
    """Prüft, ob >5 Arbeitstage/Woche für Minderjährige eine Benachrichtigung (Code 8) erzeugt."""

    start_woche = date.today() - timedelta(days=10)
    start_woche -= timedelta(days=start_woche.weekday()) # Gehe zum Montag

    # An 6 Tagen stempeln
    for i in range(6):
        add_stempel(isolated_db, test_user.mitarbeiter_id, start_woche + timedelta(days=i), start="09:00", ende="12:00")

    model.checke_arbeitstage_pro_woche_minderjaehrige()

    ben = isolated_db.query(modell.Benachrichtigungen).filter_by(
        mitarbeiter_id=test_user.mitarbeiter_id, benachrichtigungs_code=8
    ).first()
    assert ben is not None, "Verstoß gegen 5-Tage-Woche für Minderjährige wurde nicht erkannt."
