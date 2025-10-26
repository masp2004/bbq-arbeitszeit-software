import os
import logging
import logging.handlers

from kivymd.app import MDApp
from controller import Controller

# === Logging-Konfiguration ===
# Richten Sie das Logging ein, bevor etwas anderes passiert.
# Dies wird alle Log-Nachrichten von allen Modulen abfangen.
try:
    # Fügen Sie einen rotierenden Datei-Handler hinzu (z.B. 5 Dateien à 1MB)
    file_handler = logging.handlers.RotatingFileHandler(
        "app.log", maxBytes=1_000_000, backupCount=5
    )
    file_handler.setLevel(logging.DEBUG) # Alle Loglevel in die Datei schreiben
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))

    # Konsolen-Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO) # Nur INFO und höher in der Konsole
    console_handler.setFormatter(logging.Formatter(
        '%(name)s - %(levelname)s - %(message)s'
    ))

    # Root-Logger konfigurieren
    logging.basicConfig(
        level=logging.DEBUG, # Niedrigstes Level, das an Handler gesendet wird
        handlers=[
            file_handler,
            console_handler
        ]
    )

except (IOError, PermissionError) as e:
    # Fallback, wenn Log-Datei nicht erstellt werden kann
    logging.basicConfig(level=logging.INFO)
    logging.critical(f"Konnte Log-Datei 'app.log' nicht erstellen: {e}. Logge nur in Konsole.")

# Logger für diese Datei holen
logger = logging.getLogger(__name__)
# ==============================


class TimeTrackingApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        try:
            self.controller = Controller()
            self.screen_manager = self.controller.get_view_manager()
            logger.info("Controller und ScreenManager erfolgreich initialisiert.")
        except Exception as e:
            # Ein Fehler hier ist fatal und die App kann nicht starten.
            logger.critical(f"Fehler bei der Initialisierung des Controllers: {e}", exc_info=True)
            # Hier könnte man ein Kivy-Popup zeigen, bevor man beendet.
            raise # App-Start abbrechen

    def build(self):
        logger.info("Build-Methode wird aufgerufen.")
        try:
            self.icon = os.path.join(os.path.dirname(__file__), "velqor.png")
        except Exception as e:
            logger.warning(f"Konnte App-Icon nicht laden: {e}")
            self.icon = "" # Fallback
            
        self.title = "Velqor - Zeiterfassung"
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "BlueGray"
        return self.screen_manager
 

if __name__ == "__main__":
    try:
        logger.info("Anwendung startet.")
        TimeTrackingApp().run()
        logger.info("Anwendung wird normal beendet.")
    except KeyboardInterrupt:
        logger.info("Anwendung durch Benutzer (CTRL+C) beendet.")
    except Exception as e:
        # Fängt alle nicht abgefangenen Fehler ab, die zum Absturz führen würden
        logger.critical(f"Nicht abgefangener Fehler führt zum Absturz der Anwendung: {e}", exc_info=True)
        # Hier könnte man dem Benutzer eine finale Fehlermeldung zeigen.