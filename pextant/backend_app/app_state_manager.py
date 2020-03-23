import pextant.backend_app.events.event_definitions as event_definitions
import time
from pextant.backend_app.client_server.server import Server
from pextant.backend_app.dependency_injection import FeatureBroker
from pextant.backend_app.events.event_dispatcher import EventDispatcher
from pextant.backend_app.client_server.client_message_processor import ClientMessageProcessor
from pextant.backend_app.path_manager import PathManager
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

        # set current state
        self.current_state = AppStateManager.INITIALIZING

        # initialize time-tracking variables
        self.start_time = time.time()
        self.time_last_frame = self.start_time
        self.delta_time = 0.0

        # initialize registered components list
        self._registered_components = []

        # register for events
        self.event_handlers = {
            event_definitions.START_SERVER: self.start_connection_accept_server,
            event_definitions.STOP_SERVER: self.stop_connection_accept_server,
            event_definitions.UI_WINDOW_CLOSED: self.exit,
        }
        EventDispatcher.instance().set_event_listening_group(self.event_handlers, True)

        # COMPONENTS
        # path manager (threaded if gui will be used)
        self.path_manager = PathManager(self, threaded=create_gui)
        FeatureBroker.instance().provide("path_manager", self.path_manager)
        # server
        self.server = Server(HOST_NAME, HOST_PORT, self)
        FeatureBroker.instance().provide("server", self.server)
        # message manager
        self.message_manager = ClientMessageProcessor(self)
        # gui
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
        EventDispatcher.instance().set_event_listening_group(self.event_handlers, False)

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
                EventDispatcher.instance().update(self.delta_time)
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
