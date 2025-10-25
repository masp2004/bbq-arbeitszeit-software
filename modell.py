from sqlalchemy import Column, Integer, String, Date, create_engine, select, Time, Boolean, ForeignKey, UniqueConstraint, CheckConstraint
import sqlalchemy.orm as saorm
from sqlalchemy.exc import IntegrityError
from datetime import datetime, date, timedelta, time
import holidays 

engine = create_engine("sqlite:///system.db", echo=True)
Base = saorm.declarative_base()
Session = saorm.sessionmaker(bind=engine)
session = Session()

class mitarbeiter(Base):
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

    def is_minor_on_date(self,datum):
            """Prüft, ob der Mitarbeiter an bestimmten datum minderjährig ist (unter 18)."""
            if not self.geburtsdatum:
                return False
            
            age = datum.year - self.geburtsdatum.year - ((datum.month, datum.day) < (self.geburtsdatum.month, self.geburtsdatum.day))
            return age < 18

class Abwesenheit(Base):
    __tablename__ = "abwesenheiten"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mitarbeiter_id = Column(Integer, ForeignKey("users.mitarbeiter_id"), nullable=False)
    datum = Column(Date, nullable=False)
    typ = Column(String, CheckConstraint("typ IN ('Urlaub', 'Krankheit', 'Fortbildung', 'Sonstiges')"), nullable=False)
    genehmigt = Column(Boolean, nullable=False, default=False)


class Zeiteintrag(Base):
    __tablename__ = "zeiteinträge"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mitarbeiter_id = Column(Integer, ForeignKey("users.mitarbeiter_id"), nullable=False)
    zeit = Column(Time, nullable=False)
    datum = Column(Date, nullable=False)
    validiert = Column(Boolean, nullable=False, default=False) 

class Benachrichtigungen(Base):
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
        5:["Achung am", "wurde die maximale gesetzlich zulässsige Arbeitszeit überschritten."],
        6: ["Achtung, am", "wurde an einem Sonn- oder Feiertag gearbeitet."],
        7: ["In der Woche vom", "wurde die maximale Wochenarbeitszeit von 40 Stunden für Minderjährige überschritten."],
        8: ["In der Woche vom", "wurde an mehr als 5 Tagen gearbeitet, was für Minderjährige nicht zulässig ist."]
    }

    __table_args__ = (
        UniqueConstraint("mitarbeiter_id", "benachrichtigungs_code", "datum", name="uq_benachrichtigung_unique"),
    )

    def create_fehlermeldung(self):

        if self.benachrichtigungs_code == 1:
            return f"{self.CODES[1.1]} {self.datum} {self.CODES[1.2]}"
        elif self.benachrichtigungs_code == 2:
            return f"{self.CODES[2.1]} {self.datum} {self.CODES[2.2]}"
        
        elif self.benachrichtigungs_code == 3:
            return f"{self.CODES[3][0]} {self.datum} {self.CODES[3][1]}"
        
        elif self.benachrichtigungs_code ==4:
            return self.CODES[4]
        
        elif self.benachrichtigungs_code == 5:
            return f"{self.CODES[5][0]} {self.datum} {self.CODES[5][1]}"

        elif self.benachrichtigungs_code == 6:
            return f"{self.CODES[6][0]} {self.datum} {self.CODES[6][1]}"
        
        elif self.benachrichtigungs_code == 7:
            return f"{self.CODES[7][0]} {self.datum.strftime('%d.%m.%Y')} {self.CODES[7][1]}"

        elif self.benachrichtigungs_code == 8:
            return f"{self.CODES[8][0]} {self.datum.strftime('%d.%m.%Y')} {self.CODES[8][1]}"



class CalculateTime():
     def __new__(cls, eintrag1, eintrag2, nutzer):
         if eintrag1.datum != eintrag2.datum:
             return None
         return super().__new__(cls)

     def __init__(self, eintrag1, eintrag2, nutzer):
         self.nutzer = nutzer
         self.datum = eintrag1.datum
         self.startzeit = eintrag1.zeit
         self.endzeit = eintrag2.zeit
         self.start_dt = datetime.combine(self.datum, self.startzeit)
         self.end_dt = datetime.combine(self.datum, self.endzeit)


         self.gearbeitete_zeit = self.end_dt - self.start_dt  

     def gesetzliche_pausen_hinzufügen(self):
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
        Entfernt Arbeitszeit, die außerhalb des erlaubten Fensters liegt.
        Minderjährige: 06:00 - 20:00 Uhr
        Erwachsene: 06:00 - 22:00 Uhr
        """

        is_minor = self.nutzer.is_minor_on_date(self.datum)
        nachtruhe_zeit = time(20, 0) if is_minor else time(22, 0)
        # Definition der "verbotenen" Zeitfenster am selben Tag
        morgenruhe_ende = datetime.combine(self.datum, time(6, 0))
        nachtruhe_start = datetime.combine(self.datum, nachtruhe_zeit)

        abzuziehende_zeit = timedelta()

        # 1. Überschneidung mit der Morgenruhe (00:00 - 06:00)
        #    max() findet den Startpunkt der Überschneidung.
        #    min() findet den Endpunkt der Überschneidung.
        overlap_start_morgen = max(self.start_dt, datetime.combine(self.datum, time(0, 0)))
        overlap_end_morgen = min(self.end_dt, morgenruhe_ende)

        if overlap_end_morgen > overlap_start_morgen:
            abzuziehende_zeit += overlap_end_morgen - overlap_start_morgen

        # 2. Überschneidung mit der Nachtruhe (22:00 - 24:00)
        overlap_start_nacht = max(self.start_dt, nachtruhe_start)
        overlap_end_nacht = min(self.end_dt, datetime.combine(self.datum, time(23, 59, 59)))

        if overlap_end_nacht > overlap_start_nacht:
            abzuziehende_zeit += overlap_end_nacht - overlap_start_nacht
            
        # Die berechnete "verbotene" Arbeitszeit von der Gesamtzeit abziehen
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

    def get_employees(self):
        stmt = select(mitarbeiter.name).where(mitarbeiter.vorgesetzter_id == self.aktueller_nutzer_id)
        names = session.scalars(stmt).all()

        names.append(self.aktueller_nutzer_name)
        self.mitarbeiter = names

    def get_id(self):
        stmt = select(mitarbeiter.mitarbeiter_id).where(mitarbeiter.name == self.aktuelle_kalendereinträge_für_name)
        employee_id = session.execute(stmt).scalar_one_or_none()

        if employee_id:
            self.aktuelle_kalendereinträge_für_id = employee_id
        else:
            self.aktuelle_kalendereinträge_für_id = self.aktueller_nutzer_id

    def get_zeiteinträge(self):
        if self.aktueller_nutzer_id is None or self.bestimmtes_datum is None:
            return
        nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
        date = datetime.strptime(self.bestimmtes_datum, "%d.%m.%Y").date()


        stmt = select(
            Zeiteintrag
            ).where(
                (Zeiteintrag.mitarbeiter_id == self.aktuelle_kalendereinträge_für_id)&(Zeiteintrag.datum == date)
                ).order_by(
                    Zeiteintrag.datum, Zeiteintrag.zeit
                    )
        einträge = session.scalars(stmt).all()
        einträge = session.scalars(stmt).all()
        
        einträge_mit_validierung = []
        for eintrag in einträge:
            is_unvalid = False
            stempelzeit = eintrag.zeit
            
            # Prüfen ob Nutzer an diesem Tag minderjährig war
            if nutzer.is_minor_on_date(date):
                # Für Minderjährige: zwischen 6 und 20 Uhr
                if stempelzeit < time(6, 0) or stempelzeit > time(20, 0):
                    is_unvalid = True
            else:
                # Für Erwachsene: zwischen 6 und 22 Uhr
                if stempelzeit < time(6, 0) or stempelzeit > time(22, 0):
                    is_unvalid = False
            
            einträge_mit_validierung.append([eintrag, is_unvalid])

            self.zeiteinträge_bestimmtes_datum = einträge_mit_validierung


    def get_user_info(self):

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
        if self.aktueller_nutzer_gleitzeit >= self.aktueller_nutzer_ampel_grün:
            self.ampel_status = "green"

        elif (self.aktueller_nutzer_gleitzeit < self.aktueller_nutzer_ampel_grün) & (self.aktueller_nutzer_gleitzeit > self.aktueller_nutzer_ampel_rot):
            self.ampel_status = "yellow"
    
        else:
            self.ampel_status = "red"


    def get_messages(self):

        stmt = select(Benachrichtigungen).where(Benachrichtigungen.mitarbeiter_id == self.aktueller_nutzer_id)

        result = session.execute(stmt).scalars().all()
        self.benachrichtigungen = result

    def update_passwort(self):
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


        stempel = Zeiteintrag(
            mitarbeiter_id = self.aktueller_nutzer_id,
            zeit = datetime.now().time(),
            datum = date.today()
        )
        session.add(stempel)
        session.commit()
    
    def get_stamps_for_today(self):
        """
        Holt alle Zeiteinträge für den aktuellen Nutzer am heutigen Tag.
        """
        if not self.aktueller_nutzer_id:
            return []

        heute = date.today()
        stmt = select(Zeiteintrag).where(
            (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
            (Zeiteintrag.datum == heute)
        ).order_by(Zeiteintrag.zeit)

        einträge = session.scalars(stmt).all()
        return einträge


    def manueller_stempel_hinzufügen(self):
        stempel = Zeiteintrag(
            mitarbeiter_id = self.aktueller_nutzer_id,
            zeit =datetime.strptime(self.manueller_stempel_uhrzeit, "%H:%M").time(),
            datum = datetime.strptime(self.nachtragen_datum, "%d/%m/%Y").date()
        )
        session.add(stempel)
        session.commit()

        self.feedback_manueller_stempel = f"Stempel am {self.nachtragen_datum} um {self.manueller_stempel_uhrzeit} erfolgreich hinzugefügt"


    def urlaub_eintragen(self):
        if (self.nachtragen_datum is None) or (self.neuer_abwesenheitseintrag_art is None):
            return
        elif (self.neuer_abwesenheitseintrag_art == "Urlaub") or (self.neuer_abwesenheitseintrag_art == "Krankheit"):
            neue_abwesenheit = Abwesenheit(
                mitarbeiter_id = self.aktueller_nutzer_id,
                datum = datetime.strptime(self.nachtragen_datum, "%d/%m/%Y").date(),
                typ = self.neuer_abwesenheitseintrag_art

            )
        else:
            return

        session.add(neue_abwesenheit)
        session.commit()


    def checke_wochenstunden_minderjaehrige(self):
        """Prüft, ob minderjährige Mitarbeiter die 40-Stunden-Woche überschritten haben."""
        if self.aktueller_nutzer_id is None:
            return

        nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
        if not nutzer or not nutzer.is_minor_on_date(datum=nutzer.letzter_login):
                    return  # Funktion nur für aktuell Minderjährige relevant

        start_datum = nutzer.letzter_login
        end_datum = date.today() - timedelta(days=1)
        
        current_date = start_datum
        while current_date <= end_datum:
            # Finde den Montag der aktuellen Woche
            start_of_week = current_date - timedelta(days=current_date.weekday())
            end_of_week = start_of_week + timedelta(days=6)

            # Nur abgeschlossene Wochen prüfen
            if end_of_week > end_datum:
                break

            # Zeiteinträge für diese Woche laden
            stmt = select(Zeiteintrag).where(
                (Zeiteintrag.mitarbeiter_id == nutzer.mitarbeiter_id) &
                (Zeiteintrag.datum.between(start_of_week, end_of_week))
            ).order_by(Zeiteintrag.datum, Zeiteintrag.zeit)
            einträge_woche = session.scalars(stmt).all()

            if not einträge_woche:
                current_date = end_of_week + timedelta(days=1)
                continue

            # Arbeitszeit für die Woche berechnen
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
                # Benachrichtigung erstellen, falls noch nicht vorhanden
                exists_stmt = select(Benachrichtigungen).where(
                    (Benachrichtigungen.mitarbeiter_id == nutzer.mitarbeiter_id) &
                    (Benachrichtigungen.benachrichtigungs_code == 7) &
                    (Benachrichtigungen.datum == start_of_week)
                )
                if not session.execute(exists_stmt).scalar_one_or_none():
                    benachrichtigung = Benachrichtigungen(
                        mitarbeiter_id=nutzer.mitarbeiter_id,
                        benachrichtigungs_code=7,
                        datum=start_of_week
                    )
                    session.add(benachrichtigung)
                    session.commit()

            current_date = end_of_week + timedelta(days=1)


    def checke_arbeitstage_pro_woche_minderjaehrige(self):
            """Prüft, ob minderjährige Mitarbeiter an mehr als 5 Tagen pro Woche gearbeitet haben."""
            if self.aktueller_nutzer_id is None:
                return

            nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
            if not nutzer or not nutzer.is_minor_on_date(nutzer.letzter_login):
                return # Funktion nur für aktuell Minderjährige relevant

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

                # Eindeutige Arbeitstage in der Woche zählen
                stmt = select(Zeiteintrag.datum).distinct().where(
                    (Zeiteintrag.mitarbeiter_id == nutzer.mitarbeiter_id) &
                    (Zeiteintrag.datum.between(start_of_week, end_of_week))
                )
                arbeitstage_count = len(session.scalars(stmt).all())

                if arbeitstage_count > 5:
                    # Benachrichtigung erstellen, falls noch nicht vorhanden
                    exists_stmt = select(Benachrichtigungen).where(
                        (Benachrichtigungen.mitarbeiter_id == nutzer.mitarbeiter_id) &
                        (Benachrichtigungen.benachrichtigungs_code == 8) &
                        (Benachrichtigungen.datum == start_of_week)
                    )
                    if not session.execute(exists_stmt).scalar_one_or_none():
                        benachrichtigung = Benachrichtigungen(
                            mitarbeiter_id=nutzer.mitarbeiter_id,
                            benachrichtigungs_code=8,
                            datum=start_of_week
                        )
                        session.add(benachrichtigung)
                        session.commit()

                current_date = end_of_week + timedelta(days=1)


    def checke_arbeitstage(self):
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
    
    def checke_sonn_feiertage(self):
        """
        Prüft, ob seit dem letzten Login an Sonn- oder Feiertagen gestempelt wurde.
        Erstellt eine Benachrichtigung (Code 6) für jeden Verstoß.
        """
        if self.aktueller_nutzer_id is None:
            return

        # Nutzer laden für letztes Login-Datum
        nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
        if not nutzer or not nutzer.letzter_login:
            return

        start_datum = nutzer.letzter_login
        end_datum = date.today() - timedelta(days=1)

        # Deutsche Feiertage für den relevanten Zeitraum abrufen
        jahre = set(range(start_datum.year, end_datum.year + 1))
        de_holidays = holidays.Germany(years=list(jahre))

        # Alle gestempelten Tage im Zeitraum abrufen
        stmt = select(Zeiteintrag.datum).distinct().where(
            (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
            (Zeiteintrag.datum >= start_datum) &
            (Zeiteintrag.datum <= end_datum)
        )
        gestempelte_tage = session.scalars(stmt).all()

        for tag in gestempelte_tage:
            # Prüfen, ob der Tag ein Sonntag (6) oder ein Feiertag ist
            if tag.weekday() == 6 or tag in de_holidays:
                
                # Prüfen, ob für diesen Tag schon eine Benachrichtigung existiert
                exists_stmt = select(Benachrichtigungen).where(
                    (Benachrichtigungen.mitarbeiter_id == self.aktueller_nutzer_id) &
                    (Benachrichtigungen.benachrichtigungs_code == 6) &
                    (Benachrichtigungen.datum == tag)
                )
                exists = session.execute(exists_stmt).scalar_one_or_none()

                if not exists:
                    # Neue Benachrichtigung erstellen
                    benachrichtigung = Benachrichtigungen(
                        mitarbeiter_id=self.aktueller_nutzer_id,
                        benachrichtigungs_code=6,
                        datum=tag
                    )
                    session.add(benachrichtigung)
                    session.commit()

    
    def checke_ruhezeiten(self):
        """
        Prüft, ob zwischen zwei Arbeitstagen die gesetzliche Ruhezeit eingehalten wurde.
        Minderjährige: 12 Stunden, Erwachsene: 11 Stunden.
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
        
        nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
        


        tage = {}
        for e in einträge:
            erforderliche_ruhezeit = timedelta(hours=12) if nutzer.is_minor_on_date(datum=e.datum) else timedelta(hours=11)
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

            if differenz < erforderliche_ruhezeit:
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
        Erstellt eine Benachrichtigung (Code 4), wenn der Durchschnitt 8 Stunden überschreitet.
        """
        if self.aktueller_nutzer_id is None:
            return
        nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)

    
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
            calc = CalculateTime(einträge[i], einträge[i + 1], nutzer)
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
        '''
        checkt ob Täglich mehr als die erlaubte Stundenzahl gearbeitet wurde.
        Minderjährige: 8 Stunden, Erwachsene: 10 Stunden.
        '''

        if self.aktueller_nutzer_id is None:
            return
        
        nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)

        
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
            (Zeiteintrag.datum <= dates)
        ).order_by(Zeiteintrag.datum, Zeiteintrag.zeit)
            einträge = session.scalars(stmt).all()
            i = 0
            while i < len(einträge) - 1:
                calc = CalculateTime(einträge[i], einträge[i+1], nutzer)
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
            max_stunden = timedelta(hours=8) if nutzer.is_minor_on_date(datum=datum) else timedelta(hours=10)
            if arbeitszeit > max_stunden:
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
        nutzer = session.get(mitarbeiter, self.aktueller_nutzer_id)
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
            calc = CalculateTime(einträge[i], einträge[i+1], nutzer)
            if calc:
    
                if calc.datum in arbeitstage:
                    calc.gesetzliche_pausen_hinzufügen()
                    calc.arbeitsfenster_beachten()
                    
                    arbeitstage[calc.datum] += calc.gearbeitete_zeit
                else:
                    calc.gesetzliche_pausen_hinzufügen()
                    calc.arbeitsfenster_beachten()
                    
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
            calc = CalculateTime(einträge[i], einträge[i + 1], nutzer)
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
    
    def kummuliere_gleitzeit(self):
        """
        Berechnet die kumulierte Gleitzeit für den aktuellen Monat, das Quartal und das Jahr.
        Nutzt dafür die Funktion `berechne_durchschnittliche_gleitzeit` und multipliziert
        den Durchschnitt mit der Anzahl der Tage, um die Gesamtsumme zu erhalten.
        Der Parameter `self.tage_ohne_stempel_beachten` steuert die Berechnung.
        """
        if self.aktueller_nutzer_id is None:
            # Sicherstellen, dass die Werte zurückgesetzt sind, wenn keine Berechnung möglich ist
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
            # Kumulierte Zeit = Durchschnitt * Anzahl der Tage
            self.kummulierte_gleitzeit_monat = round(
                ergebnis_monat["durchschnitt_gleitzeit_stunden"] , 2
            )
        else:
            self.kummulierte_gleitzeit_monat = 0.0

        # 2. Quartal berechnen
        aktuelles_quartal = (heute.month - 1) // 3 + 1
        start_monat_quartal = (aktuelles_quartal - 1) * 3 + 1
        start_quartal = heute.replace(month=start_monat_quartal, day=1)
        ergebnis_quartal = self.berechne_durchschnittliche_gleitzeit(start_quartal, heute, include_missing)
        if "error" not in ergebnis_quartal:
            self.kummulierte_gleitzeit_quartal = round(
                ergebnis_quartal["durchschnitt_gleitzeit_stunden"] , 2
            )
        else:
            self.kummulierte_gleitzeit_quartal = 0.0

        # 3. Jahr berechnen
        start_jahr = heute.replace(month=1, day=1)
        ergebnis_jahr = self.berechne_durchschnittliche_gleitzeit(start_jahr, heute, include_missing)
        if "error" not in ergebnis_jahr:
            self.kummulierte_gleitzeit_jahr = round(
                ergebnis_jahr["durchschnitt_gleitzeit_stunden"], 2
            )
        else:
            self.kummulierte_gleitzeit_jahr = 0.0
    
    





        


class ModellLogin():

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
        if not self.neuer_nutzer_grün:
            self.neuer_nutzer_rückmeldung = "Bitte gib einen grünen Grenzwert ein"
            return
        if not self.neuer_nutzer_rot:
            self.neuer_nutzer_rückmeldung = "Bitte gib einen roten Grenzwert ein"
            return
               
        try:
            self.neuer_nutzer_geburtsdatum = datetime.strptime(self.neuer_nutzer_geburtsdatum, "%d/%m/%Y").date()
        except ValueError:
            self.neuer_nutzer_rückmeldung = "Bitte wähle ein Datum aus"
            return
        
        try:
            self.neuer_nutzer_vertragliche_wochenstunden = int(self.neuer_nutzer_vertragliche_wochenstunden)
            self.neuer_nutzer_grün = int(self.neuer_nutzer_grün)
            self.neuer_nutzer_rot = int(self.neuer_nutzer_rot)
        except (ValueError, TypeError):
            self.neuer_nutzer_rückmeldung = "Arbeitszeit und Grenzwerte müssen Zahlen sein."
            return
        
        if self.neuer_nutzer_passwort != self.neuer_nutzer_passwort_val:
            self.neuer_nutzer_rückmeldung = "Die Passwörter müssen übereinstimmen"
            return

        # Vorgesetzten prüfen
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
            vertragliche_wochenstunden=self.neuer_nutzer_vertragliche_wochenstunden, 
            geburtsdatum=self.neuer_nutzer_geburtsdatum,
            letzter_login=date.today(),
            ampel_grün=self.neuer_nutzer_grün,
            ampel_rot=self.neuer_nutzer_rot,
            vorgesetzter_id=vorgesetzter_id
        ) 
    
        try:
            session.add(neuer_nutzer)
            session.commit()
            self.neuer_nutzer_rückmeldung = "Der Account wurde erfolgreich angelegt" 
        except IntegrityError:
            session.rollback()
            self.neuer_nutzer_rückmeldung = f"Der Benutzername '{self.neuer_nutzer_name}' existiert bereits."






    def login(self):
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