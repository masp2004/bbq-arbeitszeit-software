import types
from datetime import date, datetime, time, timedelta

import pytest

import modell


class DummyEntry:
    def __init__(self, datum, zeit):
        self.datum = datum
        self.zeit = zeit


class DummySession:
    def __init__(self):
        self.updated_passwords = {}
        self.commit_called = False

    def update_password(self, user_id, password):
        self.updated_passwords[user_id] = password

    def commit(self):
        self.commit_called = True


@pytest.fixture(autouse=True)
def ensure_sqlalchemy_missing(monkeypatch):
    """Force the modell module into fallback behaviour for the tests."""
    monkeypatch.setattr(modell, "SQLALCHEMY_AVAILABLE", False, raising=False)
    yield
    # session is restored by monkeypatch context in tests


def test_calculate_time_same_day():
    start = DummyEntry(date(2024, 1, 2), time(8, 0))
    end = DummyEntry(date(2024, 1, 2), time(16, 30))

    result = modell.CalculateTime(start, end)

    assert result.datum == date(2024, 1, 2)
    assert result.gearbeitete_zeit == timedelta(hours=8, minutes=30)


def test_calculate_time_different_day_returns_none():
    start = DummyEntry(date(2024, 1, 2), time(8, 0))
    end = DummyEntry(date(2024, 1, 3), time(16, 0))

    assert modell.CalculateTime(start, end) is None


def test_calculate_time_applies_breaks():
    start = DummyEntry(date(2024, 1, 2), time(8, 0))
    end = DummyEntry(date(2024, 1, 2), time(18, 0))

    result = modell.CalculateTime(start, end)
    result.gesetzliche_pausen_hinzufügen()

    # 10 hours work -> minus 30 minutes after 6h and additional 45 minutes after 9h
    assert result.gearbeitete_zeit == timedelta(hours=8, minutes=45)


def test_benachrichtigung_create_message_code_2():
    notification = modell.Benachrichtigungen(
        mitarbeiter_id=1, benachrichtigungs_code=2, datum=date(2024, 5, 20)
    )

    message = notification.create_fehlermeldung()

    assert "2024-05-20" in message
    assert "Stempel" in message


def test_set_ampel_farbe_transitions():
    tracker = modell.ModellTrackTime()
    tracker.aktueller_nutzer_ampel_grün = 5
    tracker.aktueller_nutzer_ampel_rot = -5

    tracker.aktueller_nutzer_gleitzeit = 6
    tracker.set_ampel_farbe()
    assert tracker.ampel_status == "green"

    tracker.aktueller_nutzer_gleitzeit = 0
    tracker.set_ampel_farbe()
    assert tracker.ampel_status == "yellow"

    tracker.aktueller_nutzer_gleitzeit = -10
    tracker.set_ampel_farbe()
    assert tracker.ampel_status == "red"


def test_update_passwort_validation_messages():
    tracker = modell.ModellTrackTime()

    tracker.neues_passwort = ""
    tracker.update_passwort()
    assert tracker.feedback_neues_passwort == "Bitte gebe ein passwort ein"

    tracker.neues_passwort = "secret"
    tracker.neues_passwort_wiederholung = ""
    tracker.update_passwort()
    assert tracker.feedback_neues_passwort == "Bitte wiederhole das Passwort"

    tracker.neues_passwort = "secret"
    tracker.neues_passwort_wiederholung = "different"
    tracker.update_passwort()
    assert tracker.feedback_neues_passwort == "Die Passwörter müssen übereinstimmen"


def test_update_passwort_success_with_fallback(monkeypatch):
    tracker = modell.ModellTrackTime()
    tracker.aktueller_nutzer_id = 42
    tracker.neues_passwort = "secret"
    tracker.neues_passwort_wiederholung = "secret"

    dummy_session = DummySession()
    monkeypatch.setattr(modell, "session", dummy_session)

    tracker.update_passwort()

    assert dummy_session.updated_passwords[42] == "secret"
    assert dummy_session.commit_called is True
    assert tracker.feedback_neues_passwort == "Passwort erfolgreich geändert"


def test_update_passwort_missing_user(monkeypatch):
    tracker = modell.ModellTrackTime()
    tracker.aktueller_nutzer_id = None
    tracker.neues_passwort = "secret"
    tracker.neues_passwort_wiederholung = "secret"

    dummy_session = DummySession()
    monkeypatch.setattr(modell, "session", dummy_session)

    tracker.update_passwort()

    assert tracker.feedback_neues_passwort == "Kein Nutzer angemeldet"
    assert dummy_session.updated_passwords == {}


def test_update_passwort_no_fallback_support(monkeypatch):
    tracker = modell.ModellTrackTime()
    tracker.aktueller_nutzer_id = 99
    tracker.neues_passwort = "secret"
    tracker.neues_passwort_wiederholung = "secret"

    # session without update_password method
    incomplete_session = types.SimpleNamespace(commit=lambda: None)
    monkeypatch.setattr(modell, "session", incomplete_session)

    tracker.update_passwort()

    assert tracker.feedback_neues_passwort == "Passwortänderung nicht verfügbar"
