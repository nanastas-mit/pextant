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
        event_dispatcher.register_listener(
            event_definitions.SCENARIO_LOAD_ENDPOINTS_COMPLETE,
            self.on_scenario_endpoints_loaded
        )
        event_dispatcher.register_listener(event_definitions.MODEL_LOAD_COMPLETE, self.on_model_loaded)
        event_dispatcher.register_listener(event_definitions.START_POINT_SET_COMPLETE, self.on_start_point_set)
        event_dispatcher.register_listener(event_definitions.END_POINT_SET_COMPLETE, self.on_end_point_set)
        event_dispatcher.register_listener(
            event_definitions.OBSTACLE_CHANGE_COMPLETE,
            self.on_obstacles_changed
        )
        event_dispatcher.register_listener(event_definitions.PATH_FIND_COMPLETE, self.on_path_found)

    '''=======================================
    MESSAGE PROCESSING
    ======================================='''
    def send_message(self, msg):

        print(f"sending '{type(msg).__name__}' message (id={msg.message_type()})")

        # send
        self.server.send_message_to_all_clients(msg)

    def on_message_received(self, socket, msg):

        print(f"message received from {socket}:\n"
              f"  ID: {msg.message_type()} ({msg.__class__.__name__})\n"
              f"  content: {msg.content}")

        # send available models/scenarios response immediately
        if msg.message_type() == message_definitions.AvailableModelRequest.message_type():
            self.send_available_models_message()
        elif msg.message_type() == message_definitions.AvailableScenarioRequest.message_type():
            self.send_available_scenarios_message()

        # otherwise, transform into relevant event
        else:

            # scenario load request
            if msg.message_type() == message_definitions.ScenarioLoadRequest.message_type():
                EventDispatcher.instance().trigger_event(
                    event_definitions.SCENARIO_LOAD_REQUESTED,
                    msg.scenario_to_load
                )
            # scenario load request
            elif msg.message_type() == message_definitions.ScenarioLoadEndpointsRequest.message_type():
                EventDispatcher.instance().trigger_event(
                    event_definitions.SCENARIO_LOAD_ENDPOINTS_REQUESTED,
                    msg.scenario_to_load
                )
            # model load request
            elif msg.message_type() == message_definitions.ModelLoadRequest.message_type():
                EventDispatcher.instance().trigger_event(
                    event_definitions.MODEL_LOAD_REQUESTED,
                    msg.model_to_load,
                    msg.max_slope
                )
            # start point set request
            elif msg.message_type() == message_definitions.StartPointSetRequest.message_type():
                EventDispatcher.instance().trigger_event(
                    event_definitions.START_POINT_SET_REQUESTED,
                    msg.coordinates,
                    Cartesian.SYSTEM_NAME
                )
            # end point set request
            elif msg.message_type() == message_definitions.EndPointSetRequest.message_type():
                EventDispatcher.instance().trigger_event(
                    event_definitions.END_POINT_SET_REQUESTED,
                    msg.coordinates,
                    Cartesian.SYSTEM_NAME
                )
            # obstacle set request
            elif msg.message_type() == message_definitions.ObstaclesListSetRequest.message_type():
                EventDispatcher.instance().trigger_event(
                    event_definitions.OBSTACLE_LIST_SET_REQUESTED,
                    msg.coordinates_list,
                    Cartesian.SYSTEM_NAME,
                    msg.state,
                    True
                )
            # path find request
            elif msg.message_type() == message_definitions.PathFindRequest.message_type():
                EventDispatcher.instance().trigger_event(
                    event_definitions.PATH_FIND_REQUESTED
                )
            # find from position request
            elif msg.message_type() == message_definitions.PathFindFromPositionRequest.message_type():
                EventDispatcher.instance().trigger_event(
                    event_definitions.PATH_FIND_FROM_POSITION_REQUESTED,
                    msg.coordinates,
                    Cartesian.SYSTEM_NAME
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
    def on_scenario_loaded(self, scenario_name, terrain_model, start_point, end_point, initial_heading):

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

    def on_scenario_endpoints_loaded(self, start_point, end_point, initial_heading):

        # endpoints
        start_coordinates = start_point.to(self.path_manager.terrain_model.ROW_COL).tolist()
        end_coordinates = end_point.to(self.path_manager.terrain_model.ROW_COL).tolist()

        # create message content
        msg = message_definitions.ScenarioEndpointsLoaded(
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

    def on_obstacles_changed(self, coordinates_list, state):

        # create message content
        msg = message_definitions.ObstaclesChanged(coordinates_list, state)

        # send
        self.send_message(msg)

    def on_path_found(self, path, distance_cost, energy_cost):

        # create message content
        numpy_list = np.array(path)
        path = numpy_list.astype(int).tolist()  # argument 'path' is list of numpy ints - which json decoder fails with
        msg = message_definitions.PathFound(path, distance_cost, energy_cost)

        # send
        self.send_message(msg)
