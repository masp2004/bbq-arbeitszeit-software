"""
DEPRECATED: Alte Version der BBQ Arbeitszeit-Erfassungssoftware.

Diese Datei ist veraltet und wird nicht mehr verwendet.
Die aktuelle Anwendung verwendet:
- main.py (Einstiegspunkt)
- controller.py (Controller-Logik)
- modell.py (Datenbank-Models und Geschäftslogik)
- view.py (GUI-Komponenten)

Behalten Sie diese Datei nur zu Referenzzwecken.
Für die aktive Entwicklung verwenden Sie bitte die oben genannten Dateien.
"""

from datetime import datetime

from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.gridlayout import GridLayout
from kivy.core.window import Window
from kivymd.app import MDApp
from kivymd.uix.pickers import MDDatePicker


class LoginScreen(Screen):
    '''Anmelde-Fenster'''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.size = (300, 180)

        self.layout = BoxLayout(orientation="vertical", padding=20, spacing=10)
        self.layout.add_widget(Label(text="Anmeldung", font_size=24))

        self.username_input = TextInput(multiline=False, hint_text="Benutzername")
        self.password_input = TextInput(password=True, multiline=False, hint_text="Passwort")
        self.layout.add_widget(self.username_input)
        self.layout.add_widget(self.password_input)

        self.login_button = Button(text="Login", size_hint=(1, 1), font_size=20)
        self.login_button.bind(on_press=self.login_action)
        self.layout.add_widget(self.login_button)

        self.add_widget(self.layout)

    def login_action(self, instance):
        '''Überprüft die Anmeldedaten und wechselt zum Hauptfenster'''

        entered = self.password_input.text
        if entered == "": # Dummy-Eingabe (muss angepasst werden)
            self.manager.current = "main"
            Window.size = (800, 500)


class MainScreen(Screen):
    '''Hauptfenster der Anwendung'''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = TabbedPanel(do_default_tab=False)
        self.date_picker = MDDatePicker()
        self.date_picker.bind(on_save=self.save, on_cancel=self.cancel)
        self.create_time_tracking_tab()
        self.create_settings_tab()
        self.add_widget(self.layout)

    def create_time_tracking_tab(self):
        '''Erstellt die View für die Zeiterfassung'''

        self.time_tracking_tab = TabbedPanelItem(text="Zeiterfassung")

        self.time_tracking_layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        self.time_tracking_horizontal_layout = BoxLayout(orientation='horizontal', spacing=15, 
                                                         size_hint=(None, None), size=(200, 40))

        self.start_button = Button(text="Einstempeln", size_hint=(None, None), size=(130, 40))
        self.start_button.bind(on_press=self.start_work)
        self.time_tracking_horizontal_layout.add_widget(self.start_button)

        self.stop_button = Button(text="Ausstempeln", size_hint=(None, None), size=(130, 40))
        self.stop_button.bind(on_press=self.stop_work)

        self.time_tracking_layout.add_widget(self.time_tracking_horizontal_layout)

        self.grid = GridLayout(cols=2, padding=(0,20,0,0), spacing=15)

        self.grid.add_widget(Label(text="Datum: ", size_hint=(None, None), size=(220, 40), 
                                   text_size=(220, 40), halign="left", valign="middle"))
        self.date_input = TextInput(hint_text="TT/MM/JJJJ", size_hint=(None, None), 
                                    size=(300, 40), readonly=True, multiline=False)
        self.date_input.bind(focus=self.show_date_picker)
        self.grid.add_widget(self.date_input)

        self.grid.add_widget(Label(text="Art der zu erfassenden Zeit: ", size_hint=(None, None), 
                                   size=(220, 40), text_size=(220, 40), halign="left", valign="middle"))
        self.grid.add_widget(Spinner(text="Bitte wählen", values=("Arbeitstag", "Urlaub", "Krank"), 
                                     size_hint=(None, None), size=(300, 40)))

        self.grid.add_widget(Label(text="Beginn: ", size_hint=(None, None), size=(220, 40), 
                                   text_size=(220, 40), halign="left", valign="middle"))
        self.grid.add_widget(TextInput(hint_text="HH:MM", size_hint=(None, None), size=(300, 40), 
                                       multiline=False))

        self.grid.add_widget(Label(text="Ende: ", size_hint=(None, None), size=(220, 40), 
                                   text_size=(220, 40), halign="left", valign="middle"))
        self.grid.add_widget(TextInput(hint_text="HH:MM", size_hint=(None, None), size=(300, 40), 
                                       multiline=False))

        self.grid.add_widget(Label(text="Pause: ", size_hint=(None, None), size=(220, 40), 
                                   text_size=(220, 40), halign="left", valign="middle"))
        self.grid.add_widget(TextInput(hint_text="HH:MM", size_hint=(None, None), size=(300, 40), 
                                       multiline=False))

        self.grid.add_widget(Label(text="Arbeitszeit: ", size_hint=(None, None), size=(220, 40), 
                                   text_size=(220, 40), halign="left", valign="middle"))
        self.horizontal_layout = BoxLayout(orientation='horizontal', spacing=100, 
                                           size_hint=(None, None), size=(200, 40))
        self.horizontal_layout.add_widget(TextInput(hint_text="HH:MM", size_hint=(None, None), 
                                                    size=(300, 40), multiline=False))
        self.horizontal_layout.add_widget(Button(text="Buchen", size_hint=(None, None), size=(130, 40)))
        self.grid.add_widget(self.horizontal_layout)

        self.time_tracking_layout.add_widget(self.grid)
        self.time_tracking_tab.add_widget(self.time_tracking_layout)
        self.layout.add_widget(self.time_tracking_tab)

    def create_settings_tab(self):
        '''Erstellt die View für die Einstellungen'''

        self.settings_tab = TabbedPanelItem(text="Einstellungen")

        self.settings_horizontal_layout = BoxLayout(orientation='horizontal')
        self.settings_layout = BoxLayout(orientation='vertical', padding=30, spacing=15, 
                                         size_hint=(0.5, None))
        self.settings_layout.bind(minimum_height=self.settings_layout.setter('height'))
        self.settings_layout.pos_hint = {"top": 1}

        self.settings_layout.add_widget(Label(text="Passwort ändern", font_size=18, 
                                              size_hint=(None, None), height=20, padding=(40,0,0,0)))
        self.new_password_input = TextInput(password=True, hint_text="Neues Passwort", 
                                            size_hint=(None, None), size=(300, 40))
        self.settings_layout.add_widget(self.new_password_input)
        self.repeat_password_input = TextInput(password=True, hint_text="Neues Passwort wiederholen", 
                                               size_hint=(None, None), size=(300, 40))
        self.settings_layout.add_widget(self.repeat_password_input)
        self.change_password_button = Button(text="Passwort ändern", size_hint=(None, None), 
                                             size=(180, 40))
        self.settings_layout.add_widget(self.change_password_button)

        self.grid = GridLayout(cols=2, padding=20, spacing=15, size_hint=(0.5, 1))
        self.grid.bind(minimum_height=self.grid.setter('height'))
        
        self.grid.add_widget(Label(text="Stundenwoche: ", font_size=18, size_hint=(None, None), 
                                   size=(160, 40), text_size=(160, 40), halign="left", valign="middle"))
        self.grid.add_widget(Spinner(text="Bitte wählen", values=("30 Stunden", "35 Stunden", "40 Stunden"), 
                                     size_hint=(None, None), size=(200, 40)))
        self.grid.add_widget(Label(text="Anzahl Urlaubstage: ", font_size=18, size_hint=(None, None), 
                                   size=(160, 40), text_size=(160, 40), halign="left", valign="middle"))
        self.grid.add_widget(TextInput(multiline=False, size_hint=(None, None), size=(200, 40)))

        self.grid.add_widget(Label(text="Grenzwerte: ", font_size=18, size_hint=(None, None), size=(160, 40), 
                                   text_size=(160, 40), halign="left", valign="middle"))
        self.horizonatl_layout1 = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=40)
        self.horizonatl_layout1.add_widget(Label(text="grün: ", font_size=18, size_hint=(None, None), size=(40, 40), 
                                                 text_size=(40, 40), halign="left", valign="middle"))
        self.horizonatl_layout1.add_widget(TextInput(multiline=False, size_hint=(None, None), size=(150, 40)))
        self.grid.add_widget(self.horizonatl_layout1)

        self.grid.add_widget(Label(size_hint=(None, None), size=(160, 40)))
        self.horizonatl_layout2 = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=40)
        self.horizonatl_layout2.add_widget(Label(text="gelb: ", font_size=18, size_hint=(None, None), size=(40, 40), 
                                                 text_size=(40, 40), halign="left", valign="middle"))
        self.horizonatl_layout2.add_widget(TextInput(multiline=False, size_hint=(None, None), size=(150, 40)))
        self.grid.add_widget(self.horizonatl_layout2)

        self.grid.add_widget(Label(size_hint=(None, None), size=(160, 40)))
        self.horizonatl_layout3 = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=40)
        self.horizonatl_layout3.add_widget(Label(text="rot: ", font_size=18, size_hint=(None, None), size=(40, 40), 
                                                 text_size=(40, 40), halign="left", valign="middle"))
        self.horizonatl_layout3.add_widget(TextInput(multiline=False, size_hint=(None, None), size=(150, 40)))
        self.grid.add_widget(self.horizonatl_layout3)

        self.settings_horizontal_layout.add_widget(self.grid)
        self.settings_horizontal_layout.add_widget(self.settings_layout)
        self.settings_tab.add_widget(self.settings_horizontal_layout)
        self.layout.add_widget(self.settings_tab)

    def start_work(self, instance):
        '''Wechselt die Schaltfläche von "Einstempeln" zu "Ausstempeln"'''

        self.time_tracking_horizontal_layout.remove_widget(self.start_button)
        self.time_tracking_horizontal_layout.add_widget(self.stop_button)

    def stop_work(self, instance):
        '''Wechselt die Schaltfläche von "Ausstempeln" zu "Einstempeln"'''

        self.time_tracking_horizontal_layout.remove_widget(self.stop_button)
        self.time_tracking_horizontal_layout.add_widget(self.start_button)

    def show_date_picker(self, instance, focus):
        '''Öffnet den Kalender zur Datumsauswahl'''

        if focus:
            self.date_picker.open()
            instance.focus = False

    def save(self, instance, value, date_range):
        '''Schreibt das ausgewählte Datum in das Eingabefeld'''

        self.date_input.text = value.strftime("%d/%m/%Y")
        instance.dismiss()

    def cancel(self, instance, value):
        '''Schließt den Kalender ohne Auswahl'''

        instance.dismiss()


class TimeTrackingApp(MDApp):
    '''Hauptklasse der Anwendung'''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.screen_manager = ScreenManager()

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "BlueGray"
        self.screen_manager.add_widget(LoginScreen(name="login"))
        self.screen_manager.add_widget(MainScreen(name="main"))
        self.screen_manager.current = "login"
        return self.screen_manager


if __name__ == "__main__":
    TimeTrackingApp().run()
