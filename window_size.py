"""
Window-Size-Management-Modul für die BBQ Arbeitszeit-Erfassungssoftware.

Dieses Modul stellt Funktionen bereit, um die Fenstergröße der Kivy-Anwendung
zu fixieren und Größenänderungen durch den Benutzer zu verhindern.

Die Fixierung erfolgt durch:
- Deaktivierung von Window.resizable
- Setzen von Minimum-Werten
- Event-Binding um Resize-Versuche rückgängig zu machen

Dies ist notwendig, da die Anwendung für feste Fenstergrößen designt wurde
und dynamisches Resizing nicht unterstützt wird.
"""

from kivy.core.window import Window
from kivy.clock import Clock

# Globale Variablen für Fenstergröße und Event-Handler
_fixed_size = None
_enforce_handler = None

def set_fixed_window_size(size):
    """
    Setzt die Fenstergröße und verhindert Änderungen durch den Benutzer.
    
    Diese Funktion deaktiviert Resize-Funktionalität und bindet einen Event-Handler,
    der versucht, jede Größenänderung sofort rückgängig zu machen.
    
    Args:
        size (tuple): Gewünschte Fenstergröße als (width, height) Tupel
        
    Example:
        >>> set_fixed_window_size((800, 600))
        # Fenster wird auf 800x600 fixiert
    """
    global _fixed_size, _enforce_handler
    _fixed_size = (int(size[0]), int(size[1]))

    # Größe setzen und Resize deaktivieren
    Window.size = _fixed_size
    Window.resizable = False

    # Minimum setzen (verhindert Verkleinern)
    try:
        Window.minimum_width, Window.minimum_height = _fixed_size
    except Exception:
        pass
    # Vorherigen Enforce-Handler entfernen (falls vorhanden)
    if _enforce_handler is not None:
        try:
            Window.unbind(on_resize=_enforce_handler)
        except Exception:
            pass
    
    # Neuen Handler definieren, der das Fenster bei Resize wieder korrekt setzt
    def _enforce(window, width, height):
        """
        Interner Event-Handler zum Erzwingen der festen Fenstergröße.
        
        Wird automatisch aufgerufen, wenn Window.size geändert wird.
        Setzt die Größe asynchron zurück auf die fixierte Größe.
        
        Args:
            window: Kivy Window-Objekt
            width (int): Neue Breite
            height (int): Neue Höhe
        
        Hinweis: Die Argumente sind durch die Event-Signatur von Kivy erforderlich,
        werden aber nicht verwendet, da die Fenstergröße fest erzwungen wird.
        """
        if (int(width), int(height)) != _fixed_size:
            Clock.schedule_once(lambda dt: setattr(Window, "size", _fixed_size), 0)
        
    _enforce_handler = _enforce
    Window.bind(on_resize=_enforce_handler)