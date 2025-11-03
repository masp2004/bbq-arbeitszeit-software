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
    Erstellt für jeden Test eine isolierte In-Memory-Datenbank
    und lädt modell.py neu, um saubere SQLAlchemy-Mapper zu erzwingen.
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
    """Erzeugt einen Testnutzer mit gültigen Attributen."""
    user = modell.mitarbeiter(
        name="Testuser",
        password="1234",
        vertragliche_wochenstunden=40,
        geburtsdatum=date(1990, 1, 1),
        gleitzeit=0,
        letzter_login=date.today() - timedelta(days=5),
        ampel_grün=5,
        ampel_rot=-5,
    )
    isolated_db.add(user)
    isolated_db.commit()
    return user



@pytest.fixture
def model(test_user):
    """Initialisiert ein ModellTrackTime-Objekt mit aktivem Nutzer."""
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
    """Hilfsfunktion: fügt zwei Stempel (Start/Ende) hinzu."""
    s1 = modell.Zeiteintrag(mitarbeiter_id=mid, datum=tag, zeit=datetime.strptime(start, "%H:%M").time())
    s2 = modell.Zeiteintrag(mitarbeiter_id=mid, datum=tag, zeit=datetime.strptime(ende, "%H:%M").time())
    session.add_all([s1, s2])
    session.commit()

# ============================================================
#  TESTS: HISTORISCHE WOCHENSTUNDEN
# ============================================================

def test_wochenstunden_historie_verwendung(model, isolated_db, test_user):
    """Neuere Arbeitszeit darf ältere Tage nicht beeinflussen und wirkt nur ab Gültigkeitsdatum."""
    # Ausgangslage: 40h/Woche (8h täglich) bereits historisiert
    start_hist = date.today() - timedelta(days=30)
    isolated_db.add(
        modell.VertragswochenstundenHistorie(
            mitarbeiter_id=test_user.mitarbeiter_id,
            gueltig_ab=start_hist,
            wochenstunden=40,
        )
    )
    isolated_db.commit()

    change_date = date.today() - timedelta(days=1)
    result = model.aktualisiere_vertragliche_wochenstunden(30, gueltig_ab=change_date)
    assert result["neue_wochenstunden"] == 30

    # Nachträglicher Stempel für einen Tag VOR der Änderung → muss noch mit 8h Sollzeit laufen
    tag_alt = change_date - timedelta(days=1)
    add_stempel(isolated_db, test_user.mitarbeiter_id, tag_alt, "08:00", "16:30")

    # Stempel NACH der Änderung → soll die neue 6h-Sollzeit verwenden
    tag_neu = change_date + timedelta(days=1)
    add_stempel(isolated_db, test_user.mitarbeiter_id, tag_neu, "08:00", "16:30")

    model.berechne_gleitzeit()
    isolated_db.refresh(test_user)

    # Vor der Änderung: 8h gearbeitet -> 0h Gleitzeit; nach der Änderung: 8h gearbeitet -> +2h Gleitzeit
    assert test_user.gleitzeit == pytest.approx(2.0, abs=0.05)

    # Alle Stempel wurden validiert und Historie enthält beide Stände
    alle_stempel = isolated_db.query(modell.Zeiteintrag).filter_by(mitarbeiter_id=test_user.mitarbeiter_id).all()
    assert all(e.validiert for e in alle_stempel)

    historie = (
        isolated_db.query(modell.VertragswochenstundenHistorie)
        .filter_by(mitarbeiter_id=test_user.mitarbeiter_id)
        .order_by(modell.VertragswochenstundenHistorie.gueltig_ab)
        .all()
    )
    assert [h.wochenstunden for h in historie] == [40, 30]


# ============================================================
#  TESTS: STANDARDFUNKTIONEN
# ============================================================

def test_urlaub_verhindert_gleitzeitabzug(model, isolated_db, test_user):
    """
    Legt für alle Tage vom letzten_login bis gestern Urlaubseinträge an.
    checke_arbeitstage() darf dann keine Gleitzeit abziehen und keine Code-1-Benachrichtigungen erzeugen.
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


def test_benachrichtigung_bei_fehlendem_stempel(model, isolated_db, test_user):
    """Fehlende Arbeitstage sollen Benachrichtigungen (Code 1) erzeugen."""
    start_gz = test_user.gleitzeit
    model.checke_arbeitstage()
    isolated_db.refresh(test_user)

    ben = isolated_db.query(modell.Benachrichtigungen).filter_by(
        mitarbeiter_id=test_user.mitarbeiter_id, benachrichtigungs_code=1
    ).all()
    assert len(ben) >= 1
    assert test_user.gleitzeit < start_gz


def test_keine_doppelten_benachrichtigungen(model, isolated_db, test_user):
    """Zweiter Lauf darf keine neuen Benachrichtigungen erzeugen."""
    model.checke_arbeitstage()
    erste = isolated_db.query(modell.Benachrichtigungen).count()
    model.checke_arbeitstage()
    zweite = isolated_db.query(modell.Benachrichtigungen).count()
    assert erste == zweite


def test_benachrichtigung_fehlt_stempel(model, isolated_db, test_user):
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


def test_nachtraeglicher_stempel_an_gestempelten_tag(model, isolated_db, test_user):
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

def test_checke_ruhezeiten_verstoss(model, isolated_db, test_user):
    """<11 Stunden Ruhezeit → Benachrichtigung Code 3."""
    # sichere Werktage (Mittwoch + Donnerstag letzter Woche)
    heute = date.today()
    tag1 = heute - timedelta(days=(heute.weekday() + 5))  # Mittwoch letzte Woche
    tag2 = tag1 + timedelta(days=1)  # Donnerstag letzte Woche

    # Tag 1: Spätschicht, Tag 2: Frühschicht -> weniger als 11h Ruhe
    s1 = modell.Zeiteintrag(mitarbeiter_id=test_user.mitarbeiter_id, datum=tag1, zeit=time(14, 0))
    s2 = modell.Zeiteintrag(mitarbeiter_id=test_user.mitarbeiter_id, datum=tag1, zeit=time(22, 0))
    s3 = modell.Zeiteintrag(mitarbeiter_id=test_user.mitarbeiter_id, datum=tag2, zeit=time(6, 0))
    s4 = modell.Zeiteintrag(mitarbeiter_id=test_user.mitarbeiter_id, datum=tag2, zeit=time(14, 0))
    isolated_db.add_all([s1, s2, s3, s4])
    isolated_db.commit()

    model.checke_ruhezeiten()
    ben = isolated_db.query(modell.Benachrichtigungen).filter_by(
        mitarbeiter_id=test_user.mitarbeiter_id, benachrichtigungs_code=3
    ).first()
    assert ben is not None, "Ruhezeit-Verstoß wurde nicht erkannt"



def test_checke_durchschnittliche_arbeitszeit_zu_lang(model, isolated_db, test_user):
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


def test_checke_durchschnittliche_arbeitszeit_ok(model, isolated_db, test_user):
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

def test_arbeit_an_sonntag_erzeugt_benachrichtigung(model, isolated_db, test_user):
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


def test_arbeit_an_feiertag_erzeugt_benachrichtigung(model, isolated_db, test_user):
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


def test_arbeit_an_werktag_erzeugt_keine_sonntags_benachrichtigung(model, isolated_db, test_user):
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


# ============================================================
#  TESTS: ARBEITSFENSTER (22:00 - 06:00)
# ============================================================

def test_arbeitsfenster_und_ruhezeit_interaktion(model, isolated_db, test_user):
    """
    Prüft zwei Dinge:
    1. Arbeitszeit außerhalb von 06:00-22:00 wird NICHT zur Gleitzeit gezählt.
    2. Die Stempel werden TROTZDEM für die Ruhezeitprüfung verwendet.
    """
    # --- SETUP ---
    # Wähle zwei aufeinanderfolgende Werktage
    heute = date.today()
    tag1 = heute - timedelta(days=(heute.weekday() + 5))  # Mittwoch letzte Woche
    tag2 = tag1 + timedelta(days=1)                      # Donnerstag letzte Woche

    # Szenario:
    # Tag 1: Arbeit von 21:00 bis 23:00.
    #   - Erwartete Arbeitszeit für Gleitzeit: 1 Stunde (nur von 21-22 Uhr).
    # Tag 2: Arbeit von 07:00 bis 15:00.
    #   - Ruhezeit zwischen den Schichten: 8 Stunden (von 23:00 bis 07:00) -> VERSTOSS!
    s1 = modell.Zeiteintrag(mitarbeiter_id=test_user.mitarbeiter_id, datum=tag1, zeit=time(21, 0))
    s2 = modell.Zeiteintrag(mitarbeiter_id=test_user.mitarbeiter_id, datum=tag1, zeit=time(23, 0))
    s3 = modell.Zeiteintrag(mitarbeiter_id=test_user.mitarbeiter_id, datum=tag2, zeit=time(7, 0))
    s4 = modell.Zeiteintrag(mitarbeiter_id=test_user.mitarbeiter_id, datum=tag2, zeit=time(15, 30))
    isolated_db.add_all([s1, s2, s3, s4])
    isolated_db.commit()

    # --- TEIL 1: GLEITZEITBERECHNUNG PRÜFEN ---
    
    # Gleitzeit vor der Berechnung speichern
    gleitzeit_vorher = test_user.gleitzeit
    
    # Funktion ausführen
    model.berechne_gleitzeit()
    isolated_db.refresh(test_user)
 
    # Erwartung berechnen:
    # Tag 1: 1h Arbeit (statt 2h) - 8h Soll = -7h
    # Tag 2: 8,5h Arbeit - 0,5h Pause - 8h Soll = 0h
    # Total: -7h
    erwartete_aenderung = -7.0
    erwartete_gleitzeit = gleitzeit_vorher + erwartete_aenderung
    
    assert test_user.gleitzeit == pytest.approx(erwartete_gleitzeit), \
        "Die Gleitzeit wurde falsch berechnet. Zeit außerhalb des Arbeitsfensters wurde mitgezählt."

    # --- TEIL 2: RUHEZEITPRÜFUNG PRÜFEN ---

    # Funktion ausführen
    model.checke_ruhezeiten()

    # Prüfen, ob die Benachrichtigung (Code 3) für den Verstoß erstellt wurde
    ben = isolated_db.query(modell.Benachrichtigungen).filter_by(
        mitarbeiter_id=test_user.mitarbeiter_id,
        benachrichtigungs_code=3
    ).first()

    assert ben is not None, "Ruhezeitverstoß wurde nicht erkannt, obwohl Stempel außerhalb des Arbeitsfensters lagen."


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


