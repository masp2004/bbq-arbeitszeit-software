"""
Haupt-Einstiegspunkt für die BBQ Arbeitszeit-Erfassungssoftware.

Dieses Modul initialisiert die Kivy/KivyMD-Anwendung, konfiguriert das Logging
und startet die Anwendung durch Instanziierung des Controllers.

Die Anwendung folgt dem MVC-Pattern:
- Model: modell.py (Business-Logik und Datenbank)
- View: view.py (GUI-Komponenten)
- Controller: controller.py (Event-Handling und Koordination)

Autor: Velqor
Version: 0.3
"""

import os
import logging
import logging.handlers

from kivymd.app import MDApp
from controller import Controller

# ===================================
# === Logging-Konfiguration Setup ===
# ===================================
# WICHTIG: Logging MUSS vor allen anderen Imports konfiguriert werden,
# damit alle Module (modell.py, controller.py, view.py) die Konfiguration nutzen können.

try:
    # === Datei-Handler: Rotierendes Log-File ===
    # Speichert alle Logs in 'app.log', bei 1MB Limit wird rotiert (max. 5 Backup-Dateien)
    file_handler = logging.handlers.RotatingFileHandler(
        "app.log",              # Log-Datei-Name
        maxBytes=1_000_000,     # 1 MB pro Datei
        backupCount=5           # Max. 5 Backup-Dateien (app.log.1, app.log.2, ...)
    )
    file_handler.setLevel(logging.DEBUG)  # ALLES in die Datei schreiben (DEBUG bis CRITICAL)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'  # Zeitstempel, Modul, Level, Nachricht
    ))

    # === Konsolen-Handler: Nur wichtige Nachrichten in der Konsole ===
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # Nur INFO und höher (INFO, WARNING, ERROR, CRITICAL)
    console_handler.setFormatter(logging.Formatter(
        '%(name)s - %(levelname)s - %(message)s'  # Kürzeres Format für Konsole
    ))

    # === Root-Logger konfigurieren ===
    # Alle Module erben diese Konfiguration (modell, controller, view)
    logging.basicConfig(
        level=logging.DEBUG,  # Niedrigstes Level, das an die Handler gesendet wird
        handlers=[
            file_handler,      # Logs in Datei
            console_handler    # Logs in Konsole
        ]
    )

except (IOError, PermissionError) as e:
    # Fallback: Wenn Log-Datei nicht erstellt werden kann (z.B. keine Schreibrechte)
    # → Nur in Konsole loggen
    logging.basicConfig(level=logging.INFO)
    logging.critical(f"Konnte Log-Datei 'app.log' nicht erstellen: {e}. Logge nur in Konsole.")

# Logger für dieses Modul (main.py) holen
logger = logging.getLogger(__name__)
# ======================================


class TimeTrackingApp(MDApp):
    """
    Haupt-Anwendungsklasse für die Zeiterfassung.
    
    Erbt von MDApp (Material Design App von KivyMD) und initialisiert
    den Controller sowie den ScreenManager.
    
    Attributes:
        controller (Controller): Haupt-Controller-Instanz
        screen_manager (ScreenManager): Kivy ScreenManager mit allen Views
        
    Note:
        Bei kritischen Fehlern in __init__ wird die Anwendung NICHT gestartet.
    """
    
    def __init__(self, **kwargs):
        """
        Initialisiert die App und den Controller.
        
        Args:
            **kwargs: Keyword-Argumente für MDApp
            
        Raises:
            Exception: Bei kritischen Fehlern (z.B. Datenbank nicht erreichbar)
        """
        super().__init__(**kwargs)
        try:
            # === Schritt 1: Controller erstellen ===
            # Der Controller initialisiert Modelle und Views
            self.controller = Controller()
            
            # === Schritt 2: ScreenManager holen ===
            # Enthält alle Screens (Login, Register, Main)
            self.screen_manager = self.controller.get_view_manager()
            
            logger.info("Controller und ScreenManager erfolgreich initialisiert.")
        except Exception as e:
            # KRITISCHER FEHLER: App kann nicht funktionieren
            logger.critical(f"Fehler bei der Initialisierung des Controllers: {e}", exc_info=True)
            # Ausnahme weitergeben → App-Start wird abgebrochen
            raise

    def build(self):
        """
        Kivy build()-Methode: Erstellt die Anwendungs-GUI.
        
        Wird von Kivy automatisch beim App-Start aufgerufen.
        
        Returns:
            Widget: Root-Widget der Anwendung (ScreenManager)
            
        Note:
            Konfiguriert auch App-Icon, Titel und Theme.
        """
        logger.info("Build-Methode wird aufgerufen.")
        
        # === App-Icon setzen ===
        try:
            # Icon-Pfad relativ zur main.py-Datei
            self.icon = os.path.join(os.path.dirname(__file__), "velqor.png")
        except Exception as e:
            logger.warning(f"Konnte App-Icon nicht laden: {e}")
            self.icon = ""  # Fallback: Kein Icon
        
        # === App-Eigenschaften setzen ===
        self.title = "Velqor - Zeiterfassung"          # Fenster-Titel
        self.theme_cls.theme_style = "Dark"            # Dark Mode
        self.theme_cls.primary_palette = "BlueGray"    # Farbschema
        
        # === Root-Widget zurückgeben ===
        return self.screen_manager
 

if __name__ == "__main__":
    """
    Haupt-Einstiegspunkt beim direkten Aufruf von main.py.
    
    Startet die Kivy-Anwendung und fängt Ausnahmen ab.
    """
    try:
        logger.info("=== Anwendung startet ===")
        # App instanziieren und starten (blocking, läuft bis Fenster geschlossen wird)
        TimeTrackingApp().run()
        logger.info("=== Anwendung wird normal beendet ===")
    except KeyboardInterrupt:
        # CTRL+C in der Konsole gedrückt
        logger.info("=== Anwendung durch Benutzer (CTRL+C) beendet ===")
    except Exception as e:
        # Unbehandelter Fehler während der Laufzeit
        logger.critical(f"=== Anwendung mit Fehler beendet: {e} ===", exc_info=True)
    except Exception as e:
        # Fängt alle nicht abgefangenen Fehler ab, die zum Absturz führen würden
        logger.critical(f"Nicht abgefangener Fehler führt zum Absturz der Anwendung: {e}", exc_info=True)
        # Hier könnte man dem Benutzer eine finale Fehlermeldung zeigen.