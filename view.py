import datetime
import calendar

from datetime import datetime as dt
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
from kivymd.uix.button import MDIconButton
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, Line, Ellipse


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
        self.layout = TabbedPanel(do_default_tab=False, tab_width=170)
        self.date_picker = MDDatePicker()
        self.time_picker = MDTimePicker()
        self.create_time_tracking_tab()
        self.create_zeitnachtrag_tab()
        self.create_calendar_tab()
        self.create_benachrichtigungen_tab()
        self.create_settings_tab()
        self.add_widget(self.layout)
        self.time_tracking_tab_height = 590
        self.time_tracking_tab_width = 800

    def create_time_tracking_tab(self):
        '''Erstellt die View für die Zeiterfassung'''

        self.time_tracking_tab = TabbedPanelItem(text="Zeiterfassung")

        main_layout = BoxLayout(orientation='horizontal', padding=20)

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

        # Ampel
        self.ampel = TrafficLight()

        main_layout.add_widget(self.time_tracking_layout)
        main_layout.add_widget(self.ampel)

        # --- Tab zum TabbedPanel hinzufügen ---
        self.time_tracking_tab.add_widget(main_layout)
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

    def create_calendar_tab(self):
        '''Erstellt die View für die Kalender-Ansicht'''

        self.calendar_tab = TabbedPanelItem(text="Kalenderansicht")
        self.calendar_layout = BoxLayout(orientation="vertical")
        self.month_calendar = MonthCalendar()
        self.calendar_layout.add_widget(self.month_calendar)
        self.calendar_tab.add_widget(self.calendar_layout)
        self.layout.add_widget(self.calendar_tab)

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
            dt.now().strftime("%d.%m.%Y %H:%M")
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


class TrafficLight(BoxLayout):
    '''Ampelanzeige mit 3 Kreisen'''

    def __init__(self):
        '''Initialisiert die Ampelanzeige'''

        super().__init__()
        self.orientation = "vertical"
        self.pos_hint = {"top": 1}
        self.size_hint = (None, None)
        self.size = (60, 160)

        # Ampel-Kreise
        with self.canvas:
            # Rot
            color_red = Color(0.3, 0.3, 0.3)
            ellipse_red = Ellipse(pos=(self.x, self.y + 100), size=(40, 40))
            # Gelb
            color_yellow = Color(0.3, 0.3, 0.3)
            ellipse_yellow = Ellipse(pos=(self.x, self.y + 50), size=(40, 40))
            # Grün
            color_green = Color(0.3, 0.3, 0.3)
            ellipse_green = Ellipse(pos=(self.x, self.y), size=(40, 40))

        self.lights = {
            "red": (color_red, ellipse_red),
            "yellow": (color_yellow, ellipse_yellow),
            "green": (color_green, ellipse_green),
        }

        self.bind(pos=self.update_positions, size=self.update_positions)

    def update_positions(self, *args):
        """Bestimmt die Positionen der Ampel-Kreise"""
        
        for i, color in enumerate(["green", "yellow", "red"]):
            self.lights[color][1].pos = (self.x, self.y + i * 50)

    def set_state(self, state):
        """Setzt die Ampel auf den angegebenen Zustand"""

        for color, _ in self.lights.values():
            color.rgb = (0.3, 0.3, 0.3)

        if state == "red":
            self.lights["red"][0].rgb = (1, 0, 0)
        elif state == "yellow":
            self.lights["yellow"][0].rgb = (1, 1, 0)
        elif state == "green":
            self.lights["green"][0].rgb = (0, 1, 0)


class MonthCalendar(BoxLayout):
    '''Kalender mit Monatsübersicht und Anzeige der gestempelten Zeiten'''

    def __init__(self):
        '''Initialisiert die Monatsansicht des Kalenders'''
        
        super().__init__(orientation="vertical")
        today = datetime.date.today()
        self.year = today.year
        self.month = today.month

        self.build_ui()

    def build_ui(self):
        '''Erstellt die UI-Komponenten'''

        self.clear_widgets()

        # Auswahl, welcher Mitarbeiter-Kalender angezeigt werden soll
        calendar_choice = BoxLayout(orientation="horizontal", size_hint_y=None, height=50, padding=10)
        calendar_choice.add_widget(Label(text="Kalenderansicht:", size_hint=(None, None), size=(150, 30), 
                                   text_size=(150, 30), halign="left", valign="middle"))
        self.employee_spinner = Spinner(size_hint=(None, None), size=(200, 30))
        calendar_choice.add_widget(self.employee_spinner)
        self.add_widget(calendar_choice)

        # Header für den Kalender
        header = BoxLayout(size_hint_y=None, height=30)
        self.prev_btn = Button(text="<<", size_hint_x=None, width=60)
        self.next_btn = Button(text=">>", size_hint_x=None, width=60)
        self.title_label = Label(text=self.title_text())
        header.add_widget(self.prev_btn)
        header.add_widget(self.title_label)
        header.add_widget(self.next_btn)
        self.add_widget(header)

        # Wochentage
        weekdays = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        weekday_row = GridLayout(cols=7, padding=(0, 10, 0, 0), size_hint_y=None, height=30)
        for weekday in weekdays:
            weekday_row.add_widget(Label(text=weekday, color=(1, 1, 1, 1)))
        self.add_widget(weekday_row)

        # Grid für Kalender
        self.grid = GridLayout(cols=7, padding=(0, 10, 0, 0))
        self.add_widget(self.grid)

        self.fill_grid_with_days()

        # Tabelle für die Anzeige der gestempelten Zeiten
        self.detail_table = LinedGridLayout(cols=4, size_hint_y=None, height=150, padding=10, spacing=10)

        # Überschriften
        self.detail_table.add_widget(self.aligned_label(text="Datum", bold=True, color=(0, 0, 0, 1), 
                                                        size_hint_y=None, height=20, halign="left", valign="top"))
        self.detail_table.add_widget(self.aligned_label(text="Gestempelte Zeiten", bold=True, color=(0, 0, 0, 1), 
                                                        size_hint_y=None, height=20, halign="left", valign="top"))
        self.detail_table.add_widget(self.aligned_label(text="Gleitzeit", bold=True, color=(0, 0, 0, 1), 
                                                        size_hint_y=None, height=20, halign="left", valign="top"))
        self.detail_table.add_widget(Label(text="", size_hint_y=None, height=20))

        # Inhalte
        self.date_label = self.aligned_label(text="", color=(0, 0, 0, 1), halign="left", valign="top")

        self.times_scroll = ScrollView(size_hint=(1, 1), bar_width=10, bar_color=(0.7, 0.7, 0.7, 1))
        self.times_box = GridLayout(cols=1, size_hint_y=None, spacing=5)
        self.times_box.bind(minimum_height=self.times_box.setter("height"))
        self.times_scroll.add_widget(self.times_box)

        self.flexible_time_label = self.aligned_label(text="", color=(0, 0, 0, 1), halign="left", valign="top")

        self.edit_btn_container = AnchorLayout(anchor_x="right", anchor_y="top")
        self.edit_btn = MDIconButton(icon="pencil", theme_text_color="Custom", text_color=(0, 0, 0, 1))
        self.edit_btn_container.add_widget(self.edit_btn)

        self.detail_table.add_widget(self.date_label)
        self.detail_table.add_widget(self.times_scroll)
        self.detail_table.add_widget(self.flexible_time_label)
        self.detail_table.add_widget(self.edit_btn_container)

        self.add_widget(self.detail_table)

    def change_month(self, delta):
        """Wechselt den angezeigten Monat"""

        self.month += delta
        if self.month < 1:
            self.month = 12
            self.year -= 1
        elif self.month > 12:
            self.month = 1
            self.year += 1
        self.title_label.text = self.title_text()
        self.fill_grid_with_days()

    def title_text(self):
        """Gibt den Titel für den aktuellen Monat zurück"""

        return datetime.date(self.year, self.month, 1).strftime("%B %Y")

    def fill_grid_with_days(self):
        """Füllt das Grid mit den Tagen des Monats"""

        self.grid.clear_widgets()
        cal = calendar.Calendar(firstweekday=0)
        month_days = list(cal.itermonthdates(self.year, self.month))

        for day in month_days:
            in_month = (day.month == self.month)

            cell = DayCell(day.day, in_month=in_month)
            cell.bind(
                on_touch_down=lambda instance, touch, d=day: self.on_day_selected(d) 
                if instance.collide_point(*touch.pos) and touch.button == "left" else None
            )
            self.grid.add_widget(cell)

    def aligned_label(self, **kwargs):
        """Hilfsfunktion für Labels mit Textausrichtung"""

        lbl = Label(**kwargs)
        lbl.bind(size=lbl.setter("text_size"))
        return lbl
    
    def on_day_selected(self, date):
        """Wird aufgerufen, wenn ein Tag angeklickt wurde"""

        self.date_label.text = date.strftime("%d.%m.%Y")
        self.times_box.clear_widgets()

        if hasattr(self, "day_selected_callback"):
            self.day_selected_callback(date)

    def open_edit_popup(self, date):
        """Popup zum Bearbeiten öffnen"""

        popup_layout = BoxLayout(orientation="vertical", padding=10, spacing=10)

        # Header
        header_row = BoxLayout(size_hint_y=None, height=30, spacing=15)
        header_row.add_widget(Label(text="Von:", size_hint=(None, None), size=(80, 30), 
                                    text_size=(80, 30), halign="left", valign="middle"))
        header_row.add_widget(Label(text="Bis:", size_hint=(None, None), size=(80, 30), 
                                    text_size=(80, 30), halign="left", valign="middle"))
        popup_layout.add_widget(header_row)

        # UI-Komponenten für die Zeiteinträge
        scroll = ScrollView(size_hint=(1, 1))
        self.entries_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=10)
        self.entries_box.bind(minimum_height=self.entries_box.setter('height'))
        scroll.add_widget(self.entries_box)
        popup_layout.add_widget(scroll)
 
        # Einträge hinzufügen
        self.add_btn = Button(text="+ neuer Eintrag", size_hint_y=None, height=40)
        popup_layout.add_widget(self.add_btn)

        # Speichern-Button
        self.save_btn = Button(text="Speichern", size_hint_y=None, height=40)
        popup_layout.add_widget(self.save_btn)

        # Popup erstellen und öffnen
        popup = Popup(title=f"Einträge für den {date.strftime('%d.%m.%Y')}", content=popup_layout, 
                      size_hint=(0.3, 0.6))
        popup.open()

        self.current_popup = self
        return self

    def add_entry(self, from_time="", to_time=""):
        """Fügt eine neue Zeile für einen Eintrag hinzu"""

        entry_row = BoxLayout(size_hint_y=None, height=30, spacing=15)
        from_input = TextInput(text=from_time, multiline=False, size_hint=(None, None), size=(80, 30))
        to_input = TextInput(text=to_time, multiline=False, size_hint=(None, None), size=(80, 30))
        delete_btn = MDIconButton(icon="delete")
        delete_wrapper = AnchorLayout(size_hint_x=None, width=50)
        delete_wrapper.add_widget(delete_btn)
        entry_row.add_widget(from_input)
        entry_row.add_widget(to_input)
        entry_row.add_widget(delete_wrapper)
        self.entries_box.add_widget(entry_row)

        return entry_row, delete_btn


class LinedGridLayout(GridLayout):
    '''GridLayout mit Linien zwischen den Zellen'''

    def __init__(self, **kwargs):
        '''Initialisiert das LinedGridLayout'''

        super().__init__(**kwargs)

        self.bind(size=self._update_background, pos=self._update_background)
        self.bind(size=self._update_lines, pos=self._update_lines)

    def _update_background(self, *args):
        """Hintergrundfarbe zeichnen"""

        self.canvas.before.clear()
        with self.canvas.before:
            Color(1, 1, 1, 1)  
            Rectangle(pos=self.pos, size=self.size)

    def _update_lines(self, *args):
        """Linien zwischen den Zellen zeichnen"""

        self.canvas.after.clear()

        with self.canvas.after:
            Color(0.7, 0.7, 0.7, 1)

            col_width = self.width / self.cols
            for i in range(1, self.cols):
                x = self.x + i * col_width
                Line(points=[x, self.y, x, self.top])

            if len(self.children) >= self.cols:
                first_row_widgets = self.children[-self.cols:]
                y = min(widget.y for widget in first_row_widgets) - 5
                Line(points=[self.x, y, self.x + self.width, y])


class DayCell(BoxLayout):
    '''Einzelne Zelle im Kalender für einen Tag'''

    def __init__(self, day_number, in_month=True):
        '''Initialisiert eine Zelle für einen Tag'''

        super().__init__(orientation="vertical", padding=2, spacing=2)
        self.size_hint_y = None
        self.height = 80

        # Hintergrund und Rahmen
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.rect = Rectangle(size=self.size, pos=self.pos)
            Color(0.7, 0.7, 0.7, 1)
            self.line = Line(rectangle=(self.x, self.y, self.width, self.height), width=1)

        self.bind(size=self._update_graphics, pos=self._update_graphics)

        # Tageszahl oben rechts
        if in_month:
            color = (0, 0, 0, 1)
        else:
            color = (0.7, 0.7, 0.7, 1)

        day_label = Label(
            text=str(day_number),
            halign="right",
            valign="top",
            color=color,
            size_hint_y=None,
            padding=(10, 30)
        )
        day_label.bind(size=day_label.setter("text_size"))
        self.add_widget(day_label)

        # Bereich für Einträge
        self.entries_box = BoxLayout(orientation="vertical", spacing=1)
        self.add_widget(self.entries_box)

    def _update_graphics(self, *args):
        """Aktualisiert die Hintergrundgrafik und den Rahmen"""

        self.rect.pos = self.pos
        self.rect.size = self.size
        self.line.rectangle = (self.x, self.y, self.width, self.height)

    def add_entry(self, entry_text):
        """Fügt einen Eintrag als Label hinzu"""

        lbl = Label(
            text=entry_text,
            color=(0, 0, 0, 1),
            size_hint_y=None,
            height=20
        )
        with lbl.canvas.before:
            rect = Rectangle(size=lbl.size, pos=lbl.pos)

        def update_background(*args):
            """Aktualisiert die Hintergrundrechteckgröße und -position"""

            rect.pos = lbl.pos
            rect.size = lbl.size

        lbl.bind(size=update_background, pos=update_background)
        self.entries_box.add_widget(lbl)
