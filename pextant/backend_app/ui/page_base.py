from pextant.backend_app.events.event_dispatcher import EventDispatcher
import tkinter as tk


class PageBase(tk.Frame):
    """base class for all pages in UI"""

    def __init__(self, master, event_handlers):

        # call super
        tk.Frame.__init__(self, master)

        # register listeners
        self.event_handlers = event_handlers
        EventDispatcher.get_instance().set_event_listening_group(self.event_handlers, True)

    def page_closed(self):

        # unregister listeners
        EventDispatcher.get_instance().set_event_listening_group(self.event_handlers, False)

    def page_update(self, delta_time):
        """called once per frame by ui_controller.
        update function already exists in tk.Frame, hence 'page_update'"""
        pass
