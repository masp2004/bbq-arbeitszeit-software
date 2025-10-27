"""
Modell-Modul für die BBQ Arbeitszeit-Erfassungssoftware.

Dieses Modul enthält alle Datenbank-Models und die Geschäftslogik der Anwendung.
Es verwaltet:

- Datenbankverbindung und SQLAlchemy-Session
- Datenbank-Models (mitarbeiter, Zeiteintrag, Abwesenheit, Benachrichtigungen)
- Geschäftslogik-Klassen (ModellTrackTime, ModellLogin, CalculateTime)
- ArbZG-Validierungsfunktionen (Ruhezeiten, Pausen, Arbeitszeiten)

Die Models folgen dem SQLAlchemy ORM-Pattern und verwenden eine SQLite-Datenbank.
"""

from sqlalchemy import Column, Integer, String, Date, create_engine, select, Time, Boolean, ForeignKey, UniqueConstraint, CheckConstraint
import sqlalchemy.orm as saorm
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from datetime import datetime, date, timedelta, time
import holidays 
import logging

# Logger für dieses Modul
logger = logging.getLogger(__name__)

try:
    # Datenbankverbindung aufbauen
    # SQLite-Datenbank wird im Programmverzeichnis erstellt
    engine = create_engine("sqlite:///system.db", echo=False) # echo=True ist im Prod-Betrieb zu "laut"
    Base = saorm.declarative_base()
    Session = saorm.sessionmaker(bind=engine)
    session = Session()
except SQLAlchemyError as e:
    logger.critical(f"Fehler beim Erstellen der DB-Engine oder Session: {e}", exc_info=True)
    # Wenn das passiert, kann die App nicht funktionieren.
    # In einer realen App würde man hier vielleicht beenden.
    # Für Kivy lassen wir es, der Controller fängt die Fehler ab.
    session = None

class mitarbeiter(Base):
    """
    SQLAlchemy Model für Mitarbeiter/Benutzer der Anwendung.
    
    Speichert alle relevanten Informationen eines Mitarbeiters einschließlich
    Vertragsdaten, Passwort, Gleitzeit und Ampel-Grenzwerten.
    
    Attributes:
        mitarbeiter_id (int): Eindeutige ID (Primary Key)
        name (str): Vor- und Nachname (unique, max 30 Zeichen)
        password (str): Passwort (max 15 Zeichen, unverschlüsselt)
        vertragliche_wochenstunden (int): Soll-Arbeitszeit pro Woche
        geburtsdatum (date): Geburtsdatum zur Überprüfung des Alters (Minderjährige)
        gleitzeit (int): Aktuelle kumulierte Gleitzeit in Stunden
        letzter_login (date): Datum des letzten Logins
        ampel_grün (int): Oberer Grenzwert für grüne Ampel (Gleitzeit)
        ampel_rot (int): Unterer Grenzwert für rote Ampel (Gleitzeit)
        vorgesetzter_id (int): Foreign Key zum Vorgesetzten (optional)
    """
    __tablename__ = "users"
    mitarbeiter_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(30), unique=True, nullable=False)
    password = Column(String(15), nullable=False)
    vertragliche_wochenstunden = Column(Integer, nullable=False)
    geburtsdatum = Column(Date, nullable=False)
    gleitzeit = Column(Integer, nullable=False, default=0)
    letzter_login = Column(Date, nullable=False)
    ampel_grün = Column(Integer, nullable=False, default=5)
    ampel_rot = Column(Integer, nullable=False, default=-5)
    vorgesetzter_id = Column(Integer, ForeignKey("users.mitarbeiter_id"))

    def is_minor_on_date(self, datum):
        """
        Prüft, ob der Mitarbeiter an einem bestimmten Datum minderjährig ist (unter 18).
        
        Wichtig für die Anwendung der speziellen Jugendarbeitsschutz-Regeln.
        
        Args:
            datum (date): Das zu prüfende Datum
            
        Returns:
            bool: True wenn Mitarbeiter an diesem Datum unter 18 Jahre alt ist, sonst False
        """
        # Input-Validierung
        if not self.geburtsdatum:
            logger.warning(f"is_minor_on_date für {self.name} ohne Geburtsdatum aufgerufen.")
            return False
        if not isinstance(datum, date):
            logger.error(f"is_minor_on_date erhielt ungültigen Datumstyp: {type(datum)}")
            try:
                # Versuch einer Notfall-Konvertierung
                datum = datetime.strptime(str(datum), "%Y-%m-%d").date()
            except ValueError:
                return False # Konnte nicht konvertiert werden
        
    
        age = datum.year - self.geburtsdatum.year - ((datum.month, datum.day) < (self.geburtsdatum.month, self.geburtsdatum.day))
        return age < 18


class Abwesenheit(Base):
    """
    SQLAlchemy Model für Abwesenheiten (Urlaub, Krankheit, etc.).
    
    Speichert Abwesenheiten eines Mitarbeiters, die bei der Gleitzeitberechnung
    berücksichtigt werden müssen.
    
    Attributes:
        id (int): Eindeutige ID (Primary Key)
        mitarbeiter_id (int): Foreign Key zum Mitarbeiter
        datum (date): Datum der Abwesenheit
        typ (str): Art der Abwesenheit ('Urlaub', 'Krankheit', 'Fortbildung', 'Sonstiges')
        genehmigt (bool): Ob die Abwesenheit genehmigt wurde (Default: False)
    """
    __tablename__ = "abwesenheiten"
    id = Column(Integer, primary_key=True, autoincrement=True)
    mitarbeiter_id = Column(Integer, ForeignKey("users.mitarbeiter_id"), nullable=False)
    datum = Column(Date, nullable=False)
    typ = Column(String, CheckConstraint("typ IN ('Urlaub', 'Krankheit', 'Fortbildung', 'Sonstiges')"), nullable=False)
    genehmigt = Column(Boolean, nullable=False, default=False)

class Zeiteintrag(Base):
    """
    SQLAlchemy Model für Zeitstempel (Ein-/Ausstempeln).
    
    Speichert einzelne Zeitstempel eines Mitarbeiters. Paarweise Einträge
    (Start-Ende) bilden eine Arbeitsperiode.
    
    Attributes:
        id (int): Eindeutige ID (Primary Key)
        mitarbeiter_id (int): Foreign Key zum Mitarbeiter
        zeit (time): Uhrzeit des Stempels
        datum (date): Datum des Stempels
        validiert (bool): Ob dieser Eintrag bereits für Gleitzeitberechnung verwendet wurde
    """
    __tablename__ = "zeiteinträge"
    id = Column(Integer, primary_key=True, autoincrement=True)
    mitarbeiter_id = Column(Integer, ForeignKey("users.mitarbeiter_id"), nullable=False)
    zeit = Column(Time, nullable=False)
    datum = Column(Date, nullable=False)
    validiert = Column(Boolean, nullable=False, default=False)

class Benachrichtigungen(Base):
    """
    SQLAlchemy Model für Benachrichtigungen/Warnungen an den Mitarbeiter.
    
    Speichert Warnungen über ArbZG-Verstöße, fehlende Stempel, etc.
    Benachrichtigungscodes definieren die Art der Warnung.
    
    Attributes:
        id (int): Eindeutige ID (Primary Key)
        mitarbeiter_id (int): Foreign Key zum Mitarbeiter
        benachrichtigungs_code (int): Code der Benachrichtigungsart (siehe CODES-Dict)
        datum (date): Datum, auf das sich die Benachrichtigung bezieht (optional)
        
    Class Attributes:
        CODES (dict): Mapping von Benachrichtigungscodes zu Textbausteinen
            Code 1: Fehlender Arbeitstag ohne Stempel
            Code 2: Ungerader Stempel (Start ohne Ende)
            Code 3: Ruhezeit-Verstoß
            Code 4: Durchschnittliche Arbeitszeit > 8h
            Code 5: Maximale Tagesarbeitszeit überschritten
            Code 6: Arbeit an Sonn-/Feiertag
            Code 7: Wochenstunden-Verstoß (Minderjährige)
            Code 8: Arbeitstage-Verstoß (Minderjährige)
    """
    __tablename__ = "benachrichtigungen"
    # ... (Spalten bleiben gleich) ...
    id = Column(Integer, primary_key=True, autoincrement=True)
    mitarbeiter_id = Column(Integer, ForeignKey("users.mitarbeiter_id"), nullable=False)
    benachrichtigungs_code = Column(Integer, nullable=False)
    datum = Column(Date)

    CODES = {
        1.1:"An den Tag",
        1.2:"wurde nicht gestempelt. Es wird für jeden Tag die Tägliche arbeitszeit der Gleitzeit abgezogen",
        2.1:"Am",
        2.2:"fehlt ein Stempel, bitte tragen sie diesen nach",
        3: ["Achtung, am", "wurden die gesetzlichen Ruhezeiten nicht eingehalten"],
        4: "Achtung, Ihre durchschnittliche tägliche Arbeitszeit der letzten 6 Monate hat 8 Stunden überschritten.",
        5:["Achung am", "wurde die maximale gesetzlich zulässsige Arbeitszeit überschritten."],
        6: ["Achtung, am", "wurde an einem Sonn- oder Feiertag gearbeitet."],
        7: ["In der Woche vom", "wurde die maximale Wochenarbeitszeit von 40 Stunden für Minderjährige überschritten."],
        8: ["In der Woche vom", "wurde an mehr als 5 Tagen gearbeitet, was für Minderjährige nicht zulässig ist."]
    }

    __table_args__ = (
        UniqueConstraint("mitarbeiter_id", "benachrichtigungs_code", "datum", name="uq_benachrichtigung_unique"),
    )

    def create_fehlermeldung(self):
        """
        Erstellt einen lesbaren Fehlertext aus dem Benachrichtigungs-Code.
        
        Verwendet das CODES-Dictionary und das gespeicherte Datum, um eine
        vollständige Benachrichtigungsmeldung zu generieren.
        
        Returns:
            str: Formatierte Fehlermeldung für den Benutzer
        """
        # Wandle Code in String um, um Suffix-Probleme (1.1 vs 1) zu vermeiden
        code_str = str(self.benachrichtigungs_code)

        try:
            if code_str == "1":
                return f"{self.CODES[1.1]} {self.datum} {self.CODES[1.2]}"
            elif code_str == "2":
                return f"{self.CODES[2.1]} {self.datum} {self.CODES[2.2]}"
            elif code_str == "3":
                return f"{self.CODES[3][0]} {self.datum} {self.CODES[3][1]}"
            elif code_str == "4":
                return self.CODES[4]
            elif code_str == "5":
                return f"{self.CODES[5][0]} {self.datum} {self.CODES[5][1]}"
            elif code_str == "6":
                return f"{self.CODES[6][0]} {self.datum} {self.CODES[6][1]}"
            elif code_str == "7":
                datum_str = self.datum.strftime('%d.%m.%Y') if self.datum else "[Datum fehlt]"
                return f"{self.CODES[7][0]} {datum_str} {self.CODES[7][1]}"
            elif code_str == "8":
                datum_str = self.datum.strftime('%d.%m.%Y') if self.datum else "[Datum fehlt]"
                return f"{self.CODES[8][0]} {datum_str} {self.CODES[8][1]}"
            else:
                # Unbekannten Code abfangen
                logger.warning(f"Unbekannter Benachrichtigungscode: {self.benachrichtigungs_code}")
                return f"Unbekannte Benachrichtigung (Code: {self.benachrichtigungs_code}) am {self.datum}"
        except KeyError as e:
            logger.error(f"Fehlender Schlüssel im CODES-Dict für Code {e}", exc_info=True)
            return f"Fehler bei Benachrichtigungserstellung (Code: {self.benachrichtigungs_code})"
        except (AttributeError, TypeError) as e:
            logger.error(f"Fehler beim Formatieren der Benachrichtigung {self.benachrichtigungs_code}: {e}", exc_info=True)
            return f"Fehlerhafte Benachrichtigung (Code: {self.benachrichtigungs_code})"


class CalculateTime():
    """
    Hilfsklasse zur Berechnung von Arbeitszeiten zwischen zwei Zeitstempeln.
    
    Diese Klasse berechnet die tatsächlich gearbeitete Zeit zwischen zwei Stempeln
    unter Berücksichtigung von:
    - Gesetzlichen Pausen (abhängig von Alter und Arbeitszeit)
    - Arbeitsfenster (06:00-22:00 für Erwachsene, 06:00-20:00 für Minderjährige)
    
    Wichtig: Instanzen werden nur erstellt, wenn beide Stempel am selben Tag sind.
    
    Attributes:
        nutzer (mitarbeiter): Der Mitarbeiter, für den die Zeit berechnet wird
        datum (date): Das Datum der Zeiteinträge
        startzeit (time): Startzeit des Arbeitszeitraums
        endzeit (time): Endzeit des Arbeitszeitraums
        start_dt (datetime): Kombiniertes Start-Datum/Zeit
        end_dt (datetime): Kombiniertes End-Datum/Zeit
        gearbeitete_zeit (timedelta): Berechnete Nettoarbeitszeit
    """
    def __new__(cls, eintrag1, eintrag2, nutzer):
        """
        Factory-Methode zum Erstellen einer CalculateTime-Instanz.
        
        Erstellt nur eine Instanz, wenn beide Einträge am selben Tag sind.
        
        Args:
            eintrag1 (Zeiteintrag): Erster Zeitstempel
            eintrag2 (Zeiteintrag): Zweiter Zeitstempel  
            nutzer (mitarbeiter): Mitarbeiter-Objekt
            
        Returns:
            CalculateTime oder None: Instanz nur wenn Datum übereinstimmt
        """
        if eintrag1.datum != eintrag2.datum:
            return None
        return super().__new__(cls)

    def __init__(self, eintrag1, eintrag2, nutzer):
        """
        Initialisiert die Zeitberechnung.
        
        Args:
            eintrag1 (Zeiteintrag): Erster Zeitstempel (sollte Start sein)
            eintrag2 (Zeiteintrag): Zweiter Zeitstempel (sollte Ende sein)
            nutzer (mitarbeiter): Mitarbeiter-Objekt für Pausenberechnung
        """
        self.nutzer = nutzer
        self.datum = eintrag1.datum
        self.startzeit = eintrag1.zeit
        self.endzeit = eintrag2.zeit

        try:
           self.start_dt = datetime.combine(self.datum, self.startzeit)
           self.end_dt = datetime.combine(self.datum, self.endzeit)
           
           # Sicherstellen, dass die Endzeit nach der Startzeit liegt
           if self.end_dt < self.start_dt:
               logger.warning(f"Endzeit {self.end_dt} liegt vor Startzeit {self.start_dt}. Zeit wird als 0 behandelt.")
               self.start_dt, self.end_dt = self.end_dt, self.start_dt # Zeiten tauschen? Oder 0?
               # Annahme: Es war ein Fehler, wir setzen die gearbeitete Zeit auf 0
               self.gearbeitete_zeit = timedelta()
           else:
                self.gearbeitete_zeit = self.end_dt - self.start_dt
        
        except (TypeError, ValueError) as e:
            logger.error(f"Fehler beim Kombinieren von Datum/Zeit: {e}", exc_info=True)
            self.gearbeitete_zeit = timedelta() # Standard-Fallback

    def gesetzliche_pausen_hinzufügen(self):
        """
        Zieht gesetzlich vorgeschriebene Pausen von der Arbeitszeit ab.
        
        Pausenregelung nach ArbZG und JArbSchG:
        
        Minderjährige:
        - > 4.5h: 30 Minuten Pause
        - > 6h: 60 Minuten Pause
        
        Erwachsene:
        - > 6h: 30 Minuten Pause
        - > 9h: 45 Minuten Pause
        """
       # Validierung
       if not self.nutzer:
           logger.error("gesetzliche_pausen_hinzufügen ohne 'nutzer' aufgerufen.")
           return
       
   
       if self.nutzer.is_minor_on_date(self.datum):
           if self.gearbeitete_zeit >= timedelta(hours=6):
               self.gearbeitete_zeit -= timedelta(minutes=60)
           elif self.gearbeitete_zeit >= timedelta(hours=4.5):
               self.gearbeitete_zeit -= timedelta(minutes=30)
       else:
           if self.gearbeitete_zeit >= timedelta(hours=9):
               self.gearbeitete_zeit -= timedelta(minutes=45)
           elif self.gearbeitete_zeit >= timedelta(hours=6):
               self.gearbeitete_zeit -= timedelta(minutes=30)


    def arbeitsfenster_beachten(self):
        """
        Entfernt Arbeitszeit außerhalb des erlaubten Arbeitsfensters.
        
        Arbeitsfenster nach ArbZG und JArbSchG:
        - Minderjährige: 06:00 - 20:00 Uhr
        - Erwachsene: 06:00 - 22:00 Uhr
        
        Zeit außerhalb dieser Fenster wird nicht zur Gleitzeit gezählt,
        aber die Stempel bleiben für Ruhezeit-Prüfungen relevant.
        """
       # Validierung
       if not self.nutzer:
           logger.error("arbeitsfenster_beachten ohne 'nutzer' aufgerufen.")
           return
       if not hasattr(self, 'start_dt') or not hasattr(self, 'end_dt'):
           logger.error("arbeitsfenster_beachten: start_dt/end_dt nicht initialisiert.")
           return


       is_minor = self.nutzer.is_minor_on_date(self.datum)
       nachtruhe_zeit = time(20, 0) if is_minor else time(22, 0)
       morgenruhe_ende = datetime.combine(self.datum, time(6, 0))
       nachtruhe_start = datetime.combine(self.datum, nachtruhe_zeit)

       abzuziehende_zeit = timedelta()

       # 1. Überschneidung mit der Morgenruhe (00:00 - 06:00)
       overlap_start_morgen = max(self.start_dt, datetime.combine(self.datum, time(0, 0)))
       overlap_end_morgen = min(self.end_dt, morgenruhe_ende)

       if overlap_end_morgen > overlap_start_morgen:
           abzuziehende_zeit += overlap_end_morgen - overlap_start_morgen

       # 2. Überschneidung mit der Nachtruhe (22:00/20:00 - 24:00)
       overlap_start_nacht = max(self.start_dt, nachtruhe_start)
       overlap_end_nacht = min(self.end_dt, datetime.combine(self.datum, time(23, 59, 59)))

       if overlap_end_nacht > overlap_start_nacht:
           abzuziehende_zeit += overlap_end_nacht - overlap_start_nacht
           
       self.gearbeitete_zeit -= abzuziehende_zeit
        



class ModellTrackTime():
    def __init__(self):
        self.aktueller_nutzer_id = None
        self.aktueller_nutzer_name = None
        self.aktueller_nutzer_vertragliche_wochenstunden = None
        self.aktueller_nutzer_gleitzeit = None
        self.aktueller_nutzer_ampel_rot = None
        self.aktueller_nutzer_ampel_grün = None

        self.nachtragen_datum = None
        self.manueller_stempel_uhrzeit = None
        self.neuer_abwesenheitseintrag_art = None

        self.zeiteinträge_bestimmtes_datum = None
        self.bestimmtes_datum = None

        self.kummulierte_gleitzeit_jahr = None
        self.kummulierte_gleitzeit_quartal = None
        self.kummulierte_gleitzeit_monat = None
        self.tage_ohne_stempel_beachten = None

        self.mitarbeiter = []
        self.aktuelle_kalendereinträge_für_id = None
        self.aktuelle_kalendereinträge_für_name = None



        self.neues_passwort = None
        self.neues_passwort_wiederholung = None

        self.ampel_status = None

    
     


        self.benachrichtigungen = []


        self.feedback_manueller_stempel = ""
        self.feedback_arbeitstage = ""
        self.feedback_stempel = ""
        self.feedback_neues_passwort = ""


    # === Hilfsfunktion für sichere DB-Operationen ===
    def _safe_db_operation(self, operation_func, *args, **kwargs):
        """
        Wrapper für DB-Operationen, um try/except/rollback zu kapseln.
        operation_func ist die Funktion, die die DB-Aktionen ausführt.
        """
        if not session:
            logger.critical("Keine DB-Session vorhanden. Operation abgebrochen.")
            return None # Oder False, je nach Kontext
            
        try:
            # Führe die eigentliche Operation aus
            result = operation_func(*args, **kwargs)
            # Änderungen committen, falls die Operation erfolgreich war
            session.commit()
            logger.debug(f"DB-Operation '{operation_func.__name__}' erfolgreich committed.")
            return result
        except IntegrityError as e:
            logger.warning(f"Integritätsfehler bei DB-Operation '{operation_func.__name__}': {e}")
            session.rollback()
            # Diese Fehler sind oft "normal" (z.B. doppelter Eintrag)
            return {"error": "IntegrityError", "details": str(e)}
        except SQLAlchemyError as e:
            # Alle anderen DB-Fehler
            logger.error(f"SQLAlchemy-Fehler bei DB-Operation '{operation_func.__name__}': {e}", exc_info=True)
            session.rollback()
            return {"error": "SQLAlchemyError", "details": str(e)}
        except Exception as e:
            # Alle anderen unerwarteten Fehler (z.B. Logikfehler)
            logger.critical(f"Unerwarteter Fehler bei DB-Operation '{operation_func.__name__}': {e}", exc_info=True)
            session.rollback()
            return {"error": "Exception", "details": str(e)}
    
    # ================================================

    
    def get_employees(self):
        if self.aktueller_nutzer_id is None: return
        if not session: return

        try:
            stmt = select(mitarbeiter.name).where(mitarbeiter.vorgesetzter_id == self.aktueller_nutzer_id)
            names = session.scalars(stmt).all()
            names.append(self.aktueller_nutzer_name)
            self.mitarbeiter = names
        except SQLAlchemyError as e:
            logger.error(f"Fehler beim Laden der Mitarbeiter: {e}", exc_info=True)
            self.mitarbeiter = [self.aktueller_nutzer_name] # Fallback

    def get_id(self):
        if not self.aktuelle_kalendereinträge_für_name:
            self.aktuelle_kalendereinträge_für_id = self.aktueller_nutzer_id
            return
        if not session: return

        try:
            stmt = select(mitarbeiter.mitarbeiter_id).where(mitarbeiter.name == self.aktuelle_kalendereinträge_für_name)
            employee_id = session.execute(stmt).scalar_one_or_none()

            if employee_id:
                self.aktuelle_kalendereinträge_für_id = employee_id
            else:
                logger.warning(f"Mitarbeiter '{self.aktuelle_kalendereinträge_für_name}' nicht gefunden, falle zurück auf aktuellen Nutzer.")
                self.aktuelle_kalendereinträge_für_id = self.aktueller_nutzer_id
        except SQLAlchemyError as e:
            logger.error(f"Fehler bei get_id für '{self.aktuelle_kalendereinträge_für_name}': {e}", exc_info=True)

    def get_zeiteinträge(self):
        if self.aktueller_nutzer_id is None or self.bestimmtes_datum is None:
            return
        if not session: return

        try:
            nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
            if not nutzer:
                logger.error(f"get_zeiteinträge: Nutzer {self.aktueller_nutzer_id} nicht gefunden.")
                return

            # Datum-Parsing validieren
            try:
                date_obj = datetime.strptime(self.bestimmtes_datum, "%d.%m.%Y").date()
            except ValueError as e:
                logger.error(f"Ungültiges Datumsformat in get_zeiteinträge: {self.bestimmtes_datum} - {e}")
                self.zeiteinträge_bestimmtes_datum = []
                return

            stmt = select(Zeiteintrag).where(
                    (Zeiteintrag.mitarbeiter_id == self.aktuelle_kalendereinträge_für_id) &
                    (Zeiteintrag.datum == date_obj)
                ).order_by(Zeiteintrag.datum, Zeiteintrag.zeit)
            
            einträge = session.scalars(stmt).all()
            
            einträge_mit_validierung = []
            for eintrag in einträge:
                is_unvalid = False
                stempelzeit = eintrag.zeit
                
                if nutzer.is_minor_on_date(date_obj):
                    if stempelzeit < time(6, 0) or stempelzeit > time(20, 0):
                        is_unvalid = True
                else:
                    # Original-Logik: is_unvalid = False. Das scheint ein Bug zu sein.
                    # Sollte es nicht 'is_unvalid = True' sein, wenn außerhalb 6-22 Uhr?
                    # Ich korrigiere das defensiv.
                    if stempelzeit < time(6, 0) or stempelzeit > time(22, 0):
                        is_unvalid = True # Korrigierte Logik
                
                einträge_mit_validierung.append([eintrag, is_unvalid])

            self.zeiteinträge_bestimmtes_datum = einträge_mit_validierung

        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in get_zeiteinträge: {e}", exc_info=True)
            self.zeiteinträge_bestimmtes_datum = []
        except Exception as e:
            logger.error(f"Unerwarteter Fehler in get_zeiteinträge: {e}", exc_info=True)
            self.zeiteinträge_bestimmtes_datum = []

    def get_user_info(self):
        if self.aktueller_nutzer_id is None: return
        if not session: return

        try:
            stmt = select(mitarbeiter).where(mitarbeiter.mitarbeiter_id == self.aktueller_nutzer_id)
            nutzer = session.execute(stmt).scalar_one_or_none()
            if nutzer:
                self.aktueller_nutzer_name = nutzer.name
                self.aktueller_nutzer_vertragliche_wochenstunden = nutzer.vertragliche_wochenstunden
                # Gleitzeit ist DECIMAL(4,2) in DB, aber Integer in Klasse?
                # Das ist ein potenzieller Bug. Ich caste zu float für Sicherheit.
                self.aktueller_nutzer_gleitzeit = float(nutzer.gleitzeit)
                self.aktueller_nutzer_ampel_rot = nutzer.ampel_rot
                self.aktueller_nutzer_ampel_grün = nutzer.ampel_grün
            else:
                logger.error(f"get_user_info: Nutzer {self.aktueller_nutzer_id} nicht gefunden.")
        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in get_user_info: {e}", exc_info=True)

    def set_ampel_farbe(self):
        try:
            # Sicherstellen, dass Werte nicht None sind
            gleitzeit = float(self.aktueller_nutzer_gleitzeit or 0)
            grün = float(self.aktueller_nutzer_ampel_grün or 5)
            rot = float(self.aktueller_nutzer_ampel_rot or -5)

            if gleitzeit >= grün:
                self.ampel_status = "green"
            elif rot < gleitzeit < grün:
                self.ampel_status = "yellow"
            else:
                self.ampel_status = "red"
        except (ValueError, TypeError) as e:
            logger.error(f"Fehler beim Setzen der Ampelfarbe (Werte: {self.aktueller_nutzer_gleitzeit}, {self.aktueller_nutzer_ampel_grün}, {self.aktueller_nutzer_ampel_rot}): {e}")
            self.ampel_status = "yellow" # Fallback

    def get_messages(self):
        if self.aktueller_nutzer_id is None: return
        if not session: return

        try:
            stmt = select(Benachrichtigungen).where(Benachrichtigungen.mitarbeiter_id == self.aktueller_nutzer_id)
            result = session.execute(stmt).scalars().all()
            self.benachrichtigungen = result
        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in get_messages: {e}", exc_info=True)
            self.benachrichtigungen = []

    def update_passwort(self):
        # Input-Validierung (ist schon gut)
        if not self.neues_passwort:
            self.feedback_neues_passwort = "Bitte gebe ein passwort ein"
            return
        # ... (andere Validierungen) ...
        if self.neues_passwort != self.neues_passwort_wiederholung:
            self.feedback_neues_passwort = "Die Passwörter müssen übereinstimmen"
            return

        # Gekapselte DB-Operation
        def _db_op():
            stmt = select(mitarbeiter).where(mitarbeiter.mitarbeiter_id == self.aktueller_nutzer_id)
            nutzer = session.execute(stmt).scalar_one_or_none()
            if nutzer:
                nutzer.password = self.neues_passwort
                return True # Erfolg signalisieren
            else:
                logger.error(f"update_passwort: Nutzer {self.aktueller_nutzer_id} nicht gefunden.")
                return False

        result = self._safe_db_operation(_db_op)

        if isinstance(result, dict) and "error" in result:
            self.feedback_neues_passwort = "Fehler beim Ändern des Passworts."
        elif result is True:
            self.feedback_neues_passwort = "Passwort erfolgreich geändert"
        else:
            self.feedback_neues_passwort = "Nutzer nicht gefunden."

    def stempel_hinzufügen(self):
        # Gekapselte DB-Operation
        def _db_op():
            stempel = Zeiteintrag(
                mitarbeiter_id = self.aktueller_nutzer_id,
                zeit = datetime.now().time(),
                datum = date.today()
            )
            session.add(stempel)
            return True # Erfolg
        
        self._safe_db_operation(_db_op)
        # Feedback wird im Controller gehandhabt

    def get_stamps_for_today(self):
        if not self.aktueller_nutzer_id: return []
        if not session: return []

        try:
            heute = date.today()
            stmt = select(Zeiteintrag).where(
                (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Zeiteintrag.datum == heute)
            ).order_by(Zeiteintrag.zeit)
            einträge = session.scalars(stmt).all()
            return einträge
        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in get_stamps_for_today: {e}", exc_info=True)
            return []

    def manueller_stempel_hinzufügen(self):
        try:
            # Input-Validierung (Zeit und Datum)
            stempel_zeit = datetime.strptime(self.manueller_stempel_uhrzeit, "%H:%M").time()
            stempel_datum = datetime.strptime(self.nachtragen_datum, "%d/%m/%Y").date()
        except (ValueError, TypeError) as e:
            logger.warning(f"Ungültiges Format für manuellen Stempel: {self.manueller_stempel_uhrzeit} / {self.nachtragen_datum} - {e}")
            self.feedback_manueller_stempel = "Ungültiges Datums- oder Zeitformat."
            return

        # Prüfen: Stempel liegt in der Zukunft?
        stempel_dt = datetime.combine(stempel_datum, stempel_zeit)
        if stempel_dt > datetime.now():
            self.feedback_manueller_stempel = "Stempel in der Zukunft ist nicht erlaubt."
            return

        # Prüfen: Abwesenheit (Urlaub/Krankheit) an diesem Datum?
        try:
            urlaubs_stmt = select(Abwesenheit).where(
                (Abwesenheit.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Abwesenheit.datum == stempel_datum)
            )
            exist_urlaub = session.execute(urlaubs_stmt).scalar_one_or_none()
            if exist_urlaub:
                self.feedback_manueller_stempel = "An diesem Tag ist bereits eine Abwesenheit eingetragen."
                return
        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler beim Prüfen von Abwesenheiten: {e}", exc_info=True)
            self.feedback_manueller_stempel = "Fehler beim Prüfen von Abwesenheiten."
            return

        # Prüfen: Identischer Stempel existiert bereits?
        try:
            dup_stmt = select(Zeiteintrag).where(
                (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Zeiteintrag.datum == stempel_datum) &
                (Zeiteintrag.zeit == stempel_zeit)
            )
            exists_dup = session.execute(dup_stmt).scalar_one_or_none()
            if exists_dup:
                self.feedback_manueller_stempel = "Ein identischer Stempel existiert bereits."
                return
        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler beim Prüfen auf Duplikate: {e}", exc_info=True)
            self.feedback_manueller_stempel = "Fehler beim Prüfen vorhandener Stempel."
            return

        # Gekapselte DB-Operation zum Hinzufügen
        def _db_op():
            stempel = Zeiteintrag(
                mitarbeiter_id = self.aktueller_nutzer_id,
                zeit = stempel_zeit,
                datum = stempel_datum
            )
            session.add(stempel)
            return True

        result = self._safe_db_operation(_db_op)

        if isinstance(result, dict) and "error" in result:
            self.feedback_manueller_stempel = "Fehler beim Speichern des Stempels."
        else:
            self.feedback_manueller_stempel = f"Stempel am {self.nachtragen_datum} um {self.manueller_stempel_uhrzeit} erfolgreich hinzugefügt"

    def urlaub_eintragen(self):
        if (self.nachtragen_datum is None) or (self.neuer_abwesenheitseintrag_art is None):
            return
        if self.neuer_abwesenheitseintrag_art not in ("Urlaub", "Krankheit"):
            logger.warning(f"Ungültiger Abwesenheitstyp: {self.neuer_abwesenheitseintrag_art}")
            return
            
        try:
            abwesenheit_datum = datetime.strptime(self.nachtragen_datum, "%d/%m/%Y").date()
        except (ValueError, TypeError) as e:
            logger.warning(f"Ungültiges Format für Abwesenheit: {self.nachtragen_datum} - {e}")
            # Feedback sollte im Controller gesetzt werden
            return

        # Gekapselte DB-Operation
        def _db_op():
            neue_abwesenheit = Abwesenheit(
                mitarbeiter_id = self.aktueller_nutzer_id,
                datum = abwesenheit_datum,
                typ = self.neuer_abwesenheitseintrag_art
            )
            session.add(neue_abwesenheit)
            return True

        self._safe_db_operation(_db_op)
        # Feedback sollte im Controller gesetzt werden

    # --- Alle 'checke_...' Methoden ---
    # Diese Methoden sind komplex und führen viele DB-Operationen aus.
    # Sie sollten alle in einen try-except-Block gehüllt werden,
    # um die Stabilität des Login-Prozesses zu gewährleisten.
    # Fehler bei der Benachrichtigungserstellung (z.B. IntegrityError)
    # werden bereits in _safe_db_operation behandelt.

    def _add_benachrichtigung_safe(self, code, datum):
        """Sicheres Hinzufügen einer Benachrichtigung, fängt IntegrityError ab."""
        def _db_op():
            benachrichtigung = Benachrichtigungen(
                mitarbeiter_id=self.aktueller_nutzer_id,
                benachrichtigungs_code=code,
                datum=datum
            )
            session.add(benachrichtigung)
            return True
        
        result = self._safe_db_operation(_db_op)
        if isinstance(result, dict) and result.get("error") == "IntegrityError":
            logger.debug(f"Benachrichtigung (Code {code}, Datum {datum}) existiert bereits. Übersprungen.")
        elif isinstance(result, dict):
            logger.error(f"Konnte Benachrichtigung (Code {code}) nicht hinzufügen: {result.get('details')}")

    def checke_wochenstunden_minderjaehrige(self):
        if self.aktueller_nutzer_id is None: return
        if not session: return

        try:
            nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
            if not nutzer or not nutzer.is_minor_on_date(datum=nutzer.letzter_login):
                return

            start_datum = nutzer.letzter_login
            end_datum = date.today() - timedelta(days=1)
            
            current_date = start_datum
            while current_date <= end_datum:
                start_of_week = current_date - timedelta(days=current_date.weekday())
                end_of_week = start_of_week + timedelta(days=6)

                if end_of_week > end_datum: break

                stmt = select(Zeiteintrag).where(
                    (Zeiteintrag.mitarbeiter_id == nutzer.mitarbeiter_id) &
                    (Zeiteintrag.datum.between(start_of_week, end_of_week))
                ).order_by(Zeiteintrag.datum, Zeiteintrag.zeit)
                einträge_woche = session.scalars(stmt).all()

                if not einträge_woche:
                    current_date = end_of_week + timedelta(days=1)
                    continue

                wochenstunden = timedelta()
                i = 0
                while i < len(einträge_woche) - 1:
                    calc = CalculateTime(einträge_woche[i], einträge_woche[i+1], nutzer)
                    if calc:
                        calc.gesetzliche_pausen_hinzufügen()
                        wochenstunden += calc.gearbeitete_zeit
                        i += 2
                    else:
                        i += 1
                
                if (wochenstunden > timedelta(hours=40) and nutzer.is_minor_on_date(datum=start_of_week)):
                    self._add_benachrichtigung_safe(code=7, datum=start_of_week)

                current_date = end_of_week + timedelta(days=1)
        
        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in checke_wochenstunden_minderjaehrige: {e}", exc_info=True)
            session.rollback() # Wichtig!



    def checke_arbeitstage_pro_woche_minderjaehrige(self):
        if self.aktueller_nutzer_id is None: return
        if not session: return

        try:
            nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
            if not nutzer or not nutzer.is_minor_on_date(nutzer.letzter_login):
                return

            start_datum = nutzer.letzter_login
            end_datum = date.today() - timedelta(days=1)

            current_date = start_datum
            while current_date <= end_datum:
                start_of_week = current_date - timedelta(days=current_date.weekday())
                end_of_week = start_of_week + timedelta(days=6)

                if not nutzer.is_minor_on_date(datum=start_of_week):
                    current_date = end_of_week + timedelta(days=1)
                    continue
                if end_of_week > end_datum:
                    break

                stmt = select(Zeiteintrag.datum).distinct().where(
                    (Zeiteintrag.mitarbeiter_id == nutzer.mitarbeiter_id) &
                    (Zeiteintrag.datum.between(start_of_week, end_of_week))
                )
                arbeitstage_count = len(session.scalars(stmt).all())

                if arbeitstage_count > 5:
                    self._add_benachrichtigung_safe(code=8, datum=start_of_week)

                current_date = end_of_week + timedelta(days=1)

        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in checke_arbeitstage_pro_woche_minderjaehrige: {e}", exc_info=True)
            session.rollback()



    def checke_arbeitstage(self):
        if self.aktueller_nutzer_id is None: return
        if not session: return

        try:
            nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
            if not nutzer:
                logger.error(f"checke_arbeitstage: Nutzer {self.aktueller_nutzer_id} nicht gefunden.")
                return

            letzter_login = nutzer.letzter_login
            gestern = date.today() - timedelta(days=1)

            fehlende_tage = []
            tag = letzter_login
            while tag <= gestern:
                if tag.weekday() < 5:  # Montag–Freitag
                    stmt = select(Zeiteintrag).where(
                        (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
                        (Zeiteintrag.datum == tag)
                    )
                    eintrag = session.execute(stmt).scalars().first()
                    if not eintrag:
                        fehlende_tage.append(tag)
                tag += timedelta(days=1)

            # Validierung der Division
            if not self.aktueller_nutzer_vertragliche_wochenstunden or self.aktueller_nutzer_vertragliche_wochenstunden < 0:
                logger.warning(f"checke_arbeitstage: Ungültige Wochenstunden ({self.aktueller_nutzer_vertragliche_wochenstunden}) für Nutzer {self.aktueller_nutzer_id}.")
                tägliche_arbeitszeit = timedelta(hours=8) # Fallback auf 8h
            else:
                tägliche_arbeitszeit = timedelta(hours=(self.aktueller_nutzer_vertragliche_wochenstunden / 5))

            abgezogene_tage = []
            for tag in fehlende_tage:
                # Prüfen auf Urlaub/Krankheit
                urlaubs_stmt = select(Abwesenheit).where(
                    (Abwesenheit.mitarbeiter_id == self.aktueller_nutzer_id) &
                    (Abwesenheit.datum == tag) 
                )
                exist_urlaub = session.execute(urlaubs_stmt).scalar_one_or_none()

                if not exist_urlaub:
                    # Gekapselte Operation für Gleitzeit-Update UND Benachrichtigung
                    def _db_op():
                        # Prüfen, ob Benachrichtigung schon existiert (Atomarität)
                        exists_stmt = select(Benachrichtigungen).where(
                            (Benachrichtigungen.mitarbeiter_id == self.aktueller_nutzer_id) &
                            (Benachrichtigungen.datum == tag) &
                            (Benachrichtigungen.benachrichtigungs_code == 1)
                        )
                        exists = session.execute(exists_stmt).scalar_one_or_none()
                        
                        if not exists:
                            # Gleitzeit abziehen
                            neue_gleitzeit = float(self.aktueller_nutzer_gleitzeit) - (tägliche_arbeitszeit.total_seconds() / 3600)
                            nutzer.gleitzeit = neue_gleitzeit # Aktualisiert das Objekt in der Session
                            self.aktueller_nutzer_gleitzeit = neue_gleitzeit # Aktualisiert den lokalen Cache

                            # Benachrichtigung erstellen
                            benachrichtigung = Benachrichtigungen(
                                mitarbeiter_id=self.aktueller_nutzer_id,
                                benachrichtigungs_code=1,
                                datum=tag
                            )
                            session.add(benachrichtigung)
                            abgezogene_tage.append(tag)
                        return True

                    self._safe_db_operation(_db_op)
            
            return fehlende_tage
        
        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in checke_arbeitstage: {e}", exc_info=True)
            session.rollback()


    def checke_stempel(self):
        if self.aktueller_nutzer_id is None: return
        if not session: return

        try:
            nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
            if not nutzer: return

            letzter_login = nutzer.letzter_login
            gestern = date.today() - timedelta(days=1)

            ungerade_tage = []
            tag = letzter_login
            while tag <= gestern:
                if tag.weekday() < 5:  
                    stmt = select(Zeiteintrag).where(
                        (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
                        (Zeiteintrag.datum == tag)
                    )
                    stempel_anzahl = len(session.execute(stmt).scalars().all())
                    if stempel_anzahl % 2 != 0:
                        ungerade_tage.append(tag)
                tag += timedelta(days=1)

            self.feedback_stempel = f"An den Tagen {ungerade_tage} fehlt ein Stempel, bitte tragen sie diesen nach"

            for tag in ungerade_tage:
                self._add_benachrichtigung_safe(code=2, datum=tag)

            return ungerade_tage
        
        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in checke_stempel: {e}", exc_info=True)
            session.rollback()


    
    def checke_sonn_feiertage(self):
        if self.aktueller_nutzer_id is None: return
        if not session: return

        try:
            nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
            if not nutzer or not nutzer.letzter_login:
                return

            start_datum = nutzer.letzter_login
            end_datum = date.today() - timedelta(days=1)
            
            # Edge Case: Start- und Endjahr könnten weit auseinander liegen
            if start_datum.year > end_datum.year:
                 logger.warning("checke_sonn_feiertage: Startdatum liegt nach Enddatum.")
                 return
            
            jahre = set(range(start_datum.year, end_datum.year + 1))
            
            # holidays-Bibliothek könnte fehlschlagen (z.B. unbekanntes Land)
            try:
                de_holidays = holidays.Germany(years=list(jahre))
            except Exception as he:
                logger.error(f"Fehler beim Laden der Feiertage: {he}", exc_info=True)
                de_holidays = {} # Leeres Dict als Fallback

            stmt = select(Zeiteintrag.datum).distinct().where(
                (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Zeiteintrag.datum.between(start_datum, end_datum))
            )
            gestempelte_tage = session.scalars(stmt).all()

            for tag in gestempelte_tage:
                if tag.weekday() == 6 or tag in de_holidays:
                    self._add_benachrichtigung_safe(code=6, datum=tag)

        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in checke_sonn_feiertage: {e}", exc_info=True)
            session.rollback()

    
    def checke_ruhezeiten(self):
        if self.aktueller_nutzer_id is None: return
        if not session: return

        try:
            heute = date.today()
            gestern = heute - timedelta(days=1)

            nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
            if not nutzer:
                logger.error(f"checke_ruhezeiten: Nutzer {self.aktueller_nutzer_id} nicht gefunden.")
                return

            stmt = select(Zeiteintrag).where(
                (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Zeiteintrag.datum <= gestern)
            ).order_by(Zeiteintrag.datum, Zeiteintrag.zeit)
            einträge = session.scalars(stmt).all()

            if not einträge:
                return

            tage = {}
            for e in einträge:
                if e.datum not in tage:
                    tage[e.datum] = []
                tage[e.datum].append(e.zeit)

            sortierte_tage = sorted(tage.keys())
            verletzungen = []

            for i in range(len(sortierte_tage) - 1):
                tag_heute = sortierte_tage[i]
                tag_morgen = sortierte_tage[i + 1]

                if tag_morgen > gestern:
                    break

                # Original-Logik: überspringt Wochenenden. Ist das korrekt?
                # Ja, Ruhezeit zwischen Fr und Mo ist irrelevant.
                if tag_heute.weekday() >= 5 or tag_morgen.weekday() >= 5:
                    continue
                
                # Ruhezeit-Anforderung basierend auf dem *ersten* Tag (tag_heute)
                erforderliche_ruhezeit = timedelta(hours=12) if nutzer.is_minor_on_date(datum=tag_heute) else timedelta(hours=11)

                ende_heute = max(tage[tag_heute])
                beginn_morgen = min(tage[tag_morgen])

                ende_dt = datetime.combine(tag_heute, ende_heute)
                beginn_dt = datetime.combine(tag_morgen, beginn_morgen)
                differenz = beginn_dt - ende_dt

                if differenz < erforderliche_ruhezeit:
                    self._add_benachrichtigung_safe(code=3, datum=tag_morgen)
                    verletzungen.append((tag_heute, tag_morgen, differenz))
        
        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in checke_ruhezeiten: {e}", exc_info=True)
            session.rollback()


    def checke_durchschnittliche_arbeitszeit(self):
        if self.aktueller_nutzer_id is None: return
        if not session: return

        try:
            nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
            if not nutzer: return

            end_datum = date.today() - timedelta(days=1)
            start_datum = end_datum - timedelta(weeks=24)

            stmt = select(Zeiteintrag).where(
                (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Zeiteintrag.datum.between(start_datum, end_datum))
            ).order_by(Zeiteintrag.datum, Zeiteintrag.zeit)
            
            einträge = session.scalars(stmt).all()
            if not einträge: return

            arbeitstage = {}
            i = 0
            while i < len(einträge) - 1:
                calc = CalculateTime(einträge[i], einträge[i + 1], nutzer)
                if calc:
                    calc.gesetzliche_pausen_hinzufügen()
                    arbeitstage.setdefault(calc.datum, timedelta())
                    arbeitstage[calc.datum] += calc.gearbeitete_zeit
                    i += 2
                else:
                    i += 1
            
            if not arbeitstage: return

            gesamte_arbeitszeit = sum(arbeitstage.values(), timedelta())
            anzahl_arbeitstage = len(arbeitstage)
            
            # Division durch Null abfangen
            if anzahl_arbeitstage == 0:
                logger.debug("checke_durchschnittliche_arbeitszeit: Keine Arbeitstage gefunden.")
                return

            durchschnittliche_arbeitszeit = gesamte_arbeitszeit / anzahl_arbeitstage

            if durchschnittliche_arbeitszeit > timedelta(hours=8):
                self._add_benachrichtigung_safe(code=4, datum=date.today())

        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in checke_durchschnittliche_arbeitszeit: {e}", exc_info=True)
            session.rollback()
        except ZeroDivisionError:
             logger.warning("checke_durchschnittliche_arbeitszeit: Division durch Null (sollte nicht passieren).")
 

    def checke_max_arbeitszeit(self):
        if self.aktueller_nutzer_id is None: return
        if not session: return

        try:
            nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
            if not nutzer: return
            
            # Nur unvalidierte Einträge bis gestern holen
            stmt = select(Zeiteintrag).where(
                (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Zeiteintrag.validiert == 0) &
                (Zeiteintrag.datum <= date.today() - timedelta(days=1))
            ).order_by(Zeiteintrag.datum, Zeiteintrag.zeit)
            einträge = session.scalars(stmt).all()

            tage = {}
            for daten in einträge:
                tage.setdefault(daten.datum, timedelta()) # Initialisiert mit timedelta()

            # Zeitberechnung
            i = 0
            while i < len(einträge) - 1:
                calc = CalculateTime(einträge[i], einträge[i+1], nutzer)
                if calc:
                    # Sicherstellen, dass das Datum im 'tage'-Dict ist (sollte es sein)
                    if calc.datum in tage:
                        calc.gesetzliche_pausen_hinzufügen()
                        tage[calc.datum] += calc.gearbeitete_zeit
                    i += 2  
                else:
                    i += 1

            # Prüfung
            for datum, arbeitszeit in tage.items():
                if not isinstance(arbeitszeit, timedelta): continue # Sicherheitsscheck
                
                max_stunden = timedelta(hours=8) if nutzer.is_minor_on_date(datum=datum) else timedelta(hours=10)
                if arbeitszeit > max_stunden:
                    self._add_benachrichtigung_safe(code=5, datum=datum)

        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in checke_max_arbeitszeit: {e}", exc_info=True)
            session.rollback()



    def berechne_gleitzeit(self):
        if self.aktueller_nutzer_id is None: return
        if not session: return

        try:
            nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
            if not nutzer: return

            stmt = select(Zeiteintrag).where(
                (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Zeiteintrag.validiert == 0) &
                (Zeiteintrag.datum <= date.today() - timedelta(days=1))
            ).order_by(Zeiteintrag.datum, Zeiteintrag.zeit)
            einträge = session.scalars(stmt).all()
            
            logger.debug("Unvalidierte Einträge zur Gleitzeitberechnung:")
            for e in einträge:
                logger.debug(f"  {e.datum} {e.zeit}")
    
            arbeitstage ={}
            benutzte_einträge = [] 
            
            i = 0
            while i < len(einträge) - 1:
                calc = CalculateTime(einträge[i], einträge[i+1], nutzer)
                if calc:
                    calc.gesetzliche_pausen_hinzufügen()
                    calc.arbeitsfenster_beachten()
                    
                    arbeitstage.setdefault(calc.datum, timedelta())
                    arbeitstage[calc.datum] += calc.gearbeitete_zeit

                    benutzte_einträge.append(einträge[i])
                    benutzte_einträge.append(einträge[i+1])
                    i += 2  
                else:
                    i += 1  

            # Validierung der Division
            if not self.aktueller_nutzer_vertragliche_wochenstunden or self.aktueller_nutzer_vertragliche_wochenstunden <= 0:
                 logger.error(f"berechne_gleitzeit: Ungültige Wochenstunden ({self.aktueller_nutzer_vertragliche_wochenstunden}) für Nutzer {self.aktueller_nutzer_id}.")
                 return # Berechnung abbrechen
            
            tägliche_arbeitszeit = timedelta(hours=(self.aktueller_nutzer_vertragliche_wochenstunden / 5))

            gleitzeit_diff_total = timedelta()

            for datum, arbeitszeit in arbeitstage.items():
                # Prüfen, ob für den Tag eine "Fehlstempel"-Benachrichtigung (Code 1) existiert
                exists_stmt = select(Benachrichtigungen).where(
                    (Benachrichtigungen.mitarbeiter_id == self.aktueller_nutzer_id) &
                    (Benachrichtigungen.datum == datum) &
                    (Benachrichtigungen.benachrichtigungs_code == 1)
                )
                exists = session.execute(exists_stmt).scalar_one_or_none()
                
                # Hier ist ein Bug in der Original-Logik:
                # 'unvalidierte' prüft auf 'validiert == 1', aber wir verarbeiten 'validiert == 0'.
                # Die Prüfung 'if (not exists) and (not unvalidierte):' ist sinnlos.
                # Ich nehme an, die Prüfung auf 'exists' (Code 1) ist die relevante.
            
                if not exists: 
                    # Nur Tage berechnen, für die *nicht* schon Gleitzeit abgezogen wurde
                    differenz = arbeitszeit - tägliche_arbeitszeit
                    gleitzeit_diff_total += differenz
                else:
                    logger.debug(f"Gleitzeit für {datum} übersprungen (Code 1 Benachrichtigung existiert).")
            
            # Alle benutzten Einträge als validiert markieren
            for e in benutzte_einträge:
                e.validiert = True
            
            # Gleitzeit-Update
            gleitzeit_stunden = float(gleitzeit_diff_total.total_seconds() / 3600)
            neue_gleitzeit = float(self.aktueller_nutzer_gleitzeit or 0) + gleitzeit_stunden
            
            self.aktueller_nutzer_gleitzeit = neue_gleitzeit
            nutzer.gleitzeit = neue_gleitzeit
            
            session.commit() # Commit der validierten Einträge und der neuen Gleitzeit
            logger.info(f"Gleitzeit für Nutzer {self.aktueller_nutzer_id} berechnet. {gleitzeit_stunden}h hinzugefügt. Neu: {neue_gleitzeit}h.")

        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in berechne_gleitzeit: {e}", exc_info=True)
            session.rollback()
        except Exception as e:
            logger.error(f"Allg. Fehler in berechne_gleitzeit: {e}", exc_info=True)
            session.rollback() # Sicherstellen, dass auch bei Logikfehlern gerolltbackt wird


    def berechne_durchschnittliche_gleitzeit(self, start_datum: date, end_datum: date, include_missing_days: bool = False):
        if self.aktueller_nutzer_id is None:
            return {"error": "Kein Nutzer angemeldet"}
        if not session:
            return {"error": "Keine DB-Session"}
        if start_datum > end_datum:
            logger.warning(f"berechne_durchschnittliche_gleitzeit: Startdatum {start_datum} liegt nach Enddatum {end_datum}.")
            return {"error": "Startdatum liegt nach Enddatum"}

        try:
            nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
            if not nutzer:
                return {"error": "Nutzer nicht gefunden"}

            # Validierung der Division
            if not self.aktueller_nutzer_vertragliche_wochenstunden or self.aktueller_nutzer_vertragliche_wochenstunden <= 0:
                 logger.error(f"berechne_durchschnittliche_gleitzeit: Ungültige Wochenstunden ({self.aktueller_nutzer_vertragliche_wochenstunden}).")
                 return {"error": "Ungültige Wochenstunden"}
            
            tägliche_arbeitszeit = timedelta(hours=(self.aktueller_nutzer_vertragliche_wochenstunden / 5))

            stmt = select(Zeiteintrag).where(
                (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Zeiteintrag.datum.between(start_datum, end_datum))
            ).order_by(Zeiteintrag.datum, Zeiteintrag.zeit)

            einträge = session.scalars(stmt).all()

            arbeitstage = {}
            if einträge: # Nur berechnen, wenn Einträge vorhanden sind
                i = 0
                while i < len(einträge) - 1:
                    calc = CalculateTime(einträge[i], einträge[i + 1], nutzer)
                    if calc:
                        calc.gesetzliche_pausen_hinzufügen()
                        arbeitstage.setdefault(calc.datum, timedelta())
                        arbeitstage[calc.datum] += calc.gearbeitete_zeit
                        i += 2
                    else:
                        i += 1

            # Alle Tage im Bereich (nur Mo–Fr)
            alle_tage = [start_datum + timedelta(days=i) for i in range((end_datum - start_datum).days + 1)]
            arbeitstage_werktage = [t for t in alle_tage if t.weekday() < 5]

            gleitzeit_differenzen = []
            berücksichtigte_tage = []

            for tag in arbeitstage_werktage:
                if tag in arbeitstage:
                    differenz = arbeitstage[tag] - tägliche_arbeitszeit
                    gleitzeit_differenzen.append(differenz)
                    berücksichtigte_tage.append(tag)
                elif include_missing_days:
                    differenz = -tägliche_arbeitszeit
                    gleitzeit_differenzen.append(differenz)
                    berücksichtigte_tage.append(tag)
                
            if not gleitzeit_differenzen:
                return {"durchschnitt_gleitzeit_stunden": 0.0, "anzahl_tage": 0, "berücksichtigte_tage": []}

            # Division durch Null ist hier (len(gleitzeit_differenzen)) abgefangen
            gesamt_gleitzeit = sum(gleitzeit_differenzen, timedelta())
            durchschnitt = gesamt_gleitzeit / len(gleitzeit_differenzen)
            durchschnitt_stunden = round(durchschnitt.total_seconds() / 3600, 2)

            return {
                "durchschnitt_gleitzeit_stunden": durchschnitt_stunden,
                "anzahl_tage": len(gleitzeit_differenzen),
                "berücksichtigte_tage": berücksichtigte_tage
            }

        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in berechne_durchschnittliche_gleitzeit: {e}", exc_info=True)
            session.rollback()
            return {"error": "DB-Fehler"}
        except ZeroDivisionError:
             logger.error("berechne_durchschnittliche_gleitzeit: Division durch Null (sollte abgefangen sein).")
             return {"durchschnitt_gleitzeit_stunden": 0.0, "anzahl_tage": 0, "berücksichtigte_tage": []}


    
    def kummuliere_gleitzeit(self):
        if self.aktueller_nutzer_id is None:
            self.kummulierte_gleitzeit_monat = 0.0
            self.kummulierte_gleitzeit_quartal = 0.0
            self.kummulierte_gleitzeit_jahr = 0.0
            return

        heute = date.today()
        include_missing = bool(self.tage_ohne_stempel_beachten)

        # 1. Monat berechnen

        start_monat = heute.replace(day=1)
        ergebnis_monat = self.berechne_durchschnittliche_gleitzeit(start_monat, heute, include_missing)
        if "error" not in ergebnis_monat:
            self.kummulierte_gleitzeit_monat = round(ergebnis_monat["durchschnitt_gleitzeit_stunden"], 2)
        else:
            logger.warning(f"Fehler bei Kummulation (Monat): {ergebnis_monat.get('error')}")
            self.kummulierte_gleitzeit_monat = 0.0


        # 2. Quartal berechnen

        aktuelles_quartal = (heute.month - 1) // 3 + 1
        start_monat_quartal = (aktuelles_quartal - 1) * 3 + 1
        start_quartal = heute.replace(month=start_monat_quartal, day=1)
        ergebnis_quartal = self.berechne_durchschnittliche_gleitzeit(start_quartal, heute, include_missing)
        if "error" not in ergebnis_quartal:
            self.kummulierte_gleitzeit_quartal = round(ergebnis_quartal["durchschnitt_gleitzeit_stunden"], 2)
        else:
            logger.warning(f"Fehler bei Kummulation (Quartal): {ergebnis_quartal.get('error')}")
            self.kummulierte_gleitzeit_quartal = 0.0


        # 3. Jahr berechnen

        start_jahr = heute.replace(month=1, day=1)
        ergebnis_jahr = self.berechne_durchschnittliche_gleitzeit(start_jahr, heute, include_missing)
        if "error" not in ergebnis_jahr:
            self.kummulierte_gleitzeit_jahr = round(ergebnis_jahr["durchschnitt_gleitzeit_stunden"], 2)
        else:
            logger.warning(f"Fehler bei Kummulation (Jahr): {ergebnis_jahr.get('error')}")
            self.kummulierte_gleitzeit_jahr = 0.0



class ModellLogin():
    """
    Geschäftslogik-Klasse für Login und Registrierung.
    
    Diese Klasse verwaltet:
    - Registrierung neuer Benutzer mit Validierung
    - Login-Funktionalität mit Passwortprüfung
    - Vorgesetzten-Verwaltung
    - Feedback-Nachrichten für die UI
    
    Attributes:
        neuer_nutzer_* (str/int): Eingabedaten für Registrierung
        neuer_nutzer_rückmeldung (str): Feedback zur Registrierung
        anmeldung_* (str): Eingabedaten für Login
        anmeldung_rückmeldung (str): Feedback zum Login
        anmeldung_mitarbeiter_id_validiert (int): ID des erfolgreich angemeldeten Nutzers
    """
    def __init__(self):
        """Initialisiert ein ModellLogin-Objekt mit leeren Standardwerten."""
       self.neuer_nutzer_name = None
       self.neuer_nutzer_passwort = None
       self.neuer_nutzer_passwort_val = None
       self.neuer_nutzer_vertragliche_wochenstunden = None
       self.neuer_nutzer_geburtsdatum = None
       self.neuer_nutzer_rückmeldung = ""
       self.neuer_nutzer_vorgesetzter = None
       self.neuer_nutzer_grün = None
       self.neuer_nutzer_rot = None
       self.anmeldung_name = None
       self.anmeldung_passwort = None
       self.anmeldung_rückmeldung = ""
       self.anmeldung_mitarbeiter_id_validiert = None
       


    def neuen_nutzer_anlegen(self):
        """
        Registriert einen neuen Benutzer in der Datenbank.
        
        Führt umfassende Validierungen durch:
        - Prüfung auf leere Felder
        - Datumsformat-Validierung
        - Zahlenformat-Validierung
        - Passwort-Übereinstimmung
        - Ampel-Grenzwerte-Logik
        - Vorgesetzten-Existenz
        - Benutzername-Eindeutigkeit
        
        Setzt neuer_nutzer_rückmeldung mit Erfolgs- oder Fehlermeldung.
        """
        # Input-Validierung
        if not self.neuer_nutzer_name:
            self.neuer_nutzer_rückmeldung = "Bitte gib einen Namen ein"
            return
        # Weitere Validierungen folgen im Code...
        
        # Die try-except-Blöcke für strptime und int() sind ebenfalls sehr gut.
        try:
            geburtsdatum_obj = datetime.strptime(self.neuer_nutzer_geburtsdatum, "%d/%m/%Y").date()
        except ValueError:
            self.neuer_nutzer_rückmeldung = "Bitte wähle ein Datum aus"
            return
        
        try:
            wochenstunden_int = int(self.neuer_nutzer_vertragliche_wochenstunden)
            grün_int = int(self.neuer_nutzer_grün)
            rot_int = int(self.neuer_nutzer_rot)
            # Zusätzliche logische Prüfung
            if rot_int >= grün_int:
                self.neuer_nutzer_rückmeldung = "Roter Grenzwert muss kleiner als grüner sein."
                return
        except (ValueError, TypeError):
            self.neuer_nutzer_rückmeldung = "Arbeitszeit und Grenzwerte müssen Zahlen sein."
            return
        
        if self.neuer_nutzer_passwort != self.neuer_nutzer_passwort_val:
            self.neuer_nutzer_rückmeldung = "Die Passwörter müssen übereinstimmen"
            return

        if not session:
            self.neuer_nutzer_rückmeldung = "Datenbankverbindung fehlgeschlagen."
            return

        # Vorgesetzten-Prüfung und Nutzer-Erstellung in try-Block
        try:
            vorgesetzter_id = None
            if self.neuer_nutzer_vorgesetzter:
                stmt = select(mitarbeiter).where(mitarbeiter.name == self.neuer_nutzer_vorgesetzter)
                vorgesetzter_obj = session.execute(stmt).scalar_one_or_none()
                if vorgesetzter_obj:
                    vorgesetzter_id = vorgesetzter_obj.mitarbeiter_id
                else:
                    self.neuer_nutzer_rückmeldung = f"Vorgesetzter '{self.neuer_nutzer_vorgesetzter}' nicht gefunden."
                    return
            
            neuer_nutzer = mitarbeiter(
                name=self.neuer_nutzer_name, 
                password=self.neuer_nutzer_passwort, 
                vertragliche_wochenstunden=wochenstunden_int, 
                geburtsdatum=geburtsdatum_obj,
                letzter_login=date.today(),
                ampel_grün=grün_int,
                ampel_rot=rot_int,
                vorgesetzter_id=vorgesetzter_id
            ) 
        
            session.add(neuer_nutzer)
            session.commit()
            self.neuer_nutzer_rückmeldung = "Der Account wurde erfolgreich angelegt" 
            logger.info(f"Neuer Nutzer angelegt: {self.neuer_nutzer_name}")

        except IntegrityError:
            # Dieser Block war schon gut
            session.rollback()
            self.neuer_nutzer_rückmeldung = f"Der Benutzername '{self.neuer_nutzer_name}' existiert bereits."
            logger.warning(f"Versuch, doppelten Nutzer anzulegen: {self.neuer_nutzer_name}")
        except SQLAlchemyError as e:
            # Fängt andere DB-Fehler ab (z.B. Verbindung weg)
            session.rollback()
            self.neuer_nutzer_rückmeldung = "Ein Datenbankfehler ist aufgetreten."
            logger.error(f"Fehler beim Anlegen von Nutzer {self.neuer_nutzer_name}: {e}", exc_info=True)
        except Exception as e:
            # Fängt unerwartete Logikfehler ab
            session.rollback()
            self.neuer_nutzer_rückmeldung = "Ein unerwarteter Fehler ist aufgetreten."
            logger.critical(f"Unerwarteter Fehler beim Anlegen von Nutzer {self.neuer_nutzer_name}: {e}", exc_info=True)


    def login(self):
        """
        Authentifiziert einen Benutzer und aktualisiert das letzte Login-Datum.
        
        Prozess:
        1. Datenbankverbindung prüfen
        2. Benutzer anhand des Namens suchen
        3. Passwort vergleichen (Klartext - unsicher, nur für Demo!)
        4. Bei Erfolg: letzter_login aktualisieren und ID speichern
        
        Returns:
            bool: True bei erfolgreichem Login, False bei Fehler
            
        Note:
            Passwörter werden im Klartext gespeichert. In einer Produktionsumgebung
            sollte ein Hash-Verfahren (z.B. bcrypt) verwendet werden!
        """
        if not session:
            self.anmeldung_rückmeldung = "Datenbankverbindung fehlgeschlagen."
            return False

        try:
            stmt = select(mitarbeiter).where(mitarbeiter.name == self.anmeldung_name)
            nutzer = session.execute(stmt).scalar_one_or_none()

            if nutzer is None:
                self.anmeldung_rückmeldung = "Passwort oder Nutzername falsch"
                logger.warning(f"Fehlgeschlagener Login-Versuch für: {self.anmeldung_name}")
                return False

            elif nutzer.password == self.anmeldung_passwort:
                self.anmeldung_rückmeldung = "Login erfolgreich"
                self.anmeldung_mitarbeiter_id_validiert = nutzer.mitarbeiter_id
                
                # 'letzter_login' aktualisieren
                try:
                    nutzer.letzter_login = date.today()
                    session.commit()
                    logger.info(f"Erfolgreicher Login für: {self.anmeldung_name}. Letzter Login aktualisiert.")
                except SQLAlchemyError as e:
                    logger.error(f"Fehler beim Aktualisieren des 'letzter_login' Datums für {self.anmeldung_name}: {e}", exc_info=True)
                    session.rollback() # Rollback, aber Login trotzdem erlauben
                    
                return True

            else:
                self.anmeldung_rückmeldung = "Passwort oder Nutzername falsch"
                logger.warning(f"Falsches Passwort für: {self.anmeldung_name}")
                return False
                
        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler während Login-Versuch für {self.anmeldung_name}: {e}", exc_info=True)
            self.anmeldung_rückmeldung = "Datenbankfehler beim Login."
            session.rollback()
            return False
        except Exception as e:
            logger.critical(f"Unerwarteter Fehler während Login für {self.anmeldung_name}: {e}", exc_info=True)
            self.anmeldung_rückmeldung = "Unerwarteter Fehler beim Login."
            return False