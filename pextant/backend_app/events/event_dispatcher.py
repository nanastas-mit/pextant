import queue
import threading


class EventDispatcher:
    """class for registering for and dispatching events"""

    '''=======================================
    SINGLETON INTERFACE
    ======================================='''
    @staticmethod
    def get_instance():
        if not EventDispatcher.__instance:
            EventDispatcher()
        return EventDispatcher.__instance
    __instance = None

    '''=======================================
    STARTUP/SHUTDOWN
    ======================================='''
    def __init__(self):

        # singleton check/initialization
        if EventDispatcher.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            EventDispatcher.__instance = self

        self.delayed_message_queue = queue.Queue()
        self.event_list = {}

    '''=======================================
    UPDATE
    ======================================='''
    def update(self):

        # process messages until there are no more
        while True:
            try:
                delayed = self.delayed_message_queue.get(block=False)
            except queue.Empty:  # raised when queue is empty
                break
            delayed()

    '''=======================================
    EVENT REGISTRATION/TRIGGERING
    ======================================='''
    def register_listener(self, event_name, listener_func):

        # if not on main thread, delay performing the action
        if threading.current_thread() is not threading.main_thread():
            self.delay_until_main_thread(self.register_listener, event_name, listener_func)
            return

        # if event has not yet been registered for anything, add to dict
        if event_name not in self.event_list:
            self.event_list[event_name] = []

        # add new listener to list of registered listeners (if not already there)
        registered_functions = self.event_list[event_name]
        if listener_func not in registered_functions:
            registered_functions.append(listener_func)

    def unregister_listener(self, event_name, listener_func):

        # if not on main thread, delay performing the action
        if threading.current_thread() is not threading.main_thread():
            self.delay_until_main_thread(self.unregister_listener, event_name, listener_func)
            return

        # if no event of this name, early out
        if event_name not in self.event_list:
            return

        # remove listener from list
        registered_functions = self.event_list[event_name]
        if listener_func in registered_functions:
            registered_functions.remove(listener_func)

    def set_event_listening_group(self, event_handlers, on):

        # note whether we are registering or unregistering
        set_registration_function = self.register_listener if on else self.unregister_listener

        for event_name, registered_function in event_handlers.items():
            set_registration_function(event_name, registered_function)

    def trigger_event(self, event_name, *argv):

        # if not on main thread, delay performing the action
        if threading.current_thread() is not threading.main_thread():
            self.delay_until_main_thread(self.trigger_event, event_name, *argv)
            return

        # if no event of this name, early out
        if event_name not in self.event_list:
            return

        # call all listeners
        registered_functions = self.event_list[event_name]
        for listener_func in registered_functions:
            listener_func(*argv)

    def delay_until_main_thread(self, delayed_func, *argv):
        delayed = DelayUntilMainThreadMessage(delayed_func, *argv)
        self.delayed_message_queue.put(delayed)


class DelayUntilMainThreadMessage:
    def __init__(self, delayed_func, *argv):
        self.delayed_func = delayed_func
        self.argv = argv

    def __call__(self, *args, **kwargs):
        self.delayed_func(*self.argv)