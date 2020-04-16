import numpy as np
import pextant.backend_app.events.event_definitions as event_definitions
import pextant.backend_app.client_server.message_definitions as message_definitions
from pextant.backend_app.app_component import AppComponent
from pextant.backend_app.dependency_injection import RequiredFeature, has_attributes, has_methods
from pextant.backend_app.events.event_dispatcher import EventDispatcher
from pextant.lib.geoshapely import Cartesian, GeoPoint
from pextant.backend_app.path_manager import PathManager


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
        self.path_manager = RequiredFeature(
            "path_manager",
            has_attributes("terrain_model")
        ).result

        # EVENT REGISTRATION
        event_dispatcher = EventDispatcher.instance()
        # send/receive
        event_dispatcher.register_listener(event_definitions.SEND_MESSAGE_REQUESTED, self.on_send_message_requested)
        event_dispatcher.register_listener(event_definitions.MESSAGE_RECEIVED, self.on_message_received)
        # path finding
        event_dispatcher.register_listener(event_definitions.SCENARIO_LOAD_COMPLETE, self.on_scenario_loaded)
        event_dispatcher.register_listener(event_definitions.MODEL_LOAD_COMPLETE, self.on_model_loaded)
        event_dispatcher.register_listener(event_definitions.START_POINT_SET_COMPLETE, self.on_start_point_set)
        event_dispatcher.register_listener(event_definitions.END_POINT_SET_COMPLETE, self.on_end_point_set)
        event_dispatcher.register_listener(
            event_definitions.OBSTACLE_LIST_SET_COMPLETE,
            self.on_obstacle_list_set
        )
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

        # send available models/scenarios response immediately
        if msg.identifier() == message_definitions.AvailableModelRequest.identifier():
            self.send_available_models_message()
        elif msg.identifier() == message_definitions.AvailableScenarioRequest.identifier():
            self.send_available_scenarios_message()

        # otherwise, transform into relevant event
        else:

            # scenario load request
            if msg.identifier() == message_definitions.ScenarioLoadRequest.identifier():
                EventDispatcher.instance().trigger_event(
                    event_definitions.SCENARIO_LOAD_REQUESTED,
                    msg.scenario_to_load
                )
            # model load request
            elif msg.identifier() == message_definitions.ModelLoadRequest.identifier():
                EventDispatcher.instance().trigger_event(
                    event_definitions.MODEL_LOAD_REQUESTED,
                    msg.model_to_load,
                    msg.max_slope
                )
            # start point set request
            elif msg.identifier() == message_definitions.StartPointSetRequest.identifier():
                EventDispatcher.instance().trigger_event(
                    event_definitions.START_POINT_SET_REQUESTED,
                    msg.coordinates,
                    Cartesian.SYSTEM_NAME
                )
            # end point set request
            elif msg.identifier() == message_definitions.EndPointSetRequest.identifier():
                EventDispatcher.instance().trigger_event(
                    event_definitions.END_POINT_SET_REQUESTED,
                    msg.coordinates,
                    Cartesian.SYSTEM_NAME
                )
            # obstacle set request
            elif msg.identifier() == message_definitions.ObstacleListSetRequest.identifier():
                EventDispatcher.instance().trigger_event(
                    event_definitions.OBSTACLE_LIST_SET_REQUESTED,
                    msg.coordinate_list,
                    Cartesian.SYSTEM_NAME,
                    msg.state,
                    True
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

    def send_available_scenarios_message(self):

        # create message content
        available_scenarios = PathManager.get_available_scenarios()
        msg = message_definitions.AvailableScenarios(available_scenarios)

        # send
        self.send_message(msg)

    '''=======================================
    EVENT HANDLERS
    ======================================='''
    def on_scenario_loaded(self, terrain_model, start_point, end_point, initial_heading):

        # model
        elevations = terrain_model.data.tolist()
        obstacles = terrain_model.obstacles.astype(int).tolist()

        # endpoints
        start_coordinates = start_point.to(self.path_manager.terrain_model.ROW_COL).tolist()
        end_coordinates = end_point.to(self.path_manager.terrain_model.ROW_COL).tolist()

        # create message content
        msg = message_definitions.ScenarioLoaded(
            terrain_model.resolution,
            elevations,
            obstacles,
            start_coordinates,
            initial_heading,
            end_coordinates
        )

        # send
        self.send_message(msg)

    def on_model_loaded(self, terrain_model):

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

    def on_start_point_set(self, start_point: GeoPoint):

        # create message content
        coordinates = start_point.to(self.path_manager.terrain_model.ROW_COL).tolist()
        msg = message_definitions.StartPointSet(coordinates)

        # send
        self.send_message(msg)

    def on_end_point_set(self, start_point: GeoPoint):

        # create message content
        coordinates = start_point.to(self.path_manager.terrain_model.ROW_COL).tolist()
        msg = message_definitions.EndPointSet(coordinates)

        # send
        self.send_message(msg)

    def on_obstacle_list_set(self, geo_point_list, state):

        # create list of [row, col] coordinates
        coordinate_list = []
        for geo_point in geo_point_list:
            coordinate = geo_point.to(self.path_manager.terrain_model.ROW_COL).tolist()
            coordinate_list.append(coordinate)

        # create message content
        msg = message_definitions.ObstacleListSet(coordinate_list, state)

        # send
        self.send_message(msg)

    def on_path_found(self, path):

        # create message content
        numpy_list = np.array(path)
        path = numpy_list.astype(int).tolist()  # argument 'path' is list of numpy ints - which json decoder fails with
        msg = message_definitions.PathFound(path)

        # send
        self.send_message(msg)
