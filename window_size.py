from kivy.core.window import Window
from kivy.clock import Clock

_fixed_size = None
_enforce_handler = None

def set_fixed_window_size(size):
        """
        Setzt Fenstergröße, deaktiviert Resize und sorgt dafür,
        dass das Fenster nicht verändert werden kann.
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

            if (int(width), int(height)) != _fixed_size:
                Clock.schedule_once(lambda dt: setattr(Window, "size", _fixed_size), 0)
        
        _enforce_handler = _enforce
        Window.bind(on_resize=_enforce_handler)