from sqlalchemy import Column, Integer, String, Date, create_engine, select, Time, Boolean, ForeignKey
import sqlalchemy.orm as saorm
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
        2.2:"fehlt ein Stempel, bitte tragen sie diesen nach"
    }

    def create_fehlermeldung(self):

        if self.benachrichtigungs_code == 1:
            return f"{self.CODES[1.1]} {self.datum} {self.CODES[1.2]}"
        elif self.benachrichtigungs_code == 2:
            return f"{self.CODES[2.1]} {self.datum} {self.CODES[2.2]}"



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

        self.manueller_stempel_datum = None
        self.manueller_stempel_uhrzeit = None

        self.benachrichtigungen = []


        self.feedback_manueller_stempel = ""
        self.feedback_arbeitstage = ""
        self.feedback_stempel = ""

    def get_user_info(self):

        if self.aktueller_nutzer_id is None:
            return

        stmt = select(mitarbeiter).where(mitarbeiter.mitarbeiter_id == self.aktueller_nutzer_id)
        nutzer = session.execute(stmt).scalar_one_or_none()
        if nutzer:
            self.aktueller_nutzer_name = nutzer.name
            self.aktueller_nutzer_vertragliche_wochenstunden = nutzer.vertragliche_wochenstunden
            self.aktueller_nutzer_gleitzeit = nutzer.gleitzeit

        stmt = select(Benachrichtigungen).where(Benachrichtigungen.mitarbeiter_id == self.aktueller_nutzer_id)

        result = session.execute(stmt).scalars().all()
        self.benachrichtigungen = result




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
        if self.aktueller_nutzer_id is None:
            return

        stmt = select(mitarbeiter).where(mitarbeiter.mitarbeiter_id == self.aktueller_nutzer_id)
        nutzer = session.execute(stmt).scalar_one_or_none()
        if not nutzer:
            return

        letzter_login = nutzer.letzter_login
        gestern = date.today() - timedelta(days=1)


        fehlende_tage = []
        tag = letzter_login
        while tag <= gestern:
            if tag.weekday() < 5:  
                stmt = select(Zeiteintrag).where(
                    (Zeiteintrag.mitarbeiter_id == self.aktueller_nutzer_id) &
                    (Zeiteintrag.datum == tag)
                )
                eintrag = session.execute(stmt).scalars().first()
                if not eintrag:
                    fehlende_tage.append(tag)
            tag += timedelta(days=1)

        self.feedback_arbeitstage = f"An den Tag / Tagen {fehlende_tage} wurde nicht gestempelt. Es wird für jeden Tag die Tägliche arbeitszeit der Gleitzeit abgezogen"

        for tag in fehlende_tage:
            benachrichtigung = Benachrichtigungen(mitarbeiter_id = self.aktueller_nutzer_id,
                                                  benachrichtigungs_code = 1,
                                                  datum = tag)
            session.add(benachrichtigung)
            session.commit()

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
            session.add(benachrichtigung)
            session.commit()

        return ungerade_tage


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

        tägliche_arbeitszeit = timedelta( hours=(self.aktueller_nutzer_vertragliche_wochenstunden / 5))

        arbeitstage = {datum: zeit - tägliche_arbeitszeit for datum, zeit in arbeitstage.items()}
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