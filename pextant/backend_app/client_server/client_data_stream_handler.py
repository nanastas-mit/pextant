import io
import json
import pextant.backend_app.events.event_definitions as event_definitions
import sys
import selectors
import struct
from pextant.backend_app.events.event_dispatcher import EventDispatcher


class SocketClosedException(Exception):
    """Exception raised when client socket closes"""
    pass


class ClientDataStreamHandler:
    """class for handling reading and writing to client socket"""

    '''=======================================
    CLASS FIELDS
    ======================================='''
    PROTO_HEADER_LENGTH = 4  # size of unsigned long

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
    STARTUP/SHUTDOWN
    ======================================='''
    def __init__(self, selector, socket, address):

        # socket communication objects
        self.selector = selector
        self.socket = socket
        self.address = address

        # buffers to store data read from or to be sent to
        self._recv_buffer = b""
        self._send_buffer = b""

        # message header info
        self._jsonheader_len = None
        self.jsonheader = None

    def close(self):
        print("closing connection to", self.address)
        try:
            self.selector.unregister(self.socket)
        except Exception as e:
            print(
                f"error: selector.unregister() exception for",
                f"{self.address}: {repr(e)}",
            )

        try:
            self.socket.close()
        except OSError as e:
            print(
                f"error: socket.close() exception for",
                f"{self.address}: {repr(e)}",
            )
        finally:
            # Delete reference to socket object for garbage collection
            self.socket = None

    '''=======================================
    EVENT HANDLING
    ======================================='''
    def process_events(self, mask):

        # pending read, do read
        if mask & selectors.EVENT_READ:
            self.read()

        # pending write, do write
        if mask & selectors.EVENT_WRITE:
            self.write()

    def _set_selector_events_mask(self, mode):
        """Set selector to listen for events: mode is 'r', 'w', or 'rw'."""
        if mode == "r":
            events = selectors.EVENT_READ
        elif mode == "w":
            events = selectors.EVENT_WRITE
        elif mode == "rw":
            events = selectors.EVENT_READ | selectors.EVENT_WRITE
        else:
            raise ValueError(f"Invalid events mask mode {repr(mode)}.")
        self.selector.modify(self.socket, events, data=self)

    '''=======================================
    READ METHODS
    ======================================='''
    def read(self):

        # read in raw data
        self._read()

        # if we haven't yet processed the protoheader, do so
        if self._jsonheader_len is None:
            self._process_protoheader()

        # if we haven't yet processed the jsonheader, do so
        if self._jsonheader_len and self.jsonheader is None:
            self._process_jsonheader()

        # process the actual message body
        if self.jsonheader:
            self._process_message_body()

    def _read(self):

        # attempt to read the data
        try:
            data = self.socket.recv(4096)
        except BlockingIOError:  # Resource temporarily unavailable (errno EWOULDBLOCK)
            pass

        # read success!
        else:
            # append any new received data to our buffer
            if data:
                self._recv_buffer += data

            # data is empty, socket has been closed
            else:
                raise SocketClosedException(f"Peer at {self.address} closed.")

    def _process_protoheader(self):

        # if we have at least the size of the protoheader in our buffer...
        header_length = ClientDataStreamHandler.PROTO_HEADER_LENGTH
        if len(self._recv_buffer) >= header_length:

            # process it and remove relevant data from buffer front
            self._jsonheader_len = struct.unpack(
                "<i", self._recv_buffer[:header_length]
            )[0]
            self._recv_buffer = self._recv_buffer[header_length:]

    def _process_jsonheader(self):

        # if we have at least the size of the json header in our buffer...
        header_length = self._jsonheader_len
        if len(self._recv_buffer) >= header_length:

            # process it and remove relevant data from buffer front
            self.jsonheader = self._json_decode(
                self._recv_buffer[:header_length], "utf-8"
            )
            self._recv_buffer = self._recv_buffer[header_length:]

            # check to make sure header has everything required
            for required_field in ClientDataStreamHandler.HEADER_REQUIRED_FIELDS:
                if required_field not in self.jsonheader:
                    raise ValueError(f'Missing required header "{required_field}".')

    def _process_message_body(self):

        # if we haven't read in entire content yet, hold off
        content_length = self.jsonheader[ClientDataStreamHandler.CONTENT_LENGTH_KEY]
        if not len(self._recv_buffer) >= content_length:
            return

        # pull off relevant bytes from received buffer
        serialized_content = self._recv_buffer[:content_length]
        self._recv_buffer = self._recv_buffer[content_length:]

        # convert from json
        encoding = self.jsonheader[ClientDataStreamHandler.CONTENT_ENCODING_KEY]
        content = self._json_decode(serialized_content, encoding)

        # dispatch event
        EventDispatcher.instance().trigger_event(
            event_definitions.MESSAGE_RECEIVED,
            self.socket,
            self.jsonheader[ClientDataStreamHandler.MESSAGE_TYPE_KEY],
            content)

        # reset everything back to original state
        self._reset_after_read()

    def _reset_after_read(self):
        self._jsonheader_len = None
        self.jsonheader = None

    @staticmethod
    def _json_decode(json_bytes, encoding):
        tiow = io.TextIOWrapper(
            io.BytesIO(json_bytes), encoding=encoding, newline=""
        )
        obj = json.load(tiow)
        tiow.close()
        return obj

    '''=======================================
    WRITE METHODS
    ======================================='''
    def write(self):

        # if we have a message to send
        if self._send_buffer is not None:
            self._send_message()

    def _send_message(self):

        # if there's something to send
        if self._send_buffer:

            # send it!
            self.socket.sendall(self._send_buffer)

            # reset
            self._reset_after_write()

    def enqueue_message(self, msg_type, msg_content):

        # set writeable
        self._set_selector_events_mask("rw")

        # create message
        content_encoding = "utf-8"
        content_bytes = self._json_encode(msg_content, "utf-8")

        # serialize the message
        serialized_message = self._serialize_message(msg_type, content_encoding, content_bytes)
        self._send_buffer += serialized_message

    def _serialize_message(self, message_type, content_encoding, content_bytes):

        # create header as a python dictionary
        json_header = {
            ClientDataStreamHandler.MESSAGE_TYPE_KEY: message_type,
            ClientDataStreamHandler.CONTENT_ENCODING_KEY: content_encoding,
            ClientDataStreamHandler.BYTE_ORDER_KEY: sys.byteorder,
            ClientDataStreamHandler.CONTENT_LENGTH_KEY: len(content_bytes),
        }

        # convert dictionary header to json byte string
        json_header_bytes = self._json_encode(json_header, "utf-8")

        # create the proto header
        proto_header = struct.pack("<i", len(json_header_bytes))

        # form the entire message and return
        message = proto_header + json_header_bytes + content_bytes
        return message

    def _reset_after_write(self):
        self._send_buffer = b""
        self._set_selector_events_mask("r")

    @staticmethod
    def _json_encode(obj, encoding):
        return json.dumps(obj, ensure_ascii=False).encode(encoding)




