import pextant.backend_app.events.event_definitions as event_definitions
import pextant.backend_app.ui.fonts as fonts
import tkinter as tk
from tkinter import ttk
from pextant.backend_app.dependency_injection import RequiredFeature, has_attributes
from pextant.backend_app.events.event_dispatcher import EventDispatcher
from pextant.backend_app.ui.page_base import PageBase


class PageServer(PageBase):
    """handles all functionality of server page"""

    def __init__(self, master):

        super().__init__(master, {
            event_definitions.START_SERVER: self.on_server_started,
            event_definitions.STOP_SERVER: self.on_server_stopped,
            event_definitions.MESSAGE_RECEIVED: self.on_message_received,
        })

        # dependency injected server object
        self.server = RequiredFeature(
            "server",
            has_attributes("is_listening")
        ).result

        # ui references
        self.notification_lbl = None
        self.start_server_btn = None
        self.stop_server_btn = None

        # setup
        self.initial_setup()

    def initial_setup(self):

        # title
        label = tk.Label(self, text="SERVER", font=fonts.LARGE_FONT, underline=1)
        label.pack(pady=4)

        # notification text
        self.notification_lbl = tk.Label(self, text='-', font=fonts.SUBTITLE_FONT)
        self.notification_lbl.pack(pady=2)

        # banner
        banner_frame = ttk.Frame(self, style='Banner.TFrame')
        banner_frame.pack(pady=4, fill=tk.X)

        # start/stop server
        button_frame = ttk.Frame(banner_frame)
        button_frame.pack(pady=10)
        self.start_server_btn = tk.Button(
            button_frame,
            text="Start Server",
            font=fonts.LARGE_BTN_FONT,
            command=self.start_server
        )
        self.start_server_btn.pack(padx=10, side=tk.LEFT)
        self.stop_server_btn = tk.Button(
            button_frame,
            text="Stop Server",
            font=fonts.LARGE_BTN_FONT,
            command=self.stop_server
        )
        self.stop_server_btn.pack(padx=10, side=tk.LEFT)

        # initial refresh
        self.refresh_ui()

    def refresh_ui(self):
        if self.server.is_listening:
            self.notification_lbl['text'] = "Listening..."
            self.start_server_btn['state'] = tk.DISABLED
            self.stop_server_btn['state'] = tk.NORMAL
        else:
            self.notification_lbl['text'] = "Not Listening..."
            self.start_server_btn['state'] = tk.NORMAL
            self.stop_server_btn['state'] = tk.DISABLED

    '''=======================================
    START/STOP
    ======================================='''
    @staticmethod
    def start_server():
        EventDispatcher.instance().trigger_event(event_definitions.START_SERVER)

    @staticmethod
    def stop_server():
        EventDispatcher.instance().trigger_event(event_definitions.STOP_SERVER)

    '''=======================================
    EVENT HANDLERS
    ======================================='''
    def on_server_started(self):
        self.refresh_ui()

    def on_server_stopped(self):
        self.refresh_ui()

    def on_message_received(self, socket, msg):
        pass
