"""
Controller-Modul für die BBQ Arbeitszeit-Erfassungssoftware.

Dieses Modul implementiert den Controller im MVC-Pattern und ist verantwortlich für:

- Initialisierung und Verwaltung aller Views (Login, Register, Main)
- Binding von UI-Events an Callback-Funktionen
- Kommunikation zwischen Model und View
- Datensynchronisation (Update-Methoden)
- Event-Handling mit Fehlerbehandlung (_bind_safe)
- Timer-Logik für laufende Arbeitszeit-Anzeige
- Koordination von Workflows (Login -> Daten laden -> UI aktualisieren)

Der Controller verwendet einen Safe-Binding-Mechanismus, der alle Callbacks in
try-except-Blöcke wrapp um die Stabilität der Anwendung zu gewährleisten.
"""

from kivy.uix.screenmanager import ScreenManager
from modell import ModellLogin, ModellTrackTime
from view import LoginView, RegisterView, MainView
from kivy.core.window import Window
from kivymd.uix.pickers import MDDatePicker, MDTimePicker
from datetime import datetime, date
from window_size import set_fixed_window_size
from kivy.clock import Clock
import time
import logging

# Logger für dieses Modul
logger = logging.getLogger(__name__)


class Controller():
    """
    Haupt-Controller der Anwendung (MVC-Pattern).
    
    Der Controller koordiniert die Interaktion zwischen Models (ModellLogin, ModellTrackTime)
    und Views (LoginView, RegisterView, MainView). Er implementiert:
    
    - Safe Event-Binding mit automatischer Fehlerbehandlung
    - Datensynchronisation zwischen Model und View
    - View-Wechsel und Fenstergrößen-Management
    - Timer-Funktionalität für laufende Arbeitszeit
    - Callback-Handling für alle UI-Events
    
    Attributes:
        model_login (ModellLogin): Model für Login/Registrierung
        model_track_time (ModellTrackTime): Model für Zeiterfassung
        sm (ScreenManager): Manager für Screen-Wechsel
        register_view/login_view/main_view: Die drei Haupt-Views
        active_time_input: Aktuelles Zeiteingabe-Feld für TimePicker
        timer_event: Clock-Event für Timer-Update
        start_time_dt: Startzeit der aktuellen Arbeitsperiode
    """
    def __init__(self):
        """
        Initialisiert den Controller und alle zugehörigen Komponenten.
        
        Erstellt Models, Views und ScreenManager, bindet alle Events
        und setzt den initialen Screen auf "login".
        
        Raises:
            Exception: Bei kritischen Fehlern während der Initialisierung
        """
        try:
            self.model_login = ModellLogin()
            self.model_track_time = ModellTrackTime()
            self.sm = ScreenManager()
            self.register_view = RegisterView(name="register")
            self.login_view = LoginView(name = "login")
            self.main_view = MainView(name="main")
            self.active_time_input = None

            # status für den Timer
            self.timer_event = None
            self.start_time_dt = None
            
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
            self._bind_safe(self.main_view.stempel_button, 'on_press', self.stempel_button_clicked)
            self._bind_safe(self.main_view.nachtragen_button, 'on_press', self.nachtragen_button_clicked)

            self._bind_safe(self.main_view.month_calendar.prev_btn, 'on_release', self.prev_button_clicked)
            self._bind_safe(self.main_view.month_calendar.next_btn, 'on_release', self.next_button_clicked)

            self.main_view.month_calendar.day_selected_callback = self.day_selected
            
            logger.debug("Controller initialisiert und alle Widgets gebunden.")

        except Exception as e:
            logger.critical(f"Kritischer Fehler während der Controller-Initialisierung: {e}", exc_info=True)
            # Dieser Fehler muss nach oben weitergegeben werden, siehe main.py
            raise

    def _bind_safe(self, widget, event, callback):
        """
        Hilfsmethode, um Callbacks sicher zu binden.
        Jedes Callback wird in einen try-except-Block gehüllt.
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


    #updates (Diese sind meist unkritisch, da sie nur Daten kopieren)
    def update_model_login(self):
        # ... (Inhalt bleibt gleich) ...
        self.model_login.neuer_nutzer_name = self.register_view.reg_username_input.text
        self.model_login.neuer_nutzer_passwort = self.register_view.reg_password_input.text
        self.model_login.neuer_nutzer_passwort_val =self.register_view.reg_password_input_rep.text
        self.model_login.neuer_nutzer_geburtsdatum = self.register_view.reg_geburtsdatum.text
        self.model_login.neuer_nutzer_vertragliche_wochenstunden = self.register_view.reg_woechentliche_arbeitszeit.text
        self.model_login.neuer_nutzer_vorgesetzter = self.register_view.reg_superior.text
        self.model_login.neuer_nutzer_grün = self.register_view.reg_limit_green.text
        self.model_login.neuer_nutzer_rot = self.register_view.reg_limit_red.text
        self.model_login.anmeldung_name = self.login_view.username_input.text
        self.model_login.anmeldung_passwort = self.login_view.password_input.text

    def update_view_login(self):
        # ... (Inhalt bleibt gleich) ...
        self.register_view.register_rückmeldung_label.text = self.model_login.neuer_nutzer_rückmeldung
        self.login_view.anmeldung_rückmeldung_label.text = self.model_login.anmeldung_rückmeldung

    def update_model_time_tracking(self):
        # ... (Inhalt bleibt gleich) ...
        self.model_track_time.aktueller_nutzer_id = self.model_login.anmeldung_mitarbeiter_id_validiert
        self.model_track_time.get_user_info()
        self.model_track_time.nachtragen_datum = self.main_view.date_input.text
        self.model_track_time.manueller_stempel_uhrzeit = self.main_view.time_input.text
        self.model_track_time.neuer_abwesenheitseintrag_art = self.main_view.eintrag_art_spinner.text
        self.model_track_time.neues_passwort = self.main_view.new_password_input.text
        self.model_track_time.neues_passwort_wiederholung = self.main_view.repeat_password_input.text
        self.model_track_time.bestimmtes_datum = self.main_view.month_calendar.date_label.text


    def update_view_time_tracking(self):
        # ... (Inhalt bleibt gleich) ...
        # Hinzufügen einer Konvertierung, um sicherzustellen, dass es ein String ist
        gleitzeit_str = f"{self.model_track_time.aktueller_nutzer_gleitzeit:.2f}"
        self.main_view.anzeige_gleitzeit_wert_label.text = gleitzeit_str
        self.main_view.nachtrag_feedback.text = self.model_track_time.feedback_manueller_stempel
        self.main_view.change_password_feedback.text =self.model_track_time.feedback_neues_passwort

        if self.model_track_time.ampel_status:
            self.main_view.ampel.set_state(state=self.model_track_time.ampel_status)

        self.main_view.month_calendar.employee_spinner.values = self.model_track_time.mitarbeiter

        self.main_view.flexible_time_month.text = str(self.model_track_time.kummulierte_gleitzeit_monat)
        self.main_view.flexible_time_quarter.text = str(self.model_track_time.kummulierte_gleitzeit_quartal)
        self.main_view.flexible_time_year.text = str(self.model_track_time.kummulierte_gleitzeit_jahr)

        self.main_view.month_calendar.times_box.clear_widgets()  
        if self.model_track_time.zeiteinträge_bestimmtes_datum is not None:
            for stempel in self.model_track_time.zeiteinträge_bestimmtes_datum:
                # Sicherstellen, dass 'stempel' das erwartete Format hat
                if isinstance(stempel, list) and len(stempel) >= 2 and hasattr(stempel[0], 'zeit'):
                    zeit_str = stempel[0].zeit.strftime("%H:%M")
                    self.main_view.month_calendar.add_time_row(stempelzeit=zeit_str, is_problematic=stempel[1])
                else:
                    logger.warning(f"Unerwartetes Stempelformat in update_view_time_tracking: {stempel}")

    def update_view_benachrichtigungen(self):
        # ... (Inhalt bleibt gleich) ...
        self.main_view.benachrichtigungen_grid.clear_widgets() # Sicherstellen, dass die Liste leer ist
        for nachricht in self.model_track_time.benachrichtigungen:
            try:
                msg_text = nachricht.create_fehlermeldung()
                msg_datum = nachricht.datum or "Kein Datum" # Fallback
                self.main_view.add_benachrichtigung(text=msg_text, datum=msg_datum)
            except Exception as e:
                logger.error(f"Fehler beim Erstellen der Benachrichtigungs-UI: {e}", exc_info=True)


    #call modell funktions (Alle Callbacks werden bereits durch _bind_safe geschützt)
    
    def einloggen_button_clicked(self,b):
        # Dieser Block wird jetzt von _bind_safe geschützt
        self.update_model_login()
        success = self.model_login.login()
        self.update_view_login()
        if success:
            logger.info("Login erfolgreich, starte Daten-Lade-Prozess...")
            self.change_view_main(b=None)
            self.update_model_time_tracking()
            
            # Alle Lade-Operationen
            self.model_track_time.checke_arbeitstage()
            self.model_track_time.checke_stempel()
            self.model_track_time.berechne_gleitzeit() # Muss vor set_ampel_farbe sein
            self.model_track_time.checke_ruhezeiten()
            self.model_track_time.checke_durchschnittliche_arbeitszeit()
            self.model_track_time.checke_max_arbeitszeit()
            self.model_track_time.checke_sonn_feiertage()
            self.model_track_time.checke_wochenstunden_minderjaehrige()
            self.model_track_time.checke_arbeitstage_pro_woche_minderjaehrige()
            
            # Daten für UI holen
            self.model_track_time.get_messages()
            self.model_track_time.set_ampel_farbe()
            self.model_track_time.kummuliere_gleitzeit()
            self.model_track_time.get_employees()
            
            # UI aktualisieren
            self.update_view_time_tracking()
            self.update_view_benachrichtigungen()
            self.start_or_stop_visual_timer()
            self.model_track_time.aktuelle_kalendereinträge_für_id = self.model_track_time.aktueller_nutzer_id
            logger.info("Daten-Lade-Prozess abgeschlossen, MainView angezeigt.")

    def registrieren_button_clicked(self,b):
        self.update_model_login()
        self.model_login.neuen_nutzer_anlegen()
        self.update_view_login()


    def stempel_button_clicked(self,b):
        self.model_track_time.stempel_hinzufügen()
        self.start_or_stop_visual_timer()
        # self.update_view_time_tracking() # Nicht nötig, Timer-Funktion macht das
    
    def nachtragen_button_clicked(self,b):
        self.update_model_time_tracking()
        art = self.main_view.eintrag_art_spinner.text
        
        if art == "Zeitstempel":
            self.model_track_time.manueller_stempel_hinzufügen()
        elif art == "Urlaub" or art == "Krank":
            self.model_track_time.urlaub_eintragen()
        else:
            self.model_track_time.feedback_manueller_stempel = "Bitte eine Eintragsart wählen."
            
        self.update_view_time_tracking() # Feedback anzeigen

    def passwort_ändern_button_clicked(self,b):
        self.update_model_time_tracking()
        self.model_track_time.update_passwort()
        self.update_view_time_tracking()

        
    #call view functions
    def prev_button_clicked(self, b):
        self.main_view.month_calendar.change_month(-1)

    def next_button_clicked(self, b):
        self.main_view.month_calendar.change_month(1)


    #change views
    def change_view_register(self,b):
        set_fixed_window_size((self.register_view.width_window, self.register_view.height_window))
        self.sm.current = "register" 
    
    def change_view_login(self,b):
        set_fixed_window_size((self.login_view.width_window, self.login_view.height_window))
        self.sm.current = "login"

    def change_view_main(self,b):
        set_fixed_window_size((self.main_view.time_tracking_tab_width, self.main_view.time_tracking_tab_height))
        self.sm.current = "main"

    def show_date_picker(self, instance, focus):
        if focus:
            try:
                if instance == self.register_view.reg_geburtsdatum:
                    self.register_view.date_picker.open()
                elif instance == self.main_view.date_input:
                    self.main_view.date_picker.open()
            except Exception as e:
                logger.error(f"Fehler beim Öffnen des DatePickers: {e}", exc_info=True)
            instance.focus = False

    #timer logik
    def start_or_stop_visual_timer(self):
        if self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None

        today_stamps = self.model_track_time.get_stamps_for_today()
        is_clocked_in = len(today_stamps) % 2 != 0

        if is_clocked_in:
            try:
                last_stamp_time = today_stamps[-1].zeit
                self.start_time_dt = datetime.combine(date.today(), last_stamp_time)
                self.timer_event = Clock.schedule_interval(self.update_visual_timer, 1)
                self.update_visual_timer(0)
            except (ValueError, TypeError) as e:
                 logger.error(f"Fehler beim Starten des visuellen Timers: {e}", exc_info=True)
                 self.main_view.timer_label.text = "Error"
        else:
            self.main_view.timer_label.text = "00:00:00"

    def update_visual_timer(self, dt):
        if not self.start_time_dt:
            return

        try:
            elapsed = datetime.now() - self.start_time_dt
            total_seconds = int(elapsed.total_seconds())
            if total_seconds < 0: total_seconds = 0

            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.main_view.timer_label.text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        except Exception as e:
            logger.error(f"Fehler im update_visual_timer: {e}", exc_info=True)
            self.main_view.timer_label.text = "Error"
            if self.timer_event:
                self.timer_event.cancel() # Timer stoppen, um Endlosschleife zu verhindern

    
    def on_date_selected_register(self, instance, value, date_range):
        if value: # Input validieren
            self.register_view.reg_geburtsdatum.text = value.strftime("%d/%m/%Y")

    def on_eintrag_art_selected(self, spinner_instance, text):
        if text in ["Urlaub", "Krank"]:
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
        
    # add_entry_in_popup ist im Original-Code nicht angebunden, daher ignoriert.

    #getter
    def get_view_manager(self):
        return self.sm