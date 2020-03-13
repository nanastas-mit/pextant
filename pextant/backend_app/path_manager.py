import os
import pextant.backend_app.events.event_definitions as event_definitions
from os import path as path
from pextant.backend_app.app_component import AppComponent
from pextant.backend_app.events.event_dispatcher import EventDispatcher
from pextant.EnvironmentalModel import load_legacy, GDALMesh, load_obstacle_map
from pextant.explorers import Astronaut
from pextant.lib.geoshapely import GeoPoint
from pextant.solvers.astarMesh import ExplorerCost
from pextant_cpp import PathFinder
from threading import Thread


class PathManager(AppComponent):
    """class for managing and keeping state of current path/terrain/model"""

    '''=======================================
    FIELDS
    ======================================='''
    # consts
    MODELS_DIRECTORY = "models"

    # properties
    @property
    def costs_cached(self):
        return self.path_finder.costs_cached

    @property
    def obstacles_cached(self):
        return self.path_finder.obstacles_cached

    @property
    def heuristics_cached(self):
        return self.path_finder.heuristics_cached

    @property
    def all_data_cached(self):
        return self.path_finder.all_cached

    '''=======================================
    STARTUP/SHUTDOWN
    ======================================='''
    def __init__(self, manager, threaded):

        super().__init__(manager)

        # threading references
        self.threaded = threaded
        self._threads = {}

        # register for events
        event_dispatcher: EventDispatcher = EventDispatcher.instance()
        event_dispatcher.register_listener(
            event_definitions.MODEL_LOAD_REQUESTED,
            self.create_threaded_switch(self.load_model)
        )
        event_dispatcher.register_listener(event_definitions.MODEL_UNLOAD_REQUESTED, self.unload_model)
        event_dispatcher.register_listener(event_definitions.START_POINT_SET_REQUESTED, self.set_start_point)
        event_dispatcher.register_listener(event_definitions.END_POINT_SET_REQUESTED, self.set_end_point)
        event_dispatcher.register_listener(event_definitions.RADIAL_OBSTACLE_SET_REQUESTED, self.set_radial_obstacle)
        event_dispatcher.register_listener(
            event_definitions.COSTS_CACHING_REQUESTED,
            self.create_threaded_switch(self.cache_costs)
        )
        event_dispatcher.register_listener(event_definitions.OBSTACLES_CACHING_REQUESTED, self.cache_obstacles)
        event_dispatcher.register_listener(event_definitions.HEURISTICS_CACHING_REQUESTED, self.cache_heuristics)
        event_dispatcher.register_listener(
            event_definitions.PATH_FIND_REQUESTED,
            self.create_threaded_switch(self.find_path)
        )

        # path variables
        self.path_finder = PathFinder()
        self.agent = Astronaut(80)
        self.terrain_model = None
        self.cost_function = None
        self.start_point = None
        self.end_point = None

    def close(self):

        super().close()

        # wait for existing threads to complete
        for _, thread in self._threads.items():
            thread.join()

    '''=======================================
    MODELS
    ======================================='''
    @staticmethod
    def get_available_models():

        # get list of files in models folder
        cwd = os.getcwd()
        models_dir = path.join(cwd, PathManager.MODELS_DIRECTORY)
        model_files = [f for f in os.listdir(models_dir) if path.isfile(path.join(models_dir, f))]

        return model_files

    def load_model(self, model_name, max_slope):

        # get the name of the file of the model to load
        local_path_file_name = path.join(PathManager.MODELS_DIRECTORY, model_name)
        _, extension = path.splitext(local_path_file_name)

        # load the model
        if extension == '.txt':  # text file is 'legacy'
            grid_mesh = load_legacy(local_path_file_name)
            self.terrain_model = grid_mesh.loadSubSection(maxSlope=max_slope, cached=False)
        elif extension == '.png':  # .png is obstacle 'maze'
            self.terrain_model = load_obstacle_map(local_path_file_name)
        else:  # otherwise, a DEM
            grid_mesh = GDALMesh(local_path_file_name)
            self.terrain_model = grid_mesh.loadSubSection(maxSlope=max_slope, cached=False)

        # load the kernel, cost function
        kernel_list = self.terrain_model.searchKernel.getKernel().tolist()
        self.path_finder.set_kernel(kernel_list)
        self.cost_function = ExplorerCost(self.agent, self.terrain_model, 'Energy', cached=False)

        # dispatch loaded event
        EventDispatcher.instance().trigger_event(event_definitions.MODEL_LOAD_COMPLETE, self.terrain_model)

    def unload_model(self):

        # unload model, cost function
        self.terrain_model = None
        self.cost_function = None

        # start/end
        self.start_point = None
        self.end_point = None

        # clear out cached data in path finder
        self.path_finder.clear_all()

        # dispatch unloaded event
        EventDispatcher.instance().trigger_event(event_definitions.MODEL_UNLOAD_COMPLETE)

    '''=======================================
    ENDPOINTS
    ======================================='''
    def set_start_point(self, row, column):

        # if no terrain model, early out
        if not self.terrain_model:
            return

        # set point
        geo_point = GeoPoint(self.terrain_model.ROW_COL, row, column)
        self.start_point = geo_point

        # dispatch event
        EventDispatcher.instance().trigger_event(event_definitions.START_POINT_SET_COMPLETE, row, column)

    def set_end_point(self, row, column):

        # if no terrain model, early out
        if not self.terrain_model:
            return

        # clear cached heuristics
        self.path_finder.clear_heuristics()

        # set the point
        geo_point = GeoPoint(self.terrain_model.ROW_COL, row, column)
        self.end_point = geo_point

        # dispatch event
        EventDispatcher.instance().trigger_event(event_definitions.END_POINT_SET_COMPLETE, row, column)

    '''=======================================
    CACHING
    ======================================='''
    def cache_costs(self):

        # if no terrain model or cost function, early out
        if not self.terrain_model or not self.cost_function:
            return

        # cache costs, list-ify, and store in pathfinder
        cached_costs = self.cost_function.create_costs_cache()
        cost_map = cached_costs["energy"].tolist()
        self.path_finder.cache_costs(cost_map)

        # dispatch caching complete event
        EventDispatcher.instance().trigger_event(event_definitions.COSTS_CACHING_COMPLETE)

    def cache_obstacles(self):

        # if no terrain model, early out
        if not self.terrain_model:
            return

        # list-ify the obstacles and store in pathfinder
        obstacle_map = self.terrain_model.obstacle_mask().tolist()
        self.path_finder.cache_obstacles(obstacle_map)

        # dispatch caching complete event
        EventDispatcher.instance().trigger_event(event_definitions.OBSTACLES_CACHING_COMPLETE)

    def cache_heuristics(self):

        # if no terrain model, cost function, or end_point, early out
        if not self.terrain_model or not self.cost_function or not self.end_point:
            return

        # cache heuristics in pathfinder
        elt = self.terrain_model.getMeshElement(self.end_point)
        heuristics_map = self.cost_function.create_heuristic_cache((elt.x, elt.y)).tolist()
        self.path_finder.cache_heuristics(heuristics_map)

        # dispatch caching complete event
        EventDispatcher.instance().trigger_event(event_definitions.HEURISTICS_CACHING_COMPLETE)

    '''=======================================
    PATH FINDING & MANIPULATION
    ======================================='''
    def set_radial_obstacle(self, row, column, radius, obstacle_state):

        # clear cached obstacles
        self.path_finder.clear_obstacles()

        # convert to appropriate coordinates
        geo_point = GeoPoint(self.terrain_model.ROW_COL, row, column)
        elt = self.terrain_model.getMeshElement(geo_point)

        self.terrain_model.set_circular_obstacle(
            (elt.x, elt.y),
            radius * self.terrain_model.resolution,
            obstacle_state
        )

        # dispatch obstacle setting complete
        EventDispatcher.instance().trigger_event(event_definitions.RADIAL_OBSTACLE_SET_COMPLETE)

    def find_path(self):

        # if no terrain model, start_point, end_point, or cache, early out
        if not self.terrain_model or not self.start_point or not self.end_point or not self.all_data_cached:
            return

        # reset any prior progress
        self.path_finder.reset_progress()

        # solve!
        source = self.terrain_model.getMeshElement(self.start_point).mesh_coordinate  # unscaled (row, column)
        target = self.terrain_model.getMeshElement(self.end_point).mesh_coordinate  # unscaled (row, column)
        found_path = self.path_finder.astar_solve(source, target)

        # dispatch path found event
        EventDispatcher.instance().trigger_event(event_definitions.PATH_FIND_COMPLETE, found_path)

    '''=======================================
    HELPERS
    ======================================='''
    def create_threaded_switch(self, func):

        # start new thread if specified
        if self.threaded:

            def threaded_func(*args):
                thread_name = func.__name__
                thread = Thread(name=thread_name, target=func, args=args)
                self._threads[thread_name] = thread
                thread.start()
            return threaded_func

        # otherwise, just call the function
        else:

            def unthreaded_func(*args):
                func(*args)
            return unthreaded_func
