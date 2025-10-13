from sqlalchemy import Column, Integer, String, Date, create_engine, select, Time, Boolean, ForeignKey, UniqueConstraint, CheckConstraint
import sqlalchemy.orm as saorm
from sqlalchemy.exc import IntegrityError
from datetime import datetime, date, timedelta

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
        3: ["Achtung, am", "wurden die gesetzlichen Ruhezeiten nicht eingehalten"]
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



class CalculateTime():
     def __new__(cls, eintrag1, eintrag2):
         if eintrag1.datum != eintrag2.datum:
             return None
         return super().__new__(cls)

     def __init__(self, eintrag1, eintrag2):
         self.datum = eintrag1.datum
         self.startzeit = eintrag1.zeit
         self.endzeit = eintrag2.zeit
         start_dt = datetime.combine(self.datum, self.startzeit)
         end_dt = datetime.combine(self.datum, self.endzeit)

         self.gearbeitete_zeit = end_dt - start_dt

     def gesetzliche_pausen_hinzufügen(self):
         if self.gearbeitete_zeit > timedelta(hours=6):
             self.gearbeitete_zeit -= timedelta(minutes=30)



class ModellTrackTime():
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


        self.benachrichtigungen = []


        self.feedback_manueller_stempel = ""
        self.feedback_arbeitstage = ""
        self.feedback_stempel = ""
        self.feedback_neues_passwort = ""

    def ist_abwesend(self, datum):
        """
        Prüft, ob für den gegebenen Tag eine genehmigte Abwesenheit existiert.
        
        Parameter:
            datum (date): Das zu prüfende Datum
            
        Rückgabe:
            bool: True wenn eine genehmigte Abwesenheit existiert, sonst False
        """
        if self.aktueller_nutzer_id is None:
            return False
            
        stmt = select(Abwesenheit).where(
            (Abwesenheit.mitarbeiter_id == self.aktueller_nutzer_id) &
            (Abwesenheit.datum == datum) &
            (Abwesenheit.genehmigt == True)
        )
        abwesenheit = session.execute(stmt).scalar_one_or_none()
        return abwesenheit is not None

    def berechne_tägliche_arbeitszeit(self, datum):
        """
        Berechnet die erwartete tägliche Arbeitszeit für einen bestimmten Tag.
        Berücksichtigt genehmigte Abwesenheiten (Urlaub, Krankheit, etc.).
        
        Parameter:
            datum (date): Das Datum für das die tägliche Arbeitszeit berechnet werden soll
            
        Rückgabe:
            timedelta: Die erwartete Arbeitszeit für den Tag (0 wenn abwesend, sonst Wochenstunden/5)
        """
        # Wenn der Nutzer an diesem Tag abwesend ist, wird keine Arbeitszeit erwartet
        if self.ist_abwesend(datum):
            return timedelta(hours=0)
        
        # Standard: Wochenstunden geteilt durch 5 Arbeitstage
        # Hinweis: Diese Berechnung geht von einer 5-Tage-Woche aus.
        # In Wochen mit Feiertagen kann die tatsächliche tägliche Sollzeit höher sein.
        return timedelta(hours=(self.aktueller_nutzer_vertragliche_wochenstunden / 5))

    def get_zeiteinträge(self):
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

    def manueller_stempel_hinzufügen(self):
        stempel = Zeiteintrag(
            mitarbeiter_id = self.aktueller_nutzer_id,
            zeit =datetime.strptime(self.manueller_stempel_uhrzeit, "%H:%M").time(),
            datum = datetime.strptime(self.manueller_stempel_datum, "%d/%m/%Y").date()
        )
        session.add(stempel)
        session.commit()

        self.feedback_manueller_stempel = f"Stempel am {self.manueller_stempel_datum} um {self.manueller_stempel_uhrzeit} erfolgreich hinzugefügt"





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
                # Überspringe Tage mit genehmigten Abwesenheiten
                if not self.ist_abwesend(tag):
                    stmt = select(Zeiteintrag).where(
                        (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
                        (Zeiteintrag.datum == tag)
                    )
                    eintrag = session.execute(stmt).scalars().first()
                    if not eintrag:
                        fehlende_tage.append(tag)
            tag += timedelta(days=1)

        abgezogene_tage = []
        for tag in fehlende_tage:
            # Prüfen, ob es für diesen Tag schon eine Benachrichtigung gibt
            exists_stmt = select(Benachrichtigungen).where(
                (Benachrichtigungen.mitarbeiter_id == self.aktueller_nutzer_id) &
                (Benachrichtigungen.datum == tag) &
                (Benachrichtigungen.benachrichtigungs_code == 1)
            )
            exists = session.execute(exists_stmt).scalar_one_or_none()

            if not exists:
                # Tägliche Arbeitszeit für diesen spezifischen Tag berechnen
                tägliche_arbeitszeit = self.berechne_tägliche_arbeitszeit(tag)
                
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
    
    def checke_ruhezeiten(self):
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


    def berechne_gleitzeit(self):
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
                (Zeiteintrag.validiert == 0)
            )
             unvalidierte = session.execute(unvalidierte_stmt).scalars().all()
        
             if not exists and not unvalidierte:
                # Tägliche Arbeitszeit für diesen spezifischen Tag berechnen
                tägliche_arbeitszeit = self.berechne_tägliche_arbeitszeit(datum)
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
                # Tägliche Arbeitszeit für diesen spezifischen Tag berechnen
                tägliche_arbeitszeit = self.berechne_tägliche_arbeitszeit(tag)
                differenz = arbeitstage[tag] - tägliche_arbeitszeit
                gleitzeit_differenzen.append(differenz)
                berücksichtigte_tage.append(tag)
            elif include_missing_days:
                # Fehlender Tag wird als volle Sollzeit-Minus gewertet
                # Aber nur wenn keine genehmigte Abwesenheit vorliegt
                tägliche_arbeitszeit = self.berechne_tägliche_arbeitszeit(tag)
                if tägliche_arbeitszeit > timedelta(hours=0):
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

    def __init__(self):
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