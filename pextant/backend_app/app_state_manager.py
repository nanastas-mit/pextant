import pextant.backend_app.events.event_definitions as event_definitions
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
    # 'consts'
    SECONDS_PER_FRAME = 0.05

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
            event_definitions.START_SERVER: self.start_connection_accept_server,
            event_definitions.STOP_SERVER: self.stop_connection_accept_server,
            event_definitions.CLIENT_CONNECTED: self.on_client_connected,
            event_definitions.SEND_MESSAGE: self.on_send_message,
            event_definitions.MESSAGE_RECEIVED: self.on_message_received,
            event_definitions.UI_WINDOW_CLOSED: self.exit,
        }
        EventDispatcher.get_instance().set_event_listening_group(self.event_handlers, True)

        # initialize time-tracking variables
        self.start_time = time.time()
        self.time_last_frame = self.start_time
        self.delta_time = 0.0

        # initialize registered components list
        self._registered_components = []

        # create the connection server (only job is to listen for client connections)
        self.server = PextantServer(HOST_NAME, HOST_PORT, self)

        # if specified, create gui
        if create_gui:
            self.gui = UIController(self)
        else:
            self.gui = None
            self.server.start_listening()

    def exit(self):

        # exit sub-components
        for component in self._registered_components:
            component.close()
        self.unregister_all_components()

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

                # loop start timings
                loop_begin_time = time.time()
                self.delta_time = loop_begin_time - self.time_last_frame

                # update sub-components
                EventDispatcher.get_instance().update(self.delta_time)
                for component in self._registered_components:
                    component.update(self.delta_time)

                # loop end timings
                self.time_last_frame = loop_begin_time
                loop_end_time = time.time()
                total_loop_time = loop_end_time - loop_begin_time

                # wait until next cycle
                sleep_time = max(AppStateManager.SECONDS_PER_FRAME - total_loop_time, 0.001)
                time.sleep(sleep_time)

        # on a keyboard interrupt, exit the app
        except KeyboardInterrupt:
            print("caught keyboard interrupt, exiting")
        finally:
            self.exit()

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

    '''=======================================
    COMPONENT MANAGEMENT
    ======================================='''
    def register_component(self, component):

        if component not in self._registered_components:
            self._registered_components.append(component)

    def unegister_component(self, component):

        if component in self._registered_components:
            self._registered_components.remove(component)

    def unregister_all_components(self):
        self._registered_components.clear()
