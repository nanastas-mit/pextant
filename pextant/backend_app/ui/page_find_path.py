import os
import pextant.backend_app.events.event_definitions as event_definitions
import pextant.backend_app.ui.fonts as fonts
import PIL
import tkinter as tk
import tkinter.ttk as ttk
from matplotlib.axes import Axes
from matplotlib.backend_bases import MouseEvent, MouseButton, ResizeEvent
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.colors import LightSource
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.pyplot import Circle
from os import path as path
from pextant.backend_app.events.event_dispatcher import EventDispatcher
from pextant.backend_app.ui.page_base import PageBase
from pextant.EnvironmentalModel import load_legacy, GDALMesh
from pextant.explorers import Astronaut
from pextant.lib.geoshapely import GeoPoint
from pextant.solvers.astarMesh import ExplorerCost, MeshSearchElement
from pextant_cpp import PathFinder
from threading import Thread


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
            self.widgets["default_btn"] = tk.Button(cell_frame, text=default_btn_text, command=self._parent_command_func)
            self.widgets["default_btn"].pack(padx=BannerCell.PAD_X, pady=BannerCell.PAD_Y, side=tk.TOP)

        # do any custom setup
        if self._parent_page_setup_func:
            self._parent_page_setup_func(self, cell_frame, cell_data)

    def refresh(self):
        self._parent_page_refresh_func(self)


class PageFindPath(PageBase):
    """handles all functionality of find path page"""

    '''=======================================
    FIELDS
    ======================================='''
    MODELS_DIRECTORY = "models"

    # 'enum' for current state
    STATE_READY = 1
    STATE_LOADING_MODEL = 2
    STATE_SETTING_START = 3
    STATE_SETTING_END = 4
    STATE_SETTING_OBSTACLE = 5
    STATE_CACHING_DATA = 6
    STATE_FINDING_PATH = 7

    # by-state text lookup ui objects
    NOTIFICATION_LBL_TEXT = {
        STATE_READY: "...",
        STATE_LOADING_MODEL: "Loading Model...",
        STATE_SETTING_START: "Setting Start...",
        STATE_SETTING_END: "Setting End...",
        STATE_SETTING_OBSTACLE: "Setting Obstacle(s)...",
        STATE_CACHING_DATA: "Caching Data...",
        STATE_FINDING_PATH: "Finding Path...",
    }

    # button data
    CELL_DATA = {
        'load_model':
            {'title': 'Load Model'},
        'cache_data':
            {'title': 'Cache Data',
             'costs_btn_text': 'Costs',
             'obstacles_btn_text': 'Obstacles',
             'heuristics_btn_text': 'Heuristics'},
        'set_endpoints':
            {'title': 'Set Endpoints',
             'start_btn_text': 'Set Start',
             'end_btn_text': 'Set End'},
        'set_obstacle':
            {'title': 'Set Obstacle'},
        'find_path':
            {'title': 'Find Path',
             'btn_text': 'Find'},
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

            self.notification_lbl['text'] = PageFindPath.NOTIFICATION_LBL_TEXT[self._state]

            # refresh all buttons based on new state
            for btn in self.banner_cells:
                btn.refresh()

    @property
    def data_cached(self):
        return self.path_finder.all_cached

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

    @property
    def max_slope(self):
        return self._max_slope
    @max_slope.setter
    def max_slope(self, new_max_slope):

        self._max_slope = new_max_slope

        # if ui has been initialized
        if self.ui_initialized:

            # update radius
            self.pending_obstacle_artist.radius = self._obstacle_radius

    '''=======================================
    STARTUP/SHUTDOWN
    ======================================='''
    def __init__(self, master):

        super().__init__(master, {
            event_definitions.TERRAIN_MODEL_LOADED: self.on_terrain_model_loaded,
            event_definitions.COSTS_CACHING_COMPLETE: self.on_caching_complete,
            event_definitions.PATH_FOUND: self.on_path_found,
        })

        # ui references
        self.ui_initialized = False
        self.notification_lbl = None
        self.banner_cells = []
        self.obstacle_radius = 20
        self.max_slope = 10
        self.model_to_load = ""

        # graph references
        self.blitted_texture = None
        self.non_cached_artists = []
        self.canvas = None
        self.figure = None
        self.sub_plot = None
        self.model_img = None
        self.obstacle_img = None
        self.start_point_line = None
        self.end_point_line = None
        self.pending_obstacle_artist = None
        self.found_path_line = None
        self.on_click_id = None
        self.on_move_id = None
        self.on_resize_id = None

        # path planning references
        self.cost_function = None
        self.path_finder = PathFinder()
        self.agent = Astronaut(80)
        self.terrain_model = None
        self.start_point = None
        self.end_point = None

        # threading references
        self.load_model_thread = None
        self.cache_costs_thread = None
        self.find_path_thread = None

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

        # wait for existing threads to complete
        if self.load_model_thread:
            self.load_model_thread.join()
        if self.cache_costs_thread:
            self.cache_costs_thread.join()
        if self.find_path_thread:
            self.find_path_thread.join()

    '''=======================================
    EVENT HANDLERS
    ======================================='''
    def on_click(self, event: MouseEvent):

        # IF:
        #   -a model is loaded AND
        #   -we left or right clicked somewhere in the graph area AND
        #   -click was a left or right click
        if \
            self.terrain_model and \
            event.xdata and event.ydata and \
            (event.button == MouseButton.LEFT or event.button == MouseButton.RIGHT):

            clicked_point = GeoPoint(self.terrain_model.COL_ROW, event.xdata, event.ydata)

            # if setting obstacle
            if self.state == PageFindPath.STATE_SETTING_OBSTACLE:

                # set the obstacle
                elt = self.terrain_model.getMeshElement(clicked_point)
                self.terrain_model.set_circular_obstacle(
                    (elt.x, elt.y),
                    self.obstacle_radius * self.terrain_model.resolution,
                    event.button == MouseButton.LEFT
                )
                self.obstacle_img.set_data(self.terrain_model.obstacle_mask())

                # clear cached obstacles
                self.path_finder.clear_obstacles()

                # clear path (we've changed the cost)
                self.found_path_line.set_data([], [])

                # re-cached blitted texture (to include the new obstacle)
                self.re_cache_blitted_texture()

            # if setting start or end
            if (self.state == PageFindPath.STATE_SETTING_START or self.state == PageFindPath.STATE_SETTING_END) and \
                    event.button == MouseButton.LEFT:

                # if setting  start...
                if self.state == PageFindPath.STATE_SETTING_START:

                    # set point
                    self.start_point = clicked_point
                    col_row_point = clicked_point.to(self.terrain_model.COL_ROW)

                    # set line (i.e. draw point)
                    self.start_point_line.set_data([col_row_point[0]], [col_row_point[1]])

                # otherwise, if setting end...
                elif self.state == PageFindPath.STATE_SETTING_END:

                    # set point
                    self.end_point = clicked_point
                    col_row_point = clicked_point.to(self.terrain_model.COL_ROW)

                    # set line (i.e. draw point)
                    self.end_point_line.set_data([col_row_point[0]], [col_row_point[1]])

                    # clear cached heuristics
                    self.path_finder.clear_heuristics()

                # clear path (we've moved an endpoint => old path no longer valid)
                self.found_path_line.set_data([], [])

                # redraw (for updated points and paths)
                self.redraw_canvas()

                # head back to ready state
                self.state = PageFindPath.STATE_READY

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

    def on_terrain_model_loaded(self):

        # should be coming from loading the model
        assert self.state == PageFindPath.STATE_LOADING_MODEL

        # redraw and note that we're done loading
        self.redraw_canvas()
        self.load_model_thread = None
        self.state = PageFindPath.STATE_READY

    def on_caching_complete(self):

        # should be coming from caching
        assert self.state == PageFindPath.STATE_CACHING_DATA

        # ready for the next thing
        self.cache_costs_thread = None
        self.state = PageFindPath.STATE_READY

    def on_path_found(self):

        # should be coming from finding path
        assert self.state == PageFindPath.STATE_FINDING_PATH

        # redraw and note that we're done path-finding
        self.find_path_thread = None
        self.state = PageFindPath.STATE_READY
        self.redraw_canvas()

    '''=======================================
    CELL FUNCTIONS
    ======================================='''
    # load model
    def setup_load_model_cell(self, cell: BannerCell, cell_frame, cell_data):

        # get list of files in models folder
        cwd = os.getcwd()
        models_dir = path.join(cwd, PageFindPath.MODELS_DIRECTORY)
        model_files = [f for f in os.listdir(models_dir) if path.isfile(path.join(models_dir, f))]

        # add model dropdown
        model_dropdown = ttk.Combobox(
            cell_frame,
            width=12,
            state="readonly",
            values=model_files
        )
        def model_dropdown_callback(e):
            self.model_to_load = str(model_dropdown.get())
        model_dropdown.bind("<<ComboboxSelected>>", model_dropdown_callback)
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
            orient=tk.HORIZONTAL,
            command=slider_command
        )
        cell.widgets["slope_slider"] = slope_slider
        slope_slider.set(self.max_slope)
        slope_slider.pack(padx=4, pady=4, side=tk.TOP)

    def load_model_command(self):

        # if we're not doing anything else
        if self.state == PageFindPath.STATE_READY:

            # if we don't have a model
            if not self.terrain_model:

                # note that we're loading
                self.state = PageFindPath.STATE_LOADING_MODEL

                # start new thread to handle loading
                self.load_model_thread = Thread(name="Load Model", target=self.load_terrain_model_threaded)
                self.load_model_thread.start()

            # otherwise (already have model)
            else:

                # unload the model
                self.clear_model()

                # refresh UI and redraw
                self.refresh_ui()
                self.redraw_canvas()

    def refresh_load_model_cell(self, cell: BannerCell):

        btn = cell.widgets["default_btn"]

        # standard configuration
        btn['state'] = tk.DISABLED
        btn['text'] = "Load Model" if not self.terrain_model else "Unload Model"

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
            self.state = PageFindPath.STATE_CACHING_DATA

            # kick off thread to cache costs
            self.cache_costs_thread = Thread(name="Cache Costs", target=self.cache_costs_threaded)
            self.cache_costs_thread.start()

    def cache_obstacles_command(self):

        # if we're not doing anything else
        if self.state == PageFindPath.STATE_READY:

            # list-ify the obstacles and store in pathfinder
            obstacle_map = self.terrain_model.obstacle_mask().tolist()
            self.path_finder.cache_obstacles(obstacle_map)

            # refresh UI
            self.refresh_ui()

    def cache_heuristics_command(self):

        # if we're not doing anything else
        if self.state == PageFindPath.STATE_READY:

            # cache heuristics in pathfinder
            elt = self.terrain_model.getMeshElement(self.end_point)
            heuristics_map = self.cost_function.create_heuristic_cache((elt.x, elt.y)).tolist()
            self.path_finder.cache_heuristics(heuristics_map)

            # refresh UI
            self.refresh_ui()

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

            # enable / disable buttons based on existence of parameters
            costs_btn['state'] = \
                tk.NORMAL if not self.path_finder.costs_cached and self.cost_function else tk.DISABLED
            obstacles_btn['state'] = \
                tk.NORMAL if not self.path_finder.obstacles_cached and self.terrain_model else tk.DISABLED
            heuristics_btn['state'] = \
                tk.NORMAL if not self.path_finder.heuristics_cached and self.end_point else tk.DISABLED

    # set endpoints
    def setup_set_endpoints_cell(self, cell: BannerCell, cell_frame, cell_data):

        start_btn_text = cell_data['start_btn_text']
        end_btn_text = cell_data['end_btn_text']

        # start button
        cell.widgets["start_btn"] = tk.Button(cell_frame, text=start_btn_text, command=self.set_start_command)
        cell.widgets["start_btn"].pack(padx=BannerCell.PAD_X, pady=BannerCell.PAD_Y, side=tk.TOP)

        # end button
        cell.widgets["end_btn"] = tk.Button(cell_frame, text=end_btn_text, command=self.set_end_command)
        cell.widgets["end_btn"].pack(padx=BannerCell.PAD_X, pady=BannerCell.PAD_Y, side=tk.TOP)

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
        end_btn = cell.widgets["end_btn"]

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
            start_btn['state'] = tk.NORMAL if self.terrain_model else tk.DISABLED
            end_btn['state'] = tk.NORMAL if self.terrain_model else tk.DISABLED

    # set obstacles
    def setup_set_obstacle_cell(self, cell: BannerCell, cell_frame, cell_data):

        # add radius slider
        def slider_command(value):
            self.obstacle_radius = int(value)
        radius_slider = tk.Scale(
            cell_frame,
            from_=5,
            to=50,
            orient=tk.HORIZONTAL,
            command=slider_command
        )
        cell.widgets["radius_slider"] = radius_slider
        radius_slider.set(self.obstacle_radius)
        radius_slider.pack(padx=4, pady=4, side=tk.TOP)

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

    def refresh_set_obstacle_cell(self, cell: BannerCell):

        btn = cell.widgets["default_btn"]

        # standard configuration
        btn['state'] = tk.DISABLED
        btn['text'] = "Set Obstacle"

        if self.state == PageFindPath.STATE_SETTING_OBSTACLE:
            btn['state'] = tk.NORMAL
            btn['text'] = "Done Setting"

        # READY
        if self.state == PageFindPath.STATE_READY:

            # enable / disable buttons based on existence of parameters
            btn['state'] = tk.DISABLED if not self.terrain_model else tk.NORMAL

    # find path
    def find_path_command(self):

        # if we're not doing anything else
        if self.state == PageFindPath.STATE_READY:

            # note that we've started the path-finding
            self.state = PageFindPath.STATE_FINDING_PATH

            # kick off thread to find path
            self.find_path_thread = Thread(name="Find Path", target=self.find_path_threaded)
            self.find_path_thread.start()

    def refresh_find_path_cell(self, cell: BannerCell):

        btn = cell.widgets["default_btn"]

        # standard configuration
        btn['state'] = tk.DISABLED

        # READY
        if self.state == PageFindPath.STATE_READY:

            # enable / disable buttons based on existence of parameters
            if self.path_finder.all_cached and self.terrain_model and self.start_point and self.end_point:
                btn['state'] = tk.NORMAL
            else:
                btn['state'] = tk.DISABLED

    '''=======================================
    THREADED FUNCTIONS
    ======================================='''
    def load_terrain_model_threaded(self):

        # get the name of the file of the model to load
        local_path_file_name = path.join(PageFindPath.MODELS_DIRECTORY, self.model_to_load)
        _, extension = path.splitext(local_path_file_name)

        # text file is 'legacy'
        if extension == '.txt':
            grid_mesh = load_legacy(local_path_file_name)

        # otherwise, regular load
        else:
            grid_mesh = GDALMesh(local_path_file_name)

        # load the model, kernel, cost function
        self.terrain_model = grid_mesh.loadSubSection(maxSlope=self.max_slope, cached=True)
        kernel_list = self.terrain_model.searchKernel.getKernel().tolist()
        self.path_finder.set_kernel(kernel_list)
        self.cost_function = ExplorerCost(self.agent, self.terrain_model, 'Energy', cached=False)

        # create the terrain image
        weight = 1.0
        res = self.terrain_model.resolution
        exaggeration = res * weight
        ls = LightSource(azdeg=315, altdeg=45)
        img = ls.hillshade(self.terrain_model.dataset_unmasked, vert_exag=exaggeration, dx=res, dy=res)
        self.model_img = self.sub_plot.imshow(img, cmap='gray')

        # create obstacle image
        self.obstacle_img = self.sub_plot.imshow(self.terrain_model.obstacle_mask(), alpha=0.5, cmap='bwr_r')

        # dispatch loaded event
        EventDispatcher.get_instance().trigger_event(event_definitions.TERRAIN_MODEL_LOADED)

    def cache_costs_threaded(self):

        # should be in caching mode
        assert self.state == PageFindPath.STATE_CACHING_DATA

        # cache costs, list-ify, and store in pathfinder
        cached_costs = self.cost_function.create_costs_cache()
        cost_map = cached_costs["energy"].tolist()
        self.path_finder.cache_costs(cost_map)

        # dispatch caching complete event
        EventDispatcher.get_instance().trigger_event(event_definitions.COSTS_CACHING_COMPLETE)

    def cache_obstacles_threaded(self):

        # should be in caching mode
        assert self.state == PageFindPath.STATE_CACHING_DATA

        # list-ify the obstacles and store in pathfinder
        obstacle_map = self.terrain_model.obstacle_mask().tolist()
        self.path_finder.cache_obstacles(obstacle_map)

        # dispatch caching complete event
        EventDispatcher.get_instance().trigger_event(event_definitions.OBSTACLES_CACHING_COMPLETE)

    def cache_heuristics_threaded(self):

        # should be in caching mode
        assert self.state == PageFindPath.STATE_CACHING_DATA

        # cache heuristics in pathfinder
        elt = self.terrain_model.getMeshElement(self.end_point)
        heuristics_map = self.cost_function.create_heuristic_cache((elt.x, elt.y)).tolist()
        self.path_finder.cache_heuristics(heuristics_map)

        # dispatch caching complete event
        EventDispatcher.get_instance().trigger_event(event_definitions.HEURISTICS_CACHING_COMPLETE)

    def find_path_threaded(self):

        # should be in path finding mode
        assert self.state == PageFindPath.STATE_FINDING_PATH

        # reset any prior progress
        self.path_finder.reset_progress()

        # solve!
        source = self.terrain_model.getMeshElement(self.start_point).mesh_coordinate  # unscaled (row, column)
        target = self.terrain_model.getMeshElement(self.end_point).mesh_coordinate  # unscaled (row, column)
        search_result = self.path_finder.astar_solve(source, target)

        # update line data
        xs = [p[1] for p in search_result]
        ys = [p[0] for p in search_result]
        self.found_path_line.set_data(xs, ys)

        # dispatch path found event
        EventDispatcher.get_instance().trigger_event(event_definitions.PATH_FOUND)

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
    def clear_model(self):

        # unload model, cost function
        self.terrain_model = None
        self.cost_function = None

        # clear out cached data in path finder
        self.path_finder.clear_all()

        # terrain/images
        self.model_img.remove()
        self.obstacle_img.remove()

        # start/end
        self.start_point = None
        self.end_point = None

        # artists
        self.start_point_line.set_data([], [])
        self.end_point_line.set_data([], [])
        self.pending_obstacle_artist.set_alpha(0.0)
        self.found_path_line.set_data([], [])

    def refresh_ui(self):
        # state property will go through UI elements and refresh them
        self.state = self.state