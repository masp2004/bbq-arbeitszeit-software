from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.core.window import Window
from kivymd.uix.pickers import MDDatePicker, MDTimePicker
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.gridlayout import GridLayout
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from datetime import datetime

class LoginView(Screen):
    '''Anmelde-Fenster'''

    def __init__(self, **kwargs):
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
     def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.width_window = 800
        self.height_window = 600
        Window.size = (self.width_window, self.height_window)
        self.date_picker = MDDatePicker()
        # Hauptlayout (alles untereinander)
        self.layout = BoxLayout(orientation="vertical", padding=20, spacing=10)

        # Überschrift 
        self.layout.add_widget(Label(text="Registrieren", font_size=24, size_hint=(1, 0.2)))


        # 5 reihen
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


        # Button und labels unten hinzufügen
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
        super().__init__(**kwargs)
        self.layout = TabbedPanel(do_default_tab=False)
        self.date_picker = MDDatePicker()
        self.time_picker = MDTimePicker()
        self.create_time_tracking_tab()
        self.create_zeitnachtrag_tab()
        self.create_benachrichtigungen_tab()
        self.create_settings_tab()
        self.add_widget(self.layout)
        self.time_tracking_tab_heigt = 500
        self.time_tracking_tab_width = 800

    def create_time_tracking_tab(self):
        '''Erstellt die View für die Zeiterfassung'''

        self.time_tracking_tab = TabbedPanelItem(text="Zeiterfassung")

        # Hauptlayout vertikal
        self.time_tracking_layout = BoxLayout(orientation='vertical', padding=20, spacing=20)

        # --- Überschrift ---
        self.header_label = Label(
            text="Zeiterfassung",
            size_hint=(1, None),
            height=40,
            font_size=20,
            halign="center",
            valign="middle"
        )
        self.header_label.bind(size=self.header_label.setter('text_size'))
        self.time_tracking_layout.add_widget(self.header_label)

        # --- Erste Zeile: Stempeln + Gleitzeit ---
        self.reihe_1 = BoxLayout(orientation='horizontal', spacing=15, size_hint_y=None, height=40)

        self.stempel_button = Button(text="Stempeln", size_hint=(None, None), size=(130, 40))
        self.anzeige_gleitzeit_text_label = Label(
            text="Aktuelle Gleitzeit:", size_hint=(None, None), size=(220, 40),
            text_size=(220, 40), halign="left", valign="middle"
        )
        self.anzeige_gleitzeit_wert_label = Label(
            text="", size_hint=(None, None), size=(220, 40),
            text_size=(220, 40), halign="left", valign="middle"
        )

        self.reihe_1.add_widget(self.stempel_button)
        self.reihe_1.add_widget(self.anzeige_gleitzeit_text_label)
        self.reihe_1.add_widget(self.anzeige_gleitzeit_wert_label)
        self.time_tracking_layout.add_widget(self.reihe_1)

        # --- Testfelder sauber gruppieren ---
        self.test_labels_layout = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None)
        self.test_stempel = Label(
            text="", size_hint=(None, None), size=(450, 40),
            text_size=(450, 40), halign="left", valign="middle"
        )
        self.test_arbeitstage = Label(
            text="", size_hint=(None, None), size=(450, 40),
            text_size=(450, 40), halign="left", valign="middle"
        )
        self.test_labels_layout.add_widget(self.test_stempel)
        self.test_labels_layout.add_widget(self.test_arbeitstage)
        self.time_tracking_layout.add_widget(self.test_labels_layout)

        # --- Horizontale Buttons oder weitere Optionen (optional) ---
        self.time_tracking_horizontal_layout = BoxLayout(orientation='horizontal', spacing=15, size_hint_y=None, height=40)
        # Beispiel: Weitere Buttons oder Filter
        self.time_tracking_layout.add_widget(self.time_tracking_horizontal_layout)

        # --- Tab zum TabbedPanel hinzufügen ---
        self.time_tracking_tab.add_widget(self.time_tracking_layout)
        self.layout.add_widget(self.time_tracking_tab)

    def create_zeitnachtrag_tab(self):

        '''Erstellt die View für das manuelle Nachtragen von Zeitstempeln'''
        
        self.zeitnachtrag_tab = TabbedPanelItem(text="Zeit nachtragen")
        self.zeitnachtrag_layout = BoxLayout(orientation='vertical', padding=20, spacing=15)

        # --- Überschrift ---
        self.überschrift = Label(
            text="Manuelles Nachtragen von Zeitstempeln",
            size_hint=(1, None),
            height=40,
            halign="center",
            valign="middle",
            font_size=20
        )
        self.überschrift.bind(size=self.überschrift.setter('text_size'))  # damit halign wirkt
        self.zeitnachtrag_layout.add_widget(self.überschrift)

        # --- GridLayout nur mit Datum und Uhrzeit ---
        self.grid = GridLayout(cols=2, padding=(0, 20, 0, 0), spacing=15)

        # Datum
        self.grid.add_widget(Label(text="Datum: ", size_hint=(None, None), size=(220, 40),
                                text_size=(220, 40), halign="left", valign="middle"))
        self.date_input = TextInput(hint_text="TT/MM/JJJJ", size_hint=(None, None),
                                    size=(300, 40), readonly=True, multiline=False)

        self.grid.add_widget(self.date_input)

        # Uhrzeit
        self.grid.add_widget(Label(text="Uhrzeit: ", size_hint=(None, None), size=(220, 40),
                                text_size=(220, 40), halign="left", valign="middle"))
        self.time_input = TextInput(hint_text="HH:MM", size_hint=(None, None),
                                    size=(300, 40), readonly=True, multiline=False)
        self.grid.add_widget(self.time_input)

        # --- Button zum Nachtragen ---
        self.nachtragen_button = Button(text="Zeitstempel nachtragen", size_hint=(None, None), size=(220, 40))

        # --- Rückmeldung ---
        self.nachtrag_feedback = Label(text="", size_hint=(None, None), size=(500, 60),
                                    text_size=(500, None), halign="left", valign="middle")

        self.zeitnachtrag_layout.add_widget(self.grid)
        self.zeitnachtrag_layout.add_widget(self.nachtragen_button)
        self.zeitnachtrag_layout.add_widget(self.nachtrag_feedback)

        self.zeitnachtrag_tab.add_widget(self.zeitnachtrag_layout)
        self.layout.add_widget(self.zeitnachtrag_tab)

    def create_benachrichtigungen_tab(self):
        """Erstellt den Tab für Benachrichtigungen"""

        self.benachrichtigungen_tab = TabbedPanelItem(text="Benachrichtigungen")

        # --- Hauptlayout ---
        main_layout = BoxLayout(orientation='vertical', padding=20, spacing=15)

        # Überschrift
        header_label = Label(
            text="Benachrichtigungen",
            size_hint=(1, None),
            height=40,
            font_size=20,
            halign="center",
            valign="middle"
        )
        header_label.bind(size=header_label.setter("text_size"))
        main_layout.add_widget(header_label)

        # --- Scrollbarer Bereich ---
        scroll_view = ScrollView(size_hint=(1, 1))

        # GridLayout für Benachrichtigungen
        self.benachrichtigungen_grid = GridLayout(
            cols=1,
            spacing=10,
            size_hint_y=None,
            padding=(0, 10)
        )
        self.benachrichtigungen_grid.bind(minimum_height=self.benachrichtigungen_grid.setter('height'))

        scroll_view.add_widget(self.benachrichtigungen_grid)
        main_layout.add_widget(scroll_view)

        # --- Beispiel: Button zum Testen (optional) ---
        self.test_benachrichtigung_button = Button(
            text="Test-Benachrichtigung hinzufügen",
            size_hint=(None, None),
            size=(300, 40)
        )
        self.test_benachrichtigung_button.bind(on_press=lambda x: self.add_benachrichtigung(
            "Neue Test-Benachrichtigung!",
            datetime.now().strftime("%d.%m.%Y %H:%M")
        ))
        main_layout.add_widget(self.test_benachrichtigung_button)

        self.benachrichtigungen_tab.add_widget(main_layout)
        self.layout.add_widget(self.benachrichtigungen_tab)


    def add_benachrichtigung(self, text, datum):
        """Fügt eine einzelne Benachrichtigung zum Grid hinzu"""

        box = BoxLayout(
            orientation='vertical',
            padding=10,
            size_hint_y=None,
            height=80
        )

        # Stilvolle Umrandung oder Hintergrund
        box.canvas.before.clear()
        with box.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.15, 0.15, 0.2, 0.2)  # dezenter Hintergrund
            RoundedRectangle(pos=box.pos, size=box.size, radius=[8])
        box.bind(pos=lambda _, __: setattr(box.canvas.before.children[-1], 'pos', box.pos))
        box.bind(size=lambda _, __: setattr(box.canvas.before.children[-1], 'size', box.size))

        # Text der Benachrichtigung
        label_text = Label(
            text=text,
            font_size=16,
            halign="left",
            valign="middle",
            text_size=(600, None),
            size_hint_y=None
        )
        label_text.bind(texture_size=lambda _, s: setattr(label_text, 'height', s[1]))

        # Datum
        label_date = Label(
            text=f"[i]{datum}[/i]",
            markup=True,
            font_size=13,
            color=(0.6, 0.6, 0.6, 1),
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=20
        )

        box.add_widget(label_text)
        box.add_widget(label_date)
        self.benachrichtigungen_grid.add_widget(box)  

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
 


