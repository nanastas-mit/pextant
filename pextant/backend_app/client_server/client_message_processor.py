import pextant.backend_app.events.event_definitions as event_definitions
import pextant.backend_app.client_server.message_definitions as message_definitions
from pextant.backend_app.app_component import AppComponent
from pextant.backend_app.dependency_injection import RequiredFeature, has_methods
from pextant.backend_app.events.event_dispatcher import EventDispatcher
from pextant.backend_app.path_manager import PathManager
from pextant.EnvironmentalModel import GridMeshModel


class ClientMessageProcessor(AppComponent):
    """class for handling pextant-specific handling of server-client messages"""

    '''=======================================
    STARTUP/SHUTDOWN
    ======================================='''
    def __init__(self, manager):

        super().__init__(manager)

        # required features
        self.server = RequiredFeature(
            "server",
            has_methods("send_message_to_all_clients")
        ).result

        # EVENT REGISTRATION
        event_dispatcher = EventDispatcher.instance()
        # send/receive
        event_dispatcher.register_listener(event_definitions.SEND_MESSAGE_REQUESTED, self.on_send_message_requested)
        event_dispatcher.register_listener(event_definitions.MESSAGE_RECEIVED, self.on_message_received)
        # path finding
        event_dispatcher.register_listener(event_definitions.MODEL_LOAD_COMPLETE, self.on_model_loaded)
        event_dispatcher.register_listener(event_definitions.START_POINT_SET_COMPLETE, self.on_start_point_set)
        event_dispatcher.register_listener(event_definitions.END_POINT_SET_COMPLETE, self.on_end_point_set)
        event_dispatcher.register_listener(event_definitions.RADIAL_OBSTACLE_SET_COMPLETE, self.on_obstacles_changed)
        event_dispatcher.register_listener(event_definitions.PATH_FIND_COMPLETE, self.on_path_found)

    '''=======================================
    MESSAGE PROCESSING
    ======================================='''
    def send_message(self, msg_type, msg_content):

        print(f"sending message {msg_type}, {msg_content}")

        # send
        self.server.send_message_to_all_clients(
            msg_type,
            msg_content
        )

    def on_message_received(self, socket, msg_type, data):

        print("message received ", socket, msg_type, data)

        # available models
        if msg_type == message_definitions.AVAILABLE_MODELS_REQUEST:
            self.send_available_models_message()

        # load model
        elif msg_type == message_definitions.MODEL_LOAD_REQUEST:
            EventDispatcher.instance().trigger_event(
                event_definitions.MODEL_LOAD_REQUESTED,
                data["model_to_load"],
                data["max_slope"]
            )

        # start set
        elif msg_type == message_definitions.START_POINT_SET_REQUEST:
            EventDispatcher.instance().trigger_event(
                event_definitions.START_POINT_SET_REQUESTED,
                data["row"],
                data["column"]
            )

        # end set
        elif msg_type == message_definitions.END_POINT_SET_REQUEST:
            EventDispatcher.instance().trigger_event(
                event_definitions.END_POINT_SET_REQUESTED,
                data["row"],
                data["column"]
            )

        # obstacle set
        elif msg_type == message_definitions.RADIAL_OBSTACLE_SET_REQUEST:
            EventDispatcher.instance().trigger_event(
                event_definitions.RADIAL_OBSTACLE_SET_REQUESTED,
                data["row"],
                data["column"],
                data["radius"],
                data["state"]
            )

        # find path
        elif msg_type == message_definitions.PATH_FIND_REQUEST:
            EventDispatcher.instance().trigger_event(
                event_definitions.PATH_FIND_REQUESTED
            )

    def on_send_message_requested(self, msg_type, msg_content):

        # send it!
        self.send_message(msg_type, msg_content)

    def send_available_models_message(self):

        # create message content
        available_models = PathManager.get_available_models()
        msg_content = {
            'available_models': available_models
        }

        # send
        self.send_message(
            message_definitions.AVAILABLE_MODELS,
            msg_content
        )

    '''=======================================
    EVENT HANDLERS
    ======================================='''
    def on_model_loaded(self, terrain_model: GridMeshModel):

        # create message content
        elevation_map = terrain_model.data.tolist()
        obstacles = terrain_model.obstacles.astype(int).tolist()
        msg_content = {
            'resolution': terrain_model.resolution,
            'elevation_map': elevation_map,
            'obstacles': obstacles,
        }

        # send
        self.send_message(
            message_definitions.MODEL_LOADED,
            msg_content
        )

    def on_start_point_set(self, row, column):

        # create message content
        msg_content = {
            'row': row,
            'column': column,
        }

        # send
        self.send_message(
            message_definitions.START_POINT_SET,
            msg_content
        )

    def on_end_point_set(self, row, column):

        # create message content
        msg_content = {
            'row': row,
            'column': column,
        }

        # send
        self.send_message(
            message_definitions.END_POINT_SET,
            msg_content
        )

    def on_obstacles_changed(self, obstacles):

        # create message content
        obstacles = obstacles.astype(int).tolist()
        msg_content = {
            'obstacles': obstacles,
        }

        # send
        self.send_message(
            message_definitions.OBSTACLES_CHANGED,
            msg_content
        )

    def on_path_found(self, path):

        # create message content
        msg_content = {
            'path': path,
        }

        # send
        self.send_message(
            message_definitions.OBSTACLES_CHANGED,
            msg_content
        )
