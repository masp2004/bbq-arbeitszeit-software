"""
Controller-Modul für die BBQ Arbeitszeit-Erfassungssoftware.

Dieses Modul implementiert den Controller im MVC-Pattern und koordiniert
die Interaktion zwischen Model (Modell) und View (Ansicht). Es verarbeitet
Benutzerinteraktionen, aktualisiert die Models und Views entsprechend.
"""

from kivy.uix.screenmanager import ScreenManager
from modell import ModellLogin, ModellTrackTime
from view import LoginView, RegisterView, MainView
from kivy.core.window import Window
from kivymd.uix.pickers import MDDatePicker, MDTimePicker
from datetime import datetime


class Controller():
    """
    Zentrale Controller-Klasse für die Zeiterfassungs-Anwendung.
    
    Der Controller koordiniert die Kommunikation zwischen den verschiedenen
    Views (Login, Register, Main) und den Models (ModellLogin, ModellTrackTime).
    Er verwaltet Event-Handler für UI-Elemente und steuert die Navigation
    zwischen verschiedenen Ansichten.
    
    Attributes:
        model_login (ModellLogin): Model für Login- und Registrierungslogik
        model_track_time (ModellTrackTime): Model für Zeiterfassung und Gleitzeit
        sm (ScreenManager): Verwaltet die verschiedenen Screens
        register_view (RegisterView): View für die Registrierung
        login_view (LoginView): View für den Login
        main_view (MainView): Hauptansicht der Anwendung
    """
    
    def __init__(self):
        """
        Initialisiert den Controller mit Models, Views und Event-Bindings.
        
        Erstellt alle notwendigen Model- und View-Instanzen, fügt Views zum
        ScreenManager hinzu und bindet alle UI-Events an entsprechende Handler-Methoden.
        """
        self.model_login = ModellLogin()
        self.model_track_time = ModellTrackTime()
        self.sm = ScreenManager()
        self.register_view = RegisterView(name="register")
        self.login_view = LoginView(name = "login")
        self.main_view = MainView(name="main")
        
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

        self.register_view.register_button.bind(on_press=self.registrieren_button_clicked)


        self.main_view.stempel_button.bind(on_press=self.stempel_button_clicked)
        self.main_view.nachtragen_button.bind(on_press=self.stempel_nachtragen_button_clickes)

        self.main_view.month_calendar.prev_btn.bind(on_release=self.prev_button_clicked)
        self.main_view.month_calendar.next_btn.bind(on_release=self.next_button_clicked)

        self.main_view.month_calendar.day_selected_callback = self.day_selected

     # Update-Methoden: Synchronisieren Model und View
    def update_model_login(self):
        """
        Aktualisiert das Login-Model mit den aktuellen Werten aus der View.
        
        Überträgt Benutzereingaben aus den Login- und Registrierungs-Views
        in die entsprechenden Model-Attribute.
        """
        self.model_login.neuer_nutzer_name = self.register_view.reg_username_input.text
        self.model_login.neuer_nutzer_passwort = self.register_view.reg_password_input.text
        self.model_login.neuer_nutzer_passwort_val =self.register_view.reg_password_input_rep.text
        self.model_login.neuer_nutzer_geburtsdatum = self.register_view.reg_geburtsdatum.text
        self.model_login.neuer_nutzer_vertragliche_wochenstunden = self.register_view.reg_woechentliche_arbeitszeit.text


        self.model_login.anmeldung_name = self.login_view.username_input.text
        self.model_login.anmeldung_passwort = self.login_view.password_input.text

    def update_view_login(self):
        """
        Aktualisiert die Login-View mit Rückmeldungen aus dem Model.
        
        Zeigt Feedback-Meldungen für Registrierung und Login in der
        Benutzeroberfläche an.
        """
        self.register_view.register_rückmeldung_label.text = self.model_login.neuer_nutzer_rückmeldung
        self.login_view.anmeldung_rückmeldung_label.text = self.model_login.anmeldung_rückmeldung




    def update_model_time_tracking(self):
        """
        Aktualisiert das Zeiterfassungs-Model mit Werten aus der View.
        
        Überträgt Benutzereingaben wie manueller Stempel, neues Passwort
        und ausgewähltes Datum in die Model-Attribute.
        """
        self.model_track_time.aktueller_nutzer_id = self.model_login.anmeldung_mitarbeiter_id_validiert
        self.model_track_time.get_user_info()
        self.model_track_time.manueller_stempel_datum = self.main_view.date_input.text
        self.model_track_time.manueller_stempel_uhrzeit = self.main_view.time_input.text
        self.model_track_time.neues_passwort = self.main_view.new_password_input.text
        self.model_track_time.neues_passwort_wiederholung = self.main_view.repeat_password_input.text
        self.model_track_time.bestimmtes_datum = self.main_view.month_calendar.date_label.text


    def update_view_time_tracking(self):
        """
        Aktualisiert die Zeiterfassungs-View mit Daten aus dem Model.
        
        Aktualisiert Gleitzeit-Anzeige, Feedback-Labels, Ampelstatus
        und die Kalenderansicht mit Zeiteinträgen.
        """
        self.main_view.anzeige_gleitzeit_wert_label.text = str(self.model_track_time.aktueller_nutzer_gleitzeit)
        self.main_view.nachtrag_feedback.text = self.model_track_time.feedback_manueller_stempel
        self.main_view.change_password_feedback.text =self.model_track_time.feedback_neues_passwort

        self.main_view.ampel.set_state(state=self.model_track_time.ampel_status)



        self.main_view.month_calendar.times_box.clear_widgets()  
        if self.model_track_time.zeiteinträge_bestimmtes_datum is not None:
              
            for stempel in self.model_track_time.zeiteinträge_bestimmtes_datum:
                zeit = stempel.zeit.strftime("%H:%M")
  

                self.main_view.month_calendar.add_time_row(stempelzeit= zeit)

    def update_view_benachrichtigungen(self):
        """
        Aktualisiert die Benachrichtigungs-View mit Meldungen aus dem Model.
        
        Fügt alle aktuellen Benachrichtigungen (z.B. fehlende Stempel,
        ArbZG-Verstöße) zur Benachrichtigungsansicht hinzu.
        """
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
            self.update_view_time_tracking()
            self.update_view_benachrichtigungen()

    def registrieren_button_clicked(self,b):
        """
        Handler für Registrierungs-Button-Click.
        
        Erstellt einen neuen Benutzer im System und zeigt Feedback an.
        
        Args:
            b: Button-Instance (wird von Kivy übergeben)
        """
        self.update_model_login()
        self.model_login.neuen_nutzer_anlegen()
        self.update_view_login()


    def stempel_button_clicked(self,b):
        """
        Handler für Stempel-Button-Click.
        
        Fügt einen Zeitstempel mit der aktuellen Uhrzeit hinzu und
        aktualisiert die Anzeige.
        
        Args:
            b: Button-Instance (wird von Kivy übergeben)
        """
        self.model_track_time.stempel_hinzufügen()
        self.update_view_time_tracking()
    
    def stempel_nachtragen_button_clickes(self,b):
        """
        Handler für manuellen Stempel-Nachtrag-Button-Click.
        
        Fügt einen manuellen Zeitstempel mit vom Benutzer gewähltem
        Datum und Uhrzeit hinzu.
        
        Args:
            b: Button-Instance (wird von Kivy übergeben)
        """
        self.update_model_time_tracking()
        self.model_track_time.manueller_stempel_hinzufügen()
        self.update_view_time_tracking()

    def passwort_ändern_button_clicked(self,b):
        """
        Handler für Passwort-Ändern-Button-Click.
        
        Aktualisiert das Benutzerpasswort und zeigt Feedback an.
        
        Args:
            b: Button-Instance (wird von Kivy übergeben)
        """
        self.update_model_time_tracking()
        self.model_track_time.update_passwort()
        self.update_view_time_tracking()

        
    # View-Funktionen aufrufen
    def prev_button_clicked(self, b):
        """
        Handler für Vorheriger-Monat-Button im Kalender.
        
        Args:
            b: Button-Instance (wird von Kivy übergeben)
        """
        self.main_view.month_calendar.change_month(-1)

    def next_button_clicked(self, b):
        """
        Handler für Nächster-Monat-Button im Kalender.
        
        Args:
            b: Button-Instance (wird von Kivy übergeben)
        """
        self.main_view.month_calendar.change_month(1)



    # View-Wechsel-Methoden
    def change_view_register(self,b):
        """
        Wechselt zur Registrierungs-Ansicht.
        
        Passt die Fenstergröße an und wechselt zum Register-Screen.
        
        Args:
            b: Button-Instance (wird von Kivy übergeben)
        """
        Window.size = (self.register_view.width_window, self.register_view.height_window)
        self.sm.current = "register" 
    
    def change_view_login(self,b):
        """
        Wechselt zur Login-Ansicht.
        
        Passt die Fenstergröße an und wechselt zum Login-Screen.
        
        Args:
            b: Button-Instance (wird von Kivy übergeben)
        """
        Window.size = (self.login_view.width_window, self.login_view.height_window)
        self.sm.current = "login"

    def change_view_main(self,b):
        """
        Wechselt zur Hauptansicht (Zeiterfassung).
        
        Passt die Fenstergröße an und wechselt zum Main-Screen.
        
        Args:
            b: Button-Instance (wird von Kivy übergeben)
        """
        Window.size =(self.main_view.time_tracking_tab_width, self.main_view.time_tracking_tab_height)
        self.sm.current = "main"

    def show_date_picker(self, instance, focus):
        """
        Zeigt den Datum-Picker an, wenn ein Datums-Feld fokussiert wird.
        
        Args:
            instance: Die TextInput-Instanz, die den Fokus erhalten hat
            focus (bool): True wenn Fokus erhalten, False wenn verloren
        """
        if focus:
            if instance == self.register_view.reg_geburtsdatum:
                self.register_view.date_picker.open()
            elif instance == self.main_view.date_input:
                self.main_view.date_picker.open()
            instance.focus = False

    
    def on_date_selected_register(self, instance, value, date_range):
        """
        Callback wenn Datum im Registrierungs-Picker ausgewählt wurde.
        
        Args:
            instance: DatePicker-Instanz
            value (datetime.date): Ausgewähltes Datum
            date_range: Datumsbereich (nicht verwendet)
        """
        self.register_view.reg_geburtsdatum.text = value.strftime("%d/%m/%Y")


    def on_date_selected_main(self, instance, value, date_range):
        """
        Callback wenn Datum im Hauptansicht-Picker ausgewählt wurde.
        
        Args:
            instance: DatePicker-Instanz
            value (datetime.date): Ausgewähltes Datum
            date_range: Datumsbereich (nicht verwendet)
        """
        self.main_view.date_input.text = value.strftime("%d/%m/%Y")

    def show_time_picker(self, instance, focus):
        """
        Zeigt den Zeit-Picker an, wenn ein Zeit-Feld fokussiert wird.
        
        Args:
            instance: Die TextInput-Instanz, die den Fokus erhalten hat
            focus (bool): True wenn Fokus erhalten, False wenn verloren
        """
        if focus:
            self.main_view.time_picker.open()
            instance.focus= False

    def on_time_selected(self, instance, time):
        """
        Callback wenn Uhrzeit im Zeit-Picker ausgewählt wurde.
        
        Args:
            instance: TimePicker-Instanz
            time (datetime.time): Ausgewählte Uhrzeit
        """
        self.main_view.time_input.text = time.strftime("%H:%M")
    

    
    def day_selected(self, date):
        """
        Wird aufgerufen, wenn ein Tag im Kalender ausgewählt wird.
        
        Bindet den Edit-Button für das gewählte Datum und lädt
        die Zeiteinträge für diesen Tag.
        
        Args:
            date (datetime.date): Ausgewähltes Datum
        """

        if hasattr(self.main_view.month_calendar, "_edit_callback"):
            self.main_view.month_calendar.edit_btn.unbind(on_release=self.main_view.month_calendar._edit_callback)

        def _callback(instance):
            popup = self.main_view.month_calendar.open_edit_popup(date)
            popup.add_btn.bind(on_release=lambda instance: self.add_entry_in_popup(popup))

        self.main_view.month_calendar._edit_callback = _callback
        self.main_view.month_calendar.edit_btn.bind(on_release=self.main_view.month_calendar._edit_callback)


        self.update_model_time_tracking()
        self.model_track_time.get_zeiteinträge()
        self.update_view_time_tracking()



    def add_entry_in_popup(self, popup):
        """
        Fügt einen neuen Eintrag im Bearbeitungs-Popup hinzu.
        
        Args:
            popup: Die Popup-Instanz mit den Zeiteinträgen
        """
        entry_row, delete_btn = popup.add_entry()
        delete_btn.bind(on_release=lambda instance, row=entry_row: popup.entries_box.remove_widget(row))

    # Getter-Methode
    def get_view_manager(self):
        """
        Gibt den ScreenManager zurück.
        
        Returns:
            ScreenManager: Der zentrale ScreenManager der Anwendung
        """
        return self.sm