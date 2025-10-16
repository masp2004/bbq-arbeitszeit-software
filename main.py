"""
Hauptmodul der BBQ Arbeitszeit-Erfassungssoftware.

Dieses Modul enthält die Hauptklasse der Anwendung und startet die KivyMD-basierte
GUI für die Zeiterfassung. Die Software unterstützt Mitarbeiter dabei, das deutsche
Arbeitszeitgesetz (ArbZG) einzuhalten.
"""

import os

from kivymd.app import MDApp
from controller import Controller


class TimeTrackingApp(MDApp):
    """
    Hauptanwendungsklasse für die Zeiterfassungs-App.
    
    Diese Klasse erbt von MDApp (Material Design App) und initialisiert
    die Anwendung mit dem Controller und Screen Manager für die Navigation
    zwischen verschiedenen Views.
    
    Attributes:
        controller (Controller): Zentrale Steuerungsinstanz der Anwendung
        screen_manager (ScreenManager): Verwaltet die verschiedenen Ansichten
    """
    
    def __init__(self, **kwargs):
        """
        Initialisiert die TimeTrackingApp.
        
        Args:
            **kwargs: Zusätzliche Keyword-Argumente für MDApp
        """
        super().__init__(**kwargs)
        self.controller = Controller()
        self.screen_manager = self.controller.get_view_manager()

    def build(self):
        """
        Erstellt und konfiguriert die Benutzeroberfläche der Anwendung.
        
        Setzt das App-Icon, den Titel und das Theme (Dark Mode mit BlueGray Palette).
        
        Returns:
            ScreenManager: Der konfigurierte Screen Manager für die Navigation
        """
        self.icon = os.path.join(os.path.dirname(__file__), "velqor.png")
        self.title = "Velqor - Zeiterfassung"
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "BlueGray"
        return self.screen_manager
 

if __name__ == "__main__":
    TimeTrackingApp().run()
 