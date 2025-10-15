import pytest
from datetime import date, datetime, time, timedelta
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modell import (
    mitarbeiter, Zeiteintrag, Abwesenheit, Benachrichtigungen,
    CalculateTime, ModellTrackTime, ModellLogin
)


class TestMitarbeiter:
    """Tests for mitarbeiter (employee) model"""

    def test_create_mitarbeiter(self, test_session):
        """Test creating a new employee"""
        m = mitarbeiter(
            name="Test User",
            password="password123",
            vertragliche_wochenstunden=40,
            geburtsdatum=date(1995, 5, 15),
            gleitzeit=0,
            letzter_login=date.today()
        )
        test_session.add(m)
        test_session.commit()

        assert m.mitarbeiter_id is not None
        assert m.name == "Test User"
        assert m.gleitzeit == 0

    def test_unique_name_constraint(self, test_session, sample_mitarbeiter):
        """Test that employee names must be unique"""
        duplicate = mitarbeiter(
            name=sample_mitarbeiter.name,
            password="different",
            vertragliche_wochenstunden=35,
            geburtsdatum=date(1990, 1, 1),
            letzter_login=date.today()
        )
        test_session.add(duplicate)
        
        with pytest.raises(IntegrityError):
            test_session.commit()

    def test_default_values(self, test_session):
        """Test default values for ampel (traffic light) thresholds"""
        m = mitarbeiter(
            name="Default Test",
            password="pass",
            vertragliche_wochenstunden=40,
            geburtsdatum=date(1990, 1, 1),
            letzter_login=date.today()
        )
        test_session.add(m)
        test_session.commit()

        assert m.gleitzeit == 0
        assert m.ampel_grün == 5
        assert m.ampel_rot == -5


class TestZeiteintrag:
    """Tests for Zeiteintrag (time entry) model"""

    def test_create_zeiteintrag(self, test_session, sample_mitarbeiter):
        """Test creating a time entry"""
        z = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(9, 0),
            datum=date.today(),
            validiert=False
        )
        test_session.add(z)
        test_session.commit()

        assert z.id is not None
        assert z.zeit == time(9, 0)
        assert z.validiert is False

    def test_multiple_entries_same_day(self, test_session, sample_mitarbeiter):
        """Test creating multiple time entries for the same day"""
        z1 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(9, 0),
            datum=date.today()
        )
        z2 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(17, 0),
            datum=date.today()
        )
        test_session.add_all([z1, z2])
        test_session.commit()

        stmt = select(Zeiteintrag).where(
            Zeiteintrag.mitarbeiter_id == sample_mitarbeiter.mitarbeiter_id
        )
        entries = test_session.scalars(stmt).all()
        assert len(entries) == 2


class TestAbwesenheit:
    """Tests for Abwesenheit (absence) model"""

    def test_create_abwesenheit(self, test_session, sample_mitarbeiter):
        """Test creating an absence entry"""
        a = Abwesenheit(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            datum=date.today(),
            typ="Urlaub",
            genehmigt=False
        )
        test_session.add(a)
        test_session.commit()

        assert a.id is not None
        assert a.typ == "Urlaub"
        assert a.genehmigt is False

    def test_absence_types(self, test_session, sample_mitarbeiter):
        """Test different absence types"""
        types = ["Urlaub", "Krankheit", "Fortbildung", "Sonstiges"]
        
        for typ in types:
            a = Abwesenheit(
                mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
                datum=date.today() + timedelta(days=types.index(typ)),
                typ=typ
            )
            test_session.add(a)
        
        test_session.commit()
        
        stmt = select(Abwesenheit).where(
            Abwesenheit.mitarbeiter_id == sample_mitarbeiter.mitarbeiter_id
        )
        absences = test_session.scalars(stmt).all()
        assert len(absences) == 4


class TestBenachrichtigungen:
    """Tests for Benachrichtigungen (notifications) model"""

    def test_create_benachrichtigung(self, test_session, sample_mitarbeiter):
        """Test creating a notification"""
        b = Benachrichtigungen(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            benachrichtigungs_code=1,
            datum=date.today()
        )
        test_session.add(b)
        test_session.commit()

        assert b.id is not None
        assert b.benachrichtigungs_code == 1

    def test_unique_constraint(self, test_session, sample_mitarbeiter):
        """Test unique constraint on notification"""
        b1 = Benachrichtigungen(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            benachrichtigungs_code=1,
            datum=date.today()
        )
        test_session.add(b1)
        test_session.commit()

        b2 = Benachrichtigungen(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            benachrichtigungs_code=1,
            datum=date.today()
        )
        test_session.add(b2)
        
        with pytest.raises(IntegrityError):
            test_session.commit()

    def test_create_fehlermeldung_code_1(self, test_session, sample_mitarbeiter):
        """Test error message creation for code 1"""
        b = Benachrichtigungen(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            benachrichtigungs_code=1,
            datum=date(2024, 1, 15)
        )
        message = b.create_fehlermeldung()
        assert "2024-01-15" in message
        assert "nicht gestempelt" in message

    def test_create_fehlermeldung_code_2(self, test_session, sample_mitarbeiter):
        """Test error message creation for code 2"""
        b = Benachrichtigungen(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            benachrichtigungs_code=2,
            datum=date(2024, 1, 15)
        )
        message = b.create_fehlermeldung()
        assert "2024-01-15" in message
        assert "fehlt ein Stempel" in message

    def test_create_fehlermeldung_code_3(self, test_session, sample_mitarbeiter):
        """Test error message creation for code 3"""
        b = Benachrichtigungen(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            benachrichtigungs_code=3,
            datum=date(2024, 1, 15)
        )
        message = b.create_fehlermeldung()
        assert "2024-01-15" in message
        assert "Ruhezeiten" in message

    def test_create_fehlermeldung_code_4(self, test_session, sample_mitarbeiter):
        """Test error message creation for code 4"""
        b = Benachrichtigungen(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            benachrichtigungs_code=4,
            datum=None
        )
        message = b.create_fehlermeldung()
        assert "durchschnittliche" in message
        assert "8 Stunden" in message


class TestCalculateTime:
    """Tests for CalculateTime class"""

    def test_calculate_time_same_day(self):
        """Test time calculation for entries on the same day"""
        e1 = Zeiteintrag(
            mitarbeiter_id=1,
            zeit=time(9, 0),
            datum=date(2024, 1, 15)
        )
        e2 = Zeiteintrag(
            mitarbeiter_id=1,
            zeit=time(17, 0),
            datum=date(2024, 1, 15)
        )
        
        calc = CalculateTime(e1, e2)
        assert calc is not None
        assert calc.gearbeitete_zeit == timedelta(hours=8)

    def test_calculate_time_different_days(self):
        """Test that calculation returns None for different days"""
        e1 = Zeiteintrag(
            mitarbeiter_id=1,
            zeit=time(9, 0),
            datum=date(2024, 1, 15)
        )
        e2 = Zeiteintrag(
            mitarbeiter_id=1,
            zeit=time(17, 0),
            datum=date(2024, 1, 16)
        )
        
        calc = CalculateTime(e1, e2)
        assert calc is None

    def test_gesetzliche_pausen_6_hours(self):
        """Test mandatory break for > 6 hours"""
        e1 = Zeiteintrag(
            mitarbeiter_id=1,
            zeit=time(9, 0),
            datum=date(2024, 1, 15)
        )
        e2 = Zeiteintrag(
            mitarbeiter_id=1,
            zeit=time(16, 0),
            datum=date(2024, 1, 15)
        )
        
        calc = CalculateTime(e1, e2)
        calc.gesetzliche_pausen_hinzufügen()
        # 7 hours - 30 minutes = 6.5 hours
        assert calc.gearbeitete_zeit == timedelta(hours=6, minutes=30)

    def test_gesetzliche_pausen_9_hours(self):
        """Test mandatory break for > 9 hours"""
        e1 = Zeiteintrag(
            mitarbeiter_id=1,
            zeit=time(8, 0),
            datum=date(2024, 1, 15)
        )
        e2 = Zeiteintrag(
            mitarbeiter_id=1,
            zeit=time(18, 0),
            datum=date(2024, 1, 15)
        )
        
        calc = CalculateTime(e1, e2)
        calc.gesetzliche_pausen_hinzufügen()
        # 10 hours - 30 minutes - 45 minutes = 8 hours 45 minutes
        assert calc.gearbeitete_zeit == timedelta(hours=8, minutes=45)

    def test_no_pause_under_6_hours(self):
        """Test no mandatory break for <= 6 hours"""
        e1 = Zeiteintrag(
            mitarbeiter_id=1,
            zeit=time(9, 0),
            datum=date(2024, 1, 15)
        )
        e2 = Zeiteintrag(
            mitarbeiter_id=1,
            zeit=time(15, 0),
            datum=date(2024, 1, 15)
        )
        
        calc = CalculateTime(e1, e2)
        calc.gesetzliche_pausen_hinzufügen()
        assert calc.gearbeitete_zeit == timedelta(hours=6)


class TestModellLogin:
    """Tests for ModellLogin class"""

    def test_neuen_nutzer_anlegen_success(self, test_session, monkeypatch):
        """Test successful user registration"""
        # Mock the session
        import modell
        original_session = modell.session
        monkeypatch.setattr(modell, 'session', test_session)

        model = ModellLogin()
        model.neuer_nutzer_name = "New User"
        model.neuer_nutzer_passwort = "password123"
        model.neuer_nutzer_passwort_val = "password123"
        model.neuer_nutzer_vertragliche_wochenstunden = "40"
        model.neuer_nutzer_geburtsdatum = "15/01/1990"

        model.neuen_nutzer_anlegen()

        assert "erfolgreich" in model.neuer_nutzer_rückmeldung
        
        stmt = select(mitarbeiter).where(mitarbeiter.name == "New User")
        user = test_session.execute(stmt).scalar_one_or_none()
        assert user is not None
        assert user.name == "New User"

        monkeypatch.setattr(modell, 'session', original_session)

    def test_neuen_nutzer_anlegen_password_mismatch(self):
        """Test registration with mismatched passwords"""
        model = ModellLogin()
        model.neuer_nutzer_name = "New User"
        model.neuer_nutzer_passwort = "password123"
        model.neuer_nutzer_passwort_val = "different"
        model.neuer_nutzer_vertragliche_wochenstunden = "40"
        model.neuer_nutzer_geburtsdatum = "15/01/1990"

        model.neuen_nutzer_anlegen()

        assert "übereinstimmen" in model.neuer_nutzer_rückmeldung

    def test_neuen_nutzer_anlegen_missing_name(self):
        """Test registration with missing name"""
        model = ModellLogin()
        model.neuer_nutzer_name = None
        model.neuer_nutzer_passwort = "password123"
        model.neuer_nutzer_passwort_val = "password123"
        model.neuer_nutzer_vertragliche_wochenstunden = "40"
        model.neuer_nutzer_geburtsdatum = "15/01/1990"

        model.neuen_nutzer_anlegen()

        assert "Namen" in model.neuer_nutzer_rückmeldung

    def test_login_success(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test successful login"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)

        model = ModellLogin()
        model.anmeldung_name = sample_mitarbeiter.name
        model.anmeldung_passwort = sample_mitarbeiter.password

        result = model.login()

        assert result is True
        assert "erfolgreich" in model.anmeldung_rückmeldung
        assert model.anmeldung_mitarbeiter_id_validiert == sample_mitarbeiter.mitarbeiter_id

        monkeypatch.setattr(modell, 'session', test_session)

    def test_login_wrong_password(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test login with wrong password"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)

        model = ModellLogin()
        model.anmeldung_name = sample_mitarbeiter.name
        model.anmeldung_passwort = "wrong_password"

        result = model.login()

        assert result is None
        assert "falsch" in model.anmeldung_rückmeldung

    def test_login_nonexistent_user(self, test_session, monkeypatch):
        """Test login with non-existent user"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)

        model = ModellLogin()
        model.anmeldung_name = "NonExistent"
        model.anmeldung_passwort = "password"

        result = model.login()

        assert result is None
        assert "falsch" in model.anmeldung_rückmeldung


class TestModellTrackTime:
    """Tests for ModellTrackTime class"""

    def test_get_user_info(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test getting user information"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)

        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        model.get_user_info()

        assert model.aktueller_nutzer_name == sample_mitarbeiter.name
        assert model.aktueller_nutzer_vertragliche_wochenstunden == sample_mitarbeiter.vertragliche_wochenstunden
        assert model.aktueller_nutzer_gleitzeit == sample_mitarbeiter.gleitzeit

    def test_set_ampel_farbe_green(self):
        """Test traffic light status - green"""
        model = ModellTrackTime()
        model.aktueller_nutzer_gleitzeit = 10
        model.aktueller_nutzer_ampel_grün = 5
        model.aktueller_nutzer_ampel_rot = -5

        model.set_ampel_farbe()

        assert model.ampel_status == "green"

    def test_set_ampel_farbe_yellow(self):
        """Test traffic light status - yellow"""
        model = ModellTrackTime()
        model.aktueller_nutzer_gleitzeit = 0
        model.aktueller_nutzer_ampel_grün = 5
        model.aktueller_nutzer_ampel_rot = -5

        model.set_ampel_farbe()

        assert model.ampel_status == "yellow"

    def test_set_ampel_farbe_red(self):
        """Test traffic light status - red"""
        model = ModellTrackTime()
        model.aktueller_nutzer_gleitzeit = -10
        model.aktueller_nutzer_ampel_grün = 5
        model.aktueller_nutzer_ampel_rot = -5

        model.set_ampel_farbe()

        assert model.ampel_status == "red"

    def test_update_passwort_success(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test successful password update"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)

        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        model.neues_passwort = "newpass123"
        model.neues_passwort_wiederholung = "newpass123"

        model.update_passwort()

        assert "erfolgreich" in model.feedback_neues_passwort
        
        stmt = select(mitarbeiter).where(mitarbeiter.mitarbeiter_id == sample_mitarbeiter.mitarbeiter_id)
        user = test_session.execute(stmt).scalar_one_or_none()
        assert user.password == "newpass123"

    def test_update_passwort_mismatch(self):
        """Test password update with mismatch"""
        model = ModellTrackTime()
        model.neues_passwort = "newpass123"
        model.neues_passwort_wiederholung = "different"

        model.update_passwort()

        assert "übereinstimmen" in model.feedback_neues_passwort

    def test_stempel_hinzufügen(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test adding a time stamp"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)

        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id

        model.stempel_hinzufügen()

        stmt = select(Zeiteintrag).where(
            Zeiteintrag.mitarbeiter_id == sample_mitarbeiter.mitarbeiter_id
        )
        entries = test_session.scalars(stmt).all()
        assert len(entries) == 1
        assert entries[0].datum == date.today()

    def test_get_zeiteinträge(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test getting time entries for a specific date"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)

        # Create test entries
        z1 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(9, 0),
            datum=date.today()
        )
        z2 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(17, 0),
            datum=date.today()
        )
        test_session.add_all([z1, z2])
        test_session.commit()

        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        model.bestimmtes_datum = date.today().strftime("%d.%m.%Y")

        model.get_zeiteinträge()

        assert model.zeiteinträge_bestimmtes_datum is not None
        assert len(model.zeiteinträge_bestimmtes_datum) == 2

    def test_berechne_durchschnittliche_gleitzeit(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test calculating average flextime"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)

        # Create test entries for 5 days
        start_date = date.today() - timedelta(days=10)
        for i in range(5):
            day = start_date + timedelta(days=i)
            if day.weekday() < 5:  # Only weekdays
                z1 = Zeiteintrag(
                    mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
                    zeit=time(9, 0),
                    datum=day
                )
                z2 = Zeiteintrag(
                    mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
                    zeit=time(18, 0),  # 9 hours
                    datum=day
                )
                test_session.add_all([z1, z2])
        test_session.commit()

        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        model.aktueller_nutzer_vertragliche_wochenstunden = 40

        result = model.berechne_durchschnittliche_gleitzeit(
            start_date,
            start_date + timedelta(days=10),
            include_missing_days=False
        )

        assert "durchschnitt_gleitzeit_stunden" in result
        assert result["anzahl_tage"] > 0
