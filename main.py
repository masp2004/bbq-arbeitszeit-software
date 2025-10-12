import os

from kivymd.app import MDApp
from controller import Controller


class TimeTrackingApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.controller = Controller()
        self.screen_manager = self.controller.get_view_manager()

    def build(self):
        self.icon = os.path.join(os.path.dirname(__file__), "velqor.png")
        self.title = "Velqor - Zeiterfassung"
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "BlueGray"
        return self.screen_manager
 

if __name__ == "__main__":
    TimeTrackingApp().run()
 