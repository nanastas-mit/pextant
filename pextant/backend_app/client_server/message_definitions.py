from itertools import count


'''=======================================
HEADER
======================================='''
# protoheader (carries size of actual header)
PROTO_HEADER_LENGTH = 4  # size of unsigned long

# header
MESSAGE_TYPE_KEY = "message_type"
CONTENT_ENCODING_KEY = "content_encoding"
BYTE_ORDER_KEY = "byteorder"
CONTENT_LENGTH_KEY = "content_length"
HEADER_REQUIRED_FIELDS = (
    MESSAGE_TYPE_KEY,
    CONTENT_ENCODING_KEY,
    BYTE_ORDER_KEY,
    CONTENT_LENGTH_KEY,
)

'''=======================================
BASE
======================================='''
class BaseMessage:
    @classmethod
    def message_type(cls):
        return message_types[cls]

    def __init__(self):
        self.content = {}
        self._create_content()

    def _create_content(self):
        self.content.clear()
        instance_variables = vars(self)
        for var_name, var in instance_variables.items():
            if var != self.content:
                self.content[var_name] = var


'''=======================================
GENERAL
======================================='''
class SimpleMessage(BaseMessage):
    def __init__(self, action, value):
        self.action = action
        self.value = value
        super().__init__()


'''=======================================
PATH FINDING
======================================='''
# scenarios
class AvailableScenarioRequest(BaseMessage):
    def __int__(self):
        super.__init__()

class AvailableScenarios(BaseMessage):
    def __init__(self, available_scenarios):
        self.available_scenarios = available_scenarios
        super().__init__()

class ScenarioLoadRequest(BaseMessage):
    def __init__(self, scenario_to_load):
        self.scenario_to_load = scenario_to_load
        super().__init__()

class ScenarioLoaded(BaseMessage):
    def __init__(self, resolution, elevations, obstacles, start_coordinates, start_heading, end_coordinates):
        self.resolution = resolution
        self.elevations = elevations
        self.obstacles = obstacles
        self.start_coordinates = start_coordinates
        self.start_heading = start_heading
        self.end_coordinates = end_coordinates
        super().__init__()

class ScenarioLoadEndpointsRequest(BaseMessage):
    def __init__(self, scenario_to_load):
        self.scenario_to_load = scenario_to_load
        super().__init__()

class ScenarioEndpointsLoaded(BaseMessage):
    def __init__(self, start_coordinates, start_heading, end_coordinates):
        self.start_coordinates = start_coordinates
        self.start_heading = start_heading
        self.end_coordinates = end_coordinates
        super().__init__()

# models
class AvailableModelRequest(BaseMessage):
    def __init__(self):
        super().__init__()

class AvailableModels(BaseMessage):
    def __init__(self, available_models):
        self.available_models = available_models
        super().__init__()

class ModelLoadRequest(BaseMessage):
    def __init__(self, model_to_load, max_slope):
        self.model_to_load = model_to_load
        self.max_slope = max_slope
        super().__init__()

class ModelLoaded(BaseMessage):
    def __init__(self, resolution, elevations, obstacles):
        self.resolution = resolution
        self.elevations = elevations
        self.obstacles = obstacles
        super().__init__()

# endpoints
class StartPointSetRequest(BaseMessage):
    def __init__(self, coordinates):
        self.coordinates = coordinates
        super().__init__()

class StartPointSet(BaseMessage):
    def __init__(self, coordinates):
        self.coordinates = coordinates
        super().__init__()

class EndPointSetRequest(BaseMessage):
    def __init__(self, coordinates):
        self.coordinates = coordinates
        super().__init__()

class EndPointSet(BaseMessage):
    def __init__(self, coordinates):
        self.coordinates = coordinates
        super().__init__()

# obstacle setting
class ObstaclesListSetRequest(BaseMessage):
    def __init__(self, coordinates_list, state):
        self.coordinates_list = coordinates_list
        self.state = state
        super().__init__()

class ObstaclesChanged(BaseMessage):
    def __init__(self, coordinates_list, state):
        self.coordinates_list = coordinates_list
        self.state = state
        super().__init__()

# path finding
class PathFindRequest(BaseMessage):
    def __init__(self):
        super().__init__()

class PathFindFromPositionRequest(BaseMessage):
    def __init__(self, coordinates):
        self.coordinates = coordinates
        super().__init__()

class PathFound(BaseMessage):
    def __init__(self, path, distance_cost, energy_cost):
        self.path = path
        self.distance_cost = distance_cost
        self.energy_cost = energy_cost
        super().__init__()


'''=======================================
IDs
======================================='''
_message_type_count = count(0)
message_types = {
    BaseMessage: -1,

    # general
    SimpleMessage: next(_message_type_count),

    # scenarios
    AvailableScenarioRequest: next(_message_type_count),
    AvailableScenarios: next(_message_type_count),
    ScenarioLoadRequest: next(_message_type_count),
    ScenarioLoaded: next(_message_type_count),
    ScenarioLoadEndpointsRequest: next(_message_type_count),
    ScenarioEndpointsLoaded: next(_message_type_count),

    # models
    AvailableModelRequest: next(_message_type_count),
    AvailableModels: next(_message_type_count),
    ModelLoadRequest: next(_message_type_count),
    ModelLoaded: next(_message_type_count),

    # endpoints
    StartPointSetRequest: next(_message_type_count),
    StartPointSet: next(_message_type_count),
    EndPointSetRequest: next(_message_type_count),
    EndPointSet: next(_message_type_count),

    # obstacles
    ObstaclesListSetRequest: next(_message_type_count),
    ObstaclesChanged: next(_message_type_count),

    # path
    PathFindRequest: next(_message_type_count),
    PathFindFromPositionRequest: next(_message_type_count),
    PathFound: next(_message_type_count),
}

def create_message_from_type(message_id, **kwargs):

    for cls, message_type in message_types.items():
        if message_type == message_id:
            return cls(**kwargs)
