import datetime as dt
import pytest

# --- Smoke test to keep CI green while specs are built ---
def test_smoke():
    assert True

# NOTE:
# Die folgenden Tests sind als "Spezifikation" geschrieben.
# Sie erwarten Funktionen/Klassen, die du in deinem Code implementierst
# (z. B. in einem Modul wie `bbq/domain.py` oder `src/bbq/domain.py`).
# Bis zur Implementierung sind sie als xfail markiert, damit die Pipeline nicht rot wird.
# Entferne die xfail-Markierungen, sobald die Funktionen existieren.

# Hilfsdaten: einfache Schichten (start, ende)
def _shift(y, m, d, sh, sm, eh, em):
    return (
        dt.datetime(y, m, d, sh, sm),  # start
        dt.datetime(y, m, d, eh, em),  # end
    )


@pytest.mark.xfail(reason="Worktime-Funktionen noch nicht implementiert", strict=False)
def test_filter_time_window_counts_only_6_to_22():
    """
    Arbeitszeit vor 06:00 und nach 22:00 wird NICHT zur betrieblichen Arbeitszeit gezählt,
    muss aber für ArbZG-Prüfungen (z.B. Ruhezeit) berücksichtigt werden.
    Erwartung: count_operational_hours() schneidet auf [06:00, 22:00].
    """
    from bbq.domain import count_operational_hours  # zu implementieren

    # 05:30–07:30 => 1h betriebliche Arbeitszeit (06:00–07:00)
    s1 = _shift(2025, 9, 15, 5, 30, 7, 30)
    # 21:00–23:30 => 1h betriebliche Arbeitszeit (21:00–22:00)
    s2 = _shift(2025, 9, 16, 21, 0, 23, 30)

    assert count_operational_hours([s1]) == 1.0
    assert count_operational_hours([s2]) == 1.0
    assert count_operational_hours([s1, s2]) == 2.0


@pytest.mark.xfail(reason="ArbZG-Tageslimit noch nicht implementiert", strict=False)
def test_daily_max_10h_violation_detected():
    """
    ArbZG: max. 10h/Tag (operative Stunden). Bei >10h => Verletzung.
    """
    from bbq.domain import detect_daily_limit_violations  # zu implementieren

    # 06:00–12:00 (6h) und 13:00–18:00 (5h) => 11h operativ => Verstoß
    s1 = _shift(2025, 9, 17, 6, 0, 12, 0)
    s2 = _shift(2025, 9, 17, 13, 0, 18, 0)

    violations = detect_daily_limit_violations([s1, s2])
    assert violations  # es gibt mind. einen Verstoß
    assert violations[0]["date"] == dt.date(2025, 9, 17)
    assert "10h" in violations[0]["rule"]


@pytest.mark.xfail(reason="Ruhezeitprüfung (11h) noch nicht implementiert", strict=False)
def test_min_rest_period_11h_between_shifts():
    """
    ArbZG: Mindestruhezeit 11h zwischen zwei Arbeitstagen.
    """
    from bbq.domain import check_min_rest_period  # zu implementieren

    # Tag1: 06:00–20:00, Tag2: 06:00–14:00 => Ruhezeit 10h => Verstoß
    day1 = _shift(2025, 9, 18, 6, 0, 20, 0)
    day2 = _shift(2025, 9, 19, 6, 0, 14, 0)

    ok, hours = check_min_rest_period(day1[1], day2[0])
    assert not ok
    assert hours == 10


@pytest.mark.xfail(reason="Gleitzeit-Berechnung noch nicht implementiert", strict=False)
def test_flex_time_accumulates_month_quarter_year():
    """
    Gleitzeit = (Summe operative Stunden - Sollstunden) pro Zeitraum.
    Erwartung: summarize_flex_time() liefert Werte für Monat/Quartal/Jahr.
    """
    from bbq.domain import summarize_flex_time  # zu implementieren

    weekly_target = 40  # Beispielmodell
    # Beispiel-Arbeitswoche: 5x 8h => 40h
    week = [
        _shift(2025, 1, 6, 6, 0, 14, 0),
        _shift(2025, 1, 7, 6, 0, 14, 0),
        _shift(2025, 1, 8, 6, 0, 14, 0),
        _shift(2025, 1, 9, 6, 0, 14, 0),
        _shift(2025, 1, 10, 6, 0, 14, 0),
    ]
    # Im Monat zusätzlich 2h Überzeit
    extra = _shift(2025, 1, 15, 20, 0, 22, 0)

    res = summarize_flex_time(shifts=week + [extra], weekly_target_hours=weekly_target)
    # Erwartung (Beispielwerte):
    assert res["month"]["hours"] == 2.0
    assert res["quarter"]["hours"] >= 2.0
    assert res["year"]["hours"] >= 2.0


@pytest.mark.xfail(reason="Frühwarnungen noch nicht implementiert", strict=False)
def test_warning_on_impending_violation():
    """
    Warnung bei drohender Verletzung (z. B. wenn geplanter Tag >10h werden würde).
    """
    from bbq.domain import simulate_and_warn  # zu implementieren

    planned = [
        _shift(2025, 9, 20, 6, 0, 12, 0),  # 6h
        _shift(2025, 9, 20, 13, 0, 18, 30),  # 5.5h => Summe 11.5h => Warnung
    ]
    warnings = simulate_and_warn(planned)
    assert warnings
    assert any("drohende Überschreitung 10h" in w["message"] for w in warnings)


@pytest.mark.xfail(reason="Ampellogik noch nicht implementiert", strict=False)
def test_ampel_logic_thresholds_from_settings():
    """
    Ampellogik (Gleitzeit): Grenzwerte aus Settings.
    Beispiel: grün <= 10h, gelb 10–20h, rot > 20h Überzeit.
    """
    from bbq.domain import ampel_status  # zu implementieren

    settings = {"green_max": 10.0, "yellow_max": 20.0}
    assert ampel_status(+5.0, settings) == "green"
    assert ampel_status(+15.0, settings) == "yellow"
    assert ampel_status(+25.0, settings) == "red"


@pytest.mark.xfail(reason="Passwortfluss noch nicht implementiert", strict=False)
def test_password_initial_set_and_change_flow(tmp_path):
    """
    Beim ersten Start muss ein individuelles Passwort gesetzt werden,
    später änderbar im Einstellungsmenü. Speicherung sicher (Hash, kein Klartext).
    """
    from bbq.security import PasswordManager  # zu implementieren

    store = tmp_path / "secrets.json"
    pm = PasswordManager(storage_path=store)

    # Erststart: kein Passwort -> Setzen
    assert not pm.is_initialized()
    pm.set_password("BBQ!2025_secure")
    assert pm.is_initialized()
    assert pm.verify("BBQ!2025_secure")

    # Änderung über Settings
    pm.change_password(old="BBQ!2025_secure", new="New#2025")
    assert pm.verify("New#2025")
    assert not pm.verify("BBQ!2025_secure")
