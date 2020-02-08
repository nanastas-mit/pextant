class AppComponent:

    def __init__(self, manager):

        # register self with manager
        self.manager = manager
        manager.register_component(self)

    def update(self, delta_time):
        pass

    def close(self):
        pass
