"""
Model-Modul für die BBQ Arbeitszeit-Erfassungssoftware.

Dieses Modul enthält die Datenbank-Models und Geschäftslogik für:
- Benutzerverwaltung (Login, Registrierung)
- Zeiterfassung (Stempel, Zeiteinträge)
- Gleitzeitberechnung
- Arbeitszeitgesetz (ArbZG)-Prüfungen
- Benachrichtigungssystem

Die Models verwenden SQLAlchemy ORM für die Datenbankinteraktion.
"""

from sqlalchemy import Column, Integer, String, Date, create_engine, select, Time, Boolean, ForeignKey, UniqueConstraint, CheckConstraint
import sqlalchemy.orm as saorm
from sqlalchemy.exc import IntegrityError
from datetime import datetime, date, timedelta

engine = create_engine("sqlite:///system.db", echo=True)
Base = saorm.declarative_base()
Session = saorm.sessionmaker(bind=engine)
session = Session()

class mitarbeiter(Base):
    """
    Datenbankmodell für Mitarbeiter/Benutzer.
    
    Speichert alle relevanten Informationen zu einem Mitarbeiter inklusive
    Login-Daten, vertraglichen Arbeitsstunden und Gleitzeitkonto.
    
    Attributes:
        mitarbeiter_id (int): Eindeutige ID (Primary Key)
        name (str): Benutzername (unique, max 30 Zeichen)
        password (str): Passwort (max 15 Zeichen)
        vertragliche_wochenstunden (int): Vertraglich vereinbarte Wochenstunden
        geburtsdatum (date): Geburtsdatum des Mitarbeiters
        gleitzeit (int): Aktueller Gleitzeitstand in Stunden
        letzter_login (date): Datum des letzten Logins
        ampel_grün (int): Grenzwert für grüne Ampel (Standard: 5)
        ampel_rot (int): Grenzwert für rote Ampel (Standard: -5)
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

class Abwesenheit(Base):
    """
    Datenbankmodell für Abwesenheiten (Urlaub, Krankheit, etc.).
    
    Attributes:
        id (int): Eindeutige ID (Primary Key)
        mitarbeiter_id (int): Foreign Key zum Mitarbeiter
        datum (date): Datum der Abwesenheit
        typ (str): Art der Abwesenheit ('Urlaub', 'Krankheit', 'Fortbildung', 'Sonstiges')
        genehmigt (bool): Status der Genehmigung (Standard: False)
    """
    __tablename__ = "abwesenheiten"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mitarbeiter_id = Column(Integer, ForeignKey("users.mitarbeiter_id"), nullable=False)
    datum = Column(Date, nullable=False)
    typ = Column(String, CheckConstraint("typ IN ('Urlaub', 'Krankheit', 'Fortbildung', 'Sonstiges')"), nullable=False)
    genehmigt = Column(Boolean, nullable=False, default=False)


class Zeiteintrag(Base):
    """
    Datenbankmodell für Zeitstempel/Zeiteinträge.
    
    Speichert einzelne Zeitstempel (Ein- und Ausstempelungen) für die
    Arbeitszeiterfassung.
    
    Attributes:
        id (int): Eindeutige ID (Primary Key)
        mitarbeiter_id (int): Foreign Key zum Mitarbeiter
        zeit (time): Uhrzeit des Stempels
        datum (date): Datum des Stempels
        validiert (bool): Ob der Eintrag bereits für Gleitzeitberechnung verwendet wurde
    """
    __tablename__ = "zeiteinträge"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mitarbeiter_id = Column(Integer, ForeignKey("users.mitarbeiter_id"), nullable=False)
    zeit = Column(Time, nullable=False)
    datum = Column(Date, nullable=False)
    validiert = Column(Boolean, nullable=False, default=False) 

class Benachrichtigungen(Base):
    """
    Datenbankmodell für Benachrichtigungen an Mitarbeiter.
    
    Speichert verschiedene Arten von Benachrichtigungen wie fehlende Stempel,
    ArbZG-Verstöße, etc.
    
    Attributes:
        id (int): Eindeutige ID (Primary Key)
        mitarbeiter_id (int): Foreign Key zum Mitarbeiter
        benachrichtigungs_code (int): Code der Benachrichtigungsart (1-5)
        datum (date): Datum, auf das sich die Benachrichtigung bezieht
        
    Benachrichtigungs-Codes:
        1: Fehlender Arbeitstag (nicht gestempelt)
        2: Ungerader Stempel (fehlt Ein- oder Ausstempelung)
        3: Ruhezeit-Verstoß
        4: Durchschnittliche Arbeitszeit > 8 Stunden
        5: Maximale Tagesarbeitszeit > 10 Stunden
    """
    __tablename__ = "benachrichtigungen"

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
        5:["Achtung am", "wurde die maximale gesetzlich zulässsige Arbeitszeit überschritten."]
    }

    __table_args__ = (
        UniqueConstraint("mitarbeiter_id", "benachrichtigungs_code", "datum", name="uq_benachrichtigung_unique"),
    )

    def create_fehlermeldung(self):
        """
        Erstellt eine lesbare Fehlermeldung basierend auf dem Benachrichtigungscode.
        
        Returns:
            str: Formatierte Fehlermeldung für die Benutzeranzeige
        """

        if self.benachrichtigungs_code == 1:
            return f"{self.CODES[1.1]} {self.datum} {self.CODES[1.2]}"
        elif self.benachrichtigungs_code == 2:
            return f"{self.CODES[2.1]} {self.datum} {self.CODES[2.2]}"
        
        elif self.benachrichtigungs_code == 3:
            return f"{self.CODES[3][0]} {self.datum} {self.CODES[3][1]}"
        
        elif self.benachrichtigungs_code ==4:
            return self.CODES[4]



class CalculateTime():
    """
    Hilfsklasse zur Berechnung der Arbeitszeit zwischen zwei Zeiteinträgen.
    
    Berechnet die Differenz zwischen Start- und Endzeit eines Arbeitstages
    und berücksichtigt gesetzliche Pausen.
    
    Attributes:
        datum (date): Datum der Zeiteinträge
        startzeit (time): Startzeit (Einstempelung)
        endzeit (time): Endzeit (Ausstempelung)
        gearbeitete_zeit (timedelta): Berechnete Arbeitszeit
    """
     def __new__(cls, eintrag1, eintrag2):
         """
         Factory-Methode zur Validierung der Zeiteinträge.
         
         Gibt nur eine Instanz zurück, wenn beide Einträge vom selben Datum sind.
         
         Args:
             eintrag1: Erster Zeiteintrag (Einstempelung)
             eintrag2: Zweiter Zeiteintrag (Ausstempelung)
             
         Returns:
             CalculateTime: Neue Instanz oder None bei unterschiedlichen Daten
         """
         if eintrag1.datum != eintrag2.datum:
             return None
         return super().__new__(cls)

     def __init__(self, eintrag1, eintrag2):
         """
         Initialisiert die Zeitberechnung zwischen zwei Einträgen.
         
         Args:
             eintrag1: Erster Zeiteintrag (Einstempelung)
             eintrag2: Zweiter Zeiteintrag (Ausstempelung)
         """
         self.datum = eintrag1.datum
         self.startzeit = eintrag1.zeit
         self.endzeit = eintrag2.zeit
         start_dt = datetime.combine(self.datum, self.startzeit)
         end_dt = datetime.combine(self.datum, self.endzeit)

         self.gearbeitete_zeit = end_dt - start_dt  

     def gesetzliche_pausen_hinzufügen(self):
         """
         Zieht gesetzlich vorgeschriebene Pausen von der Arbeitszeit ab.
         
         Gemäß ArbZG:
         - > 6 Stunden: 30 Minuten Pause
         - > 9 Stunden: 45 Minuten Pause (zusätzlich)
         """
         if self.gearbeitete_zeit > timedelta(hours=6):
             self.gearbeitete_zeit -= timedelta(minutes=30)

         if self.gearbeitete_zeit > timedelta(hours=9):
             self.gearbeitete_zeit -= timedelta(minutes=45)



class ModellTrackTime():
    """
    Model-Klasse für Zeiterfassung und Arbeitszeitverwaltung.
    
    Verwaltet alle Funktionen rund um Zeiterfassung, Gleitzeitberechnung,
    ArbZG-Prüfungen und Benachrichtigungen.
    
    Attributes:
        aktueller_nutzer_id (int): ID des angemeldeten Benutzers
        aktueller_nutzer_name (str): Name des angemeldeten Benutzers
        aktueller_nutzer_vertragliche_wochenstunden (int): Vertragliche Wochenstunden
        aktueller_nutzer_gleitzeit (float): Aktueller Gleitzeitstand
        aktueller_nutzer_ampel_rot/grün (int): Ampel-Grenzwerte
        manueller_stempel_datum/uhrzeit (str): Daten für manuellen Stempel
        zeiteinträge_bestimmtes_datum (list): Zeiteinträge für ausgewähltes Datum
        bestimmtes_datum (str): Ausgewähltes Datum im Kalender
        neues_passwort/wiederholung (str): Neue Passwort-Daten
        ampel_status (str): Aktueller Ampelstatus ('red', 'yellow', 'green')
        benachrichtigungen (list): Liste von Benachrichtigungen
        feedback_* (str): Feedback-Texte für verschiedene Aktionen
    """
    def __init__(self):
        self.aktueller_nutzer_id = None
        self.aktueller_nutzer_name = None
        self.aktueller_nutzer_vertragliche_wochenstunden = None
        self.aktueller_nutzer_gleitzeit = None
        self.aktueller_nutzer_ampel_rot = None
        self.aktueller_nutzer_ampel_grün = None

        self.manueller_stempel_datum = None
        self.manueller_stempel_uhrzeit = None

        self.zeiteinträge_bestimmtes_datum = None
        self.bestimmtes_datum = None

        self.neues_passwort = None
        self.neues_passwort_wiederholung = None

        self.ampel_status = None

        self.neuer_abwesenheitseintrag_datum = None
        self.neuer_abwesenheitseintrag_art = None


        self.benachrichtigungen = []


        self.feedback_manueller_stempel = ""
        self.feedback_arbeitstage = ""
        self.feedback_stempel = ""
        self.feedback_neues_passwort = ""

    def get_zeiteinträge(self):
        """
        Lädt Zeiteinträge für ein bestimmtes Datum aus der Datenbank.
        
        Ruft alle Zeitstempel des angemeldeten Benutzers für das in
        self.bestimmtes_datum gespeicherte Datum ab.
        """
        if self.aktueller_nutzer_id is None or self.bestimmtes_datum is None:
            return
        
        date = datetime.strptime(self.bestimmtes_datum, "%d.%m.%Y").date()


        stmt = select(
            Zeiteintrag
            ).where(
                (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id)&(Zeiteintrag.datum == date)
                ).order_by(
                    Zeiteintrag.datum, Zeiteintrag.zeit
                    )
        einträge = session.scalars(stmt).all()
        self.zeiteinträge_bestimmtes_datum = einträge


    def get_user_info(self):
        """
        Lädt die Benutzerinformationen aus der Datenbank.
        
        Aktualisiert alle Attribute des angemeldeten Benutzers
        (Name, Wochenstunden, Gleitzeit, Ampel-Grenzwerte).
        """

        if self.aktueller_nutzer_id is None:
            return

        stmt = select(mitarbeiter).where(mitarbeiter.mitarbeiter_id == self.aktueller_nutzer_id)
        nutzer = session.execute(stmt).scalar_one_or_none()
        if nutzer:
            self.aktueller_nutzer_name = nutzer.name
            self.aktueller_nutzer_vertragliche_wochenstunden = nutzer.vertragliche_wochenstunden
            self.aktueller_nutzer_gleitzeit = nutzer.gleitzeit
            self.aktueller_nutzer_ampel_rot = nutzer.ampel_rot
            self.aktueller_nutzer_ampel_grün = nutzer.ampel_grün

    def set_ampel_farbe(self):
        """
        Setzt den Ampelstatus basierend auf der aktuellen Gleitzeit.
        
        Grün: Gleitzeit >= Grenzwert grün
        Gelb: Grenzwert rot < Gleitzeit < Grenzwert grün
        Rot: Gleitzeit <= Grenzwert rot
        """
        if self.aktueller_nutzer_gleitzeit >= self.aktueller_nutzer_ampel_grün:
            self.ampel_status = "green"

        elif (self.aktueller_nutzer_gleitzeit < self.aktueller_nutzer_ampel_grün) & (self.aktueller_nutzer_gleitzeit > self.aktueller_nutzer_ampel_rot):
            self.ampel_status = "yellow"
    
        else:
            self.ampel_status = "red"


    def get_messages(self):
        """
        Lädt alle Benachrichtigungen des Benutzers aus der Datenbank.
        """

        stmt = select(Benachrichtigungen).where(Benachrichtigungen.mitarbeiter_id == self.aktueller_nutzer_id)

        result = session.execute(stmt).scalars().all()
        self.benachrichtigungen = result

    def update_passwort(self):
        """
        Aktualisiert das Passwort des angemeldeten Benutzers.
        
        Validiert die Eingaben (beide Felder ausgefüllt, identisch) und
        speichert das neue Passwort in der Datenbank.
        """
        if not self.neues_passwort:
            self.feedback_neues_passwort = "Bitte gebe ein passwort ein"
            return
        elif  not self.neues_passwort_wiederholung:
            self.feedback_neues_passwort = "Bitte wiederhole das Passwort"
            return
        elif self.neues_passwort != self.neues_passwort_wiederholung:
            self.feedback_neues_passwort = "Die Passwörter müssen übereinstimmen"
            return
        else:
            stmt = select(mitarbeiter).where(mitarbeiter.mitarbeiter_id == self.aktueller_nutzer_id)
            nutzer = session.execute(stmt).scalar_one_or_none()
            nutzer.password = self.neues_passwort
            session.commit()
            self.feedback_neues_passwort = "Passwort erfolgreich geändert"
            return



    def stempel_hinzufügen(self):
        """
        Fügt einen neuen Zeitstempel mit aktueller Uhrzeit hinzu.
        
        Erstellt einen neuen Zeiteintrag mit der aktuellen Uhrzeit und
        dem heutigen Datum.
        """


        stempel = Zeiteintrag(
            mitarbeiter_id = self.aktueller_nutzer_id,
            zeit = datetime.now().time(),
            datum = date.today()
        )
        session.add(stempel)
        session.commit()

    def manueller_stempel_hinzufügen(self):
        """
        Fügt einen manuellen Zeitstempel mit gewähltem Datum/Uhrzeit hinzu.
        
        Erstellt einen Zeiteintrag mit vom Benutzer angegebenen Datum
        und Uhrzeit (z.B. zum Nachtragen vergessener Stempel).
        """
        stempel = Zeiteintrag(
            mitarbeiter_id = self.aktueller_nutzer_id,
            zeit =datetime.strptime(self.manueller_stempel_uhrzeit, "%H:%M").time(),
            datum = datetime.strptime(self.manueller_stempel_datum, "%d/%m/%Y").date()
        )
        session.add(stempel)
        session.commit()

        self.feedback_manueller_stempel = f"Stempel am {self.manueller_stempel_datum} um {self.manueller_stempel_uhrzeit} erfolgreich hinzugefügt"


    def urlaub_eintragen(self):
        """
        Trägt eine Abwesenheit (Urlaub/Krankheit) ein.
        
        Erstellt einen neuen Abwesenheitseintrag in der Datenbank.
        """
        if (self.neuer_abwesenheitseintrag_datum is None) or (self.neuer_abwesenheitseintrag_art is None):
            return
        elif (self.neuer_abwesenheitseintrag_art == "Urlaub") or (self.neuer_abwesenheitseintrag_art == "Krankheit"):
            neue_abwesenheit = Abwesenheit(
                mitarbeiter_id = self.aktueller_nutzer_id,
                datum = self.neuer_abwesenheitseintrag_datum,
                typ = self.neuer_abwesenheitseintrag_art

            )
        else:
            return

        session.add(neue_abwesenheit)
        session.commit()



    def checke_arbeitstage(self):
        """
        Prüft, ob an Arbeitstagen (Mo–Fr) seit letztem Login Stempel fehlen.
        
        Für jeden fehlenden Arbeitstag wird die tägliche Arbeitszeit von der 
        Gleitzeit abgezogen und eine Benachrichtigung erstellt. Urlaubstage
        werden berücksichtigt. Doppelte Benachrichtigungen/Abzüge werden verhindert.
        
        Returns:
            list: Liste der fehlenden Arbeitstage
        """
        """Prüft, ob an Arbeitstagen (Mo–Fr) seit letztem Login Stempel fehlen.
        Für jeden fehlenden Tag wird die tägliche Arbeitszeit von der Gleitzeit abgezogen.
        Doppelte Benachrichtigungen oder Abzüge werden verhindert.
        """
        if self.aktueller_nutzer_id is None:
            return

        # Nutzer laden
        stmt = select(mitarbeiter).where(mitarbeiter.mitarbeiter_id == self.aktueller_nutzer_id)
        nutzer = session.execute(stmt).scalar_one_or_none()
        if not nutzer:
            return

        letzter_login = nutzer.letzter_login
        gestern = date.today() - timedelta(days=1)

        # Fehlende Arbeitstage ermitteln
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

        # Tägliche Arbeitszeit berechnen
        tägliche_arbeitszeit = timedelta(hours=(self.aktueller_nutzer_vertragliche_wochenstunden / 5))

        abgezogene_tage = []
        for tag in fehlende_tage:
            # Prüfen, ob es für diesen Tag schon eine Benachrichtigung gibt
            exists_stmt = select(Benachrichtigungen).where(
                (Benachrichtigungen.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Benachrichtigungen.datum == tag) &
                (Benachrichtigungen.benachrichtigungs_code == 1)
            )
            exists = session.execute(exists_stmt).scalar_one_or_none()

            # prüfen ob Urlaubstage vorhanden sind
            urlaubs_stmt = select(Abwesenheit).where(
                (Abwesenheit.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Abwesenheit.datum == tag) 
            )
            exist_urlaub = session.execute(urlaubs_stmt).scalar_one_or_none()

            if not exists and not exist_urlaub:
                # Nur wenn noch keine Benachrichtigung existiert → Gleitzeit abziehen
                self.aktueller_nutzer_gleitzeit -= tägliche_arbeitszeit.total_seconds() / 3600
                nutzer.gleitzeit = self.aktueller_nutzer_gleitzeit

                benachrichtigung = Benachrichtigungen(
                    mitarbeiter_id=self.aktueller_nutzer_id,
                    benachrichtigungs_code=1,
                    datum=tag
                )
                session.add(benachrichtigung)
                session.commit()
                abgezogene_tage.append(tag)

        return fehlende_tage   
    
    def checke_stempel(self):
        """
        Prüft, ob an Arbeitstagen eine ungerade Anzahl von Stempeln vorliegt.
        
        Eine ungerade Anzahl bedeutet, dass entweder die Einstempelung oder
        Ausstempelung fehlt. Für jeden betroffenen Tag wird eine Benachrichtigung
        (Code 2) erstellt.
        
        Returns:
            list: Liste der Tage mit ungerader Stempelanzahl
        """
        if self.aktueller_nutzer_id is None:
            return


        stmt = select(mitarbeiter).where(mitarbeiter.mitarbeiter_id == self.aktueller_nutzer_id)
        nutzer = session.execute(stmt).scalar_one_or_none()
        if not nutzer:
            return

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
                stempel_anzahl = session.execute(stmt).scalars().all()
                if len(stempel_anzahl) % 2 != 0:
                    ungerade_tage.append(tag)
            tag += timedelta(days=1)

        self.feedback_stempel = f"An den Tagen {ungerade_tage} fehlt ein Stempel, bitte tragen sie diesen nach"

        for tag in ungerade_tage:
            benachrichtigung = Benachrichtigungen(mitarbeiter_id = self.aktueller_nutzer_id,
                                                  benachrichtigungs_code = 2,
                                                  datum = tag)
            try:
                session.add(benachrichtigung)
                session.commit()
            except IntegrityError:
                session.rollback()

        return ungerade_tage
    
    def checke_ruhezeiten(self):
        """
        Prüft, ob zwischen zwei Arbeitstagen die gesetzliche Ruhezeit von 11 Stunden eingehalten wurde.
        
        Berücksichtigt nur Tage bis gestern (heutiger Tag wird ignoriert) und
        nur Werktage (Mo-Fr). Bei Verstößen wird eine Benachrichtigung (Code 3)
        erstellt. Doppelte Benachrichtigungen werden vermieden.
        """
        """
        Prüft, ob zwischen zwei Arbeitstagen die gesetzliche Ruhezeit von 11 Stunden eingehalten wurde.
        Berücksichtigt nur Tage bis gestern (heutiger Tag wird ignoriert).
        Bei Verstößen wird eine Benachrichtigung mit Code 3 erstellt.
        Doppelte Benachrichtigungen werden vermieden.
        """
        if self.aktueller_nutzer_id is None:
            return

        heute = date.today()
        gestern = heute - timedelta(days=1)


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

  
            # In Python, weekday() returns 5 for Saturday and 6 for Sunday.
            # This logic skips weekends for rest period checking.
            if tag_heute.weekday() >= 5 or tag_morgen.weekday() >= 5:
                continue

            ende_heute = max(tage[tag_heute])
            beginn_morgen = min(tage[tag_morgen])

            ende_dt = datetime.combine(tag_heute, ende_heute)
            beginn_dt = datetime.combine(tag_morgen, beginn_morgen)

            differenz = beginn_dt - ende_dt

            if differenz < timedelta(hours=11):
                # Prüfen, ob schon Benachrichtigung existiert
                exists_stmt = select(Benachrichtigungen).where(
                    (Benachrichtigungen.mitarbeiter_id == self.aktueller_nutzer_id) &
                    (Benachrichtigungen.datum == tag_morgen) &
                    (Benachrichtigungen.benachrichtigungs_code == 3)
                )
                exists = session.execute(exists_stmt).scalar_one_or_none()

                if not exists:
                    benachrichtigung = Benachrichtigungen(
                        mitarbeiter_id=self.aktueller_nutzer_id,
                        benachrichtigungs_code=3,
                        datum=tag_morgen
                    )
                    session.add(benachrichtigung)
                    session.commit()
                    verletzungen.append((tag_heute, tag_morgen, differenz))

    def checke_durchschnittliche_arbeitszeit(self):
        """
        Prüft die durchschnittliche Arbeitszeit der letzten 6 Monate (24 Wochen).
        
        Erstellt eine Benachrichtigung (Code 4), wenn der Durchschnitt der
        täglichen Arbeitszeit 8 Stunden überschreitet (gemäß ArbZG).
        """
        if self.aktueller_nutzer_id is None:
            return

    
        end_datum = date.today() - timedelta(days=1)
        start_datum = end_datum - timedelta(weeks=24)


        stmt = select(Zeiteintrag).where(
            (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
            (Zeiteintrag.datum >= start_datum) &
            (Zeiteintrag.datum <= end_datum)
        ).order_by(Zeiteintrag.datum, Zeiteintrag.zeit)
        
        einträge = session.scalars(stmt).all()

        if not einträge:
            return

        # Arbeitsstunden pro Tag berechnen
        arbeitstage = {}
        i = 0
        while i < len(einträge) - 1:
            calc = CalculateTime(einträge[i], einträge[i + 1])
            if calc:
                calc.gesetzliche_pausen_hinzufügen()
                if calc.datum in arbeitstage:
                    arbeitstage[calc.datum] += calc.gearbeitete_zeit
                else:
                    arbeitstage[calc.datum] = calc.gearbeitete_zeit
                i += 2
            else:
                i += 1
        
        # Nur Tage mit Einträgen für die Durchschnittsberechnung berücksichtigen
        if not arbeitstage:
            return

      
        gesamte_arbeitszeit = sum(arbeitstage.values(), timedelta())
        anzahl_arbeitstage = len(arbeitstage)
        
        durchschnittliche_arbeitszeit = gesamte_arbeitszeit / anzahl_arbeitstage

       
        if durchschnittliche_arbeitszeit > timedelta(hours=8):
            
       
            exists_stmt = select(Benachrichtigungen).where(
                (Benachrichtigungen.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Benachrichtigungen.benachrichtigungs_code == 4) &
                (Benachrichtigungen.datum == date.today())
            )
            exists = session.execute(exists_stmt).scalar_one_or_none()

            if not exists:
                benachrichtigung = Benachrichtigungen(
                    mitarbeiter_id=self.aktueller_nutzer_id,
                    benachrichtigungs_code=4,
                    datum=date.today()  # Datum der Prüfung
                )
                session.add(benachrichtigung)
                session.commit()

    def checke_max_arbeitszeit(self):
        """
        Prüft, ob die maximale Arbeitszeit von 10 Stunden pro Tag überschritten wurde.
        
        Überprüft alle noch nicht validierten Zeiteinträge bis gestern.
        Bei Überschreitung wird eine Benachrichtigung (Code 5) erstellt.
        Dies entspricht den Anforderungen des ArbZG § 3.
        """
        stmt = select(Zeiteintrag).where(
            (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
            (Zeiteintrag.validiert == 0) &
            (Zeiteintrag.datum <= date.today() - timedelta(days=1))
        ).order_by(Zeiteintrag.datum, Zeiteintrag.zeit)
        einträge = session.scalars(stmt).all()
        tage = {}

        for daten in einträge:
            if daten.datum in tage:
                continue
            else:
                tage[daten.datum] = 0

        for dates in tage.keys():
            stmt = select(Zeiteintrag).where(
            (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
            (Zeiteintrag.datum == dates)
        ).order_by(Zeiteintrag.datum, Zeiteintrag.zeit)
            einträge = session.scalars(stmt).all()
            i = 0
            while i < len(einträge) - 1:
                calc = CalculateTime(einträge[i], einträge[i+1])
                if calc:
        
                    if calc.datum in tage:
                        calc.gesetzliche_pausen_hinzufügen()
                        tage[calc.datum] += calc.gearbeitete_zeit
                    else:
                        calc.gesetzliche_pausen_hinzufügen()
                        tage[calc.datum] = calc.gearbeitete_zeit


                    i += 2  
                else:
                    i += 1

        for datum, arbeitszeit in tage.items():
            if arbeitszeit > timedelta(hours=10):
                exists_stmt = select(Benachrichtigungen).where(
                    (Benachrichtigungen.mitarbeiter_id == self.aktueller_nutzer_id) &
                    (Benachrichtigungen.benachrichtigungs_code == 5) &
                    (Benachrichtigungen.datum == datum)
                )
                exists = session.execute(exists_stmt).scalar_one_or_none()

                if not exists:
                    benachrichtigung = Benachrichtigungen(
                        mitarbeiter_id=self.aktueller_nutzer_id,
                        benachrichtigungs_code=5,
                        datum=datum  # Datum der Prüfung
                    )
                    session.add(benachrichtigung)
                    session.commit()


    def berechne_gleitzeit(self):
        """
        Berechnet die Gleitzeit basierend auf noch nicht validierten Zeiteinträgen.
        
        Verarbeitet paarweise Zeitstempel (Ein-/Ausstempelung), berechnet die
        Arbeitszeit unter Berücksichtigung gesetzlicher Pausen, zieht die
        Sollarbeitszeit ab und aktualisiert das Gleitzeitkonto.
        Bereits validierte Einträge werden als solche markiert.
        """
        stmt = select(Zeiteintrag).where(
            (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
            (Zeiteintrag.validiert == 0) &
            (Zeiteintrag.datum <= date.today() - timedelta(days=1))
        ).order_by(Zeiteintrag.datum, Zeiteintrag.zeit)
        einträge = session.scalars(stmt).all()
        for e in einträge:
            print(e.datum, e.zeit)
 
        arbeitstage ={}
        benutzte_einträge = [] 




        i = 0
        while i < len(einträge) - 1:
            calc = CalculateTime(einträge[i], einträge[i+1])
            if calc:
    
                if calc.datum in arbeitstage:
                    calc.gesetzliche_pausen_hinzufügen()
                    arbeitstage[calc.datum] += calc.gearbeitete_zeit
                else:
                    calc.gesetzliche_pausen_hinzufügen()
                    arbeitstage[calc.datum] = calc.gearbeitete_zeit

                benutzte_einträge.append(einträge[i])
                benutzte_einträge.append(einträge[i+1])
                i += 2  
            else:
                i += 1  

        tägliche_arbeitszeit = timedelta( hours=(self.aktueller_nutzer_vertragliche_wochenstunden / 5))

        for datum, arbeitszeit in arbeitstage.items():
             exists_stmt = select(Benachrichtigungen).where(
                (Benachrichtigungen.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Benachrichtigungen.datum == datum) &
                (Benachrichtigungen.benachrichtigungs_code == 1)
             )
             exists = session.execute(exists_stmt).scalar_one_or_none()

             unvalidierte_stmt = select(Zeiteintrag).where(
                (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Zeiteintrag.datum == datum) &
                (Zeiteintrag.validiert == 1)
            )
             unvalidierte = session.execute(unvalidierte_stmt).scalars().all()
        
             if (not exists) and (not unvalidierte): 
                arbeitstage[datum] -= tägliche_arbeitszeit


        for e in benutzte_einträge:
            e.validiert = True
            session.commit()

        gleitzeit_delta = sum(arbeitstage.values(), timedelta())
        gleitzeit_stunden = float(gleitzeit_delta.total_seconds() / 3600)
        self.aktueller_nutzer_gleitzeit += gleitzeit_stunden


        nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
        if nutzer:
            nutzer.gleitzeit = self.aktueller_nutzer_gleitzeit
            session.commit()

    def berechne_durchschnittliche_gleitzeit(self, start_datum: date, end_datum: date, include_missing_days: bool = False):
        """
        Berechnet die durchschnittliche tägliche Gleitzeit im angegebenen Zeitraum.
        
        Args:
            start_datum (date): Startdatum der Auswertung (inklusive)
            end_datum (date): Enddatum der Auswertung (inklusive)
            include_missing_days (bool): 
                Wenn True -> Tage ohne Stempel werden als 0 Stunden Arbeit (negativ) gewertet.
                Wenn False -> Nur Tage mit Stempel werden berücksichtigt.
        
        Returns:
            dict: Enthält 'durchschnitt_gleitzeit_stunden', 'anzahl_tage', 'berücksichtigte_tage'
                  oder 'error' bei ungültigen Parametern
        """
        """
        Berechnet die durchschnittliche tägliche Gleitzeit im angegebenen Zeitraum.
        
        Parameter:
            start_datum (date): Startdatum der Auswertung (inklusive)
            end_datum (date): Enddatum der Auswertung (inklusive)
            include_missing_days (bool): 
                Wenn True -> Tage ohne Stempel werden als 0 Stunden Arbeit (negativ) gewertet.
                Wenn False -> Nur Tage mit Stempel werden berücksichtigt.
        
        Rückgabe:
            dict mit 'durchschnitt_gleitzeit_stunden', 'anzahl_tage', 'berücksichtigte_tage'
        """
        if self.aktueller_nutzer_id is None:
            return {"error": "Kein Nutzer angemeldet"}

        if start_datum > end_datum:
            return {"error": "Startdatum liegt nach Enddatum"}

        # Nutzer laden
        stmt = select(mitarbeiter).where(mitarbeiter.mitarbeiter_id == self.aktueller_nutzer_id)
        nutzer = session.execute(stmt).scalar_one_or_none()
        if not nutzer:
            return {"error": "Nutzer nicht gefunden"}

        # Vertragliche tägliche Arbeitszeit
        tägliche_arbeitszeit = timedelta(hours=(self.aktueller_nutzer_vertragliche_wochenstunden / 5))

        # Zeiteinträge im Zeitraum abrufen
        stmt = select(Zeiteintrag).where(
            (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
            (Zeiteintrag.datum >= start_datum) &
            (Zeiteintrag.datum <= end_datum)
        ).order_by(Zeiteintrag.datum, Zeiteintrag.zeit)

        einträge = session.scalars(stmt).all()
        if not einträge:
            return {"durchschnitt_gleitzeit_stunden": 0.0, "anzahl_tage": 0, "berücksichtigte_tage": []}

        # Arbeitszeiten pro Tag berechnen
        arbeitstage = {}
        i = 0
        while i < len(einträge) - 1:
            calc = CalculateTime(einträge[i], einträge[i + 1])
            if calc:
                calc.gesetzliche_pausen_hinzufügen()
                if calc.datum in arbeitstage:
                    arbeitstage[calc.datum] += calc.gearbeitete_zeit
                else:
                    arbeitstage[calc.datum] = calc.gearbeitete_zeit
                i += 2
            else:
                i += 1

        # Alle Tage im Bereich (nur Mo–Fr)
        alle_tage = [start_datum + timedelta(days=i) for i in range((end_datum - start_datum).days + 1)]
        arbeitstage_werktage = [t for t in alle_tage if t.weekday() < 5]

        # Gleitzeitdifferenz berechnen
        gleitzeit_differenzen = []
        berücksichtigte_tage = []

        for tag in arbeitstage_werktage:
            if tag in arbeitstage:
                differenz = arbeitstage[tag] - tägliche_arbeitszeit
                gleitzeit_differenzen.append(differenz)
                berücksichtigte_tage.append(tag)
            elif include_missing_days:
                # Fehlender Tag wird als volle Sollzeit-Minus gewertet
                differenz = -tägliche_arbeitszeit
                gleitzeit_differenzen.append(differenz)
                berücksichtigte_tage.append(tag)
            else:
                # Tag wird ignoriert
                continue

        if not gleitzeit_differenzen:
            return {"durchschnitt_gleitzeit_stunden": 0.0, "anzahl_tage": 0, "berücksichtigte_tage": []}

        # Durchschnitt berechnen
        gesamt_gleitzeit = sum(gleitzeit_differenzen, timedelta())
        durchschnitt = gesamt_gleitzeit / len(gleitzeit_differenzen)
        durchschnitt_stunden = round(durchschnitt.total_seconds() / 3600, 2)

        return {
            "durchschnitt_gleitzeit_stunden": durchschnitt_stunden,
            "anzahl_tage": len(gleitzeit_differenzen),
            "berücksichtigte_tage": berücksichtigte_tage
        }
    





        


class ModellLogin():
    """
    Model-Klasse für Login und Benutzerregistrierung.
    
    Verwaltet die Authentifizierung und Erstellung neuer Benutzer.
    
    Attributes:
        neuer_nutzer_* (str): Daten für die Registrierung eines neuen Benutzers
        neuer_nutzer_rückmeldung (str): Feedback-Text für Registrierung
        anmeldung_name/passwort (str): Login-Daten
        anmeldung_rückmeldung (str): Feedback-Text für Login
        anmeldung_mitarbeiter_id_validiert (int): ID des erfolgreich angemeldeten Benutzers
    """

    def __init__(self):
       """Initialisiert alle Attribute des Login-Models."""
       self.neuer_nutzer_name = None
       self.neuer_nutzer_passwort = None
       self.neuer_nutzer_passwort_val = None
       self.neuer_nutzer_vertragliche_wochenstunden = None
       self.neuer_nutzer_geburtsdatum = None
       self.neuer_nutzer_rückmeldung = ""

       self.anmeldung_name = None
       self.anmeldung_passwort = None
       self.anmeldung_rückmeldung = ""
       self.anmeldung_mitarbeiter_id_validiert = None
       

    def neuen_nutzer_anlegen(self):
         """
         Erstellt einen neuen Benutzer in der Datenbank.
         
         Validiert alle Eingaben (vollständig, korrekt formatiert, Passwörter identisch)
         und erstellt bei Erfolg einen neuen Mitarbeiter-Eintrag.
         """
         # Prüfe auf None für jedes Attribut
        if not self.neuer_nutzer_name:
            self.neuer_nutzer_rückmeldung = "Bitte gib einen Namen ein"
            return
        if not self.neuer_nutzer_passwort:
            self.neuer_nutzer_rückmeldung = "Bitte gib ein Passwort ein"
            return
        if not self.neuer_nutzer_passwort_val:
            self.neuer_nutzer_rückmeldung = "Bitte wiederhole das Passwort"
            return
        if not self.neuer_nutzer_vertragliche_wochenstunden:
            self.neuer_nutzer_rückmeldung = "Bitte wähle deine Arbeitszeit aus"
            return
        if not self.neuer_nutzer_geburtsdatum:
            self.neuer_nutzer_rückmeldung = "Bitte wähle ein Geburtsdatum aus"
            return
               
        try:
            self.neuer_nutzer_geburtsdatum = datetime.strptime(self.neuer_nutzer_geburtsdatum, "%d/%m/%Y").date()
        except ValueError:
            self.neuer_nutzer_rückmeldung = "Bitte wähle ein Datum aus"
            return
        
        try:
            self.neuer_nutzer_vertragliche_wochenstunden = int(self.neuer_nutzer_vertragliche_wochenstunden)
        except ValueError:
            self.neuer_nutzer_rückmeldung = "Bitte wähle deine Arbeitszeit aus"
            return
        
        if self.neuer_nutzer_passwort != self.neuer_nutzer_passwort_val:
            self.neuer_nutzer_rückmeldung = "Die Passwörter müssen übereinstimmen"
        
        else :
            neuer_nutzer = mitarbeiter(name = self.neuer_nutzer_name, 
                                   password = self.neuer_nutzer_passwort, 
                                   vertragliche_wochenstunden = self.neuer_nutzer_vertragliche_wochenstunden, 
                                   geburtsdatum = self.neuer_nutzer_geburtsdatum,
                                   letzter_login = date.today()) 
        
            session.add(neuer_nutzer)
            session.commit()
            self.neuer_nutzer_rückmeldung = "Der Account wurde erfolgreich angelegt" 



    def login(self):
        """
        Authentifiziert einen Benutzer.
        
        Überprüft Benutzername und Passwort gegen die Datenbank.
        Bei Erfolg wird die Mitarbeiter-ID gespeichert.
        
        Returns:
            bool: True bei erfolgreichem Login, None bei Fehler
        """
        stmt = select(mitarbeiter).where(mitarbeiter.name == self.anmeldung_name)
        nutzer = session.execute(stmt).scalar_one_or_none()

        if nutzer is None:
            self.anmeldung_rückmeldung = "Passwort oder Nutzername falsch"

        elif nutzer.password == self.anmeldung_passwort:
            self.anmeldung_rückmeldung = "Login erfolgreich"
            self.anmeldung_mitarbeiter_id_validiert = nutzer.mitarbeiter_id
            return True

        else:
            self.anmeldung_rückmeldung = "Passwort oder Nutzername falsch"