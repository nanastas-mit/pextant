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
    def send_message(self, msg):

        print(f"sending '{type(msg).__name__}' message (id={msg.identifier()})")

        # send
        self.server.send_message_to_all_clients(msg)

    def on_message_received(self, socket, msg):

        print(f"message received from {socket}:\n"
              f"  ID: {msg.identifier()} ({msg.__class__.__name__})\n"
              f"  content: {msg.content}")

        # send available models response immediately
        if msg.identifier() == message_definitions.AvailableModelRequest.identifier():
            self.send_available_models_message()

        # otherwise, transform into relevant event
        else:

            # model load request
            if msg.identifier() == message_definitions.ModelLoadRequest.identifier():
                EventDispatcher.instance().trigger_event(
                    event_definitions.MODEL_LOAD_REQUESTED,
                    msg.model_to_load,
                    msg.max_slope
                )
            # start point set request
            elif msg.identifier() == message_definitions.StartPointSetRequest.identifier():
                EventDispatcher.instance().trigger_event(
                    event_definitions.START_POINT_SET_REQUESTED,
                    msg.row,
                    msg.column
                )
            # end point set request
            elif msg.identifier() == message_definitions.EndPointSetRequest.identifier():
                EventDispatcher.instance().trigger_event(
                    event_definitions.END_POINT_SET_REQUESTED,
                    msg.row,
                    msg.column
                )
            # radial obstacle set request
            elif msg.identifier() == message_definitions.RadialObstacleSetRequest.identifier():
                EventDispatcher.instance().trigger_event(
                    event_definitions.RADIAL_OBSTACLE_SET_REQUESTED,
                    msg.row,
                    msg.column,
                    msg.radius,
                    msg.state
                )
            # path find request
            elif msg.identifier() == message_definitions.PathFindRequest.identifier():
                EventDispatcher.instance().trigger_event(
                    event_definitions.PATH_FIND_REQUESTED
                )

    def on_send_message_requested(self, msg):

        # send it!
        self.send_message(msg)

    def send_available_models_message(self):

        # create message content
        available_models = PathManager.get_available_models()
        msg = message_definitions.AvailableModels(available_models)

        # send
        self.send_message(msg)

    '''=======================================
    EVENT HANDLERS
    ======================================='''
    def on_model_loaded(self, terrain_model: GridMeshModel):

        # create message content
        elevations = terrain_model.data.tolist()
        obstacles = terrain_model.obstacles.astype(int).tolist()
        msg = message_definitions.ModelLoaded(
            terrain_model.resolution,
            elevations,
            obstacles
        )

        # send
        self.send_message(msg)

    def on_start_point_set(self, row, column):

        # create message content
        msg = message_definitions.StartPointSet(row, column)

        # send
        self.send_message(msg)

    def on_end_point_set(self, row, column):

        # create message content
        msg = message_definitions.EndPointSet(row, column)

        # send
        self.send_message(msg)

    def on_obstacles_changed(self, obstacles):

        # create message content
        obstacles = obstacles.astype(int).tolist()
        msg = message_definitions.ObstaclesChanged(obstacles)

        # send
        self.send_message(msg)

    def on_path_found(self, path):

        # create message content
        msg = message_definitions.PathFound(path)

        # send
        self.send_message(msg)
