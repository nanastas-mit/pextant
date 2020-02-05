from pextant.backend_app.events.event_dispatcher import EventDispatcher
from itertools import count
import pextant.backend_app.events.pextant_events as pextant_events
import tkinter as tk
import tkinter.ttk as ttk


class UIController:
    """main class for controlling UI window"""

    '''=======================================
    STARTUP/SHUTDOWN
    ======================================='''
    def __init__(self):

        # create and setup root
        self.root = tk.Tk()
        self.root.title("Sextant")
        self.root.geometry('640x420')
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_closed)
        self.window_open = True

        # create tabs
        self.tab_control = ttk.Notebook(self.root)
        self.tabs = [
            self.create_tab(ServerTab, "Server"),
            self.create_tab(TestTab, "Test"),
        ]
        self.tab_control.pack(expand=1, fill='both')

    def on_window_closed(self):

        # inform all tabs of window close
        for tab in self.tabs:
            tab.on_window_closed()

        self.window_open = False
        EventDispatcher.get_instance().trigger_event(pextant_events.UI_WINDOW_CLOSED)

    '''=======================================
    UPDATES
    ======================================='''
    def update(self):
        if self.window_open:
            self.root.update_idletasks()
            self.root.update()

    '''=======================================
    TAB MANIPULATION
    ======================================='''
    def create_tab(self, cls, name):

        frame = ttk.Frame(self.tab_control)
        self.tab_control.add(frame, text=name)
        tab = cls(self, frame)

        return tab


class UITabBase:
    """base class for all tabs in UI"""

    event_handlers = {}

    def __init__(self, parent, tab_frame):

        # register self with parent
        self.parent = parent
        self.tab_frame = tab_frame

        # register listeners
        EventDispatcher.get_instance().set_event_listening_group(self.event_handlers, True)

    def on_window_closed(self):

        # unregister listeners
        EventDispatcher.get_instance().set_event_listening_group(self.event_handlers, False)


class ServerTab(UITabBase):
    """handles all functionality of server tab"""

    def __init__(self, parent, tab_frame):

        # specify event handlers
        self.event_handlers = {
            pextant_events.START_SERVER: self.on_server_started,
            pextant_events.STOP_SERVER: self.on_server_stopped,
            pextant_events.MESSAGE_RECEIVED: self.on_message_received,
        }

        # parent initialize (must come after event_handler setting)
        super().__init__(parent, tab_frame)

        # references for later use
        self.start_server_btn = None
        self.stop_server_btn = None
        self.received_action_lbl = None
        self.received_value_lbl = None

        # setup
        self.initial_setup()

    def initial_setup(self):

        # widgets: https://likegeeks.com/python-gui-examples-tkinter-tutorial/
        # events/bindings: https://effbot.org/tkinterbook/tkinter-events-and-bindings.htm

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
        title = tk.Label(self.tab_frame, text="SERVER", font=("Arial Bold", 24))
        title.grid(column=0, row=next(current_row))

        # start/stop server
        def start_server():
            EventDispatcher.get_instance().trigger_event(pextant_events.START_SERVER)
        def stop_server():
            EventDispatcher.get_instance().trigger_event(pextant_events.STOP_SERVER)
        self.start_server_btn = tk.Button(self.tab_frame, text="Start Server", command=start_server, justify=tk.LEFT)
        self.start_server_btn.grid(column=0, row=next(current_row), sticky=tk.W)
        self.stop_server_btn = tk.Button(self.tab_frame, text="Stop Server", command=stop_server, justify=tk.LEFT)
        self.stop_server_btn.grid(column=0, row=next(current_row), sticky=tk.W)

        # action/value headings
        action_value_heading_row = next(current_row)
        tk.Label(self.tab_frame, text="action", font=("Arial", 8)).grid(column=1, row=action_value_heading_row)
        tk.Label(self.tab_frame, text="value", font=("Arial", 8)).grid(column=2, row=action_value_heading_row)

        # send message
        send_button_row = next(current_row)
        action_tx = tk.Entry(self.tab_frame, width=10, justify=tk.LEFT)
        action_tx.grid(column=1, row=send_button_row, sticky=tk.W)
        value_tx = tk.Entry(self.tab_frame, width=20, justify=tk.LEFT)
        value_tx.grid(column=2, row=send_button_row, sticky=tk.W)
        def send_message():
            greet_msg = {"action": action_tx.get(), "value": value_tx.get()}
            EventDispatcher.get_instance().trigger_event(pextant_events.SEND_MESSAGE, greet_msg)
        send_message_btn = tk.Button(self.tab_frame, text="Send Message", command=send_message, justify=tk.LEFT)
        send_message_btn.grid(column=0, row=send_button_row, sticky=tk.W)

        # receive message
        receive_row = next(current_row)
        tk.Label(self.tab_frame, text="Received:", justify=tk.LEFT).grid(column=0, row=receive_row, sticky=tk.W)
        self.received_action_lbl = tk.Label(self.tab_frame, justify=tk.LEFT)
        self.received_action_lbl.grid(column=1, row=receive_row, sticky=tk.W)
        self.received_value_lbl = tk.Label(self.tab_frame, justify=tk.LEFT)
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

    def on_message_received(self, socket, data):

        self.received_action_lbl["text"] = data["action"]
        self.received_value_lbl["text"] = data["value"]


class TestTab(UITabBase):
    """handles all functionality of test tab"""

    def __init__(self, parent, tab_frame):
        super().__init__(parent, tab_frame)
