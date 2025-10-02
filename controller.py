from kivy.uix.screenmanager import ScreenManager
from modell import ModellLogin, ModellTrackTime
from view import LoginView, RegisterView, MainView
from kivy.core.window import Window
from kivymd.uix.pickers import MDDatePicker
import datetime


class Controller():
    def __init__(self):
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
        self.register_view.reg_geburtsdatum.bind(focus=self.show_date_picker)
        self.register_view.date_picker.bind(on_save=self.on_date_selected)
        self.register_view.register_button.bind(on_press=self.registrieren_button_clicked)


        self.main_view.stempel_button.bind(on_press=self.stempel_button_clicked)

     #updates   
    def update_model_login(self):
        self.model_login.neuer_nutzer_name = self.register_view.reg_username_input.text
        self.model_login.neuer_nutzer_passwort = self.register_view.reg_password_input.text
        self.model_login.neuer_nutzer_passwort_val =self.register_view.reg_password_input_rep.text
        self.model_login.neuer_nutzer_geburtsdatum = self.register_view.reg_geburtsdatum.text
        self.model_login.neuer_nutzer_vertragliche_wochenstunden = self.register_view.reg_woechentliche_arbeitszeit.text


        self.model_login.anmeldung_name = self.login_view.username_input.text
        self.model_login.anmeldung_passwort = self.login_view.password_input.text

    def update_view_login(self):
        self.register_view.register_rückmeldung_label.text = self.model_login.neuer_nutzer_rückmeldung
        self.login_view.anmeldung_rückmeldung_label.text = self.model_login.anmeldung_rückmeldung




    def update_model_time_tracking(self):
        self.model_track_time.aktueller_nutzer_id = self.model_login.anmeldung_mitarbeiter_id_validiert
        self.model_track_time.get_user_info()


    def update_view_time_tracking(self):
        self.main_view.anzeige_gleitzeit_wert_label.text = str(self.model_track_time.aktueller_nutzer_gleitzeit)



    #call modell funktions
    def einloggen_button_clicked(self,b):
        self.update_model_login()
        succes = self.model_login.login()
        self.update_view_login()
        if succes:
            self.change_view_main(b=None)
            self.update_model_time_tracking()
            self.update_view_time_tracking()
        

    def registrieren_button_clicked(self,b):
        self.update_model_login()
        self.model_login.neuen_nutzer_anlegen()
        self.update_view_login()


    def stempel_button_clicked(self,b):
        self.model_track_time.stempel_hinzufügen()
        self.model_track_time.berechne_gleitzeit()
        self.update_view_time_tracking()

        


    #change views
    def change_view_register(self,b):
        Window.size = (self.register_view.width_window, self.register_view.height_window)
        self.sm.current = "register"
    
    def change_view_login(self,b):
        Window.size = (self.login_view.width_window, self.login_view.height_window)
        self.sm.current = "login"

    def change_view_main(self,b):
        Window.size =(self.main_view.time_tracking_tab_width, self.main_view.time_tracking_tab_heigt)
        self.sm.current = "main"

    def show_date_picker(self, instance, focus):
        '''Öffnet den Kalender zur Datumsauswahl'''

        if focus:
            self.register_view.date_picker.open()
            instance.focus = False
    
    def on_date_selected(self, instance, value, date_range):
        """ value ist ein datetime.date Objekt """
        self.register_view.reg_geburtsdatum.text = value.strftime("%d/%m/%Y")
    
    

    #getter
    def get_view_manager(self):
        return self.sm
