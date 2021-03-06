import sys
sys.path.append('../../..')
import io
import json
import socket
import struct
import sys
import tkinter as tk
import threading
import pextant.backend_app.client_server.message_definitions as message_definitions
from itertools import count
from pextant.backend_app.client_server.client_data_stream_handler import ClientDataStreamHandler

HOST_NAME = 'localhost'
HOST_PORT = 3000

def _json_encode(obj, encoding):
    return json.dumps(obj, ensure_ascii=False).encode(encoding)

def _json_decode(json_bytes, encoding):
    tiow = io.TextIOWrapper(
        io.BytesIO(json_bytes), encoding=encoding, newline=""
    )
    obj = json.load(tiow)
    tiow.close()
    return obj

def create_message(action, value):

    print("create_request", action, value)

    msg = message_definitions.SimpleMessage(action, value)
    content_encoding = "utf-8"
    content_bytes = _json_encode(msg.content, content_encoding)

    jsonheader = {
        message_definitions.MESSAGE_TYPE_KEY: msg.message_type(),
        message_definitions.CONTENT_ENCODING_KEY: content_encoding,
        message_definitions.BYTE_ORDER_KEY: sys.byteorder,
        message_definitions.CONTENT_LENGTH_KEY: len(content_bytes),
    }
    jsonheader_bytes = _json_encode(jsonheader, content_encoding)
    message_hdr = struct.pack("<i", len(jsonheader_bytes))
    message = message_hdr + jsonheader_bytes + content_bytes

    return message

def create_gui(client):

    root = tk.Tk()
    root.title("Pextant Client")
    root.geometry('350x200')
    current_row = count(0)

    # label
    title = tk.Label(root, text="CLIENT", font=("Arial Bold", 24))
    title.grid(column=0, row=next(current_row))

    # send message
    def send_message():
        action = "search"
        value = "fun cat facts"
        msg = create_message(action, value)
        client.sendall(msg)
    start_server_btn = tk.Button(root, text="Send Message", command=send_message, justify=tk.LEFT)
    start_server_btn.grid(column=0, row=next(current_row), sticky=tk.W)

    return root

def process_received(recv_buffer):
    recv_buffer, jsonheader_len = process_protoheader(recv_buffer)
    recv_buffer, jsonheader = process_jsonheader(recv_buffer, jsonheader_len)
    response = process_response(recv_buffer, jsonheader)
    return response

def process_protoheader(recv_buffer):

    proto_header_len = 4
    jsonheader_len = 0

    # get the json header length
    if len(recv_buffer) >= proto_header_len:
        jsonheader_len = struct.unpack("<i", recv_buffer[:proto_header_len])[0]

    return recv_buffer[proto_header_len:], jsonheader_len

def process_jsonheader(recv_buffer, jsonheader_len):

    header_length = jsonheader_len
    jsonheader = None

    if len(recv_buffer) >= header_length:
        jsonheader = _json_decode(
            recv_buffer[:header_length], "utf-8"
        )
        recv_buffer = recv_buffer[header_length:]

    return recv_buffer, jsonheader

def process_response(_recv_buffer, jsonheader):

    content_len = jsonheader[message_definitions.CONTENT_LENGTH_KEY]
    if not len(_recv_buffer) >= content_len:
        return

    data = _recv_buffer[:content_len]
    _recv_buffer = _recv_buffer[content_len:]

    encoding = jsonheader[message_definitions.CONTENT_ENCODING_KEY]
    response = _json_decode(data, encoding)

    return response

def main():

    # connect
    print('try connect')
    client = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    client.connect((HOST_NAME, HOST_PORT))
    print('connected')

    # create receive thread
    stop_receiving = False
    def receive_loop():
        while not stop_receiving:
            recv_buffer = client.recv(4096)
            if recv_buffer == b'':
                print("breaking out of receive loop")
                break
            msg = process_received(recv_buffer)
            print("received data:", msg)
    receive_thread = threading.Thread(target=receive_loop)
    receive_thread.start()

    # create gui
    root = create_gui(client)
    root.mainloop()

    stop_receiving = True
    receive_thread.join()
    client.close()
    print("goodbye")


if __name__ == "__main__":
    main()
