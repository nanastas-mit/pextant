import pextant.backend_app.events.event_definitions as event_definitions
import pextant.backend_app.client_server.message_definitions as message_definitions
import pextant.backend_app.ui.fonts as fonts
import tkinter as tk
from pextant.backend_app.events.event_dispatcher import EventDispatcher
from pextant.backend_app.ui.page_base import PageBase
from itertools import count


class PageServer(PageBase):
    """handles all functionality of server page"""

    def __init__(self, master):

        super().__init__(master, {
            event_definitions.START_SERVER: self.on_server_started,
            event_definitions.STOP_SERVER: self.on_server_stopped,
            event_definitions.MESSAGE_RECEIVED: self.on_message_received,
        })

        # references for later use
        self.start_server_btn = None
        self.stop_server_btn = None
        self.received_action_lbl = None
        self.received_value_lbl = None

        # setup
        self.initial_setup()

    def initial_setup(self):

        '''
        def key_r(event):
            print("released {0}", repr(event.char))
        def key_p(event):
            print("pressed {0}", repr(event.char))
        def key(event):
            print("key {0}", repr(event.char))
        def callback(event):
            print("clicked at ({0}, {1})", event.x, event.y)
        self.gui_window.bind("<Key>", key)
        self.gui_window.bind("<KeyPress>", key_p)
        self.gui_window.bind("<KeyRelease>", key_r)
        self.gui_window.bind("<Button-1>", callback)
        '''

        current_row = count(0)

        # Title
        title = tk.Label(self, text="SERVER", font=fonts.LARGE_FONT)
        title.grid(column=0, row=next(current_row))

        # start/stop server
        def start_server():
            EventDispatcher.instance().trigger_event(event_definitions.START_SERVER)
        def stop_server():
            EventDispatcher.instance().trigger_event(event_definitions.STOP_SERVER)
        self.start_server_btn = tk.Button(self, text="Start Server", command=start_server, justify=tk.LEFT)
        self.start_server_btn.grid(column=0, row=next(current_row), sticky=tk.W)
        self.stop_server_btn = tk.Button(self, text="Stop Server", command=stop_server, justify=tk.LEFT)
        self.stop_server_btn.grid(column=0, row=next(current_row), sticky=tk.W)

        # action/value headings
        action_value_heading_row = next(current_row)
        tk.Label(self, text="action", font=("Arial", 8)).grid(column=1, row=action_value_heading_row)
        tk.Label(self, text="value", font=("Arial", 8)).grid(column=2, row=action_value_heading_row)

        # send message
        send_button_row = next(current_row)
        action_tx = tk.Entry(self, width=10, justify=tk.LEFT)
        action_tx.grid(column=1, row=send_button_row, sticky=tk.W)
        value_tx = tk.Entry(self, width=20, justify=tk.LEFT)
        value_tx.grid(column=2, row=send_button_row, sticky=tk.W)
        def send_message():
            msg = message_definitions.SimpleMessage(action_tx.get(), value_tx.get())
            EventDispatcher.instance().trigger_event(
                event_definitions.SEND_MESSAGE_REQUESTED,
                msg
            )
        send_message_btn = tk.Button(self, text="Send Message", command=send_message, justify=tk.LEFT)
        send_message_btn.grid(column=0, row=send_button_row, sticky=tk.W)

        # receive message
        receive_row = next(current_row)
        tk.Label(self, text="Received:", justify=tk.LEFT).grid(column=0, row=receive_row, sticky=tk.W)
        self.received_action_lbl = tk.Label(self, justify=tk.LEFT)
        self.received_action_lbl.grid(column=1, row=receive_row, sticky=tk.W)
        self.received_value_lbl = tk.Label(self, justify=tk.LEFT)
        self.received_value_lbl.grid(column=2, row=receive_row, sticky=tk.W)

        # combo box
        '''
        combo = ttk.Combobox(self.root, justify=tk.LEFT)
        combo['values'] = (1, 2, 3, 4, 5, "Text")
        combo.current(1)  # set the selected item
        combo.grid(column=0, row=next(current_row), sticky=tk.W)
        '''

    '''=======================================
    EVENT HANDLERS
    ======================================='''
    def on_server_started(self):
        pass

    def on_server_stopped(self):
        pass

    def on_message_received(self, socket, msg):
        pass
