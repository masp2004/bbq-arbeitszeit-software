from kivy.uix.screenmanager import ScreenManager
from modell import ModellLogin, ModellTrackTime
from view import LoginView, RegisterView, MainView
from kivy.core.window import Window
from kivymd.uix.pickers import MDDatePicker, MDTimePicker
from datetime import datetime, date
from window_size import set_fixed_window_size
from kivy.clock import Clock
import time


class Controller():
    def __init__(self):
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


        self.login_view.change_view_registrieren_button.bind(on_press=self.change_view_register)
        self.register_view.change_view_login_button.bind(on_press=self.change_view_login)
        self.login_view.login_button.bind(on_press=self.einloggen_button_clicked)
        self.main_view.change_password_button.bind(on_press = self.passwort_ändern_button_clicked)

        self.register_view.reg_geburtsdatum.bind(focus=self.show_date_picker)
        self.register_view.date_picker.bind(on_save=self.on_date_selected_register)
        self.main_view.date_input.bind(focus=self.show_date_picker)
        self.main_view.date_picker.bind(on_save=self.on_date_selected_main)
        self.main_view.time_input.bind(focus=self.show_time_picker)
        self.main_view.time_picker.bind(on_save=self.on_time_selected)
        # Binden der Checkbox an eine Controller-Methode
        self.main_view.checkbox.bind(active=self.on_checkbox_changed)

        #bearbeiten button im Calender
        # self.main_view.calendar_layout.edit_button.bind(on_press=lambda instance, time=stempelzeit: self.open_edit_popup(self.date_label.text, time))

        self.main_view.eintrag_art_spinner.bind(text=self.on_eintrag_art_selected)

                # Binden des Spinners
        self.main_view.month_calendar.employee_spinner.bind(text=self.on_employee_selected)

        self.register_view.register_button.bind(on_press=self.registrieren_button_clicked)


        self.main_view.stempel_button.bind(on_press=self.stempel_button_clicked)
        self.main_view.nachtragen_button.bind(on_press=self.nachtragen_button_clicked)

        self.main_view.month_calendar.prev_btn.bind(on_release=self.prev_button_clicked)
        self.main_view.month_calendar.next_btn.bind(on_release=self.next_button_clicked)

        self.main_view.month_calendar.day_selected_callback = self.day_selected

     #updates   
    def update_model_login(self):
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
        self.register_view.register_rückmeldung_label.text = self.model_login.neuer_nutzer_rückmeldung
        self.login_view.anmeldung_rückmeldung_label.text = self.model_login.anmeldung_rückmeldung




    def update_model_time_tracking(self):
        self.model_track_time.aktueller_nutzer_id = self.model_login.anmeldung_mitarbeiter_id_validiert
        self.model_track_time.get_user_info()
        self.model_track_time.nachtragen_datum = self.main_view.date_input.text
        self.model_track_time.manueller_stempel_uhrzeit = self.main_view.time_input.text
        self.model_track_time.neuer_abwesenheitseintrag_art = self.main_view.eintrag_art_spinner.text
        self.model_track_time.neues_passwort = self.main_view.new_password_input.text
        self.model_track_time.neues_passwort_wiederholung = self.main_view.repeat_password_input.text
        self.model_track_time.bestimmtes_datum = self.main_view.month_calendar.date_label.text


    def update_view_time_tracking(self):
        self.main_view.anzeige_gleitzeit_wert_label.text = str(self.model_track_time.aktueller_nutzer_gleitzeit)
        self.main_view.nachtrag_feedback.text = self.model_track_time.feedback_manueller_stempel
        self.main_view.change_password_feedback.text =self.model_track_time.feedback_neues_passwort

        self.main_view.ampel.set_state(state=self.model_track_time.ampel_status)

        self.main_view.month_calendar.employee_spinner.values = self.model_track_time.mitarbeiter

        self.main_view.flexible_time_month.text = str(self.model_track_time.kummulierte_gleitzeit_monat)
        self.main_view.flexible_time_quarter.text = str(self.model_track_time.kummulierte_gleitzeit_quartal)
        self.main_view.flexible_time_year.text = str(self.model_track_time.kummulierte_gleitzeit_jahr)


        self.main_view.month_calendar.times_box.clear_widgets()  
        if self.model_track_time.zeiteinträge_bestimmtes_datum is not None:
              
            for stempel in self.model_track_time.zeiteinträge_bestimmtes_datum:
                zeit = stempel[0].zeit.strftime("%H:%M")
  

                self.main_view.month_calendar.add_time_row(stempelzeit= zeit, is_problematic=stempel[1])

    def update_view_benachrichtigungen(self):
        for nachricht in self.model_track_time.benachrichtigungen:
            self.main_view.add_benachrichtigung(text=nachricht.create_fehlermeldung(),
                                                datum=nachricht.datum)





    #call modell funktions
    def einloggen_button_clicked(self,b):
        self.update_model_login()
        success = self.model_login.login()
        self.update_view_login()
        if success:
            self.change_view_main(b=None)
            self.update_model_time_tracking()
            self.model_track_time.checke_arbeitstage()
            self.model_track_time.checke_stempel()
            self.model_track_time.berechne_gleitzeit()
            self.model_track_time.checke_ruhezeiten()
            self.model_track_time.get_messages()
            self.model_track_time.set_ampel_farbe()
            self.model_track_time.kummuliere_gleitzeit()
            self.model_track_time.get_employees()
            self.update_view_time_tracking()
            self.update_view_benachrichtigungen()
            self.start_or_stop_visual_timer()
            self.model_track_time.aktuelle_kalendereinträge_für_id = self.model_track_time.aktueller_nutzer_id

    def registrieren_button_clicked(self,b):
        self.update_model_login()
        self.model_login.neuen_nutzer_anlegen()
        self.update_view_login()


    def stempel_button_clicked(self,b):
        self.model_track_time.stempel_hinzufügen()
        self.start_or_stop_visual_timer()
        self.update_view_time_tracking()
    
    def nachtragen_button_clicked(self,b):
        self.update_model_time_tracking()
        if self.main_view.eintrag_art_spinner.text == "Zeitstempel":
            self.model_track_time.manueller_stempel_hinzufügen()
        elif self.main_view.eintrag_art_spinner.text == "Urlaub" or self.main_view.eintrag_art_spinner.text == "Krank":
            self.model_track_time.urlaub_eintragen()
        self.update_view_time_tracking()

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
            if instance == self.register_view.reg_geburtsdatum:
                self.register_view.date_picker.open()
            elif instance == self.main_view.date_input:
                self.main_view.date_picker.open()
            instance.focus = False

    #timer logik

    def toggle_timer(self, _):
        """Startet oder stoppt den Timer, wenn auf 'Stempeln' geklickt wird"""

        if not hasattr(self, "timer_running"):
            self.timer_running = False

        if self.timer_running:
            # Timer stoppen
            Clock.unschedule(self.update_timer)
            self.timer_running = False
            self.timer_label.text = "00:00:00"
        else:
            # Timer starten
            self.start_time = time.time()
            self.timer_running = True
            Clock.schedule_interval(self.update_timer, 1)

    def update_timer(self, _):
        """Wird jede Sekunde aufgerufen, um die gestempelte Zeit zu aktualisieren"""

        elapsed = int(time.time() - self.start_time)
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.timer_label.text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"    


    def start_or_stop_visual_timer(self):
        """
        Prüft den Stempelstatus im Modell und startet/stoppt den 
        visuellen Timer in der MainView entsprechend.
        """
        # Eventuellen alten Timer stoppen
        if self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None

        # Model fragen, ob der Nutzer gerade eingestempelt ist
        today_stamps = self.model_track_time.get_stamps_for_today()
        is_clocked_in = len(today_stamps) % 2 != 0

        if is_clocked_in:
            # Letzte Stempelzeit holen und Timer starten
            last_stamp_time = today_stamps[-1].zeit
            self.start_time_dt = datetime.combine(date.today(), last_stamp_time)
            self.timer_event = Clock.schedule_interval(self.update_visual_timer, 1)
            self.update_visual_timer(0) # Sofort aktualisieren
        else:
            # Nicht eingestempelt, Timer auf 00:00:00 setzen
            self.main_view.timer_label.text = "00:00:00"

    # NEUE METHODE
    def update_visual_timer(self, dt):
        """
        Wird jede Sekunde aufgerufen, um die Timer-Anzeige zu aktualisieren.
        """
        if not self.start_time_dt:
            return

        elapsed = datetime.now() - self.start_time_dt
        total_seconds = int(elapsed.total_seconds())

        # Sicherstellen, dass die Zeit nicht negativ wird (z.B. bei Systemzeitänderungen)
        if total_seconds < 0:
            total_seconds = 0

        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.main_view.timer_label.text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def on_date_selected_register(self, instance, value, date_range):
        """ value ist ein datetime.date Objekt """
        self.register_view.reg_geburtsdatum.text = value.strftime("%d/%m/%Y")

    def on_eintrag_art_selected(self, spinner_instance, text):
        """Blendet Zeitauswahl ein/aus je nach Art des Eintrags"""
        if text in ["Urlaub", "Krank"]:
            self.main_view.time_input.opacity = 0
            self.main_view.time_label.opacity = 0
        else:
            self.main_view.time_input.opacity = 1
            self.main_view.time_label.opacity = 1

    


    def on_date_selected_main(self, instance, value, date_range):
        """ value ist ein datetime.date Objekt """
        self.main_view.date_input.text = value.strftime("%d/%m/%Y")

    def on_checkbox_changed(self, checkbox_instance, value):
        """
        Diese Methode wird jedes Mal aufgerufen, wenn die Checkbox geklickt wird.
        """
        # 1. Den booleschen Wert aus dem 'active'-Attribut holen
        is_checked = value  # 'value' ist der neue Zustand (True oder False)

        # 2. Den Wert an das Model übergeben
        self.model_track_time.tage_ohne_stempel_beachten = is_checked

        # 3. Die Berechnung im Model neu anstoßen
        self.model_track_time.kummuliere_gleitzeit()

        # 4. Die View mit den neuen Werten aktualisieren
        self.update_view_time_tracking()
    
    def on_employee_selected(self, spinner_instance, employee_name):
        """
        Wird aufgerufen, wenn ein Mitarbeiter im Spinner ausgewählt wird.
        Aktualisiert das Modell und die Kalenderansicht.
        """
        # 1. Modell anweisen, die ID für den ausgewählten Mitarbeiter zu setzen
        self.model_track_time.aktuelle_kalendereinträge_für_name = self.main_view.month_calendar.employee_spinner.text
        self.model_track_time.get_id()

        # 2. Die Zeiteinträge für den aktuell im Kalender ausgewählten Tag neu laden
        # Wir rufen einfach die bestehende day_selected Funktion erneut auf


    def show_time_picker(self, instance, focus):
        self.active_time_input = instance
        if focus:
            self.main_view.time_picker.open()
            instance.focus= False

    def on_time_selected(self, instance, time):
        if self.active_time_input:
            self.active_time_input.text = time.strftime("%H:%M")
    
    def day_selected(self, date):
        ''' Wird aufgerufen, wenn ein Tag im Kalender ausgewählt wird '''

        self.update_model_time_tracking()
        self.model_track_time.get_zeiteinträge()
        self.update_view_time_tracking()



    def add_entry_in_popup(self, popup):
        entry_row, delete_btn = popup.add_entry()
        delete_btn.bind(on_release=lambda instance, row=entry_row: popup.entries_box.remove_widget(row))

    #getter
    def get_view_manager(self):
        return self.sm