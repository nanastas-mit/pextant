import numpy as np
import pextant.backend_app.events.event_definitions as event_definitions
import pextant.backend_app.utils as utils
from os import path
from pextant.backend_app.app_component import AppComponent
from pextant.backend_app.events.event_dispatcher import EventDispatcher
from pextant.EnvironmentalModel import load_legacy, GDALMesh, load_obstacle_map
from pextant.explorers import Astronaut, TraversePath
from pextant.lib.geoshapely import GeoPoint, GeoPolygon, LatLon, Cartesian, LAT_LONG
from pextant.solvers.astarMesh import ExplorerCost
from pextant_cpp import PathFinder
from threading import Thread


class PathManager(AppComponent):
    """class for managing and keeping state of current path/terrain/model"""

    '''=======================================
    FIELDS
    ======================================='''
    # consts
    SCENARIOS_DIRECTORY = 'scenarios'
    MODELS_DIRECTORY = 'models'
    OBSTACLES_DIRECTORY = 'obstacles'

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
            event_definitions.SCENARIO_LOAD_REQUESTED,
            self.create_threaded_switch(self.load_scenario)
        )
        event_dispatcher.register_listener(
            event_definitions.SCENARIO_LOAD_ENDPOINTS_REQUESTED,
            self.load_scenario_endpoints
        )
        event_dispatcher.register_listener(
            event_definitions.SCENARIO_LOAD_OBSTACLE_REQUEST,
            self.load_scenario_obstacles
        )
        event_dispatcher.register_listener(
            event_definitions.MODEL_LOAD_REQUESTED,
            self.create_threaded_switch(self.load_model)
        )
        event_dispatcher.register_listener(event_definitions.MODEL_UNLOAD_REQUESTED, self.unload_model)
        event_dispatcher.register_listener(event_definitions.START_POINT_SET_REQUESTED, self.set_start_point)
        event_dispatcher.register_listener(event_definitions.END_POINT_SET_REQUESTED, self.set_end_point)
        event_dispatcher.register_listener(event_definitions.RADIAL_OBSTACLE_SET_REQUESTED, self.set_radial_obstacle)
        event_dispatcher.register_listener(event_definitions.OBSTACLE_LIST_SET_REQUESTED, self.set_obstacle_list),
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
        event_dispatcher.register_listener(
            event_definitions.PATH_FIND_FROM_POSITION_REQUESTED,
            self.create_threaded_switch(self.find_path_from_position)
        )

        # path variables
        self.path_finder = PathFinder()
        self.agent = Astronaut(80)
        self.terrain_model = None
        self.cost_function = None
        self.start_point = None
        self.end_point = None
        self.found_path = None
        self.path_distance = -1
        self.path_energy = -1

    def close(self):

        super().close()

        # wait for existing threads to complete
        for _, thread in self._threads.items():
            thread.join()

    '''=======================================
    SCENARIOS
    ======================================='''
    @staticmethod
    def get_available_scenarios():
        """gets list of available scenarios to be loaded.
        A scenario is a set of features that are needed to produce a full 'path-walking' experience -
        a model, a max slope, a start point, an initial heading, and an end point"""

        return utils.get_files_in_subdirectory(PathManager.SCENARIOS_DIRECTORY)

    def load_scenario(self, scenario_to_load):
        """Loads the specified scenario.
        A scenario is a set of features that are needed to produce a full 'path-walking' experience -
        a model, a max slope, a start point, an initial heading, and an end point"""

        # read in the scenario file
        scenario: dict = utils.read_file_as_json(scenario_to_load, PathManager.SCENARIOS_DIRECTORY)

        # decode json
        model_file = scenario['model']
        max_slope = scenario['max_slope']
        start_coordinates = scenario['start']
        end_coordinates = scenario['end']
        coordinate_system = scenario['coordinate_system']
        start_heading = scenario['start_heading']
        obstacles_file = scenario.get('obstacles', None)
        obstacles_list_file = scenario.get('obstacles_list', None)

        # model
        self.load_model(model_file, max_slope, False)
        # obstacles
        if obstacles_file:
            json_object = utils.read_file_as_json(obstacles_file, PathManager.OBSTACLES_DIRECTORY)
            self.terrain_model.set_obstacles(json_object['obstacles'])
        # obstacles list
        elif obstacles_list_file:
            json_object = utils.read_file_as_json(obstacles_list_file, PathManager.OBSTACLES_DIRECTORY)
            obstacles_list = json_object['obstacles']
            obstacles_grid = np.zeros(self.terrain_model.shape, dtype=bool)
            for coordinates in obstacles_list:
                obstacles_grid[coordinates[0], coordinates[1]] = True
            self.terrain_model.set_obstacles(obstacles_grid)
        # endpoint setting
        self.set_start_point(start_coordinates, coordinate_system, False)
        self.set_end_point(end_coordinates, coordinate_system, False)
        # caching
        self.cache_costs(False)
        self.cache_obstacles(False)
        self.cache_heuristics(False)

        # all done! dispatch event
        EventDispatcher.instance().trigger_event(
            event_definitions.SCENARIO_LOAD_COMPLETE,
            scenario_to_load,
            self.terrain_model,
            self.start_point,
            self.end_point,
            start_heading
        )

    def load_scenario_endpoints(self, scenario_to_load):
        """Loads the endpoints listed in specified scenario."""

        # read in the scenario file
        local_path_file_name = path.join(PathManager.SCENARIOS_DIRECTORY, scenario_to_load)
        with open(local_path_file_name, 'rb') as in_file:
            json_bytes = in_file.read()

        # decode json
        scenario: dict = utils.json_decode(json_bytes)
        start_coordinates = scenario['start']
        end_coordinates = scenario['end']
        coordinate_system = scenario['coordinate_system']
        start_heading = scenario['start_heading']

        # endpoint setting
        self.set_start_point(start_coordinates, coordinate_system, False)
        self.set_end_point(end_coordinates, coordinate_system, False)
        # caching
        self.cache_heuristics(False)

        # all done! dispatch event
        EventDispatcher.instance().trigger_event(
            event_definitions.SCENARIO_LOAD_ENDPOINTS_COMPLETE,
            self.start_point,
            self.end_point,
            start_heading
        )

    def load_scenario_obstacles(self, scenario_to_load):

        # clear cached obstacles
        self.path_finder.clear_obstacles()

        # read in the scenario file
        scenario: dict = utils.read_file_as_json(scenario_to_load, PathManager.SCENARIOS_DIRECTORY)
        obstacles_file = scenario.get('obstacles', None)
        obstacles_list_file = scenario.get('obstacles_list', None)

        # obstacles
        if obstacles_file:
            json_object = utils.read_file_as_json(obstacles_file, PathManager.OBSTACLES_DIRECTORY)
            self.terrain_model.set_obstacles(json_object['obstacles'])
        # obstacles list
        elif obstacles_list_file:
            json_object = utils.read_file_as_json(obstacles_list_file, PathManager.OBSTACLES_DIRECTORY)
            obstacles_list = json_object['obstacles']
            obstacles_grid = np.zeros(self.terrain_model.shape, dtype=bool)
            for coordinates in obstacles_list:
                obstacles_grid[coordinates[0], coordinates[1]] = True
            self.terrain_model.set_obstacles(obstacles_grid)

        # get new obstacles
        new_obstacles = self.terrain_model.obstacles.astype(bool)

        # dispatch obstacle setting complete
        EventDispatcher.instance().trigger_event(
            event_definitions.SCENARIO_LOAD_OBSTACLE_COMPLETE,
            new_obstacles
        )

    '''=======================================
    MODELS
    ======================================='''
    @staticmethod
    def get_available_models():
        """gets list of available model files that can be loaded"""

        return utils.get_files_in_subdirectory(PathManager.MODELS_DIRECTORY)

    def load_model(self, model_to_load, max_slope, dispatch_completed_event=True):
        """load terrain model from data at specified 'model_to_load' location"""

        # clear everything
        self.path_finder.clear_all()

        # get the name of the file of the model to load
        local_path_file_name = path.join(PathManager.MODELS_DIRECTORY, model_to_load)
        _, extension = path.splitext(local_path_file_name)

        # load the model
        if extension == '.txt':  # text file is 'legacy'
            grid_mesh = load_legacy(local_path_file_name)
            self.terrain_model = grid_mesh.loadSubSection(maxSlope=max_slope, cached=True)
        elif extension == '.png':  # .png is obstacle 'maze'
            self.terrain_model = load_obstacle_map(local_path_file_name)
        elif extension == '.img' or extension == '.tif':  # .img and .tif are DEMs
            grid_mesh = GDALMesh(local_path_file_name)
            self.terrain_model = grid_mesh.loadSubSection(maxSlope=max_slope, cached=True)
        else:
            print(f"File type {extension} not valid for model loading!")
            return

        # load the kernel, cost function
        kernel_list = self.terrain_model.searchKernel.getKernel().tolist()
        self.path_finder.set_kernel(kernel_list)
        self.cost_function = ExplorerCost(self.agent, self.terrain_model, 'Energy', cached=True)

        # dispatch loaded event
        if dispatch_completed_event:
            EventDispatcher.instance().trigger_event(
                event_definitions.MODEL_LOAD_COMPLETE,
                self.terrain_model
            )

    def unload_model(self):
        """Unload (and clear cache) of whatever model is in memory"""

        # unload model, cost function
        self.terrain_model = None
        self.cost_function = None

        # start/end
        self.start_point = None
        self.end_point = None

        # clear out cached data in path finder
        self.path_finder.clear_all()

        # path itself
        self.found_path = None
        self.path_distance = -1
        self.path_energy = -1

        # dispatch unloaded event
        EventDispatcher.instance().trigger_event(event_definitions.MODEL_UNLOAD_COMPLETE)

    '''=======================================
    ENDPOINTS
    ======================================='''
    def set_start_point(self, coordinates, coordinate_system, dispatch_completed_event=True):
        """specify the point at which path-finding should begin"""

        # if no terrain model, early out
        if not self.terrain_model:
            return

        # set start
        self.start_point = self.create_geo_point_from_coordinates(coordinates, coordinate_system)

        # dispatch event
        if dispatch_completed_event:
            EventDispatcher.instance().trigger_event(event_definitions.START_POINT_SET_COMPLETE, self.start_point)

    def set_end_point(self, coordinates, coordinate_system, dispatch_completed_event=True):
        """specify the point at which path-finding should end"""

        # if no terrain model, early out
        if not self.terrain_model:
            return

        # clear cached heuristics
        self.path_finder.clear_heuristics()

        # set the point
        self.end_point = self.create_geo_point_from_coordinates(coordinates, coordinate_system)

        # dispatch event
        if dispatch_completed_event:
            EventDispatcher.instance().trigger_event(event_definitions.END_POINT_SET_COMPLETE, self.end_point)

    '''=======================================
    CACHING
    ======================================='''
    def cache_costs(self, dispatch_completed_event=True):
        """calculates costs from every node to all of its 8 adjacent nodes, stores
        that data in path_finder (C++) memory. Having data + algorithm in C++ speeds things up considerably"""

        # if no terrain model or cost function, early out
        if not self.terrain_model or not self.cost_function:
            return

        # cache costs, list-ify, and store in pathfinder
        cached_costs = self.cost_function.create_costs_cache()
        cost_map = cached_costs["energy"].tolist()
        self.path_finder.cache_costs(cost_map)

        # dispatch caching complete event
        if dispatch_completed_event:
            EventDispatcher.instance().trigger_event(event_definitions.COSTS_CACHING_COMPLETE)

    def cache_obstacles(self, dispatch_completed_event=True):
        """stores obstacle data in path_finder (C++) memory.
        Having data + algorithm in C++ speeds things up considerably"""

        # if no terrain model, early out
        if not self.terrain_model:
            return

        # list-ify the obstacles and store in pathfinder
        obstacle_map = self.terrain_model.obstacles.astype(int).tolist()
        self.path_finder.cache_obstacles(obstacle_map)

        # dispatch caching complete event
        if dispatch_completed_event:
            EventDispatcher.instance().trigger_event(event_definitions.OBSTACLES_CACHING_COMPLETE)

    def cache_heuristics(self, dispatch_completed_event=True):
        """calculates heuristic cost from every node to the specified end point, stores
        that data in path_finder (C++) memory. Having data + algorithm in C++ speeds things up considerably."""

        # if no terrain model, cost function, or end_point, early out
        if not self.terrain_model or not self.cost_function or not self.end_point:
            return

        # cache heuristics in pathfinder
        elt = self.terrain_model.getMeshElement(self.end_point)
        heuristics_map = self.cost_function.create_heuristic_cache((elt.x, elt.y)).tolist()
        self.path_finder.cache_heuristics(heuristics_map)

        # dispatch caching complete event
        if dispatch_completed_event:
            EventDispatcher.instance().trigger_event(event_definitions.HEURISTICS_CACHING_COMPLETE)

    '''=======================================
    OBSTACLES
    ======================================='''
    def set_radial_obstacle(self, coordinates, coordinate_system, radius, state, cache_immediate=False):
        """Mark a circle of specified radius at the specified location as either
        an obstacle (state=true) or passable (state=false)"""

        # clear cached obstacles
        self.path_finder.clear_obstacles()

        # store original obstacles
        original_obstacles = self.terrain_model.obstacles.astype(int)
        if isinstance(original_obstacles, np.ma.core.MaskedArray):
            original_obstacles = original_obstacles.filled(0)

        # convert to appropriate coordinates
        geo_point = self.create_geo_point_from_coordinates(coordinates, coordinate_system)
        elt = self.terrain_model.getMeshElement(geo_point)

        # TODO: USE setRadialKeepOutZone?
        self.terrain_model.set_circular_obstacle(
            (elt.x, elt.y),
            radius * self.terrain_model.resolution,
            state
        )

        # cache immediately if specified
        if cache_immediate:
            self.cache_obstacles()

        # get new obstacles
        new_obstacles = self.terrain_model.obstacles.astype(int)
        if isinstance(original_obstacles, np.ma.core.MaskedArray):
            new_obstacles = original_obstacles.filled(0)

        # create list of changed points
        changed_obstacles = new_obstacles - original_obstacles
        row_col_coordinates_list = np.array(changed_obstacles.nonzero()).transpose().tolist()

        # dispatch obstacle change complete
        EventDispatcher.instance().trigger_event(
            event_definitions.OBSTACLE_CHANGE_COMPLETE,
            row_col_coordinates_list,
            state
        )

    def set_obstacle_list(self, coordinates_list, coordinate_system, state, cache_immediate=False):
        """Mark coordinates specified in list as either
        an obstacle (state=true) or passable (state=false)"""

        # clear cached obstacles
        self.path_finder.clear_obstacles()

        # go through all coordinates in list, create geo_point list
        geo_point_list = []
        for coordinates in coordinates_list:
            geo_point = self.create_geo_point_from_coordinates(coordinates, coordinate_system)
            geo_point_list.append(geo_point)

        # set the obstacles at specified points
        self.terrain_model.set_obstacle_list(geo_point_list, state)

        # cache immediately if specified
        if cache_immediate:
            self.cache_obstacles()

        # convert list to [row, col] coordinates
        row_col_coordinates_list = [geo_point.to(self.terrain_model.ROW_COL).tolist() for geo_point in geo_point_list]

        # dispatch obstacle setting complete
        EventDispatcher.instance().trigger_event(
            event_definitions.OBSTACLE_CHANGE_COMPLETE,
            row_col_coordinates_list,
            state
        )

    def clear_all_obstacles(self, cache_immediate=False):
        """Clears all obstacles / makes all regions of terrain 'passable'"""

        # clear cached obstacles
        self.path_finder.clear_obstacles()

        # store original obstacles
        original_obstacles = self.terrain_model.obstacles.astype(bool)
        if isinstance(original_obstacles, np.ma.core.MaskedArray):
            original_obstacles = original_obstacles.filled(False)

        # unset obstacle status at each current obstacle point
        self.terrain_model.set_obstacle_map(original_obstacles, False)

        # cache immediately if specified
        if cache_immediate:
            self.cache_obstacles()

        # create list of changed points
        row_col_coordinates_list = np.array(original_obstacles.nonzero()).transpose().tolist()

        # dispatch obstacle setting complete
        EventDispatcher.instance().trigger_event(
            event_definitions.OBSTACLE_CHANGE_COMPLETE,
            row_col_coordinates_list,
            False
        )

    '''=======================================
    PATH FINDING
    ======================================='''
    def find_path(self):
        """If all relevant data has been set (model, start/end points, chaches), finds an optimal path"""

        # if no terrain model, start_point, end_point, or cache, early out
        if not self.terrain_model or not self.start_point or not self.end_point or not self.all_data_cached:
            return

        # reset any prior progress
        self.path_finder.reset_progress()

        # solve!
        source = self.terrain_model.getMeshElement(self.start_point).mesh_coordinate  # unscaled (row, column)
        target = self.terrain_model.getMeshElement(self.end_point).mesh_coordinate  # unscaled (row, column)

        # save path
        source_passable = len(self.terrain_model.isPassable(self.start_point)) > 0
        target_passable = len(self.terrain_model.isPassable(self.end_point)) > 0
        if source_passable and target_passable:
            self.found_path = self.path_finder.astar_solve(source, target)  # list of unscaled (row, column)
        else:
            self.found_path = []

        # calculate costs
        if len(self.found_path) > 0:
            col_row = np.array(self.found_path).transpose()[::-1]  # matrix where 0th row is x's, 1st is y's
            found_geo_polygon_path = GeoPolygon(self.terrain_model.COL_ROW, *col_row)
            traverse = TraversePath.frommap(found_geo_polygon_path, self.terrain_model)
            _, _, incremental_distances = self.agent.path_dl_slopes(traverse)
            self.path_distance = np.sum(incremental_distances)
            incremental_energy_usage, _ = self.agent.path_energy_expenditure(traverse)
            self.path_energy = np.sum(incremental_energy_usage)
        else:
            self.path_distance = 0
            self.path_energy = 0

        # dispatch path found event
        EventDispatcher.instance().trigger_event(
            event_definitions.PATH_FIND_COMPLETE,
            self.found_path,
            self.path_distance,
            self.path_energy
        )

    def find_path_from_position(self, coordinates, coordinate_system):

        # set new start
        self.set_start_point(coordinates, coordinate_system)

        # find path
        self.find_path()

    def set_path(self, path_to_set, coordinate_system):

        # if no terrain model, early out
        if not self.terrain_model:
            return

        # go through all coordinates in list, create row_col list
        row_col_coordinates_list = []
        for coordinates in path_to_set:
            geo_point = self.create_geo_point_from_coordinates(coordinates, coordinate_system)
            row_col = geo_point.to(self.terrain_model.ROW_COL)
            row_col_coordinates_list.append(row_col)

        # set endpoints
        if len(row_col_coordinates_list) > 0:
            self.set_start_point(row_col_coordinates_list[0], Cartesian.SYSTEM_NAME)
            self.set_end_point(row_col_coordinates_list[-1], Cartesian.SYSTEM_NAME)

        # save path
        self.found_path = row_col_coordinates_list

        # calculate costs
        col_row = np.array(self.found_path).transpose()[::-1]  # matrix where 0th row is x's, 1st is y's
        found_geo_polygon_path = GeoPolygon(self.terrain_model.COL_ROW, *col_row)
        traverse = TraversePath.frommap(found_geo_polygon_path, self.terrain_model)
        _, _, incremental_distances = self.agent.path_dl_slopes(traverse)
        self.path_distance = np.sum(incremental_distances)
        incremental_energy_usage, _ = self.agent.path_energy_expenditure(traverse)
        self.path_energy = np.sum(incremental_energy_usage)

        # dispatch path found event
        EventDispatcher.instance().trigger_event(
            event_definitions.PATH_FIND_COMPLETE,
            self.found_path,
            self.path_distance,
            self.path_energy
        )

    '''=======================================
    HELPERS
    ======================================='''
    def create_threaded_switch(self, func):
        """function that - based on value of self.threaded - returns another function that runs either
        on main thread (threaded=false) or on a separate thread (threaded=true)"""

        # start new thread if specified
        if self.threaded:

            def threaded_func(*args, **kwargs):
                thread_name = func.__name__
                thread = Thread(name=thread_name, target=func, args=args, kwargs=kwargs)
                self._threads[thread_name] = thread
                thread.start()
            return threaded_func

        # otherwise, just call the function
        else:

            def unthreaded_func(*args, **kwargs):
                func(*args, **kwargs)
            return unthreaded_func

    def create_geo_point_from_coordinates(self, coordinates, coordinate_system) -> GeoPoint:
        """Takes a set of coordinates and a coordinate system, returns geo_point
        in location specified (with respect to terrain_model for UTM and ROW_COL)"""

        if coordinate_system == LatLon.SYSTEM_NAME:
            geo_point = GeoPoint(LAT_LONG, coordinates[0], coordinates[1])
        elif coordinate_system == Cartesian.SYSTEM_NAME:
            geo_point = GeoPoint(self.terrain_model.ROW_COL, coordinates[0], coordinates[1])
        else:  # assume UTM (coordinate_system == UTM.SYSTEM_NAME)
            geo_point = GeoPoint(self.terrain_model.UTM_REF, coordinates[0], coordinates[1])

        return geo_point

