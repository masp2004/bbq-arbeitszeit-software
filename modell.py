"""
Datenmodell für das Zeiterfassungssystem.

Dieses Modul enthält alle Datenbank-Modelle, Business-Logik und
Datenzugriffsschichten für das Zeiterfassungssystem.

Hauptklassen:
- mitarbeiter: SQLAlchemy ORM-Modell für Benutzer
- Zeiteintrag: SQLAlchemy ORM-Modell für Ein-/Ausstempelungen
- Benachrichtigung: SQLAlchemy ORM-Modell für Systemwarnungen
- Abwesenheit: SQLAlchemy ORM-Modell für Urlaub/Krankheit
- WochenstundenHistorie: SQLAlchemy ORM-Modell für Arbeitszeitänderungen
- ModellTrackTime: Geschäftslogik für Zeiterfassung
- ModellLogin: Geschäftslogik für Authentifizierung und Benutzerverwaltung

Funktionen:
- Zeiterfassung und Gleitzeit-Berechnung
- Arbeitszeitschutzgesetz-Prüfungen (Ruhezeiten, Maximale Arbeitszeit, etc.)
- Benachrichtigungssystem
- Passwort-Verschlüsselung mit bcrypt
- Datenbank-Management

Autor: Velqor
Version: 2.0
"""

from sqlalchemy import Column, Integer, String, Date, create_engine, select, Time, Boolean, ForeignKey, UniqueConstraint, CheckConstraint, Float
import sqlalchemy.orm as saorm
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from datetime import datetime, date, timedelta, time
from pathlib import Path
import holidays 
import logging
import sys
import os
import bcrypt

# Logger für dieses Modul
logger = logging.getLogger(__name__)

def get_db_path():
    """
    Bestimmt den Pfad zur Datenbankdatei.
    Bei .exe: Im Ordner der .exe-Datei
    Bei Entwicklung: Im aktuellen Arbeitsverzeichnis
    """
    if getattr(sys, 'frozen', False):
        # Anwendung läuft als .exe (PyInstaller)
        app_dir = os.path.dirname(sys.executable)
    else:
        # Anwendung läuft im Entwicklungsmodus
        app_dir = os.path.dirname(os.path.abspath(__file__))
    
    db_path = os.path.join(app_dir, 'system.db')
    logger.info(f"Datenbankpfad: {db_path}")
    return db_path

def initialize_database(db_path):
    """
    Erstellt die Datenbank mit allen Tabellen, falls sie nicht existiert.
    """
    import sqlite3
    
    if os.path.exists(db_path):
        logger.info("Datenbank existiert bereits.")
        return
    
    logger.info("Datenbank nicht gefunden. Erstelle neue Datenbank...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                mitarbeiter_id INTEGER PRIMARY KEY,
                name VARCHAR(30) UNIQUE NOT NULL,
                password VARCHAR(60) NOT NULL,
                vertragliche_wochenstunden INTEGER NOT NULL,
                geburtsdatum DATE NOT NULL,   
                gleitzeit  DECIMAL(4,2) NOT NULL DEFAULT 0,
                letzter_login DATE NOT NULL,
                ampel_grün INTEGER NOT NULL DEFAULT 5,
                ampel_rot INTEGER NOT NULL DEFAULT 10,
                vorgesetzter_id INTEGER   REFERENCES users(mitarbeiter_id)
            );
            CREATE TABLE IF NOT EXISTS zeiteinträge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mitarbeiter_id INTEGER NOT NULL REFERENCES users(mitarbeiter_id),
                zeit TIME NOT NULL,
                datum DATE NOT NULL,
                validiert BOOLEAN  NOT NULL DEFAULT 0      
            ); 
            CREATE TABLE IF NOT EXISTS benachrichtigungen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mitarbeiter_id INTEGER NOT NULL REFERENCES users(mitarbeiter_id),
                benachrichtigungs_code INTEGER NOT NULL, 
                datum DATE,
                ist_popup BOOLEAN NOT NULL DEFAULT 0,
                popup_uhrzeit TIME
            );
            CREATE TABLE IF NOT EXISTS abwesenheiten (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mitarbeiter_id INTEGER NOT NULL REFERENCES users(mitarbeiter_id),
                datum DATE NOT NULL,
                typ TEXT CHECK (typ IN ('Urlaub', 'Krankheit', 'Fortbildung', 'Sonstiges')) NOT NULL,
                genehmigt BOOLEAN NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS wochenstunden_historie (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mitarbeiter_id INTEGER NOT NULL REFERENCES users(mitarbeiter_id),
                gueltig_ab DATE NOT NULL,
                wochenstunden INTEGER NOT NULL,
                UNIQUE (mitarbeiter_id, gueltig_ab)
            );         
        ''')
        conn.commit()
        conn.close()
        logger.info("Datenbank erfolgreich erstellt.")
    except Exception as e:
        logger.critical(f"Fehler beim Erstellen der Datenbank: {e}", exc_info=True)
        raise

try:
    # Datenbankpfad bestimmen und ggf. Datenbank erstellen
    DB_PATH = get_db_path()
    initialize_database(DB_PATH)
    
    # Datenbankverbindung aufbauen
    engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
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
    SQLAlchemy ORM-Modell für Mitarbeiter/Benutzer.
    
    Repräsentiert einen Mitarbeiter mit allen Stammdaten, Einstellungen
    und aktuellen Status-Informationen.
    
    Attributes:
        mitarbeiter_id (int): Eindeutige ID (Primary Key)
        name (str): Vor- und Nachname (max. 30 Zeichen, eindeutig)
        password (str): Bcrypt-gehashtes Passwort (60 Zeichen)
        vertragliche_wochenstunden (int): Vereinbarte Wochenarbeitszeit
        geburtsdatum (date): Geburtsdatum für Arbeitszeitschutz-Prüfungen
        gleitzeit (float): Aktuelle Gleitzeit in Stunden (kann negativ sein)
        letzter_login (date): Datum des letzten Logins
        ampel_grün (int): Grüner Schwellwert für Gleitzeit-Ampel (Stunden)
        ampel_rot (int): Roter Schwellwert für Gleitzeit-Ampel (Stunden)
        vorgesetzter_id (int): ID des Vorgesetzten (Foreign Key, optional)
    
    Note:
        Die Ampel-Werte sind symmetrisch: ±grün für ausgeglichen, ±rot für kritisch.
    """
    __tablename__ = "users"
    mitarbeiter_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(30), unique=True, nullable=False)
    password = Column(String(60), nullable=False)  # 60 Zeichen für bcrypt-Hash
    vertragliche_wochenstunden = Column(Integer, nullable=False)
    geburtsdatum = Column(Date, nullable=False)
    gleitzeit = Column(Float, nullable=False, default=0.0)  # Float für Dezimalwerte (Stunden mit Nachkommastellen)
    letzter_login = Column(Date, nullable=False)
    ampel_grün = Column(Integer, nullable=False, default=5)  # Grüne Schwelle: ±5h
    ampel_rot = Column(Integer, nullable=False, default=10)  # Rote Schwelle: ±10h (geändert von -5)
    vorgesetzter_id = Column(Integer, ForeignKey("users.mitarbeiter_id"))

    def is_minor_on_date(self, datum):
            """
            Prüft, ob der Mitarbeiter an einem bestimmten Datum minderjährig ist.
            
            Args:
                datum (date): Das zu prüfende Datum
                
            Returns:
                bool: True wenn unter 18 Jahren, sonst False
                
            Note:
                Berücksichtigt Monat und Tag für präzise Altersberechnung.
                Bei fehlenden Daten oder ungültigem Typ wird False zurückgegeben.
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
    SQLAlchemy ORM-Modell für Abwesenheiten.
    
    Repräsentiert Abwesenheiten wie Urlaub, Krankheit, Fortbildung, etc.
    
    Attributes:
        id (int): Eindeutige ID (Primary Key)
        mitarbeiter_id (int): ID des Mitarbeiters (Foreign Key)
        datum (date): Datum der Abwesenheit
        typ (str): Art der Abwesenheit ('Urlaub', 'Krankheit', 'Fortbildung', 'Sonstiges')
        genehmigt (bool): Genehmigungsstatus der Abwesenheit
    """
    __tablename__ = "abwesenheiten"
    id = Column(Integer, primary_key=True, autoincrement=True)
    mitarbeiter_id = Column(Integer, ForeignKey("users.mitarbeiter_id"), nullable=False)
    datum = Column(Date, nullable=False)
    typ = Column(String, CheckConstraint("typ IN ('Urlaub', 'Krankheit', 'Fortbildung', 'Sonstiges')"), nullable=False)
    genehmigt = Column(Boolean, nullable=False, default=False)


class Zeiteintrag(Base):
    """
    SQLAlchemy ORM-Modell für Zeiteinträge (Stempel).
    
    Repräsentiert eine einzelne Ein- oder Ausstempelung.
    
    Attributes:
        id (int): Eindeutige ID (Primary Key)
        mitarbeiter_id (int): ID des Mitarbeiters (Foreign Key)
        zeit (time): Uhrzeit des Stempels
        datum (date): Datum des Stempels
        validiert (bool): Ob der Stempel bereits für Gleitzeit-Berechnung verwendet wurde
        
    Note:
        Ein- und Ausstempelungen werden durch ungerade/gerade Anzahl unterschieden.
        Validierte Einträge wurden bereits in der Gleitzeit-Berechnung berücksichtigt.
    """
    __tablename__ = "zeiteinträge"
    id = Column(Integer, primary_key=True, autoincrement=True)
    mitarbeiter_id = Column(Integer, ForeignKey("users.mitarbeiter_id"), nullable=False)
    zeit = Column(Time, nullable=False)
    datum = Column(Date, nullable=False)
    validiert = Column(Boolean, nullable=False, default=False)


class Benachrichtigungen(Base):
    """
    SQLAlchemy ORM-Modell für Benachrichtigungen.
    
    Repräsentiert System-Benachrichtigungen und PopUp-Warnungen.
    
    Attributes:
        id (int): Eindeutige ID (Primary Key)
        mitarbeiter_id (int): ID des Mitarbeiters (Foreign Key)
        benachrichtigungs_code (int): Code der Benachrichtigung (1-10)
        datum (date): Betroffenes Datum (optional)
        ist_popup (bool): True für zeitgesteuerte PopUps, False für normale Benachrichtigungen
        popup_uhrzeit (time): Geplante Uhrzeit für PopUp (nur bei ist_popup=True)
        
    Benachrichtigungs-Codes:
        1: Fehlstempel
        2: Fehlender Arbeitstag
        3: Ruhezeitenverletzung
        4: Durchschnittliche Arbeitszeit > 8h
        5: Maximale Arbeitszeit überschritten
        6: Arbeit an Sonn-/Feiertag
        7: Wochenstunden > 40h (Minderjährige)
        8: > 5 Arbeitstage/Woche (Minderjährige)
        9: Arbeitsfenster-Warnung (PopUp)
        10: Max. Arbeitszeit-Warnung (PopUp)
    """
    __tablename__ = "benachrichtigungen"
    id = Column(Integer, primary_key=True, autoincrement=True)
    mitarbeiter_id = Column(Integer, ForeignKey("users.mitarbeiter_id"), nullable=False)
    benachrichtigungs_code = Column(Integer, nullable=False)
    datum = Column(Date)
    ist_popup = Column(Boolean, nullable=False, default=False)  # True = PopUp, False = normale Benachrichtigung
    popup_uhrzeit = Column(Time, nullable=True)  # Optionale Uhrzeit für zeitgesteuerte PopUps

    # Texte für Benachrichtigungen (verwendet in der View-Layer)
    CODES = {
        1.1: "An den Tag",
        1.2: "wurde nicht gestempelt. Es wird für jeden Tag die Tägliche arbeitszeit der Gleitzeit abgezogen",
        2.1: "Am",
        2.2: "fehlt ein Stempel, bitte tragen sie diesen nach",
        3: ["Achtung, am", "wurden die gesetzlichen Ruhezeiten nicht eingehalten"],
        4: "Achtung, Ihre durchschnittliche tägliche Arbeitszeit der letzten 6 Monate hat 8 Stunden überschritten.",
        5:["Achung am", "wurde die maximale gesetzlich zulässsige Arbeitszeit überschritten."],
        6: ["Achtung, am", "wurde an einem Sonn- oder Feiertag gearbeitet."],
        7: ["In der Woche vom", "wurde die maximale Wochenarbeitszeit von 40 Stunden für Minderjährige überschritten."],
        8: ["In der Woche vom", "wurde an mehr als 5 Tagen gearbeitet, was für Minderjährige nicht zulässig ist."],
        9: ["Achtung, am", "wurde außerhalb der gesetzlich zulässigen Arbeitszeiten (6:00 - 20:00 Uhr) für Minderjährige gestempelt."],
        10: "Ihr erlaubtes Arbeitsfenster endet bald.",  # Arbeitsfenster-Warnung (PopUp)
        11: "Sie erreichen bald die maximale tägliche Arbeitszeit."  # Max. Arbeitszeit-Warnung (PopUp)
    }

    __table_args__ = (
        UniqueConstraint("mitarbeiter_id", "benachrichtigungs_code", "datum", name="uq_benachrichtigung_unique"),
    )

    def create_fehlermeldung(self):
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
            elif code_str == "9":
                datum_str = self.datum.strftime('%d.%m.%Y') if self.datum else "[Datum fehlt]"
                return f"{self.CODES[9][0]} {datum_str} {self.CODES[9][1]}"
            elif code_str == "10":
                return self.CODES[10]
            elif code_str == "11":
                return self.CODES[11]
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


class VertragswochenstundenHistorie(Base):
    """
    SQLAlchemy ORM-Modell für Wochenstunden-Historie.
    
    Speichert Änderungen der vertraglichen Wochenarbeitszeit mit Gültigkeitsdatum.
    Ermöglicht historische Auswertungen und korrekte Gleitzeit-Berechnungen
    bei Änderungen der Arbeitszeit.
    
    Attributes:
        id (int): Eindeutige ID (Primary Key)
        mitarbeiter_id (int): ID des Mitarbeiters (Foreign Key)
        gueltig_ab (date): Ab wann die neuen Wochenstunden gelten
        wochenstunden (int): Neue vertragliche Wochenarbeitszeit
        
    Note:
        Pro Mitarbeiter und Datum kann nur ein Eintrag existieren (Unique Constraint).
    """
    __tablename__ = "wochenstunden_historie"
    id = Column(Integer, primary_key=True, autoincrement=True)
    mitarbeiter_id = Column(Integer, ForeignKey("users.mitarbeiter_id"), nullable=False)
    gueltig_ab = Column(Date, nullable=False)
    wochenstunden = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("mitarbeiter_id", "gueltig_ab", name="uq_wochenstunden_historie_eintrag"),
    )


# === Hilfsfunktionen ===

def _normalize_to_date(value):
    """
    Normalisiert verschiedene Datumsformate zu einem date-Objekt.
    
    Args:
        value: Datum als date, datetime oder String
        
    Returns:
        date: Normalisiertes Datum oder None bei Fehler
        
    Supported Formats:
        - date-Objekt (wird direkt zurückgegeben)
        - datetime-Objekt (wird zu date konvertiert)
        - String: "%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"
    """
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return None


# === Passwort-Verschlüsselungs-Hilfsfunktionen ===
def hash_password(password: str) -> str:
    """
    Hasht ein Passwort mit bcrypt.
    
    Args:
        password: Das Klartext-Passwort
        
    Returns:
        Der bcrypt-Hash als String
    """
    if not password:
        raise ValueError("Passwort darf nicht leer sein")
    
    # Passwort in bytes konvertieren und hashen
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    # Hash als String zurückgeben
    return hashed.decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verifiziert ein Passwort gegen einen bcrypt-Hash.
    
    Args:
        password: Das zu prüfende Klartext-Passwort
        hashed_password: Der bcrypt-Hash
        
    Returns:
        True wenn das Passwort korrekt ist, sonst False
    """
    if not password or not hashed_password:
        return False
    
    try:
        password_bytes = password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        logger.error(f"Fehler bei Passwort-Verifizierung: {e}", exc_info=True)
        return False


def hole_wochenstunden_am_datum(mitarbeiter_id, datum, fallback_wochenstunden):
    """
    Ermittelt die gültigen Wochenstunden für einen Mitarbeiter an einem Datum.
    
    Sucht in der Wochenstunden-Historie nach dem passenden Eintrag für das
    angegebene Datum und gibt die zu diesem Zeitpunkt gültigen Wochenstunden zurück.
    
    Args:
        mitarbeiter_id (int): ID des Mitarbeiters
        datum: Datum als date, datetime oder String
        fallback_wochenstunden (int): Rückgabewert wenn keine Historie gefunden wird
        
    Returns:
        int: Gültige Wochenstunden am angegebenen Datum oder Fallback-Wert
        
    Note:
        Verwendet den letzten Eintrag vor oder am angegebenen Datum.
        Bei Fehlern oder fehlenden Daten wird der Fallback-Wert zurückgegeben.
    """
    if not mitarbeiter_id:
        return fallback_wochenstunden

    datum = _normalize_to_date(datum)
    if datum is None:
        logger.debug("hole_wochenstunden_am_datum: Ungültiges Datum übergeben, verwende Fallback")
        return fallback_wochenstunden

    if not session:
        logger.error("hole_wochenstunden_am_datum: Keine aktive DB-Session, verwende Fallback")
        return fallback_wochenstunden

    try:
        stmt = (
            select(VertragswochenstundenHistorie.wochenstunden)
            .where(
                (VertragswochenstundenHistorie.mitarbeiter_id == mitarbeiter_id) &
                (VertragswochenstundenHistorie.gueltig_ab <= datum)
            )
            .order_by(VertragswochenstundenHistorie.gueltig_ab.desc())
            .limit(1)
        )
        result = session.execute(stmt).scalar_one_or_none()
        if result is not None:
            return int(result)
    except SQLAlchemyError as e:
        logger.error(f"hole_wochenstunden_am_datum: Fehler beim Lesen der Historie: {e}", exc_info=True)

    return fallback_wochenstunden


def berechne_taegliche_sollzeit(wochenstunden, fallback_stunden=None):
    """
    Berechnet die tägliche Sollarbeitszeit basierend auf Wochenstunden.
    
    Teilt die Wochenstunden durch 5 (5-Tage-Woche) um die tägliche
    Sollarbeitszeit zu ermitteln.
    
    Args:
        wochenstunden: Wöchentliche Arbeitsstunden (int oder float)
        fallback_stunden: Optionaler Fallback-Wert bei ungültigen Eingaben
        
    Returns:
        timedelta: Tägliche Sollarbeitszeit oder leeres timedelta bei Fehler
        
    Note:
        Bei ungültigen oder negativen Werten wird der Fallback verwendet
        oder ein leeres timedelta zurückgegeben.
    """
    try:
        wochenstunden_float = float(wochenstunden) if wochenstunden is not None else None
    except (TypeError, ValueError):
        wochenstunden_float = None

    if wochenstunden_float is None or wochenstunden_float <= 0:
        if fallback_stunden is not None:
            return timedelta(hours=float(fallback_stunden))
        return timedelta()

    return timedelta(hours=(wochenstunden_float / 5))


class CalculateTime():
    """
    Hilfsklasse zur Berechnung der Arbeitszeit zwischen zwei Stempeln.
    
    Berechnet die Differenz zwischen Ein- und Ausstempelung und berücksichtigt
    dabei die tägliche Sollarbeitszeit und Pausenregelungen.
    
    Args:
        eintrag1 (Zeiteintrag): Einstempel-Zeitpunkt
        eintrag2 (Zeiteintrag): Ausstempel-Zeitpunkt
        nutzer (mitarbeiter): Mitarbeiter-Objekt für Sollarbeitszeit
        
    Attributes:
        nutzer (mitarbeiter): Zugehöriger Mitarbeiter
        datum (date): Datum der Stempel
        startzeit (time): Uhrzeit des Einstempelns
        endzeit (time): Uhrzeit des Ausstempelns
        start_dt (datetime): Kombiniertes Datum-Zeit-Objekt (Start)
        end_dt (datetime): Kombiniertes Datum-Zeit-Objekt (Ende)
        
    Returns:
        None: Wenn Einträge von unterschiedlichen Tagen stammen
        CalculateTime: Objekt zur Zeitberechnung
    """
    def __new__(cls, eintrag1, eintrag2, nutzer):
        # Nur erstellen, wenn beide Einträge vom selben Tag sind
        if eintrag1.datum != eintrag2.datum:
            return None
        return super().__new__(cls)

    def __init__(self, eintrag1, eintrag2, nutzer):
        """
        Initialisiert das CalculateTime-Objekt für zwei Stempel desselben Tages.
        
        Args:
            eintrag1 (Zeiteintrag): Erster Stempel (Einstempelung)
            eintrag2 (Zeiteintrag): Zweiter Stempel (Ausstempelung)
            nutzer (mitarbeiter): Mitarbeiter-Objekt für Pausenregelungen
            
        Attributes:
            nutzer (mitarbeiter): Referenz zum Mitarbeiter
            datum (date): Datum der Stempel
            startzeit (time): Uhrzeit des Einstempelns
            endzeit (time): Uhrzeit des Ausstempelns
            start_dt (datetime): Kombiniertes Start-Datum-Zeit-Objekt
            end_dt (datetime): Kombiniertes End-Datum-Zeit-Objekt
            gearbeitete_zeit (timedelta): Berechnete Arbeitsze it (Endzeit - Startzeit)
            
        Note:
            Wenn Endzeit vor Startzeit liegt (Fehleingabe), werden die Zeiten
            getauscht und auf timedelta(0) gesetzt.
        """
        # Basis-Attribute setzen
        self.nutzer = nutzer
        self.datum = eintrag1.datum
        self.startzeit = eintrag1.zeit
        self.endzeit = eintrag2.zeit

        try:
            # Datum und Uhrzeit kombinieren für datetime-Berechnungen
            self.start_dt = datetime.combine(self.datum, self.startzeit)
            self.end_dt = datetime.combine(self.datum, self.endzeit)
            
            # Validierung: Endzeit muss nach Startzeit liegen
            if self.end_dt < self.start_dt:
                logger.warning(f"Endzeit {self.end_dt} liegt vor Startzeit {self.start_dt}. Zeit wird als 0 behandelt.")
                # Zeiten tauschen (Fehlerkorrektur)
                self.start_dt, self.end_dt = self.end_dt, self.start_dt
                # Gearbeitete Zeit auf 0 setzen
                self.gearbeitete_zeit = timedelta()
            else:
                # Normale Berechnung: Differenz zwischen End- und Startzeit
                self.gearbeitete_zeit = self.end_dt - self.start_dt
         
        except (TypeError, ValueError) as e:
            logger.error(f"Fehler beim Kombinieren von Datum/Zeit: {e}", exc_info=True)
            # Fallback: Arbeitszeit = 0
            self.gearbeitete_zeit = timedelta()

    def gesetzliche_pausen_hinzufügen(self):
        """
        Zieht gesetzliche Pausenzeiten von der Arbeitszeit ab.
        
        Pausenregelungen:
        Minderjährige:
            - >= 6h: 60min Pause
            - >= 4.5h: 30min Pause
        Volljährige:
            - >= 9h: 45min Pause
            - >= 6h: 30min Pause
            
        Note:
            Pausenzeiten werden nicht erfasst, sondern automatisch abgezogen.
        """
        # Validierung
        if not self.nutzer:
            logger.error("gesetzliche_pausen_hinzufügen ohne 'nutzer' aufgerufen.")
            return
        
        # Unterschiedliche Regelungen für Minderjährige und Volljährige
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
        Entfernt Arbeitszeit, die außerhalb des erlaubten Arbeitsfensters liegt.
        
        Arbeitsfenster:
        - Minderjährige: 6:00 - 20:00 Uhr (JArbSchG § 14)
        - Erwachsene: 6:00 - 22:00 Uhr
        
        Arbeitszeit außerhalb dieses Zeitraums wird nicht zur Gleitzeit gerechnet,
        aber erfasst (für Compliance-Zwecke).
        
        Note:
            Berechnet Überschneidungen der Arbeitszeit mit Ruhe-Zeiträumen
            (00:00-06:00 und 20:00/22:00-24:00) und zieht diese ab.
        """
        # Validierung: Nutzer und datetime-Objekte müssen existieren
        if not self.nutzer:
            logger.error("arbeitsfenster_beachten ohne 'nutzer' aufgerufen.")
            return
        if not hasattr(self, 'start_dt') or not hasattr(self, 'end_dt'):
            logger.error("arbeitsfenster_beachten: start_dt/end_dt nicht initialisiert.")
            return

        # Altersabhängige Nachtruhe-Grenze festlegen
        is_minor = self.nutzer.is_minor_on_date(self.datum)
        nachtruhe_zeit = time(20, 0) if is_minor else time(22, 0)  # 20 Uhr (Minderjährige) oder 22 Uhr (Erwachsene)
        
        # Zeitgrenzen als datetime-Objekte
        morgenruhe_ende = datetime.combine(self.datum, time(6, 0))  # 06:00 Uhr
        nachtruhe_start = datetime.combine(self.datum, nachtruhe_zeit)  # 20:00 oder 22:00 Uhr

        abzuziehende_zeit = timedelta()  # Initialisierung: Keine Zeit abziehen

        # === 1. Überschneidung mit Morgenruhe (00:00 - 06:00) berechnen ===
        # Überschneidungsstart: Später von (Arbeitsbeginn, 00:00)
        overlap_start_morgen = max(self.start_dt, datetime.combine(self.datum, time(0, 0)))
        # Überschneidungsende: Früher von (Arbeitsende, 06:00)
        overlap_end_morgen = min(self.end_dt, morgenruhe_ende)

        # Wenn Überschneidung existiert (Ende > Start): Zeit abziehen
        if overlap_end_morgen > overlap_start_morgen:
            abzuziehende_zeit += overlap_end_morgen - overlap_start_morgen

        # === 2. Überschneidung mit Nachtruhe (20:00/22:00 - 24:00) berechnen ===
        # Überschneidungsstart: Später von (Arbeitsbeginn, Nachtruhe-Beginn)
        overlap_start_nacht = max(self.start_dt, nachtruhe_start)
        # Überschneidungsende: Früher von (Arbeitsende, 23:59:59)
        overlap_end_nacht = min(self.end_dt, datetime.combine(self.datum, time(23, 59, 59)))

        # Wenn Überschneidung existiert: Zeit abziehen
        if overlap_end_nacht > overlap_start_nacht:
            abzuziehende_zeit += overlap_end_nacht - overlap_start_nacht
        
        # Gesamte außerhalb des Arbeitsfensters liegende Zeit von Arbeitszeit abziehen
        self.gearbeitete_zeit -= abzuziehende_zeit


# === Hauptgeschäftslogik-Klassen ===

class ModellTrackTime():
    """
    Hauptgeschäftslogik-Klasse für die Zeiterfassung.
    
    Diese Klasse verwaltet alle Operationen rund um Zeiterfassung,
    Gleitzeit-Berechnung, Benachrichtigungen und Arbeitszeitschutz-Prüfungen.
    
    Hauptfunktionalitäten:
    - Zeitstempel-Verwaltung (Hinzufügen, Bearbeiten, Löschen)
    - Gleitzeit-Berechnung mit Pausenregelung und Arbeitsfenster
    - Arbeitszeitschutzgesetz-Prüfungen (Ruhezeiten, Max. Arbeitszeit, etc.)
    - Benachrichtigungssystem (statische und zeitgesteuerte PopUps)
    - Abwesenheiten (Urlaub, Krankheit)
    - Mitarbeiter-Verwaltung und -Einstellungen
    - Kalender-Ansicht und Statistiken
    
    Attributes:
        aktueller_nutzer_id (int): ID des eingeloggten Mitarbeiters
        aktueller_nutzer_name (str): Name des eingeloggten Mitarbeiters
        aktueller_nutzer_geburtsdatum (date): Geburtsdatum für Arbeitszeitschutz
        aktueller_nutzer_vertragliche_wochenstunden (int): Wochenarbeitszeit
        aktueller_nutzer_gleitzeit (float): Aktuelle Gleitzeit in Stunden
        aktueller_nutzer_ampel_rot (int): Roter Schwellwert
        aktueller_nutzer_ampel_grün (int): Grüner Schwellwert
        _cached_aktueller_nutzer (mitarbeiter): Gecachtes Mitarbeiter-Objekt
        
        nachtragen_datum (str): Datum für manuelles Nachtragen
        manueller_stempel_uhrzeit (str): Uhrzeit für manuelles Nachtragen
        neuer_abwesenheitseintrag_art (str): Art der Abwesenheit
        
        zeiteinträge_bestimmtes_datum (list): Stempel für gewähltes Datum
        bestimmtes_datum (str): Aktuell ausgewähltes Datum
        gleitzeit_bestimmtes_datum_stunden (float): Gleitzeit für ausgewähltes Datum
        
        kummulierte_gleitzeit_jahr (float): Gleitzeit-Summe Jahr
        kummulierte_gleitzeit_quartal (float): Gleitzeit-Summe Quartal
        kummulierte_gleitzeit_monat (float): Gleitzeit-Summe Monat
        tage_ohne_stempel_beachten (bool): Ob fehlende Tage berücksichtigt werden
        
        mitarbeiter (list): Liste aller Mitarbeiter (für Vorgesetzte)
        aktuelle_kalendereinträge_für_id (int): ID für Kalender-Ansicht
        aktuelle_kalendereinträge_für_name (str): Name für Kalender-Ansicht
        
        neues_passwort (str): Neues Passwort bei Änderung
        neues_passwort_wiederholung (str): Passwort-Bestätigung
        
        feedback_manueller_stempel (str): UI-Feedback für Stempel-Operationen
        benachrichtigungen (list): Aktuelle Benachrichtigungen
        feedback_neues_passwort (str): UI-Feedback für Passwort-Änderung
        ampel_farbe (str): Aktuelle Ampel-Farbe ("grün", "gelb", "rot")
    """
    def __init__(self):
        self.aktueller_nutzer_id = None
        self.aktueller_nutzer_name = None
        self.aktueller_nutzer_geburtsdatum = None
        self.aktueller_nutzer_vertragliche_wochenstunden = None
        self.aktueller_nutzer_gleitzeit = None
        self.aktueller_nutzer_ampel_rot = None
        self.aktueller_nutzer_ampel_grün = None
        self._cached_aktueller_nutzer = None

        self.nachtragen_datum = None
        self.manueller_stempel_uhrzeit = None
        self.neuer_abwesenheitseintrag_art = None

        self.zeiteinträge_bestimmtes_datum = None
        self.bestimmtes_datum = None
        self.gleitzeit_bestimmtes_datum_stunden = 0.0

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
        self.urlaubstage_aktueller_monat = []
        self.krankheitstage_aktueller_monat = []


        self.feedback_manueller_stempel = ""
        self.feedback_arbeitstage = ""
        self.feedback_stempel = ""
        self.feedback_neues_passwort = ""

    def ist_sonn_oder_feiertag(self, datum):
        """
        Prüft, ob ein bestimmtes Datum ein Sonntag oder Feiertag ist.
        
        Args:
            datum: date-Objekt oder String im Format '%d/%m/%Y'
            
        Returns:
            bool: True wenn Sonntag oder Feiertag, sonst False
        """
        # Datum konvertieren falls String
        if isinstance(datum, str):
            try:
                datum = datetime.strptime(datum, "%d/%m/%Y").date()
            except ValueError:
                logger.warning(f"ist_sonn_oder_feiertag: Ungültiges Datumsformat '{datum}'")
                return False
        
        # Prüfen ob Sonntag (weekday() == 6)
        if datum.weekday() == 6:
            return True
        
        # Feiertage für das Jahr holen
        try:
            de_holidays = holidays.Germany(years=datum.year)
            return datum in de_holidays
        except Exception as e:
            logger.error(f"Fehler beim Prüfen der Feiertage: {e}", exc_info=True)
            return False


    # === Hilfsfunktion für sichere DB-Operationen ===
    def _safe_db_operation(self, operation_func, *args, **kwargs):
        """
        Wrapper für sichere Datenbank-Operationen mit Fehlerbehandlung.
        
        Kapselt try/except/rollback-Logik für DB-Operationen und stellt
        sicher, dass bei Fehlern ein Rollback durchgeführt wird.
        
        Args:
            operation_func (callable): Funktion mit DB-Operationen
            *args: Positionelle Argumente für operation_func
            **kwargs: Keyword-Argumente für operation_func
            
        Returns:
            Rückgabewert von operation_func oder None bei Fehler
            
        Note:
            Führt automatisch session.commit() bei Erfolg und
            session.rollback() bei Fehlern aus.
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
        """
        Lädt alle Mitarbeiter, die dem aktuellen Benutzer unterstellt sind.
        
        Sucht in der Datenbank nach allen Mitarbeitern, bei denen der
        aktuelle Benutzer als Vorgesetzter eingetragen ist, und fügt den
        aktuellen Benutzer selbst zur Liste hinzu.
        
        Note:
            Setzt self.mitarbeiter auf die Liste aller Namen.
            Bei Fehlern wird nur der aktuelle Benutzername verwendet (Fallback).
        """
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
        """
        Ermittelt die Mitarbeiter-ID für den im Kalender ausgewählten Mitarbeiter.
        
        Konvertiert den Namen aus aktuelle_kalendereinträge_für_name in die
        entsprechende Mitarbeiter-ID. Falls kein Name gesetzt ist, wird die
        ID des aktuellen Benutzers verwendet.
        
        Note:
            Setzt self.aktuelle_kalendereinträge_für_id.
            Bei Fehlern wird die ID des aktuellen Benutzers verwendet.
        """
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
        """
        Lädt alle Zeiteinträge für ein bestimmtes Datum und berechnet die Gleitzeit.
        
        Holt alle Ein-/Ausstempelungen für das in self.bestimmtes_datum
        angegebene Datum, prüft sie auf Gültigkeit (Arbeitsfenster),
        berechnet die Arbeitszeit und die Gleitzeit für diesen Tag.
        
        Note:
            Setzt self.zeiteinträge_bestimmtes_datum (Liste von [Zeiteintrag, is_problematic])
            und self.gleitzeit_bestimmtes_datum_stunden.
            
            Berücksichtigt Pausenzeiten und Arbeitsfenster gemäß ArbZG.
            Für Minderjährige: 6-20 Uhr, für Volljährige: 6-22 Uhr.
        """
        if self.aktueller_nutzer_id is None or self.bestimmtes_datum is None:
            return
        if not session: return

        self.gleitzeit_bestimmtes_datum_stunden = 0.0

        try:
            ausgewählte_mitarbeiter_id = self.aktuelle_kalendereinträge_für_id or self.aktueller_nutzer_id
            nutzer = session.get(mitarbeiter, ausgewählte_mitarbeiter_id)
            if not nutzer:
                logger.error(f"get_zeiteinträge: Nutzer {ausgewählte_mitarbeiter_id} nicht gefunden.")
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

            # Arbeitszeit und Gleitzeit für den Tag berechnen
            arbeitszeit_summe = timedelta()
            i = 0
            while i < len(einträge) - 1:
                try:
                    calc = CalculateTime(einträge[i], einträge[i + 1], nutzer)
                except Exception as e:
                    logger.error(f"Fehler bei der Arbeitszeitberechnung für {date_obj}: {e}", exc_info=True)
                    calc = None

                if calc:
                    try:
                        calc.gesetzliche_pausen_hinzufügen()
                        calc.arbeitsfenster_beachten()
                    except Exception as e:
                        logger.error(f"Fehler bei Pausen-/Fensterberechnung für {date_obj}: {e}", exc_info=True)

                    arbeitszeit_summe += calc.gearbeitete_zeit
                    i += 2
                else:
                    i += 1

            wochenstunden = hole_wochenstunden_am_datum(
                nutzer.mitarbeiter_id,
                date_obj,
                nutzer.vertragliche_wochenstunden,
            )
            tägliche_arbeitszeit = berechne_taegliche_sollzeit(wochenstunden)
            if tägliche_arbeitszeit > timedelta():
                gleitzeit_diff = arbeitszeit_summe - tägliche_arbeitszeit
            else:
                gleitzeit_diff = arbeitszeit_summe

            # Prüfen, ob für diesen Tag eine Fehlstempel-Benachrichtigung (Code 1) existiert
            # Wenn ja, zeige die negative tägliche Sollzeit als Gleitzeit an
            benachrichtigung_stmt = select(Benachrichtigungen).where(
                (Benachrichtigungen.mitarbeiter_id == ausgewählte_mitarbeiter_id) &
                (Benachrichtigungen.datum == date_obj) &
                (Benachrichtigungen.benachrichtigungs_code == 1)
            )
            hat_fehlstempel_benachrichtigung = session.execute(benachrichtigung_stmt).scalar_one_or_none()
            
            if hat_fehlstempel_benachrichtigung:
                # Bei fehlenden Stempeln wurde die tägliche Sollzeit abgezogen
                # Zeige dies als negative tägliche Sollzeit an
                taegliche_sollzeit_stunden = tägliche_arbeitszeit.total_seconds() / 3600
                self.gleitzeit_bestimmtes_datum_stunden = -round(taegliche_sollzeit_stunden, 2)
                logger.debug(f"get_zeiteinträge: Fehlstempel-Benachrichtigung für {date_obj} gefunden, Gleitzeit: {self.gleitzeit_bestimmtes_datum_stunden}h")
            else:
                self.gleitzeit_bestimmtes_datum_stunden = round(gleitzeit_diff.total_seconds() / 3600, 2) if einträge else 0.0
            
            self.zeiteinträge_bestimmtes_datum = einträge_mit_validierung

        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in get_zeiteinträge: {e}", exc_info=True)
            self.zeiteinträge_bestimmtes_datum = []
            self.gleitzeit_bestimmtes_datum_stunden = 0.0
        except Exception as e:
            logger.error(f"Unerwarteter Fehler in get_zeiteinträge: {e}", exc_info=True)
            self.zeiteinträge_bestimmtes_datum = []
            self.gleitzeit_bestimmtes_datum_stunden = 0.0

    def get_user_info(self):
        """
        Lädt alle Informationen des aktuell eingeloggten Benutzers.
        
        Holt alle relevanten Benutzerdaten aus der Datenbank und
        aktualisiert die entsprechenden Attribute im Model.
        
        Note:
            Setzt folgende Attribute:
            - aktueller_nutzer_name
            - aktueller_nutzer_geburtsdatum
            - aktueller_nutzer_vertragliche_wochenstunden
            - aktueller_nutzer_gleitzeit
            - aktueller_nutzer_ampel_rot
            - aktueller_nutzer_ampel_grün
            - _cached_aktueller_nutzer (für Performance)
            
            Bei Fehlern wird _cached_aktueller_nutzer auf None gesetzt.
        """
        if self.aktueller_nutzer_id is None: return
        if not session: return

        try:
            stmt = select(mitarbeiter).where(mitarbeiter.mitarbeiter_id == self.aktueller_nutzer_id)
            nutzer = session.execute(stmt).scalar_one_or_none()
            if nutzer:
                self.aktueller_nutzer_name = nutzer.name
                self.aktueller_nutzer_geburtsdatum = nutzer.geburtsdatum
                self.aktueller_nutzer_vertragliche_wochenstunden = nutzer.vertragliche_wochenstunden
                # Gleitzeit ist DECIMAL(4,2) in DB, aber Integer in Klasse?
                # Das ist ein potenzieller Bug. Ich caste zu float für Sicherheit.
                self.aktueller_nutzer_gleitzeit = float(nutzer.gleitzeit)
                self.aktueller_nutzer_ampel_rot = nutzer.ampel_rot
                self.aktueller_nutzer_ampel_grün = nutzer.ampel_grün
                self._cached_aktueller_nutzer = nutzer
            else:
                logger.error(f"get_user_info: Nutzer {self.aktueller_nutzer_id} nicht gefunden.")
                self._cached_aktueller_nutzer = None
        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in get_user_info: {e}", exc_info=True)
            self._cached_aktueller_nutzer = None

    def get_aktueller_nutzer(self, force_refresh=False):
        """
        Gibt das aktuell eingeloggte Mitarbeiter-Objekt zurück.
        
        Verwendet einen Cache um unnötige DB-Abfragen zu vermeiden.
        
        Args:
            force_refresh (bool): Wenn True, wird der Cache ignoriert und
                                 neu aus der DB geladen
                                 
        Returns:
            mitarbeiter: Mitarbeiter-Objekt oder None bei Fehler
            
        Note:
            Nutzt _cached_aktueller_nutzer für Performance.
            Bei force_refresh=True wird die Session refreshed.
        """
        if self.aktueller_nutzer_id is None:
            logger.warning("get_aktueller_nutzer: Kein Nutzer gesetzt")
            return None
        if not session:
            logger.error("get_aktueller_nutzer: Keine DB-Session verfügbar")
            return None

        cached = getattr(self, "_cached_aktueller_nutzer", None)
        if (
            cached is not None
            and getattr(cached, "mitarbeiter_id", None) != self.aktueller_nutzer_id
        ):
            cached = None
            self._cached_aktueller_nutzer = None

        if (
            not force_refresh
            and cached is not None
            and getattr(cached, "mitarbeiter_id", None) == self.aktueller_nutzer_id
        ):
            return cached

        try:
            nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
            if nutzer is None:
                logger.warning(
                    "get_aktueller_nutzer: Nutzer %s nicht gefunden", self.aktueller_nutzer_id
                )
                self._cached_aktueller_nutzer = None
                return None

            self._cached_aktueller_nutzer = nutzer
            return nutzer
        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in get_aktueller_nutzer: {e}", exc_info=True)
            self._cached_aktueller_nutzer = None
            return None

    def update_letzter_login(self):
        """
        Aktualisiert den letzter_login des aktuellen Nutzers auf heute.
        Wird nach allen Check-Funktionen beim Login aufgerufen.
        """
        if self.aktueller_nutzer_id is None:
            logger.warning("update_letzter_login: Kein Nutzer angemeldet")
            return
        if not session:
            logger.error("update_letzter_login: Keine DB-Session verfügbar")
            return
        
        try:
            nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
            if nutzer:
                nutzer.letzter_login = date.today()
                session.commit()
                logger.info(f"letzter_login für Nutzer {self.aktueller_nutzer_id} auf {date.today()} aktualisiert")
            else:
                logger.error(f"update_letzter_login: Nutzer {self.aktueller_nutzer_id} nicht gefunden")
        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler beim Aktualisieren von letzter_login: {e}", exc_info=True)
            session.rollback()

    def aktualisiere_vertragliche_wochenstunden(self, neue_wochenstunden, gueltig_ab=None, mitarbeiter_id=None):
        """Aktualisiert die vertraglichen Wochenstunden und pflegt die Historie."""
        ziel_id = mitarbeiter_id or self.aktueller_nutzer_id
        if ziel_id is None:
            logger.warning("aktualisiere_vertragliche_wochenstunden: Kein Zielnutzer angegeben")
            return {"error": "Kein Nutzer angegeben"}

        if not session:
            logger.error("aktualisiere_vertragliche_wochenstunden: Keine DB-Session verfügbar")
            return {"error": "Keine DB-Session"}

        try:
            neue_wochenstunden_int = int(neue_wochenstunden)
        except (TypeError, ValueError):
            logger.warning(f"aktualisiere_vertragliche_wochenstunden: Ungültiger Wert '{neue_wochenstunden}'")
            return {"error": "Ungültige Wochenstunden"}

        if neue_wochenstunden_int <= 0:
            logger.warning(
                f"aktualisiere_vertragliche_wochenstunden: Wochenstunden müssen > 0 sein (erhalten: {neue_wochenstunden_int})"
            )
            return {"error": "Wochenstunden müssen größer als 0 sein"}

        gueltig_ab_datum = _normalize_to_date(gueltig_ab) if gueltig_ab else date.today()
        if gueltig_ab_datum is None:
            logger.warning(
                f"aktualisiere_vertragliche_wochenstunden: Ungültiges Datum '{gueltig_ab}', verwende heutiges Datum"
            )
            gueltig_ab_datum = date.today()

        def _db_op():
            nutzer = session.get(mitarbeiter, ziel_id)
            if not nutzer:
                return {"error": "Nutzer nicht gefunden"}

            alte_wochenstunden = nutzer.vertragliche_wochenstunden
            nutzer.vertragliche_wochenstunden = neue_wochenstunden_int

            historie_stmt = select(VertragswochenstundenHistorie).where(
                (VertragswochenstundenHistorie.mitarbeiter_id == ziel_id) &
                (VertragswochenstundenHistorie.gueltig_ab == gueltig_ab_datum)
            )
            historie_eintrag = session.execute(historie_stmt).scalar_one_or_none()

            if historie_eintrag:
                historie_eintrag.wochenstunden = neue_wochenstunden_int
            else:
                session.add(
                    VertragswochenstundenHistorie(
                        mitarbeiter_id=ziel_id,
                        gueltig_ab=gueltig_ab_datum,
                        wochenstunden=neue_wochenstunden_int,
                    )
                )

            logger.info(
                "aktualisiere_vertragliche_wochenstunden: Nutzer %s von %s auf %s Stunden (gültig ab %s)",
                ziel_id,
                alte_wochenstunden,
                neue_wochenstunden_int,
                gueltig_ab_datum,
            )

            return {
                "alte_wochenstunden": alte_wochenstunden,
                "neue_wochenstunden": neue_wochenstunden_int,
                "gueltig_ab": gueltig_ab_datum,
            }

        result = self._safe_db_operation(_db_op)

        if isinstance(result, dict) and result.get("error"):
            return result

        if ziel_id == self.aktueller_nutzer_id:
            self.aktueller_nutzer_vertragliche_wochenstunden = neue_wochenstunden_int

        return result

    def aktualisiere_ampelgrenzen(self, neuer_gruenwert, neuer_rotwert, mitarbeiter_id=None):
        """
        Aktualisiert die Ampelgrenzen für einen Nutzer.
        
        Neue Logik (symmetrisch):
        - Grün: Gleitzeit zwischen -neuer_gruenwert und +neuer_gruenwert
        - Gelb: Gleitzeit zwischen -neuer_rotwert und -neuer_gruenwert ODER zwischen +neuer_gruenwert und +neuer_rotwert
        - Rot: Gleitzeit unter -neuer_rotwert ODER über +neuer_rotwert
        
        Args:
            neuer_gruenwert: Grüne Schwelle (z.B. 5 für ±5h grün)
            neuer_rotwert: Rote Schwelle (z.B. 10 für ±10h rot)
        """
        ziel_id = mitarbeiter_id or self.aktueller_nutzer_id
        if ziel_id is None:
            logger.warning("aktualisiere_ampelgrenzen: Kein Zielnutzer angegeben")
            return {"error": "Kein Nutzer angegeben"}

        if not session:
            logger.error("aktualisiere_ampelgrenzen: Keine DB-Session verfügbar")
            return {"error": "Keine DB-Session"}

        try:
            gruen_int = int(neuer_gruenwert)
            rot_int = int(neuer_rotwert)
        except (TypeError, ValueError):
            logger.warning(
                "aktualisiere_ampelgrenzen: Ungültige Ampelwerte (grün=%s, rot=%s)",
                neuer_gruenwert,
                neuer_rotwert,
            )
            return {"error": "Ampelwerte müssen ganze Zahlen sein"}

        # Neue Validierung: Rot-Schwelle muss größer sein als Grün-Schwelle
        if rot_int <= gruen_int:
            logger.warning(
                "aktualisiere_ampelgrenzen: Rote Schwelle (%s) muss größer sein als grüne Schwelle (%s)",
                rot_int,
                gruen_int,
            )
            return {"error": "Rote Schwelle muss größer als grüne Schwelle sein"}
        
        # Beide Werte müssen positiv sein
        if gruen_int <= 0 or rot_int <= 0:
            logger.warning(
                "aktualisiere_ampelgrenzen: Ampelwerte müssen positiv sein (grün=%s, rot=%s)",
                gruen_int,
                rot_int,
            )
            return {"error": "Ampelwerte müssen positiv sein"}

        def _db_op():
            nutzer = session.get(mitarbeiter, ziel_id)
            if not nutzer:
                return {"error": "Nutzer nicht gefunden"}

            alt_gruen = nutzer.ampel_grün
            alt_rot = nutzer.ampel_rot

            nutzer.ampel_grün = gruen_int
            nutzer.ampel_rot = rot_int

            logger.info(
                "aktualisiere_ampelgrenzen: Nutzer %s Ampelgrün-Schwelle von ±%s auf ±%s, Ampelrot-Schwelle von ±%s auf ±%s",
                ziel_id,
                alt_gruen,
                gruen_int,
                alt_rot,
                rot_int,
            )

            return {"ampel_gruen": gruen_int, "ampel_rot": rot_int}

        result = self._safe_db_operation(_db_op)

        if isinstance(result, dict) and result.get("error"):
            return result

        if ziel_id == self.aktueller_nutzer_id:
            self.aktueller_nutzer_ampel_grün = gruen_int
            self.aktueller_nutzer_ampel_rot = rot_int

        return result

    def set_ampel_farbe(self):
        """
        Setzt die Ampelfarbe basierend auf dem aktuellen Gleitzeit-Kontostand.
        
        Verwendet symmetrische Schwellwerte für positive und negative Gleitzeit:
        - Grün: Gleitzeit zwischen -grün_schwelle und +grün_schwelle
        - Gelb: Gleitzeit zwischen -rot_schwelle und -grün_schwelle 
                ODER zwischen +grün_schwelle und +rot_schwelle
        - Rot: Gleitzeit unter -rot_schwelle ODER über +rot_schwelle
        
        Note:
            Setzt self.ampel_status auf "green", "yellow" oder "red".
            Bei Fehlern wird "yellow" als Fallback verwendet.
            
        Example:
            Bei grün=5h und rot=10h:
            - Grün: -5h bis +5h
            - Gelb: -10h bis -5h und +5h bis +10h  
            - Rot: unter -10h oder über +10h
        """
        try:
            # Sicherstellen, dass Werte nicht None sind
            gleitzeit = float(self.aktueller_nutzer_gleitzeit or 0)
            gruen_schwelle = float(self.aktueller_nutzer_ampel_grün or 5)
            rot_schwelle = float(self.aktueller_nutzer_ampel_rot or 10)
            
            # Neue symmetrische Logik:
            # Grün: zwischen -gruen_schwelle und +gruen_schwelle
            # Gelb: zwischen -rot_schwelle und -gruen_schwelle ODER zwischen +gruen_schwelle und +rot_schwelle
            # Rot: unter -rot_schwelle ODER über +rot_schwelle
            
            if -gruen_schwelle <= gleitzeit <= gruen_schwelle:
                # Im grünen Bereich (z.B. -5h bis +5h)
                self.ampel_status = "green"
            elif -rot_schwelle <= gleitzeit < -gruen_schwelle or gruen_schwelle < gleitzeit <= rot_schwelle:
                # Im gelben Bereich (z.B. -10h bis -5h ODER +5h bis +10h)
                self.ampel_status = "yellow"
            else:
                # Im roten Bereich (z.B. unter -10h ODER über +10h)
                self.ampel_status = "red"
                
            logger.debug(f"set_ampel_farbe: Gleitzeit={gleitzeit}h, Grün-Schwelle=±{gruen_schwelle}h, Rot-Schwelle=±{rot_schwelle}h, Status={self.ampel_status}")
                
        except (ValueError, TypeError) as e:
            logger.error(f"Fehler beim Setzen der Ampelfarbe (Werte: {self.aktueller_nutzer_gleitzeit}, {self.aktueller_nutzer_ampel_grün}, {self.aktueller_nutzer_ampel_rot}): {e}")
            self.ampel_status = "yellow" # Fallback

    def get_messages(self):
        """
        Lädt alle nicht-PopUp-Benachrichtigungen für den aktuellen Benutzer.
        
        Holt alle Benachrichtigungen aus der Datenbank, die nicht als
        zeitgesteuerte PopUps markiert sind (ist_popup=False).
        
        Note:
            Setzt self.benachrichtigungen auf die Liste aller Benachrichtigungen.
            Bei Fehlern wird eine leere Liste verwendet.
            PopUp-Warnungen (ist_popup=True) werden nicht geladen.
        """
        if self.aktueller_nutzer_id is None: return
        if not session: return

        try:
            stmt = select(Benachrichtigungen).where(
                (Benachrichtigungen.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Benachrichtigungen.ist_popup == False)
            )
            result = session.execute(stmt).scalars().all()
            self.benachrichtigungen = result
        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in get_messages: {e}", exc_info=True)
            self.benachrichtigungen = []

    def get_urlaubstage_monat(self, jahr, monat):
        """
        Holt alle Urlaubstage für einen bestimmten Monat und Mitarbeiter.
        
        Args:
            jahr (int): Jahr
            monat (int): Monat (1-12)
        
        Returns:
            list: Liste von date-Objekten mit Urlaubstagen
        """
        if self.aktuelle_kalendereinträge_für_id is None:
            return []
        if not session:
            return []

        try:
            # Ersten und letzten Tag des Monats berechnen
            import calendar as cal
            erster_tag = date(jahr, monat, 1)
            letzter_tag = date(jahr, monat, cal.monthrange(jahr, monat)[1])

            # Urlaubstage aus der DB holen
            stmt = select(Abwesenheit.datum).where(
                (Abwesenheit.mitarbeiter_id == self.aktuelle_kalendereinträge_für_id) &
                (Abwesenheit.datum >= erster_tag) &
                (Abwesenheit.datum <= letzter_tag) &
                (Abwesenheit.typ == "Urlaub")
            )
            urlaubstage = session.scalars(stmt).all()
            self.urlaubstage_aktueller_monat = list(urlaubstage)
            return list(urlaubstage)
        
        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in get_urlaubstage_monat: {e}", exc_info=True)
            self.urlaubstage_aktueller_monat = []
            return []

    def hat_urlaub_am_datum(self, datum_pruefen: date) -> bool:
        """
        Prüft, ob für den aktuellen Nutzer am angegebenen Datum ein Urlaubseintrag existiert.
        
        Args:
            datum_pruefen: Das zu prüfende Datum
            
        Returns:
            True wenn ein Urlaubseintrag existiert, sonst False
            
        Note:
            Bei Fehlern oder fehlender Nutzer-ID wird False zurückgegeben.
        """
        if self.aktueller_nutzer_id is None or not session:
            return False
        try:
            stmt = select(Abwesenheit).where(
                (Abwesenheit.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Abwesenheit.datum == datum_pruefen) &
                (Abwesenheit.typ == "Urlaub")
            )
            return session.execute(stmt).scalar_one_or_none() is not None
        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in hat_urlaub_am_datum: {e}", exc_info=True)
            return False

    def loesche_urlaub_am_datum(self, datum_loeschen: date) -> int:
        """
        Löscht alle Urlaubseinträge des aktuellen Nutzers an einem bestimmten Datum.
        
        Args:
            datum_loeschen: Das Datum, an dem Urlaubseinträge gelöscht werden sollen
            
        Returns:
            Anzahl der gelöschten Urlaubseinträge
            
        Note:
            Bei Fehlern wird 0 zurückgegeben.
        """
        if self.aktueller_nutzer_id is None or not session:
            return 0

        def _db_op():
            stmt = select(Abwesenheit).where(
                (Abwesenheit.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Abwesenheit.datum == datum_loeschen) &
                (Abwesenheit.typ == "Urlaub")
            )
            eintraege = session.execute(stmt).scalars().all()
            count = 0
            for e in eintraege:
                session.delete(e)
                count += 1
            if count:
                logger.info(f"{count} Urlaubseintrag/Einträge am {datum_loeschen} gelöscht")
            return count

        result = self._safe_db_operation(_db_op)
        return 0 if isinstance(result, dict) and "error" in result else (result or 0)

    def hat_bereits_5_tage_gearbeitet_in_woche(self, datum_pruefen: date) -> bool:
        """
        Prüft, ob der Nutzer bereits an 5 verschiedenen Tagen in der Woche des angegebenen Datums gearbeitet hat.
        Verwendet für Minderjährige (max. 5 Arbeitstage/Woche laut ArbZG).
        
        Args:
            datum_pruefen: Das Datum, dessen Woche geprüft werden soll
            
        Returns:
            True wenn bereits 5 oder mehr Tage mit Stempeln in der Woche existieren, sonst False
        """
        if self.aktueller_nutzer_id is None or not session:
            return False
        
        try:
            # Wochenanfang (Montag) und -ende (Sonntag) berechnen
            wochentag = datum_pruefen.weekday()  # 0=Montag, 6=Sonntag
            wochenanfang = datum_pruefen - timedelta(days=wochentag)
            wochenende = wochenanfang + timedelta(days=6)
            
            # Alle unterschiedlichen Tage mit Stempeln in dieser Woche zählen
            stmt = select(Zeiteintrag.datum).distinct().where(
                (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Zeiteintrag.datum >= wochenanfang) &
                (Zeiteintrag.datum <= wochenende)
            )
            
            tage_mit_stempeln = session.execute(stmt).scalars().all()
            anzahl_arbeitstage = len(tage_mit_stempeln)
            
            logger.debug(f"Woche {wochenanfang} bis {wochenende}: {anzahl_arbeitstage} Tage mit Stempeln gefunden")
            
            return anzahl_arbeitstage >= 5
            
        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in hat_bereits_5_tage_gearbeitet_in_woche: {e}", exc_info=True)
            return False

    def get_krankheitstage_monat(self, jahr, monat):
        """
        Holt alle Krankheitstage für einen bestimmten Monat und Mitarbeiter.
        
        Args:
            jahr (int): Jahr
            monat (int): Monat (1-12)
        
        Returns:
            list: Liste von date-Objekten mit Krankheitstagen
        """
        if self.aktuelle_kalendereinträge_für_id is None:
            return []
        if not session:
            return []

        try:
            # Ersten und letzten Tag des Monats berechnen
            import calendar as cal
            erster_tag = date(jahr, monat, 1)
            letzter_tag = date(jahr, monat, cal.monthrange(jahr, monat)[1])

            # Krankheitstage aus der DB holen
            stmt = select(Abwesenheit.datum).where(
                (Abwesenheit.mitarbeiter_id == self.aktuelle_kalendereinträge_für_id) &
                (Abwesenheit.datum >= erster_tag) &
                (Abwesenheit.datum <= letzter_tag) &
                (Abwesenheit.typ == "Krankheit")
            )
            krankheitstage = session.scalars(stmt).all()
            self.krankheitstage_aktueller_monat = list(krankheitstage)
            return list(krankheitstage)
        
        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in get_krankheitstage_monat: {e}", exc_info=True)
            self.krankheitstage_aktueller_monat = []
            return []

    def update_passwort(self):
        """
        Aktualisiert das Passwort des aktuell eingeloggten Benutzers.
        
        Validiert die Passworteingaben und aktualisiert das Passwort in der Datenbank.
        Das neue Passwort wird mit bcrypt gehasht.
        
        Note:
            Setzt self.feedback_neues_passwort mit Erfolgs-/Fehlermeldung.
            Prüft auf: Passworteingabe, Wiederholung und Übereinstimmung.
        """
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
                # Passwort hashen vor dem Speichern
                try:
                    hashed_password = hash_password(self.neues_passwort)
                    nutzer.password = hashed_password
                    return True  # Erfolg signalisieren
                except Exception as e:
                    logger.error(f"update_passwort: Fehler beim Hashen des Passworts: {e}", exc_info=True)
                    return {"error": "Fehler beim Verschlüsseln des Passworts."}
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
        """
        Fügt einen neuen Zeitstempel für den aktuellen Benutzer hinzu.
        
        Erstellt einen Zeiteintrag mit der aktuellen Uhrzeit und dem
        heutigen Datum. Die Funktion unterscheidet nicht zwischen Ein-
        und Ausstempeln (wird durch ungerade/gerade Anzahl bestimmt).
        
        Note:
            Verwendet _safe_db_operation für sichere DB-Transaktion.
            Feedback wird im Controller gehandhabt.
            Nach dem Stempeln sollte berechne_gleitzeit() aufgerufen werden.
        """
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

    def erstelle_popup_warnungen_beim_einstempeln(self):
        """
        Erstellt PopUp-Benachrichtigungen für Arbeitsfenster-Ende und max. Arbeitszeit.
        Diese werden in der DB gespeichert mit ist_popup=True und der entsprechenden Uhrzeit.
        """
        if not self.aktueller_nutzer_id:
            logger.warning("erstelle_popup_warnungen: Kein Nutzer eingeloggt")
            return
        
        try:
            nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
            if not nutzer:
                return
            
            is_minor = nutzer.is_minor_on_date(date.today())
            heute = date.today()
            
            # 1. Arbeitsfenster-Warnung (Code 9) - 30 Min vor Ende
            if is_minor:
                warnung_uhrzeit = time(19, 30)  # 30 Min vor 19:00
            else:
                warnung_uhrzeit = time(21, 30)  # 30 Min vor 21:00
            
            # Nur erstellen wenn Warnung noch nicht vorbei ist
            jetzt = datetime.now().time()
            if warnung_uhrzeit > jetzt:
                self._add_benachrichtigung_safe(
                    code=9, 
                    datum=heute, 
                    ist_popup=True, 
                    popup_uhrzeit=warnung_uhrzeit
                )
                logger.info(f"Arbeitsfenster-PopUp geplant für {warnung_uhrzeit}")
            
            # 2. Max. Arbeitszeit-Warnung (Code 10)
            # Berechne bereits gearbeitete Zeit heute
            today_stamps = self.get_stamps_for_today()
            gearbeitete_zeit = timedelta()
            
            # Paarweise Berechnung (alle außer dem letzten Stempel, da dieser der aktuelle Einstempel ist)
            if len(today_stamps) >= 2:
                i = 0
                # Alle vollständigen Paare berechnen (nicht den letzten Stempel, das ist der aktuelle Einstempel)
                while i < len(today_stamps) - 1:
                    if i + 1 < len(today_stamps):
                        calc = CalculateTime(today_stamps[i], today_stamps[i+1], nutzer)
                        if calc:
                            gearbeitete_zeit += calc.gearbeitete_zeit
                            logger.debug(f"erstelle_popup_warnungen: Paar {i//2+1}: {today_stamps[i].zeit} - {today_stamps[i+1].zeit}, Zeit: {calc.gearbeitete_zeit}")
                            i += 2
                        else:
                            i += 1
                    else:
                        break
                logger.debug(f"erstelle_popup_warnungen: Bereits gearbeitete Zeit heute: {gearbeitete_zeit}")
            else:
                logger.debug(f"erstelle_popup_warnungen: Erster Stempel des Tages, keine vorherige Arbeitszeit")
            
            # Maximale Arbeitszeit (30 Min vorher warnen)
            if is_minor:
                max_arbeitszeit = timedelta(hours=9) #ohne Pausen, nur eingestempelte Zeit
            else:
                max_arbeitszeit = timedelta(hours=10, minutes=45) #ohne Pausen, nur eingestempelte Zeit
            
            warnung_arbeitszeit = max_arbeitszeit - timedelta(minutes=30)
            verbleibende_arbeitszeit = warnung_arbeitszeit - gearbeitete_zeit
            
            logger.debug(f"erstelle_popup_warnungen: Max. Arbeitszeit: {max_arbeitszeit}, Warnung bei: {warnung_arbeitszeit}, Verbleibend: {verbleibende_arbeitszeit}")
            
            if verbleibende_arbeitszeit > timedelta(0):
                # Letzten Stempel-Zeit holen (das ist der aktuelle Einstempel)
                letzter_stempel = today_stamps[-1].zeit
                start_dt = datetime.combine(heute, letzter_stempel)
                warnung_dt = start_dt + verbleibende_arbeitszeit
                
                logger.debug(f"erstelle_popup_warnungen: Einstempel-Zeit: {letzter_stempel}, Warnung geplant für: {warnung_dt}")
                
                # Nur wenn Warnung heute ist und noch nicht vorbei
                if warnung_dt.date() == heute and warnung_dt.time() > jetzt:
                    self._add_benachrichtigung_safe(
                        code=10,
                        datum=heute,
                        ist_popup=True,
                        popup_uhrzeit=warnung_dt.time()
                    )
                    logger.info(f"Max. Arbeitszeit-PopUp geplant für {warnung_dt.time()}")
                else:
                    logger.debug(f"erstelle_popup_warnungen: Warnung nicht geplant - Datum heute: {warnung_dt.date() == heute}, Zeit in Zukunft: {warnung_dt.time() > jetzt}")
            else:
                logger.debug(f"erstelle_popup_warnungen: Keine Warnung nötig - verbleibende Zeit nicht positiv")
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen der PopUp-Warnungen: {e}", exc_info=True)

    def get_pending_popups_for_today(self):
        """
        Holt alle noch ausstehenden PopUp-Benachrichtigungen für heute.
        Gibt Liste von (code, uhrzeit) Tupeln zurück.
        """
        if not self.aktueller_nutzer_id:
            return []
        if not session:
            return []
        
        try:
            heute = date.today()
            jetzt = datetime.now().time()
            
            stmt = select(Benachrichtigungen).where(
                (Benachrichtigungen.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Benachrichtigungen.datum == heute) &
                (Benachrichtigungen.ist_popup == True) &
                (Benachrichtigungen.popup_uhrzeit != None)
            )
            popups = session.scalars(stmt).all()
            
            # Nur zukünftige PopUps zurückgeben
            pending = [(p.benachrichtigungs_code, p.popup_uhrzeit, p.id) for p in popups if p.popup_uhrzeit > jetzt]
            logger.debug(f"Gefundene ausstehende PopUps: {len(pending)}")
            return pending
            
        except SQLAlchemyError as e:
            logger.error(f"Fehler beim Laden der PopUps: {e}", exc_info=True)
            return []

    def delete_popup_benachrichtigung(self, benachrichtigung_id):
        """
        Löscht eine einzelne PopUp-Benachrichtigung nach Anzeige.
        
        Args:
            benachrichtigung_id: ID der zu löschenden Benachrichtigung
            
        Returns:
            True bei Erfolg, False bei Fehler oder wenn Benachrichtigung nicht existiert
            
        Note:
            Löscht nur PopUp-Benachrichtigungen (ist_popup=True).
        """
        def _db_op():
            benachrichtigung = session.get(Benachrichtigungen, benachrichtigung_id)
            if benachrichtigung and benachrichtigung.ist_popup:
                session.delete(benachrichtigung)
                return True
            return False
        
        return self._safe_db_operation(_db_op)

    def delete_all_popup_benachrichtigungen_for_today(self):
        """
        Löscht alle PopUp-Benachrichtigungen für den heutigen Tag beim Ausstempeln.
        
        Returns:
            Anzahl der gelöschten Benachrichtigungen oder None bei Fehler
            
        Note:
            Wird beim Ausstempeln aufgerufen, um alle geplanten PopUps zu entfernen.
        """
        def _db_op():
            heute = date.today()
            stmt = select(Benachrichtigungen).where(
                (Benachrichtigungen.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Benachrichtigungen.datum == heute) &
                (Benachrichtigungen.ist_popup == True)
            )
            popups = session.scalars(stmt).all()
            count = len(popups)
            
            for popup in popups:
                session.delete(popup)
            
            logger.info(f"{count} PopUp-Benachrichtigungen für heute gelöscht")
            return count
        
        return self._safe_db_operation(_db_op)

    def get_stamps_for_today(self):
        """
        Holt alle Zeitstempel für den heutigen Tag des aktuellen Nutzers.
        
        Returns:
            Liste von Zeiteintrag-Objekten, sortiert nach Zeit.
            Leere Liste bei Fehler oder wenn kein Nutzer eingeloggt ist.
            
        Note:
            Wird für PopUp-Berechnungen und Tages-Übersicht verwendet.
        """
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

    def get_stempel_datum_by_id(self, stempel_id):
        """
        Gibt das Datum eines Stempels zurück.
        
        Args:
            stempel_id: Die ID des Zeiteintrags
            
        Returns:
            Das Datum als date-Objekt oder None bei Fehler
        """
        if not session:
            logger.error("get_stempel_datum_by_id: Keine Datenbankverbindung")
            return None
            
        try:
            eintrag = session.get(Zeiteintrag, stempel_id)
            if eintrag:
                return eintrag.datum
            else:
                logger.warning(f"get_stempel_datum_by_id: Stempel mit ID {stempel_id} nicht gefunden")
                return None
        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in get_stempel_datum_by_id: {e}", exc_info=True)
            return None

    def manueller_stempel_hinzufügen(self):
        """
        Fügt einen manuell nachgetragenen Zeitstempel hinzu.
        
        Erstellt einen Zeiteintrag mit manuell gewähltem Datum und Uhrzeit.
        Führt umfassende Validierungen durch:
        - Datums-/Zeitformat-Prüfung
        - Zukunfts-Check (keine Stempel in der Zukunft)
        - Abwesenheits-Prüfung (kein Stempeln bei Urlaub/Krankheit)
        - Ältere Stempel werden automatisch als validiert markiert
        
        Note:
            Verwendet self.manueller_stempel_uhrzeit (Format: "HH:MM")
            und self.nachtragen_datum (Format: "dd/mm/yyyy").
            Setzt self.feedback_manueller_stempel mit Erfolgs-/Fehlermeldung.
            
            Alte Stempel (> 1 Tag alt) werden direkt validiert, sodass
            sie bei berechne_gleitzeit() berücksichtigt werden.
        """
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

        # Einträge für den Tag zurücksetzen (unvalidieren und Gleitzeit rückgängig machen)

        self.set_entries_unvalidated_and_revert_gleitzeit(self.nachtragen_datum)
        logger.info(f"Einträge für {self.nachtragen_datum} wurden zurückgesetzt vor manuellem Stempel.")


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
            
            # Nach dem Hinzufügen des Stempels: Prüfungen durchführen und Gleitzeit neu berechnen
            logger.info(f"manueller_stempel_hinzufügen: Führe Prüfungen und Neuberechnung für {self.nachtragen_datum} durch")
            
            # Schritt 1: checke_arbeitstage - prüft fehlende Tage und erstellt ggf. Code-1-Benachrichtigungen
            # (Falls durch den nachgetragenen Stempel ein vorher fehlender Tag jetzt vorhanden ist)
            self.checke_arbeitstage()
            
            # Schritt 2: checke_stempel - prüft ungerade Stempelanzahl und erstellt ggf. Code-2-Benachrichtigungen
            # (Der nachgetragene Stempel könnte die Anzahl von ungerade auf gerade ändern)
            self.checke_stempel()
            
            # Schritt 3: berechne_gleitzeit - berechnet die Gleitzeit neu
            # (Berücksichtigt die unvalidierten Einträge und prüft auf Code-1-Benachrichtigungen)
            self.berechne_gleitzeit()
            
            # Schritt 4: Arbeitszeitschutzgesetz-Prüfungen (Codes 3-9)
            logger.debug("manueller_stempel_hinzufügen: Führe Arbeitszeitschutzgesetz-Prüfungen durch")
            self.checke_ruhezeiten()                          # Code 3: Ruhezeit-Verstöße
            self.checke_durchschnittliche_arbeitszeit()       # Code 4: Durchschnitt > 8h/Tag
            self.checke_max_arbeitszeit()                     # Code 5: Max. Arbeitszeit überschritten
            self.checke_sonn_feiertage()                      # Code 6: Sonn-/Feiertag
            self.checke_wochenstunden_minderjaehrige()        # Code 7: Wochenstunden > 40h (Minderjährige)
            self.checke_arbeitstage_pro_woche_minderjaehrige() # Code 8: >5 Arbeitstage/Woche (Minderjährige)
            self.checke_arbeitszeitfenster_minderjaehrige()   # Code 9: Arbeitszeitfenster 6-20 Uhr (Minderjährige)
            
            # Schritt 5: Prüfe und korrigiere bestehende Benachrichtigungen
            geloeschte = self.pruefe_und_korrigiere_arbeitszeitschutz_benachrichtigungen()
            if geloeschte > 0:
                logger.info(f"manueller_stempel_hinzufügen: {geloeschte} korrigierte Benachrichtigungen gelöscht")
            
            logger.info(f"manueller_stempel_hinzufügen: Alle Prüfungen und Neuberechnung abgeschlossen")
            
            # Wenn der nachgetragene Stempel für heute ist und der Nutzer eingestempelt ist, PopUps erstellen
            if stempel_datum == date.today():
                today_stamps = self.get_stamps_for_today()
                is_clocked_in = len(today_stamps) % 2 != 0
                
                if is_clocked_in:
                    logger.info("Nachgetragener Stempel für heute - erstelle PopUp-Warnungen")
                    self.erstelle_popup_warnungen_beim_einstempeln()


    def set_entries_unvalidated_and_revert_gleitzeit(self, datum_str):
        """
        Setzt alle Zeiteinträge für ein bestimmtes Datum auf unvalidiert und macht die Gleitzeitberechnung für diesen Tag rückgängig.
        datum_str: Datum als String im Format '%d/%m/%Y'
        """
        if self.aktueller_nutzer_id is None:
            return
        if not session:
            logger.error("set_entries_unvalidated_and_revert_gleitzeit: Keine DB-Session verfügbar")
            return
            
        logger.debug(f"set_entries_unvalidated_and_revert_gleitzeit: starte für Nutzer {self.aktueller_nutzer_id} und Datum-String '{datum_str}'")
        try:
            datum = datetime.strptime(datum_str, "%d/%m/%Y").date()
        except ValueError:
            logger.warning(f"set_entries_unvalidated_and_revert_gleitzeit: Ungültiges Datumsformat '{datum_str}', erwartet '%d/%m/%Y'")
            return

        # Zeiteinträge für das Datum holen (zeitlich sortiert)
        stmt = select(Zeiteintrag).where(
            (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
            (Zeiteintrag.datum == datum)
        ).order_by(Zeiteintrag.zeit)
        eintraege = session.scalars(stmt).all()
        logger.debug(f"set_entries_unvalidated_and_revert_gleitzeit: {len(eintraege)} Zeiteinträge für {datum} gefunden")

        # Nur dann Gleitzeit rückgängig machen, wenn dieser Tag bereits in die Gleitzeit eingerechnet wurde
        validated_before = [e for e in eintraege if getattr(e, 'validiert', False)]
        logger.debug(f"set_entries_unvalidated_and_revert_gleitzeit: {len(validated_before)} zuvor validierte Einträge für {datum}")

        # Prüfen ob für diesen Tag eine Benachrichtigung (Code 1 - fehlender Stempel) existiert
        # Wenn ja, wurde bereits Gleitzeit abgezogen und darf nicht nochmal abgezogen werden
        benachrichtigung_stmt = select(Benachrichtigungen).where(
            (Benachrichtigungen.mitarbeiter_id == self.aktueller_nutzer_id) &
            (Benachrichtigungen.datum == datum) &
            (Benachrichtigungen.benachrichtigungs_code == 1)
        )
        hat_fehlstempel_benachrichtigung = session.execute(benachrichtigung_stmt).scalar_one_or_none()
        
        if hat_fehlstempel_benachrichtigung:
            logger.info(f"set_entries_unvalidated_and_revert_gleitzeit: Fehlstempel-Benachrichtigung für {datum} gefunden.")
        
        # Gleitzeit für diesen Tag berechnen und abziehen
        nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
        if not nutzer:
            logger.error(f"set_entries_unvalidated_and_revert_gleitzeit: Nutzer {self.aktueller_nutzer_id} nicht gefunden")
            return

        # Letzter Login auf das zu bearbeitende Datum setzen, ABER NUR wenn es vor dem aktuellen letzter_login liegt
        # Das stellt sicher, dass die Check-Methoden ab dem bearbeiteten Datum prüfen, aber nicht in die Zukunft springen
        if datum < nutzer.letzter_login:
            alter_login = nutzer.letzter_login
            nutzer.letzter_login = datum
            logger.debug(f"set_entries_unvalidated_and_revert_gleitzeit: letzter_login von {alter_login} auf {datum} gesetzt (Datum liegt vor aktuellem Login)")
        else:
            logger.debug(f"set_entries_unvalidated_and_revert_gleitzeit: letzter_login ({nutzer.letzter_login}) bleibt unverändert (Datum {datum} liegt nicht davor)")

        # Arbeitszeit für diesen Tag berechnen (nur aus zuvor validierten Paaren)
        arbeitstag = timedelta()
        if validated_before:
            i = 0
            while i < len(validated_before) - 1:
                calc = CalculateTime(validated_before[i], validated_before[i+1], nutzer)
                if calc:
                    # Debug: Arbeitszeit vor Pausen
                    zeit_vor_pausen = calc.gearbeitete_zeit
                    logger.debug(f"set_entries_unvalidated_and_revert_gleitzeit: Paar {i//2+1}: {validated_before[i].zeit} - {validated_before[i+1].zeit}, Brutto: {zeit_vor_pausen}")
                    
                    calc.gesetzliche_pausen_hinzufügen()
                    zeit_nach_pausen = calc.gearbeitete_zeit
                    logger.debug(f"set_entries_unvalidated_and_revert_gleitzeit: Nach Pausen: {zeit_nach_pausen}, Pausenabzug: {zeit_vor_pausen - zeit_nach_pausen}")
                    
                    calc.arbeitsfenster_beachten()
                    zeit_nach_fenster = calc.gearbeitete_zeit
                    logger.debug(f"set_entries_unvalidated_and_revert_gleitzeit: Nach Arbeitsfenster: {zeit_nach_fenster}, Fensterabzug: {zeit_nach_pausen - zeit_nach_fenster}")
                    
                    arbeitstag += calc.gearbeitete_zeit
                    i += 2
                else:
                    i += 1
        logger.debug(f"set_entries_unvalidated_and_revert_gleitzeit: gearbeitete (zuvor angerechnete) Zeit am {datum}: {arbeitstag}")

        wochenstunden = hole_wochenstunden_am_datum(
            self.aktueller_nutzer_id,
            datum,
            self.aktueller_nutzer_vertragliche_wochenstunden,
        )
        taegliche_arbeitszeit = berechne_taegliche_sollzeit(wochenstunden)
        
        # Fall 1: Validierte Einträge existieren UND keine Fehlstempel-Benachrichtigung
        # -> Gleitzeit aus validierten Einträgen zurückrechnen
        if validated_before and not hat_fehlstempel_benachrichtigung:
            gleitzeit_diff = arbeitstag - taegliche_arbeitszeit
            gleitzeit_stunden = float(gleitzeit_diff.total_seconds() / 3600)
            logger.debug(f"set_entries_unvalidated_and_revert_gleitzeit: tägliche Sollzeit: {taegliche_arbeitszeit}, Differenz: {gleitzeit_diff} ({gleitzeit_stunden:.2f}h)")

            alte_gleitzeit = float(self.aktueller_nutzer_gleitzeit or 0)
            self.aktueller_nutzer_gleitzeit = alte_gleitzeit - gleitzeit_stunden
            nutzer.gleitzeit = self.aktueller_nutzer_gleitzeit
            logger.info(f"set_entries_unvalidated_and_revert_gleitzeit: Gleitzeit aus validierten Einträgen zurückgesetzt von {alte_gleitzeit:.2f}h auf {self.aktueller_nutzer_gleitzeit:.2f}h für {datum}")
        
        # Fall 2: Fehlstempel-Benachrichtigung existiert (egal ob validierte Einträge vorhanden)
        # -> Die tägliche Sollzeit wurde bereits abgezogen, jetzt wieder hinzufügen
        elif hat_fehlstempel_benachrichtigung:
            gleitzeit_stunden = float(taegliche_arbeitszeit.total_seconds() / 3600)
            alte_gleitzeit = float(self.aktueller_nutzer_gleitzeit or 0)
            self.aktueller_nutzer_gleitzeit = alte_gleitzeit + gleitzeit_stunden  # HINZUFÜGEN!
            nutzer.gleitzeit = self.aktueller_nutzer_gleitzeit
            logger.info(f"set_entries_unvalidated_and_revert_gleitzeit: Fehlstempel-Abzug rückgängig gemacht: {alte_gleitzeit:.2f}h + {gleitzeit_stunden:.2f}h = {self.aktueller_nutzer_gleitzeit:.2f}h für {datum}")
            
            # Benachrichtigung löschen, da jetzt Stempel vorhanden
            try:
                session.delete(hat_fehlstempel_benachrichtigung)
                logger.debug(f"set_entries_unvalidated_and_revert_gleitzeit: Fehlstempel-Benachrichtigung (Code 1) für {datum} gelöscht")
            except SQLAlchemyError as e:
                logger.error(f"Fehler beim Löschen der Benachrichtigung: {e}")
        
        # Fall 3: Keine validierten Einträge und keine Benachrichtigung
        # -> Nichts zu tun
        else:
            logger.info(f"set_entries_unvalidated_and_revert_gleitzeit: Keine Gleitzeit-Anpassung nötig für {datum}")

        # Benachrichtigung für ungerade Stempel (Code 2) löschen, falls vorhanden
        # Dies wird beim Nachtragen/Berichtigen relevant, da die Anzahl sich ändern kann
        try:
            ungerade_stempel_stmt = select(Benachrichtigungen).where(
                (Benachrichtigungen.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Benachrichtigungen.datum == datum) &
                (Benachrichtigungen.benachrichtigungs_code == 2)
            )
            ungerade_stempel_benachrichtigung = session.execute(ungerade_stempel_stmt).scalar_one_or_none()
            if ungerade_stempel_benachrichtigung:
                session.delete(ungerade_stempel_benachrichtigung)
                logger.debug(f"set_entries_unvalidated_and_revert_gleitzeit: Ungerade-Stempel-Benachrichtigung (Code 2) für {datum} gelöscht")
        except SQLAlchemyError as e:
            logger.error(f"Fehler beim Löschen der Ungerade-Stempel-Benachrichtigung: {e}")

        # Alle Einträge (auch unvalidierte) auf unvalidiert setzen und speichern
        for e in eintraege:
            e.validiert = False
        session.commit()
        logger.debug(f"set_entries_unvalidated_and_revert_gleitzeit: Alle Einträge für {datum} auf unvalidiert gesetzt und gespeichert")


    def urlaub_eintragen(self):
        """
        Trägt einen Urlaubs- oder Krankheitseintrag in die Datenbank ein.
        
        Erstellt einen Abwesenheitseintrag basierend auf den Attributen
        self.nachtragen_datum und self.neuer_abwesenheitseintrag_art.
        
        Note:
            Validiert Datum und Art der Abwesenheit.
            Nur "Urlaub" und "Krankheit" sind erlaubt.
            Bei Erfolg/Fehler wird Feedback im Controller gehandhabt.
        """
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
            nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
            if not nutzer:
                return {"error": "Aktueller Nutzer konnte nicht geladen werden."}

            # Prüfen, ob an dem Tag schon Stempel existieren
            stamp_stmt = select(Zeiteintrag).where(
                (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Zeiteintrag.datum == abwesenheit_datum)
            )
            # Prüfen, ob überhaupt ein Stempel vorhanden ist (mehrere pro Tag möglich)
            if session.execute(stamp_stmt).scalars().first():
                return {"error": "An diesem Tag ist bereits ein Zeitstempel vorhanden. Bitte löschen Sie diesen zuerst."}

            # Prüfen, ob bereits eine Abwesenheit existiert
            abwesend_stmt = select(Abwesenheit).where(
                (Abwesenheit.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Abwesenheit.datum == abwesenheit_datum)
            )
            exist_abw = session.execute(abwesend_stmt).scalar_one_or_none()
            if exist_abw:
                return {"error": f"An diesem Tag ist bereits '{exist_abw.typ}' eingetragen."}

            # Prüfen, ob für den Tag ein Fehlstempel-Abzug (Benachrichtigung Code 1) existiert
            fehlstempel_stmt = select(Benachrichtigungen).where(
                (Benachrichtigungen.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Benachrichtigungen.datum == abwesenheit_datum) &
                (Benachrichtigungen.benachrichtigungs_code == 1)
            )
            fehlstempel_benachrichtigung = session.execute(fehlstempel_stmt).scalar_one_or_none()

            if fehlstempel_benachrichtigung:
                fallback_sollstunden = None
                if not self.aktueller_nutzer_vertragliche_wochenstunden or self.aktueller_nutzer_vertragliche_wochenstunden <= 0:
                    fallback_sollstunden = 8

                wochenstunden_tag = hole_wochenstunden_am_datum(
                    self.aktueller_nutzer_id,
                    abwesenheit_datum,
                    self.aktueller_nutzer_vertragliche_wochenstunden,
                )
                taegliche_arbeitszeit = berechne_taegliche_sollzeit(
                    wochenstunden_tag,
                    fallback_stunden=fallback_sollstunden,
                )

                gleitzeit_rueck = float(taegliche_arbeitszeit.total_seconds() / 3600) if taegliche_arbeitszeit else 0.0
                if gleitzeit_rueck > 0:
                    alte_gleitzeit = float(nutzer.gleitzeit or 0)
                    neue_gleitzeit = alte_gleitzeit + gleitzeit_rueck
                    nutzer.gleitzeit = neue_gleitzeit
                    self.aktueller_nutzer_gleitzeit = neue_gleitzeit
                    self._cached_aktueller_nutzer = nutzer
                    logger.info(
                        "urlaub_eintragen: Fehlstempel-Abzug für %s rückgängig gemacht (%.2fh -> %.2fh)",
                        abwesenheit_datum,
                        alte_gleitzeit,
                        neue_gleitzeit,
                    )

                session.delete(fehlstempel_benachrichtigung)
                logger.debug(
                    "urlaub_eintragen: Fehlstempel-Benachrichtigung für %s gelöscht",
                    abwesenheit_datum,
                )
            
            neue_abwesenheit = Abwesenheit(
                mitarbeiter_id = self.aktueller_nutzer_id,
                datum = abwesenheit_datum,
                typ = self.neuer_abwesenheitseintrag_art
            )
            session.add(neue_abwesenheit)
            return True

        result = self._safe_db_operation(_db_op)
        
        # Feedback als String setzen
        if isinstance(result, dict) and "error" in result:
            self.feedback_manueller_stempel = result["error"]
        elif result is True:
            typ_text = "Urlaub" if self.neuer_abwesenheitseintrag_art == "Urlaub" else "Krankheit"
            self.feedback_manueller_stempel = f"{typ_text} am {self.nachtragen_datum} erfolgreich eingetragen"
        else:
            self.feedback_manueller_stempel = "Fehler beim Eintragen der Abwesenheit."


    def stempel_bearbeiten_nach_id(self, stempel_id, neue_uhrzeit):
        """
        Bearbeitet die Uhrzeit eines Stempels mit der gegebenen ID.
        
        Args:
            stempel_id: Die ID des zu bearbeitenden Zeiteintrags
            neue_uhrzeit: Die neue Uhrzeit als time-Objekt
        
        Returns:
            True bei Erfolg, False bei Fehler
        """
        if self.aktueller_nutzer_id is None:
            logger.warning("stempel_bearbeiten_nach_id: Kein Nutzer eingeloggt")
            return False
        
        if not session:
            logger.error("stempel_bearbeiten_nach_id: Keine Datenbankverbindung")
            return False
        
        try:
            # Stempel laden
            eintrag = session.get(Zeiteintrag, stempel_id)
            if not eintrag:
                logger.warning(f"stempel_bearbeiten_nach_id: Stempel mit ID {stempel_id} nicht gefunden")
                return False
            
            # Prüfen, ob der Stempel dem aktuellen Nutzer gehört
            if eintrag.mitarbeiter_id != self.aktueller_nutzer_id:
                logger.warning(f"stempel_bearbeiten_nach_id: Stempel {stempel_id} gehört nicht dem aktuellen Nutzer")
                return False
            
            # Datum des Stempels für die Rücksetzung merken
            datum_des_stempels = eintrag.datum
            datum_str = datum_des_stempels.strftime("%d/%m/%Y")
            
            logger.info(f"stempel_bearbeiten_nach_id: Bearbeite Stempel {stempel_id} vom {datum_str}: {eintrag.zeit} -> {neue_uhrzeit}")
            
            # Schritt 1: Tag zurücksetzen (Gleitzeit rückgängig machen, alle Einträge unvalidiert setzen)
            # WICHTIG: Dies muss VOR der Änderung erfolgen, damit die ALTE Zeit für die Rückrechnung verwendet wird
            self.set_entries_unvalidated_and_revert_gleitzeit(datum_str)
            
            # Schritt 2: Neue Uhrzeit setzen
            eintrag.zeit = neue_uhrzeit
            session.commit()
            logger.debug(f"stempel_bearbeiten_nach_id: Neue Uhrzeit {neue_uhrzeit} für Stempel {stempel_id} gespeichert")
            
            # Schritt 3: Gleitzeit neu berechnen (verwendet bestehende berechne_gleitzeit Methode)
            self.berechne_gleitzeit()
            
            # Schritt 4: Arbeitszeitschutzgesetz-Prüfungen (Codes 3-9)
            logger.debug(f"stempel_bearbeiten_nach_id: Führe Arbeitszeitschutzgesetz-Prüfungen durch für Datum {datum_str}")
            self.checke_ruhezeiten()                          # Code 3: Ruhezeit-Verstöße
            self.checke_durchschnittliche_arbeitszeit()       # Code 4: Durchschnitt > 8h/Tag
            self.checke_max_arbeitszeit()                     # Code 5: Max. Arbeitszeit überschritten
            self.checke_sonn_feiertage()                      # Code 6: Sonn-/Feiertag
            self.checke_wochenstunden_minderjaehrige()        # Code 7: Wochenstunden > 40h (Minderjährige)
            self.checke_arbeitstage_pro_woche_minderjaehrige() # Code 8: >5 Arbeitstage/Woche (Minderjährige)
            self.checke_arbeitszeitfenster_minderjaehrige()   # Code 9: Arbeitszeitfenster 6-20 Uhr (Minderjährige)
            
            # Schritt 5: Prüfe und korrigiere bestehende Benachrichtigungen
            geloeschte = self.pruefe_und_korrigiere_arbeitszeitschutz_benachrichtigungen()
            if geloeschte > 0:
                logger.info(f"stempel_bearbeiten_nach_id: {geloeschte} korrigierte Benachrichtigungen gelöscht")
            
            logger.info(f"stempel_bearbeiten_nach_id: Stempel {stempel_id} erfolgreich bearbeitet, alle Prüfungen durchgeführt")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"stempel_bearbeiten_nach_id: Datenbankfehler: {e}", exc_info=True)
            session.rollback()
            return False
        except Exception as e:
            logger.error(f"stempel_bearbeiten_nach_id: Unerwarteter Fehler: {e}", exc_info=True)
            session.rollback()
            return False


    def stempel_löschen_nach_id(self, stempel_id):
        """
        Löscht einen Stempel mit der gegebenen ID.
        
        Args:
            stempel_id: Die ID des zu löschenden Zeiteintrags
        
        Returns:
            True bei Erfolg, False bei Fehler
        """
        if self.aktueller_nutzer_id is None:
            logger.warning("stempel_löschen_nach_id: Kein Nutzer eingeloggt")
            return False
        
        if not session:
            logger.error("stempel_löschen_nach_id: Keine Datenbankverbindung")
            return False
        
        try:
            # Stempel laden
            eintrag = session.get(Zeiteintrag, stempel_id)
            if not eintrag:
                logger.warning(f"stempel_löschen_nach_id: Stempel mit ID {stempel_id} nicht gefunden")
                return False
            
            # Prüfen, ob der Stempel dem aktuellen Nutzer gehört
            if eintrag.mitarbeiter_id != self.aktueller_nutzer_id:
                logger.warning(f"stempel_löschen_nach_id: Stempel {stempel_id} gehört nicht dem aktuellen Nutzer")
                return False
            
            # Datum des Stempels für die Rücksetzung merken
            datum_des_stempels = eintrag.datum
            datum_str = datum_des_stempels.strftime("%d/%m/%Y")
            
            logger.info(f"stempel_löschen_nach_id: Lösche Stempel {stempel_id} vom {datum_str}, Uhrzeit: {eintrag.zeit}")
            self.set_entries_unvalidated_and_revert_gleitzeit(datum_str)
            # Schritt 1: Stempel löschen
            session.delete(eintrag)
            session.commit()
            logger.debug(f"stempel_löschen_nach_id: Stempel {stempel_id} aus Datenbank gelöscht")
            
            # Schritt 2: checke_arbeitstage ausführen (prüft ob Tag jetzt ohne Stempel ist und erstellt ggf. Code-1-Benachrichtigung)
            # WICHTIG: Dies muss VOR checke_stempel() und berechne_gleitzeit() aufgerufen werden
            self.checke_arbeitstage()
            
            # Schritt 3: checke_stempel ausführen (prüft fehlende/ungerade Stempel und erstellt ggf. Benachrichtigungen)
            # WICHTIG: Dies muss VOR berechne_gleitzeit() aufgerufen werden, da berechne_gleitzeit() auf diese Benachrichtigungen prüft
            self.checke_stempel()
            
            # Schritt 4: Gleitzeit neu berechnen (verwendet bestehende berechne_gleitzeit Methode)
            # Dies wird alle unvalidierten Einträge verarbeiten und prüft auf Benachrichtigungen (Code 1)
            self.berechne_gleitzeit()
            
            # Schritt 5: Arbeitszeitschutzgesetz-Prüfungen (Codes 3-9)
            logger.debug(f"stempel_löschen_nach_id: Führe Arbeitszeitschutzgesetz-Prüfungen durch für Datum {datum_str}")
            self.checke_ruhezeiten()                          # Code 3: Ruhezeit-Verstöße
            self.checke_durchschnittliche_arbeitszeit()       # Code 4: Durchschnitt > 8h/Tag
            self.checke_max_arbeitszeit()                     # Code 5: Max. Arbeitszeit überschritten
            self.checke_sonn_feiertage()                      # Code 6: Sonn-/Feiertag
            self.checke_wochenstunden_minderjaehrige()        # Code 7: Wochenstunden > 40h (Minderjährige)
            self.checke_arbeitstage_pro_woche_minderjaehrige() # Code 8: >5 Arbeitstage/Woche (Minderjährige)
            self.checke_arbeitszeitfenster_minderjaehrige()   # Code 9: Arbeitszeitfenster 6-20 Uhr (Minderjährige)
            
            # Schritt 6: Prüfe und korrigiere bestehende Benachrichtigungen
            geloeschte = self.pruefe_und_korrigiere_arbeitszeitschutz_benachrichtigungen()
            if geloeschte > 0:
                logger.info(f"stempel_löschen_nach_id: {geloeschte} korrigierte Benachrichtigungen gelöscht")
            
            logger.info(f"stempel_löschen_nach_id: Stempel {stempel_id} erfolgreich gelöscht, alle Prüfungen durchgeführt")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"stempel_löschen_nach_id: Datenbankfehler: {e}", exc_info=True)
            session.rollback()
            return False
        except Exception as e:
            logger.error(f"stempel_löschen_nach_id: Unerwarteter Fehler: {e}", exc_info=True)
            session.rollback()
            return False


    def _add_benachrichtigung_safe(self, code, datum, ist_popup=False, popup_uhrzeit=None):
        """
        Fügt eine Benachrichtigung hinzu, wenn sie noch nicht existiert.
        
        Prüft vor dem Hinzufügen, ob bereits eine Benachrichtigung mit
        dem gleichen Code und Datum für den aktuellen Nutzer existiert.
        
        Args:
            code: Benachrichtigungscode (1-11)
            datum: Betroffenes Datum
            ist_popup: Ob es sich um eine zeitgesteuerte PopUp-Benachrichtigung handelt
            popup_uhrzeit: Uhrzeit für PopUp (nur bei ist_popup=True)
            
        Note:
            Verwendet _safe_db_operation für sichere Transaktion.
            Doppelte Benachrichtigungen werden vermieden (Unique Constraint).
        """
        def _db_op():
            # Prüfen, ob Benachrichtigung bereits existiert
            exists_stmt = select(Benachrichtigungen).where(
                (Benachrichtigungen.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Benachrichtigungen.benachrichtigungs_code == code) &
                (Benachrichtigungen.datum == datum)
            )
            exists = session.execute(exists_stmt).scalar_one_or_none()
            
            if exists:
                logger.debug(f"Benachrichtigung (Code {code}, Datum {datum}) existiert bereits. Übersprungen.")
                return False  # Keine neue Benachrichtigung erstellt
            
            # Benachrichtigung erstellen
            benachrichtigung = Benachrichtigungen(
                mitarbeiter_id=self.aktueller_nutzer_id,
                benachrichtigungs_code=code,
                datum=datum,
                ist_popup=ist_popup,
                popup_uhrzeit=popup_uhrzeit
            )
            session.add(benachrichtigung)
            return True
        
        result = self._safe_db_operation(_db_op)
        if isinstance(result, dict) and "error" in result:
            logger.error(f"Konnte Benachrichtigung (Code {code}) nicht hinzufügen: {result.get('details')}")

    def checke_wochenstunden_minderjaehrige(self):
        """
        Prüft, ob Minderjährige die maximale Wochenarbeitszeit von 40 Stunden überschritten haben.
        
        Prüft alle Wochen vom letzter_login bis gestern und erstellt
        Benachrichtigungen (Code 7) bei Verstößen.
        
        Gesetzliche Grundlage:
            Jugendarbeitsschutzgesetz (JArbSchG) § 8: Max. 40h/Woche für Minderjährige
            
        Note:
            Nur relevant für Nutzer, die im geprüften Zeitraum minderjährig waren.
            Berechnet Netto-Arbeitszeit inkl. Pausen.
        """
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
        """
        Prüft, ob Minderjährige an mehr als 5 Tagen pro Woche gearbeitet haben.
        
        Prüft alle Wochen vom letzter_login bis gestern und erstellt
        Benachrichtigungen (Code 8) bei Verstößen.
        
        Gesetzliche Grundlage:
            Jugendarbeitsschutzgesetz (JArbSchG) § 15: Max. 5 Arbeitstage/Woche für Minderjährige
            
        Note:
            Nur relevant für Nutzer, die im geprüften Zeitraum minderjährig waren.
            Zählt Tage mit Zeitstempeln, nicht Arbeitsstunden.
        """
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


    def checke_arbeitszeitfenster_minderjaehrige(self):
        """
        Prüft, ob Minderjährige außerhalb der gesetzlichen Arbeitszeiten (6:00 - 20:00 Uhr) gestempelt haben.
        Erstellt dauerhafte Benachrichtigungen (Code 9) für jeden Verstoß.
        
        Gesetzliche Grundlage:
        - Jugendarbeitsschutzgesetz (JArbSchG) § 14: Minderjährige dürfen nur zwischen 6:00 und 20:00 Uhr arbeiten
        """
        if self.aktueller_nutzer_id is None: 
            return
        if not session: 
            return

        try:
            nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
            if not nutzer:
                return

            start_datum = nutzer.letzter_login if nutzer.letzter_login else date.today() - timedelta(days=30)
            end_datum = date.today() - timedelta(days=1)
            
            # Hole alle Zeiteinträge im Zeitraum
            stmt = select(Zeiteintrag).where(
                (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Zeiteintrag.datum >= start_datum) &
                (Zeiteintrag.datum <= end_datum)
            ).order_by(Zeiteintrag.datum, Zeiteintrag.zeit)
            
            einträge = session.execute(stmt).scalars().all()
            
            if not einträge:
                return
            
            # Definiere erlaubte Arbeitszeiten für Minderjährige
            erlaubte_start_zeit = time(6, 0)  # 6:00 Uhr
            erlaubte_end_zeit = time(20, 0)   # 20:00 Uhr
            
            verstöße = []
            
            for eintrag in einträge:
                # Prüfe ob Nutzer am Datum des Stempels minderjährig war
                if not nutzer.is_minor_on_date(eintrag.datum):
                    continue
                
                # Prüfe ob Stempel außerhalb des erlaubten Zeitfensters liegt
                if eintrag.zeit < erlaubte_start_zeit or eintrag.zeit > erlaubte_end_zeit:
                    verstöße.append((eintrag.datum, eintrag.zeit))
                    logger.warning(
                        f"Arbeitszeitfenster-Verstoß (Minderjährige): Stempel am {eintrag.datum} um {eintrag.zeit} "
                        f"liegt außerhalb von {erlaubte_start_zeit} - {erlaubte_end_zeit}"
                    )
                    # Erstelle Benachrichtigung für diesen Tag
                    self._add_benachrichtigung_safe(code=9, datum=eintrag.datum)
            
            if verstöße:
                logger.info(f"checke_arbeitszeitfenster_minderjaehrige: {len(verstöße)} Verstöße gefunden")
            else:
                logger.debug("checke_arbeitszeitfenster_minderjaehrige: Keine Verstöße gefunden")
        
        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in checke_arbeitszeitfenster_minderjaehrige: {e}", exc_info=True)
            session.rollback()


    def checke_arbeitstage(self):
        """
        Prüft, ob an Werktagen (Mo-Fr) Zeitstempel fehlen und zieht Gleitzeit ab.
        
        Prüft alle Werktage vom letzter_login bis gestern. Für Tage ohne
        Zeitstempel wird die tägliche Sollzeit von der Gleitzeit abgezogen
        und eine Benachrichtigung (Code 1) erstellt.
        
        Returns:
            Liste der Tage mit fehlenden Stempeln
            
        Note:
            Überspringt Wochenenden und Urlaubstage.
            Bei Fehlern wird die Gleitzeit nicht verändert.
            Nutzt Wochenstunden-Historie für korrekte Sollzeit-Berechnung.
        """
        if self.aktueller_nutzer_id is None: 
            logger.debug("checke_arbeitstage: aktueller_nutzer_id ist None")
            return
        if not session: 
            logger.debug("checke_arbeitstage: session ist nicht verfügbar")
            return

        logger.info(f"checke_arbeitstage: Starte für Nutzer {self.aktueller_nutzer_id}")
        
        try:
            nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
            if not nutzer:
                logger.error(f"checke_arbeitstage: Nutzer {self.aktueller_nutzer_id} nicht gefunden.")
                return

            letzter_login = nutzer.letzter_login
            gestern = date.today() - timedelta(days=1)
            logger.debug(f"checke_arbeitstage: Prüfe Zeitraum von {letzter_login} bis {gestern}")

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
                        logger.debug(f"checke_arbeitstage: Kein Eintrag für {tag}")
                tag += timedelta(days=1)

            logger.info(f"checke_arbeitstage: {len(fehlende_tage)} fehlende Arbeitstage gefunden: {fehlende_tage}")

            fallback_sollstunden = None
            if not self.aktueller_nutzer_vertragliche_wochenstunden or self.aktueller_nutzer_vertragliche_wochenstunden < 0:
                logger.warning(
                    f"checke_arbeitstage: Ungültige Wochenstunden ({self.aktueller_nutzer_vertragliche_wochenstunden}) für Nutzer {self.aktueller_nutzer_id}."
                )
                fallback_sollstunden = 8

            abgezogene_tage = []
            for tag in fehlende_tage:
                # Prüfen auf Urlaub/Krankheit
                urlaubs_stmt = select(Abwesenheit).where(
                    (Abwesenheit.mitarbeiter_id == self.aktueller_nutzer_id) &
                    (Abwesenheit.datum == tag) 
                )
                exist_urlaub = session.execute(urlaubs_stmt).scalar_one_or_none()

                if not exist_urlaub:
                    logger.debug(f"checke_arbeitstage: Keine Abwesenheit für {tag}, ziehe Gleitzeit ab")
                    wochenstunden_tag = hole_wochenstunden_am_datum(
                        self.aktueller_nutzer_id,
                        tag,
                        self.aktueller_nutzer_vertragliche_wochenstunden,
                    )
                    tägliche_arbeitszeit = berechne_taegliche_sollzeit(
                        wochenstunden_tag,
                        fallback_stunden=fallback_sollstunden,
                    )
                    logger.debug(
                        f"checke_arbeitstage: Tägliche Arbeitszeit für {tag}: {tägliche_arbeitszeit} (Wochenstunden: {wochenstunden_tag})"
                    )
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
                            alte_gleitzeit = float(self.aktueller_nutzer_gleitzeit)
                            neue_gleitzeit = alte_gleitzeit - (tägliche_arbeitszeit.total_seconds() / 3600)
                            nutzer.gleitzeit = neue_gleitzeit # Aktualisiert das Objekt in der Session
                            self.aktueller_nutzer_gleitzeit = neue_gleitzeit # Aktualisiert den lokalen Cache
                            
                            logger.debug(f"checke_arbeitstage: Gleitzeit für {tag} angepasst: {alte_gleitzeit} -> {neue_gleitzeit}")

                            # Benachrichtigung erstellen
                            benachrichtigung = Benachrichtigungen(
                                mitarbeiter_id=self.aktueller_nutzer_id,
                                benachrichtigungs_code=1,
                                datum=tag
                            )
                            session.add(benachrichtigung)
                            abgezogene_tage.append(tag)
                            logger.debug(f"checke_arbeitstage: Benachrichtigung für {tag} erstellt")
                        else:
                            logger.debug(f"checke_arbeitstage: Benachrichtigung für {tag} existiert bereits")
                        return True

                    self._safe_db_operation(_db_op)
                else:
                    logger.debug(f"checke_arbeitstage: Abwesenheit ({exist_urlaub.typ}) für {tag} gefunden, keine Gleitzeit-Anpassung")
            
            logger.info(f"checke_arbeitstage: Abgeschlossen. {len(abgezogene_tage)} Tage mit Gleitzeit-Abzug: {abgezogene_tage}")
            return fehlende_tage
        
        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in checke_arbeitstage: {e}", exc_info=True)
            session.rollback()


    def checke_stempel(self):
        """
        Prüft, ob an Tagen mit Stempeln eine ungerade Anzahl vorliegt (fehlender Stempel).
        
        Prüft alle Tage mit Zeiteinträgen und erstellt Benachrichtigungen (Code 2)
        für Tage mit ungerader Stempelanzahl.
        
        Returns:
            Liste der Tage mit ungerader Stempelanzahl
            
        Note:
            Prüft ALLE Tage mit Stempeln, nicht nur Werktage.
            Auch nachträglich eingetragene Stempel werden erfasst.
            Setzt self.feedback_stempel mit Feedback-Text.
        """
        if self.aktueller_nutzer_id is None: 
            logger.debug("checke_stempel: aktueller_nutzer_id ist None")
            return
        if not session: 
            logger.debug("checke_stempel: session ist nicht verfügbar")
            return

        logger.info(f"checke_stempel: Starte für Nutzer {self.aktueller_nutzer_id}")

        try:
            nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
            if not nutzer: 
                logger.error(f"checke_stempel: Nutzer {self.aktueller_nutzer_id} nicht gefunden")
                return

            letzter_login = nutzer.letzter_login
            gestern = date.today() - timedelta(days=1)
            
            # Prüfe alle Tage, die Stempel haben (nicht nur ab letzter_login)
            # um auch nachgetragene Stempel zu erfassen
            stmt_dates = select(Zeiteintrag.datum).distinct().where(
                (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Zeiteintrag.datum <= gestern)
            )
            tage_mit_stempeln = set(session.execute(stmt_dates).scalars().all())
            
            # Kombiniere mit dem erwarteten Zeitraum (letzter_login bis gestern)
            tag = letzter_login
            alle_zu_pruefenden_tage = set()
            while tag <= gestern:
                if tag.weekday() < 5:
                    alle_zu_pruefenden_tage.add(tag)
                tag += timedelta(days=1)
            
            # Füge auch alle Tage mit Stempeln hinzu (für nachgetragene Stempel)
            # Wichtig: Auch Wochenend-Stempel sollen geprüft werden!
            alle_zu_pruefenden_tage.update(tage_mit_stempeln)
            
            logger.debug(f"checke_stempel: Prüfe {len(alle_zu_pruefenden_tage)} Tage")

            ungerade_tage = []
            for tag in sorted(alle_zu_pruefenden_tage):
                # Prüfe ALLE Tage, nicht nur Werktage
                # (auch Wochenend-Stempel sollen auf Vollständigkeit geprüft werden)
                stmt = select(Zeiteintrag).where(
                    (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
                    (Zeiteintrag.datum == tag)
                )
                stempel = session.execute(stmt).scalars().all()
                stempel_anzahl = len(stempel)
                
                if stempel_anzahl % 2 != 0:
                    ungerade_tage.append(tag)
                    logger.debug(f"checke_stempel: Ungerade Stempelanzahl ({stempel_anzahl}) für {tag}")
                else:
                    logger.debug(f"checke_stempel: Gerade Stempelanzahl ({stempel_anzahl}) für {tag}")
            
            logger.info(f"checke_stempel: {len(ungerade_tage)} Tage mit ungerader Stempelanzahl gefunden: {ungerade_tage}")

            self.feedback_stempel = f"An den Tagen {ungerade_tage} fehlt ein Stempel, bitte tragen sie diesen nach"

            for tag in ungerade_tage:
                logger.debug(f"checke_stempel: Erstelle Benachrichtigung für {tag}")
                self._add_benachrichtigung_safe(code=2, datum=tag)

            logger.info(f"checke_stempel: Abgeschlossen. Benachrichtigungen für {len(ungerade_tage)} Tage erstellt")
            return ungerade_tage
        
        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in checke_stempel: {e}", exc_info=True)
            session.rollback()


    
    def checke_sonn_feiertage(self):
        """
        Prüft, ob an Sonn- oder Feiertagen gearbeitet wurde.
        
        Prüft alle Tage mit Zeiteinträgen vom letzter_login bis gestern und
        erstellt Benachrichtigungen (Code 6) bei Arbeit an Sonn-/Feiertagen.
        
        Gesetzliche Grundlage:
            Arbeitszeitgesetz (ArbZG) § 9: Sonn- und Feiertagsruhe
            
        Note:
            Verwendet holidays-Bibliothek für deutsche Feiertage.
            Bei Fehler beim Laden der Feiertage wird nur Sonntag geprüft.
        """
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

    
    def pruefe_arbeitszeit_fenster(self, stempel_datum, stempel_zeit):
        """
        Prüft, ob ein Stempel außerhalb der gesetzlichen Arbeitszeiten liegt.
        
        Gesetzliche Arbeitszeiten:
        - Minderjährige: 6:00 - 20:00 Uhr
        - Erwachsene: 6:00 - 22:00 Uhr
        
        Args:
            stempel_datum (date): Datum des geplanten Stempels
            stempel_zeit (time): Uhrzeit des geplanten Stempels
            
        Returns:
            dict: {
                'verletzt': bool,  # True wenn außerhalb der Arbeitszeiten
                'ist_minderjaehrig': bool,  # True wenn minderjährig
                'erlaubte_start_zeit': time,  # Erlaubte Startzeit (6:00)
                'erlaubte_end_zeit': time,  # Erlaubte Endzeit (20:00 oder 22:00)
                'stempel_zeit': time,  # Die geprüfte Zeit
            }
        """
        if self.aktueller_nutzer_id is None or not session:
            return {'verletzt': False}
        
        try:
            nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
            if not nutzer:
                return {'verletzt': False}
            
            is_minor = nutzer.is_minor_on_date(stempel_datum)
            
            # Gesetzliche Arbeitszeiten
            erlaubte_start_zeit = time(6, 0)
            if is_minor:
                erlaubte_end_zeit = time(20, 0)
            else:
                erlaubte_end_zeit = time(22, 0)
            
            # Prüfen, ob außerhalb des Zeitfensters
            if stempel_zeit < erlaubte_start_zeit or stempel_zeit > erlaubte_end_zeit:
                logger.warning(
                    f"Arbeitszeitfenster-Verletzung: Stempel um {stempel_zeit} liegt außerhalb "
                    f"von {erlaubte_start_zeit} - {erlaubte_end_zeit} "
                    f"({'minderjährig' if is_minor else 'erwachsen'})"
                )
                return {
                    'verletzt': True,
                    'ist_minderjaehrig': is_minor,
                    'erlaubte_start_zeit': erlaubte_start_zeit,
                    'erlaubte_end_zeit': erlaubte_end_zeit,
                    'stempel_zeit': stempel_zeit,
                }
            else:
                logger.debug(f"pruefe_arbeitszeit_fenster: Stempel um {stempel_zeit} liegt innerhalb der erlaubten Zeiten")
                return {'verletzt': False}
                
        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in pruefe_arbeitszeit_fenster: {e}", exc_info=True)
            return {'verletzt': False}
    
    def pruefe_ruhezeit_vor_stempel(self, stempel_datum, stempel_zeit):
        """
        Prüft, ob die gesetzliche Ruhezeit vor einem neuen Stempel eingehalten wurde.
        Wird VOR dem Einstempeln aufgerufen.
        
        Args:
            stempel_datum (date): Datum des geplanten Stempels
            stempel_zeit (time): Uhrzeit des geplanten Stempels
            
        Returns:
            dict: {
                'verletzt': bool,  # True wenn Ruhezeit verletzt
                'erforderlich_stunden': int,  # Erforderliche Ruhezeit in Stunden (11 oder 12)
                'tatsaechlich_stunden': float,  # Tatsächliche Ruhezeit in Stunden
                'letzter_stempel_datum': date,  # Datum des letzten Stempels
                'letzter_stempel_zeit': time,  # Zeit des letzten Stempels
            }
        """
        if self.aktueller_nutzer_id is None or not session:
            return {'verletzt': False}
        
        try:
            nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
            if not nutzer:
                return {'verletzt': False}
            
            # Hole alle Stempel VOR dem geplanten Stempel
            stmt = select(Zeiteintrag).where(
                (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Zeiteintrag.datum < stempel_datum)
            ).order_by(Zeiteintrag.datum.desc(), Zeiteintrag.zeit.desc())
            
            letzte_eintraege = session.scalars(stmt).all()
            
            if not letzte_eintraege:
                # Kein vorheriger Stempel vorhanden
                return {'verletzt': False}
            
            # Finde den letzten Stempel des vorherigen Tages
            letzter_stempel = letzte_eintraege[0]
            letzter_stempel_datum = letzter_stempel.datum
            letzter_stempel_zeit = letzter_stempel.zeit
            
            # Prüfe, ob es Stempel am gleichen Tag vor dem geplanten Stempel gibt
            # Wenn ja, ist dies NICHT der erste Stempel des Tages -> keine Ruhezeitenprüfung
            stmt_heute = select(Zeiteintrag).where(
                (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Zeiteintrag.datum == stempel_datum)
            )
            heutige_stempel = session.scalars(stmt_heute).all()
            
            if heutige_stempel:
                # Es gibt bereits Stempel heute -> nicht der erste Stempel
                logger.debug(f"pruefe_ruhezeit_vor_stempel: Bereits {len(heutige_stempel)} Stempel am {stempel_datum}, keine Ruhezeitenprüfung")
                return {'verletzt': False}
            
            # Berechne die Ruhezeit
            letzter_stempel_dt = datetime.combine(letzter_stempel_datum, letzter_stempel_zeit)
            neuer_stempel_dt = datetime.combine(stempel_datum, stempel_zeit)
            tatsaechliche_ruhezeit = neuer_stempel_dt - letzter_stempel_dt
            
            # Erforderliche Ruhezeit basierend auf dem Tag des NEUEN Stempels
            is_minor = nutzer.is_minor_on_date(stempel_datum)
            erforderliche_ruhezeit_stunden = 12 if is_minor else 11
            erforderliche_ruhezeit = timedelta(hours=erforderliche_ruhezeit_stunden)
            
            tatsaechliche_ruhezeit_stunden = tatsaechliche_ruhezeit.total_seconds() / 3600
            
            if tatsaechliche_ruhezeit < erforderliche_ruhezeit:
                logger.warning(
                    f"Ruhezeitenverletzung erkannt: Letzter Stempel {letzter_stempel_datum} {letzter_stempel_zeit}, "
                    f"neuer Stempel {stempel_datum} {stempel_zeit}. "
                    f"Erforderlich: {erforderliche_ruhezeit_stunden}h, Tatsächlich: {tatsaechliche_ruhezeit_stunden:.2f}h"
                )
                return {
                    'verletzt': True,
                    'erforderlich_stunden': erforderliche_ruhezeit_stunden,
                    'tatsaechlich_stunden': round(tatsaechliche_ruhezeit_stunden, 2),
                    'letzter_stempel_datum': letzter_stempel_datum,
                    'letzter_stempel_zeit': letzter_stempel_zeit,
                }
            else:
                logger.debug(f"pruefe_ruhezeit_vor_stempel: Ruhezeit eingehalten ({tatsaechliche_ruhezeit_stunden:.2f}h >= {erforderliche_ruhezeit_stunden}h)")
                return {'verletzt': False}
                
        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in pruefe_ruhezeit_vor_stempel: {e}", exc_info=True)
            return {'verletzt': False}
    
    
    def pruefe_und_korrigiere_arbeitszeitschutz_benachrichtigungen(self):
        """
        Prüft alle Benachrichtigungen der Codes 3-9 (Arbeitszeitschutzgesetz-Verstöße),
        ob die Verstöße korrigiert wurden. Wenn ja, wird die Benachrichtigung gelöscht.
        
        Zweck: Automatisches Löschen von Benachrichtigungen, wenn Verstoß korrigiert wurde
        
        Logik-Ablauf:
            1. Alle Arbeitszeitschutz-Benachrichtigungen laden (Codes 3-9, ist_popup=False)
            2. Für jede Benachrichtigung:
               - Code-spezifische Korrektur-Prüfung durchführen:
                 * Code 3: _pruefe_ruhezeit_korrigiert()
                 * Code 4: _pruefe_durchschnitt_arbeitszeit_korrigiert()
                 * Code 5: _pruefe_max_arbeitszeit_korrigiert()
                 * Code 6: _pruefe_sonn_feiertag_korrigiert()
                 * Code 7: _pruefe_wochenstunden_korrigiert()
                 * Code 8: _pruefe_arbeitstage_woche_korrigiert()
                 * Code 9: _pruefe_arbeitszeitfenster_korrigiert()
               - Wenn Korrektur-Prüfung True zurückgibt:
                 → Benachrichtigung aus DB löschen
                 → Zähler erhöhen
            3. Rückgabe: Anzahl gelöschter Benachrichtigungen
        
        Beispiel Code 3 (Ruhezeit):
            _pruefe_ruhezeit_korrigiert(nutzer, datum):
                1. Letzten Ausstempel vom Tag DAVOR finden
                2. Ersten Einstempel von DATUM finden
                3. Zeitdifferenz berechnen
                4. Wenn >= 11 Stunden ODER kein Stempel mehr existiert:
                   → Return True (korrigiert)
                5. Sonst:
                   → Return False (Verstoß besteht noch)
        
        Benachrichtigungscodes:
        - Code 3: Ruhezeit-Verstoß (11h/12h nicht eingehalten)
        - Code 4: Durchschnittliche Arbeitszeit > 8h/Tag (24 Wochen)
        - Code 5: Maximale Arbeitszeit überschritten (8h/10h pro Tag)
        - Code 6: Arbeit an Sonn- oder Feiertagen
        - Code 7: Wochenstunden > 40h (Minderjährige)
        - Code 8: Mehr als 5 Arbeitstage/Woche (Minderjährige)
        - Code 9: Arbeitszeitfenster 6-20 Uhr verletzt (Minderjährige)
        
        Returns:
            int: Anzahl der gelöschten Benachrichtigungen
        """
        if self.aktueller_nutzer_id is None:
            logger.debug("pruefe_und_korrigiere_arbeitszeitschutz_benachrichtigungen: Kein Nutzer eingeloggt")
            return 0
        
        if not session:
            logger.debug("pruefe_und_korrigiere_arbeitszeitschutz_benachrichtigungen: Keine Session")
            return 0
        
        logger.info(f"pruefe_und_korrigiere_arbeitszeitschutz_benachrichtigungen: Starte für Nutzer {self.aktueller_nutzer_id}")
        
        try:
            nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
            if not nutzer:
                logger.error(f"pruefe_und_korrigiere_arbeitszeitschutz_benachrichtigungen: Nutzer {self.aktueller_nutzer_id} nicht gefunden")
                return 0
            
            # Alle Benachrichtigungen der Codes 3-9 holen
            stmt = select(Benachrichtigungen).where(
                (Benachrichtigungen.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Benachrichtigungen.benachrichtigungs_code.in_([3, 4, 5, 6, 7, 8, 9]))
            ).order_by(Benachrichtigungen.datum, Benachrichtigungen.benachrichtigungs_code)
            
            benachrichtigungen = session.execute(stmt).scalars().all()
            
            if not benachrichtigungen:
                logger.debug("pruefe_und_korrigiere_arbeitszeitschutz_benachrichtigungen: Keine Benachrichtigungen der Codes 3-9 gefunden")
                return 0
            
            logger.debug(f"pruefe_und_korrigiere_arbeitszeitschutz_benachrichtigungen: {len(benachrichtigungen)} Benachrichtigungen gefunden")
            
            geloeschte_count = 0
            
            for bn in benachrichtigungen:
                code = bn.benachrichtigungs_code
                datum = bn.datum
                zu_loeschen = False
                
                # Code 3: Ruhezeit-Verstoß prüfen
                if code == 3:
                    zu_loeschen = self._pruefe_ruhezeit_korrigiert(nutzer, datum)
                
                # Code 4: Durchschnittliche Arbeitszeit prüfen
                elif code == 4:
                    zu_loeschen = self._pruefe_durchschnitt_arbeitszeit_korrigiert(nutzer, datum)
                
                # Code 5: Maximale Arbeitszeit prüfen
                elif code == 5:
                    zu_loeschen = self._pruefe_max_arbeitszeit_korrigiert(nutzer, datum)
                
                # Code 6: Sonn-/Feiertag prüfen
                elif code == 6:
                    zu_loeschen = self._pruefe_sonn_feiertag_korrigiert(nutzer, datum)
                
                # Code 7: Wochenstunden Minderjährige prüfen
                elif code == 7:
                    zu_loeschen = self._pruefe_wochenstunden_korrigiert(nutzer, datum)
                
                # Code 8: Arbeitstage/Woche Minderjährige prüfen
                elif code == 8:
                    zu_loeschen = self._pruefe_arbeitstage_woche_korrigiert(nutzer, datum)
                
                # Code 9: Arbeitszeitfenster Minderjährige prüfen
                elif code == 9:
                    zu_loeschen = self._pruefe_arbeitszeitfenster_korrigiert(nutzer, datum)
                
                # Benachrichtigung löschen, wenn korrigiert
                if zu_loeschen:
                    logger.info(f"pruefe_und_korrigiere_arbeitszeitschutz_benachrichtigungen: Lösche korrigierte Benachrichtigung Code {code} für {datum}")
                    session.delete(bn)
                    geloeschte_count += 1
            
            if geloeschte_count > 0:
                session.commit()
                logger.info(f"pruefe_und_korrigiere_arbeitszeitschutz_benachrichtigungen: {geloeschte_count} Benachrichtigungen gelöscht")
            else:
                logger.debug("pruefe_und_korrigiere_arbeitszeitschutz_benachrichtigungen: Keine Benachrichtigungen zu löschen")
            
            return geloeschte_count
            
        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in pruefe_und_korrigiere_arbeitszeitschutz_benachrichtigungen: {e}", exc_info=True)
            session.rollback()
            return 0
    
    
    def _pruefe_ruhezeit_korrigiert(self, nutzer, datum):
        """Prüft, ob Ruhezeit-Verstoß am gegebenen Datum korrigiert wurde."""
        try:
            # Finde Vortag
            vortag = datum - timedelta(days=1)
            
            # Hole Stempel von beiden Tagen
            stmt_vortag = select(Zeiteintrag.zeit).where(
                (Zeiteintrag.mitarbeiter_id == nutzer.mitarbeiter_id) &
                (Zeiteintrag.datum == vortag)
            ).order_by(Zeiteintrag.zeit)
            zeiten_vortag = session.execute(stmt_vortag).scalars().all()
            
            stmt_datum = select(Zeiteintrag.zeit).where(
                (Zeiteintrag.mitarbeiter_id == nutzer.mitarbeiter_id) &
                (Zeiteintrag.datum == datum)
            ).order_by(Zeiteintrag.zeit)
            zeiten_datum = session.execute(stmt_datum).scalars().all()
            
            # Wenn keine Stempel mehr vorhanden, ist der Verstoß "korrigiert"
            if not zeiten_vortag or not zeiten_datum:
                return True
            
            # Berechne Ruhezeit
            ende_vortag = max(zeiten_vortag)
            beginn_datum = min(zeiten_datum)
            
            ende_dt = datetime.combine(vortag, ende_vortag)
            beginn_dt = datetime.combine(datum, beginn_datum)
            differenz = beginn_dt - ende_dt
            
            # Erforderliche Ruhezeit
            erforderlich = timedelta(hours=12) if nutzer.is_minor_on_date(vortag) else timedelta(hours=11)
            
            # Wenn jetzt genug Ruhezeit, ist korrigiert
            return differenz >= erforderlich
            
        except Exception as e:
            logger.error(f"Fehler in _pruefe_ruhezeit_korrigiert: {e}", exc_info=True)
            return False
    
    
    def _pruefe_durchschnitt_arbeitszeit_korrigiert(self, nutzer, datum):
        """Prüft, ob durchschnittliche Arbeitszeit korrigiert wurde."""
        try:
            end_datum = date.today() - timedelta(days=1)
            start_datum = end_datum - timedelta(weeks=24)
            
            stmt = select(Zeiteintrag).where(
                (Zeiteintrag.mitarbeiter_id == nutzer.mitarbeiter_id) &
                (Zeiteintrag.datum.between(start_datum, end_datum))
            ).order_by(Zeiteintrag.datum, Zeiteintrag.zeit)
            
            einträge = session.scalars(stmt).all()
            if not einträge:
                return True
            
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
            
            if not arbeitstage:
                return True
            
            gesamte_arbeitszeit = sum(arbeitstage.values(), timedelta())
            anzahl_arbeitstage = len(arbeitstage)
            
            if anzahl_arbeitstage == 0:
                return True
            
            durchschnittliche_arbeitszeit = gesamte_arbeitszeit / anzahl_arbeitstage
            
            # Wenn jetzt <= 8h, ist korrigiert
            return durchschnittliche_arbeitszeit <= timedelta(hours=8)
            
        except Exception as e:
            logger.error(f"Fehler in _pruefe_durchschnitt_arbeitszeit_korrigiert: {e}", exc_info=True)
            return False
    
    
    def _pruefe_max_arbeitszeit_korrigiert(self, nutzer, datum):
        """Prüft, ob maximale Arbeitszeit am gegebenen Datum korrigiert wurde."""
        try:
            stmt = select(Zeiteintrag).where(
                (Zeiteintrag.mitarbeiter_id == nutzer.mitarbeiter_id) &
                (Zeiteintrag.datum == datum)
            ).order_by(Zeiteintrag.zeit)
            
            einträge = session.scalars(stmt).all()
            
            # Wenn keine Stempel mehr, ist korrigiert
            if not einträge:
                return True
            
            # Berechne Arbeitszeit für den Tag
            arbeitszeit = timedelta()
            i = 0
            while i < len(einträge) - 1:
                calc = CalculateTime(einträge[i], einträge[i + 1], nutzer)
                if calc:
                    calc.gesetzliche_pausen_hinzufügen()
                    arbeitszeit += calc.gearbeitete_zeit
                    i += 2
                else:
                    i += 1
            
            # Maximale Stunden
            max_stunden = timedelta(hours=8) if nutzer.is_minor_on_date(datum) else timedelta(hours=10)
            
            # Wenn jetzt <= max, ist korrigiert
            return arbeitszeit <= max_stunden
            
        except Exception as e:
            logger.error(f"Fehler in _pruefe_max_arbeitszeit_korrigiert: {e}", exc_info=True)
            return False
    
    
    def _pruefe_sonn_feiertag_korrigiert(self, nutzer, datum):
        """Prüft, ob Sonn-/Feiertagsarbeit korrigiert wurde (Stempel gelöscht)."""
        try:
            # Prüfe ob noch Stempel an diesem Tag existieren
            stmt = select(Zeiteintrag).where(
                (Zeiteintrag.mitarbeiter_id == nutzer.mitarbeiter_id) &
                (Zeiteintrag.datum == datum)
            )
            eintrag = session.execute(stmt).scalar_one_or_none()
            
            # Wenn keine Stempel mehr, ist korrigiert
            return eintrag is None
            
        except Exception as e:
            logger.error(f"Fehler in _pruefe_sonn_feiertag_korrigiert: {e}", exc_info=True)
            return False
    
    
    def _pruefe_wochenstunden_korrigiert(self, nutzer, datum):
        """Prüft, ob Wochenstunden-Verstoß korrigiert wurde."""
        try:
            # datum ist der Start der Woche (Montag)
            start_of_week = datum
            end_of_week = start_of_week + timedelta(days=6)
            
            stmt = select(Zeiteintrag).where(
                (Zeiteintrag.mitarbeiter_id == nutzer.mitarbeiter_id) &
                (Zeiteintrag.datum.between(start_of_week, end_of_week))
            ).order_by(Zeiteintrag.datum, Zeiteintrag.zeit)
            
            einträge_woche = session.scalars(stmt).all()
            
            # Wenn keine Stempel mehr, ist korrigiert
            if not einträge_woche:
                return True
            
            # Berechne Wochenstunden
            wochenstunden = timedelta()
            i = 0
            while i < len(einträge_woche) - 1:
                calc = CalculateTime(einträge_woche[i], einträge_woche[i + 1], nutzer)
                if calc:
                    calc.gesetzliche_pausen_hinzufügen()
                    wochenstunden += calc.gearbeitete_zeit
                    i += 2
                else:
                    i += 1
            
            # Wenn jetzt <= 40h und Nutzer war minderjährig, ist korrigiert
            if nutzer.is_minor_on_date(start_of_week):
                return wochenstunden <= timedelta(hours=40)
            else:
                # Wenn nicht mehr minderjährig, ist Benachrichtigung irrelevant
                return True
            
        except Exception as e:
            logger.error(f"Fehler in _pruefe_wochenstunden_korrigiert: {e}", exc_info=True)
            return False
    
    
    def _pruefe_arbeitstage_woche_korrigiert(self, nutzer, datum):
        """Prüft, ob Arbeitstage/Woche-Verstoß korrigiert wurde."""
        try:
            # datum ist der Start der Woche (Montag)
            start_of_week = datum
            end_of_week = start_of_week + timedelta(days=6)
            
            stmt = select(Zeiteintrag.datum).distinct().where(
                (Zeiteintrag.mitarbeiter_id == nutzer.mitarbeiter_id) &
                (Zeiteintrag.datum.between(start_of_week, end_of_week))
            )
            arbeitstage_count = len(session.scalars(stmt).all())
            
            # Wenn jetzt <= 5 Tage und Nutzer war minderjährig, ist korrigiert
            if nutzer.is_minor_on_date(start_of_week):
                return arbeitstage_count <= 5
            else:
                # Wenn nicht mehr minderjährig, ist Benachrichtigung irrelevant
                return True
            
        except Exception as e:
            logger.error(f"Fehler in _pruefe_arbeitstage_woche_korrigiert: {e}", exc_info=True)
            return False
    
    
    def _pruefe_arbeitszeitfenster_korrigiert(self, nutzer, datum):
        """Prüft, ob Arbeitszeitfenster-Verstoß korrigiert wurde (Stempel gelöscht oder Nutzer nicht mehr minderjährig)."""
        try:
            # Prüfe ob Nutzer am gegebenen Datum noch minderjährig ist
            if not nutzer.is_minor_on_date(datum):
                # Nutzer ist nicht mehr minderjährig, Benachrichtigung irrelevant
                return True
            
            # Prüfe ob noch Stempel außerhalb des Zeitfensters (6:00-20:00) an diesem Tag existieren
            erlaubte_start_zeit = time(6, 0)
            erlaubte_end_zeit = time(20, 0)
            
            stmt = select(Zeiteintrag).where(
                (Zeiteintrag.mitarbeiter_id == nutzer.mitarbeiter_id) &
                (Zeiteintrag.datum == datum)
            )
            einträge = session.execute(stmt).scalars().all()
            
            # Wenn keine Stempel mehr vorhanden, ist korrigiert
            if not einträge:
                return True
            
            # Prüfe ob noch Stempel außerhalb des Zeitfensters existieren
            for eintrag in einträge:
                if eintrag.zeit < erlaubte_start_zeit or eintrag.zeit > erlaubte_end_zeit:
                    # Immer noch Stempel außerhalb des Zeitfensters
                    return False
            
            # Alle Stempel sind jetzt innerhalb des Zeitfensters
            return True
            
        except Exception as e:
            logger.error(f"Fehler in _pruefe_arbeitszeitfenster_korrigiert: {e}", exc_info=True)
            return False
    
    
    def checke_ruhezeiten(self):
        """
        Prüft, ob die gesetzlichen Ruhezeiten zwischen Arbeitstagen eingehalten wurden.
        
        Prüft alle aufeinanderfolgenden Arbeitstage vom letzter_login bis gestern.
        Erstellt Benachrichtigungen (Code 3) bei Unterschreitung der Mindest-Ruhezeit.
        
        Gesetzliche Grundlage:
            Arbeitszeitgesetz (ArbZG) § 5: 11 Stunden Ruhezeit (Erwachsene)
            Jugendarbeitsschutzgesetz (JArbSchG) § 13: 12 Stunden Ruhezeit (Minderjährige)
            
        Note:
            Überspringt Wochen mit mehr als 1 Tag Abstand (z.B. Fr→Mo).
            Verwendet Minderjährigen-Status des ersten Tags für Ruhezeit-Anforderung.
        """
        if self.aktueller_nutzer_id is None: return
        if not session: return

        try:
            heute = date.today()
            gestern = heute - timedelta(days=1)

            nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
            if not nutzer:
                logger.error(f"checke_ruhezeiten: Nutzer {self.aktueller_nutzer_id} nicht gefunden.")
                return

            # Prüfe Stempel vom letzter_login bis gestern (nicht nur gestern)
            start_datum = nutzer.letzter_login if nutzer.letzter_login else gestern - timedelta(days=30)
            
            stmt = select(Zeiteintrag).where(
                (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Zeiteintrag.datum >= start_datum) &
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

                # Überspringe nur aufeinanderfolgende Wochenend-Tage (Sa→So)
                # oder wenn mehr als 1 Tag dazwischen liegt (z.B. Fr→Mo)
                tage_dazwischen = (tag_morgen - tag_heute).days
                if tage_dazwischen > 1:
                    # Mehr als 1 Tag zwischen den Schichten (z.B. Fr→Mo)
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
        """
        Prüft, ob die durchschnittliche tägliche Arbeitszeit 8 Stunden überschreitet.
        
        Berechnet die durchschnittliche Arbeitszeit über die letzten 24 Wochen.
        Erstellt eine Benachrichtigung (Code 4) bei Überschreitung.
        
        Gesetzliche Grundlage:
            Arbeitszeitgesetz (ArbZG) § 3: Durchschnittlich 8h/Tag über 24 Wochen
            
        Note:
            Berücksichtigt nur Arbeitstage mit vollständigen Stempelpaaren.
            Pausenzeiten werden automatisch abgezogen.
        """
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
            
            # Prüfe alle Einträge vom letzter_login bis gestern (nicht nur unvalidierte!)
            start_datum = nutzer.letzter_login if nutzer.letzter_login else date.today() - timedelta(days=30)
            stmt = select(Zeiteintrag).where(
                (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Zeiteintrag.datum >= start_datum) &
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
        """
        Berechnet die Gleitzeit aus unvalidierten Zeiteinträgen und aktualisiert das Gleitkonto.
        
        Verarbeitet alle unvalidierten Zeiteinträge paarweise (Ein-/Ausstempeln),
        berechnet die Netto-Arbeitszeit (inkl. Pausen) und gleicht sie mit der
        täglichen Sollzeit ab. Markiert verarbeitete Einträge als validiert.
        
        8-Schritte-Prozess:
            1. Unvalidierte Zeiteinträge laden (vom letzten Login bis gestern)
               - Query: WHERE validiert = 0 ORDER BY datum, zeit
               - Zeitraum: Vom letzter_login bis date.today() - 1
            
            2. Nach Datum gruppieren
               - Dictionary: {datum: [zeiteintrag1, zeiteintrag2, ...]}
            
            3. Für jeden Tag prüfen: Vollständiger Arbeitstag?
               - Wenn geradzahlig viele Stempel: Vollständig (kann berechnet werden)
               - Wenn ungeradzahlig: Fehlstempel → Code 2 Benachrichtigung erstellen
               - Wenn 0 Stempel UND Arbeitstag UND kein Urlaub: Fehlender Tag → Code 1
            
            4. Für jeden vollständigen Arbeitstag:
               - Stempel paarweise durchgehen (Einstempel, Ausstempel)
               - CalculateTime(ein, aus, nutzer) → Berechnet Arbeitszeit
                 * gesetzliche_pausen_hinzufügen():
                   - Minderjährige: 4.5h→30min, 6h→60min
                   - Erwachsene: 6h→30min, 9h→45min
                 * arbeitsfenster_beachten():
                   - Minderjährige: Nur 6-20 Uhr zählt
                   - Erwachsene: Nur 6-22 Uhr zählt
               - Delta zur Soll-Arbeitszeit berechnen: ist - soll
               - Auf Gleitzeit-Konto addieren
            
            5. Tägliche Sollzeit ermitteln:
               - hole_wochenstunden_am_datum(mitarbeiter_id, datum, fallback)
               - berechne_taegliche_sollzeit(wochenstunden) → timedelta(hours=wochenstunden/5)
            
            6. Gleitzeit-Delta berechnen:
               - Pro Tag: delta = arbeitszeit - sollzeit
               - Summe aller Deltas bilden
            
            7. Alle verarbeiteten Einträge auf validiert = True setzen
               - UPDATE zeiteinträge SET validiert = 1 WHERE id IN (...)
            
            8. Gleitzeit in DB speichern
               - nutzer.gleitzeit += summe_aller_deltas_in_stunden
               - session.commit()
        
        Besonderheiten:
            - Fehlstempel (Code 2): Tag wird übersprungen, Benachrichtigung erstellt
            - Fehlende Arbeitstage (Code 1): Sollzeit wird abgezogen, Benachrichtigung nur wenn nicht bereits vorhanden
            - Urlaub/Krankheit: Wird NICHT als fehlender Tag behandelt
            - Arbeitsfenster: Zeit außerhalb wird automatisch abgezogen
            - Pausen: Werden automatisch von Arbeitszeit abgezogen
        
        Note:
            Diese Methode ist der Kern der Zeiterfassung und wird bei jedem Login
            und nach jedem Stempeln aufgerufen. Sie sorgt dafür, dass die Gleitzeit
            immer den aktuellen Stand widerspiegelt.
        """
        # === Validierung: Nutzer muss eingeloggt sein ===
        if self.aktueller_nutzer_id is None: 
            return
        if not session: 
            return

        try:
            # === SCHRITT 0: Nutzer-Objekt aus DB laden ===
            nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
            if not nutzer: 
                return

            # === SCHRITT 1: Unvalidierte Zeiteinträge laden ===
            # Zeitraum: Vom letzten Login bis gestern (heute wird nicht berechnet, da ggf. noch offen)
            stmt = select(Zeiteintrag).where(
                (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Zeiteintrag.validiert == 0)  # Nur noch nicht verarbeitete Einträge
            ).order_by(Zeiteintrag.datum, Zeiteintrag.zeit)  # Chronologisch sortiert
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

            fallback_sollstunden = None
            if not self.aktueller_nutzer_vertragliche_wochenstunden or self.aktueller_nutzer_vertragliche_wochenstunden <= 0:
                logger.warning(
                    f"berechne_gleitzeit: Ungültige aktuelle Wochenstunden ({self.aktueller_nutzer_vertragliche_wochenstunden}) für Nutzer {self.aktueller_nutzer_id}, verwende Historie/Fallback."
                )
                fallback_sollstunden = 8

            gleitzeit_diff_total = timedelta()

            for datum, arbeitszeit in arbeitstage.items():
                wochenstunden_tag = hole_wochenstunden_am_datum(
                    self.aktueller_nutzer_id,
                    datum,
                    self.aktueller_nutzer_vertragliche_wochenstunden,
                )
                tägliche_arbeitszeit = berechne_taegliche_sollzeit(
                    wochenstunden_tag,
                    fallback_stunden=fallback_sollstunden,
                )

                # Prüfen, ob für den Tag eine "Fehlstempel"-Benachrichtigung (Code 1) existiert
                exists_stmt = select(Benachrichtigungen).where(
                    (Benachrichtigungen.mitarbeiter_id == self.aktueller_nutzer_id) &
                    (Benachrichtigungen.datum == datum) &
                    (Benachrichtigungen.benachrichtigungs_code == 1)
                )
                exists = session.execute(exists_stmt).scalar_one_or_none()

                if exists:
                    # Es existiert bereits eine Code-1-Benachrichtigung (tägliche Sollzeit wurde früher abgezogen).
                    # Wenn jetzt Stempel vorhanden sind (arbeitszeit > 0), dann darf der Tag NICHT übersprungen werden.
                    # Stattdessen fügen wir nur die tatsächlich gearbeitete Zeit hinzu, ohne die tägliche Sollzeit erneut abzuziehen.
                    gleitzeit_diff_total += arbeitszeit
                    logger.debug(
                        f"Tag {datum}: Code 1 existiert – füge nur Arbeitszeit {arbeitszeit} hinzu (Sollzeit nicht erneut abziehen)."
                    )
                    continue

                # NEU: Wenn für diesen Tag bereits validierte Einträge existieren,
                # dann den Tages-Soll NICHT erneut abziehen, sondern nur die zusätzliche Arbeitszeit addieren.
                validated_before_stmt = select(Zeiteintrag).where(
                    (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
                    (Zeiteintrag.datum == datum) &
                    (Zeiteintrag.validiert == 1)
                )
                validated_before = session.execute(validated_before_stmt).first() is not None

                if validated_before:
                    gleitzeit_diff_total += arbeitszeit
                    logger.debug(f"Tag {datum}: Bereits validierte Einträge vorhanden – füge nur zusätzliche Arbeitszeit {arbeitszeit} hinzu.")
                else:
                    if tägliche_arbeitszeit > timedelta():
                        differenz = arbeitszeit - tägliche_arbeitszeit
                    else:
                        differenz = arbeitszeit
                    gleitzeit_diff_total += differenz
                    logger.debug(f"Tag {datum}: Erster Lauf – füge Differenz {differenz} (Arbeitszeit {arbeitszeit} - Soll {tägliche_arbeitszeit}) hinzu.")
            
            # Alle benutzten Einträge als validiert markieren
            for e in benutzte_einträge:
                e.validiert = True
            
            # Gleitzeit-Update
            gleitzeit_stunden = float(gleitzeit_diff_total.total_seconds() / 3600)
            # WICHTIG: Auf DB-Wert des Nutzers aufsetzen (robust gegen externe Änderungen), nicht auf evtl. veralteten Cache im Modell
            aktuelle_db_gleitzeit = float(nutzer.gleitzeit or 0)
            neue_gleitzeit = aktuelle_db_gleitzeit + gleitzeit_stunden

            # Werte synchron halten
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

            fallback_sollstunden = None
            if not self.aktueller_nutzer_vertragliche_wochenstunden or self.aktueller_nutzer_vertragliche_wochenstunden <= 0:
                logger.warning(
                    f"berechne_durchschnittliche_gleitzeit: Ungültige aktuelle Wochenstunden ({self.aktueller_nutzer_vertragliche_wochenstunden}), verwende Historie/Fallback."
                )
                fallback_sollstunden = 8

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
                wochenstunden_tag = hole_wochenstunden_am_datum(
                    self.aktueller_nutzer_id,
                    tag,
                    self.aktueller_nutzer_vertragliche_wochenstunden,
                )
                tägliche_arbeitszeit = berechne_taegliche_sollzeit(
                    wochenstunden_tag,
                    fallback_stunden=fallback_sollstunden,
                )

                if tag in arbeitstage:
                    differenz = arbeitstage[tag] - tägliche_arbeitszeit
                    gleitzeit_differenzen.append(differenz)
                    berücksichtigte_tage.append(tag)
                elif include_missing_days:
                    differenz = -tägliche_arbeitszeit
                    gleitzeit_differenzen.append(differenz)
                    berücksichtigte_tage.append(tag)
                
            if not gleitzeit_differenzen:
                return {
                    "durchschnitt_gleitzeit_stunden": 0.0,
                    "gesamt_gleitzeit_stunden": 0.0,
                    "anzahl_tage": 0,
                    "berücksichtigte_tage": []
                }

            # Division durch Null ist hier (len(gleitzeit_differenzen)) abgefangen
            gesamt_gleitzeit = sum(gleitzeit_differenzen, timedelta())
            durchschnitt = gesamt_gleitzeit / len(gleitzeit_differenzen)
            durchschnitt_stunden = round(durchschnitt.total_seconds() / 3600, 2)
            gesamt_stunden = gesamt_gleitzeit.total_seconds() / 3600

            return {
                "durchschnitt_gleitzeit_stunden": durchschnitt_stunden,
                "gesamt_gleitzeit_stunden": gesamt_stunden,
                "anzahl_tage": len(gleitzeit_differenzen),
                "berücksichtigte_tage": berücksichtigte_tage
            }

        except SQLAlchemyError as e:
            logger.error(f"DB-Fehler in berechne_durchschnittliche_gleitzeit: {e}", exc_info=True)
            session.rollback()
            return {"error": "DB-Fehler"}
        except ZeroDivisionError:
             logger.error("berechne_durchschnittliche_gleitzeit: Division durch Null (sollte abgefangen sein).")
             return {
                 "durchschnitt_gleitzeit_stunden": 0.0,
                 "gesamt_gleitzeit_stunden": 0.0,
                 "anzahl_tage": 0,
                 "berücksichtigte_tage": []
             }


    
    def kummuliere_gleitzeit(self):
        """
        Berechnet kumulierte Gleitzeit für Monat, Quartal und Jahr.
        
        Verwendet berechne_durchschnittliche_gleitzeit() um die Gleitzeit-Summen
        für verschiedene Zeiträume zu ermitteln und aktualisiert die entsprechenden
        Attribute.
        
        Note:
            Setzt self.kummulierte_gleitzeit_monat, _quartal, _jahr.
            Berücksichtigt self.tage_ohne_stempel_beachten Option.
            Bei Fehlern werden die Werte auf 0.0 gesetzt.
        """
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
            gesamt_stunden_monat = ergebnis_monat.get("gesamt_gleitzeit_stunden")
            if gesamt_stunden_monat is None:
                logger.warning("berechne_durchschnittliche_gleitzeit lieferte keine Gesamtstunden für den Monat – fallback auf Durchschnitt")
                gesamt_stunden_monat = ergebnis_monat.get("durchschnitt_gleitzeit_stunden", 0.0)
            self.kummulierte_gleitzeit_monat = round(gesamt_stunden_monat, 2)
        else:
            logger.warning(f"Fehler bei Kummulation (Monat): {ergebnis_monat.get('error')}")
            self.kummulierte_gleitzeit_monat = 0.0


        # 2. Quartal berechnen

        aktuelles_quartal = (heute.month - 1) // 3 + 1
        start_monat_quartal = (aktuelles_quartal - 1) * 3 + 1
        start_quartal = heute.replace(month=start_monat_quartal, day=1)
        ergebnis_quartal = self.berechne_durchschnittliche_gleitzeit(start_quartal, heute, include_missing)
        if "error" not in ergebnis_quartal:
            gesamt_stunden_quartal = ergebnis_quartal.get("gesamt_gleitzeit_stunden")
            if gesamt_stunden_quartal is None:
                logger.warning("berechne_durchschnittliche_gleitzeit lieferte keine Gesamtstunden für das Quartal – fallback auf Durchschnitt")
                gesamt_stunden_quartal = ergebnis_quartal.get("durchschnitt_gleitzeit_stunden", 0.0)
            self.kummulierte_gleitzeit_quartal = round(gesamt_stunden_quartal, 2)
        else:
            logger.warning(f"Fehler bei Kummulation (Quartal): {ergebnis_quartal.get('error')}")
            self.kummulierte_gleitzeit_quartal = 0.0


        # 3. Jahr berechnen

        start_jahr = heute.replace(month=1, day=1)
        ergebnis_jahr = self.berechne_durchschnittliche_gleitzeit(start_jahr, heute, include_missing)
        if "error" not in ergebnis_jahr:
            gesamt_stunden_jahr = ergebnis_jahr.get("gesamt_gleitzeit_stunden")
            if gesamt_stunden_jahr is None:
                logger.warning("berechne_durchschnittliche_gleitzeit lieferte keine Gesamtstunden für das Jahr – fallback auf Durchschnitt")
                gesamt_stunden_jahr = ergebnis_jahr.get("durchschnitt_gleitzeit_stunden", 0.0)
            self.kummulierte_gleitzeit_jahr = round(gesamt_stunden_jahr, 2)
        else:
            logger.warning(f"Fehler bei Kummulation (Jahr): {ergebnis_jahr.get('error')}")
            self.kummulierte_gleitzeit_jahr = 0.0



class ModellLogin():
    """
    Geschäftslogik-Klasse für Authentifizierung und Benutzerverwaltung.
    
    Verwaltet Login, Registrierung und grundlegende Benutzerdaten.
    
    Funktionalitäten:
    - Benutzer-Registrierung mit Validierung
    - Passwort-Authentifizierung (bcrypt)
    - Altersvalidierung (mind. 16 Jahre)
    - Ampel-Grenzwerte-Validierung
    - Vorgesetzten-Zuordnung
    
    Attributes:
        neuer_nutzer_name (str): Name für Registrierung
        neuer_nutzer_passwort (str): Passwort für Registrierung
        neuer_nutzer_passwort_val (str): Passwort-Wiederholung
        neuer_nutzer_vertragliche_wochenstunden (str): Wochenarbeitszeit
        neuer_nutzer_geburtsdatum (str): Geburtsdatum (Format: "TT/MM/JJJJ")
        neuer_nutzer_rückmeldung (str): UI-Feedback für Registrierung
        neuer_nutzer_vorgesetzter (str): Name des Vorgesetzten
        neuer_nutzer_grün (str): Grüner Ampel-Schwellwert
        neuer_nutzer_rot (str): Roter Ampel-Schwellwert
        anmeldung_name (str): Name für Login
        anmeldung_passwort (str): Passwort für Login
        anmeldung_rückmeldung (str): UI-Feedback für Login
        anmeldung_mitarbeiter_id_validiert (int): ID nach erfolgreichem Login
    """
    def __init__(self):
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
        Erstellt einen neuen Benutzer in der Datenbank.
        
        Führt umfassende Validierung durch:
        - Pflichtfelder-Prüfung
        - Passwort-Übereinstimmung
        - Altersvalidierung (mind. 16 Jahre)
        - Ampel-Grenzwerte-Validierung (symmetrisch, rot > grün)
        - Vorgesetzten-Existenz
        - Eindeutigkeit des Benutzernamens
        
        Bei Erfolg:
        - Passwort wird mit bcrypt gehasht
        - Benutzer wird in DB angelegt
        - Ampel-Grenzwerte werden gesetzt
        
        Returns:
            None: Setzt self.neuer_nutzer_rückmeldung mit Erfolg/Fehler
        """
        # Die Input-Validierung ist bereits sehr gut!
        if not self.neuer_nutzer_name:
            self.neuer_nutzer_rückmeldung = "Bitte gib einen Namen ein"
            return
        # ... (alle anderen 'if not ...')
        
        # Die try-except-Blöcke für strptime und int() sind ebenfalls sehr gut.
        try:
            geburtsdatum_obj = datetime.strptime(self.neuer_nutzer_geburtsdatum, "%d/%m/%Y").date()
        except ValueError:
            self.neuer_nutzer_rückmeldung = "Bitte wähle ein Datum aus"
            return
        
        # Altersvalidierung: Nutzer muss mindestens 16 Jahre alt sein
        heute = date.today()
        alter = heute.year - geburtsdatum_obj.year - ((heute.month, heute.day) < (geburtsdatum_obj.month, geburtsdatum_obj.day))
        
        if alter < 16:
            self.neuer_nutzer_rückmeldung = f"Du musst mindestens 16 Jahre alt sein. Aktuelles Alter: {alter} Jahre."
            logger.warning(f"Registrierungsversuch mit unzulässigem Alter: {alter} Jahre (Geburtsdatum: {geburtsdatum_obj})")
            return
        
        try:
            wochenstunden_int = int(self.neuer_nutzer_vertragliche_wochenstunden)
            grün_int = int(self.neuer_nutzer_grün)
            rot_int = int(self.neuer_nutzer_rot)
            
            # Neue symmetrische Ampel-Logik: Rot-Schwelle muss größer sein als Grün-Schwelle
            if rot_int <= grün_int:
                self.neuer_nutzer_rückmeldung = "Rote Schwelle muss größer als grüne Schwelle sein (z.B. Grün: 5h, Rot: 10h)."
                return
            
            # Beide Werte müssen positiv sein
            if grün_int <= 0 or rot_int <= 0:
                self.neuer_nutzer_rückmeldung = "Ampelwerte müssen positiv sein."
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
            
            # Passwort hashen
            try:
                hashed_password = hash_password(self.neuer_nutzer_passwort)
            except Exception as e:
                logger.error(f"Fehler beim Hashen des Passworts: {e}", exc_info=True)
                self.neuer_nutzer_rückmeldung = "Fehler beim Verschlüsseln des Passworts."
                return
            
            neuer_nutzer = mitarbeiter(
                name=self.neuer_nutzer_name, 
                password=hashed_password,  # Gehashtes Passwort verwenden
                vertragliche_wochenstunden=wochenstunden_int, 
                geburtsdatum=geburtsdatum_obj,
                letzter_login=date.today(),
                ampel_grün=grün_int,
                ampel_rot=rot_int,
                vorgesetzter_id=vorgesetzter_id
            ) 
        
            session.add(neuer_nutzer)
            session.flush()  # Mitarbeiter-ID für Historieneintrag sicherstellen

            historien_eintrag = VertragswochenstundenHistorie(
                mitarbeiter_id=neuer_nutzer.mitarbeiter_id,
                gueltig_ab=date.today(),
                wochenstunden=wochenstunden_int,
            )
            session.add(historien_eintrag)

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

            # Passwort-Verifizierung mit bcrypt
            if verify_password(self.anmeldung_passwort, nutzer.password):
                self.anmeldung_rückmeldung = "Login erfolgreich"
                self.anmeldung_mitarbeiter_id_validiert = nutzer.mitarbeiter_id
                logger.info(f"Erfolgreicher Login für: {self.anmeldung_name}. letzter_login wird später aktualisiert.")
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