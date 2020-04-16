from itertools import count


'''=======================================
HEADER
======================================='''
# protoheader (carries size of actual header)
PROTO_HEADER_LENGTH = 4  # size of unsigned long

# header
MESSAGE_IDENTIFIER_KEY = "message_identifier"
CONTENT_ENCODING_KEY = "content_encoding"
BYTE_ORDER_KEY = "byteorder"
CONTENT_LENGTH_KEY = "content_length"
HEADER_REQUIRED_FIELDS = (
    MESSAGE_IDENTIFIER_KEY,
    CONTENT_ENCODING_KEY,
    BYTE_ORDER_KEY,
    CONTENT_LENGTH_KEY,
)

'''=======================================
BASE
======================================='''
class BaseMessage:
    @classmethod
    def identifier(cls):
        return message_identifiers[cls]

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
class ObstacleListSetRequest(BaseMessage):
    def __init__(self, coordinate_list, state):
        self.coordinate_list = coordinate_list
        self.state = state
        super().__init__()

class ObstacleListSet(BaseMessage):
    def __init__(self, coordinate_list, state):
        self.coordinate_list = coordinate_list
        self.state = state
        super().__init__()

# path finding
class PathFindRequest(BaseMessage):
    def __init__(self):
        super().__init__()

class PathFound(BaseMessage):
    def __init__(self, path):
        self.path = path
        super().__init__()


'''=======================================
IDs
======================================='''
_message_identifier_count = count(0)
message_identifiers = {
    BaseMessage: -1,

    # general
    SimpleMessage: next(_message_identifier_count),

    # scenarios
    AvailableScenarioRequest: next(_message_identifier_count),
    AvailableScenarios: next(_message_identifier_count),
    ScenarioLoadRequest: next(_message_identifier_count),
    ScenarioLoaded: next(_message_identifier_count),

    # models
    AvailableModelRequest: next(_message_identifier_count),
    AvailableModels: next(_message_identifier_count),
    ModelLoadRequest: next(_message_identifier_count),
    ModelLoaded: next(_message_identifier_count),

    # endpoints
    StartPointSetRequest: next(_message_identifier_count),
    StartPointSet: next(_message_identifier_count),
    EndPointSetRequest: next(_message_identifier_count),
    EndPointSet: next(_message_identifier_count),

    # obstacles
    ObstacleListSetRequest: next(_message_identifier_count),
    ObstacleListSet: next(_message_identifier_count),

    # path
    PathFindRequest: next(_message_identifier_count),
    PathFound: next(_message_identifier_count),
}

def create_message_from_id(message_id, **kwargs):

    for cls, identifier in message_identifiers.items():
        if identifier == message_id:
            return cls(**kwargs)
