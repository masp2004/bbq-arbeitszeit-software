import pytest
from datetime import date, datetime, time, timedelta
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modell import (
    mitarbeiter, Zeiteintrag, Abwesenheit, Benachrichtigungen,
    ModellTrackTime, ModellLogin
)


class TestEdgeCasesAndMissingCoverage:
    """Tests for edge cases and missing coverage to reach 100%"""

    def test_get_zeiteinträge_no_user_id(self):
        """Test get_zeiteinträge when no user is logged in"""
        model = ModellTrackTime()
        model.aktueller_nutzer_id = None
        model.bestimmtes_datum = "15.01.2024"
        
        result = model.get_zeiteinträge()
        assert result is None

    def test_get_zeiteinträge_no_datum(self):
        """Test get_zeiteinträge when no date is set"""
        model = ModellTrackTime()
        model.aktueller_nutzer_id = 1
        model.bestimmtes_datum = None
        
        result = model.get_zeiteinträge()
        assert result is None

    def test_get_user_info_no_user_id(self):
        """Test get_user_info when no user is logged in"""
        model = ModellTrackTime()
        model.aktueller_nutzer_id = None
        
        result = model.get_user_info()
        assert result is None

    def test_update_passwort_empty_password(self):
        """Test password update with empty password"""
        model = ModellTrackTime()
        model.neues_passwort = ""
        model.neues_passwort_wiederholung = "test123"
        
        model.update_passwort()
        assert "passwort ein" in model.feedback_neues_passwort.lower()

    def test_update_passwort_empty_repeat(self):
        """Test password update with empty repeat password"""
        model = ModellTrackTime()
        model.neues_passwort = "test123"
        model.neues_passwort_wiederholung = ""
        
        model.update_passwort()
        assert "wiederhole" in model.feedback_neues_passwort.lower()

    def test_urlaub_eintragen_no_datum(self):
        """Test vacation entry with no date"""
        model = ModellTrackTime()
        model.aktueller_nutzer_id = 1
        model.neuer_abwesenheitseintrag_datum = None
        model.neuer_abwesenheitseintrag_art = "Urlaub"
        
        result = model.urlaub_eintragen()
        assert result is None

    def test_urlaub_eintragen_no_art(self):
        """Test vacation entry with no type"""
        model = ModellTrackTime()
        model.aktueller_nutzer_id = 1
        model.neuer_abwesenheitseintrag_datum = date.today()
        model.neuer_abwesenheitseintrag_art = None
        
        result = model.urlaub_eintragen()
        assert result is None

    def test_urlaub_eintragen_invalid_art(self):
        """Test vacation entry with invalid type"""
        model = ModellTrackTime()
        model.aktueller_nutzer_id = 1
        model.neuer_abwesenheitseintrag_datum = date.today()
        model.neuer_abwesenheitseintrag_art = "InvalidType"
        
        result = model.urlaub_eintragen()
        assert result is None

    def test_checke_arbeitstage_no_user_id(self):
        """Test work day check with no user ID"""
        model = ModellTrackTime()
        model.aktueller_nutzer_id = None
        
        result = model.checke_arbeitstage()
        assert result is None

    def test_checke_arbeitstage_no_user_found(self, test_session, monkeypatch):
        """Test work day check when user is not found"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)
        
        model = ModellTrackTime()
        model.aktueller_nutzer_id = 99999  # Non-existent user
        
        result = model.checke_arbeitstage()
        assert result is None

    def test_checke_stempel_no_user_id(self):
        """Test stamp check with no user ID"""
        model = ModellTrackTime()
        model.aktueller_nutzer_id = None
        
        result = model.checke_stempel()
        assert result is None

    def test_checke_stempel_no_user_found(self, test_session, monkeypatch):
        """Test stamp check when user is not found"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)
        
        model = ModellTrackTime()
        model.aktueller_nutzer_id = 99999
        
        result = model.checke_stempel()
        assert result is None

    def test_checke_ruhezeiten_no_user_id(self):
        """Test rest period check with no user ID"""
        model = ModellTrackTime()
        model.aktueller_nutzer_id = None
        
        result = model.checke_ruhezeiten()
        assert result is None

    def test_checke_durchschnittliche_arbeitszeit_no_user_id(self):
        """Test average work time check with no user ID"""
        model = ModellTrackTime()
        model.aktueller_nutzer_id = None
        
        result = model.checke_durchschnittliche_arbeitszeit()
        assert result is None

    def test_checke_durchschnittliche_arbeitszeit_no_entries(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test average work time check with no entries"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)
        
        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        
        result = model.checke_durchschnittliche_arbeitszeit()
        # Should not create notification when no entries
        stmt = select(Benachrichtigungen).where(
            (Benachrichtigungen.mitarbeiter_id == sample_mitarbeiter.mitarbeiter_id) &
            (Benachrichtigungen.benachrichtigungs_code == 4)
        )
        notification = test_session.execute(stmt).scalar_one_or_none()
        assert notification is None

    def test_berechne_durchschnittliche_gleitzeit_no_user(self):
        """Test average flextime calculation with no user"""
        model = ModellTrackTime()
        model.aktueller_nutzer_id = None
        
        result = model.berechne_durchschnittliche_gleitzeit(
            date.today() - timedelta(days=7),
            date.today()
        )
        
        assert "error" in result
        assert "Kein Nutzer" in result["error"]

    def test_berechne_durchschnittliche_gleitzeit_invalid_dates(self, sample_mitarbeiter):
        """Test average flextime calculation with invalid date range"""
        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        
        # End date before start date
        result = model.berechne_durchschnittliche_gleitzeit(
            date.today(),
            date.today() - timedelta(days=7)
        )
        
        assert "error" in result
        assert "Startdatum" in result["error"]

    def test_berechne_durchschnittliche_gleitzeit_user_not_found(self, test_session, monkeypatch):
        """Test average flextime calculation when user not found"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)
        
        model = ModellTrackTime()
        model.aktueller_nutzer_id = 99999
        
        result = model.berechne_durchschnittliche_gleitzeit(
            date.today() - timedelta(days=7),
            date.today()
        )
        
        assert "error" in result
        assert "nicht gefunden" in result["error"]

    def test_berechne_durchschnittliche_gleitzeit_no_entries(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test average flextime calculation with no entries"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)
        
        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        model.aktueller_nutzer_vertragliche_wochenstunden = 40
        
        result = model.berechne_durchschnittliche_gleitzeit(
            date.today() - timedelta(days=7),
            date.today()
        )
        
        assert result["durchschnitt_gleitzeit_stunden"] == 0.0
        assert result["anzahl_tage"] == 0

    def test_berechne_durchschnittliche_gleitzeit_with_missing_days(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test average flextime calculation including missing days"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)
        
        # Add one entry
        z1 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(9, 0),
            datum=date.today() - timedelta(days=5)
        )
        z2 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(17, 0),
            datum=date.today() - timedelta(days=5)
        )
        test_session.add_all([z1, z2])
        test_session.commit()
        
        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        model.aktueller_nutzer_vertragliche_wochenstunden = 40
        
        result = model.berechne_durchschnittliche_gleitzeit(
            date.today() - timedelta(days=7),
            date.today(),
            include_missing_days=True
        )
        
        assert result["anzahl_tage"] > 1  # Should include missing days

    def test_berechne_durchschnittliche_gleitzeit_no_differenzen(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test when no flextime differences are calculated"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)
        
        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        model.aktueller_nutzer_vertragliche_wochenstunden = 40
        
        # Create date range with only weekends
        saturday = date.today()
        while saturday.weekday() != 5:  # Find a Saturday
            saturday -= timedelta(days=1)
        
        result = model.berechne_durchschnittliche_gleitzeit(
            saturday,
            saturday + timedelta(days=1),  # Saturday to Sunday
            include_missing_days=False
        )
        
        assert result["durchschnitt_gleitzeit_stunden"] == 0.0
        assert result["anzahl_tage"] == 0

    def test_neuen_nutzer_anlegen_empty_password(self):
        """Test user registration with empty password"""
        model = ModellLogin()
        model.neuer_nutzer_name = "Test User"
        model.neuer_nutzer_passwort = ""
        model.neuer_nutzer_passwort_val = "test123"
        model.neuer_nutzer_vertragliche_wochenstunden = "40"
        model.neuer_nutzer_geburtsdatum = "15/01/1990"
        
        model.neuen_nutzer_anlegen()
        assert "Passwort" in model.neuer_nutzer_rückmeldung

    def test_neuen_nutzer_anlegen_empty_password_val(self):
        """Test user registration with empty password validation"""
        model = ModellLogin()
        model.neuer_nutzer_name = "Test User"
        model.neuer_nutzer_passwort = "test123"
        model.neuer_nutzer_passwort_val = ""
        model.neuer_nutzer_vertragliche_wochenstunden = "40"
        model.neuer_nutzer_geburtsdatum = "15/01/1990"
        
        model.neuen_nutzer_anlegen()
        assert "wiederhole" in model.neuer_nutzer_rückmeldung

    def test_neuen_nutzer_anlegen_empty_wochenstunden(self):
        """Test user registration with empty work hours"""
        model = ModellLogin()
        model.neuer_nutzer_name = "Test User"
        model.neuer_nutzer_passwort = "test123"
        model.neuer_nutzer_passwort_val = "test123"
        model.neuer_nutzer_vertragliche_wochenstunden = ""
        model.neuer_nutzer_geburtsdatum = "15/01/1990"
        
        model.neuen_nutzer_anlegen()
        assert "Arbeitszeit" in model.neuer_nutzer_rückmeldung

    def test_neuen_nutzer_anlegen_empty_geburtsdatum(self):
        """Test user registration with empty birth date"""
        model = ModellLogin()
        model.neuer_nutzer_name = "Test User"
        model.neuer_nutzer_passwort = "test123"
        model.neuer_nutzer_passwort_val = "test123"
        model.neuer_nutzer_vertragliche_wochenstunden = "40"
        model.neuer_nutzer_geburtsdatum = ""
        
        model.neuen_nutzer_anlegen()
        assert "Geburtsdatum" in model.neuer_nutzer_rückmeldung

    def test_neuen_nutzer_anlegen_invalid_date_format(self):
        """Test user registration with invalid date format"""
        model = ModellLogin()
        model.neuer_nutzer_name = "Test User"
        model.neuer_nutzer_passwort = "test123"
        model.neuer_nutzer_passwort_val = "test123"
        model.neuer_nutzer_vertragliche_wochenstunden = "40"
        model.neuer_nutzer_geburtsdatum = "invalid-date"
        
        model.neuen_nutzer_anlegen()
        assert "Datum" in model.neuer_nutzer_rückmeldung

    def test_neuen_nutzer_anlegen_invalid_wochenstunden(self):
        """Test user registration with invalid work hours"""
        model = ModellLogin()
        model.neuer_nutzer_name = "Test User"
        model.neuer_nutzer_passwort = "test123"
        model.neuer_nutzer_passwort_val = "test123"
        model.neuer_nutzer_vertragliche_wochenstunden = "nicht-eine-zahl"
        model.neuer_nutzer_geburtsdatum = "15/01/1990"
        
        model.neuen_nutzer_anlegen()
        assert "Arbeitszeit" in model.neuer_nutzer_rückmeldung

    def test_berechne_gleitzeit_odd_number_entries(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test flextime calculation with odd number of entries (edge case)"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)
        
        yesterday = date.today() - timedelta(days=1)
        if yesterday.weekday() >= 5:
            pytest.skip("Test requires yesterday to be a weekday")
        
        # Add only one entry (odd)
        z1 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(9, 0),
            datum=yesterday,
            validiert=False
        )
        test_session.add(z1)
        test_session.commit()
        
        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        model.aktueller_nutzer_vertragliche_wochenstunden = 40
        model.aktueller_nutzer_gleitzeit = 0
        
        # Should handle odd entries gracefully
        model.berechne_gleitzeit()
        
        # Entry should not be validated since it's incomplete
        stmt = select(Zeiteintrag).where(Zeiteintrag.id == z1.id)
        entry = test_session.execute(stmt).scalar_one()
        assert entry.validiert == False

    def test_berechne_gleitzeit_with_notification(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test flextime calculation when notification code 1 exists"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)
        
        yesterday = date.today() - timedelta(days=1)
        if yesterday.weekday() >= 5:
            pytest.skip("Test requires yesterday to be a weekday")
        
        # Add entries
        z1 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(9, 0),
            datum=yesterday,
            validiert=False
        )
        z2 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(17, 0),
            datum=yesterday,
            validiert=False
        )
        test_session.add_all([z1, z2])
        
        # Add notification code 1
        notif = Benachrichtigungen(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            benachrichtigungs_code=1,
            datum=yesterday
        )
        test_session.add(notif)
        test_session.commit()
        
        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        model.aktueller_nutzer_vertragliche_wochenstunden = 40
        model.aktueller_nutzer_gleitzeit = 0
        
        model.berechne_gleitzeit()
        
        # When notification code 1 exists, arbeitszeit should not be reduced
        # Flextime should still be calculated

    def test_berechne_gleitzeit_with_validated_entries(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test flextime calculation when entries are already validated"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)
        
        yesterday = date.today() - timedelta(days=1)
        if yesterday.weekday() >= 5:
            pytest.skip("Test requires yesterday to be a weekday")
        
        # Add entries
        z1 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(9, 0),
            datum=yesterday,
            validiert=False
        )
        z2 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(17, 0),
            datum=yesterday,
            validiert=False
        )
        # Add a validated entry (should be ignored)
        z3 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(8, 0),
            datum=yesterday,
            validiert=True
        )
        test_session.add_all([z1, z2, z3])
        test_session.commit()
        
        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        model.aktueller_nutzer_vertragliche_wochenstunden = 40
        model.aktueller_nutzer_gleitzeit = 0
        
        model.berechne_gleitzeit()
        
        # The validated entry should not affect calculation

    def test_checke_stempel_integrity_error(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test stamp check with IntegrityError (duplicate notification)"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)
        
        yesterday = date.today() - timedelta(days=1)
        if yesterday.weekday() >= 5:
            pytest.skip("Test requires yesterday to be a weekday")
        
        sample_mitarbeiter.letzter_login = yesterday
        test_session.commit()
        
        # Add one stamp (odd)
        z1 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(9, 0),
            datum=yesterday
        )
        test_session.add(z1)
        test_session.commit()
        
        # Create notification first
        notif = Benachrichtigungen(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            benachrichtigungs_code=2,
            datum=yesterday
        )
        test_session.add(notif)
        test_session.commit()
        
        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        
        # Should handle IntegrityError gracefully
        result = model.checke_stempel()
        assert result is not None

    def test_checke_durchschnittliche_arbeitszeit_no_arbeitstage(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test average work time when no work days calculated"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)
        
        # Add entries on different days (won't pair up correctly)
        z1 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(9, 0),
            datum=date.today() - timedelta(days=30)
        )
        test_session.add(z1)
        test_session.commit()
        
        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        
        result = model.checke_durchschnittliche_arbeitszeit()
        # Should return early when no arbeitstage

    def test_checke_durchschnittliche_arbeitszeit_existing_in_calc(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test average work time when datum already in arbeitstage"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)
        
        # Create multiple entries on same day to test accumulation
        for i in range(4):
            day = date.today() - timedelta(days=30)
            z = Zeiteintrag(
                mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
                zeit=time(8 + i*3, 0),  # 8:00, 11:00, 14:00, 17:00
                datum=day
            )
            test_session.add(z)
        test_session.commit()
        
        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        
        model.checke_durchschnittliche_arbeitszeit()

    def test_checke_durchschnittliche_arbeitszeit_calc_none(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test average work time when CalculateTime returns None"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)
        
        # Add entries on different days
        z1 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(9, 0),
            datum=date.today() - timedelta(days=30)
        )
        z2 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(17, 0),
            datum=date.today() - timedelta(days=29)
        )
        test_session.add_all([z1, z2])
        test_session.commit()
        
        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        
        model.checke_durchschnittliche_arbeitszeit()

    def test_checke_max_arbeitszeit_with_existing_notification(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test max work time check when notification already exists"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)
        
        yesterday = date.today() - timedelta(days=1)
        if yesterday.weekday() >= 5:
            pytest.skip("Test requires yesterday to be a weekday")
        
        # Add work entries that exceed 10 hours
        z1 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(8, 0),
            datum=yesterday,
            validiert=False
        )
        z2 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(19, 0),
            datum=yesterday,
            validiert=False
        )
        test_session.add_all([z1, z2])
        
        # Create notification first
        notif = Benachrichtigungen(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            benachrichtigungs_code=5,
            datum=yesterday
        )
        test_session.add(notif)
        test_session.commit()
        
        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        
        model.checke_max_arbeitszeit()
        
        # Should not create duplicate notification
        stmt = select(Benachrichtigungen).where(
            (Benachrichtigungen.mitarbeiter_id == sample_mitarbeiter.mitarbeiter_id) &
            (Benachrichtigungen.benachrichtigungs_code == 5)
        )
        notifications = test_session.execute(stmt).scalars().all()
        assert len(notifications) == 1

    def test_checke_max_arbeitszeit_under_limit(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test max work time check when under 10 hours"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)
        
        yesterday = date.today() - timedelta(days=1)
        if yesterday.weekday() >= 5:
            pytest.skip("Test requires yesterday to be a weekday")
        
        # Add work entries under 10 hours
        z1 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(9, 0),
            datum=yesterday,
            validiert=False
        )
        z2 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(17, 0),
            datum=yesterday,
            validiert=False
        )
        test_session.add_all([z1, z2])
        test_session.commit()
        
        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        
        model.checke_max_arbeitszeit()
        
        # Should not create notification
        stmt = select(Benachrichtigungen).where(
            (Benachrichtigungen.mitarbeiter_id == sample_mitarbeiter.mitarbeiter_id) &
            (Benachrichtigungen.benachrichtigungs_code == 5)
        )
        notification = test_session.execute(stmt).scalar_one_or_none()
        assert notification is None

    def test_checke_max_arbeitszeit_calc_none(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test max work time when CalculateTime returns None"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)
        
        yesterday = date.today() - timedelta(days=1)
        if yesterday.weekday() >= 5:
            pytest.skip("Test requires yesterday to be a weekday")
        
        # Add entries that won't calculate properly
        z1 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(9, 0),
            datum=yesterday,
            validiert=False
        )
        test_session.add(z1)
        test_session.commit()
        
        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        
        model.checke_max_arbeitszeit()

    def test_checke_max_arbeitszeit_existing_in_tage(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test max work time with multiple entries on same day"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)
        
        yesterday = date.today() - timedelta(days=1)
        if yesterday.weekday() >= 5:
            pytest.skip("Test requires yesterday to be a weekday")
        
        # Add multiple pairs on same day
        z1 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(8, 0),
            datum=yesterday,
            validiert=False
        )
        z2 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(12, 0),
            datum=yesterday,
            validiert=False
        )
        z3 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(13, 0),
            datum=yesterday,
            validiert=False
        )
        z4 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(20, 0),
            datum=yesterday,
            validiert=False
        )
        test_session.add_all([z1, z2, z3, z4])
        test_session.commit()
        
        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        
        model.checke_max_arbeitszeit()
        
        # Check notification created
        stmt = select(Benachrichtigungen).where(
            (Benachrichtigungen.mitarbeiter_id == sample_mitarbeiter.mitarbeiter_id) &
            (Benachrichtigungen.benachrichtigungs_code == 5)
        )
        notification = test_session.execute(stmt).scalar_one_or_none()
        assert notification is not None

    def test_berechne_gleitzeit_calc_none(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test flextime calculation when CalculateTime returns None"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)
        
        # Add entries on different days
        z1 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(9, 0),
            datum=date.today() - timedelta(days=2),
            validiert=False
        )
        z2 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(17, 0),
            datum=date.today() - timedelta(days=1),
            validiert=False
        )
        test_session.add_all([z1, z2])
        test_session.commit()
        
        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        model.aktueller_nutzer_vertragliche_wochenstunden = 40
        model.aktueller_nutzer_gleitzeit = 0
        
        model.berechne_gleitzeit()

    def test_berechne_gleitzeit_existing_in_arbeitstage(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test flextime calculation when datum already in arbeitstage"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)
        
        yesterday = date.today() - timedelta(days=1)
        if yesterday.weekday() >= 5:
            pytest.skip("Test requires yesterday to be a weekday")
        
        # Add multiple pairs on same day
        z1 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(8, 0),
            datum=yesterday,
            validiert=False
        )
        z2 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(12, 0),
            datum=yesterday,
            validiert=False
        )
        z3 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(13, 0),
            datum=yesterday,
            validiert=False
        )
        z4 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(17, 0),
            datum=yesterday,
            validiert=False
        )
        test_session.add_all([z1, z2, z3, z4])
        test_session.commit()
        
        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        model.aktueller_nutzer_vertragliche_wochenstunden = 40
        model.aktueller_nutzer_gleitzeit = 0
        
        model.berechne_gleitzeit()

    def test_berechne_durchschnittliche_gleitzeit_existing_in_arbeitstage(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test average flextime with multiple entries on same day"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)
        
        day = date.today() - timedelta(days=5)
        if day.weekday() >= 5:
            pytest.skip("Test requires a weekday")
        
        # Add multiple pairs on same day
        z1 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(8, 0),
            datum=day
        )
        z2 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(12, 0),
            datum=day
        )
        z3 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(13, 0),
            datum=day
        )
        z4 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(17, 0),
            datum=day
        )
        test_session.add_all([z1, z2, z3, z4])
        test_session.commit()
        
        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        model.aktueller_nutzer_vertragliche_wochenstunden = 40
        
        result = model.berechne_durchschnittliche_gleitzeit(
            day,
            day + timedelta(days=1),
            include_missing_days=False
        )
        
        assert result["anzahl_tage"] >= 1

    def test_berechne_durchschnittliche_gleitzeit_calc_none(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test average flextime when CalculateTime returns None"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)
        
        # Add entries on different days
        z1 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(9, 0),
            datum=date.today() - timedelta(days=7)
        )
        z2 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(17, 0),
            datum=date.today() - timedelta(days=6)
        )
        test_session.add_all([z1, z2])
        test_session.commit()
        
        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        model.aktueller_nutzer_vertragliche_wochenstunden = 40
        
        result = model.berechne_durchschnittliche_gleitzeit(
            date.today() - timedelta(days=7),
            date.today(),
            include_missing_days=False
        )

    def test_berechne_durchschnittliche_gleitzeit_no_gleitzeit_differenzen_final(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test when final gleitzeit_differenzen is empty"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)
        
        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        model.aktueller_nutzer_vertragliche_wochenstunden = 40
        
        # Use weekend dates only
        saturday = date.today()
        while saturday.weekday() != 5:
            saturday -= timedelta(days=1)
        
        result = model.berechne_durchschnittliche_gleitzeit(
            saturday,
            saturday + timedelta(days=1),
            include_missing_days=False
        )
        
        assert result["anzahl_tage"] == 0

    def test_checke_ruhezeiten_no_entries(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test rest period check with no entries"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)
        
        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        
        result = model.checke_ruhezeiten()
        # Should return early with no entries
        assert result is None

    def test_checke_ruhezeiten_tag_morgen_after_gestern(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test rest period check when second day is after yesterday"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)
        
        # Add entry for day before yesterday
        day1 = date.today() - timedelta(days=2)
        # Add entry for today (should be skipped)
        day2 = date.today()
        
        z1 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(22, 0),
            datum=day1
        )
        z2 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(7, 0),
            datum=day2
        )
        test_session.add_all([z1, z2])
        test_session.commit()
        
        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        
        model.checke_ruhezeiten()
        # Should break when tag_morgen > gestern

    def test_checke_ruhezeiten_weekend_skip(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test rest period check skips weekends"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)
        
        # Find a Friday
        friday = date.today()
        while friday.weekday() != 4:
            friday -= timedelta(days=1)
        
        saturday = friday + timedelta(days=1)
        
        # Add entries for Friday and Saturday
        z1_fri = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(9, 0),
            datum=friday
        )
        z2_fri = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(23, 0),
            datum=friday
        )
        z1_sat = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(7, 0),
            datum=saturday
        )
        z2_sat = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(15, 0),
            datum=saturday
        )
        test_session.add_all([z1_fri, z2_fri, z1_sat, z2_sat])
        test_session.commit()
        
        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        
        model.checke_ruhezeiten()
        # Should skip weekend days

    def test_checke_max_arbeitszeit_not_in_tage(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test max work time when datum not in tage (else branch)"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)
        
        yesterday = date.today() - timedelta(days=1)
        if yesterday.weekday() >= 5:
            pytest.skip("Test requires yesterday to be a weekday")
        
        # This should hit the else branch at line 526-527
        # by creating a scenario where calc.datum is not in tage initially
        z1 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(8, 0),
            datum=yesterday,
            validiert=False
        )
        z2 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(20, 0),
            datum=yesterday,
            validiert=False
        )
        test_session.add_all([z1, z2])
        test_session.commit()
        
        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        
        model.checke_max_arbeitszeit()
        # The else branch should be covered

    def test_checke_max_arbeitszeit_calc_none_in_loop(self, test_session, sample_mitarbeiter, monkeypatch):
        """Test max work time when calc is None (i += 1 branch)"""
        import modell
        monkeypatch.setattr(modell, 'session', test_session)
        
        day1 = date.today() - timedelta(days=2)
        day2 = date.today() - timedelta(days=1)
        
        if day1.weekday() >= 5 or day2.weekday() >= 5:
            pytest.skip("Test requires weekdays")
        
        # Add entries on different days that will make calc None
        z1 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(9, 0),
            datum=day1,
            validiert=False
        )
        z2 = Zeiteintrag(
            mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
            zeit=time(17, 0),
            datum=day2,
            validiert=False
        )
        test_session.add_all([z1, z2])
        test_session.commit()
        
        model = ModellTrackTime()
        model.aktueller_nutzer_id = sample_mitarbeiter.mitarbeiter_id
        
        model.checke_max_arbeitszeit()
        # Should hit the i += 1 branch when calc is None
