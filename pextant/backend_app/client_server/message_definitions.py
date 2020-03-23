from itertools import count

_message_id_count = count(0) 

'''=======================================
GENERAL
======================================='''
SIMPLE = next(_message_id_count)
VARIABLE = next(_message_id_count)

'''=======================================
PATH FINDING
======================================='''
# model selection
AVAILABLE_MODELS_REQUEST = next(_message_id_count)
AVAILABLE_MODELS = next(_message_id_count)

# model loading
MODEL_LOAD_REQUEST = next(_message_id_count)
MODEL_LOADED = next(_message_id_count)

# endpoints
START_POINT_SET_REQUEST = next(_message_id_count)
START_POINT_SET = next(_message_id_count)
END_POINT_SET_REQUEST = next(_message_id_count)
END_POINT_SET = next(_message_id_count)

# obstacle setting
RADIAL_OBSTACLE_SET_REQUEST = next(_message_id_count)
OBSTACLES_CHANGED = next(_message_id_count)

# path finding
PATH_FIND_REQUEST = next(_message_id_count)
PATH_FOUND = next(_message_id_count)
