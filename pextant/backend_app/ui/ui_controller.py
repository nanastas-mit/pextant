import pextant.backend_app.events.event_definitions as event_definitions
import tkinter as tk
import tkinter.ttk as ttk
from pextant.backend_app.app_component import AppComponent
from pextant.backend_app.events.event_dispatcher import EventDispatcher
from pextant.backend_app.ui.page_server import PageServer
from pextant.backend_app.ui.page_find_path import PageFindPath
from pextant.backend_app.ui.widget_styles import UIStyleManager


class UIController(AppComponent):
    """main class for controlling UI window"""

    '''=======================================
    STARTUP/SHUTDOWN
    ======================================='''
    def __init__(self, manager):

        super().__init__(manager)

        # create and setup root
        self.root = tk.Tk()
        self.root.title("Sextant")
        self.root.geometry('740x620')
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_closed)

        # initialize styles
        UIStyleManager.initialize_styles()

        # create pages
        self.tab_control = ttk.Notebook(self.root)
        self.pages = [
            self.create_page(PageFindPath, "Path"),
            self.create_page(PageServer, "Server"),
        ]
        self.tab_control.pack(fill=tk.BOTH, expand=1)

    def on_window_closed(self):

        # inform all pages of window close
        for page in self.pages:
            page.page_closed()

        EventDispatcher.instance().trigger_event(event_definitions.UI_WINDOW_CLOSED)

    '''=======================================
    UPDATES
    ======================================='''
    def update(self, delta_time):

        super().update(delta_time)

        # update tkinter
        self.root.update_idletasks()
        self.root.update()

        # call update on all pages
        for page in self.pages:
            page.page_update(delta_time)

    '''=======================================
    PAGE MANIPULATION
    ======================================='''
    def create_page(self, cls, name):

        page = cls(self.tab_control)
        self.tab_control.add(page, text=name)

        return page
