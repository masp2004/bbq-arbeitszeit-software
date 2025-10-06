from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.core.window import Window
from kivymd.uix.pickers import MDDatePicker
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.gridlayout import GridLayout
from kivy.uix.spinner import Spinner


class LoginView(Screen):
    '''Anmelde-Fenster'''

    def __init__(self, **kwargs):
        '''Initialisiert die Login-View'''
        super().__init__(**kwargs)
        self.width_window = 300
        self.height_window = 220
        Window.size = (400, 300)

        self.layout = BoxLayout(orientation="vertical", padding=20, spacing=10)
        self.layout.add_widget(Label(text="Anmeldung", font_size=24))

        self.username_input = TextInput(multiline=False, hint_text="Benutzername")
        self.password_input = TextInput(password=True, multiline=False, hint_text="Passwort")
        self.anmeldung_rückmeldung_label = Label(text="")
        self.layout.add_widget(self.username_input)
        self.layout.add_widget(self.password_input)

        self.login_button = Button(text="Login", size_hint=(1, 1), font_size=20)
        self.change_view_registrieren_button = Button(text="Registrieren", size_hint=(1, 1), font_size=20)
        self.layout.add_widget(self.login_button)
        self.layout.add_widget(self.change_view_registrieren_button)
        self.layout.add_widget(self.anmeldung_rückmeldung_label)

        self.add_widget(self.layout)


class RegisterView(Screen):
    '''Registrierungs-Fenster'''

    def __init__(self, **kwargs):
        '''Initialisiert die Register-View'''
        super().__init__(**kwargs)

        self.width_window = 800
        self.height_window = 600
        Window.size = (self.width_window, self.height_window)
        self.date_picker = MDDatePicker()

        # Hauptlayout (alles untereinander)
        self.layout = BoxLayout(orientation="vertical", padding=20, spacing=10)

        # Überschrift
        self.layout.add_widget(Label(text="Registrieren", font_size=24, size_hint=(1, 0.2)))

        # 5 Reihen
        self.layout_reihe1 = BoxLayout(orientation="horizontal", spacing=10,  size_hint_y=None, height=40)
        self.layout_reihe2 = BoxLayout(orientation="horizontal", spacing=10,  size_hint_y=None, height=40)
        self.layout_reihe3 = BoxLayout(orientation="horizontal", spacing=10,  size_hint_y=None, height=40)
        self.layout_reihe4 = BoxLayout(orientation="horizontal", spacing=10,  size_hint_y=None, height=40)
        self.layout_reihe5 = BoxLayout(orientation="horizontal", spacing=10,  size_hint_y=None, height=40)

        # Labels
        self.layout_reihe1.add_widget(Label(text="Vor- und Nachname:"))
        self.layout_reihe2.add_widget(Label(text="Passwort:"))
        self.layout_reihe3.add_widget(Label(text="Passwort wiederholen:"))
        self.layout_reihe4.add_widget(Label(text="Wöchentliche Arbeitszeit:"))
        self.layout_reihe5.add_widget(Label(text="Geburtsdatum:"))
        
        # Eingabefelder
        self.reg_username_input = TextInput(
            multiline=False,
            hint_text="Vor und Nachname",
            font_size=18,
            size_hint_y=None,
            height=40
        )
        self.reg_password_input = TextInput(
            password=True,
            multiline=False,
            hint_text="Passwort",
            font_size=18,
            size_hint_y=None,
            height=40
        )
        self.reg_password_input_rep = TextInput(
            password=True,
            multiline=False,
            hint_text="Passwort Wiederholen",
            font_size=18,
            size_hint_y=None,
            height=40
        )
        self.reg_woechentliche_arbeitszeit = Spinner(
            text="Wöchentliche Arbeitszeit wählen",
            values=("30", "35", "40"),  # muss String sein
            size_hint_y=None,
            height=40,
            font_size=18
        )
        self.reg_geburtsdatum = TextInput(
            hint_text="TT/MM/JJJJ",
            size_hint=(1, None),
            readonly=True,
            multiline=False,
            font_size=18,
            height=40
        )

        self.layout_reihe1.add_widget(self.reg_username_input)
        self.layout_reihe2.add_widget(self.reg_password_input)
        self.layout_reihe3.add_widget(self.reg_password_input_rep)
        self.layout_reihe4.add_widget(self.reg_woechentliche_arbeitszeit)
        self.layout_reihe5.add_widget(self.reg_geburtsdatum)

        # Spalten ins horizontale Layout packen
        self.layout.add_widget(self.layout_reihe1)
        self.layout.add_widget(self.layout_reihe2)
        self.layout.add_widget(self.layout_reihe3)
        self.layout.add_widget(self.layout_reihe4)
        self.layout.add_widget(self.layout_reihe5)

        # Button und Labels unten hinzufügen
        self.change_view_login_button = Button(text="Zurück zum Login", size_hint=(1, 0.3), font_size=20)
        self.register_button = Button(text="Registrieren", size_hint=(1, 0.3), font_size=20)
        self.register_rückmeldung_label = Label(
            text="",
            font_size=12,   # kleiner als Standard
            size_hint=(1, 0.1)
        )
        self.layout.add_widget(self.register_rückmeldung_label)
        self.layout.add_widget(self.register_button)
        self.layout.add_widget(self.change_view_login_button)

        # Alles ins Screen packen
        self.add_widget(self.layout)


class MainView(Screen):
    '''Hauptfenster der Anwendung'''

    def __init__(self, **kwargs):
        '''Initialisiert die Main-View'''
        super().__init__(**kwargs)
        self.layout = TabbedPanel(do_default_tab=False)
        self.date_picker = MDDatePicker()
        self.create_time_tracking_tab()
        self.add_widget(self.layout)
        self.time_tracking_tab_heigt = 500
        self.time_tracking_tab_width = 800

    def create_time_tracking_tab(self):
        '''Erstellt die View für die Zeiterfassung'''

        self.time_tracking_tab = TabbedPanelItem(text="Zeiterfassung")

        self.time_tracking_layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        self.time_tracking_horizontal_layout = BoxLayout(orientation='horizontal', spacing=15, 
                                                         size_hint=(None, None), size=(200, 40))

        self.stempel_button = Button(text="Stempeln", size_hint=(None, None), size=(130, 40))
        self.anzeige_gleitzeit_text_label = Label(text="aktuelle Gleitzeit:", size_hint=(None, None), size=(220, 40), 
                                   text_size=(220, 40), halign="left", valign="middle")
        self.anzeige_gleitzeit_wert_label = Label(text="", size_hint=(None, None), size=(220, 40), 
                                   text_size=(220, 40), halign="left", valign="middle")
        self.reihe_1 = BoxLayout(orientation="horizontal", spacing=10,  size_hint_y=None, height=40)

        self.reihe_1.add_widget(self.stempel_button)
        self.reihe_1.add_widget(self.anzeige_gleitzeit_text_label)
        self.reihe_1.add_widget(self.anzeige_gleitzeit_wert_label)

        self.time_tracking_horizontal_layout.add_widget(self.reihe_1)

        self.stop_button = Button(text="Ausstempeln", size_hint=(None, None), size=(130, 40))

        self.time_tracking_layout.add_widget(self.time_tracking_horizontal_layout)

        self.grid = GridLayout(cols=2, padding=(0,20,0,0), spacing=15)

        self.grid.add_widget(Label(text="Datum: ", size_hint=(None, None), size=(220, 40), 
                                   text_size=(220, 40), halign="left", valign="middle"))
        self.date_input = TextInput(hint_text="TT/MM/JJJJ", size_hint=(None, None), 
                                    size=(300, 40), readonly=True, multiline=False)
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
