from kivy.uix.screenmanager import ScreenManager
from modell import ModellLogin, ModellTrackTime
from view import LoginView, RegisterView, MainView
from kivy.core.window import Window
from kivymd.uix.pickers import MDDatePicker, MDTimePicker
from datetime import datetime, date, time as datetime_time, timedelta
from window_size import set_fixed_window_size
from kivy.clock import Clock
import time
import logging
# Logger für dieses Modul
logger = logging.getLogger(__name__)
class Controller():
    def __init__(self):
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
            
            # Warnungs-Events für Arbeitsfenster und max. Arbeitszeit
            self.arbeitsfenster_warning_event = None
            self.max_arbeitszeit_warning_event = None
            
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

            self._bind_safe(
                self.main_view.edit_week_hours_button,
                'on_release',
                lambda *_: self.on_settings_edit_button("Vertragliche Wochenstunden", "week_hours_value_label")
            )
            self._bind_safe(
                self.main_view.edit_green_limit_button,
                'on_release',
                lambda *_: self.on_settings_edit_button("Ampel grün (h)", "green_limit_value_label")
            )
            self._bind_safe(
                self.main_view.edit_red_limit_button,
                'on_release',
                lambda *_: self.on_settings_edit_button("Ampel rot (h)", "red_limit_value_label")
            )
            self._bind_safe(
                self.main_view.save_settings_button,
                'on_release',
                self.save_settings_button_clicked
            )

            self.main_view.month_calendar.day_selected_callback = self.day_selected
            self.main_view.bind(on_settings_value_selected=self.on_settings_value_selected)

            # Controller-Referenz im MonthCalendar setzen für Edit/Delete-Callbacks
            self.main_view.month_calendar.controller = self
            
            # Tab-Wechsel beobachten: Beim Öffnen des Zeiterfassungs-/Gleitzeit-Tabs neu berechnen
            try:
                self.main_view.layout.bind(current_tab=self.on_tab_changed)
            except Exception as e:
                logger.error(f"Konnte Tab-Wechsel nicht binden: {e}")
            
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

    def on_settings_edit_button(self, field_label, label_attr):
        current_value = ""
        if hasattr(self.main_view, label_attr):
            current_value = getattr(self.main_view, label_attr).text
        if hasattr(self.main_view, "open_settings_edit_popup"):
            self.main_view.open_settings_edit_popup(field_label, current_value, label_attr)

    def on_settings_value_selected(self, instance, field_label, new_value, label_attr):
        if hasattr(self.main_view, label_attr):
            if new_value:
                if label_attr == "week_hours_value_label":
                    display_value = f"{new_value} h"
                elif label_attr in {"green_limit_value_label", "red_limit_value_label"}:
                    display_value = f"{new_value} h"
                else:
                    display_value = new_value
            else:
                display_value = new_value
            getattr(self.main_view, label_attr).text = display_value

    def save_settings_button_clicked(self, *_):
        if not self.model_track_time or self.model_track_time.aktueller_nutzer_id is None:
            if hasattr(self.main_view, "show_messagebox"):
                self.main_view.show_messagebox("Fehler", "Keine Nutzeranmeldung aktiv.")
            return

        def _extract_numeric(label):
            text = (label.text if label and label.text else "").strip()
            if text.endswith("h"):
                text = text[:-1].strip()
            return text

        week_hours_text = _extract_numeric(getattr(self.main_view, "week_hours_value_label", None))
        green_limit_text = _extract_numeric(getattr(self.main_view, "green_limit_value_label", None))
        red_limit_text = _extract_numeric(getattr(self.main_view, "red_limit_value_label", None))

        try:
            neue_wochenstunden = int(week_hours_text)
        except (TypeError, ValueError):
            if hasattr(self.main_view, "show_messagebox"):
                self.main_view.show_messagebox("Fehler", "Vertragliche Wochenstunden müssen eine Zahl sein.")
            return

        try:
            ampel_gruen = int(green_limit_text)
            ampel_rot = int(red_limit_text)
        except (TypeError, ValueError):
            if hasattr(self.main_view, "show_messagebox"):
                self.main_view.show_messagebox("Fehler", "Ampelgrenzen müssen ganze Stunden sein.")
            return

        result_hours = self.model_track_time.aktualisiere_vertragliche_wochenstunden(neue_wochenstunden)
        if isinstance(result_hours, dict) and result_hours.get("error"):
            if hasattr(self.main_view, "show_messagebox"):
                self.main_view.show_messagebox("Fehler", result_hours.get("error"))
            return

        result_ampel = self.model_track_time.aktualisiere_ampelgrenzen(ampel_gruen, ampel_rot)
        if isinstance(result_ampel, dict) and result_ampel.get("error"):
            if hasattr(self.main_view, "show_messagebox"):
                self.main_view.show_messagebox("Fehler", result_ampel.get("error"))
            return

        self.model_track_time.set_ampel_farbe()
        self.update_view_time_tracking()

        if hasattr(self.main_view, "show_messagebox"):
            self.main_view.show_messagebox("Erfolg", "Einstellungen wurden gespeichert.")

    def _format_hours_minutes(self, hours_float):
        """
        Formatiert eine Stundenzahl als String in Stunden und Minuten.
        
        Args:
            hours_float: Stunden als Float (z.B. 1.5, -2.75)
            
        Returns:
            str: Formatierter String (z.B. "1h 30min", "-2h 45min")
        """
        if hours_float is None:
            return "0h 0min"
        
        stunden = int(hours_float)
        minuten = int(abs((hours_float - stunden) * 60))
        vorzeichen = "-" if hours_float < 0 else ""
        
        return f"{vorzeichen}{abs(stunden)}h {minuten}min"
    def _can_edit_selected_employee(self):
        """Gibt True zurück, wenn der aktuell ausgewählte Kalender dem eingeloggten Nutzer entspricht."""
        model = self.model_track_time
        if not model:
            return False
        selected_id = getattr(model, "aktuelle_kalendereinträge_für_id", None)
        if selected_id in (None, model.aktueller_nutzer_id):
            return True
        return False
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
        self.main_view.welcome_label.text = f"Willkommen zurück, {self.model_login.anmeldung_name}!"
        # Gleitzeit in Stunden und Minuten umwandeln
        gleitzeit_stunden = self.model_track_time.aktueller_nutzer_gleitzeit or 0
        stunden = int(gleitzeit_stunden)
        minuten = int(abs((gleitzeit_stunden - stunden) * 60))
        vorzeichen = "-" if gleitzeit_stunden < 0 else ""
        gleitzeit_str = f"{vorzeichen}{abs(stunden)}h {minuten}min"
        
        self.main_view.anzeige_gleitzeit_wert_label.text = gleitzeit_str
        self.main_view.nachtrag_feedback.text = self.model_track_time.feedback_manueller_stempel
        self.main_view.change_password_feedback.text =self.model_track_time.feedback_neues_passwort

        if hasattr(self.main_view, "name_value_label"):
            self.main_view.name_value_label.text = self.model_track_time.aktueller_nutzer_name or ""

        if hasattr(self.main_view, "birth_value_label"):
            geburtstag = self.model_track_time.aktueller_nutzer_geburtsdatum
            if isinstance(geburtstag, date):
                birth_text = geburtstag.strftime("%d.%m.%Y")
            elif isinstance(geburtstag, str):
                birth_text = geburtstag
            else:
                birth_text = ""
            self.main_view.birth_value_label.text = birth_text

        if hasattr(self.main_view, "week_hours_value_label"):
            wochenstunden = self.model_track_time.aktueller_nutzer_vertragliche_wochenstunden
            self.main_view.week_hours_value_label.text = f"{wochenstunden} h" if wochenstunden is not None else ""

        if hasattr(self.main_view, "green_limit_value_label"):
            ampel_gruen = self.model_track_time.aktueller_nutzer_ampel_grün
            self.main_view.green_limit_value_label.text = f"{ampel_gruen} h" if ampel_gruen is not None else ""

        if hasattr(self.main_view, "red_limit_value_label"):
            ampel_rot = self.model_track_time.aktueller_nutzer_ampel_rot
            self.main_view.red_limit_value_label.text = f"{ampel_rot} h" if ampel_rot is not None else ""

        if self.model_track_time.ampel_status:
            self.main_view.ampel.set_state(state=self.model_track_time.ampel_status)

        spinner = self.main_view.month_calendar.employee_spinner
        spinner.values = self.model_track_time.mitarbeiter
        aktueller_name = self.model_track_time.aktueller_nutzer_name
        if aktueller_name:
            if not spinner.text or spinner.text not in spinner.values:
                spinner.text = aktueller_name
                self.model_track_time.aktuelle_kalendereinträge_für_name = aktueller_name
                self.model_track_time.aktuelle_kalendereinträge_für_id = self.model_track_time.aktueller_nutzer_id
        # Kumulierte Gleitzeit auch in Stunden und Minuten umwandeln
        self.main_view.flexible_time_month.text = self._format_hours_minutes(self.model_track_time.kummulierte_gleitzeit_monat)
        self.main_view.flexible_time_quarter.text = self._format_hours_minutes(self.model_track_time.kummulierte_gleitzeit_quartal)
        self.main_view.flexible_time_year.text = self._format_hours_minutes(self.model_track_time.kummulierte_gleitzeit_jahr)
        self.main_view.month_calendar.times_box.clear_widgets()  
        allow_edit = self._can_edit_selected_employee()
        gleitzeit_tag = self.model_track_time.gleitzeit_bestimmtes_datum_stunden
        if gleitzeit_tag is None:
            gleitzeit_tag = 0.0
        gleitzeit_text = self._format_hours_minutes(gleitzeit_tag)
        self.main_view.month_calendar.flexible_time_label.text = gleitzeit_text
        if self.model_track_time.zeiteinträge_bestimmtes_datum is not None:
            for stempel in self.model_track_time.zeiteinträge_bestimmtes_datum:
                # Sicherstellen, dass 'stempel' das erwartete Format hat
                if isinstance(stempel, list) and len(stempel) >= 2 and hasattr(stempel[0], 'zeit'):
                    zeiteintrag_obj = stempel[0]
                    zeit_str = zeiteintrag_obj.zeit.strftime("%H:%M")
                    stempel_id = zeiteintrag_obj.id
                    date_str = self.main_view.month_calendar.date_label.text  # Aktuell angezeigtes Datum
                    self.main_view.month_calendar.add_time_row(
                        stempelzeit=zeit_str, 
                        is_problematic=stempel[1],
                        stempel_id=stempel_id,
                        date_str=date_str,
                        allow_edit=allow_edit,
                        gleitzeit_text=gleitzeit_text
                    )
                else:
                    logger.warning(f"Unerwartetes Stempelformat in update_view_time_tracking: {stempel}")
    def update_view_benachrichtigungen(self):
        # ... (Inhalt bleibt gleich) ...
        logger.debug(f"update_view_benachrichtigungen: Clearing widgets. Current count: {len(self.main_view.benachrichtigungen_grid.children)}")
        self.main_view.benachrichtigungen_grid.clear_widgets() # Sicherstellen, dass die Liste leer ist
        logger.debug(f"update_view_benachrichtigungen: After clear. Count: {len(self.main_view.benachrichtigungen_grid.children)}")
        logger.debug(f"update_view_benachrichtigungen: Anzahl Benachrichtigungen im Modell: {len(self.model_track_time.benachrichtigungen)}")
        
        for i, nachricht in enumerate(self.model_track_time.benachrichtigungen):
            try:
                msg_text = nachricht.create_fehlermeldung()
                msg_datum = nachricht.datum or "Kein Datum" # Fallback
                logger.debug(f"  Benachrichtigung {i+1}: Code={nachricht.benachrichtigungs_code}, Datum={msg_datum}")
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
            
            # Jetzt letzter_login aktualisieren (nach allen Checks)
            self.model_track_time.update_letzter_login()
            
            # UI aktualisieren
            self.update_view_time_tracking()
            self.update_view_benachrichtigungen()
            self.start_or_stop_visual_timer()
            self.model_track_time.aktuelle_kalendereinträge_für_id = self.model_track_time.aktueller_nutzer_id
            self.model_track_time.aktuelle_kalendereinträge_für_name = self.model_track_time.aktueller_nutzer_name
            self.load_vacation_days_for_calendar()  # Urlaubstage für den Kalender laden
            logger.info("Daten-Lade-Prozess abgeschlossen, MainView angezeigt.")
    def registrieren_button_clicked(self,b):
        self.update_model_login()
        self.model_login.neuen_nutzer_anlegen()
        self.update_view_login()
    def stempel_button_clicked(self,b):
        # Aktuelles Datum und Uhrzeit für Bestätigung
        from datetime import datetime, date as _date
        jetzt = datetime.now()
        datum_str = jetzt.strftime("%d.%m.%Y")
        uhrzeit_str = jetzt.strftime("%H:%M:%S")
        # 1) Urlaub prüfen -> spezielles Warn-Popup
        try:
            if self.model_track_time.hat_urlaub_am_datum(_date.today()):
                self.main_view.show_messagebox(
                    title="Urlaubstag-Warnung",
                    message=(
                        f"Heute ({datum_str}) ist als Urlaub eingetragen.\n\n"
                        f"Wenn Sie fortfahren, wird der Urlaubstag gelöscht und der Stempel wird gesetzt."
                    ),
                    callback_yes=self._urlaub_loeschen_und_stempeln,
                    callback_no=None,
                    yes_text="Fortfahren und Urlaub löschen",
                    no_text="Abbrechen",
                )
                return
        except Exception as e:
            logger.error(f"Fehler bei der Prüfung auf Urlaubstag: {e}", exc_info=True)

        # 2) Sonn-/Feiertagswarnung oder normale Bestätigung
        # 2) Minderjährige: Prüfung auf 6. Arbeitstag in der Woche
        try:
            nutzer = self.model_track_time.get_aktueller_nutzer()
            if nutzer and nutzer.is_minor_on_date(_date.today()):
                if self.model_track_time.hat_bereits_5_tage_gearbeitet_in_woche(_date.today()):
                    self.main_view.show_messagebox(
                        title="Arbeitszeitschutz-Warnung",
                        message=(
                            f"ACHTUNG: Sie haben bereits an 5 Tagen in dieser Woche gearbeitet!\n\n"
                            f"Nach dem Arbeitszeitschutzgesetz dürfen Minderjährige maximal 5 Tage pro Woche arbeiten.\n\n"
                            f"Möchten Sie trotzdem fortfahren?"
                        ),
                        callback_yes=self._stempel_nach_6_tage_warnung,
                        callback_no=None,
                        yes_text="Trotzdem fortfahren",
                        no_text="Abbrechen",
                    )
                    return
        except Exception as e:
            logger.error(f"Fehler bei der Prüfung auf 6. Arbeitstag: {e}", exc_info=True)

        # 3) Sonn-/Feiertagswarnung oder normale Bestätigung
        if self.model_track_time.ist_sonn_oder_feiertag(jetzt.date()):
            nachricht = (
                f"ACHTUNG: Sonn-/Feiertag!\n\nDatum: {datum_str}\nUhrzeit: {uhrzeit_str}\n\n"
                f"Möchten Sie diesen Stempel hinzufügen?"
            )
        else:
            nachricht = (
                f"Stempel-Zusammenfassung:\n\nDatum: {datum_str}\nUhrzeit: {uhrzeit_str}\n\nStempel hinzufügen?"
            )
        # Bestätigungs-Popup anzeigen
        self.main_view.show_messagebox(
            title="Stempel bestätigen",
            message=nachricht,
            callback_yes=self._stempel_ausfuehren,
            callback_no=None,
            yes_text="OK",
            no_text="Abbrechen",
        )
    def _urlaub_loeschen_und_stempeln(self):
        """Löscht Urlaubseintrag von heute und setzt anschließend den Stempel."""
        from datetime import date as _date
        try:
            geloescht = self.model_track_time.loesche_urlaub_am_datum(_date.today())
            if geloescht:
                # Urlaubstage im Kalender neu laden
                self.model_track_time.aktuelle_kalendereinträge_für_id = self.model_track_time.aktueller_nutzer_id
                self.load_vacation_days_for_calendar()
                logger.info("Urlaubstag gelöscht – fahre mit Stempel fort.")
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Urlaubstags: {e}", exc_info=True)
        # Danach normal stempeln
        self._stempel_ausfuehren()

    def _stempel_nach_6_tage_warnung(self):
        """Führt den Stempel aus, nachdem die 6-Tage-Warnung akzeptiert wurde."""
        from datetime import datetime, date as _date
        jetzt = datetime.now()

        # Jetzt noch die Sonn-/Feiertagsprüfung durchführen
        if self.model_track_time.ist_sonn_oder_feiertag(jetzt.date()):
            datum_str = jetzt.strftime("%d.%m.%Y")
            uhrzeit_str = jetzt.strftime("%H:%M:%S")
            nachricht = (
                f"ACHTUNG: Sonn-/Feiertag!\n\nDatum: {datum_str}\nUhrzeit: {uhrzeit_str}\n\n"
                f"Möchten Sie diesen Stempel hinzufügen?"
            )
            self.main_view.show_messagebox(
                title="Stempel bestätigen",
                message=nachricht,
                callback_yes=self._stempel_ausfuehren,
                callback_no=None,
                yes_text="OK",
                no_text="Abbrechen",
            )
        else:
            # Keine weitere Warnung nötig, direkt stempeln
            self._stempel_ausfuehren()

    def _stempel_ausfuehren(self):
        """Führt den eigentlichen Stempelvorgang aus."""
        self.model_track_time.stempel_hinzufügen()
        # Nach dem Stempeln: Gleitzeit (bis gestern) neu berechnen, Ampel und Kumulierung aktualisieren
        try:
            self.model_track_time.berechne_gleitzeit()
            self.model_track_time.set_ampel_farbe()
            self.model_track_time.kummuliere_gleitzeit()
        finally:
            # Timer-UI aktualisieren (für laufende Zeit ab letztem Stempel)
            self.start_or_stop_visual_timer()
            # View-Werte (Gleitzeit/Ampel/Kumulierung) aktualisieren
            self.update_view_time_tracking()
    
    def nachtragen_button_clicked(self,b):
        self.update_model_time_tracking()
        art = self.main_view.eintrag_art_spinner.text
        
        if art == "Zeitstempel":
            # Prüfen, ob Datum gesetzt ist
            if self.model_track_time.nachtragen_datum:
                # Erst Urlaub prüfen
                try:
                    from datetime import datetime as _dt
                    nachtrage_datum_obj = _dt.strptime(self.model_track_time.nachtragen_datum, "%d/%m/%Y").date()
                    if self.model_track_time.hat_urlaub_am_datum(nachtrage_datum_obj):
                        self.main_view.show_messagebox(
                            title="Urlaubstag-Warnung",
                            message=(
                                f"Am ausgewählten Tag ({self.model_track_time.nachtragen_datum}) ist Urlaub eingetragen.\n\n"
                                f"Wenn Sie fortfahren, wird der Urlaubstag gelöscht und der Zeitstempel wird nachgetragen."
                            ),
                            callback_yes=self._urlaub_loeschen_und_nachtragen_zeitstempel,
                            callback_no=None,
                            yes_text="Fortfahren und Urlaub löschen",
                            no_text="Abbrechen",
                        )
                        return
                except Exception as e:
                    logger.error(f"Fehler bei der Urlaubstagsprüfung (Nachtragen): {e}", exc_info=True)

                # Dann Minderjährige: Prüfung auf 6. Arbeitstag
                try:
                    from datetime import datetime as _dt
                    nachtrage_datum_obj = _dt.strptime(self.model_track_time.nachtragen_datum, "%d/%m/%Y").date()
                    nutzer = self.model_track_time.get_aktueller_nutzer()
                    if nutzer and nutzer.is_minor_on_date(nachtrage_datum_obj):
                        if self.model_track_time.hat_bereits_5_tage_gearbeitet_in_woche(nachtrage_datum_obj):
                            self.main_view.show_messagebox(
                                title="Arbeitszeitschutz-Warnung",
                                message=(
                                    f"ACHTUNG: Es wurden bereits an 5 Tagen in der Woche vom {self.model_track_time.nachtragen_datum} gearbeitet!\n\n"
                                    f"Nach dem Arbeitszeitschutzgesetz dürfen Minderjährige maximal 5 Tage pro Woche arbeiten.\n\n"
                                    f"Möchten Sie trotzdem fortfahren?"
                                ),
                                callback_yes=self._nachtragen_nach_6_tage_warnung,
                                callback_no=None,
                                yes_text="Trotzdem fortfahren",
                                no_text="Abbrechen",
                            )
                            return
                except Exception as e:
                    logger.error(f"Fehler bei der 6-Tage-Prüfung (Nachtragen): {e}", exc_info=True)

                # Danach Sonn-/Feiertag prüfen
                if self.model_track_time.ist_sonn_oder_feiertag(self.model_track_time.nachtragen_datum):
                    self.main_view.show_messagebox(
                        title="Sonn-/Feiertagswarnung",
                        message=(
                            f"Sie versuchen an einem Sonntag oder Feiertag ({self.model_track_time.nachtragen_datum}) einen Zeitstempel nachzutragen.\n\nMöchten Sie fortfahren?"
                        ),
                        callback_yes=self._nachtragen_zeitstempel_ausfuehren,
                        callback_no=None,
                        yes_text="Fortfahren",
                        no_text="Abbrechen",
                    )
                else:
                    # Direkt nachtragen wenn kein besonderer Tag
                    self._nachtragen_zeitstempel_ausfuehren()
            else:
                self.model_track_time.feedback_manueller_stempel = "Bitte ein Datum auswählen."
                self.update_view_time_tracking()
        elif art == "Urlaub" or art == "Krankheit":
            self.model_track_time.urlaub_eintragen()
            # Nach dem Eintragen von Urlaub/Krankheit die Abwesenheitstage neu laden
            self.load_vacation_days_for_calendar()
            # Nach jedem Nachtrag neu berechnen
            try:
                self.model_track_time.berechne_gleitzeit()
                self.model_track_time.set_ampel_farbe()
                self.model_track_time.kummuliere_gleitzeit()
            finally:
                self.update_view_time_tracking()
        else:
            self.model_track_time.feedback_manueller_stempel = "Bitte eine Eintragsart wählen."
            self.update_view_time_tracking()
    
    def _nachtragen_zeitstempel_ausfuehren(self):
        """Führt das eigentliche Nachtragen eines Zeitstempels aus."""
        self.model_track_time.manueller_stempel_hinzufügen()
        # Nach jedem Nachtrag neu berechnen (z.B. wenn vergangene Tage betroffen sind)
        try:
            self.model_track_time.berechne_gleitzeit()
            self.model_track_time.set_ampel_farbe()
            self.model_track_time.kummuliere_gleitzeit()
        finally:
            self.update_view_time_tracking() # Feedback + aktualisierte Werte anzeigen
        # PopUp-Warnungen nach einem Nachtrag immer aktualisieren
        self._refresh_popup_warnings()

    def _nachtragen_nach_6_tage_warnung(self):
        """Führt das Nachtragen aus, nachdem die 6-Tage-Warnung akzeptiert wurde."""
        # Jetzt noch die Sonn-/Feiertagsprüfung durchführen
        if self.model_track_time.ist_sonn_oder_feiertag(self.model_track_time.nachtragen_datum):
            self.main_view.show_messagebox(
                title="Sonn-/Feiertagswarnung",
                message=(
                    f"Sie versuchen an einem Sonntag oder Feiertag ({self.model_track_time.nachtragen_datum}) einen Zeitstempel nachzutragen.\n\nMöchten Sie fortfahren?"
                ),
                callback_yes=self._nachtragen_zeitstempel_ausfuehren,
                callback_no=None,
                yes_text="Fortfahren",
                no_text="Abbrechen",
            )
        else:
            # Keine weitere Warnung nötig, direkt nachtragen
            self._nachtragen_zeitstempel_ausfuehren()

    def _urlaub_loeschen_und_nachtragen_zeitstempel(self):
        """Löscht Urlaub am ausgewählten Nachtrags-Datum und trägt dann den Zeitstempel nach."""
        from datetime import datetime as _dt
        try:
            if not self.model_track_time.nachtragen_datum:
                self.model_track_time.feedback_manueller_stempel = "Bitte ein Datum auswählen."
                self.update_view_time_tracking()
                return
            datum_obj = _dt.strptime(self.model_track_time.nachtragen_datum, "%d/%m/%Y").date()
            geloescht = self.model_track_time.loesche_urlaub_am_datum(datum_obj)
            if geloescht:
                # Urlaubstage im Kalender neu laden
                self.model_track_time.aktuelle_kalendereinträge_für_id = self.model_track_time.aktueller_nutzer_id
                self.load_vacation_days_for_calendar()
                logger.info(f"Urlaubstag {self.model_track_time.nachtragen_datum} gelöscht – trage Zeitstempel nach.")
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Urlaubstags (Nachtragen): {e}", exc_info=True)
        # Danach den normalen Nachtragsfluss starten
        self._nachtragen_zeitstempel_ausfuehren()
    def passwort_ändern_button_clicked(self,b):
        self.update_model_time_tracking()
        self.model_track_time.update_passwort()
        self.update_view_time_tracking()
        
    #call view functions
    def prev_button_clicked(self, b):
        self.main_view.month_calendar.change_month(-1)
        self.load_vacation_days_for_calendar()
    def next_button_clicked(self, b):
        self.main_view.month_calendar.change_month(1)
        self.load_vacation_days_for_calendar()
    def load_vacation_days_for_calendar(self):
        """Lädt die Urlaubs- und Krankheitstage für den aktuell angezeigten Monat im Kalender."""
        jahr = self.main_view.month_calendar.year
        monat = self.main_view.month_calendar.month
        urlaubstage = self.model_track_time.get_urlaubstage_monat(jahr, monat)
        krankheitstage = self.model_track_time.get_krankheitstage_monat(jahr, monat)
        self.main_view.month_calendar.urlaubstage = urlaubstage
        self.main_view.month_calendar.krankheitstage = krankheitstage
        self.main_view.month_calendar.fill_grid_with_days()
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
        # Bestehende Events abbrechen
        if self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None
        if self.arbeitsfenster_warning_event:
            self.arbeitsfenster_warning_event.cancel()
            self.arbeitsfenster_warning_event = None
        if self.max_arbeitszeit_warning_event:
            self.max_arbeitszeit_warning_event.cancel()
            self.max_arbeitszeit_warning_event = None
        today_stamps = self.model_track_time.get_stamps_for_today()
        is_clocked_in = len(today_stamps) % 2 != 0
        if is_clocked_in:
            try:
                last_stamp_time = today_stamps[-1].zeit
                self.start_time_dt = datetime.combine(date.today(), last_stamp_time)
                self.timer_event = Clock.schedule_interval(self.update_visual_timer, 60)  # Update alle 60 Sekunden
                self.update_visual_timer(0)
                
                # PopUp-Warnungen in DB erstellen und laden
                self.model_track_time.erstelle_popup_warnungen_beim_einstempeln()
                self._load_and_schedule_popups()
                
            except (ValueError, TypeError) as e:
                 logger.error(f"Fehler beim Starten des visuellen Timers: {e}", exc_info=True)
                 self.main_view.timer_label.text = "Error"
        else:
            # Beim Ausstempeln: Alle PopUp-Benachrichtigungen für heute löschen
            self.main_view.timer_label.text = "00:00"
            self.model_track_time.delete_all_popup_benachrichtigungen_for_today()
            logger.info("PopUp-Benachrichtigungen beim Ausstempeln gelöscht")
    def _load_and_schedule_popups(self):
        """
        Lädt ausstehende PopUp-Benachrichtigungen aus der DB und plant sie für die richtige Uhrzeit.
        """
        try:
            pending_popups = self.model_track_time.get_pending_popups_for_today()
            
            for code, popup_uhrzeit, benachrichtigung_id in pending_popups:
                # Berechne Sekunden bis zum PopUp
                now = datetime.now()
                popup_dt = datetime.combine(date.today(), popup_uhrzeit)
                
                if popup_dt > now:
                    sekunden_bis_popup = (popup_dt - now).total_seconds()
                    
                    # PopUp planen
                    if code == 9:  # Arbeitsfenster-Warnung
                        self.arbeitsfenster_warning_event = Clock.schedule_once(
                            lambda dt, bid=benachrichtigung_id: self._show_popup_from_db(9, bid),
                            sekunden_bis_popup
                        )
                        logger.info(f"Arbeitsfenster-PopUp aus DB geplant für {popup_uhrzeit}")
                    elif code == 10:  # Max. Arbeitszeit-Warnung
                        self.max_arbeitszeit_warning_event = Clock.schedule_once(
                            lambda dt, bid=benachrichtigung_id: self._show_popup_from_db(10, bid),
                            sekunden_bis_popup
                        )
                        logger.info(f"Max. Arbeitszeit-PopUp aus DB geplant für {popup_uhrzeit}")
        
        except Exception as e:
            logger.error(f"Fehler beim Laden/Planen der PopUps: {e}", exc_info=True)
    def _refresh_popup_warnings(self):
        """Aktualisiert alle PopUp-Warnungen basierend auf den aktuellen Stempeln."""
        try:
            # Laufende geplante Events abbrechen, damit wir sie neu planen können
            if self.arbeitsfenster_warning_event:
                self.arbeitsfenster_warning_event.cancel()
                self.arbeitsfenster_warning_event = None
            if self.max_arbeitszeit_warning_event:
                self.max_arbeitszeit_warning_event.cancel()
                self.max_arbeitszeit_warning_event = None
            today_stamps = self.model_track_time.get_stamps_for_today()
            is_clocked_in = len(today_stamps) % 2 != 0
            # Bestehende PopUps entfernen, damit neue Zeiten gespeichert werden können
            self.model_track_time.delete_all_popup_benachrichtigungen_for_today()
            if is_clocked_in:
                self.model_track_time.erstelle_popup_warnungen_beim_einstempeln()
                self._load_and_schedule_popups()
            else:
                logger.debug("_refresh_popup_warnings: Nutzer ist nicht eingestempelt – PopUps gelöscht.")
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der PopUp-Warnungen: {e}", exc_info=True)
    def _show_popup_from_db(self, code, benachrichtigung_id):
        """
        Zeigt ein PopUp basierend auf dem Code aus der DB an und löscht die Benachrichtigung danach.
        """
        try:
            from modell import session, mitarbeiter
            nutzer = session.get(mitarbeiter, self.model_track_time.aktueller_nutzer_id)
            if not nutzer:
                return
            
            is_minor = nutzer.is_minor_on_date(date.today())
            
            if code == 9:  # Arbeitsfenster-Warnung
                ende_zeit = "20:00" if is_minor else "22:00"
                self.main_view.show_messagebox(
                    title="Arbeitsfenster endet bald!",
                    message=f"WARNUNG: Ihr erlaubtes Arbeitsfenster endet um {ende_zeit} Uhr.\n\nBitte beachten Sie, dass Sie rechtzeitig ausstempeln.",
                    callback_yes=None,
                    yes_text="OK"
                )
                logger.warning(f"Arbeitsfenster-Warnung angezeigt (endet um {ende_zeit} Uhr)")
            
            elif code == 10:  # Max. Arbeitszeit-Warnung
                max_zeit = "7,5 Stunden" if is_minor else "9 Stunden"
                self.main_view.show_messagebox(
                    title="Maximale Arbeitszeit bald erreicht!",
                    message=f"WARNUNG: Sie erreichen in ca. 30 Minuten die maximale tägliche Arbeitszeit von {max_zeit}.\n\nBitte stempeln Sie rechtzeitig aus.",
                    callback_yes=None,
                    yes_text="OK"
                )
                logger.warning(f"Max. Arbeitszeit-Warnung angezeigt (max. {max_zeit})")
            
            # PopUp-Benachrichtigung aus DB löschen
            self.model_track_time.delete_popup_benachrichtigung(benachrichtigung_id)
            
        except Exception as e:
            logger.error(f"Fehler beim Anzeigen des PopUps (Code {code}): {e}", exc_info=True)
    def update_visual_timer(self, dt):
        if not self.start_time_dt:
            return
        try:
            elapsed = datetime.now() - self.start_time_dt
            total_seconds = int(elapsed.total_seconds())
            if total_seconds < 0: total_seconds = 0
            hours, remainder = divmod(total_seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            self.main_view.timer_label.text = f"{hours:02d}:{minutes:02d}"
        except Exception as e:
            logger.error(f"Fehler im update_visual_timer: {e}", exc_info=True)
            self.main_view.timer_label.text = "Error"
            if self.timer_event:
                self.timer_event.cancel() # Timer stoppen, um Endlosschleife zu verhindern
    
    def on_date_selected_register(self, instance, value, date_range):
        if value: # Input validieren
            self.register_view.reg_geburtsdatum.text = value.strftime("%d/%m/%Y")
    def on_eintrag_art_selected(self, spinner_instance, text):
        if text in ["Urlaub", "Krankheit"]:
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
        self.load_vacation_days_for_calendar()  # Urlaubstage für den neuen Mitarbeiter laden
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
    
    def on_tab_changed(self, panel, new_tab):
        """Wird aufgerufen, wenn im Haupt-TabbedPanel der Tab gewechselt wird.
        Wenn der Zeiterfassungs-/Gleitzeit-Tab aktiv wird, Gleitzeit neu berechnen und UI aktualisieren.
        """
        try:
            tab_text = getattr(new_tab, 'text', '') if new_tab else ''
            if tab_text in ("Zeiterfassung", "Gleitzeit"):
                # Modell aktualisieren und Gleitzeit-Kennzahlen neu berechnen
                self.update_model_time_tracking()
                self.model_track_time.berechne_gleitzeit()
                self.model_track_time.set_ampel_farbe()
                self.model_track_time.kummuliere_gleitzeit()
                # UI auffrischen
                self.update_view_time_tracking()
            elif tab_text == "Einstellungen":
                self.update_model_time_tracking()
                self.model_track_time.get_user_info()
                self.update_view_time_tracking()
        except Exception as e:
            logger.error(f"Fehler in on_tab_changed: {e}", exc_info=True)

    def stempel_bearbeiten_button_clicked(self, stempel_id: int, neue_zeit_str: str):
        """
        Wird aufgerufen, wenn der Bearbeiten-Button im Popup bestätigt wird.
        Ruft die Modell-Methode zum Bearbeiten des Stempels auf.
        
        Args:
            stempel_id (int): ID des zu bearbeitenden Zeiteintrags
            neue_zeit_str (str): Neue Uhrzeit als String (Format: "HH:MM")
        """
        if not self._can_edit_selected_employee():
            logger.info("Bearbeiten von Zeiteinträgen anderer Mitarbeitender ist nicht erlaubt")
            self.model_track_time.feedback_manueller_stempel = "Keine Berechtigung zum Bearbeiten fremder Stempel."
            self.update_view_time_tracking()
            return
        try:
            # Zeit-String in time-Objekt konvertieren
            neue_zeit = datetime.strptime(neue_zeit_str, "%H:%M").time()
            
            # Modell-Methode aufrufen
            erfolg = self.model_track_time.stempel_bearbeiten_nach_id(stempel_id, neue_zeit)
            
            if erfolg:
                logger.info(f"Stempel {stempel_id} erfolgreich auf {neue_zeit_str} geändert")
                # UI aktualisieren
                self.update_model_time_tracking()
                self.model_track_time.set_ampel_farbe()
                self.model_track_time.kummuliere_gleitzeit()
                self.update_view_time_tracking()
                self._refresh_popup_warnings()
                
                # Kalender neu laden
                if hasattr(self.main_view.month_calendar, 'date_label') and self.main_view.month_calendar.date_label.text:
                    datum_str = self.main_view.month_calendar.date_label.text
                    self.model_track_time.bestimmtes_datum = datum_str
                    self.model_track_time.get_zeiteinträge()
                    self.update_view_time_tracking()
            else:
                logger.error(f"Fehler beim Bearbeiten von Stempel {stempel_id}")
                self.main_view.show_messagebox("Fehler", "Stempel konnte nicht bearbeitet werden.")
        
        except ValueError as e:
            logger.error(f"Ungültiges Zeitformat: {neue_zeit_str} - {e}")
            self.main_view.show_messagebox("Fehler", f"Ungültiges Zeitformat: {neue_zeit_str}")
        except Exception as e:
            logger.error(f"Fehler beim Bearbeiten des Stempels: {e}", exc_info=True)
            self.main_view.show_messagebox("Fehler", f"Ein Fehler ist aufgetreten:\n{e}")
    def stempel_löschen_button_clicked(self, stempel_id: int):
        """
        Wird aufgerufen, wenn der Löschen-Button im Bestätigungsdialog bestätigt wird.
        Ruft die Modell-Methode zum Löschen des Stempels auf.
        
        Args:
            stempel_id (int): ID des zu löschenden Zeiteintrags
        """
        if not self._can_edit_selected_employee():
            logger.info("Löschen von Zeiteinträgen anderer Mitarbeitender ist nicht erlaubt")
            self.model_track_time.feedback_manueller_stempel = "Keine Berechtigung zum Löschen fremder Stempel."
            self.update_view_time_tracking()
            return
        try:
            # Modell-Methode aufrufen
            erfolg = self.model_track_time.stempel_löschen_nach_id(stempel_id)
            
            if erfolg:
                logger.info(f"Stempel {stempel_id} erfolgreich gelöscht")
                # UI aktualisieren
                self.update_model_time_tracking()
                self.model_track_time.set_ampel_farbe()
                self.model_track_time.kummuliere_gleitzeit()
                self.update_view_time_tracking()
                self._refresh_popup_warnings()
                
                # Kalender neu laden
                if hasattr(self.main_view.month_calendar, 'date_label') and self.main_view.month_calendar.date_label.text:
                    datum_str = self.main_view.month_calendar.date_label.text
                    self.model_track_time.bestimmtes_datum = datum_str
                    self.model_track_time.get_zeiteinträge()
                    self.update_view_time_tracking()
            else:
                logger.error(f"Fehler beim Löschen von Stempel {stempel_id}")
                self.main_view.show_messagebox("Fehler", "Stempel konnte nicht gelöscht werden.")
        
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Stempels: {e}", exc_info=True)
            self.main_view.show_messagebox("Fehler", f"Ein Fehler ist aufgetreten:\n{e}")
        
    # add_entry_in_popup ist im Original-Code nicht angebunden, daher ignoriert.
    #getter
    def get_view_manager(self):
        return self.sm