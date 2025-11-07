"""
Controller-Modul für das Zeiterfassungssystem.

Implementiert das MVC-Pattern als Vermittler zwischen Modell (Business-Logik)
und View (Benutzeroberfläche).

Hauptverantwortlichkeiten:
- Event-Handling und UI-Interaktionen
- Datenbindung zwischen Modell und View
- Timer-Management für Echtzeit-Anzeigen
- Navigation zwischen verschiedenen Views
- PopUp-Verwaltung und Benachrichtigungen
- Kalender-Logik und Mitarbeiter-Auswahl

Autor: Velqor
Version: 2.0
"""

from kivy.uix.screenmanager import ScreenManager
from modell import ModellLogin, ModellTrackTime
from view import LoginView, RegisterView, MainView
from kivy.core.window import Window
from kivymd.uix.pickers import MDDatePicker, MDTimePicker
from datetime import datetime, date, time as datetime_time, timedelta
from window_size import set_fixed_window_size
from kivy.clock import Clock
import time
import logging

# Logger für dieses Modul
logger = logging.getLogger(__name__)


class Controller():
    """
    Haupt-Controller-Klasse für die Zeiterfassungs-Anwendung.
    
    Verwaltet alle Interaktionen zwischen Benutzeroberfläche (View)
    und Geschäftslogik (Modell).
    
    Attributes:
        model_login (ModellLogin): Modell für Authentifizierung
        model_track_time (ModellTrackTime): Modell für Zeiterfassung
        sm (ScreenManager): Kivy ScreenManager für Navigation
        register_view (RegisterView): Registrierungs-Screen
        login_view (LoginView): Login-Screen
        main_view (MainView): Hauptanwendungs-Screen
        active_time_input: Aktuell aktives Zeit-Eingabefeld
        timer_event: Geplantes Event für Timer-Updates
        start_time_dt (datetime): Startzeitpunkt für Timer-Berechnung
        arbeitsfenster_warning_event: Geplantes Event für Arbeitsfenster-Warnung
        max_arbeitszeit_warning_event: Geplantes Event für Max-Arbeitszeit-Warnung
    """
    def __init__(self):
        try:
            self.model_login = ModellLogin()
            self.model_track_time = ModellTrackTime()
            self.sm = ScreenManager()
            self.register_view = RegisterView(name="register")
            self.login_view = LoginView(name="login")
            self.main_view = MainView(name="main")
            self.active_time_input = None
            
            # Status für den Timer
            self.timer_event = None
            self.start_time_dt = None
            
            # Warnungs-Events für Arbeitsfenster und max. Arbeitszeit
            self.arbeitsfenster_warning_event = None
            self.max_arbeitszeit_warning_event = None
            
            # Screens ins ScreenManager packen
            self.sm.add_widget(self.register_view)
            self.sm.add_widget(self.login_view)
            self.sm.add_widget(self.main_view)
            self.sm.current = "login"
            # === Bindings ===
            # Binden der Funktionen mit Fehlerbehandlung
            self._bind_safe(self.login_view.change_view_registrieren_button, 'on_press', self.change_view_register)
            self._bind_safe(self.register_view.change_view_login_button, 'on_press', self.change_view_login)
            self._bind_safe(self.login_view.login_button, 'on_press', self.einloggen_button_clicked)
            self._bind_safe(self.main_view.change_password_button, 'on_press', self.passwort_ändern_button_clicked)
            self._bind_safe(self.register_view.reg_geburtsdatum, 'focus', self.show_date_picker)
            self._bind_safe(self.register_view.date_picker, 'on_save', self.on_date_selected_register)
            self._bind_safe(self.main_view.date_input, 'focus', self.show_date_picker)
            self._bind_safe(self.main_view.date_picker, 'on_save', self.on_date_selected_main)
            self._bind_safe(self.main_view.time_input, 'focus', self.show_time_picker)
            self._bind_safe(self.main_view.time_picker, 'on_save', self.on_time_selected)
            self._bind_safe(self.main_view.checkbox, 'active', self.on_checkbox_changed)
            self._bind_safe(self.main_view.eintrag_art_spinner, 'text', self.on_eintrag_art_selected)
            self._bind_safe(self.main_view.month_calendar.employee_spinner, 'text', self.on_employee_selected)
            self._bind_safe(self.register_view.register_button, 'on_press', self.registrieren_button_clicked)
            self._bind_safe(self.register_view.reg_woechentliche_arbeitszeit, 'text', self.on_weekly_hours_selected)
            self._bind_safe(self.main_view.stempel_button, 'on_press', self.stempel_button_clicked)
            self._bind_safe(self.main_view.nachtragen_button, 'on_press', self.nachtragen_button_clicked)
            self._bind_safe(self.main_view.month_calendar.prev_btn, 'on_release', self.prev_button_clicked)
            self._bind_safe(self.main_view.month_calendar.next_btn, 'on_release', self.next_button_clicked)

            self._bind_safe(
                self.main_view.edit_week_hours_button,
                'on_release',
                lambda *_: self.on_settings_edit_button("Vertragliche Wochenstunden", "week_hours_value_label")
            )
            self._bind_safe(
                self.main_view.edit_green_limit_button,
                'on_release',
                lambda *_: self.on_settings_edit_button("Ampel grün (h)", "green_limit_value_label")
            )
            self._bind_safe(
                self.main_view.edit_red_limit_button,
                'on_release',
                lambda *_: self.on_settings_edit_button("Ampel rot (h)", "red_limit_value_label")
            )
            self._bind_safe(
                self.main_view.save_settings_button,
                'on_release',
                self.save_settings_button_clicked
            )
            self._bind_safe(
                self.main_view.logout_button,
                'on_press',
                self.logout_button_clicked
            )

            self.main_view.month_calendar.day_selected_callback = self.day_selected
            self.main_view.bind(on_settings_value_selected=self.on_settings_value_selected)

            # Controller-Referenz im MonthCalendar setzen für Edit/Delete-Callbacks
            self.main_view.month_calendar.controller = self
            
            # Tab-Wechsel beobachten: Beim Öffnen des Zeiterfassungs-/Gleitzeit-Tabs neu berechnen
            try:
                self.main_view.layout.bind(current_tab=self.on_tab_changed)
            except Exception as e:
                logger.error(f"Konnte Tab-Wechsel nicht binden: {e}")
            
            logger.debug("Controller initialisiert und alle Widgets gebunden.")
        except Exception as e:
            logger.critical(f"Kritischer Fehler während der Controller-Initialisierung: {e}", exc_info=True)
            # Dieser Fehler muss nach oben weitergegeben werden, siehe main.py
            raise
    
    # === Hilfsmethoden ===
    
    def _bind_safe(self, widget, event, callback):
        """
        Bindet Callbacks mit automatischer Fehlerbehandlung.
        
        Wrapper-Funktion, die jedes Callback in einen try-except-Block hüllt,
        um Abstürze bei Laufzeitfehlern zu verhindern.
        
        Args:
            widget: Das Kivy-Widget, an das gebunden werden soll
            event (str): Der Event-Name (z.B. 'on_press', 'on_release')
            callback (callable): Die aufzurufende Callback-Funktion
            
        Note:
            Bei Fehlern wird der Fehler geloggt und optional eine MessageBox angezeigt.
            Die Anwendung läuft weiter.
        """
        def safe_callback(*args, **kwargs):
            try:
                return callback(*args, **kwargs)
            except Exception as e:
                # Verhindert den Absturz der App bei einem Fehler im Callback
                logger.error(f"Fehler im Callback '{callback.__name__}' ausgelöst durch '{event}' auf {widget}: {e}", exc_info=True)
                # Optional: Dem Benutzer eine Fehlermeldung anzeigen
                if hasattr(self, 'main_view') and hasattr(self.main_view, 'show_messagebox'):
                    self.main_view.show_messagebox("Unerwarteter Fehler", f"Ein Fehler ist aufgetreten:\n{e}")

        widget.bind(**{event: safe_callback})

    # === View-Wechsel-Methoden ===

    def on_settings_edit_button(self, field_label, label_attr):
        """
        Öffnet den Einstellungs-Editor für ein bestimmtes Feld.
        
        Args:
            field_label (str): Beschriftung des zu bearbeitenden Feldes
            label_attr (str): Attribut-Name des Labels in der View
        """
        current_value = ""
        if hasattr(self.main_view, label_attr):
            current_value = getattr(self.main_view, label_attr).text
        if hasattr(self.main_view, "open_settings_edit_popup"):
            self.main_view.open_settings_edit_popup(field_label, current_value, label_attr)

    def on_settings_value_selected(self, instance, field_label, new_value, label_attr):
        """
        Aktualisiert das Label in der View mit dem neuen Einstellungswert.
        
        Wird vom View-Event ausgelöst, wenn ein Wert im Einstellungs-Popup
        ausgewählt wurde. Formatiert den Wert entsprechend dem Feld-Typ.
        
        Args:
            instance: Das auslösende Widget (MainView)
            field_label (str): Beschriftung des bearbeiteten Feldes
            new_value (str): Der neue Wert als String
            label_attr (str): Name des Label-Attributs in der View
            
        Note:
            Wochenstunden und Ampelgrenzen erhalten ein 'h'-Suffix (für Stunden).
            Andere Werte werden ohne Formatierung übernommen.
        """
        # Prüfen ob das Label-Attribut existiert
        if hasattr(self.main_view, label_attr):
            # Formatierung basierend auf Feld-Typ
            if new_value:
                if label_attr == "week_hours_value_label":
                    # Wochenstunden: Füge " h" hinzu
                    display_value = f"{new_value} h"
                elif label_attr in {"green_limit_value_label", "red_limit_value_label"}:
                    # Ampelgrenzen: Füge " h" hinzu
                    display_value = f"{new_value} h"
                else:
                    # Andere Felder: Unverändert
                    display_value = new_value
            else:
                # Leerer Wert
                display_value = new_value
            
            # Label-Text aktualisieren
            getattr(self.main_view, label_attr).text = display_value

    def save_settings_button_clicked(self, *_):
        """
        Speichert geänderte Einstellungen in der Datenbank.
        
        Verarbeitet Änderungen an:
        - Vertragliche Wochenstunden
        - Ampel-Grenzwerte (grün und rot)
        
        Führt Validierung durch und zeigt Feedback-Messages.
        
        Args:
            *_: Kivy Event-Parameter (werden ignoriert)
            
        Note:
            Ampel-Grenzwerte werden auf symmetrische Logik validiert (rot > grün, beide positiv).
        """
        if not self.model_track_time or self.model_track_time.aktueller_nutzer_id is None:
            if hasattr(self.main_view, "show_messagebox"):
                self.main_view.show_messagebox("Fehler", "Keine Nutzeranmeldung aktiv.")
            return

        def _extract_numeric(label):
            """Extrahiert numerischen Wert aus Label-Text (entfernt 'h'-Suffix)."""
            text = (label.text if label and label.text else "").strip()
            if text.endswith("h"):
                text = text[:-1].strip()
            return text

        week_hours_text = _extract_numeric(getattr(self.main_view, "week_hours_value_label", None))
        green_limit_text = _extract_numeric(getattr(self.main_view, "green_limit_value_label", None))
        red_limit_text = _extract_numeric(getattr(self.main_view, "red_limit_value_label", None))

        try:
            neue_wochenstunden = int(week_hours_text)
        except (TypeError, ValueError):
            if hasattr(self.main_view, "show_messagebox"):
                self.main_view.show_messagebox("Fehler", "Vertragliche Wochenstunden müssen eine Zahl sein.")
            return

        try:
            ampel_gruen = int(green_limit_text)
            ampel_rot = int(red_limit_text)
        except (TypeError, ValueError):
            if hasattr(self.main_view, "show_messagebox"):
                self.main_view.show_messagebox("Fehler", "Ampelgrenzen müssen ganze Stunden sein.")
            return

        result_hours = self.model_track_time.aktualisiere_vertragliche_wochenstunden(neue_wochenstunden)
        if isinstance(result_hours, dict) and result_hours.get("error"):
            if hasattr(self.main_view, "show_messagebox"):
                self.main_view.show_messagebox("Fehler", result_hours.get("error"))
            return

        result_ampel = self.model_track_time.aktualisiere_ampelgrenzen(ampel_gruen, ampel_rot)
        if isinstance(result_ampel, dict) and result_ampel.get("error"):
            if hasattr(self.main_view, "show_messagebox"):
                self.main_view.show_messagebox("Fehler", result_ampel.get("error"))
            return

        self.model_track_time.set_ampel_farbe()
        self.update_view_time_tracking()

        if hasattr(self.main_view, "show_messagebox"):
            self.main_view.show_messagebox("Erfolg", "Einstellungen wurden gespeichert.")

    def logout_button_clicked(self, *_):
        """
        Loggt den Nutzer aus und kehrt zur Login-Seite zurück.
        Setzt alle relevanten Modell-, Controller- und View-Daten zurück.
        """
        logger.info(f"Logout-Versuch für Nutzer ID: {self.model_track_time.aktueller_nutzer_id if self.model_track_time else 'None'}")
        
        # Timer stoppen falls aktiv
        if hasattr(self, 'timer_event') and self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None
        
        # Model Track Time zurücksetzen
        if self.model_track_time:
            # Nutzer-Daten
            self.model_track_time.aktueller_nutzer_id = None
            self.model_track_time.aktueller_nutzer_name = None
            self.model_track_time.aktueller_nutzer_gleitzeit = 0
            self.model_track_time.aktueller_nutzer_vertragliche_wochenstunden = 0
            self.model_track_time.benachrichtigungen = []
            self.model_track_time._cached_aktueller_nutzer = None
            
            # Kalender-Daten zurücksetzen
            self.model_track_time.aktuelle_kalendereinträge_für_id = None
            self.model_track_time.aktuelle_kalendereinträge_für_name = None
            self.model_track_time.bestimmtes_datum = None
            self.model_track_time.zeiteinträge_bestimmtes_datum = None
            self.model_track_time.gleitzeit_bestimmtes_datum_stunden = 0.0
            
            # Nachtrag-Daten zurücksetzen
            self.model_track_time.nachtragen_datum = None
            self.model_track_time.manueller_stempel_uhrzeit = None
            
            # Weitere Modell-Variablen
            self.model_track_time.feedback_stempel = ""
        
        # Login-Model zurücksetzen
        if self.model_login:
            self.model_login.anmeldung_name = ""
            self.model_login.anmeldung_passwort = ""
            self.model_login.anmeldung_rückmeldung = ""
            self.model_login.anmeldung_mitarbeiter_id_validiert = None
        
        # Login-View Felder leeren
        if self.login_view:
            self.login_view.username_input.text = ""
            self.login_view.password_input.text = ""
            self.login_view.anmeldung_rückmeldung_label.text = ""
        
        # Main-View Kalender zurücksetzen (falls vorhanden)
        if self.main_view:
            try:
                # Kalender-Dropdown zurücksetzen und als "ungültig" markieren
                if hasattr(self.main_view, 'month_calendar') and hasattr(self.main_view.month_calendar, 'employee_spinner'):
                    spinner = self.main_view.month_calendar.employee_spinner
                    spinner.text = ""
                    spinner.values = []  # Auch values leeren, damit alte Werte nicht mehr gültig sind
                
                # Kalender-Anzeige leeren
                if hasattr(self.main_view, 'calendar_label'):
                    self.main_view.calendar_label.text = ""
                
                # Zeitstempel-Liste leeren
                if hasattr(self.main_view.month_calendar, 'times_box'):
                    self.main_view.month_calendar.times_box.clear_widgets()
                    
            except Exception as e:
                logger.warning(f"Fehler beim Zurücksetzen der View-Elemente: {e}")
        
        logger.info("Logout erfolgreich, alle Daten zurückgesetzt, wechsle zur Login-Ansicht")
        
        # Zur Login-Seite wechseln
        self.change_view_login(None)

    def _format_hours_minutes(self, hours_float):
        """
        Formatiert eine Stundenzahl als String in Stunden und Minuten.
        
        Args:
            hours_float (float): Stunden als Dezimalzahl (z.B. 1.5, -2.75)
            
        Returns:
            str: Formatierter String (z.B. "1h 30min", "-2h 45min")
            
        Examples:
            >>> _format_hours_minutes(1.5)
            "1h 30min"
            >>> _format_hours_minutes(-2.75)
            "-2h 45min"
            >>> _format_hours_minutes(None)
            "0h 0min"
        """
        # Prüfen ob es ein String ist (z.B. "Stempel vervollständigen...")
        if isinstance(hours_float, str):
            return hours_float
        
        if hours_float is None:
            return "0h 0min"
        
        stunden = int(hours_float)
        minuten = int(abs((hours_float - stunden) * 60))
        vorzeichen = "-" if hours_float < 0 else ""
        
        return f"{vorzeichen}{abs(stunden)}h {minuten}min"
    
    def _can_edit_selected_employee(self):
        """
        Prüft, ob der eingeloggte Benutzer den ausgewählten Kalender bearbeiten darf.
        
        Returns:
            bool: True wenn der ausgewählte Kalender dem eingeloggten User gehört,
                  False wenn ein anderer Mitarbeiter ausgewählt ist (Vorgesetzten-Ansicht)
                  
        Note:
            Wird verwendet, um Bearbeitungs-/Lösch-Operationen zu autorisieren.
            Vorgesetzte können Kalender ihrer Mitarbeiter nur ansehen, nicht bearbeiten.
        """
        model = self.model_track_time
        if not model:
            return False
        selected_id = getattr(model, "aktuelle_kalendereinträge_für_id", None)
        if selected_id in (None, model.aktueller_nutzer_id):
            return True
        return False
    # === Modell-View-Synchronisation ===
    
    def update_model_login(self):
        """
        Überträgt Benutzereingaben von den Views ins Login-Modell.
        
        Kopiert alle Registrierungs- und Login-Daten aus den
        Eingabefeldern in die entsprechenden Modell-Attribute.
        
        Note:
            Wird vor jeder Login-/Registrierungs-Aktion aufgerufen,
            um sicherzustellen, dass das Modell die aktuellen Eingaben hat.
        """
        # Registrierungsdaten übertragen
        self.model_login.neuer_nutzer_name = self.register_view.reg_username_input.text
        self.model_login.neuer_nutzer_passwort = self.register_view.reg_password_input.text
        self.model_login.neuer_nutzer_passwort_val = self.register_view.reg_password_input_rep.text
        self.model_login.neuer_nutzer_geburtsdatum = self.register_view.reg_geburtsdatum.text
        self.model_login.neuer_nutzer_vertragliche_wochenstunden = self.register_view.reg_woechentliche_arbeitszeit.text
        self.model_login.neuer_nutzer_vorgesetzter = self.register_view.reg_superior.text
        self.model_login.neuer_nutzer_grün = self.register_view.reg_limit_green.text
        self.model_login.neuer_nutzer_rot = self.register_view.reg_limit_red.text
        
        # Login-Daten übertragen
        self.model_login.anmeldung_name = self.login_view.username_input.text
        self.model_login.anmeldung_passwort = self.login_view.password_input.text
    
    # === Modell-View-Synchronisation ===
    
    def update_view_login(self):
        """
        Aktualisiert Login-/Register-View mit Daten aus dem Modell.
        
        Überträgt Feedback-Nachrichten vom Modell zur Anzeige in der UI.
        """
        self.register_view.register_rückmeldung_label.text = self.model_login.neuer_nutzer_rückmeldung
        self.login_view.anmeldung_rückmeldung_label.text = self.model_login.anmeldung_rückmeldung
    
    def update_model_time_tracking(self):
        """
        Überträgt Daten von der View ins Zeiterfassungs-Modell.
        
        Synchronisiert alle relevanten Eingabefelder mit dem Modell,
        einschließlich Datum, Uhrzeit, Abwesenheitsart und Passwort-Änderungen.
        """
        self.model_track_time.aktueller_nutzer_id = self.model_login.anmeldung_mitarbeiter_id_validiert
        self.model_track_time.get_user_info()
        self.model_track_time.nachtragen_datum = self.main_view.date_input.text
        self.model_track_time.manueller_stempel_uhrzeit = self.main_view.time_input.text
        self.model_track_time.neuer_abwesenheitseintrag_art = self.main_view.eintrag_art_spinner.text
        self.model_track_time.neues_passwort = self.main_view.new_password_input.text
        self.model_track_time.neues_passwort_wiederholung = self.main_view.repeat_password_input.text
        self.model_track_time.bestimmtes_datum = self.main_view.month_calendar.date_label.text
    
    def update_view_time_tracking(self):
        """
        Aktualisiert Zeiterfassungs-View mit Daten aus dem Modell.
        
        Überträgt alle relevanten Informationen:
        - Benutzername und Begrüßung
        - Aktuelle Gleitzeit (formatiert als Stunden und Minuten)
        - Feedback-Nachrichten für Operationen
        - Einstellungen (Geburtsdatum, Wochenstunden, Ampel-Werte)
        - Benachrichtigungen
        - Kalender-Einträge
        - Gleitzeit-Ampel-Farbe
        """
        self.main_view.welcome_label.text = f"Willkommen zurück, {self.model_login.anmeldung_name}!"
        
        # Gleitzeit in Stunden und Minuten umwandeln
        gleitzeit_stunden = self.model_track_time.aktueller_nutzer_gleitzeit or 0
        stunden = int(gleitzeit_stunden)
        minuten = int(abs((gleitzeit_stunden - stunden) * 60))
        vorzeichen = "-" if gleitzeit_stunden < 0 else ""
        gleitzeit_str = f"{vorzeichen}{abs(stunden)}h {minuten}min"
        
        self.main_view.anzeige_gleitzeit_wert_label.text = gleitzeit_str
        self.main_view.nachtrag_feedback.text = self.model_track_time.feedback_manueller_stempel
        self.main_view.change_password_feedback.text = self.model_track_time.feedback_neues_passwort

        if hasattr(self.main_view, "name_value_label"):
            self.main_view.name_value_label.text = self.model_track_time.aktueller_nutzer_name or ""

        if hasattr(self.main_view, "birth_value_label"):
            geburtstag = self.model_track_time.aktueller_nutzer_geburtsdatum
            if isinstance(geburtstag, date):
                birth_text = geburtstag.strftime("%d.%m.%Y")
            elif isinstance(geburtstag, str):
                birth_text = geburtstag
            else:
                birth_text = ""
            self.main_view.birth_value_label.text = birth_text

        if hasattr(self.main_view, "week_hours_value_label"):
            wochenstunden = self.model_track_time.aktueller_nutzer_vertragliche_wochenstunden
            self.main_view.week_hours_value_label.text = f"{wochenstunden} h" if wochenstunden is not None else ""

        if hasattr(self.main_view, "green_limit_value_label"):
            ampel_gruen = self.model_track_time.aktueller_nutzer_ampel_grün
            self.main_view.green_limit_value_label.text = f"{ampel_gruen} h" if ampel_gruen is not None else ""

        if hasattr(self.main_view, "red_limit_value_label"):
            ampel_rot = self.model_track_time.aktueller_nutzer_ampel_rot
            self.main_view.red_limit_value_label.text = f"{ampel_rot} h" if ampel_rot is not None else ""

        if self.model_track_time.ampel_status:
            self.main_view.ampel.set_state(state=self.model_track_time.ampel_status)

        spinner = self.main_view.month_calendar.employee_spinner
        spinner.values = self.model_track_time.mitarbeiter
        aktueller_name = self.model_track_time.aktueller_nutzer_name
        
        # WICHTIG: Spinner nur zurücksetzen, wenn keine gültige Auswahl vorhanden ist
        # Erlaubt Vorgesetzten, andere Mitarbeiter auszuwählen
        if aktueller_name:
            # Wenn Spinner leer ist ODER der aktuelle Text nicht in den verfügbaren Werten ist
            # DANN auf aktuellen Nutzer zurücksetzen
            if not spinner.text or spinner.text not in spinner.values:
                spinner.text = aktueller_name
                self.model_track_time.aktuelle_kalendereinträge_für_name = aktueller_name
                self.model_track_time.aktuelle_kalendereinträge_für_id = self.model_track_time.aktueller_nutzer_id
            # Wenn eine gültige Auswahl existiert, Model synchronisieren
            elif spinner.text != self.model_track_time.aktuelle_kalendereinträge_für_name:
                self.model_track_time.aktuelle_kalendereinträge_für_name = spinner.text
                self.model_track_time.get_id()  # ID aus Namen ableiten
        else:
            spinner.text = ""
            
        # Kumulierte Gleitzeit auch in Stunden und Minuten umwandeln
        self.main_view.flexible_time_month.text = self._format_hours_minutes(self.model_track_time.kummulierte_gleitzeit_monat)
        self.main_view.flexible_time_quarter.text = self._format_hours_minutes(self.model_track_time.kummulierte_gleitzeit_quartal)
        self.main_view.flexible_time_year.text = self._format_hours_minutes(self.model_track_time.kummulierte_gleitzeit_jahr)
        self.main_view.month_calendar.times_box.clear_widgets()  
        allow_edit = self._can_edit_selected_employee()
        gleitzeit_tag = self.model_track_time.gleitzeit_bestimmtes_datum_stunden
        if gleitzeit_tag is None:
            gleitzeit_tag = 0.0
        gleitzeit_text = self._format_hours_minutes(gleitzeit_tag)
        self.main_view.month_calendar.flexible_time_label.text = gleitzeit_text
        if self.model_track_time.zeiteinträge_bestimmtes_datum is not None:
            for stempel in self.model_track_time.zeiteinträge_bestimmtes_datum:
                # Sicherstellen, dass 'stempel' das erwartete Format hat
                if isinstance(stempel, list) and len(stempel) >= 2 and hasattr(stempel[0], 'zeit'):
                    zeiteintrag_obj = stempel[0]
                    zeit_str = zeiteintrag_obj.zeit.strftime("%H:%M")
                    stempel_id = zeiteintrag_obj.id
                    date_str = self.main_view.month_calendar.date_label.text  # Aktuell angezeigtes Datum
                    self.main_view.month_calendar.add_time_row(
                        stempelzeit=zeit_str, 
                        is_problematic=stempel[1],
                        stempel_id=stempel_id,
                        date_str=date_str,
                        allow_edit=allow_edit,
                        gleitzeit_text=gleitzeit_text
                    )
                else:
                    logger.warning(f"Unerwartetes Stempelformat in update_view_time_tracking: {stempel}")
    def update_view_benachrichtigungen(self):
        """
        Aktualisiert die Benachrichtigungs-View mit aktuellen Meldungen.
        
        Löscht alle bestehenden Benachrichtigungs-Widgets und fügt die
        aktuellen Benachrichtigungen aus dem Modell neu hinzu.
        
        Note:
            Bei Fehlern beim Erstellen einzelner Benachrichtigungen wird
            ein Fehler geloggt, aber die Verarbeitung fortgesetzt.
        """
        # Grid leeren
        logger.debug(f"update_view_benachrichtigungen: Clearing widgets. Current count: {len(self.main_view.benachrichtigungen_grid.children)}")
        self.main_view.benachrichtigungen_grid.clear_widgets()
        logger.debug(f"update_view_benachrichtigungen: After clear. Count: {len(self.main_view.benachrichtigungen_grid.children)}")
        logger.debug(f"update_view_benachrichtigungen: Anzahl Benachrichtigungen im Modell: {len(self.model_track_time.benachrichtigungen)}")
        
        # Alle Benachrichtigungen aus dem Modell hinzufügen
        for i, nachricht in enumerate(self.model_track_time.benachrichtigungen):
            try:
                # Fehlermeldung erstellen (formatierter Text)
                msg_text = nachricht.create_fehlermeldung()
                msg_datum = nachricht.datum or "Kein Datum"
                logger.debug(f"  Benachrichtigung {i+1}: Code={nachricht.benachrichtigungs_code}, Datum={msg_datum}")
                
                # Widget zur View hinzufügen
                self.main_view.add_benachrichtigung(text=msg_text, datum=msg_datum)
            except Exception as e:
                logger.error(f"Fehler beim Erstellen der Benachrichtigungs-UI: {e}", exc_info=True)
    
    # === Button-Click-Handler (Alle Callbacks werden bereits durch _bind_safe geschützt) ===
    
    def einloggen_button_clicked(self, b):
        """
        Handler für Login-Button.
        
        Führt Login-Prozess durch und initialisiert alle Daten:
        - Authentifizierung
        - Laden der Benutzerdaten
        - Prüfung aller Arbeitszeitschutz-Regelungen
        - Bereinigung korrigierter Benachrichtigungen
        - Laden von Nachrichten und Ampel-Status
        - Start des visuellen Timers
        
        Args:
            b: Kivy Button-Instanz (wird nicht verwendet)
            
        Ablauf (10 Schritte):
            1. Benutzereingaben (Name, Passwort) ins Modell übertragen
            2. model_login.login() aufrufen → Authentifizierung mit bcrypt
            3. Bei Erfolg: Zur Hauptansicht wechseln
            4. Benutzerdaten laden (update_model_time_tracking)
            5. ALLE Arbeitszeitschutz-Prüfungen durchführen:
               - checke_arbeitstage() - Fehlende Arbeitstage identifizieren
               - checke_stempel() - Fehlende Stempel identifizieren
               - berechne_gleitzeit() - Gleitzeit aktualisieren (MUSS vor set_ampel_farbe!)
               - checke_ruhezeiten() - ArbZG § 5 (11h Ruhezeit)
               - checke_durchschnittliche_arbeitszeit() - ArbZG § 3 (Ø 8h/Tag über 6 Monate)
               - checke_max_arbeitszeit() - 10h/Tag Maximum
               - checke_sonn_feiertage() - ArbZG § 9 (Sonntagsruhe)
               - checke_wochenstunden_minderjaehrige() - JArbSchG § 8 (40h/Woche)
               - checke_arbeitstage_pro_woche_minderjaehrige() - JArbSchG § 15 (max. 5 Tage)
               - checke_arbeitszeitfenster_minderjaehrige() - JArbSchG § 14 (6-20 Uhr)
            6. Benachrichtigungs-Korrektur: pruefe_und_korrigiere_arbeitszeitschutz_benachrichtigungen()
               → Löscht Benachrichtigungen für korrigierte Verstöße (MUSS vor get_messages()!)
            7. Daten für UI holen: get_messages(), set_ampel_farbe(), kummuliere_gleitzeit()
            8. Mitarbeiter-Liste laden (für Vorgesetzten-Ansicht): get_employees()
            9. letzter_login auf heute setzen (NACH allen Checks, damit korrekter Zeitraum!)
            10. UI aktualisieren und Timer starten
            
        Warum diese Reihenfolge?
            - Gleitzeit-Berechnung MUSS VOR Ampel-Farbe erfolgen (Ampel basiert auf Gleitzeit)
            - Arbeitszeitschutz-Checks MÜSSEN VOR Benachrichtigungs-Korrektur erfolgen (neue Checks erstellen Meldungen)
            - Benachrichtigungs-Korrektur MUSS VOR get_messages() erfolgen (sonst werden gelöschte Meldungen angezeigt)
            - letzter_login-Update AM ENDE, damit alle Checks den Zeitraum "letzter_login bis gestern" korrekt abdecken
        """
        # === SCHRITT 1: Eingaben ins Modell übertragen ===
        self.update_model_login()
        
        # === SCHRITT 2: Authentifizierung durchführen ===
        success = self.model_login.login()  # bcrypt-Passwort-Vergleich
        
        # === Feedback an View zurückgeben ===
        self.update_view_login()
        
        if success:
            logger.info("Login erfolgreich, starte Daten-Lade-Prozess...")
            
            # === SCHRITT 3: Zur Hauptansicht wechseln ===
            self.change_view_main(b=None)
            
            # === SCHRITT 4: Benutzerdaten laden ===
            self.update_model_time_tracking()
            
            # === SCHRITT 5: ALLE Arbeitszeitschutz-Prüfungen durchführen ===
            # Fehlende Arbeitstage finden (Code 1 Benachrichtigung)
            self.model_track_time.checke_arbeitstage()
            
            # Fehlstempel finden (Code 2 Benachrichtigung)
            self.model_track_time.checke_stempel()
            
            # Gleitzeit berechnen (MUSS vor set_ampel_farbe sein!)
            self.model_track_time.berechne_gleitzeit()
            
            # Ruhezeiten prüfen: ArbZG § 5 / JArbSchG § 13 (11h zwischen Arbeitstagen)
            self.model_track_time.checke_ruhezeiten()  # Code 3
            
            # Durchschnittliche Arbeitszeit prüfen: ArbZG § 3 (Ø max. 8h/Tag über 6 Monate)
            self.model_track_time.checke_durchschnittliche_arbeitszeit()  # Code 4
            
            # Maximale Tagesarbeitszeit prüfen: 10h/Tag
            self.model_track_time.checke_max_arbeitszeit()  # Code 5
            
            # Sonn- und Feiertagsarbeit prüfen: ArbZG § 9
            self.model_track_time.checke_sonn_feiertage()  # Code 6
            
            # Wochenstunden für Minderjährige prüfen: JArbSchG § 8 (max. 40h/Woche)
            self.model_track_time.checke_wochenstunden_minderjaehrige()  # Code 7
            
            # Arbeitstage pro Woche für Minderjährige: JArbSchG § 15 (max. 5 Tage)
            self.model_track_time.checke_arbeitstage_pro_woche_minderjaehrige()  # Code 8
            
            # Arbeitszeitfenster für Minderjährige: JArbSchG § 14 (6-20 Uhr)
            self.model_track_time.checke_arbeitszeitfenster_minderjaehrige()  # Code 9
            
            # Pausenzeiten prüfen: ArbZG § 4 / JArbSchG § 11 (Mindestpausen)
            self.model_track_time.checke_pausenzeiten()  # Code 12
            
            # === SCHRITT 6: Benachrichtigungs-Korrektur (Codes 3-9, 12) ===
            # WICHTIG: MUSS VOR get_messages() aufgerufen werden!
            # Löscht Benachrichtigungen, deren Verstöße korrigiert wurden (z.B. Stempel nachgetragen)
            geloeschte = self.model_track_time.pruefe_und_korrigiere_arbeitszeitschutz_benachrichtigungen()
            if geloeschte > 0:
                logger.info(f"Login: {geloeschte} korrigierte Arbeitszeitschutz-Benachrichtigungen gelöscht")
            
            # === SCHRITT 7: Daten für UI holen ===
            self.model_track_time.get_messages()        # Benachrichtigungen aus DB laden
            self.model_track_time.set_ampel_farbe()     # Ampel-Status berechnen (grün/gelb/rot)
            self.model_track_time.kummuliere_gleitzeit()  # Gleitzeit für Monat/Quartal/Jahr
            
            # === SCHRITT 8: Mitarbeiter-Liste laden (für Vorgesetzten-Ansicht) ===
            self.model_track_time.get_employees()
            
            # === SCHRITT 9: letzter_login aktualisieren (NACH allen Checks!) ===
            # Grund: Checks verwenden Zeitraum "letzter_login bis gestern"
            # Wenn wir vorher updaten, würden keine Checks durchgeführt (Zeitraum leer)
            self.model_track_time.update_letzter_login()
            
            # === SCHRITT 10: UI aktualisieren und Timer starten ===
            self.update_view_time_tracking()            # Gleitzeit, Ampel, etc. anzeigen
            self.update_view_benachrichtigungen()       # Benachrichtigungen anzeigen
            self.start_or_stop_visual_timer()           # Timer starten wenn eingestempelt
            
            # Kalender-Einstellungen initialisieren
            self.model_track_time.aktuelle_kalendereinträge_für_id = self.model_track_time.aktueller_nutzer_id
            self.model_track_time.aktuelle_kalendereinträge_für_name = self.model_track_time.aktueller_nutzer_name
            self.load_vacation_days_for_calendar()      # Urlaubstage für Kalender-Ansicht laden
            
            logger.info("Daten-Lade-Prozess abgeschlossen, MainView angezeigt.")
    
    def registrieren_button_clicked(self, b):
        """
        Handler für Registrierungs-Button.
        
        Führt die Benutzerregistrierung durch mit vollständiger Validierung
        (Pflichtfelder, Passwort-Match, Alter, Ampel-Werte, etc.).
        
        Args:
            b: Kivy Button-Instanz (wird nicht verwendet)
        """
        self.update_model_login()
        self.model_login.neuen_nutzer_anlegen()
        self.update_view_login()
    
    def stempel_button_clicked(self, b):
        """
        Handler für Stempel-Button (Ein-/Ausstempeln).
        
        Führt mehrstufigen Prüf- und Bestätigungsprozess durch:
        
        Prüf-Kaskade (5 Stufen):
            1. Arbeitszeitfenster-Prüfung → _stempel_nach_arbeitsfenster_warnung()
               - Minderjährige: 6-20 Uhr (JArbSchG § 14)
               - Erwachsene: 6-22 Uhr
               - Bei Verstoß: Warnung mit Ja/Nein-Dialog
            
            2. Ruhezeiten-Prüfung → _stempel_nach_ruhezeiten_warnung()
               - Mindestens 11h zwischen letztem Ausstempel und neuem Einstempel
               - ArbZG § 5 / JArbSchG § 13
               - Bei Verstoß: Warnung mit Ja/Nein-Dialog
            
            3. Urlaubstag-Prüfung → _urlaub_loeschen_und_stempeln()
               - Prüft ob heute Urlaub eingetragen ist
               - Bei JA: Warnung "Urlaub löschen und stempeln?" mit Ja/Nein-Dialog
            
            4. 6-Tage-Woche-Prüfung (nur Minderjährige)
               - JArbSchG § 15: Max. 5 Arbeitstage pro Woche
               - Prüft ob bereits 5 Tage in aktueller Woche gearbeitet
               - Bei JA: Warnung mit Ja/Nein-Dialog
            
            5. Stempel-Ausführung → _stempel_ausfuehren()
               - Tatsächliches Eintragen des Stempels in DB
               - Gleitzeit-Berechnung
               - PopUp-Warnungen erstellen (Code 10, 11)
               - UI aktualisieren
        
        Ablauf-Logik:
            - Jede Prüfung kann zum Abbruch führen (Benutzer klickt "Nein")
            - Bei "Ja" wird die nächste Prüfung aufgerufen
            - Nur wenn ALLE Prüfungen bestanden/bestätigt: Stempel wird eingetragen
        
        Args:
            b: Kivy Button-Instanz (wird nicht verwendet)
            
        Note:
            Dieser mehrstufige Prozess verhindert versehentliche Verstöße gegen
            das Arbeitszeitschutzgesetz durch defensive Programmierung.
        """
        # === Aktuelles Datum und Uhrzeit ermitteln ===
        from datetime import datetime, date as _date
        jetzt = datetime.now()
        datum_str = jetzt.strftime("%d.%m.%Y")
        uhrzeit_str = jetzt.strftime("%H:%M:%S")
        
        # === STUFE 1: Arbeitszeitfenster-Prüfung ===
        # Prüft ob Stempel innerhalb der erlaubten Zeiten liegt
        # Minderjährige: 6-20 Uhr, Erwachsene: 6-22 Uhr
        try:
            arbeitsfenster_result = self.model_track_time.pruefe_arbeitszeit_fenster(
                jetzt.date(),  # Heutiges Datum
                jetzt.time()   # Aktuelle Uhrzeit
            )
            
            # Wenn außerhalb des Arbeitsfensters: Warnung anzeigen
            if arbeitsfenster_result.get('verletzt', False):
                ist_minderjaehrig = arbeitsfenster_result['ist_minderjaehrig']
                erlaubte_start = arbeitsfenster_result['erlaubte_start_zeit']
                erlaubte_end = arbeitsfenster_result['erlaubte_end_zeit']
                
                altersgruppe = "Minderjährige" if ist_minderjaehrig else "Arbeitnehmer"
                
                # Dialog anzeigen: Trotzdem fortfahren?
                self.main_view.show_messagebox(
                    title="Arbeitszeitfenster-Warnung",
                    message=(
                        f"WARNUNG: Stempel außerhalb der gesetzlichen Arbeitszeiten!\n\n"
                        f"Aktueller Stempel: {datum_str} um {uhrzeit_str}\n\n"
                        f"Erlaubte Arbeitszeiten für {altersgruppe}:\n"
                        f"{erlaubte_start.strftime('%H:%M')} - {erlaubte_end.strftime('%H:%M')} Uhr\n\n"
                        f"Möchten Sie trotzdem fortfahren?"
                    ),
                    callback_yes=self._stempel_nach_arbeitsfenster_warnung,  # → STUFE 2
                    callback_no=None,  # Abbruch
                    yes_text="Trotzdem fortfahren",
                    no_text="Abbrechen",
                )
                return  # Warten auf Benutzer-Entscheidung
        except Exception as e:
            logger.error(f"Fehler bei der Arbeitszeitfenster-Prüfung: {e}", exc_info=True)
        
        # === STUFE 2: Ruhezeitenprüfung ===
        # Wenn Arbeitsfenster OK (oder nicht geprüft wegen Fehler): Weiter mit Ruhezeiten
        try:
            ruhezeit_result = self.model_track_time.pruefe_ruhezeit_vor_stempel(
                jetzt.date(), 
                jetzt.time()
            )
            if ruhezeit_result.get('verletzt', False):
                erforderlich = ruhezeit_result['erforderlich_stunden']
                tatsaechlich = ruhezeit_result['tatsaechlich_stunden']
                letzter_datum = ruhezeit_result['letzter_stempel_datum']
                letzter_zeit = ruhezeit_result['letzter_stempel_zeit']
                
                self.main_view.show_messagebox(
                    title="Ruhezeitenverletzung",
                    message=(
                        f"WARNUNG: Gesetzliche Ruhezeit nicht eingehalten!\n\n"
                        f"Letzter Stempel: {letzter_datum.strftime('%d.%m.%Y')} um {letzter_zeit.strftime('%H:%M')}\n"
                        f"Neuer Stempel: {datum_str} um {uhrzeit_str}\n\n"
                        f"Erforderliche Ruhezeit: {erforderlich} Stunden\n"
                        f"Tatsächliche Ruhezeit: {tatsaechlich} Stunden\n\n"
                        f"Möchten Sie trotzdem fortfahren?"
                    ),
                    callback_yes=self._stempel_nach_ruhezeiten_warnung,
                    callback_no=None,
                    yes_text="Trotzdem fortfahren",
                    no_text="Abbrechen",
                )
                return
        except Exception as e:
            logger.error(f"Fehler bei der Ruhezeitenprüfung: {e}", exc_info=True)
        
        # 1) Urlaub prüfen -> spezielles Warn-Popup
        try:
            if self.model_track_time.hat_urlaub_am_datum(_date.today()):
                self.main_view.show_messagebox(
                    title="Urlaubstag-Warnung",
                    message=(
                        f"Heute ({datum_str}) ist als Urlaub eingetragen.\n\n"
                        f"Wenn Sie fortfahren, wird der Urlaubstag gelöscht und der Stempel wird gesetzt."
                    ),
                    callback_yes=self._urlaub_loeschen_und_stempeln,
                    callback_no=None,
                    yes_text="Fortfahren und Urlaub löschen",
                    no_text="Abbrechen",
                )
                return
        except Exception as e:
            logger.error(f"Fehler bei der Prüfung auf Urlaubstag: {e}", exc_info=True)

        # 2) Minderjährige: Prüfung auf 6. Arbeitstag in der Woche
        # WICHTIG: Nur warnen, wenn heute noch KEIN Stempel existiert (erster Stempel des Tages)
        try:
            nutzer = self.model_track_time.get_aktueller_nutzer()
            if nutzer and nutzer.is_minor_on_date(_date.today()):
                # Prüfen ob heute bereits Stempel existieren
                stempel_heute = self.model_track_time.get_stamps_for_today()
                
                # Nur warnen, wenn heute noch KEINE Stempel vorhanden sind
                if not stempel_heute:
                    if self.model_track_time.hat_bereits_5_tage_gearbeitet_in_woche(_date.today()):
                        self.main_view.show_messagebox(
                            title="Arbeitszeitschutz-Warnung",
                            message=(
                                f"ACHTUNG: Sie haben bereits an 5 Tagen in dieser Woche gearbeitet!\n\n"
                                f"Nach dem Arbeitszeitschutzgesetz dürfen Minderjährige maximal 5 Tage pro Woche arbeiten.\n\n"
                                f"Möchten Sie trotzdem fortfahren?"
                            ),
                            callback_yes=self._stempel_nach_6_tage_warnung,
                            callback_no=None,
                            yes_text="Trotzdem fortfahren",
                            no_text="Abbrechen",
                        )
                        return
        except Exception as e:
            logger.error(f"Fehler bei der Prüfung auf 6. Arbeitstag: {e}", exc_info=True)

        # 3) Sonn-/Feiertagswarnung oder normale Bestätigung
        if self.model_track_time.ist_sonn_oder_feiertag(jetzt.date()):
            nachricht = (
                f"ACHTUNG: Sonn-/Feiertag!\n\nDatum: {datum_str}\nUhrzeit: {uhrzeit_str}\n\n"
                f"Möchten Sie diesen Stempel hinzufügen?"
            )
        else:
            nachricht = (
                f"Stempel-Zusammenfassung:\n\nDatum: {datum_str}\nUhrzeit: {uhrzeit_str}\n\nStempel hinzufügen?"
            )
        # Bestätigungs-Popup anzeigen
        self.main_view.show_messagebox(
            title="Stempel bestätigen",
            message=nachricht,
            callback_yes=self._stempel_ausfuehren,
            callback_no=None,
            yes_text="OK",
            no_text="Abbrechen",
        )
    
    def _stempel_nach_ruhezeiten_warnung(self):
        """Führt den Stempel aus, nachdem die Ruhezeitenwarnung akzeptiert wurde."""
        from datetime import datetime, date as _date
        jetzt = datetime.now()
        datum_str = jetzt.strftime("%d.%m.%Y")
        uhrzeit_str = jetzt.strftime("%H:%M:%S")
        
        # Weiter mit Urlaubsprüfung
        try:
            if self.model_track_time.hat_urlaub_am_datum(_date.today()):
                self.main_view.show_messagebox(
                    title="Urlaubstag-Warnung",
                    message=(
                        f"Heute ({datum_str}) ist als Urlaub eingetragen.\n\n"
                        f"Wenn Sie fortfahren, wird der Urlaubstag gelöscht und der Stempel wird gesetzt."
                    ),
                    callback_yes=self._urlaub_loeschen_und_stempeln,
                    callback_no=None,
                    yes_text="Fortfahren und Urlaub löschen",
                    no_text="Abbrechen",
                )
                return
        except Exception as e:
            logger.error(f"Fehler bei der Prüfung auf Urlaubstag: {e}", exc_info=True)
        
        # Weiter mit 6-Tage-Prüfung bei Minderjährigen
        # WICHTIG: Nur warnen, wenn heute noch KEIN Stempel existiert (erster Stempel des Tages)
        try:
            nutzer = self.model_track_time.get_aktueller_nutzer()
            if nutzer and nutzer.is_minor_on_date(_date.today()):
                # Prüfen ob heute bereits Stempel existieren
                stempel_heute = self.model_track_time.get_stamps_for_today()
                
                # Nur warnen, wenn heute noch KEINE Stempel vorhanden sind
                if not stempel_heute:
                    if self.model_track_time.hat_bereits_5_tage_gearbeitet_in_woche(_date.today()):
                        self.main_view.show_messagebox(
                            title="Arbeitszeitschutz-Warnung",
                            message=(
                                f"ACHTUNG: Sie haben bereits an 5 Tagen in dieser Woche gearbeitet!\n\n"
                                f"Nach dem Arbeitszeitschutzgesetz dürfen Minderjährige maximal 5 Tage pro Woche arbeiten.\n\n"
                                f"Möchten Sie trotzdem fortfahren?"
                            ),
                            callback_yes=self._stempel_nach_6_tage_warnung,
                            callback_no=None,
                            yes_text="Trotzdem fortfahren",
                            no_text="Abbrechen",
                        )
                        return
        except Exception as e:
            logger.error(f"Fehler bei der Prüfung auf 6. Arbeitstag: {e}", exc_info=True)
        
        # Weiter mit Sonn-/Feiertagsprüfung
        if self.model_track_time.ist_sonn_oder_feiertag(jetzt.date()):
            nachricht = (
                f"ACHTUNG: Sonn-/Feiertag!\n\nDatum: {datum_str}\nUhrzeit: {uhrzeit_str}\n\n"
                f"Möchten Sie diesen Stempel hinzufügen?"
            )
            self.main_view.show_messagebox(
                title="Stempel bestätigen",
                message=nachricht,
                callback_yes=self._stempel_ausfuehren,
                callback_no=None,
                yes_text="OK",
                no_text="Abbrechen",
            )
        else:
            # Keine weitere Warnung nötig, direkt stempeln
            self._stempel_ausfuehren()
    
    def _stempel_nach_arbeitsfenster_warnung(self):
        """Führt den Stempel aus, nachdem die Arbeitszeitfenster-Warnung akzeptiert wurde."""
        from datetime import datetime, date as _date
        jetzt = datetime.now()
        datum_str = jetzt.strftime("%d.%m.%Y")
        uhrzeit_str = jetzt.strftime("%H:%M:%S")
        
        # Weiter mit Ruhezeitenprüfung
        try:
            ruhezeit_result = self.model_track_time.pruefe_ruhezeit_vor_stempel(
                jetzt.date(), 
                jetzt.time()
            )
            if ruhezeit_result.get('verletzt', False):
                erforderlich = ruhezeit_result['erforderlich_stunden']
                tatsaechlich = ruhezeit_result['tatsaechlich_stunden']
                letzter_datum = ruhezeit_result['letzter_stempel_datum']
                letzter_zeit = ruhezeit_result['letzter_stempel_zeit']
                
                self.main_view.show_messagebox(
                    title="Ruhezeitenverletzung",
                    message=(
                        f"WARNUNG: Gesetzliche Ruhezeit nicht eingehalten!\n\n"
                        f"Letzter Stempel: {letzter_datum.strftime('%d.%m.%Y')} um {letzter_zeit.strftime('%H:%M')}\n"
                        f"Neuer Stempel: {datum_str} um {uhrzeit_str}\n\n"
                        f"Erforderliche Ruhezeit: {erforderlich} Stunden\n"
                        f"Tatsächliche Ruhezeit: {tatsaechlich} Stunden\n\n"
                        f"Möchten Sie trotzdem fortfahren?"
                    ),
                    callback_yes=self._stempel_nach_ruhezeiten_warnung,
                    callback_no=None,
                    yes_text="Trotzdem fortfahren",
                    no_text="Abbrechen",
                )
                return
        except Exception as e:
            logger.error(f"Fehler bei der Ruhezeitenprüfung: {e}", exc_info=True)
        
        # Weiter mit Urlaubsprüfung
        try:
            if self.model_track_time.hat_urlaub_am_datum(_date.today()):
                self.main_view.show_messagebox(
                    title="Urlaubstag-Warnung",
                    message=(
                        f"Heute ({datum_str}) ist als Urlaub eingetragen.\n\n"
                        f"Wenn Sie fortfahren, wird der Urlaubstag gelöscht und der Stempel wird gesetzt."
                    ),
                    callback_yes=self._urlaub_loeschen_und_stempeln,
                    callback_no=None,
                    yes_text="Fortfahren und Urlaub löschen",
                    no_text="Abbrechen",
                )
                return
        except Exception as e:
            logger.error(f"Fehler bei der Prüfung auf Urlaubstag: {e}", exc_info=True)
        
        # Weiter mit 6-Tage-Prüfung bei Minderjährigen
        # WICHTIG: Nur warnen, wenn heute noch KEIN Stempel existiert (erster Stempel des Tages)
        try:
            nutzer = self.model_track_time.get_aktueller_nutzer()
            if nutzer and nutzer.is_minor_on_date(_date.today()):
                # Prüfen ob heute bereits Stempel existieren
                stempel_heute = self.model_track_time.get_stamps_for_today()
                
                # Nur warnen, wenn heute noch KEINE Stempel vorhanden sind
                if not stempel_heute:
                    if self.model_track_time.hat_bereits_5_tage_gearbeitet_in_woche(_date.today()):
                        self.main_view.show_messagebox(
                            title="Arbeitszeitschutz-Warnung",
                            message=(
                                f"ACHTUNG: Sie haben bereits an 5 Tagen in dieser Woche gearbeitet!\n\n"
                                f"Nach dem Arbeitszeitschutzgesetz dürfen Minderjährige maximal 5 Tage pro Woche arbeiten.\n\n"
                                f"Möchten Sie trotzdem fortfahren?"
                            ),
                            callback_yes=self._stempel_nach_6_tage_warnung,
                            callback_no=None,
                            yes_text="Trotzdem fortfahren",
                            no_text="Abbrechen",
                        )
                        return
        except Exception as e:
            logger.error(f"Fehler bei der Prüfung auf 6. Arbeitstag: {e}", exc_info=True)
        
        # Weiter mit Sonn-/Feiertagsprüfung
        if self.model_track_time.ist_sonn_oder_feiertag(jetzt.date()):
            nachricht = (
                f"ACHTUNG: Sonn-/Feiertag!\n\nDatum: {datum_str}\nUhrzeit: {uhrzeit_str}\n\n"
                f"Möchten Sie diesen Stempel hinzufügen?"
            )
            self.main_view.show_messagebox(
                title="Stempel bestätigen",
                message=nachricht,
                callback_yes=self._stempel_ausfuehren,
                callback_no=None,
                yes_text="OK",
                no_text="Abbrechen",
            )
        else:
            # Keine weitere Warnung nötig, direkt stempeln
            self._stempel_ausfuehren()
    
    def _urlaub_loeschen_und_stempeln(self):
        """Löscht Urlaubseintrag von heute und setzt anschließend den Stempel."""
        from datetime import date as _date
        try:
            geloescht = self.model_track_time.loesche_urlaub_am_datum(_date.today())
            if geloescht:
                # Urlaubstage im Kalender neu laden
                self.model_track_time.aktuelle_kalendereinträge_für_id = self.model_track_time.aktueller_nutzer_id
                self.load_vacation_days_for_calendar()
                logger.info("Urlaubstag gelöscht – fahre mit Stempel fort.")
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Urlaubstags: {e}", exc_info=True)
        # Danach normal stempeln
        self._stempel_ausfuehren()

    def _stempel_nach_6_tage_warnung(self):
        """Führt den Stempel aus, nachdem die 6-Tage-Warnung akzeptiert wurde."""
        from datetime import datetime, date as _date
        jetzt = datetime.now()

        # Jetzt noch die Sonn-/Feiertagsprüfung durchführen
        if self.model_track_time.ist_sonn_oder_feiertag(jetzt.date()):
            datum_str = jetzt.strftime("%d.%m.%Y")
            uhrzeit_str = jetzt.strftime("%H:%M:%S")
            nachricht = (
                f"ACHTUNG: Sonn-/Feiertag!\n\nDatum: {datum_str}\nUhrzeit: {uhrzeit_str}\n\n"
                f"Möchten Sie diesen Stempel hinzufügen?"
            )
            self.main_view.show_messagebox(
                title="Stempel bestätigen",
                message=nachricht,
                callback_yes=self._stempel_ausfuehren,
                callback_no=None,
                yes_text="OK",
                no_text="Abbrechen",
            )
        else:
            # Keine weitere Warnung nötig, direkt stempeln
            self._stempel_ausfuehren()

    def _stempel_ausfuehren(self):
        """Führt den eigentlichen Stempelvorgang aus."""
        self.model_track_time.stempel_hinzufügen()
        # Nach dem Stempeln: Gleitzeit (bis gestern) neu berechnen, Ampel und Kumulierung aktualisieren
        try:
            self.model_track_time.berechne_gleitzeit()
            self.model_track_time.set_ampel_farbe()
            self.model_track_time.kummuliere_gleitzeit()
        finally:
            # Timer-UI aktualisieren (für laufende Zeit ab letztem Stempel)
            self.start_or_stop_visual_timer()
            # View-Werte (Gleitzeit/Ampel/Kumulierung) aktualisieren
            self.update_view_time_tracking()
    
    def nachtragen_button_clicked(self,b):
        self.update_model_time_tracking()
        art = self.main_view.eintrag_art_spinner.text
        
        if art == "Zeitstempel":
            # Prüfen, ob Datum gesetzt ist
            if self.model_track_time.nachtragen_datum:
                # 0a) Arbeitszeitfenster-Prüfung
                try:
                    from datetime import datetime as _dt
                    nachtrage_datum_obj = _dt.strptime(self.model_track_time.nachtragen_datum, "%d/%m/%Y").date()
                    nachtrage_zeit_obj = _dt.strptime(self.model_track_time.manueller_stempel_uhrzeit, "%H:%M").time()
                    
                    arbeitsfenster_result = self.model_track_time.pruefe_arbeitszeit_fenster(
                        nachtrage_datum_obj,
                        nachtrage_zeit_obj
                    )
                    
                    if arbeitsfenster_result.get('verletzt', False):
                        ist_minderjaehrig = arbeitsfenster_result['ist_minderjaehrig']
                        erlaubte_start = arbeitsfenster_result['erlaubte_start_zeit']
                        erlaubte_end = arbeitsfenster_result['erlaubte_end_zeit']
                        
                        altersgruppe = "Minderjährige" if ist_minderjaehrig else "Arbeitnehmer"
                        
                        self.main_view.show_messagebox(
                            title="Arbeitszeitfenster-Warnung",
                            message=(
                                f"WARNUNG: Stempel außerhalb der gesetzlichen Arbeitszeiten!\n\n"
                                f"Nachzutragender Stempel: {self.model_track_time.nachtragen_datum} um {self.model_track_time.manueller_stempel_uhrzeit}\n\n"
                                f"Erlaubte Arbeitszeiten für {altersgruppe}:\n"
                                f"{erlaubte_start.strftime('%H:%M')} - {erlaubte_end.strftime('%H:%M')} Uhr\n\n"
                                f"Möchten Sie trotzdem fortfahren?"
                            ),
                            callback_yes=self._nachtragen_nach_arbeitsfenster_warnung,
                            callback_no=None,
                            yes_text="Trotzdem fortfahren",
                            no_text="Abbrechen",
                        )
                        return
                except ValueError as ve:
                    logger.error(f"Fehler beim Parsen von Datum/Zeit für Arbeitszeitfenster-Prüfung: {ve}", exc_info=True)
                    self.model_track_time.feedback_manueller_stempel = "Ungültiges Datums- oder Zeitformat."
                    self.update_view_time_tracking()
                    return
                except Exception as e:
                    logger.error(f"Fehler bei der Arbeitszeitfenster-Prüfung (Nachtragen): {e}", exc_info=True)
                
                # 0b) Ruhezeitenprüfung
                try:
                    from datetime import datetime as _dt
                    nachtrage_datum_obj = _dt.strptime(self.model_track_time.nachtragen_datum, "%d/%m/%Y").date()
                    nachtrage_zeit_obj = _dt.strptime(self.model_track_time.manueller_stempel_uhrzeit, "%H:%M").time()
                    
                    ruhezeit_result = self.model_track_time.pruefe_ruhezeit_vor_stempel(
                        nachtrage_datum_obj,
                        nachtrage_zeit_obj
                    )
                    
                    if ruhezeit_result.get('verletzt', False):
                        erforderlich = ruhezeit_result['erforderlich_stunden']
                        tatsaechlich = ruhezeit_result['tatsaechlich_stunden']
                        letzter_datum = ruhezeit_result['letzter_stempel_datum']
                        letzter_zeit = ruhezeit_result['letzter_stempel_zeit']
                        
                        self.main_view.show_messagebox(
                            title="Ruhezeitenverletzung",
                            message=(
                                f"WARNUNG: Gesetzliche Ruhezeit nicht eingehalten!\n\n"
                                f"Letzter Stempel: {letzter_datum.strftime('%d.%m.%Y')} um {letzter_zeit.strftime('%H:%M')}\n"
                                f"Nachzutragender Stempel: {self.model_track_time.nachtragen_datum} um {self.model_track_time.manueller_stempel_uhrzeit}\n\n"
                                f"Erforderliche Ruhezeit: {erforderlich} Stunden\n"
                                f"Tatsächliche Ruhezeit: {tatsaechlich} Stunden\n\n"
                                f"Möchten Sie trotzdem fortfahren?"
                            ),
                            callback_yes=self._nachtragen_nach_ruhezeiten_warnung,
                            callback_no=None,
                            yes_text="Trotzdem fortfahren",
                            no_text="Abbrechen",
                        )
                        return
                except ValueError as ve:
                    logger.error(f"Fehler beim Parsen von Datum/Zeit für Ruhezeitenprüfung: {ve}", exc_info=True)
                    self.model_track_time.feedback_manueller_stempel = "Ungültiges Datums- oder Zeitformat."
                    self.update_view_time_tracking()
                    return
                except Exception as e:
                    logger.error(f"Fehler bei der Ruhezeitenprüfung (Nachtragen): {e}", exc_info=True)
                
                # 1) Erst Urlaub prüfen
                try:
                    from datetime import datetime as _dt
                    nachtrage_datum_obj = _dt.strptime(self.model_track_time.nachtragen_datum, "%d/%m/%Y").date()
                    if self.model_track_time.hat_urlaub_am_datum(nachtrage_datum_obj):
                        self.main_view.show_messagebox(
                            title="Urlaubstag-Warnung",
                            message=(
                                f"Am ausgewählten Tag ({self.model_track_time.nachtragen_datum}) ist Urlaub eingetragen.\n\n"
                                f"Wenn Sie fortfahren, wird der Urlaubstag gelöscht und der Zeitstempel wird nachgetragen."
                            ),
                            callback_yes=self._urlaub_loeschen_und_nachtragen_zeitstempel,
                            callback_no=None,
                            yes_text="Fortfahren und Urlaub löschen",
                            no_text="Abbrechen",
                        )
                        return
                except Exception as e:
                    logger.error(f"Fehler bei der Urlaubstagsprüfung (Nachtragen): {e}", exc_info=True)

                # Dann Minderjährige: Prüfung auf 6. Arbeitstag
                # WICHTIG: Nur warnen, wenn am Nachtrag-Datum noch KEIN Stempel existiert
                try:
                    from datetime import datetime as _dt
                    nachtrage_datum_obj = _dt.strptime(self.model_track_time.nachtragen_datum, "%d/%m/%Y").date()
                    nutzer = self.model_track_time.get_aktueller_nutzer()
                    if nutzer and nutzer.is_minor_on_date(nachtrage_datum_obj):
                        # Prüfen ob am Nachtrag-Datum bereits Stempel existieren
                        stempel_am_datum = self.model_track_time.get_stamps_for_date(nachtrage_datum_obj)
                        
                        # Nur warnen, wenn am Nachtrag-Datum noch KEINE Stempel vorhanden sind
                        if not stempel_am_datum:
                            if self.model_track_time.hat_bereits_5_tage_gearbeitet_in_woche(nachtrage_datum_obj):
                                self.main_view.show_messagebox(
                                    title="Arbeitszeitschutz-Warnung",
                                    message=(
                                        f"ACHTUNG: Es wurden bereits an 5 Tagen in der Woche vom {self.model_track_time.nachtragen_datum} gearbeitet!\n\n"
                                        f"Nach dem Arbeitszeitschutzgesetz dürfen Minderjährige maximal 5 Tage pro Woche arbeiten.\n\n"
                                        f"Möchten Sie trotzdem fortfahren?"
                                    ),
                                    callback_yes=self._nachtragen_nach_6_tage_warnung,
                                    callback_no=None,
                                    yes_text="Trotzdem fortfahren",
                                    no_text="Abbrechen",
                                )
                                return
                except Exception as e:
                    logger.error(f"Fehler bei der 6-Tage-Prüfung (Nachtragen): {e}", exc_info=True)

                # Danach Sonn-/Feiertag prüfen
                if self.model_track_time.ist_sonn_oder_feiertag(self.model_track_time.nachtragen_datum):
                    self.main_view.show_messagebox(
                        title="Sonn-/Feiertagswarnung",
                        message=(
                            f"Sie versuchen an einem Sonntag oder Feiertag ({self.model_track_time.nachtragen_datum}) einen Zeitstempel nachzutragen.\n\nMöchten Sie fortfahren?"
                        ),
                        callback_yes=self._nachtragen_zeitstempel_ausfuehren,
                        callback_no=None,
                        yes_text="Fortfahren",
                        no_text="Abbrechen",
                    )
                else:
                    # Direkt nachtragen wenn kein besonderer Tag
                    self._nachtragen_zeitstempel_ausfuehren()
            else:
                self.model_track_time.feedback_manueller_stempel = "Bitte ein Datum auswählen."
                self.update_view_time_tracking()
        elif art == "Urlaub" or art == "Krankheit":
            # Prüfen ob Stempel vorhanden sind
            result = self.model_track_time.urlaub_eintragen()
            
            # Wenn Stempel vorhanden sind, Warnung anzeigen
            if isinstance(result, dict) and result.get("stempel_vorhanden"):
                anzahl = result.get("anzahl_stempel", 0)
                try:
                    from datetime import datetime as _dt
                    nachtrage_datum_obj = _dt.strptime(self.model_track_time.nachtragen_datum, "%d/%m/%Y").date()
                    self.main_view.show_messagebox(
                        title="Stempel vorhanden",
                        message=(
                            f"Am ausgewählten Tag ({self.model_track_time.nachtragen_datum}) "
                            f"{'ist bereits ein Zeitstempel' if anzahl == 1 else f'sind bereits {anzahl} Zeitstempel'} vorhanden.\n\n"
                            f"Wenn Sie fortfahren, {'wird der Stempel gelöscht' if anzahl == 1 else 'werden die Stempel gelöscht'} "
                            f"und die Gleitzeit wird rückgängig gemacht."
                        ),
                        callback_yes=lambda: self._stempel_loeschen_und_urlaub_eintragen(nachtrage_datum_obj),
                        callback_no=None,
                        yes_text="Fortfahren und Stempel löschen",
                        no_text="Abbrechen",
                    )
                    return
                except Exception as e:
                    logger.error(f"Fehler bei der Stempel-Prüfung (Urlaub eintragen): {e}", exc_info=True)
            
            # Wenn keine Stempel vorhanden oder nach Löschung: Normal fortfahren
            # Nach dem Eintragen von Urlaub/Krankheit die Abwesenheitstage neu laden
            self.load_vacation_days_for_calendar()
            # Nach jedem Nachtrag neu berechnen
            try:
                self.model_track_time.berechne_gleitzeit()
                self.model_track_time.set_ampel_farbe()
                self.model_track_time.kummuliere_gleitzeit()
            finally:
                self.update_view_time_tracking()
        else:
            self.model_track_time.feedback_manueller_stempel = "Bitte eine Eintragsart wählen."
            self.update_view_time_tracking()
    
    def _nachtragen_zeitstempel_ausfuehren(self):
        """Führt das eigentliche Nachtragen eines Zeitstempels aus."""
        from datetime import datetime as _dt, date as _date
        
        # Prüfen, ob der nachgetragene Stempel für heute ist
        ist_heute = False
        try:
            if self.model_track_time.nachtragen_datum:
                nachtrage_datum_obj = _dt.strptime(self.model_track_time.nachtragen_datum, "%d/%m/%Y").date()
                ist_heute = (nachtrage_datum_obj == _date.today())
        except (ValueError, TypeError) as e:
            logger.error(f"Fehler beim Parsen des Nachtragsdatums: {e}", exc_info=True)
        
        self.model_track_time.manueller_stempel_hinzufügen()
        # Nach jedem Nachtrag neu berechnen (z.B. wenn vergangene Tage betroffen sind)
        try:
            self.model_track_time.berechne_gleitzeit()
            self.model_track_time.set_ampel_farbe()
            self.model_track_time.kummuliere_gleitzeit()
        finally:
            self.update_view_time_tracking() # Feedback + aktualisierte Werte anzeigen
        
        # Wenn Stempel für heute nachgetragen wurde, Timer aktualisieren
        if ist_heute:
            self.start_or_stop_visual_timer()
            logger.info("Timer aktualisiert nach Nachtrag für heute")
        
        # PopUp-Warnungen nach einem Nachtrag immer aktualisieren
        self._refresh_popup_warnings()

    def _nachtragen_nach_6_tage_warnung(self):
        """Führt das Nachtragen aus, nachdem die 6-Tage-Warnung akzeptiert wurde."""
        # Jetzt noch die Sonn-/Feiertagsprüfung durchführen
        if self.model_track_time.ist_sonn_oder_feiertag(self.model_track_time.nachtragen_datum):
            self.main_view.show_messagebox(
                title="Sonn-/Feiertagswarnung",
                message=(
                    f"Sie versuchen an einem Sonntag oder Feiertag ({self.model_track_time.nachtragen_datum}) einen Zeitstempel nachzutragen.\n\nMöchten Sie fortfahren?"
                ),
                callback_yes=self._nachtragen_zeitstempel_ausfuehren,
                callback_no=None,
                yes_text="Fortfahren",
                no_text="Abbrechen",
            )
        else:
            # Keine weitere Warnung nötig, direkt nachtragen
            self._nachtragen_zeitstempel_ausfuehren()

    def _nachtragen_nach_ruhezeiten_warnung(self):
        """Führt das Nachtragen aus, nachdem die Ruhezeitenwarnung akzeptiert wurde."""
        from datetime import datetime as _dt
        
        # Weiter mit Urlaubsprüfung
        try:
            nachtrage_datum_obj = _dt.strptime(self.model_track_time.nachtragen_datum, "%d/%m/%Y").date()
            if self.model_track_time.hat_urlaub_am_datum(nachtrage_datum_obj):
                self.main_view.show_messagebox(
                    title="Urlaubstag-Warnung",
                    message=(
                        f"Am ausgewählten Tag ({self.model_track_time.nachtragen_datum}) ist Urlaub eingetragen.\n\n"
                        f"Wenn Sie fortfahren, wird der Urlaubstag gelöscht und der Zeitstempel wird nachgetragen."
                    ),
                    callback_yes=self._urlaub_loeschen_und_nachtragen_zeitstempel,
                    callback_no=None,
                    yes_text="Fortfahren und Urlaub löschen",
                    no_text="Abbrechen",
                )
                return
        except Exception as e:
            logger.error(f"Fehler bei der Urlaubstagsprüfung (Nachtragen nach Ruhezeiten): {e}", exc_info=True)
        
        # Weiter mit 6-Tage-Prüfung bei Minderjährigen
        # WICHTIG: Nur warnen, wenn am Nachtrag-Datum noch KEIN Stempel existiert
        try:
            nachtrage_datum_obj = _dt.strptime(self.model_track_time.nachtragen_datum, "%d/%m/%Y").date()
            nutzer = self.model_track_time.get_aktueller_nutzer()
            if nutzer and nutzer.is_minor_on_date(nachtrage_datum_obj):
                # Prüfen ob am Nachtrag-Datum bereits Stempel existieren
                stempel_am_datum = self.model_track_time.get_stamps_for_date(nachtrage_datum_obj)
                
                # Nur warnen, wenn am Nachtrag-Datum noch KEINE Stempel vorhanden sind
                if not stempel_am_datum:
                    if self.model_track_time.hat_bereits_5_tage_gearbeitet_in_woche(nachtrage_datum_obj):
                        self.main_view.show_messagebox(
                            title="Arbeitszeitschutz-Warnung",
                            message=(
                                f"ACHTUNG: Es wurden bereits an 5 Tagen in der Woche vom {self.model_track_time.nachtragen_datum} gearbeitet!\n\n"
                                f"Nach dem Arbeitszeitschutzgesetz dürfen Minderjährige maximal 5 Tage pro Woche arbeiten.\n\n"
                                f"Möchten Sie trotzdem fortfahren?"
                            ),
                            callback_yes=self._nachtragen_nach_6_tage_warnung,
                            callback_no=None,
                            yes_text="Trotzdem fortfahren",
                            no_text="Abbrechen",
                        )
                        return
        except Exception as e:
            logger.error(f"Fehler bei der 6-Tage-Prüfung (Nachtragen nach Ruhezeiten): {e}", exc_info=True)
        
        # Weiter mit Sonn-/Feiertagsprüfung
        if self.model_track_time.ist_sonn_oder_feiertag(self.model_track_time.nachtragen_datum):
            self.main_view.show_messagebox(
                title="Sonn-/Feiertagswarnung",
                message=(
                    f"Sie versuchen an einem Sonntag oder Feiertag ({self.model_track_time.nachtragen_datum}) einen Zeitstempel nachzutragen.\n\nMöchten Sie fortfahren?"
                ),
                callback_yes=self._nachtragen_zeitstempel_ausfuehren,
                callback_no=None,
                yes_text="Fortfahren",
                no_text="Abbrechen",
            )
        else:
            # Keine weitere Warnung nötig, direkt nachtragen
            self._nachtragen_zeitstempel_ausfuehren()

    def _nachtragen_nach_arbeitsfenster_warnung(self):
        """Führt das Nachtragen aus, nachdem die Arbeitszeitfenster-Warnung akzeptiert wurde."""
        from datetime import datetime as _dt
        
        # Weiter mit Ruhezeitenprüfung
        try:
            nachtrage_datum_obj = _dt.strptime(self.model_track_time.nachtragen_datum, "%d/%m/%Y").date()
            nachtrage_zeit_obj = _dt.strptime(self.model_track_time.manueller_stempel_uhrzeit, "%H:%M").time()
            
            ruhezeit_result = self.model_track_time.pruefe_ruhezeit_vor_stempel(
                nachtrage_datum_obj,
                nachtrage_zeit_obj
            )
            
            if ruhezeit_result.get('verletzt', False):
                erforderlich = ruhezeit_result['erforderlich_stunden']
                tatsaechlich = ruhezeit_result['tatsaechlich_stunden']
                letzter_datum = ruhezeit_result['letzter_stempel_datum']
                letzter_zeit = ruhezeit_result['letzter_stempel_zeit']
                
                self.main_view.show_messagebox(
                    title="Ruhezeitenverletzung",
                    message=(
                        f"WARNUNG: Gesetzliche Ruhezeit nicht eingehalten!\n\n"
                        f"Letzter Stempel: {letzter_datum.strftime('%d.%m.%Y')} um {letzter_zeit.strftime('%H:%M')}\n"
                        f"Nachzutragender Stempel: {self.model_track_time.nachtragen_datum} um {self.model_track_time.manueller_stempel_uhrzeit}\n\n"
                        f"Erforderliche Ruhezeit: {erforderlich} Stunden\n"
                        f"Tatsächliche Ruhezeit: {tatsaechlich} Stunden\n\n"
                        f"Möchten Sie trotzdem fortfahren?"
                    ),
                    callback_yes=self._nachtragen_nach_ruhezeiten_warnung,
                    callback_no=None,
                    yes_text="Trotzdem fortfahren",
                    no_text="Abbrechen",
                )
                return
        except Exception as e:
            logger.error(f"Fehler bei der Ruhezeitenprüfung (Nachtragen nach Arbeitsfenster): {e}", exc_info=True)
        
        # Weiter mit Urlaubsprüfung
        try:
            nachtrage_datum_obj = _dt.strptime(self.model_track_time.nachtragen_datum, "%d/%m/%Y").date()
            if self.model_track_time.hat_urlaub_am_datum(nachtrage_datum_obj):
                self.main_view.show_messagebox(
                    title="Urlaubstag-Warnung",
                    message=(
                        f"Am ausgewählten Tag ({self.model_track_time.nachtragen_datum}) ist Urlaub eingetragen.\n\n"
                        f"Wenn Sie fortfahren, wird der Urlaubstag gelöscht und der Zeitstempel wird nachgetragen."
                    ),
                    callback_yes=self._urlaub_loeschen_und_nachtragen_zeitstempel,
                    callback_no=None,
                    yes_text="Fortfahren und Urlaub löschen",
                    no_text="Abbrechen",
                )
                return
        except Exception as e:
            logger.error(f"Fehler bei der Urlaubstagsprüfung (Nachtragen nach Arbeitsfenster): {e}", exc_info=True)
        
        # Weiter mit 6-Tage-Prüfung bei Minderjährigen
        # WICHTIG: Nur warnen, wenn am Nachtrag-Datum noch KEIN Stempel existiert
        try:
            nachtrage_datum_obj = _dt.strptime(self.model_track_time.nachtragen_datum, "%d/%m/%Y").date()
            nutzer = self.model_track_time.get_aktueller_nutzer()
            if nutzer and nutzer.is_minor_on_date(nachtrage_datum_obj):
                # Prüfen ob am Nachtrag-Datum bereits Stempel existieren
                stempel_am_datum = self.model_track_time.get_stamps_for_date(nachtrage_datum_obj)
                
                # Nur warnen, wenn am Nachtrag-Datum noch KEINE Stempel vorhanden sind
                if not stempel_am_datum:
                    if self.model_track_time.hat_bereits_5_tage_gearbeitet_in_woche(nachtrage_datum_obj):
                        self.main_view.show_messagebox(
                            title="Arbeitszeitschutz-Warnung",
                            message=(
                                f"ACHTUNG: Es wurden bereits an 5 Tagen in der Woche vom {self.model_track_time.nachtragen_datum} gearbeitet!\n\n"
                                f"Nach dem Arbeitszeitschutzgesetz dürfen Minderjährige maximal 5 Tage pro Woche arbeiten.\n\n"
                                f"Möchten Sie trotzdem fortfahren?"
                            ),
                            callback_yes=self._nachtragen_nach_6_tage_warnung,
                            callback_no=None,
                            yes_text="Trotzdem fortfahren",
                            no_text="Abbrechen",
                        )
                        return
        except Exception as e:
            logger.error(f"Fehler bei der 6-Tage-Prüfung (Nachtragen nach Arbeitsfenster): {e}", exc_info=True)
        
        # Weiter mit Sonn-/Feiertagsprüfung
        if self.model_track_time.ist_sonn_oder_feiertag(self.model_track_time.nachtragen_datum):
            self.main_view.show_messagebox(
                title="Sonn-/Feiertagswarnung",
                message=(
                    f"Sie versuchen an einem Sonntag oder Feiertag ({self.model_track_time.nachtragen_datum}) einen Zeitstempel nachzutragen.\n\nMöchten Sie fortfahren?"
                ),
                callback_yes=self._nachtragen_zeitstempel_ausfuehren,
                callback_no=None,
                yes_text="Fortfahren",
                no_text="Abbrechen",
            )
        else:
            # Keine weitere Warnung nötig, direkt nachtragen
            self._nachtragen_zeitstempel_ausfuehren()

    def _urlaub_loeschen_und_nachtragen_zeitstempel(self):
        """Löscht Urlaub am ausgewählten Nachtrags-Datum und trägt dann den Zeitstempel nach."""
        from datetime import datetime as _dt
        try:
            if not self.model_track_time.nachtragen_datum:
                self.model_track_time.feedback_manueller_stempel = "Bitte ein Datum auswählen."
                self.update_view_time_tracking()
                return
            datum_obj = _dt.strptime(self.model_track_time.nachtragen_datum, "%d/%m/%Y").date()
            geloescht = self.model_track_time.loesche_urlaub_am_datum(datum_obj)
            if geloescht:
                # Urlaubstage im Kalender neu laden
                self.model_track_time.aktuelle_kalendereinträge_für_id = self.model_track_time.aktueller_nutzer_id
                self.load_vacation_days_for_calendar()
                logger.info(f"Urlaubstag {self.model_track_time.nachtragen_datum} gelöscht – trage Zeitstempel nach.")
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Urlaubstags (Nachtragen): {e}", exc_info=True)
        # Danach den normalen Nachtragsfluss starten
        self._nachtragen_zeitstempel_ausfuehren()

    def _stempel_loeschen_und_urlaub_eintragen(self, datum_obj):
        """Löscht alle Stempel am ausgewählten Datum und trägt dann Urlaub/Krankheit ein."""
        try:
            erfolg = self.model_track_time.loesche_alle_stempel_am_datum(datum_obj)
            if erfolg:
                logger.info(f"Alle Stempel am {datum_obj} gelöscht – trage Abwesenheit ein.")
                # Jetzt erneut urlaub_eintragen aufrufen (diesmal ohne Stempel)
                self.model_track_time.urlaub_eintragen()
                # Abwesenheitstage im Kalender neu laden
                self.load_vacation_days_for_calendar()
                # Gleitzeit neu berechnen
                try:
                    self.model_track_time.berechne_gleitzeit()
                    self.model_track_time.set_ampel_farbe()
                    self.model_track_time.kummuliere_gleitzeit()
                finally:
                    self.update_view_time_tracking()
            else:
                logger.error(f"Fehler beim Löschen der Stempel am {datum_obj}")
                self.model_track_time.feedback_manueller_stempel = "Fehler beim Löschen der Stempel."
                self.update_view_time_tracking()
        except Exception as e:
            logger.error(f"Fehler beim Löschen der Stempel (Urlaub eintragen): {e}", exc_info=True)
            self.model_track_time.feedback_manueller_stempel = f"Fehler: {e}"
            self.update_view_time_tracking()

    def passwort_ändern_button_clicked(self, b):
        """
        Handler für Passwort-Ändern-Button.
        
        Führt die Passwort-Änderung durch mit Validierung und bcrypt-Hashing.
        
        Args:
            b: Kivy Button-Instanz (wird nicht verwendet)
        """
        self.update_model_time_tracking()
        self.model_track_time.update_passwort()
        self.update_view_time_tracking()
    
    # === Kalender-Navigation und -Verwaltung ===
    
    def prev_button_clicked(self, b):
        """
        Handler für vorheriger Monat-Button.
        
        Navigiert im Kalender einen Monat zurück und lädt Abwesenheiten.
        
        Args:
            b: Kivy Button-Instanz (wird nicht verwendet)
        """
        self.main_view.month_calendar.change_month(-1)
        self.load_vacation_days_for_calendar()
    
    def next_button_clicked(self, b):
        """
        Handler für nächster Monat-Button.
        
        Navigiert im Kalender einen Monat vorwärts und lädt Abwesenheiten.
        
        Args:
            b: Kivy Button-Instanz (wird nicht verwendet)
        """
        self.main_view.month_calendar.change_month(1)
        self.load_vacation_days_for_calendar()
    
    def load_vacation_days_for_calendar(self):
        """
        Lädt Abwesenheiten für den aktuell angezeigten Kalendermonat.
        
        Holt Urlaubs- und Krankheitstage aus dem Modell und aktualisiert
        die Kalender-Ansicht entsprechend.
        
        Note:
            Wird automatisch beim Monatswechsel und nach Login aufgerufen.
        """
        jahr = self.main_view.month_calendar.year
        monat = self.main_view.month_calendar.month
        urlaubstage = self.model_track_time.get_urlaubstage_monat(jahr, monat)
        krankheitstage = self.model_track_time.get_krankheitstage_monat(jahr, monat)
        self.main_view.month_calendar.urlaubstage = urlaubstage
        self.main_view.month_calendar.krankheitstage = krankheitstage
        self.main_view.month_calendar.fill_grid_with_days()
    
    # === View-Wechsel-Methoden ===
    
    def change_view_register(self, b):
        """
        Wechselt zur Registrierungs-Ansicht.
        
        Args:
            b: Kivy Button-Instanz (wird nicht verwendet)
        """
        set_fixed_window_size((self.register_view.width_window, self.register_view.height_window))
        self.sm.current = "register"
    
    def change_view_login(self, b):
        """
        Wechselt zur Login-Ansicht.
        
        Args:
            b: Kivy Button-Instanz (wird nicht verwendet)
        """
        set_fixed_window_size((self.login_view.width_window, self.login_view.height_window))
        self.sm.current = "login"
    
    def change_view_main(self, b):
        """
        Wechselt zur Hauptanwendungs-Ansicht.
        
        Args:
            b: Kivy Button-Instanz (wird nicht verwendet)
        """
        set_fixed_window_size((self.main_view.time_tracking_tab_width, self.main_view.time_tracking_tab_height))
        self.sm.current = "main"
    
    # === Datum/Zeit-Picker-Handler ===
    
    def show_date_picker(self, instance, focus):
        """
        Öffnet den Datums-Picker bei Fokus auf Datumsfeld.
        
        Args:
            instance: Das Text-Input-Widget
            focus (bool): Ob das Widget Fokus hat
            
        Note:
            Wird für Registrierungs- und Nachtrage-Datumsfelder verwendet.
        """
        if focus:
            try:
                if instance == self.register_view.reg_geburtsdatum:
                    self.register_view.date_picker.open()
                elif instance == self.main_view.date_input:
                    self.main_view.date_picker.open()
            except Exception as e:
                logger.error(f"Fehler beim Öffnen des DatePickers: {e}", exc_info=True)
            instance.focus = False
    
    # === Timer-Logik und PopUp-Warnungen ===
    
    def start_or_stop_visual_timer(self):
        """
        Startet oder stoppt den visuellen Timer basierend auf Stempel-Status.
        
        Zweck: Zeigt Arbeitszeit seit letztem Einstempeln in Echtzeit an
        
        Logik-Ablauf:
            1. Anzahl Stempel heute abrufen
            2. Wenn ungerade Anzahl (= eingestempelt):
               → Timer STARTEN:
                 a) Letzten Stempel (Einstempel-Zeit) finden
                 b) start_time_dt = datetime(heute, einstempel_uhrzeit)
                 c) Clock.schedule_interval(update_visual_timer, 60) → Update alle 60s
                 d) Timer-Text grün färben
                 e) PopUp-Warnungen in DB erstellen (Code 10, 11)
                 f) PopUp-Warnungen für heute laden und schedulen
            
            3. Wenn gerade Anzahl (= ausgestempelt):
               → Timer STOPPEN:
                 a) Clock-Event abbrechen (timer_event.cancel())
                 b) Timer auf "00:00" setzen
                 c) Timer-Text rot färben (implizit durch View)
                 d) ALLE PopUp-Benachrichtigungen für heute löschen (Code 10, 11)
        
        PopUp-Warnungen (Code 10, 11):
            Code 10: "Ihr erlaubtes Arbeitsfenster endet bald."
                     → 30min vor 22:00 (Erwachsene) bzw. 20:00 (Minderjährige)
            Code 11: "Sie erreichen bald die maximale tägliche Arbeitszeit."
                     → 9h 30min nach Einstempeln (30min vor 10h-Grenze)
        
        Note:
            Diese Methode wird aufgerufen:
            - Nach Login (wenn bereits eingestempelt)
            - Nach jedem Stempeln (Ein- oder Ausstempeln)
            - Nach manuellem Nachtragen von Stempeln für heute
        """
        # === Schritt 0: Alle bestehenden Timer-Events abbrechen ===
        # Verhindert mehrfache gleichzeitige Timer
        if self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None
        if self.arbeitsfenster_warning_event:
            self.arbeitsfenster_warning_event.cancel()
            self.arbeitsfenster_warning_event = None
        if self.max_arbeitszeit_warning_event:
            self.max_arbeitszeit_warning_event.cancel()
            self.max_arbeitszeit_warning_event = None
        
        # === Schritt 1: Stempel-Status ermitteln ===
        today_stamps = self.model_track_time.get_stamps_for_today()
        is_clocked_in = len(today_stamps) % 2 != 0  # Ungerade = eingestempelt
        
        if is_clocked_in:
            # === Eingestempelt: Timer STARTEN ===
            try:
                # Schritt 2a: Letzten Stempel (Einstempel-Zeit) finden
                last_stamp_time = today_stamps[-1].zeit  # Letzter Stempel = aktuellster Einstempel
                
                # Schritt 2b: Start-Zeitpunkt als datetime-Objekt speichern
                self.start_time_dt = datetime.combine(date.today(), last_stamp_time)
                
                # Schritt 2c: Timer schedulen (Update alle 60 Sekunden)
                self.timer_event = Clock.schedule_interval(self.update_visual_timer, 60)
                
                # Einmal sofort updaten (nicht auf 60s warten)
                self.update_visual_timer(0)
                
                # Schritt 2e: PopUp-Warnungen in DB erstellen (falls noch nicht vorhanden)
                # Erstellt Code 10 (Arbeitsfenster-Ende) und Code 11 (Max. Arbeitszeit)
                self.model_track_time.erstelle_popup_warnungen_beim_einstempeln()
                
                # Schritt 2f: PopUp-Warnungen aus DB laden und zur richtigen Uhrzeit schedulen
                self._load_and_schedule_popups()
                
            except (ValueError, TypeError) as e:
                logger.error(f"Fehler beim Starten des visuellen Timers: {e}", exc_info=True)
                self.main_view.timer_label.text = "Error"  # Fehler-Anzeige
        else:
            # === Ausgestempelt: Timer STOPPEN ===
            # Schritt 3b: Timer-Display auf "00:00" setzen
            self.main_view.timer_label.text = "00:00"
            
            # Schritt 3d: ALLE PopUp-Benachrichtigungen für heute aus DB löschen
            # Grund: Keine Warnungen mehr nötig, da ausgestempelt
            self.model_track_time.delete_all_popup_benachrichtigungen_for_today()
            logger.info("PopUp-Benachrichtigungen beim Ausstempeln gelöscht")
    
    def _load_and_schedule_popups(self):
        """
        Lädt ausstehende PopUp-Benachrichtigungen aus der DB und plant sie für die richtige Uhrzeit.
        
        Ablauf:
            1. Alle heutigen PopUp-Benachrichtigungen aus DB laden (ist_popup=True)
            2. Für jede Benachrichtigung:
               a) Aktuelle Zeit ermitteln
               b) Zielzeit (popup_uhrzeit) aus DB lesen
               c) Wenn Zielzeit in Zukunft:
                  → Verzögerung berechnen: (zielzeit - jetzt) in Sekunden
                  → Clock.schedule_once(_show_popup_from_db, verzögerung)
               d) Wenn Zielzeit bereits vorbei:
                  → PopUp sofort anzeigen (Verzögerung = 0)
        
        Note:
            Diese Methode wird nach jedem Einstempeln und nach Login aufgerufen.
            Bereits angezeigte PopUps werden automatisch aus DB gelöscht nach Bestätigung.
        """
        try:
            # === Schritt 1: Alle heutigen PopUps aus DB laden ===
            pending_popups = self.model_track_time.get_pending_popups_for_today()
            
            for code, popup_uhrzeit, benachrichtigung_id in pending_popups:
                # === Schritt 2a: Aktuelle Zeit ermitteln ===
                now = datetime.now()
                
                # === Schritt 2b: Zielzeit als datetime-Objekt ===
                popup_dt = datetime.combine(date.today(), popup_uhrzeit)
                
                # === Schritt 2c/d: Verzögerung berechnen und PopUp schedulen ===
                if popup_dt > now:
                    sekunden_bis_popup = (popup_dt - now).total_seconds()
                    
                    # PopUp planen
                    if code == 9:  # Arbeitsfenster-Warnung
                        self.arbeitsfenster_warning_event = Clock.schedule_once(
                            lambda dt, bid=benachrichtigung_id: self._show_popup_from_db(9, bid),
                            sekunden_bis_popup
                        )
                        logger.info(f"Arbeitsfenster-PopUp aus DB geplant für {popup_uhrzeit}")
                    elif code == 10:  # Max. Arbeitszeit-Warnung
                        self.max_arbeitszeit_warning_event = Clock.schedule_once(
                            lambda dt, bid=benachrichtigung_id: self._show_popup_from_db(10, bid),
                            sekunden_bis_popup
                        )
                        logger.info(f"Max. Arbeitszeit-PopUp aus DB geplant für {popup_uhrzeit}")
        
        except Exception as e:
            logger.error(f"Fehler beim Laden/Planen der PopUps: {e}", exc_info=True)
    
    def _refresh_popup_warnings(self):
        """
        Aktualisiert alle PopUp-Warnungen nach Stempel-Änderungen.
        
        Wird nach manuellen Stempel-Operationen (Bearbeiten, Löschen, Hinzufügen)
        aufgerufen, um die PopUp-Zeitpunkte neu zu berechnen.
        
        Logik:
        - Löscht alle bestehenden geplanten Events
        - Löscht alle heutigen PopUps aus der DB
        - Erstellt neue PopUps, wenn eingestempelt
        - Plant neue zeitgesteuerte Events
        """
        try:
            # Laufende geplante Events abbrechen, damit wir sie neu planen können
            if self.arbeitsfenster_warning_event:
                self.arbeitsfenster_warning_event.cancel()
                self.arbeitsfenster_warning_event = None
            if self.max_arbeitszeit_warning_event:
                self.max_arbeitszeit_warning_event.cancel()
                self.max_arbeitszeit_warning_event = None
            
            today_stamps = self.model_track_time.get_stamps_for_today()
            is_clocked_in = len(today_stamps) % 2 != 0
            
            # Bestehende PopUps entfernen, damit neue Zeiten gespeichert werden können
            self.model_track_time.delete_all_popup_benachrichtigungen_for_today()
            
            if is_clocked_in:
                self.model_track_time.erstelle_popup_warnungen_beim_einstempeln()
                self._load_and_schedule_popups()
            else:
                logger.debug("_refresh_popup_warnings: Nutzer ist nicht eingestempelt – PopUps gelöscht.")
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der PopUp-Warnungen: {e}", exc_info=True)
    
    def _show_popup_from_db(self, code, benachrichtigung_id):
        """
        Zeigt zeitgesteuertes PopUp an und löscht es aus der Datenbank.
        
        Args:
            code (int): Benachrichtigungs-Code (9=Arbeitsfenster, 10=Max. Arbeitszeit)
            benachrichtigung_id (int): ID der Benachrichtigung in der DB
            
        Note:
            Wird automatisch zum geplanten Zeitpunkt durch Clock.schedule_once aufgerufen.
        """
        try:
            from modell import session, mitarbeiter
            nutzer = session.get(mitarbeiter, self.model_track_time.aktueller_nutzer_id)
            if not nutzer:
                return
            
            is_minor = nutzer.is_minor_on_date(date.today())
            
            if code == 9:  # Arbeitsfenster-Warnung
                ende_zeit = "20:00" if is_minor else "22:00"
                self.main_view.show_messagebox(
                    title="Arbeitsfenster endet bald!",
                    message=f"WARNUNG: Ihr erlaubtes Arbeitsfenster endet um {ende_zeit} Uhr.\n\nBitte beachten Sie, dass Sie rechtzeitig ausstempeln.",
                    callback_yes=None,
                    yes_text="OK"
                )
                logger.warning(f"Arbeitsfenster-Warnung angezeigt (endet um {ende_zeit} Uhr)")
            
            elif code == 10:  # Max. Arbeitszeit-Warnung
                max_zeit = "8 Stunden" if is_minor else "10 Stunden"
                self.main_view.show_messagebox(
                    title="Maximale Arbeitszeit bald erreicht!",
                    message=f"WARNUNG: Sie erreichen in ca. 30 Minuten die maximale tägliche Arbeitszeit von {max_zeit}.\n\nBitte stempeln Sie rechtzeitig aus.",
                    callback_yes=None,
                    yes_text="OK"
                )
                logger.warning(f"Max. Arbeitszeit-Warnung angezeigt (max. {max_zeit})")
            
            # PopUp-Benachrichtigung aus DB löschen
            self.model_track_time.delete_popup_benachrichtigung(benachrichtigung_id)
            
        except Exception as e:
            logger.error(f"Fehler beim Anzeigen des PopUps (Code {code}): {e}", exc_info=True)
    def update_visual_timer(self, dt):
        if not self.start_time_dt:
            return
        try:
            elapsed = datetime.now() - self.start_time_dt
            total_seconds = int(elapsed.total_seconds())
            if total_seconds < 0: total_seconds = 0
            hours, remainder = divmod(total_seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            self.main_view.timer_label.text = f"{hours:02d}:{minutes:02d}"
        except Exception as e:
            logger.error(f"Fehler im update_visual_timer: {e}", exc_info=True)
            self.main_view.timer_label.text = "Error"
            if self.timer_event:
                self.timer_event.cancel() # Timer stoppen, um Endlosschleife zu verhindern
    
    def on_date_selected_register(self, instance, value, date_range):
        if value: # Input validieren
            self.register_view.reg_geburtsdatum.text = value.strftime("%d/%m/%Y")
    
    def on_weekly_hours_selected(self, spinner_instance, text):
        """
        Callback für die Auswahl der wöchentlichen Arbeitszeit.
        
        Berechnet automatisch Default-Werte für die Ampel-Grenzwerte:
        - Grün: Ein Arbeitstag (wochenstunden / 5)
        - Rot: Zwei Arbeitstage (wochenstunden * 2 / 5)
        
        Args:
            spinner_instance: Das Spinner-Widget
            text: Der ausgewählte Text (z.B. "40")
        """
        try:
            # Nur berechnen, wenn ein gültiger Wert ausgewählt wurde
            if text and text != "Wöchentliche Arbeitszeit wählen":
                wochenstunden = int(text)
                
                # Berechne Default-Werte
                gruen_default = int(wochenstunden / 5)  # Ein Arbeitstag
                rot_default = int(wochenstunden * 2 / 5)  # Zwei Arbeitstage
                
                # Setze die Default-Werte in die Eingabefelder
                self.register_view.reg_limit_green.text = str(gruen_default)
                self.register_view.reg_limit_red.text = str(rot_default)
                
                logger.debug(f"Ampel-Grenzwerte automatisch gesetzt: grün={gruen_default}h, rot={rot_default}h (basierend auf {wochenstunden}h/Woche)")
        except ValueError:
            # Falls der Text nicht in eine Zahl konvertiert werden kann, ignorieren
            logger.warning(f"Konnte wöchentliche Arbeitszeit nicht konvertieren: {text}")
        except Exception as e:
            logger.error(f"Fehler beim Berechnen der Ampel-Grenzwerte: {e}")
    
    def on_eintrag_art_selected(self, spinner_instance, text):
        if text in ["Urlaub", "Krankheit"]:
            self.main_view.time_input.opacity = 0
            self.main_view.time_label.opacity = 0
        else:
            self.main_view.time_input.opacity = 1
            self.main_view.time_label.opacity = 1
    def on_date_selected_main(self, instance, value, date_range):
        if value: # Input validieren
            self.main_view.date_input.text = value.strftime("%d/%m/%Y")
    def on_checkbox_changed(self, checkbox_instance, value):
        self.model_track_time.tage_ohne_stempel_beachten = bool(value)
        self.model_track_time.kummuliere_gleitzeit()
        self.update_view_time_tracking()
    
    def on_employee_selected(self, spinner_instance, employee_name):
        if not employee_name: # Ignorieren, wenn Spinner zurückgesetzt wird
            return
            
        self.model_track_time.aktuelle_kalendereinträge_für_name = employee_name
        self.model_track_time.get_id()
        self.load_vacation_days_for_calendar()  # Urlaubstage für den neuen Mitarbeiter laden
        # Day-Selected-Callback manuell auslösen, um die Ansicht für den neuen Mitarbeiter zu laden
        try:
            # Datum aus dem Label im Kalender holen
            current_date_str = self.main_view.month_calendar.date_label.text
            if current_date_str:
                current_date_obj = datetime.strptime(current_date_str, "%d.%m.%Y").date()
                self.day_selected(current_date_obj)
            else:
                # Fallback: Heutiges Datum
                self.day_selected(date.today())
        except ValueError:
             logger.warning(f"Ungültiges Datum im Kalender-Label: {current_date_str}. Lade für heute.")
             self.day_selected(date.today())
             
    def show_time_picker(self, instance, focus):
        self.active_time_input = instance
        if focus:
            try:
                self.main_view.time_picker.open()
            except Exception as e:
                logger.error(f"Fehler beim Öffnen des TimePickers: {e}", exc_info=True)
            instance.focus = False
    def on_time_selected(self, instance, time_val):
        if self.active_time_input and time_val: # Input validieren
            self.active_time_input.text = time_val.strftime("%H:%M")
    
    def day_selected(self, date_val):
        if not date_val: # Input validieren
            logger.warning("day_selected mit None-Datum aufgerufen.")
            return
            
        self.model_track_time.bestimmtes_datum = date_val.strftime("%d.%m.%Y")
        self.model_track_time.get_zeiteinträge()
        self.update_view_time_tracking()
    
    def on_tab_changed(self, panel, new_tab):
        """Wird aufgerufen, wenn im Haupt-TabbedPanel der Tab gewechselt wird.
        Wenn der Zeiterfassungs-/Gleitzeit-Tab aktiv wird, Gleitzeit neu berechnen und UI aktualisieren.
        Wenn der Benachrichtigungen-Tab aktiv wird, Benachrichtigungen neu laden.
        """
        try:
            tab_text = getattr(new_tab, 'text', '') if new_tab else ''
            if tab_text in ("Zeiterfassung", "Gleitzeit"):
                # Modell aktualisieren und Gleitzeit-Kennzahlen neu berechnen
                self.update_model_time_tracking()
                self.model_track_time.berechne_gleitzeit()
                self.model_track_time.set_ampel_farbe()
                self.model_track_time.kummuliere_gleitzeit()
                # UI auffrischen
                self.update_view_time_tracking()
            elif tab_text == "Einstellungen":
                self.update_model_time_tracking()
                self.model_track_time.get_user_info()
                self.update_view_time_tracking()
            elif tab_text == "Benachrichtigungen":
                # Benachrichtigungen aus der DB neu laden und UI aktualisieren
                logger.debug("Benachrichtigungen-Tab geöffnet, lade Benachrichtigungen neu")
                self.model_track_time.get_messages()
                self.update_view_benachrichtigungen()
        except Exception as e:
            logger.error(f"Fehler in on_tab_changed: {e}", exc_info=True)

    def stempel_bearbeiten_button_clicked(self, stempel_id: int, neue_zeit_str: str):
        """
        Wird aufgerufen, wenn der Bearbeiten-Button im Popup bestätigt wird.
        Ruft die Modell-Methode zum Bearbeiten des Stempels auf.
        
        Args:
            stempel_id (int): ID des zu bearbeitenden Zeiteintrags
            neue_zeit_str (str): Neue Uhrzeit als String (Format: "HH:MM")
        """
        if not self._can_edit_selected_employee():
            logger.info("Bearbeiten von Zeiteinträgen anderer Mitarbeitender ist nicht erlaubt")
            self.model_track_time.feedback_manueller_stempel = "Keine Berechtigung zum Bearbeiten fremder Stempel."
            self.update_view_time_tracking()
            return
        try:
            # Datum des Stempels vor der Bearbeitung ermitteln
            stempel_ist_heute = False
            try:
                stempel_datum = self.model_track_time.get_stempel_datum_by_id(stempel_id)
                if stempel_datum and stempel_datum == date.today():
                    stempel_ist_heute = True
                    logger.debug(f"Stempel {stempel_id} ist vom heutigen Tag")
            except Exception as e:
                logger.warning(f"Konnte Stempel-Datum nicht prüfen: {e}")
            
            # Zeit-String in time-Objekt konvertieren
            neue_zeit = datetime.strptime(neue_zeit_str, "%H:%M").time()
            
            # Modell-Methode aufrufen
            erfolg = self.model_track_time.stempel_bearbeiten_nach_id(stempel_id, neue_zeit)
            
            if erfolg:
                logger.info(f"Stempel {stempel_id} erfolgreich auf {neue_zeit_str} geändert")
                # UI aktualisieren
                self.update_model_time_tracking()
                self.model_track_time.set_ampel_farbe()
                self.model_track_time.kummuliere_gleitzeit()
                self.update_view_time_tracking()
                self._refresh_popup_warnings()
                
                # Timer-Status aktualisieren, falls Stempel vom heutigen Tag bearbeitet wurde
                if stempel_ist_heute:
                    self.start_or_stop_visual_timer()
                    logger.debug("Timer-Status nach Stempel-Bearbeitung aktualisiert")
                
                # Kalender neu laden
                if hasattr(self.main_view.month_calendar, 'date_label') and self.main_view.month_calendar.date_label.text:
                    datum_str = self.main_view.month_calendar.date_label.text
                    self.model_track_time.bestimmtes_datum = datum_str
                    self.model_track_time.get_zeiteinträge()
                    self.update_view_time_tracking()
            else:
                logger.error(f"Fehler beim Bearbeiten von Stempel {stempel_id}")
                self.main_view.show_messagebox("Fehler", "Stempel konnte nicht bearbeitet werden.")
        
        except ValueError as e:
            logger.error(f"Ungültiges Zeitformat: {neue_zeit_str} - {e}")
            self.main_view.show_messagebox("Fehler", f"Ungültiges Zeitformat: {neue_zeit_str}")
        except Exception as e:
            logger.error(f"Fehler beim Bearbeiten des Stempels: {e}", exc_info=True)
            self.main_view.show_messagebox("Fehler", f"Ein Fehler ist aufgetreten:\n{e}")
    def stempel_löschen_button_clicked(self, stempel_id: int):
        """
        Wird aufgerufen, wenn der Löschen-Button im Bestätigungsdialog bestätigt wird.
        Ruft die Modell-Methode zum Löschen des Stempels auf.
        
        Args:
            stempel_id (int): ID des zu löschenden Zeiteintrags
        """
        if not self._can_edit_selected_employee():
            logger.info("Löschen von Zeiteinträgen anderer Mitarbeitender ist nicht erlaubt")
            self.model_track_time.feedback_manueller_stempel = "Keine Berechtigung zum Löschen fremder Stempel."
            self.update_view_time_tracking()
            return
        try:
            # Datum des Stempels vor dem Löschen ermitteln
            stempel_ist_heute = False
            try:
                stempel_datum = self.model_track_time.get_stempel_datum_by_id(stempel_id)
                if stempel_datum and stempel_datum == date.today():
                    stempel_ist_heute = True
                    logger.debug(f"Stempel {stempel_id} ist vom heutigen Tag")
            except Exception as e:
                logger.warning(f"Konnte Stempel-Datum nicht prüfen: {e}")
            
            # Modell-Methode aufrufen
            erfolg = self.model_track_time.stempel_löschen_nach_id(stempel_id)
            
            if erfolg:
                logger.info(f"Stempel {stempel_id} erfolgreich gelöscht")
                # UI aktualisieren
                self.update_model_time_tracking()
                self.model_track_time.set_ampel_farbe()
                self.model_track_time.kummuliere_gleitzeit()
                self.update_view_time_tracking()
                self._refresh_popup_warnings()
                
                # Timer-Status aktualisieren, falls Stempel vom heutigen Tag gelöscht wurde
                if stempel_ist_heute:
                    self.start_or_stop_visual_timer()
                    logger.debug("Timer-Status nach Stempel-Löschung aktualisiert")
                
                # Kalender neu laden
                if hasattr(self.main_view.month_calendar, 'date_label') and self.main_view.month_calendar.date_label.text:
                    datum_str = self.main_view.month_calendar.date_label.text
                    self.model_track_time.bestimmtes_datum = datum_str
                    self.model_track_time.get_zeiteinträge()
                    self.update_view_time_tracking()
            else:
                logger.error(f"Fehler beim Löschen von Stempel {stempel_id}")
                self.main_view.show_messagebox("Fehler", "Stempel konnte nicht gelöscht werden.")
        
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Stempels: {e}", exc_info=True)
            self.main_view.show_messagebox("Fehler", f"Ein Fehler ist aufgetreten:\n{e}")
        
    # add_entry_in_popup ist im Original-Code nicht angebunden, daher ignoriert.
    #getter
    def get_view_manager(self):
        return self.sm