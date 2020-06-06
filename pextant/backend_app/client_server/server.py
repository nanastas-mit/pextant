import pextant.backend_app.events.event_definitions as event_definitions
import socket
import selectors
import traceback
from pextant.backend_app.app_component import AppComponent
from pextant.backend_app.events.event_dispatcher import EventDispatcher
from pextant.backend_app.client_server.client_data_stream_handler import ClientDataStreamHandler, SocketClosedException


class Server(AppComponent):
    """A simple server used for accepting client connections and handling subsequent communication"""

    '''=======================================
    FIELDS
    ======================================='''
    # consts
    CONNECTION_ACCEPT_SERVER_DATA = "SERVER_SOCKET"

    # properties
    @property
    def is_listening(self):
        return self.server_socket is not None

    '''=======================================
    STARTUP/SHUTDOWN
    ======================================='''
    def __init__(self, host_name, host_port, manager):

        super().__init__(manager)

        # create selector
        self.selector = selectors.DefaultSelector()

        # store server information, reference to socket
        self.server_address = (host_name, host_port)
        self.server_socket = None

        # store information about all clients that connect
        self.connected_client_handlers = {}

    def close(self):

        super().close()

        self.stop_listening()
        self.selector.close()

    def start_listening(self):

        # if we don't already have an active listening socket
        if self.server_socket is None:

            # create the server socket
            self.server_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(self.server_address)
            self.server_socket.listen()

            print(f"listening for clients at {self.server_address[0]}:{self.server_address[1]}")

            # register with selector (read only - only job is to accept connections)
            self.selector.register(self.server_socket, selectors.EVENT_READ, data=Server.CONNECTION_ACCEPT_SERVER_DATA)

    def stop_listening(self):

        # close all client connections
        self._close_all_client_sockets()

        # if we have a connection accept socket
        if self.server_socket:

            # shut it down
            self.selector.unregister(self.server_socket)
            self.server_socket.close()
            self.server_socket = None

            print("listening socket closed")

    '''=======================================
    UPDATES
    ======================================='''
    def update(self, delta_time):

        super().update(delta_time)

        # if we have no server socket, do nothing
        if self.server_socket is None:
            return

        # get all events that are currently ready
        events = self.selector.select(timeout=0)
        for key, mask in events:

            # check to see if socket is our connection server
            if key.data == Server.CONNECTION_ACCEPT_SERVER_DATA:

                # all this thing does is accept connections
                self._accept_pending_connection()

            # otherwise... (one of our connected, peer-to-peer sockets)
            else:

                # have the event handler process the event
                client_socket = key.fileobj
                client_event_handler = self.connected_client_handlers[client_socket]
                try:
                    client_event_handler.process_events(mask)

                # if client socket closes, just close on our end
                except SocketClosedException as e:
                    print("SocketClosedException:", e)
                    self._close_client_socket(client_socket)

                # some other exception - print it out
                except Exception as e:  # RuntimeError or ValueError
                    print(
                        "main: error: exception for",
                        f"{client_event_handler.address}:\n{traceback.format_exc()}",
                    )
                    self._close_client_socket(client_socket)

    '''=======================================
    CONNECTED CLIENTS
    ======================================='''
    def send_message_to_client(self, client_socket, msg):

        # if client is in list of connected
        if client_socket in self.connected_client_handlers:

            # get handler and send a message
            client_event_handler = self.connected_client_handlers[client_socket]
            client_event_handler.enqueue_message(msg)

    def send_message_to_all_clients(self, msg):

        # for each connected client
        for client_socket in self.connected_client_handlers.keys():

            # send the message
            self.send_message_to_client(client_socket, msg)

    def _accept_pending_connection(self):

        # accept connection
        client_socket, address = self.server_socket.accept()

        # register with our selector
        client_event_handler = ClientDataStreamHandler(self.selector, client_socket, address)
        events = selectors.EVENT_READ  # | selectors.EVENT_WRITE
        self.selector.register(client_socket, events)

        # add to container of connected clients
        self.connected_client_handlers[client_socket] = client_event_handler

        # dispatch event
        EventDispatcher.instance().trigger_event(event_definitions.CLIENT_CONNECTED, client_socket, address)

    def _close_client_socket(self, client_socket):

        # close the handler (will close socket) and remove from container
        if client_socket in self.connected_client_handlers:
            client_event_handler = self.connected_client_handlers[client_socket]
            del self.connected_client_handlers[client_socket]
            client_event_handler.close()

    def _close_all_client_sockets(self):

        # close all handlers
        for client_event_handler in self.connected_client_handlers.values():
            client_event_handler.close()

        # clear the container
        self.connected_client_handlers.clear()
