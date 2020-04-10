import io
import json
from os import path, getcwd, listdir

def get_files_in_subdirectory(subdirectory):

    # get list of files in specified directory
    working_directory = getcwd()
    full_path = path.join(working_directory, subdirectory)
    files = [f for f in listdir(full_path) if path.isfile(path.join(full_path, f))]

    return files

def json_encode(obj, encoding="utf-8"):
    return json.dumps(obj, ensure_ascii=False).encode(encoding)

def json_decode(json_bytes, encoding="utf-8"):
    wrapper = io.TextIOWrapper(
        io.BytesIO(json_bytes), encoding=encoding, newline=""
    )
    obj = json.load(wrapper)
    wrapper.close()
    return obj
