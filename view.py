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
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, Line, Ellipse, RoundedRectangle
from kivy.uix.image import Image
from kivy.uix.checkbox import CheckBox
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.metrics import sp

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

        self.layout = BoxLayout(orientation="vertical", padding=dp(24), spacing=dp(8))

        # Horizontaler Bereich für Logo und Überschrift
        top_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(64))
        title = Label(text="Anmeldung", font_size=sp(20), valign="middle", halign="left")
        title.bind(size=title.setter("text_size"))
        logo = Image(source="velqor.png", size_hint=(None, None), size=(dp(77), dp(77)))
        top_row.add_widget(title)
        top_row.add_widget(logo)

        self.layout.add_widget(top_row)

        self.username_input = TabTextInput(multiline=False, hint_text="Benutzername", 
                                           size_hint_y=None, height=dp(28))
        self.password_input = TabTextInput(password=True, multiline=False, hint_text="Passwort", 
                                           size_hint_y=None, height=dp(28))

        self.anmeldung_rückmeldung_label = Label(text="", color=(1, 0, 0))
        self.layout.add_widget(self.username_input)
        self.layout.add_widget(self.password_input)
        self.layout.add_widget(self.anmeldung_rückmeldung_label)

        button_layout = BoxLayout(spacing=dp(8))
        self.login_button = Button(text="Login", size_hint=(None, None), size=(dp(132), dp(32)), font_size=sp(16))
        self.change_view_registrieren_button = Button(text="Registrieren", size_hint=(None, None), 
                                                      size=(dp(132), dp(32)), font_size=sp(16))
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
        self.layout = BoxLayout(orientation="vertical", padding=dp(24), spacing=dp(16))

        # Überschrift 
        self.layout.add_widget(Label(text="Registrieren", font_size=sp(20), size_hint_y=None, height=dp(16)))

        grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None, height=dp(192))
        grid.bind(minimum_height=grid.setter('height'))
        
        # Eingabefelder
        self.reg_username_input = TabTextInput(
            multiline=False,
            hint_text="Vor- und Nachname",
            size_hint_y=None,
            height=dp(28)
        )
        self.reg_password_input = TabTextInput(
            password=True,
            multiline=False,
            hint_text="Passwort",
            size_hint_y=None,
            height=dp(28)
        )
        self.reg_password_input_rep = TabTextInput(
            password=True,
            multiline=False,
            hint_text="Passwort wiederholen",
            size_hint_y=None,
            height=dp(28)
        )
        self.reg_woechentliche_arbeitszeit = Spinner(
            text="Wöchentliche Arbeitszeit wählen",
            values=("30", "35", "40"),  # muss String sein
            size_hint_y=None,
            height=dp(32),
        )
        self.reg_geburtsdatum = TabTextInput(
            hint_text="TT/MM/JJJJ",
            size_hint_y=None,
            readonly=True,
            multiline=False,
            height=dp(28)
        )
        self.reg_limit_green = TabTextInput(
            multiline=False,
            input_filter='int',
            hint_text="Grenzwert (Zahl)",
            size_hint_y=None,
            height=dp(28)
        )
        self.reg_limit_red = TabTextInput(
            multiline=False,
            input_filter='int',
            hint_text="Grenzwert (Zahl)",
            size_hint_y=None,
            height=dp(28)
        )
        self.reg_superior = TabTextInput(
            multiline=False,
            hint_text="Name des Vorgesetzten",
            size_hint_y=None,
            height=dp(28)
        )

        grid.add_widget(Label(
            text="Vor- und Nachname:", size_hint=(None, None), size=(dp(184), dp(28)), text_size=(dp(184), dp(28)),
            halign="left", valign="middle")
        )
        grid.add_widget(self.reg_username_input)
        grid.add_widget(Label(
            text="Passwort:", size_hint=(None, None), size=(dp(184), dp(28)), text_size=(dp(184), dp(28)),
            halign="left", valign="middle")
        )
        grid.add_widget(self.reg_password_input)
        grid.add_widget(Label(
            text="Passwort wiederholen:", size_hint=(None, None), size=(dp(184), dp(28)), text_size=(dp(184), dp(28)),
            halign="left", valign="middle")
        )
        grid.add_widget(self.reg_password_input_rep)
        grid.add_widget(Label(
            text="Wöchentliche Arbeitszeit:", size_hint=(None, None), size=(dp(184), dp(32)), text_size=(dp(184), dp(32)),
            halign="left", valign="middle")
        )
        grid.add_widget(self.reg_woechentliche_arbeitszeit)
        grid.add_widget(Label(
            text="Geburtsdatum:", size_hint=(None, None), size=(dp(184), dp(28)), text_size=(dp(184), dp(28)),
            halign="left", valign="middle")
        )
        grid.add_widget(self.reg_geburtsdatum)
        grid.add_widget(Label(
            text="Grenzwerte:", size_hint=(None, None), size=(dp(184), dp(28)), text_size=(dp(184), dp(28)),
            halign="left", valign="middle")
        )
        limit_layout = BoxLayout(spacing=dp(8))
        limit_layout.add_widget(Label(
            text="grün:", size_hint=(None, None), size=(dp(34), dp(28)), text_size=(dp(34), dp(28)),
            halign="right", valign="middle")
        )
        limit_layout.add_widget(self.reg_limit_green)
        
        limit_layout.add_widget(Label(
            text="rot:", size_hint=(None, None), size=(dp(24), dp(28)), text_size=(dp(24), dp(28)),
            halign="right", valign="middle")
        )
        limit_layout.add_widget(self.reg_limit_red)
        grid.add_widget(limit_layout)
        grid.add_widget(Label(
            text="Vorgesetzte/r:", size_hint=(None, None), size=(dp(184), dp(28)), text_size=(dp(184), dp(28)),
            halign="left", valign="middle")
        )
        grid.add_widget(self.reg_superior)
        
        self.layout.add_widget(grid)

        # Button und Labels unten hinzufügen
        button_layout = BoxLayout(spacing=dp(8))
        self.change_view_login_button = Button(text="Zurück zum Login", size_hint=(None, None), size=(dp(240), dp(40)), 
                                               font_size=sp(16))
        self.register_button = Button(text="Registrieren", size_hint=(None, None), size=(dp(240), dp(40)), font_size=sp(16))
        self.register_rückmeldung_label = Label(
            text="",
            font_size=sp(15),
            size_hint_y=None,
            height=dp(24),
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

    def __init__(self, **kwargs):
        """
        Initialisiert die Main-View.
        
        Erstellt alle Tabs und ihre Inhalte.
        
        Args:
            **kwargs: Keyword-Argumente für Screen
        """
        super().__init__(**kwargs)
        # Flags zur Synchronisation zwischen Anzeige-Labels und Eingabefeldern
        self._syncing_week_hours = False
        self._syncing_green_limit = False
        self._syncing_red_limit = False
        self.register_event_type('on_settings_value_selected')
        self.layout = TabbedPanel(do_default_tab=False, tab_width=dp(136))
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

        main_layout = BoxLayout(orientation='horizontal', padding=dp(16))

        # Hauptlayout vertikal
        self.time_tracking_layout = BoxLayout(orientation='vertical', spacing=dp(16), size_hint_y=None, height=dp(self.time_tracking_tab_height*0.8))
        self.time_tracking_layout.bind(minimum_height=self.time_tracking_layout.setter('height'))
        self.time_tracking_layout.pos_hint = {"top": 1}

        self.welcome_label = Label(
            size_hint=(None, None),
            size=(dp(480), dp(40)),
            text_size=(dp(480), dp(40)),
            halign="left",
            valign="top",
            font_size=sp(23)
        )
        self.time_tracking_layout.add_widget(self.welcome_label)

        # Stempeln
        self.reihe_1 = BoxLayout(orientation='horizontal', spacing=dp(12), size_hint_y=None, height=dp(32))

        self.stempel_button = Button(text="Stempeln", size_hint=(None, None), size=(dp(104), dp(32)))

        # Timer
        self.timer_label = MDLabel(
            text="00:00:00",
            size_hint_x=None,
            width=dp(305),
            halign="center",
            font_style="H5",
            bold=True,
            theme_text_color="Custom",
            text_color=(0, 1, 0, 1)
        )
        self.reihe_1.add_widget(self.stempel_button)
        self.reihe_1.add_widget(self.timer_label)
        self.time_tracking_layout.add_widget(self.reihe_1)

        # Gleitzeit
        self.reihe_2 = BoxLayout(orientation='horizontal', spacing=dp(12), size_hint_y=None, height=dp(40))

        self.anzeige_gleitzeit_text_label = Label(
            text="Aktuelle Gleitzeit:", size_hint=(None, None), size=(dp(128), dp(32)),
            text_size=(dp(128), dp(32)), halign="left", valign="bottom", font_size=sp(16)
        )
        self.anzeige_gleitzeit_wert_label = Label(
            text="", size_hint=(None, None), size=(dp(176), dp(32)),
            text_size=(dp(176), dp(32)), halign="left", valign="bottom", font_size=sp(16)
        )
        self.reihe_2.add_widget(self.anzeige_gleitzeit_text_label)
        self.reihe_2.add_widget(self.anzeige_gleitzeit_wert_label)
        self.time_tracking_layout.add_widget(self.reihe_2)

        # Anzeige der Gleitzeit
        flexible_time_header = Label(
            text="Kumulierte Gleitzeit",
            size_hint=(None, None),
            size=(dp(176), dp(24)),
            text_size=(dp(176), dp(24)),
            halign="left",
            valign="bottom",
            font_size=sp(16)
        )
        self.time_tracking_layout.add_widget(flexible_time_header)

        input_card = MDCard(
            orientation="vertical",
            padding=dp(20),
            spacing=dp(12),
            size_hint=(None, None),
            size=(dp(304), dp(176)),
            md_bg_color=(0.25, 0.25, 0.25, 1),
            radius=[10, 10, 10, 10]
        )

        flexible_time_grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None, height=dp(88))
        flexible_time_grid.add_widget(Label(
            text="Monat:",
            size_hint=(None, None),
            size=(dp(56), dp(24)),
            text_size=(dp(56), dp(24)),
            halign="left",
            valign="middle"
        ))
        self.flexible_time_month = BorderedLabel(
            size_hint=(None, None), size=(dp(110), dp(24)), text_size=(dp(94), dp(24)), halign="right", valign="middle"
        )
        flexible_time_grid.add_widget(self.flexible_time_month)
        flexible_time_grid.add_widget(Label(
            text="Quartal:",
            size_hint=(None, None),
            size=(dp(56), dp(24)),
            text_size=(dp(56), dp(24)),
            halign="left",
            valign="middle"
        ))
        self.flexible_time_quarter = BorderedLabel(
            size_hint=(None, None), size=(dp(110), dp(24)), text_size=(dp(94), dp(24)), halign="right", valign="middle"
        )
        flexible_time_grid.add_widget(self.flexible_time_quarter)
        flexible_time_grid.add_widget(Label(
            text="Jahr:",
            size_hint=(None, None),
            size=(dp(56), dp(24)),
            text_size=(dp(56), dp(24)),
            halign="left",
            valign="middle"
        ))
        self.flexible_time_year = BorderedLabel(
            size_hint=(None, None), size=(dp(110), dp(24)), text_size=(dp(94), dp(24)), halign="right", valign="middle"
        )
        flexible_time_grid.add_widget(self.flexible_time_year)
        input_card.add_widget(flexible_time_grid)

        # Zeile mit Checkbox und Label nebeneinander
        checkbox_row = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(32))

        self.checkbox = CheckBox(size_hint=(None, None), size=(dp(24), dp(24)), active=False)
        checkbox_row.add_widget(self.checkbox)

        checkbox_row.add_widget(Label(
            text="Tage ohne Stempel berücksichtigen",
            size_hint=(None, None),
            size=(dp(240), dp(24)),
            text_size=(dp(240), dp(24)),
            halign="left",
            valign="middle"
        ))

        input_card.add_widget(checkbox_row)
        self.time_tracking_layout.add_widget(input_card)

        # Vertikales Layout für Logo und Ampel
        widgets_layout = BoxLayout(orientation="vertical", spacing=dp(16), size_hint=(None, None), size=(dp(80), dp(self.time_tracking_tab_height*0.8)))
        widgets_layout.bind(minimum_height=widgets_layout.setter('height'))
        widgets_layout.pos_hint = {"right": 1, "top": 1}

        logo = Image(source="bbq.png", size_hint=(None, None), size=(dp(64), dp(64)))
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
        self.zeitnachtrag_layout = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12), 
                                             size_hint_y=None, height=dp(self.time_tracking_tab_height))
        self.zeitnachtrag_layout.bind(minimum_height=self.zeitnachtrag_layout.setter('height'))

        # Überschrift
        self.überschrift = Label(
            text="Manuelles Nachtragen von Zeitstempeln",
            size_hint=(1, None),
            height=dp(24),
            halign="left",
            valign="middle",
            font_size=sp(16)
        )
        self.überschrift.bind(size=self.überschrift.setter('text_size'))
        self.zeitnachtrag_layout.add_widget(self.überschrift)

        input_card = MDCard(
            orientation="vertical",
            padding=dp(20),
            spacing=dp(12),
            size_hint=(None, None),
            size=(dp(296), dp(212)),
            md_bg_color=(0.25, 0.25, 0.25, 1),
            radius=[10, 10, 10, 10]
        )

        # GridLayout für Datum, Uhrzeit und Art des Eintrags
        self.grid = GridLayout(cols=2, padding=(dp(0), dp(8), dp(0), dp(0)), spacing=dp(12), size_hint_y=None, height=dp(136))

        # Art des Eintrags (Zeitstempel/Urlaub/Krank)
        self.grid.add_widget(Label(text="Art des Eintrags: ", size_hint=(None, None), size=(dp(115), dp(32)),
                            text_size=(dp(115), dp(32)), halign="left", valign="middle"))
        
        self.eintrag_art_spinner = Spinner(
            text="Bitte wählen",
            values=("Zeitstempel", "Urlaub", "Krankheit"), # muss krankheit heisen, das der Kontroller die EIntragsart erkennt
            size_hint=(None, None),
            size=(dp(129), dp(32))
        )
        self.grid.add_widget(self.eintrag_art_spinner)

        # Datum
        self.grid.add_widget(Label(text="Datum: ", size_hint=(None, None), size=(dp(115), dp(28)),
                                text_size=(dp(115), dp(28)), halign="left", valign="middle"))
        self.date_input = TextInput(hint_text="TT/MM/JJJJ", size_hint=(None, None),
                                    size=(dp(129), dp(28)), readonly=True, multiline=False)
        self.grid.add_widget(self.date_input)

        # Uhrzeit (mit Label in separate Variablen für Opacity-Steuerung)
        self.time_label = Label(text="Uhrzeit: ", size_hint=(None, None), size=(dp(115), dp(28)),
                                text_size=(dp(115), dp(28)), halign="left", valign="middle")
        self.grid.add_widget(self.time_label)
        self.time_input = TextInput(hint_text="HH:MM", size_hint=(None, None),
                                    size=(dp(129), dp(28)), readonly=True, multiline=False)
        self.grid.add_widget(self.time_input)

        input_card.add_widget(self.grid)

        # Button zum Nachtragen
        self.nachtragen_button = Button(text="Eintrag speichern", size_hint=(None, None), size=(dp(256), dp(32)))
        input_card.add_widget(self.nachtragen_button)

        # Rückmeldung
        self.nachtrag_feedback = Label(text="", size_hint=(None, None), size=(dp(400), dp(48)),
                                    text_size=(dp(400), dp(48)), halign="left", valign="middle")

        self.zeitnachtrag_layout.add_widget(input_card)
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
        main_layout = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))

        # Scrollbarer Bereich
        scroll_view = ScrollView(size_hint=(1, 1))

        # GridLayout für Benachrichtigungen
        self.benachrichtigungen_grid = GridLayout(
            cols=1,
            spacing=dp(8),
            size_hint_y=None,
            padding=(dp(0), dp(8))
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
            padding=dp(8),
            size_hint_y=None,
            height=dp(64)
        )

        # Stilvolle Umrandung oder Hintergrund
        box.canvas.before.clear()
        with box.canvas.before:
            Color(0.15, 0.15, 0.2, 0.2)  # dezenter Hintergrund
            RoundedRectangle(pos=box.pos, size=box.size, radius=[8])
        box.bind(pos=lambda _, __: setattr(box.canvas.before.children[-1], 'pos', box.pos))
        box.bind(size=lambda _, __: setattr(box.canvas.before.children[-1], 'size', box.size))

        # Text der Benachrichtigung
        label_text = Label(
            text=text,
            font_size=sp(13),
            halign="left",
            valign="middle",
            text_size=(dp(480), None),
            size_hint_y=None
        )
        label_text.bind(texture_size=lambda _, s: setattr(label_text, 'height', s[1]))

        # Datum
        label_date = Label(
            text=f"[i]{datum}[/i]",
            markup=True,
            font_size=sp(11),
            color=(0.6, 0.6, 0.6, 1),
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=dp(16)
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

        self.settings_horizontal_layout = BoxLayout(
            orientation='horizontal',
        )

        # Passwort ändern Layout
        self.settings_layout = BoxLayout(
            orientation='vertical',
            padding=dp(16),
            spacing=dp(12),
            size_hint=(0.55, None)
        )
        self.settings_layout.bind(minimum_height=self.settings_layout.setter('height'))
        self.settings_layout.pos_hint = {"top": 1}

        password_label = Label(
            text="Passwort ändern",
            size_hint=(1, None),
            height=dp(24),
            halign="left",
            valign="middle",
            font_size=sp(16)
        )
        password_label.bind(size=password_label.setter('text_size'))
        self.settings_layout.add_widget(password_label)

        right_card = MDCard(
            orientation="vertical",
            padding=dp(20),
            spacing=dp(12),
            size_hint=(None, None),
            size=(dp(280), dp(152)),
            md_bg_color=(0.25, 0.25, 0.25, 1),
            radius=[10, 10, 10, 10]
        )

        self.new_password_input = TabTextInput(
            password=True,
            hint_text="Neues Passwort",
            size_hint=(None, None),
            size=(dp(240), dp(28))
        )
        right_card.add_widget(self.new_password_input)

        self.repeat_password_input = TabTextInput(
            password=True,
            hint_text="Neues Passwort wiederholen",
            size_hint=(None, None),
            size=(dp(240), dp(28))
        )
        right_card.add_widget(self.repeat_password_input)

        self.change_password_button = Button(
            text="Passwort ändern",
            size_hint=(None, None),
            size=(dp(240), dp(32))
        )
        right_card.add_widget(self.change_password_button)

        self.settings_layout.add_widget(right_card)

        self.change_password_feedback = Label(
            text="",
            size_hint=(None, None),
            size=(dp(400), dp(48)),
            text_size=(dp(400), None),
            halign="left",
            valign="middle"
        )
        self.settings_layout.add_widget(self.change_password_feedback)

        # Allgemeine Einstellungen Layout
        self.settings_layout_left = BoxLayout(
            orientation='vertical',
            padding=dp(16),
            spacing=dp(12),
            size_hint=(0.45, None)
        )
        self.settings_layout_left.bind(
            minimum_height=self.settings_layout_left.setter('height')
        )
        self.settings_layout_left.pos_hint = {"top": 1}

        settings_label = Label(
            text="Allgemeine Einstellungen",
            size_hint=(1, None),
            height=dp(24),
            halign="left",
            valign="middle",
            font_size=sp(16)
        )
        settings_label.bind(size=settings_label.setter('text_size'))
        self.settings_layout_left.add_widget(settings_label)

        left_card = MDCard(
            orientation="vertical",
            padding=dp(20),
            spacing=dp(16),
            size_hint=(1, None),
            md_bg_color=(0.25, 0.25, 0.25, 1),
            radius=[10, 10, 10, 10]
        )
        left_card.bind(minimum_height=left_card.setter('height'))

        info_grid = GridLayout(cols=1, spacing=dp(12), size_hint=(1, None), width=dp(320))
        info_grid.bind(minimum_height=info_grid.setter('height'))

        def _info_row(caption, value, button_text=None, button_attr=None):
            row = BoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                height=dp(32),
                spacing=dp(8)
            )
            caption_lbl = Label(
                text=caption,
                size_hint=(0.6, 1),
                halign="left",
                valign="middle",
                text_size=(None, dp(32)),
                font_size=sp(14)
            )
            caption_lbl.bind(
                size=lambda inst, _: setattr(inst, 'text_size', (inst.width, dp(32)))
            )
            value_lbl = Label(
                text=value,
                size_hint=(0.25, 1),
                halign="left",
                valign="middle",
                text_size=(None, dp(32)),
                font_size=sp(14)
            )
            value_lbl.bind(
                size=lambda inst, _: setattr(inst, 'text_size', (inst.width, dp(32)))
            )
            row.add_widget(caption_lbl)
            row.add_widget(value_lbl)
            if button_text:
                btn = MDIconButton(
                    icon="pencil",
                    theme_text_color="Custom",
                    text_color=(1, 1, 1, 1)
                )
                setattr(self, button_attr, btn)
                btn_container = AnchorLayout(size_hint=(None, 1), width=dp(40))
                btn_container.add_widget(btn)
                row.add_widget(btn_container)
            return row, value_lbl

        self.name_row, self.name_value_label = _info_row("Name:", "")
        info_grid.add_widget(self.name_row)

        self.birth_row, self.birth_value_label = _info_row("Geburtsdatum:", "")
        info_grid.add_widget(self.birth_row)

        self.week_hours_row, self.week_hours_value_label = _info_row(
            "Vertragliche Wochenstunden:", "", button_text="Bearbeiten", button_attr="edit_week_hours_button"
        )
        info_grid.add_widget(self.week_hours_row)

        self.green_limit_row, self.green_limit_value_label = _info_row(
            "Ampel grün (h):", "", button_text="Bearbeiten", button_attr="edit_green_limit_button"
        )
        info_grid.add_widget(self.green_limit_row)

        self.red_limit_row, self.red_limit_value_label = _info_row(
            "Ampel rot (h):", "", button_text="Bearbeiten", button_attr="edit_red_limit_button"
        )
        info_grid.add_widget(self.red_limit_row)

        left_card.add_widget(info_grid)

        self.save_settings_button = Button(
            text="Änderungen speichern",
            size_hint=(1, None),
            height=dp(32)
        )
        left_card.add_widget(self.save_settings_button)

        self.settings_layout_left.add_widget(left_card)

        self.settings_horizontal_layout.add_widget(self.settings_layout_left)
        self.settings_horizontal_layout.add_widget(self.settings_layout)

        self.settings_tab.add_widget(self.settings_horizontal_layout)
        self.layout.add_widget(self.settings_tab)

       
    def show_messagebox(self, title, message, callback_yes=None, callback_no=None, yes_text="OK", no_text=None):
        """
        Zeigt eine Messagebox mit optionalen Buttons.
        
        Args:
            title: Titel des Popups
            message: Nachricht
            callback_yes: Callback für "Ja/OK/Fortfahren"-Button
            callback_no: Callback für "Nein/Abbrechen"-Button (optional)
            yes_text: Text für den Ja-Button (Standard: "OK")
            no_text: Text für den Nein-Button (optional, wenn None wird nur ein Button angezeigt)
        """
        layout = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(12))

        # Label mit Umbruch
        message_label = Label(
            text=message,
            halign="left",
            valign="middle",
            size_hint=(1, None),
            text_size=(dp(430), None)
        )
        message_label.bind(
            texture_size=lambda instance, value: setattr(instance, 'height', value[1])
        )
        layout.add_widget(message_label)

        # Button-Layout
        button_layout = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(32))

        popup = Popup(
            title=title,
            content=layout,
            size_hint=(None, None),
            size=(dp(470), dp(160)),
            auto_dismiss=False
        )

        if no_text:
            # Zwei Buttons: Abbrechen und Fortfahren
            no_button = Button(text=no_text, size_hint=(0.5, 1))
            yes_button = Button(text=yes_text, size_hint=(0.5, 1))
            
            def on_no(*args):
                popup.dismiss()
                if callback_no:
                    callback_no()
            
            def on_yes(*args):
                popup.dismiss()
                if callback_yes:
                    callback_yes()
            
            no_button.bind(on_release=on_no)
            yes_button.bind(on_release=on_yes)
            
            button_layout.add_widget(no_button)
            button_layout.add_widget(yes_button)
        else:
            # Ein Button: OK
            ok_button = Button(text=yes_text, size_hint=(1, 1))
            
            def on_ok(*args):
                popup.dismiss()
                if callback_yes:
                    callback_yes()
            
            ok_button.bind(on_release=on_ok)
            button_layout.add_widget(ok_button)
        
        layout.add_widget(button_layout)

        def adjust_popup_height(*args):
            # Höhe anpassen
            popup.height = message_label.height + dp(120)

        message_label.bind(height=adjust_popup_height)
        popup.open()

    def open_settings_edit_popup(self, field_label, current_value="", label_attr=None):
        """Zeigt ein Bearbeitungs-Popup für Einstellungen an."""

        popup_layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(12))

        headline = Label(
            text=f"{field_label}",
            size_hint_y=None,
            height=dp(24),
            halign="left",
            valign="middle"
        )
        headline.bind(size=headline.setter("text_size"))
        popup_layout.add_widget(headline)

        selection_widget = None
        if label_attr == "week_hours_value_label":
            cleaned_value = str(current_value).strip() if current_value is not None else ""
            if cleaned_value.endswith("h"):
                cleaned_value = cleaned_value[:-1].strip()
            if cleaned_value not in {"30", "35", "40"}:
                cleaned_value = "40"
            selection_widget = Spinner(
                text=cleaned_value,
                values=("30", "35", "40"),
                size_hint_y=None,
                height=dp(32)
            )
        elif label_attr in {"green_limit_value_label", "red_limit_value_label"}:
            cleaned_value = str(current_value).strip() if current_value is not None else ""
            if cleaned_value.endswith("h"):
                cleaned_value = cleaned_value[:-1].strip()
            selection_widget = TabTextInput(
                text=cleaned_value,
                multiline=False,
                size_hint_y=None,
                height=dp(32),
                input_filter="int"
            )
        else:
            selection_widget = TabTextInput(
                text=str(current_value) if current_value is not None else "",
                multiline=False,
                size_hint_y=None,
                height=dp(32)
            )

        popup_layout.add_widget(selection_widget)

        button_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(32), spacing=dp(12))
        cancel_btn = Button(text="Abbrechen")
        save_btn = Button(text="Übernehmen")
        button_row.add_widget(cancel_btn)
        button_row.add_widget(save_btn)
        popup_layout.add_widget(button_row)

        popup = Popup(
            title="Wert bearbeiten",
            content=popup_layout,
            size_hint=(None, None),
            size=(dp(320), dp(200)),
            auto_dismiss=False
        )

        cancel_btn.bind(on_release=popup.dismiss)

        def _save_and_dispatch(*_):
            new_value = selection_widget.text.strip() if hasattr(selection_widget, 'text') and selection_widget.text else ""
            self.dispatch('on_settings_value_selected', field_label, new_value, label_attr)
            popup.dismiss()

        save_btn.bind(on_release=_save_and_dispatch)

        popup.open()

    def on_settings_value_selected(self, field_label, new_value, label_attr):
        if label_attr and hasattr(self, label_attr):
            if new_value:
                if label_attr == "week_hours_value_label":
                    display_value = f"{new_value} h"
                elif label_attr in {"green_limit_value_label", "red_limit_value_label"}:
                    display_value = f"{new_value} h"
                else:
                    display_value = new_value
            else:
                display_value = new_value
            getattr(self, label_attr).text = display_value

    def on_enter(self):
        """
        Wird aufgerufen, wenn der Main-Screen betreten wird.
        
        Konfiguriert die Tab-Navigation zwischen den Eingabefeldern.
        """
        focus_chain = [
            getattr(self, "day_off_input", None),
            getattr(self, "green_limit_input", None),
            getattr(self, "red_limit_input", None),
            getattr(self, "new_password_input", None),
            getattr(self, "repeat_password_input", None),
        ]

        widgets = [widget for widget in focus_chain if widget is not None]
        if len(widgets) < 2:
            return

        for idx, widget in enumerate(widgets):
            widget.focus_next = widgets[(idx + 1) % len(widgets)]

    def _update_week_hours_input(self, _instance, value):
        if not hasattr(self, "week_hours_spinner") or self._syncing_week_hours:
            return
        cleaned = (value or "").strip()
        if cleaned.endswith("h"):
            cleaned = cleaned[:-1].strip()
        target_text = cleaned if cleaned else "Bitte wählen"
        if self.week_hours_spinner.text == target_text:
            return
        self._syncing_week_hours = True
        try:
            self.week_hours_spinner.text = target_text
        finally:
            self._syncing_week_hours = False

    def _on_week_hours_spinner_change(self, _spinner, value):
        if self._syncing_week_hours:
            return
        numeric = value.strip()
        if not numeric:
            display_value = ""
        else:
            display_value = f"{numeric} h"
        if self.week_hours_value_label.text == display_value:
            return
        self._syncing_week_hours = True
        try:
            self.week_hours_value_label.text = display_value
        finally:
            self._syncing_week_hours = False

    def _update_green_limit_input(self, _instance, value):
        if not hasattr(self, "green_limit_input") or self._syncing_green_limit:
            return
        cleaned = (value or "").strip()
        if cleaned.endswith("h"):
            cleaned = cleaned[:-1].strip()
        if self.green_limit_input.text == cleaned:
            return
        self._syncing_green_limit = True
        try:
            self.green_limit_input.text = cleaned
        finally:
            self._syncing_green_limit = False

    def _on_green_limit_input_change(self, _instance, value):
        if self._syncing_green_limit:
            return
        cleaned = value.strip()
        display_value = f"{cleaned} h" if cleaned else ""
        if self.green_limit_value_label.text == display_value:
            return
        self._syncing_green_limit = True
        try:
            self.green_limit_value_label.text = display_value
        finally:
            self._syncing_green_limit = False

    def _update_red_limit_input(self, _instance, value):
        if not hasattr(self, "red_limit_input") or self._syncing_red_limit:
            return
        cleaned = (value or "").strip()
        if cleaned.endswith("h"):
            cleaned = cleaned[:-1].strip()
        if self.red_limit_input.text == cleaned:
            return
        self._syncing_red_limit = True
        try:
            self.red_limit_input.text = cleaned
        finally:
            self._syncing_red_limit = False

    def _on_red_limit_input_change(self, _instance, value):
        if self._syncing_red_limit:
            return
        cleaned = value.strip()
        display_value = f"{cleaned} h" if cleaned else ""
        if self.red_limit_value_label.text == display_value:
            return
        self._syncing_red_limit = True
        try:
            self.red_limit_value_label.text = display_value
        finally:
            self._syncing_red_limit = False


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
        self.size = (dp(48), dp(128))

        # Ampel-Kreise
        with self.canvas:
            # Rot
            color_red = Color(0.3, 0.3, 0.3)
            ellipse_red = Ellipse(pos=(self.x, self.y + dp(80)), size=(dp(32), dp(32)))
            # Gelb
            color_yellow = Color(0.3, 0.3, 0.3)
            ellipse_yellow = Ellipse(pos=(self.x, self.y + dp(40)), size=(dp(32), dp(32)))
            # Grün
            color_green = Color(0.3, 0.3, 0.3)
            ellipse_green = Ellipse(pos=(self.x, self.y), size=(dp(32), dp(32)))

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
            self.lights[color][1].pos = (self.x, self.y + i * dp(40))

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
        self.urlaubstage = []  # Liste der Urlaubstage für den aktuellen Monat
        self.krankheitstage = []  # Liste der Krankheitstage für den aktuellen Monat
        self.controller = None  # Wird vom Controller gesetzt

        self.build_ui()

    def build_ui(self):
        """
        Erstellt die UI-Komponenten des Kalenders.
        
        Baut das komplette Layout mit Mitarbeiter-Auswahl, Monatsnavigation,
        Kalendergrid und Detail-Tabelle auf.
        """

        self.clear_widgets()

        # Auswahl, welcher Mitarbeiter-Kalender angezeigt werden soll
        calendar_choice = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40), padding=dp(8))
        calendar_choice.add_widget(Label(text="Kalenderansicht:", size_hint=(None, None), size=(dp(120), dp(24)), 
                                   text_size=(dp(120), dp(24)), halign="left", valign="middle"))
        self.employee_spinner = Spinner(size_hint=(None, None), size=(dp(160), dp(24)))
        calendar_choice.add_widget(self.employee_spinner)
        self.add_widget(calendar_choice)

        # Header für den Kalender
        header = BoxLayout(size_hint_y=None, height=dp(24))
        self.prev_btn = Button(text="<<", size_hint_x=None, width=dp(48))
        self.next_btn = Button(text=">>", size_hint_x=None, width=dp(48))
        self.title_label = Label(text=self.title_text())
        header.add_widget(self.prev_btn)
        header.add_widget(self.title_label)
        header.add_widget(self.next_btn)
        self.add_widget(header)

        # Wochentage
        weekdays = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        weekday_row = GridLayout(cols=7, padding=(dp(0), dp(8), dp(0), dp(0)), size_hint_y=None, height=dp(24))
        for weekday in weekdays:
            weekday_row.add_widget(Label(text=weekday, color=(1, 1, 1, 1)))
        self.add_widget(weekday_row)

        # Grid für Kalender
        self.grid = GridLayout(cols=7, padding=(dp(0), dp(8), dp(0), dp(0)))
        self.add_widget(self.grid)

        self.fill_grid_with_days()

        # Tabelle für die Anzeige der gestempelten Zeiten
        self.detail_table = LinedGridLayout(cols=3, size_hint_y=None, height=dp(120), padding=dp(8), spacing=dp(8))

        # Überschriften
        self.detail_table.add_widget(self.aligned_label(text="Datum", bold=True, color=(0, 0, 0, 1), 
                                                        size_hint_y=None, height=dp(16), halign="left", valign="top"))
        self.detail_table.add_widget(self.aligned_label(text="Zeiten", bold=True, color=(0, 0, 0, 1), 
                                                        size_hint_y=None, height=dp(16), halign="left", valign="top"))
        self.detail_table.add_widget(self.aligned_label(text="Gleitzeit", bold=True, color=(0, 0, 0, 1), 
                                                        size_hint_y=None, height=dp(16), halign="left", valign="top"))

        # Inhalte
        self.date_label = self.aligned_label(text="", color=(0, 0, 0, 1), halign="left", valign="top")

        self.times_scroll = ScrollView(size_hint=(1, 1), bar_width=dp(8), bar_color=(0.7, 0.7, 0.7, 1))
        self.times_box = GridLayout(cols=1, size_hint_y=None, spacing=dp(4))
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
            is_vacation = day in self.urlaubstage  # Prüfen ob Urlaubstag
            is_sick = day in self.krankheitstage  # Prüfen ob Krankheitstag

            self.cell = DayCell(day.day, in_month, is_weekend, is_holiday, is_vacation, is_sick)
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

    def add_time_row(self, stempelzeit: str, is_problematic, stempel_id: int, date_str: str, allow_edit: bool = True, gleitzeit_text: str = ""):
        """
        Fügt eine Zeile mit einer Stempelzeit zur Detail-Tabelle hinzu.
        
        Args:
            stempelzeit (str): Formatierte Stempelzeit (z.B. "08:30")
            is_problematic (bool): Ob der Eintrag problematisch ist
            stempel_id (int): ID des Zeiteintrags in der Datenbank
            date_str (str): Datum als String (Format: "dd.mm.yyyy")
            allow_edit (bool): Ob Bearbeiten-/Löschen-Buttons angezeigt werden sollen
            gleitzeit_text (str): Formatierte Gleitzeit für den Tag
        """

        # Layout für eine Zeile (Zeit + optional Buttons)
        row_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(24), spacing=dp(8))


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
        edit_button = MDIconButton(
            icon="pencil", 
            theme_text_color="Custom",
            text_color=(0, 0, 0, 1)
        )
        # Button-Event binden: Ruft open_edit_popup mit stempel_id, date_str und aktueller Zeit auf
        edit_button.bind(on_release=lambda btn: self.open_edit_popup(stempel_id, date_str, stempelzeit))
        edit_wrapper = AnchorLayout(size_hint_x=None, width=dp(40))
        edit_wrapper.add_widget(edit_button)



        delete_button = MDIconButton(
            icon="delete",
            theme_text_color="Custom",
            text_color=(0, 0, 0, 1)
        )
        # Button-Event binden: Ruft open_delete_popup mit stempel_id und date_str auf
        delete_button.bind(on_release=lambda btn: self.open_delete_popup(stempel_id, date_str, stempelzeit))
        delete_wrapper = AnchorLayout(size_hint_x=None, width=dp(40))
        delete_wrapper.add_widget(delete_button)

        row_layout.add_widget(times_label)
        if allow_edit:
            row_layout.add_widget(edit_wrapper)
            row_layout.add_widget(delete_wrapper)

        # Die ganze Zeile (Layout) zur times_box hinzufügen
        self.times_box.add_widget(row_layout)

        if gleitzeit_text:
            self.flexible_time_label.text = gleitzeit_text


    def open_edit_popup(self, stempel_id: int, date_str: str, time_str: str):
        """
        Öffnet ein Popup zum Bearbeiten von Zeiteinträgen.
        
        Args:
            stempel_id (int): ID des Zeiteintrags in der Datenbank
            date_str (str): Datum als String (Format: "dd.mm.yyyy")
            time_str (str): Aktuelle Zeit als String (Format: "HH:MM")
        """

        popup_layout = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(16))

        # Header
        header_row = BoxLayout(size_hint_y=None, height=dp(32), spacing=dp(12))
        header_row.add_widget(Label(text="Zeitstempel:", size_hint=(None, None), size=(dp(80), dp(28)), 
                                    text_size=(dp(80), dp(28)), halign="left", valign="middle"))
        time_input = TextInput(text=time_str, multiline=False, size_hint=(None, None), size=(dp(64), dp(28)), readonly=True)
        
        # Time Picker binden
        def show_time_picker_for_edit(instance, value):
            if value:  # Nur wenn focused
                if hasattr(self, 'controller') and self.controller:
                    # Speichere Referenz zum Input-Feld im Controller
                    self.controller.active_time_input = time_input
                    self.controller.show_time_picker(instance, value)
        
        time_input.bind(focus=show_time_picker_for_edit)
        header_row.add_widget(time_input)
        popup_layout.add_widget(header_row)

        # Speichern-Button
        save_btn = Button(text="Speichern", size_hint_y=None, height=dp(32))
        
        # Popup erstellen
        popup = Popup(title=f"Stempel bearbeiten - {date_str}", content=popup_layout, 
                     size_hint=(None, None), size=(dp(200), dp(160)))
        
        # Speichern-Button-Event: Ruft Controller-Methode auf
        def on_save(*args):
            neue_zeit_str = time_input.text
            if hasattr(self, 'controller') and self.controller:
                self.controller.stempel_bearbeiten_button_clicked(stempel_id, neue_zeit_str)
            popup.dismiss()
        
        save_btn.bind(on_release=on_save)
        popup_layout.add_widget(save_btn)

        popup.open()


    def open_delete_popup(self, stempel_id: int, date_str: str, time_str: str):
        """
        Öffnet ein Popup zur Bestätigung des Löschens eines Zeiteintrags.
        
        Args:
            stempel_id (int): ID des Zeiteintrags in der Datenbank
            date_str (str): Datum als String (Format: "dd.mm.yyyy")
            time_str (str): Zeit als String (Format: "HH:MM")
        """
        nachricht = f"Zeitstempel löschen:\n\nDatum: {date_str}\nUhrzeit: {time_str}\n\nMöchten Sie diesen Stempel wirklich löschen?"
        
        def on_confirm():
            if hasattr(self, 'controller') and self.controller:
                self.controller.stempel_löschen_button_clicked(stempel_id)
        
        # MainView Messagebox verwenden (über parent-Hierarchie)
        main_view = None
        parent = self.parent
        while parent:
            if isinstance(parent, MainView):
                main_view = parent
                break
            parent = parent.parent
        
        if main_view:
            main_view.show_messagebox(
                title="Stempel löschen",
                message=nachricht,
                callback_yes=on_confirm,
                callback_no=None,
                yes_text="Löschen",
                no_text="Abbrechen"
            )


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
                y = min(widget.y for widget in first_row_widgets) - dp(4)
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

    def __init__(self, day_number, in_month, is_weekend, is_holiday, is_vacation=False, is_sick=False):
        """
        Initialisiert eine Kalender-Zelle für einen Tag.
        
        Args:
            day_number (int): Tageszahl
            in_month (bool): True wenn Tag im aktuellen Monat, False für Nachbar-Monate
            is_weekend (bool): True wenn Wochenende
            is_holiday (bool): True wenn Feiertag
            is_vacation (bool): True wenn Urlaubstag
            is_sick (bool): True wenn Krankheitstag
        """

        super().__init__(orientation="vertical", padding=dp(1.6), spacing=dp(1.6))
        self.size_hint_y = None
        self.height = dp(64)

        # Priorität der Hintergrundfarben: Feiertag > Wochenende > Normal
        if is_holiday:
            bg_color = (1, 0.8, 0.8, 1)  # Rosa für Feiertag
        elif is_weekend:
            bg_color = (0.9, 0.9, 0.9, 1)  # Grau für Wochenende
        else:
            bg_color = (1, 1, 1, 1)  # Weiß für normale Tage

        # Hintergrund und Rahmen
        with self.canvas.before:
            Color(*bg_color)
            self.rect = Rectangle(size=self.size, pos=self.pos)
            Color(0.7, 0.7, 0.7, 1)
            self.line = Line(rectangle=(self.x, self.y, self.width, self.height), width=dp(0.8))

        self.bind(size=self._update_graphics, pos=self._update_graphics)

        # Tageszahl oben rechts
        if in_month:
            color = (0, 0, 0, 1)
        else:
            color = (0.7, 0.7, 0.7, 1)

        day_container = FloatLayout(size_hint_y=None, height=dp(64))

        day_label = Label(
            text=str(day_number),
            halign="right",
            valign="top",
            color=color,
            size_hint=(None, None),
            size=(dp(35), dp(40))
        )
        day_label.bind(size=day_label.setter("text_size"))
        day_label.pos_hint = {"right": 1, "top": 1}

        day_container.add_widget(day_label)
        self.add_widget(day_container)

        # Bereich für Einträge
        self.entries_box = BoxLayout(orientation="vertical", spacing=dp(0.8))
        self.add_widget(self.entries_box)

        if is_sick:
            self.add_entry("Krank", (1, 0.9, 0.7, 1))
        elif is_vacation:
            self.add_entry("Urlaub", (0.8, 0.9, 1, 1))

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
            height=dp(16)
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
            self.border_line = Line(rectangle=(self.x, self.y, self.width, self.height), width=dp(0.8))

        # Aktualisieren, wenn sich etwas ändert
        self.bind(pos=self.update_graphics, size=self.update_graphics)

    def update_graphics(self, *args):
        """
        Aktualisiert Position, Größe und Rahmen.
        
        Args:
            *args: Event-Argumente
        """
        
        self.border_line.rectangle = (self.x, self.y, self.width, self.height)