"""
View-Modul für die BBQ Arbeitszeit-Erfassungssoftware.

Dieses Modul enthält alle GUI-Komponenten der Anwendung, entwickelt mit Kivy/KivyMD.
Es implementiert die verschiedenen Screens und UI-Elemente:

- LoginView: Anmeldebildschirm
- RegisterView: Registrierungsbildschirm
- MainView: Hauptansicht mit Tabs für Zeiterfassung, Kalender, Benachrichtigungen, Einstellungen
- Hilfsklassen: TrafficLight (Ampel), MonthCalendar (Kalenderansicht), custom UI-Elemente

Die Views folgen dem MVC-Pattern und kommunizieren mit dem Controller.
"""

import datetime
import calendar
import time
import holidays

from datetime import datetime as dt, time as dt_time
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
from kivy.uix.image import Image
from kivy.uix.checkbox import CheckBox
from kivymd.uix.label import MDLabel
from kivy.clock import Clock

from window_size import set_fixed_window_size


class LoginView(Screen):
    """
    Anmelde-Screen der Anwendung.
    
    Zeigt Eingabefelder für Benutzername und Passwort sowie
    Buttons für Login und Wechsel zur Registrierung.
    
    Attributes:
        width_window (int): Breite des Fensters
        height_window (int): Höhe des Fensters
        username_input (TabTextInput): Eingabefeld für Benutzername
        password_input (TabTextInput): Eingabefeld für Passwort
        anmeldung_rückmeldung_label (Label): Feedback-Label für Login
        login_button (Button): Login-Button
        change_view_registrieren_button (Button): Button zum Wechsel zur Registrierung
    """

    def __init__(self, **kwargs):
        """
        Initialisiert die Login-View.
        
        Erstellt das Layout mit Logo, Eingabefeldern und Buttons.
        
        Args:
            **kwargs: Keyword-Argumente für Screen
        """
        super().__init__(**kwargs)
        self.width_window = 320
        self.height_window = 270
        set_fixed_window_size((self.width_window, self.height_window))

        self.layout = BoxLayout(orientation="vertical", padding=30, spacing=10)

        # Horizontaler Bereich für Logo und Überschrift
        top_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=80)
        title = Label(text="Anmeldung", font_size=24, valign="middle", halign="left")
        title.bind(size=title.setter("text_size"))
        logo = Image(source="velqor.png", size_hint=(None, None), size=(90, 90))
        top_row.add_widget(title)
        top_row.add_widget(logo)

        self.layout.add_widget(top_row)

        self.username_input = TabTextInput(multiline=False, hint_text="Benutzername", 
                                           size_hint_y=None, height=35)
        self.password_input = TabTextInput(password=True, multiline=False, hint_text="Passwort", 
                                           size_hint_y=None, height=35)

        self.anmeldung_rückmeldung_label = Label(text="", color=(1, 0, 0))
        self.layout.add_widget(self.username_input)
        self.layout.add_widget(self.password_input)
        self.layout.add_widget(self.anmeldung_rückmeldung_label)

        button_layout = BoxLayout(spacing=10)
        self.login_button = Button(text="Login", size_hint=(None, None), size=(165, 40), font_size=20)
        self.change_view_registrieren_button = Button(text="Registrieren", size_hint=(None, None), 
                                                      size=(165, 40), font_size=20)
        button_layout.add_widget(self.change_view_registrieren_button)
        button_layout.add_widget(self.login_button)
        self.layout.add_widget(button_layout)

        self.add_widget(self.layout)

    def on_enter(self):
        """
        Wird aufgerufen, wenn der Login-Screen betreten wird.
        
        Setzt den Fokus auf das Benutzername-Feld und konfiguriert
        die Tab-Navigation zwischen Eingabefeldern.
        """
        self.username_input.focus = True
        self.username_input.focus_next = self.password_input
        self.password_input.focus_next = self.username_input


class RegisterView(Screen):
    """
    Registrierungs-Screen der Anwendung.
    
    Zeigt Eingabefelder für alle notwendigen Daten zur Registrierung
    eines neuen Benutzers (Name, Passwort, Geburtsdatum, Arbeitszeit, etc.).
    
    Attributes:
        width_window (int): Breite des Fensters
        height_window (int): Höhe des Fensters
        date_picker (MDDatePicker): Datum-Picker für Geburtsdatum
        reg_*_input: Verschiedene Eingabefelder für Registrierungsdaten
        register_button (Button): Registrierungs-Button
        change_view_login_button (Button): Button zum Wechsel zum Login
    """

    def __init__(self, **kwargs):
        """
        Initialisiert die Register-View.
        
        Erstellt das Layout mit allen Registrierungs-Eingabefeldern
        und Buttons.
        
        Args:
            **kwargs: Keyword-Argumente für Screen
        """
        super().__init__(**kwargs)

        self.width_window = 535
        self.height_window = 430
        self.date_picker = MDDatePicker()

        # Hauptlayout (alles untereinander)
        self.layout = BoxLayout(orientation="vertical", padding=30, spacing=20)

        # Überschrift 
        self.layout.add_widget(Label(text="Registrieren", font_size=24, size_hint_y=None, height=20))

        grid = GridLayout(cols=2, spacing=10, size_hint_y=None, height=240)
        grid.bind(minimum_height=grid.setter('height'))
        
        # Eingabefelder
        self.reg_username_input = TabTextInput(
            multiline=False,
            hint_text="Vor- und Nachname",
            size_hint_y=None,
            height=35
        )
        self.reg_password_input = TabTextInput(
            password=True,
            multiline=False,
            hint_text="Passwort",
            size_hint_y=None,
            height=35
        )
        self.reg_password_input_rep = TabTextInput(
            password=True,
            multiline=False,
            hint_text="Passwort wiederholen",
            size_hint_y=None,
            height=35
        )
        self.reg_woechentliche_arbeitszeit = Spinner(
            text="Wöchentliche Arbeitszeit wählen",
            values=("30", "35", "40"),  # muss String sein
            size_hint_y=None,
            height=40,
        )
        self.reg_geburtsdatum = TabTextInput(
            hint_text="TT/MM/JJJJ",
            size_hint_y=None,
            readonly=True,
            multiline=False,
            height=35
        )
        self.reg_limit_green = TabTextInput(
            multiline=False,
            input_filter='int',
            hint_text="Grenzwert (Zahl)",
            size_hint_y=None,
            height=35
        )
        self.reg_limit_red = TabTextInput(
            multiline=False,
            input_filter='int',
            hint_text="Grenzwert (Zahl)",
            size_hint_y=None,
            height=35
        )
        self.reg_superior = TabTextInput(
            multiline=False,
            hint_text="Name des Vorgesetzten",
            size_hint_y=None,
            height=35
        )

        grid.add_widget(Label(
            text="Vor- und Nachname:", size_hint=(None, None), size=(230, 35), text_size=(230, 35),
            halign="left", valign="middle")
        )
        grid.add_widget(self.reg_username_input)
        grid.add_widget(Label(
            text="Passwort:", size_hint=(None, None), size=(230, 35), text_size=(230, 35),
            halign="left", valign="middle")
        )
        grid.add_widget(self.reg_password_input)
        grid.add_widget(Label(
            text="Passwort wiederholen:", size_hint=(None, None), size=(230, 35), text_size=(230, 35),
            halign="left", valign="middle")
        )
        grid.add_widget(self.reg_password_input_rep)
        grid.add_widget(Label(
            text="Wöchentliche Arbeitszeit:", size_hint=(None, None), size=(230, 40), text_size=(230, 40),
            halign="left", valign="middle")
        )
        grid.add_widget(self.reg_woechentliche_arbeitszeit)
        grid.add_widget(Label(
            text="Geburtsdatum:", size_hint=(None, None), size=(230, 35), text_size=(230, 35),
            halign="left", valign="middle")
        )
        grid.add_widget(self.reg_geburtsdatum)
        grid.add_widget(Label(
            text="Grenzwerte:", size_hint=(None, None), size=(230, 35), text_size=(230, 35),
            halign="left", valign="middle")
        )
        limit_layout = BoxLayout(spacing=10)
        limit_layout.add_widget(Label(
            text="grün:", size_hint=(None, None), size=(40, 35), text_size=(40, 35),
            halign="right", valign="middle")
        )
        limit_layout.add_widget(self.reg_limit_green)
        
        limit_layout.add_widget(Label(
            text="rot:", size_hint=(None, None), size=(30, 35), text_size=(30, 35),
            halign="right", valign="middle")
        )
        limit_layout.add_widget(self.reg_limit_red)
        grid.add_widget(limit_layout)
        grid.add_widget(Label(
            text="Vorgesetzte/r:", size_hint=(None, None), size=(230, 35), text_size=(230, 35),
            halign="left", valign="middle")
        )
        grid.add_widget(self.reg_superior)
        
        self.layout.add_widget(grid)

        # Button und Labels unten hinzufügen
        button_layout = BoxLayout(spacing=10)
        self.change_view_login_button = Button(text="Zurück zum Login", size_hint=(None, None), size=(300, 50), 
                                               font_size=20)
        self.register_button = Button(text="Registrieren", size_hint=(None, None), size=(300, 50), font_size=20)
        self.register_rückmeldung_label = Label(
            text="",
            font_size=18,
            size_hint_y=None,
            height=30,
            color=(1, 0, 0)
        )
        self.layout.add_widget(self.register_rückmeldung_label)
        button_layout.add_widget(self.change_view_login_button)
        button_layout.add_widget(self.register_button)
        self.layout.add_widget(button_layout)

        # Alles ins Screen packen
        self.add_widget(self.layout)

    def on_enter(self):
        """
        Wird aufgerufen, wenn der Registrierungs-Screen betreten wird.
        
        Setzt den Fokus und konfiguriert die Tab-Navigation zwischen
        den Eingabefeldern.
        """
        self.reg_username_input.focus = True
        self.reg_username_input.focus_next = self.reg_password_input
        self.reg_password_input.focus_next = self.reg_password_input_rep
        self.reg_password_input_rep.focus_next = self.reg_geburtsdatum
        self.reg_geburtsdatum.focus_next = self.reg_limit_green
        self.reg_limit_green.focus_next = self.reg_limit_red
        self.reg_limit_red.focus_next = self.reg_superior
        self.reg_superior.focus_next = self.reg_username_input


class MainView(Screen):
    """
    Hauptansicht der Anwendung mit Tabs.
    
    Enthält mehrere Tabs für verschiedene Funktionen:
    - Zeiterfassung: Stempeln, Gleitzeit-Anzeige, Ampel
    - Zeit nachtragen: Manuelles Hinzufügen von Zeitstempeln
    - Kalenderansicht: Monatlicher Überblick über Zeiteinträge
    - Benachrichtigungen: Warnungen und Hinweise
    - Einstellungen: Passwortänderung und Einstellungen
    
    Attributes:
        layout (TabbedPanel): Hauptlayout mit Tabs
        date_picker (MDDatePicker): Datum-Picker
        time_picker (MDTimePicker): Zeit-Picker
        time_tracking_tab_height/width (int): Fensterdimensionen
        stempel_button (Button): Button zum Stempeln
        nachtragen_button (Button): Button zum manuellen Nachtragen
        ampel (TrafficLight): Ampel-Widget zur Gleitzeit-Visualisierung
        month_calendar (MonthCalendar): Kalender-Widget
    """

    def __init__(self,  **kwargs):
        """
        Initialisiert die Main-View.
        
        Erstellt alle Tabs und ihre Inhalte.
        
        Args:
            **kwargs: Keyword-Argumente für Screen
        """
        super().__init__(**kwargs)
        self.layout = TabbedPanel(do_default_tab=False, tab_width=170)
        self.date_picker = MDDatePicker()
        self.time_picker = MDTimePicker()
        self.time_tracking_tab_height = 590
        self.time_tracking_tab_width = 800
        self.create_time_tracking_tab()
        self.create_zeitnachtrag_tab()
        self.create_calendar_tab()
        self.create_benachrichtigungen_tab()
        self.create_settings_tab()
        self.add_widget(self.layout)

    def create_time_tracking_tab(self):
        """
        Erstellt den Tab für die Zeiterfassung.
        
        Enthält Stempel-Button, Gleitzeit-Anzeige und Ampel-Widget.
        """

        self.time_tracking_tab = TabbedPanelItem(text="Zeiterfassung")

        main_layout = BoxLayout(orientation='horizontal', padding=20)

        # Hauptlayout vertikal
        self.time_tracking_layout = BoxLayout(orientation='vertical', spacing=20, size_hint_y=None, height=self.time_tracking_tab_height)
        self.time_tracking_layout.bind(minimum_height=self.time_tracking_layout.setter('height'))
        self.time_tracking_layout.pos_hint = {"top": 1}

        # Stempeln und Gleitzeit
        self.reihe_1 = BoxLayout(orientation='horizontal', spacing=15, size_hint_y=None, height=40)

        self.stempel_button = Button(text="Stempeln", size_hint=(None, None), size=(130, 40))


        # Timer
        self.timer_label = MDLabel(
            text="00:00:00",
            size_hint_x=None,
            width=180,
            halign="center",
            font_style="H5",
            bold=True
        )

        # Gleitzeit
        self.anzeige_gleitzeit_text_label = Label(
            text="Aktuelle Gleitzeit:", size_hint=(None, None), size=(170, 40),
            text_size=(170, 40), halign="right", valign="middle"
        )
        self.anzeige_gleitzeit_wert_label = Label(
            text="", size_hint=(None, None), size=(220, 40),
            text_size=(220, 40), halign="left", valign="middle"
        )

        self.reihe_1.add_widget(self.stempel_button)
        self.reihe_1.add_widget(self.timer_label)
        self.reihe_1.add_widget(self.anzeige_gleitzeit_text_label)
        self.reihe_1.add_widget(self.anzeige_gleitzeit_wert_label)
        self.time_tracking_layout.add_widget(self.reihe_1)

        # Anzeige der Gleitzeit
        flexible_time_header = Label(
            text="Kumulierte Gleitzeit",
            size_hint=(None, None),
            size=(220, 50),
            text_size=(220, 50),
            halign="left",
            valign="bottom",
            font_size=20
        )
        self.time_tracking_layout.add_widget(flexible_time_header)

        flexible_time_grid = GridLayout(cols=2, spacing=10, size_hint_y=None, height=110)
        flexible_time_grid.add_widget(Label(
            text="Monat:",
            size_hint=(None, None),
            size=(70, 30),
            text_size=(70, 30),
            halign="left",
            valign="middle"
        ))
        self.flexible_time_month = BorderedLabel(
            size_hint=(None, None), size=(100, 30), text_size=(80, 30), halign="right", valign="middle"
        )
        flexible_time_grid.add_widget(self.flexible_time_month)
        flexible_time_grid.add_widget(Label(
            text="Quartal:",
            size_hint=(None, None),
            size=(70, 30),
            text_size=(70, 30),
            halign="left",
            valign="middle"
        ))
        self.flexible_time_quarter = BorderedLabel(
            size_hint=(None, None), size=(100, 30), text_size=(80, 30), halign="right", valign="middle"
        )
        flexible_time_grid.add_widget(self.flexible_time_quarter)
        flexible_time_grid.add_widget(Label(
            text="Jahr:",
            size_hint=(None, None),
            size=(70, 30),
            text_size=(70, 30),
            halign="left",
            valign="middle"
        ))
        self.flexible_time_year = BorderedLabel(
            size_hint=(None, None), size=(100, 30), text_size=(80, 30), halign="right", valign="middle"
        )
        flexible_time_grid.add_widget(self.flexible_time_year)
        self.time_tracking_layout.add_widget(flexible_time_grid)

        # Zeile mit Checkbox und Label nebeneinander
        checkbox_row = BoxLayout(spacing=10, size_hint_y=None, height=40)

        self.checkbox = CheckBox(size_hint=(None, None), size=(30, 30), active=False)
        checkbox_row.add_widget(self.checkbox)

        checkbox_row.add_widget(Label(
            text="Tage ohne Stempel berücksichtigen",
            size_hint=(None, None),
            size=(300, 30),
            text_size=(300, 30),
            halign="left",
            valign="middle"
        ))

        self.time_tracking_layout.add_widget(checkbox_row)

        # Vertikales Layout für Logo und Ampel
        widgets_layout = BoxLayout(orientation="vertical", spacing=20, size_hint=(None, None), size=(100, self.time_tracking_tab_height))
        widgets_layout.bind(minimum_height=widgets_layout.setter('height'))
        widgets_layout.pos_hint = {"right": 1, "top": 1}

        logo = Image(source="bbq.png", size_hint=(None, None), size=(80, 80))
        logo.pos_hint = {"right": 1}
        widgets_layout.add_widget(logo)

        # Ampel
        self.ampel = TrafficLight()
        self.ampel.pos_hint = {"right": 1}
        widgets_layout.add_widget(self.ampel)

        main_layout.add_widget(self.time_tracking_layout)
        main_layout.add_widget(widgets_layout)

        # Tab zum TabbedPanel hinzufügen
        self.time_tracking_tab.add_widget(main_layout)
        self.layout.add_widget(self.time_tracking_tab)



    def create_zeitnachtrag_tab(self):
        """
        Erstellt den Tab für das manuelle Nachtragen von Zeitstempeln.
        
        Ermöglicht das Hinzufügen von Zeitstempeln mit gewähltem Datum und Uhrzeit
        sowie das Eintragen von Urlaub und Krankheit.
        """
        
        self.zeitnachtrag_tab = TabbedPanelItem(text="Zeit nachtragen")
        self.zeitnachtrag_layout = BoxLayout(orientation='vertical', padding=20, spacing=15, 
                                             size_hint_y=None, height=590)
        self.zeitnachtrag_layout.bind(minimum_height=self.zeitnachtrag_layout.setter('height'))

        # Überschrift
        self.überschrift = Label(
            text="Manuelles Nachtragen von Zeitstempeln",
            size_hint=(1, None),
            height=30,
            halign="left",
            valign="middle",
            font_size=20
        )
        self.überschrift.bind(size=self.überschrift.setter('text_size'))
        self.zeitnachtrag_layout.add_widget(self.überschrift)

        # GridLayout für Datum, Uhrzeit und Art des Eintrags
        self.grid = GridLayout(cols=2, padding=(0, 10, 0, 0), spacing=15, size_hint_y=None, height=180)

        # Art des Eintrags (Zeitstempel/Urlaub/Krank)
        self.grid.add_widget(Label(text="Art des Eintrags: ", size_hint=(None, None), size=(120, 40),
                            text_size=(120, 40), halign="left", valign="middle"))
        # In der bestehenden Methode, nach der Definition des Spinners:
        self.eintrag_art_spinner = Spinner(
            text="Bitte wählen",
            values=("Zeitstempel", "Urlaub", "Krank"),
            size_hint=(None, None),
            size=(300, 40)
        )
        self.grid.add_widget(self.eintrag_art_spinner)

        # Datum
        self.grid.add_widget(Label(text="Datum: ", size_hint=(None, None), size=(60, 40),
                            text_size=(60, 40), halign="left", valign="middle"))
        self.date_input = TextInput(hint_text="TT/MM/JJJJ", size_hint=(None, None),
                                size=(300, 40), readonly=True, multiline=False)
        self.grid.add_widget(self.date_input)

        # Uhrzeit (mit Label in separate Variablen für Opacity-Steuerung)
        self.time_label = Label(text="Uhrzeit: ", size_hint=(None, None), size=(60, 40),
                            text_size=(60, 40), halign="left", valign="middle")
        self.grid.add_widget(self.time_label)
        self.time_input = TextInput(hint_text="HH:MM", size_hint=(None, None),
                                size=(300, 40), readonly=True, multiline=False)
        self.grid.add_widget(self.time_input)

        # Button zum Nachtragen
        self.nachtragen_button = Button(text="Eintrag speichern", size_hint=(None, None), size=(220, 40))

        # Rückmeldung
        self.nachtrag_feedback = Label(text="", size_hint=(None, None), size=(500, 60),
                                    text_size=(500, 60), halign="left", valign="middle")

        self.zeitnachtrag_layout.add_widget(self.grid)
        self.zeitnachtrag_layout.add_widget(self.nachtragen_button)
        self.zeitnachtrag_layout.add_widget(self.nachtrag_feedback)

        self.zeitnachtrag_tab.add_widget(self.zeitnachtrag_layout)
        self.layout.add_widget(self.zeitnachtrag_tab)

    def create_calendar_tab(self):
        """
        Erstellt den Tab für die Kalenderansicht.
        
        Zeigt einen Monatskalender mit den Zeiteinträgen des Benutzers.
        """

        self.calendar_tab = TabbedPanelItem(text="Kalenderansicht")
        self.calendar_layout = BoxLayout(orientation="vertical")
        self.month_calendar = MonthCalendar()
        self.calendar_layout.add_widget(self.month_calendar)
        self.calendar_tab.add_widget(self.calendar_layout)
        self.layout.add_widget(self.calendar_tab)

    def create_benachrichtigungen_tab(self):
        """
        Erstellt den Tab für Benachrichtigungen.
        
        Zeigt Warnungen und Hinweise zu fehlenden Stempeln,
        ArbZG-Verstößen, etc.
        """

        self.benachrichtigungen_tab = TabbedPanelItem(text="Benachrichtigungen")

        # Hauptlayout
        main_layout = BoxLayout(orientation='vertical', padding=20, spacing=15)

        # Scrollbarer Bereich
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



        self.benachrichtigungen_tab.add_widget(main_layout)
        self.layout.add_widget(self.benachrichtigungen_tab)


    def add_benachrichtigung(self, text, datum):
        """
        Fügt eine einzelne Benachrichtigung zum Grid hinzu.
        
        Args:
            text (str): Text der Benachrichtigung
            datum: Datum der Benachrichtigung
        """

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
        """
        Erstellt den Tab für Einstellungen.
        
        Ermöglicht Passwortänderung und Anpassung von Einstellungen
        wie Wochenstunden und Ampel-Grenzwerte.
        """

        self.settings_tab = TabbedPanelItem(text="Einstellungen")

        self.settings_horizontal_layout = BoxLayout(orientation='horizontal')
        self.settings_layout = BoxLayout(orientation='vertical', padding=30, spacing=15, 
                                         size_hint=(0.5, None))
        self.settings_layout.bind(minimum_height=self.settings_layout.setter('height'))
        self.settings_layout.pos_hint = {"top": 1}

        self.settings_layout.add_widget(Label(text="Passwort ändern", font_size=18, 
                                              size_hint=(None, None), height=20, padding=(40,0,0,0)))
        self.new_password_input = TabTextInput(password=True, hint_text="Neues Passwort", 
                                            size_hint=(None, None), size=(300, 35))
        self.settings_layout.add_widget(self.new_password_input)
        self.repeat_password_input = TabTextInput(password=True, hint_text="Neues Passwort wiederholen", 
                                               size_hint=(None, None), size=(300, 35))
        self.settings_layout.add_widget(self.repeat_password_input)
        self.change_password_button = Button(text="Passwort ändern", size_hint=(None, None), 
                                             size=(180, 40))
        self.change_password_feedback = Label(text="", size_hint=(None, None), size=(500, 60),
                        text_size=(500, None), halign="left", valign="middle")
        self.settings_layout.add_widget(self.change_password_button)
        self.settings_layout.add_widget(self.change_password_feedback)

        self.grid = GridLayout(cols=2, padding=20, spacing=15, size_hint=(0.5, 1))
        self.grid.bind(minimum_height=self.grid.setter('height'))
        
        self.grid.add_widget(Label(text="Stundenwoche: ", font_size=18, size_hint=(None, None), 
                                   size=(160, 40), text_size=(160, 40), halign="left", valign="middle"))
        self.grid.add_widget(Spinner(text="Bitte wählen", values=("30 Stunden", "35 Stunden", "40 Stunden"), 
                                     size_hint=(None, None), size=(200, 40)))
        self.grid.add_widget(Label(text="Anzahl Urlaubstage: ", font_size=18, size_hint=(None, None), 
                                   size=(160, 35), text_size=(160, 35), halign="left", valign="middle"))
        self.day_off_input = TabTextInput(multiline=False, size_hint=(None, None), size=(200, 35), halign="right",
                                          input_filter='int')
        self.grid.add_widget(self.day_off_input)

        self.grid.add_widget(Label(text="Grenzwerte: ", font_size=18, size_hint=(None, None), size=(160, 35), 
                                   text_size=(160, 35), halign="left", valign="middle"))
        self.horizonatl_layout1 = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=40)
        self.horizonatl_layout1.add_widget(Label(text="grün: ", font_size=18, size_hint=(None, None), size=(40, 35), 
                                                 text_size=(40, 35), halign="left", valign="middle"))
        self.green_limit_input = TabTextInput(multiline=False, size_hint=(None, None), size=(150, 35), halign="right",
                                              input_filter='int')
        self.horizonatl_layout1.add_widget(self.green_limit_input)
        self.grid.add_widget(self.horizonatl_layout1)

        self.grid.add_widget(Label(size_hint=(None, None), size=(160, 40)))
        self.horizonatl_layout2 = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=40)
        self.horizonatl_layout2.add_widget(Label(text="gelb: ", font_size=18, size_hint=(None, None), size=(40, 35), 
                                                 text_size=(40, 35), halign="left", valign="middle"))
        self.yellow_limit_input = TabTextInput(multiline=False, size_hint=(None, None), size=(150, 35), halign="right",
                                               input_filter='int')
        self.horizonatl_layout2.add_widget(self.yellow_limit_input)
        self.grid.add_widget(self.horizonatl_layout2)

        self.grid.add_widget(Label(size_hint=(None, None), size=(160, 40)))
        self.horizonatl_layout3 = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=40)
        self.horizonatl_layout3.add_widget(Label(text="rot: ", font_size=18, size_hint=(None, None), size=(40, 35), 
                                                 text_size=(40, 35), halign="left", valign="middle"))
        self.red_limit_input = TabTextInput(multiline=False, size_hint=(None, None), size=(150, 35), halign="right",
                                            input_filter='int')
        self.horizonatl_layout3.add_widget(self.red_limit_input)
        self.grid.add_widget(self.horizonatl_layout3)

        self.settings_horizontal_layout.add_widget(self.grid)
        self.settings_horizontal_layout.add_widget(self.settings_layout)
        self.settings_tab.add_widget(self.settings_horizontal_layout)
        self.layout.add_widget(self.settings_tab)

    def show_messagebox(self, title, message):
        layout = BoxLayout(orientation="vertical", padding=10, spacing=15)

        # Label mit Umbruch
        message_label = Label(
            text=message,
            halign="left",
            valign="middle",
            size_hint=(1, None),
            text_size=(350, None)
        )
        message_label.bind(
            texture_size=lambda instance, value: setattr(instance, 'height', value[1])
        )
        layout.add_widget(message_label)

        close_button = Button(text="OK", size_hint_y=None, height=40)
        layout.add_widget(close_button)

        popup = Popup(
            title=title,
            content=layout,
            size_hint=(None, None),
            size=(400, 200),
            auto_dismiss=False
        )

        def adjust_popup_height(*args):
            # Höhe anpassen
            popup.height = message_label.height + 150

        message_label.bind(height=adjust_popup_height)

        close_button.bind(on_release=popup.dismiss)
        popup.open()

    def on_enter(self):
        """
        Wird aufgerufen, wenn der Main-Screen betreten wird.
        
        Konfiguriert die Tab-Navigation zwischen den Eingabefeldern.
        """
        self.day_off_input.focus_next = self.green_limit_input
        self.green_limit_input.focus_next = self.yellow_limit_input
        self.yellow_limit_input.focus_next = self.red_limit_input
        self.red_limit_input.focus_next = self.new_password_input
        self.new_password_input.focus_next = self.repeat_password_input
        self.repeat_password_input.focus_next = self.day_off_input


class TrafficLight(BoxLayout):
    """
    Ampel-Widget zur Visualisierung des Gleitzeitstatus.
    
    Zeigt eine grafische Ampel mit drei Zuständen:
    - Grün: Gleitzeit im positiven Bereich
    - Gelb: Gleitzeit im neutralen Bereich
    - Rot: Gleitzeit im negativen Bereich
    
    Attributes:
        lights (dict): Dictionary mit Farb- und Ellipsen-Objekten
    """

    def __init__(self):
        """
        Initialisiert die Ampel mit drei Kreisen (rot, gelb, grün).
        """

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
        """
        Aktualisiert die Positionen der Ampel-Kreise.
        
        Wird aufgerufen, wenn sich Position oder Größe des Widgets ändert.
        
        Args:
            *args: Kivy Event-Argumente
        """
        
        for i, color in enumerate(["green", "yellow", "red"]):
            self.lights[color][1].pos = (self.x, self.y + i * 50)

    def set_state(self, state):
        """
        Setzt die Ampel auf den angegebenen Zustand.
        
        Args:
            state (str): 'red', 'yellow' oder 'green'
        """

        for color, _ in self.lights.values():
            color.rgb = (0.3, 0.3, 0.3)

        if state == "red":
            self.lights["red"][0].rgb = (1, 0, 0)
        elif state == "yellow":
            self.lights["yellow"][0].rgb = (1, 1, 0)
        elif state == "green":
            self.lights["green"][0].rgb = (0, 1, 0)


class MonthCalendar(BoxLayout):
    """
    Kalender-Widget mit Monatsübersicht und Zeiteintrags-Anzeige.
    
    Zeigt einen Monatskalender an, in dem der Benutzer Tage auswählen
    und die Zeiteinträge für den jeweiligen Tag ansehen kann.
    
    Attributes:
        year (int): Aktuell angezeigtes Jahr
        month (int): Aktuell angezeigter Monat
        day_selected_callback: Callback-Funktion für Tages-Auswahl
        prev_btn/next_btn (Button): Navigation zwischen Monaten
        date_label (Label): Zeigt ausgewähltes Datum
        times_box (GridLayout): Container für Zeiteinträge
        edit_btn (MDIconButton): Button zum Bearbeiten von Einträgen
    """

    def __init__(self):
        """
        Initialisiert die Monatsansicht des Kalenders.
        
        Setzt das aktuelle Jahr und den aktuellen Monat.
        """
        
        super().__init__(orientation="vertical")
        today = datetime.date.today()
        self.year = today.year
        self.month = today.month

        self.build_ui()

    def build_ui(self):
        """
        Erstellt die UI-Komponenten des Kalenders.
        
        Baut das komplette Layout mit Mitarbeiter-Auswahl, Monatsnavigation,
        Kalendergrid und Detail-Tabelle auf.
        """

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
        self.detail_table = LinedGridLayout(cols=3, size_hint_y=None, height=150, padding=10, spacing=10)

        # Überschriften
        self.detail_table.add_widget(self.aligned_label(text="Datum", bold=True, color=(0, 0, 0, 1), 
                                                        size_hint_y=None, height=20, halign="left", valign="top"))
        self.detail_table.add_widget(self.aligned_label(text="Zeiten", bold=True, color=(0, 0, 0, 1), 
                                                        size_hint_y=None, height=20, halign="left", valign="top"))
        self.detail_table.add_widget(self.aligned_label(text="Gleitzeit", bold=True, color=(0, 0, 0, 1), 
                                                        size_hint_y=None, height=20, halign="left", valign="top"))

        # Inhalte
        self.date_label = self.aligned_label(text="", color=(0, 0, 0, 1), halign="left", valign="top")

        self.times_scroll = ScrollView(size_hint=(1, 1), bar_width=10, bar_color=(0.7, 0.7, 0.7, 1))
        self.times_box = GridLayout(cols=1, size_hint_y=None, spacing=5)
        self.times_box.bind(minimum_height=self.times_box.setter("height"))
        self.times_scroll.add_widget(self.times_box)

        self.flexible_time_label = self.aligned_label(text="", color=(0, 0, 0, 1), halign="left", valign="top")

        self.detail_table.add_widget(self.date_label)
        self.detail_table.add_widget(self.times_scroll)
        self.detail_table.add_widget(self.flexible_time_label)

        self.add_widget(self.detail_table)

    def change_month(self, delta):
        """
        Wechselt den angezeigten Monat.
        
        Args:
            delta (int): +1 für nächsten Monat, -1 für vorherigen Monat
        """

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
        """
        Gibt den Titel für den aktuellen Monat zurück.
        
        Returns:
            str: Monatsname und Jahr, z.B. "Januar 2024"
        """

        return datetime.date(self.year, self.month, 1).strftime("%B %Y")

    def fill_grid_with_days(self):
        """
        Füllt das Kalender-Grid mit den Tagen des Monats.
        
        Erstellt für jeden Tag eine DayCell und bindet Click-Events.
        """

        self.grid.clear_widgets()
        cal = calendar.Calendar(firstweekday=0)
        month_days = list(cal.itermonthdates(self.year, self.month))

        for day in month_days:
            in_month = (day.month == self.month)

            weekday = day.weekday()
            is_weekend = weekday >= 5
            is_holiday = self.is_holiday(day)

            self.cell = DayCell(day.day, in_month, is_weekend, is_holiday)
            self.cell.bind(
                on_touch_down=lambda instance, touch, d=day: self.on_day_selected(d) 
                if instance.collide_point(*touch.pos) and touch.button == "left" else None
            )
            self.grid.add_widget(self.cell)

    def aligned_label(self, **kwargs):
        """
        Hilfsfunktion zur Erstellung von Labels mit Textausrichtung.
        
        Args:
            **kwargs: Keyword-Argumente für Label
            
        Returns:
            Label: Konfiguriertes Label-Widget
        """

        lbl = Label(**kwargs)
        lbl.bind(size=lbl.setter("text_size"))
        return lbl
    
    def on_day_selected(self, date):
        """
        Wird aufgerufen, wenn ein Tag angeklickt wurde.
        
        Args:
            date (datetime.date): Ausgewähltes Datum
        """

        self.date_label.text = date.strftime("%d.%m.%Y")
        self.times_box.clear_widgets()

        if hasattr(self, "day_selected_callback"):
            self.day_selected_callback(date)

    def add_time_row(self, stempelzeit: str, is_problematic):
        """
        Fügt eine Zeile mit einer Stempelzeit zur Detail-Tabelle hinzu.
        
        Args:
            stempelzeit (str): Formatierte Stempelzeit (z.B. "08:30")
        """

        # Layout für eine Zeile (Zeit + Button)
        row_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=30, spacing=10)


        if is_problematic:
            label_color = (1, 0.8, 0.8, 1)
        else:
            label_color = (1, 1, 1, 1)

        # Gestempelte Zeit als Label
        times_label = self.aligned_label(
            text=stempelzeit,
            color=(0, 0, 0, 1),
            halign="left",
            valign="middle",
            size_hint_x=1  # Nimmt den restlichen Platz ein
        )

        with times_label.canvas.before:
            Color(*label_color)
            rect = Rectangle(size=times_label.size, pos=times_label.pos)

        # Größe & Position automatisch anpassen
        times_label.bind(size=lambda instance, value: setattr(rect, 'size', value))
        times_label.bind(pos=lambda instance, value: setattr(rect, 'pos', value))

        # Bearbeiten-Button
        self.edit_button = MDIconButton(
            icon="pencil", 
            theme_text_color="Custom",
            text_color=(0, 0, 0, 1)
        )
        edit_wrapper = AnchorLayout(size_hint_x=None, width=50)
        edit_wrapper.add_widget(self.edit_button)



        self.delete_button = MDIconButton(
            icon="delete",
            theme_text_color="Custom",
            text_color=(0, 0, 0, 1)
        )

        delete_wrapper = AnchorLayout(size_hint_x=None, width=50)
        delete_wrapper.add_widget(self.delete_button)

        row_layout.add_widget(times_label)
        row_layout.add_widget(edit_wrapper)
        row_layout.add_widget(delete_wrapper)

        # Die ganze Zeile (Layout) zur times_box hinzufügen
        self.times_box.add_widget(row_layout)


    def open_edit_popup(self, date, time):
        """
        Öffnet ein Popup zum Bearbeiten von Zeiteinträgen.
        
        Args:
            date (datetime.date): Datum, für das Einträge bearbeitet werden sollen
            
        Returns:
            self: Popup-Instanz für weitere Konfiguration
        """

        popup_layout = BoxLayout(orientation="vertical", padding=10, spacing=20)

        # Header
        header_row = BoxLayout(size_hint_y=None, height=40, spacing=15)
        header_row.add_widget(Label(text="Zeitstempel:", size_hint=(None, None), size=(100, 35), 
                                    text_size=(100, 35), halign="left", valign="middle"))
        self.time_input = TextInput(text=time, multiline=False, size_hint=(None, None), size=(80, 35), readonly=True)
        self.time_input.bind(focus=self.controller.show_time_picker)
        header_row.add_widget(self.time_input)
        popup_layout.add_widget(header_row)

        # Speichern-Button
        self.save_btn = Button(text="Speichern", size_hint_y=None, height=40)
        popup_layout.add_widget(self.save_btn)

        # Popup erstellen und öffnen
        popup = Popup(title=f"{date}", content=popup_layout, size_hint=(None, None), size=(250, 200))
        popup.open()

        self.current_popup = self
        return self

    def is_holiday(self, date):
        """Prüft, ob das gegebene Datum ein Feiertag ist"""

        de_holidays = holidays.Germany(years=[date.year])
        return date in de_holidays


class LinedGridLayout(GridLayout):
    """
    GridLayout mit visuellen Linien zwischen den Zellen.
    
    Zeichnet automatisch Hintergrund und Trennlinien für eine tabellarische
    Darstellung.
    """

    def __init__(self, **kwargs):
        """
        Initialisiert das LinedGridLayout.
        
        Args:
            **kwargs: Keyword-Argumente für GridLayout
        """

        super().__init__(**kwargs)

        self.bind(size=self._update_background, pos=self._update_background)
        self.bind(size=self._update_lines, pos=self._update_lines)

    def _update_background(self, *args):
        """
        Zeichnet die Hintergrundfarbe.
        
        Args:
            *args: Event-Argumente
        """

        self.canvas.before.clear()
        with self.canvas.before:
            Color(1, 1, 1, 1)  
            Rectangle(pos=self.pos, size=self.size)

    def _update_lines(self, *args):
        """
        Zeichnet die Trennlinien zwischen den Zellen.
        
        Args:
            *args: Event-Argumente
        """

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
    """
    Einzelne Kalender-Zelle für einen Tag.
    
    Zeigt die Tageszahl und kann Einträge für diesen Tag aufnehmen.
    
    Attributes:
        rect (Rectangle): Hintergrund-Rechteck
        line (Line): Rahmen der Zelle
        entries_box (BoxLayout): Container für Tag-Einträge
    """

    def __init__(self, day_number, in_month, is_weekend, is_holiday):
        """
        Initialisiert eine Kalender-Zelle für einen Tag.
        
        Args:
            day_number (int): Tageszahl
            in_month (bool): True wenn Tag im aktuellen Monat, False für Nachbar-Monate
        """

        super().__init__(orientation="vertical", padding=2, spacing=2)
        self.size_hint_y = None
        self.height = 80

        if is_weekend:
            bg_color = (0.9, 0.9, 0.9, 1)
        elif is_holiday:
            bg_color = (1, 0.8, 0.8, 1)
        else:
            bg_color = (1, 1, 1, 1)

        # Hintergrund und Rahmen
        with self.canvas.before:
            Color(*bg_color)
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
        """
        Aktualisiert die Hintergrundgrafik und den Rahmen.
        
        Args:
            *args: Event-Argumente
        """

        self.rect.pos = self.pos
        self.rect.size = self.size
        self.line.rectangle = (self.x, self.y, self.width, self.height)

    def add_entry(self, entry_text, color):
        """
        Fügt einen Eintrag als Label zur Zelle hinzu.
        
        Args:
            entry_text (str): Text des Eintrags
        """

        lbl = Label(
            text=entry_text,
            color=(0, 0, 0, 1),
            size_hint_y=None,
            height=20
        )
        with lbl.canvas.before:
            lbl.bg_color = Color(*color)
            rect = Rectangle(size=lbl.size, pos=lbl.pos)

        def update_background(*args):
            """
            Aktualisiert die Hintergrundrechteckgröße und -position.
            
            Args:
                *args: Event-Argumente
            """

            rect.pos = lbl.pos
            rect.size = lbl.size

        lbl.bind(size=update_background, pos=update_background)
        self.entries_box.add_widget(lbl)


class TabTextInput(TextInput):
    """
    TextInput-Feld mit Tab-Navigation.
    
    Erweitert TextInput um die Möglichkeit, mit der Tab-Taste zum
    nächsten Eingabefeld zu springen (statt Tab-Zeichen einzufügen).
    
    Attributes:
        focus_next: Nächstes Eingabefeld für Tab-Navigation
    """

    def __init__(self, **kwargs):
        """
        Initialisiert das TabTextInput-Feld.
        
        Args:
            **kwargs: Keyword-Argumente für TextInput
        """

        super().__init__(**kwargs)
        self.write_tab = False

    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        """
        Wird aufgerufen, wenn eine Taste gedrückt wird.
        
        Fängt die Tab-Taste ab und wechselt zum nächsten Eingabefeld.
        
        Args:
            window: Kivy Window
            keycode: Tuple mit (keycode, keyname)
            text: Eingegebener Text
            modifiers: Modifier-Tasten (Shift, Ctrl, etc.)
            
        Returns:
            bool: True wenn Event behandelt wurde
        """

        if keycode[1] == 'tab':
            if self.focus_next:
                self.focus_next.focus = True
            return True  # Event abfangen (kein Tab-Zeichen einfügen)
        return super().keyboard_on_key_down(window, keycode, text, modifiers)
    

class BorderedLabel(Label):
    """
    Label mit sichtbarem Rahmen.
    
    Erweitert das Standard-Label um einen gezeichneten Rahmen.
    
    Attributes:
        border_color (Color): Farbe des Rahmens
        border_line (Line): Line-Objekt für den Rahmen
    """

    def __init__(self, **kwargs):
        """
        Initialisiert das BorderedLabel.
        
        Args:
            **kwargs: Keyword-Argumente für Label
        """

        super().__init__(**kwargs)

        # Rand
        with self.canvas.after:
            self.border_color = Color(0.5, 0.5, 0.5, 1)
            self.border_line = Line(rectangle=(self.x, self.y, self.width, self.height), width=1)

        # Aktualisieren, wenn sich etwas ändert
        self.bind(pos=self.update_graphics, size=self.update_graphics)

    def update_graphics(self, *args):
        """
        Aktualisiert Position, Größe und Rahmen.
        
        Args:
            *args: Event-Argumente
        """
        
        self.border_line.rectangle = (self.x, self.y, self.width, self.height)