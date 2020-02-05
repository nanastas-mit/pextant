import pextant.backend_app.events.pextant_events as pextant_events
import time
from pextant.backend_app.events.event_dispatcher import EventDispatcher
from pextant.backend_app.backend_server import PextantServer
from pextant.backend_app.ui.ui_controller import UIController

HOST_NAME = 'localhost'
HOST_PORT = 3000


class AppStateManager:
    """The top level class of the app, controls the overall flow of the program (contains main loop, etc.)"""

    '''=======================================
    FIELDS
    ======================================='''
    # 'enum' for tracking app state
    INITIALIZING = 1
    RUNNING = 2
    PENDING_EXIT = 3

    '''=======================================
    STARTUP/SHUTDOWN
    ======================================='''
    def __init__(self, create_gui=False):

        self.nick_client = None  # TODO: make me better

        # set current state
        self.current_state = AppStateManager.INITIALIZING

        # register for events
        self.event_handlers = {
            pextant_events.START_SERVER: self.start_connection_accept_server,
            pextant_events.STOP_SERVER: self.stop_connection_accept_server,
            pextant_events.CLIENT_CONNECTED: self.on_client_connected,
            pextant_events.SEND_MESSAGE: self.on_send_message,
            pextant_events.MESSAGE_RECEIVED: self.on_message_received,
            pextant_events.UI_WINDOW_CLOSED: self.exit,
        }
        EventDispatcher.get_instance().set_event_listening_group(self.event_handlers, True)

        # create the connection server (only job is to listen for client connections)
        self.server = PextantServer(HOST_NAME, HOST_PORT)

        # if specified, create gui
        if create_gui:
            self.gui = UIController()
        else:
            self.gui = None
            self.server.start_listening()

    def exit(self):

        # stop server
        self.server.close()

        # stop listening for events
        EventDispatcher.get_instance().set_event_listening_group(self.event_handlers, False)

        # signal we should stop main loop
        self.current_state = AppStateManager.PENDING_EXIT

    '''=======================================
    UPDATES
    ======================================='''
    def mainloop(self):

        # set current state to running
        self.current_state = AppStateManager.RUNNING

        # main loop
        try:
            while self.current_state == AppStateManager.RUNNING:

                # update sub-components
                EventDispatcher.get_instance().update()
                self.server.update()
                if self.gui:
                    self.gui.update()

                # input
                self.handle_input()

                # wait until next cycle
                time.sleep(0.033)

        # on a keyboard interrupt, exit the app
        except KeyboardInterrupt:
            print("caught keyboard interrupt, exiting")
        finally:
            self.exit()

    def handle_input(self):
        pass

    '''=======================================
    EVENT HANDLERS
    ======================================='''
    def start_connection_accept_server(self):
        self.server.start_listening()

    def stop_connection_accept_server(self):
        self.server.stop_listening()

    def on_client_connected(self, client_socket, address):
        self.nick_client = client_socket
        print("client connected", client_socket, address)

    @staticmethod
    def on_message_received(socket, data):
        print("message received ", socket, data)

    def on_send_message(self, content):
        print("sending message ", content)
        self.server.send_message_to_client(self.nick_client, content)

