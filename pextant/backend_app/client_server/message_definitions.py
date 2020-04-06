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
# model selection
class AvailableModelRequest(BaseMessage):
    def __int__(self):
        super().__init__()

class AvailableModels(BaseMessage):
    def __init__(self, available_models):
        self.available_models = available_models
        super().__init__()

# model loading
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
    def __init__(self, row, column):
        self.row = row
        self.column = column
        super().__init__()

class StartPointSet(BaseMessage):
    def __init__(self, row, column):
        self.row = row
        self.column = column
        super().__init__()

class EndPointSetRequest(BaseMessage):
    def __init__(self, row, column):
        self.row = row
        self.column = column
        super().__init__()

class EndPointSet(BaseMessage):
    def __init__(self, row, column):
        self.row = row
        self.column = column
        super().__init__()

# obstacle setting
class RadialObstacleSetRequest(BaseMessage):
    def __init__(self, row, column, radius, state):
        self.row = row
        self.column = column
        self.radius = radius
        self.state = state
        super().__init__()

class ObstaclesChanged(BaseMessage):
    def __init__(self, obstacles):
        self.obstacles = obstacles
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

    # model selection
    AvailableModelRequest: next(_message_identifier_count),
    AvailableModels: next(_message_identifier_count),

    # model loading
    ModelLoadRequest: next(_message_identifier_count),
    ModelLoaded: next(_message_identifier_count),

    # endpoints
    StartPointSetRequest: next(_message_identifier_count),
    StartPointSet: next(_message_identifier_count),
    EndPointSetRequest: next(_message_identifier_count),
    EndPointSet: next(_message_identifier_count),

    # obstacles
    RadialObstacleSetRequest: next(_message_identifier_count),
    ObstaclesChanged: next(_message_identifier_count),

    # path
    PathFindRequest: next(_message_identifier_count),
    PathFound: next(_message_identifier_count),
}

def create_message_from_id(message_id, **kwargs):

    for cls, identifier in message_identifiers.items():
        if identifier == message_id:
            return cls(**kwargs)
