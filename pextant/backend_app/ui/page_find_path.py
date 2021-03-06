import numpy as np
import os
import pextant.backend_app.events.event_definitions as event_definitions
import pextant.backend_app.ui.fonts as fonts
import pextant.backend_app.utils as utils
import tkinter as tk
import tkinter.ttk as ttk
from matplotlib.axes import Axes
from matplotlib.backend_bases import MouseEvent, MouseButton, ResizeEvent
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.colors import LightSource
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.pyplot import Circle
from pextant.backend_app.dependency_injection import RequiredFeature, has_attributes
from pextant.backend_app.events.event_dispatcher import EventDispatcher
from pextant.lib.geoshapely import GeoPoint, Cartesian
from pextant.backend_app.path_manager import PathManager
from pextant.backend_app.ui.page_base import PageBase
from tkinter.filedialog import FileDialog

class BannerCell:
    COMMAND_PREFIX = ""
    COMMAND_POSTFIX = "_command"
    SETUP_PREFIX = "setup_"
    SETUP_POSTFIX = "_cell"
    REFRESH_PREFIX = "refresh_"
    REFRESH_POSTFIX = "_cell"
    PAD_X = 4
    PAD_Y = 4

    def __init__(self, parent_page, key):

        # map for holding named references to all cell widgets
        self.widgets = {}

        # store command func
        command_func_name = BannerCell.COMMAND_PREFIX + key + BannerCell.COMMAND_POSTFIX
        self._parent_command_func = \
            getattr(parent_page, command_func_name) if hasattr(parent_page, command_func_name) else None

        # store setup func
        setup_func_name = BannerCell.SETUP_PREFIX + key + BannerCell.SETUP_POSTFIX
        self._parent_page_setup_func = \
            getattr(parent_page, setup_func_name) if hasattr(parent_page, setup_func_name) else None

        # store refresh func
        refresh_func_name = BannerCell.REFRESH_PREFIX + key + BannerCell.REFRESH_POSTFIX
        self._parent_page_refresh_func = \
            getattr(parent_page, refresh_func_name) if hasattr(parent_page, refresh_func_name) else None

    def setup(self, frame, cell_data):

        cell_title = cell_data["title"]
        default_btn_text = cell_data["btn_text"] if "btn_text" in cell_data else cell_title

        # create frame
        cell_frame = ttk.Frame(frame, style='BannerCell.TFrame')
        cell_frame.pack(padx=BannerCell.PAD_X, pady=BannerCell.PAD_Y, side=tk.LEFT, fill=tk.Y)

        # cell title
        title_label = tk.Label(cell_frame, text=cell_title, font=fonts.CELL_TITLE, underline=1)
        title_label.pack(padx=BannerCell.PAD_X, pady=BannerCell.PAD_Y, side=tk.TOP)

        # if there is a default command function, add a default button
        if self._parent_command_func:
            self.widgets["default_btn"] = tk.Button(cell_frame, text=default_btn_text,
                                                    command=self._parent_command_func)
            self.widgets["default_btn"].pack(padx=BannerCell.PAD_X, pady=BannerCell.PAD_Y, side=tk.TOP)

        # do any custom setup
        if self._parent_page_setup_func:
            self._parent_page_setup_func(self, cell_frame, cell_data)

    def refresh(self):
        if self._parent_page_refresh_func:
            self._parent_page_refresh_func(self)


class PageFindPath(PageBase):
    """handles all functionality of find path page"""

    '''=======================================
    FIELDS
    ======================================='''
    MODELS_DIRECTORY = "models"

    # 'enum' for current state
    STATE_READY = 1
    STATE_LOADING_SCENARIO = 2
    STATE_LOADING_MODEL = 3
    STATE_SETTING_START = 4
    STATE_SETTING_END = 5
    STATE_SETTING_OBSTACLE = 6
    STATE_CACHING_COSTS = 7
    STATE_FINDING_PATH = 8

    # by-state text lookup ui objects
    NOTIFICATION_LBL_TEXT = {
        STATE_READY: "...",
        STATE_LOADING_SCENARIO: "Loading Scenario...",
        STATE_LOADING_MODEL: "Loading Model...",
        STATE_SETTING_START: "Setting Start...",
        STATE_SETTING_END: "Setting End...",
        STATE_SETTING_OBSTACLE: "Setting Obstacle(s)...",
        STATE_CACHING_COSTS: "Caching Costs...",
        STATE_FINDING_PATH: "Finding Path...",
    }

    # button data
    CELL_DATA = {
        'load_scenario': {
            'title': 'Scenarios',
            'btn_text': 'Load',
            'load_endpoints_text': 'Endpoints',
            'load_obstacles_text': 'Obstacles'
        },
        'load_model': {
            'title': 'Terrain Model',
            'btn_text': 'Load'
        },
        'cache_data': {
            'title': 'Cache Data',
            'costs_btn_text': 'Costs',
            'obstacles_btn_text': 'Obstacles',
            'heuristics_btn_text': 'Heuristics'
        },
        'set_endpoints': {
            'title': 'Endpoints',
            'start_btn_text': 'Set Start',
            'end_btn_text': 'Set End'
        },
        'set_obstacle': {
            'title': 'Obstacles',
            'clear_btn_title': 'Clear All'
        },
        'find_path': {
            'title': 'Find Path',
            'btn_text': 'Find'
        },
        'save_data': {
            'title': 'Save Data',
            'save_grid_btn_title': 'Obstacles (grid)',
            'save_list_btn_title': 'Obstacles (list)'
        },
    }

    # properties
    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, new_state):

        self._state = new_state

        # if ui has been initialized
        if self.ui_initialized:

            self.notification_lbl['text'] = PageFindPath.NOTIFICATION_LBL_TEXT.get(self._state, "Doing Something...")

            # refresh all cells based on new state
            for cell in self.banner_cells:
                cell.refresh()

    @property
    def blitting_active(self):
        return self.blitted_texture is not None

    @property
    def obstacle_radius(self):
        return self._obstacle_radius

    @obstacle_radius.setter
    def obstacle_radius(self, new_radius):

        self._obstacle_radius = new_radius

        # if ui has been initialized
        if self.ui_initialized:
            # update radius
            self.pending_obstacle_artist.radius = self._obstacle_radius

    '''=======================================
    STARTUP/SHUTDOWN
    ======================================='''

    def __init__(self, master):

        super().__init__(master, {
            event_definitions.SCENARIO_LOAD_COMPLETE: self.on_scenario_loaded,
            event_definitions.SCENARIO_LOAD_ENDPOINTS_COMPLETE: self.on_scenario_endpoints_loaded,
            event_definitions.SCENARIO_LOAD_OBSTACLE_COMPLETE: self.on_obstacles_changed,
            event_definitions.MODEL_LOAD_COMPLETE: self.on_model_loaded,
            event_definitions.MODEL_UNLOAD_COMPLETE: self.on_model_unloaded,
            event_definitions.START_POINT_SET_COMPLETE: self.on_start_point_set,
            event_definitions.END_POINT_SET_COMPLETE: self.on_end_point_set,
            event_definitions.OBSTACLE_CHANGE_COMPLETE: self.on_obstacles_changed,
            event_definitions.COSTS_CACHING_COMPLETE: self.on_costs_caching_complete,
            event_definitions.OBSTACLES_CACHING_COMPLETE: self.refresh_ui,
            event_definitions.HEURISTICS_CACHING_COMPLETE: self.refresh_ui,
            event_definitions.PATH_FIND_COMPLETE: self.on_path_found,
        })

        # dependency injected path_manager object
        self.path_manager = RequiredFeature(
            "path_manager",
            has_attributes(
                "terrain_model", "cost_function", "start_point", "end_point",
                "costs_cached", "obstacles_cached", "heuristics_cached", "heuristics_cached"
            )
        ).result

        # ui references
        self.ui_initialized = False
        self.notification_lbl = None
        self.banner_cells = []
        self.scenario_to_load = ''
        self.model_to_load = ''
        self.max_slope = 10
        self.obstacle_radius = 5
        self.loaded_scenario = ''

        # graph references
        self.blitted_texture = None
        self.non_cached_artists = []
        self.canvas = None
        self.figure = None
        self.sub_plot = None
        self.model_img = None
        self.obstacle_img = None
        self.added_obstacles_img = None
        self.start_point_line = None
        self.end_point_line = None
        self.pending_obstacle_artist = None
        self.found_path_line = None
        self.on_click_id = None
        self.on_move_id = None
        self.on_resize_id = None

        # do initial setup
        self.initial_setup()

        # set initial state
        self.state = PageFindPath.STATE_READY

    def initial_setup(self):

        # title
        label = tk.Label(self, text="PATH FINDING", font=fonts.LARGE_FONT, underline=1)
        label.pack(pady=4)

        # notification text
        self.notification_lbl = tk.Label(self, text="...", font=fonts.SUBTITLE_FONT)
        self.notification_lbl.pack(pady=2)

        # banner cells
        banner_frame = ttk.Frame(self, style='Banner.TFrame')
        banner_frame.pack(pady=4)
        for key, data in PageFindPath.CELL_DATA.items():
            cell = BannerCell(self, key)
            cell.setup(banner_frame, data)
            self.banner_cells.append(cell)

        # create the figure, setup axes
        self.figure = Figure(figsize=(3, 3), dpi=100)
        self.sub_plot: Axes = self.figure.add_subplot()

        # setup artists
        self.start_point_line = Line2D([], [], linestyle='None', marker='*', color='g', markeredgecolor='k',
                                       markersize=10)
        self.sub_plot.add_line(self.start_point_line)
        self.end_point_line = Line2D([], [], linestyle='None', marker='X', color='r', markeredgecolor='k',
                                     markersize=10)
        self.sub_plot.add_line(self.end_point_line)
        self.pending_obstacle_artist = Circle((0, 0), radius=self.obstacle_radius, color='r', alpha=0.0)
        self.sub_plot.add_artist(self.pending_obstacle_artist)
        self.found_path_line = Line2D([], [], color='b')
        self.sub_plot.add_line(self.found_path_line)

        # create rendering object
        self.canvas = FigureCanvasTkAgg(self.figure, self)
        self.redraw_canvas()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # add toolbar
        toolbar = NavigationToolbar2Tk(self.canvas, self)
        toolbar.update()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # listen for graph events
        self.on_click_id = self.figure.canvas.mpl_connect('button_press_event', self.on_click)
        self.on_move_id = self.figure.canvas.mpl_connect('motion_notify_event', self.on_cursor_move)
        self.on_resize_id = self.figure.canvas.mpl_connect('resize_event', self.on_canvas_resize)

        self.ui_initialized = True

    def page_closed(self):

        super().page_closed()

        # stop listening for graph events
        self.figure.canvas.mpl_disconnect(self.on_click_id)
        self.figure.canvas.mpl_disconnect(self.on_move_id)

    '''=======================================
    UI EVENT HANDLERS
    ======================================='''

    def on_click(self, event: MouseEvent):

        # IF:
        #   -a model is loaded AND
        #   -we left or right clicked somewhere in the graph area AND
        #   -click was a left or right click
        if self.path_manager.terrain_model and \
                event.xdata and event.ydata and \
                (event.button == MouseButton.LEFT or event.button == MouseButton.RIGHT):

            # we want whole numbers
            clicked_row = round(event.ydata)
            clicked_column = round(event.xdata)

            # if setting start or end
            if (self.state == PageFindPath.STATE_SETTING_START or self.state == PageFindPath.STATE_SETTING_END) and \
                    event.button == MouseButton.LEFT:

                # if setting  start...
                if self.state == PageFindPath.STATE_SETTING_START:

                    # issue start point set request
                    EventDispatcher.instance().trigger_event(
                        event_definitions.START_POINT_SET_REQUESTED,
                        (clicked_row, clicked_column),
                        Cartesian.SYSTEM_NAME
                    )

                # otherwise, if setting end...
                elif self.state == PageFindPath.STATE_SETTING_END:

                    # issue end point set request
                    EventDispatcher.instance().trigger_event(
                        event_definitions.END_POINT_SET_REQUESTED,
                        (clicked_row, clicked_column),
                        Cartesian.SYSTEM_NAME
                    )

            # if setting obstacle
            if self.state == PageFindPath.STATE_SETTING_OBSTACLE:
                # issue obstacle set request
                EventDispatcher.instance().trigger_event(
                    event_definitions.RADIAL_OBSTACLE_SET_REQUESTED,
                    (clicked_row, clicked_column),
                    Cartesian.SYSTEM_NAME,
                    self.obstacle_radius,
                    event.button == MouseButton.LEFT
                )

    def on_cursor_move(self, event: MouseEvent):

        # if setting new obstacles
        if self.state == PageFindPath.STATE_SETTING_OBSTACLE:
            # draw the obstacle marker
            self.pending_obstacle_artist.center = (event.xdata, event.ydata)
            self.redraw_canvas()

    def on_canvas_resize(self, event: ResizeEvent):

        # if we're blitting
        if self.blitting_active:
            # re-cache the blitted bits
            self.re_cache_blitted_texture()

    '''=======================================
    APP EVENT HANDLERS
    ======================================='''

    def on_scenario_loaded(self, scenario_name, terrain_model, start_point, end_point, initial_heading):

        # set loaded scenario
        self.loaded_scenario = scenario_name

        self.on_model_loaded(terrain_model)
        self.on_start_point_set(start_point)
        self.on_end_point_set(end_point)

    def on_scenario_endpoints_loaded(self, start_point, end_point, initial_heading):

        self.on_start_point_set(start_point)
        self.on_end_point_set(end_point)

    def on_model_loaded(self, terrain_model):

        # create the terrain image
        weight = 1.0
        res = terrain_model.resolution
        exaggeration = res * weight
        ls = LightSource(azdeg=315, altdeg=45)
        img = ls.hillshade(terrain_model.dataset_unmasked, vert_exag=exaggeration, dx=res, dy=res)
        self.model_img = self.sub_plot.imshow(img, cmap='gray')

        # create obstacle image
        self.obstacle_img = self.sub_plot.imshow(terrain_model.obstacle_mask(), alpha=0.5, cmap='bwr_r')

        # redraw and note that we're done loading
        self.redraw_canvas()
        self.state = PageFindPath.STATE_READY

    def on_model_unloaded(self):

        # clear loaded scenario
        self.loaded_scenario = ''

        # clear terrain/images
        if self.model_img:
            self.model_img.remove()
            self.model_img = None
        if self.obstacle_img:
            self.obstacle_img.remove()
            self.obstacle_img = None

        # clear artists
        self.start_point_line.set_data([], [])
        self.end_point_line.set_data([], [])
        self.pending_obstacle_artist.set_alpha(0.0)
        self.found_path_line.set_data([], [])

        # refresh UI and redraw
        self.refresh_ui()
        self.redraw_canvas()

    def on_start_point_set(self, start_point: GeoPoint):
        self.on_any_point_set(start_point, self.start_point_line)

    def on_end_point_set(self, end_point: GeoPoint):
        self.on_any_point_set(end_point, self.end_point_line)

    def on_any_point_set(self, set_point: GeoPoint, set_point_line: Line2D):

        # set line (i.e. draw point)
        row, column = set_point.to(self.path_manager.terrain_model.ROW_COL)
        set_point_line.set_data([column], [row])

        # clear path (we've moved an endpoint => old path no longer valid)
        self.found_path_line.set_data([], [])

        # redraw (for updated points and paths)
        self.redraw_canvas()

        # head back to ready state
        self.state = PageFindPath.STATE_READY

    def on_obstacles_changed(self, *args, **kwargs):

        # update obstacle image
        obstacle_mask = self.path_manager.terrain_model.obstacle_mask()
        self.obstacle_img.set_data(obstacle_mask)

        # re-cached blitted texture (to include the new obstacle)
        if self.blitting_active:
            self.re_cache_blitted_texture()

        # if in ready state, force a refresh
        if self.state == PageFindPath.STATE_READY:
            self.refresh_ui()

        # redraw
        self.redraw_canvas()

    def on_costs_caching_complete(self):

        # ready for the next thing
        self.state = PageFindPath.STATE_READY

    def on_path_found(self, path, distance_cost, energy_cost):

        # update line data
        xs = [node[1] for node in path]
        ys = [node[0] for node in path]
        self.found_path_line.set_data(xs, ys)

        # redraw and note that we're done path-finding
        self.state = PageFindPath.STATE_READY
        self.redraw_canvas()

    '''=======================================
    CELL FUNCTIONS
    ======================================='''

    # load scenario
    def setup_load_scenario_cell(self, cell: BannerCell, cell_frame, cell_data):

        # load endpoints button
        cell.widgets["load_endpoint_btn"] = \
            tk.Button(cell_frame, text=cell_data['load_endpoints_text'], command=self.load_scenario_endpoints_command)
        cell.widgets["load_endpoint_btn"].pack(padx=BannerCell.PAD_X, pady=BannerCell.PAD_Y, side=tk.TOP)

        # load endpoints button
        cell.widgets["load_obstacles_btn"] = \
            tk.Button(cell_frame, text=cell_data['load_obstacles_text'], command=self.load_scenario_obstacles_command)
        cell.widgets["load_obstacles_btn"].pack(padx=BannerCell.PAD_X, pady=BannerCell.PAD_Y, side=tk.TOP)

        # get list of available scenarios
        scenario_files = PathManager.get_available_scenarios()

        # scenario dropdown
        def update_values():
            scenario_dropdown['values'] = PathManager.get_available_scenarios()
        def on_scenario_selected(e):
            self.scenario_to_load = str(scenario_dropdown.get())
        scenario_dropdown = ttk.Combobox(
            cell_frame,
            width=12,
            state="readonly",
            values=scenario_files,
            postcommand=update_values
        )
        scenario_dropdown.bind("<<ComboboxSelected>>", on_scenario_selected)
        if len(scenario_files) > 0:
            scenario_dropdown.current(0)
        on_scenario_selected(None)  # simulate a select of 'current'
        scenario_dropdown.pack(padx=4, pady=4, side=tk.TOP)

    def load_scenario_command(self):

        # if we're not doing anything else
        if self.state == PageFindPath.STATE_READY:

            # simulate an unload before a new load
            self.on_model_unloaded()

            # note that we're loading
            self.state = PageFindPath.STATE_LOADING_SCENARIO

            # issue load model request
            EventDispatcher.instance().trigger_event(
                event_definitions.SCENARIO_LOAD_REQUESTED,
                self.scenario_to_load
            )

    def load_scenario_endpoints_command(self):

        # only load endpoints for an already-loaded scenario
        if self.loaded_scenario == self.scenario_to_load:

            # if we're not doing anything else
            if self.state == PageFindPath.STATE_READY:

                # issue load endpoints request
                EventDispatcher.instance().trigger_event(
                    event_definitions.SCENARIO_LOAD_ENDPOINTS_REQUESTED,
                    self.scenario_to_load
                )

    def load_scenario_obstacles_command(self):

        # only load endpoints for an already-loaded scenario
        if self.loaded_scenario == self.scenario_to_load:

            # if we're not doing anything else
            if self.state == PageFindPath.STATE_READY:

                # issue load model request
                EventDispatcher.instance().trigger_event(
                    event_definitions.SCENARIO_LOAD_OBSTACLE_REQUEST,
                    self.scenario_to_load
                )

    def refresh_load_scenario_cell(self, cell: BannerCell):

        btn = cell.widgets["default_btn"]
        load_endpoint_btn = cell.widgets["load_endpoint_btn"]
        load_obstacles_btn = cell.widgets["load_obstacles_btn"]

        # standard configuration
        btn['state'] = tk.DISABLED
        load_endpoint_btn['state'] = tk.DISABLED
        load_obstacles_btn['state'] = tk.DISABLED

        # READY
        if self.state == PageFindPath.STATE_READY:
            # enable / disable buttons based on existence of parameters
            btn['state'] = tk.NORMAL
            load_endpoint_btn['state'] = tk.DISABLED if self.path_manager.terrain_model is None else tk.NORMAL
            load_obstacles_btn['state'] = tk.DISABLED if self.path_manager.terrain_model is None else tk.NORMAL

    # load model
    def setup_load_model_cell(self, cell: BannerCell, cell_frame, cell_data):

        # get list of available models
        model_files = PathManager.get_available_models()

        # add model dropdown
        def update_values():
            model_dropdown['values'] = PathManager.get_available_models()
        def model_dropdown_callback(e):
            self.model_to_load = str(model_dropdown.get())
        model_dropdown = ttk.Combobox(
            cell_frame,
            width=12,
            state="readonly",
            values=model_files,
            postcommand=update_values
        )
        model_dropdown.bind("<<ComboboxSelected>>", model_dropdown_callback)
        if len(model_files) > 0:
            model_dropdown.current(0)
        model_dropdown_callback(None)  # simulate a select of 'current'
        model_dropdown.pack(padx=4, pady=4, side=tk.TOP)

        # add slope slider
        def slider_command(value):
            self.max_slope = int(value)

        slope_slider = tk.Scale(
            cell_frame,
            from_=0,
            to=90,
            resolution=5,
            orient=tk.HORIZONTAL,
            command=slider_command,
            length=0
        )
        slope_slider.set(self.max_slope)
        slope_slider.pack(padx=4, pady=0, side=tk.TOP, fill=tk.X)

    def load_model_command(self):

        # if we're not doing anything else
        if self.state == PageFindPath.STATE_READY:

            # simulate an unload before a new load
            self.on_model_unloaded()

            # note that we're loading
            self.state = PageFindPath.STATE_LOADING_MODEL

            # issue load model request
            EventDispatcher.instance().trigger_event(
                event_definitions.MODEL_LOAD_REQUESTED,
                self.model_to_load,
                self.max_slope
            )

    def refresh_load_model_cell(self, cell: BannerCell):

        btn = cell.widgets["default_btn"]

        # standard configuration
        btn['state'] = tk.DISABLED
        btn['text'] = "Load"

        # READY
        if self.state == PageFindPath.STATE_READY:
            # enable / disable buttons based on existence of parameters
            btn['state'] = tk.NORMAL

    # cache data
    def setup_cache_data_cell(self, cell: BannerCell, cell_frame, cell_data):

        costs_btn_text = cell_data['costs_btn_text']
        obstacles_btn_text = cell_data['obstacles_btn_text']
        heuristics_btn_text = cell_data['heuristics_btn_text']

        # costs button
        cell.widgets["costs_btn"] = \
            tk.Button(cell_frame, text=costs_btn_text, command=self.cache_costs_command)
        cell.widgets["costs_btn"].pack(padx=BannerCell.PAD_X, pady=BannerCell.PAD_Y, side=tk.TOP)

        # obstacles button
        cell.widgets["obstacles_btn"] = \
            tk.Button(cell_frame, text=obstacles_btn_text, command=self.cache_obstacles_command)
        cell.widgets["obstacles_btn"].pack(padx=BannerCell.PAD_X, pady=BannerCell.PAD_Y, side=tk.TOP)

        # heuristics button
        cell.widgets["heuristics_btn"] = \
            tk.Button(cell_frame, text=heuristics_btn_text, command=self.cache_heuristics_command)
        cell.widgets["heuristics_btn"].pack(padx=BannerCell.PAD_X, pady=BannerCell.PAD_Y, side=tk.TOP)

    def cache_costs_command(self):

        # if we're not doing anything else
        if self.state == PageFindPath.STATE_READY:
            # note that we've started caching
            self.state = PageFindPath.STATE_CACHING_COSTS

            # issue cost caching request
            EventDispatcher.instance().trigger_event(event_definitions.COSTS_CACHING_REQUESTED)

    def cache_obstacles_command(self):

        # if we're not doing anything else
        if self.state == PageFindPath.STATE_READY:
            # issue obstacles caching request
            EventDispatcher.instance().trigger_event(event_definitions.OBSTACLES_CACHING_REQUESTED)

    def cache_heuristics_command(self):

        # if we're not doing anything else
        if self.state == PageFindPath.STATE_READY:
            # issue heuristic caching request
            EventDispatcher.instance().trigger_event(event_definitions.HEURISTICS_CACHING_REQUESTED)

    def refresh_cache_data_cell(self, cell: BannerCell):

        costs_btn = cell.widgets["costs_btn"]
        obstacles_btn = cell.widgets["obstacles_btn"]
        heuristics_btn = cell.widgets["heuristics_btn"]

        # standard configuration
        costs_btn['state'] = tk.DISABLED
        obstacles_btn['state'] = tk.DISABLED
        heuristics_btn['state'] = tk.DISABLED

        # READY
        if self.state == PageFindPath.STATE_READY:

            # costs
            if not self.path_manager.costs_cached and self.path_manager.cost_function:
                costs_btn['state'] = tk.NORMAL
            else:
                costs_btn['state'] = tk.DISABLED

            # obstacles
            if not self.path_manager.obstacles_cached and self.path_manager.terrain_model:
                obstacles_btn['state'] = tk.NORMAL
            else:
                obstacles_btn['state'] = tk.DISABLED

            # heuristics
            if not self.path_manager.heuristics_cached and self.path_manager.end_point:
                heuristics_btn['state'] = tk.NORMAL
            else:
                heuristics_btn['state'] = tk.DISABLED

    # endpoints
    def setup_set_endpoints_cell(self, cell: BannerCell, cell_frame, cell_data):

        start_btn_text = cell_data['start_btn_text']
        end_btn_text = cell_data['end_btn_text']

        # start button
        cell.widgets["start_btn"] = tk.Button(cell_frame, text=start_btn_text, command=self.set_start_command)
        cell.widgets["start_btn"].pack(padx=BannerCell.PAD_X, pady=BannerCell.PAD_Y, side=tk.TOP)

        # start coords label
        cell.widgets["start_label"] = tk.Label(cell_frame, text="[-,-]")
        cell.widgets["start_label"].pack(padx=BannerCell.PAD_X, pady=0, side=tk.TOP)

        # end button
        cell.widgets["end_btn"] = tk.Button(cell_frame, text=end_btn_text, command=self.set_end_command)
        cell.widgets["end_btn"].pack(padx=BannerCell.PAD_X, pady=BannerCell.PAD_Y, side=tk.TOP)

        # end coords label
        cell.widgets["end_label"] = tk.Label(cell_frame, text="[-,-]")
        cell.widgets["end_label"].pack(padx=BannerCell.PAD_X, pady=0, side=tk.TOP)

    def set_start_command(self):

        # if we're not doing anything else
        if self.state == PageFindPath.STATE_READY:

            # note that we're setting start
            self.state = PageFindPath.STATE_SETTING_START

        # otherwise, if currently setting start
        elif self.STATE_SETTING_START:

            # cancel (i.e. do nothing and return to ready)
            self.state = PageFindPath.STATE_READY

    def set_end_command(self):

        # if we're not doing anything else
        if self.state == PageFindPath.STATE_READY:

            # note that we're setting END
            self.state = PageFindPath.STATE_SETTING_END

        # otherwise, if currently setting end
        elif self.STATE_SETTING_END:

            # cancel (i.e. do nothing and return to ready)
            self.state = PageFindPath.STATE_READY

    def refresh_set_endpoints_cell(self, cell: BannerCell):

        start_btn = cell.widgets["start_btn"]
        start_label = cell.widgets["start_label"]
        end_btn = cell.widgets["end_btn"]
        end_label = cell.widgets["end_label"]

        # standard configuration
        start_btn['state'] = tk.DISABLED
        start_btn['text'] = "Set Start"
        end_btn['state'] = tk.DISABLED
        end_btn['text'] = "Set End"

        # SETTING START
        if self.state == PageFindPath.STATE_SETTING_START:

            # cancel set start enabled
            start_btn['state'] = tk.NORMAL
            start_btn['text'] = "Cancel"

        # SETTING END
        elif self.state == PageFindPath.STATE_SETTING_END:

            # cancel set end enabled
            end_btn['state'] = tk.NORMAL
            end_btn['text'] = "Cancel"

        # READY
        elif self.state == PageFindPath.STATE_READY:

            # enable / disable buttons based on existence of parameters
            start_btn['state'] = tk.NORMAL if self.path_manager.terrain_model else tk.DISABLED
            end_btn['state'] = tk.NORMAL if self.path_manager.terrain_model else tk.DISABLED

        # start label
        if self.path_manager.start_point:
            row, column = self.path_manager.start_point.to(self.path_manager.terrain_model.ROW_COL)
            start_label['text'] = f"[{row},{column}]"
        else:
            start_label['text'] = "[-,-]"

        # end label
        if self.path_manager.end_point:
            row, column = self.path_manager.end_point.to(self.path_manager.terrain_model.ROW_COL)
            end_label['text'] = f"[{row},{column}]"
        else:
            end_label['text'] = "[-,-]"

    # obstacles
    def setup_set_obstacle_cell(self, cell: BannerCell, cell_frame, cell_data):

        # add radius slider
        def slider_command(value):
            self.obstacle_radius = float(value)
        radius_slider = tk.Scale(
            cell_frame,
            from_=0.5,
            to=10,
            resolution=0.5,
            orient=tk.HORIZONTAL,
            command=slider_command,
            length=0
        )
        cell.widgets["radius_slider"] = radius_slider
        radius_slider.set(self.obstacle_radius)
        radius_slider.pack(padx=4, pady=0, side=tk.TOP, fill=tk.X)

        # add save (grid) obstacles button
        clear_btn = tk.Button(
            cell_frame,
            text=cell_data['clear_btn_title'],
            command=self.clear_all_obstacles_command
        )
        cell.widgets["clear_btn"] = clear_btn
        clear_btn.pack(padx=4, pady=4, side=tk.TOP)

    def set_obstacle_command(self):

        # if we're not doing anything else
        if self.state == PageFindPath.STATE_READY:

            # note that we're setting an obstacle
            self.state = PageFindPath.STATE_SETTING_OBSTACLE

            # begin blitting
            self.begin_blitting([self.pending_obstacle_artist])

            # show the pending obstacle
            self.pending_obstacle_artist.set_alpha(1.0)

        # otherwise, if currently setting obstacle
        elif self.STATE_SETTING_OBSTACLE:

            # end blitting
            self.end_blitting()

            # cancel (i.e. do nothing and return to ready)
            self.state = PageFindPath.STATE_READY

            # hide pending obstacle and redraw
            self.pending_obstacle_artist.set_alpha(0.0)
            self.redraw_canvas()

    def clear_all_obstacles_command(self):

        self.path_manager.clear_all_obstacles()
        self.refresh_ui()

    def refresh_set_obstacle_cell(self, cell: BannerCell):

        btn = cell.widgets["default_btn"]
        clear_btn = cell.widgets["clear_btn"]

        # standard configuration
        btn['state'] = tk.DISABLED
        btn['text'] = "Set Obstacle"
        clear_btn['state'] = tk.DISABLED

        if self.state == PageFindPath.STATE_SETTING_OBSTACLE:
            btn['state'] = tk.NORMAL
            btn['text'] = "Done Setting"

        # READY
        if self.state == PageFindPath.STATE_READY:
            # enable / disable buttons based on existence of parameters
            btn['state'] = tk.DISABLED if not self.path_manager.terrain_model else tk.NORMAL
            clear_btn['state'] = tk.DISABLED if not self.path_manager.terrain_model else tk.NORMAL

    # find path
    def setup_find_path_cell(self, cell: BannerCell, cell_frame, cell_data):

        # distance text
        cell.widgets["distance_label"] = tk.Label(cell_frame, text="Distance: -")
        cell.widgets["distance_label"].pack(padx=BannerCell.PAD_X, pady=BannerCell.PAD_Y, side=tk.TOP)

        # metabolic cost text
        cell.widgets["metabolic_label"] = tk.Label(cell_frame, text="Energy: -")
        cell.widgets["metabolic_label"].pack(padx=BannerCell.PAD_X, pady=BannerCell.PAD_Y, side=tk.TOP)

    def find_path_command(self):

        # if we're not doing anything else
        if self.state == PageFindPath.STATE_READY:

            # note that we've started the path-finding
            self.state = PageFindPath.STATE_FINDING_PATH

            # issue request for path find
            EventDispatcher.instance().trigger_event(event_definitions.PATH_FIND_REQUESTED)

    def refresh_find_path_cell(self, cell: BannerCell):

        btn = cell.widgets["default_btn"]
        distance_label = cell.widgets["distance_label"]
        metabolic_label = cell.widgets["metabolic_label"]

        # standard configuration
        btn['state'] = tk.DISABLED

        # READY
        if self.state == PageFindPath.STATE_READY:

            # enable / disable buttons based on existence of parameters
            if self.path_manager.all_data_cached and self.path_manager.terrain_model and \
                    self.path_manager.start_point and self.path_manager.end_point:
                btn['state'] = tk.NORMAL
            else:
                btn['state'] = tk.DISABLED

        # if a path is found
        if self.path_manager.found_path:
            distance_label['text'] = "Distance: {:.1f}m".format(self.path_manager.path_distance)
            metabolic_label['text'] = "Energy: {:.1f}kJ".format(self.path_manager.path_energy / 1000)
        else:
            distance_label['text'] = "Distance: -"
            metabolic_label['text'] = "Energy: -"

    # save
    def setup_save_data_cell(self, cell: BannerCell, cell_frame, cell_data):

        # add save (grid) obstacles button
        save_grid_btn = tk.Button(
            cell_frame,
            text=cell_data['save_grid_btn_title'],
            command=self.save_obstacles_as_grid_command
        )
        cell.widgets["save_grid_btn"] = save_grid_btn
        save_grid_btn.pack(padx=4, pady=4, side=tk.TOP)

        # add save (list) obstacles button
        save_list_btn = tk.Button(
            cell_frame,
            text=cell_data['save_list_btn_title'],
            command=self.save_obstacles_as_list_command
        )
        cell.widgets["save_list_btn"] = save_list_btn
        save_list_btn.pack(padx=4, pady=4, side=tk.TOP)

    def save_obstacles_as_grid_command(self):

        # open dialog for saving file
        cwd = os.getcwd()
        obstacles_dir = os.path.join(cwd, PathManager.OBSTACLES_DIRECTORY)
        in_file = tk.filedialog.asksaveasfile(
                mode="wb",
                title='Save Obstacles (boolean grid)',
                initialdir=obstacles_dir,
                filetypes=[('JSON', '*.json')],
                defaultextension='json'
        )
        if in_file is not None:

            # get python 'matrix' (list of lists) of current obstacles
            current_obstacles = self.path_manager.terrain_model.obstacles.tolist()

            # encode as json
            json_object = {
                'obstacles': current_obstacles
            }
            json_bytes = utils.json_encode(json_object)

            # write the json to the file
            in_file.write(json_bytes)

            # close file
            in_file.close()

    def save_obstacles_as_list_command(self):

        # open dialog for saving file
        cwd = os.getcwd()
        obstacles_dir = os.path.join(cwd, PathManager.OBSTACLES_DIRECTORY)
        in_file = tk.filedialog.asksaveasfile(
                mode="wb",
                title='Save Obstacles (coordinates list)',
                initialdir=obstacles_dir,
                filetypes=[('JSON', '*.json')],
                defaultextension='json'
        )
        if in_file is not None:

            # get 2D list of current obstacles
            current_obstacles = self.path_manager.terrain_model.obstacles
            obstacle_coordinates_list = np.array(current_obstacles.nonzero()).transpose().tolist()

            # encode as json
            json_object = {
                'obstacles': obstacle_coordinates_list
            }
            json_bytes = utils.json_encode(json_object)

            # write the json to the file
            in_file.write(json_bytes)

            # close file
            in_file.close()

    def refresh_save_data_cell(self, cell: BannerCell):

        save_grid_btn = cell.widgets["save_grid_btn"]
        save_list_btn = cell.widgets["save_list_btn"]

        # standard configuration
        save_grid_btn['state'] = tk.DISABLED
        save_list_btn['state'] = tk.DISABLED

        # READY
        if self.state == PageFindPath.STATE_READY:
            # enable / disable buttons based on existence of parameters
            save_grid_btn['state'] = tk.DISABLED if not self.path_manager.terrain_model else tk.NORMAL
            save_list_btn['state'] = tk.DISABLED if not self.path_manager.terrain_model else tk.NORMAL

    '''=======================================
    DRAWING
    ======================================='''

    def begin_blitting(self, artists_to_full_redraw):
        self.blitted_texture = self.canvas.copy_from_bbox(self.sub_plot.bbox)
        self.non_cached_artists = artists_to_full_redraw

    def redraw_canvas(self, force_full_redraw=False):

        # if blitting (should be faster redraw) and *not* forcing a redraw
        if self.blitting_active and not force_full_redraw:

            # restore background
            self.canvas.restore_region(self.blitted_texture)

            # redraw specified artists
            for artist in self.non_cached_artists:
                self.sub_plot.draw_artist(artist)

            # fill in the axes rectangle
            self.canvas.blit(self.sub_plot.bbox)

        # otherwise...
        else:

            # just redraw everything
            self.canvas.draw()

    def end_blitting(self):
        self.blitted_texture = None
        self.non_cached_artists = []

    def re_cache_blitted_texture(self):

        artist_alphas = {}

        # store alphas of non_cached artists, set to 0 alpha
        for artist in self.non_cached_artists:
            artist_alphas[artist] = artist.get_alpha()
            artist.set_alpha(0.0)

        # re-cache (need to force a redraw to get canvas state where all re-drawn artists are alpha'd out)
        self.redraw_canvas(force_full_redraw=True)
        self.blitted_texture = self.canvas.copy_from_bbox(self.sub_plot.bbox)

        # restore artist alphas
        for artist, alpha in artist_alphas.items():
            artist.set_alpha(alpha)

    '''=======================================
    HELPERS
    ======================================='''

    def refresh_ui(self):
        # state property will go through UI elements and refresh them
        self.state = self.state
