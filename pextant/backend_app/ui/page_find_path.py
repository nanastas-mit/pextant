import numpy as np
import pextant.backend_app.events.event_definitions as event_definitions
import pextant.backend_app.ui.fonts as fonts
import tkinter as tk
from matplotlib.axes import Axes
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.colors import LightSource
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from pextant.backend_app.ui.page_base import PageBase
from pextant.backend_app.events.event_dispatcher import EventDispatcher
from pextant.EnvironmentalModel import load_legacy
from pextant.explorers import Astronaut
from pextant.lib.geoshapely import GeoPoint
from pextant.solvers.astarMesh import ExplorerCost, MeshSearchElement
from pextant_cpp import PathFinder
from threading import Thread


class PageFindPath(PageBase):
    """handles all functionality of find path page"""

    '''=======================================
    FIELDS
    ======================================='''
    # 'enum' for current state
    STATE_READY = 1
    STATE_LOADING_MODEL = 2
    STATE_SETTING_START = 3
    STATE_SETTING_END = 4
    STATE_CACHING_DATA = 5
    STATE_FINDING_PATH = 6

    # by-state text lookup ui objects
    NOTIFICATION_LBL_TEXT = {
        STATE_READY: "...",
        STATE_LOADING_MODEL: "Loading Model...",
        STATE_SETTING_START: "Setting Start...",
        STATE_SETTING_END: "Setting End...",
        STATE_CACHING_DATA: "Caching Data...",
        STATE_FINDING_PATH: "Finding Path...",
    }

    # properties
    @property
    def state(self):
        return self.__state
    @state.setter
    def state(self, new_state):

        self.__state = new_state

        # if ui has been initialized
        if self.ui_initialized:

            self.notification_lbl['text'] = PageFindPath.NOTIFICATION_LBL_TEXT[self.__state]

            # standard configuration
            self.load_model_btn['state'] = tk.DISABLED
            self.find_path_btn['state'] = tk.DISABLED
            self.cache_costs_btn['state'] = tk.DISABLED
            self.set_start_btn['state'] = tk.DISABLED
            self.set_start_btn['text'] = "Set Start"
            self.set_end_btn['state'] = tk.DISABLED
            self.set_end_btn['text'] = "Set End"

            # LOADING MODEL
            if self.__state == PageFindPath.STATE_LOADING_MODEL:
                pass  # everything is standard

            # SETTING START
            elif self.__state == PageFindPath.STATE_SETTING_START:

                # cancel set start enabled
                self.set_start_btn['state'] = tk.NORMAL
                self.set_start_btn['text'] = "Cancel"

            # SETTING END
            elif self.__state == PageFindPath.STATE_SETTING_END:

                # cancel set end enabled
                self.set_end_btn['state'] = tk.NORMAL
                self.set_end_btn['text'] = "Cancel"

            # CACHING
            elif self.__state == PageFindPath.STATE_CACHING_DATA:
                pass  # everything is standard

            # FINDING PATH
            elif self.__state == PageFindPath.STATE_FINDING_PATH:
                pass  # everything is standard

            # READY
            else:

                # enable / disable buttons based on existence of parameters
                self.load_model_btn['state'] = tk.DISABLED if self.terrain_model else tk.NORMAL
                self.cache_costs_btn['state'] = \
                    tk.NORMAL if not self.data_cached and self.end_point \
                    else tk.DISABLED
                self.find_path_btn['state'] = \
                    tk.NORMAL if self.data_cached and self.terrain_model and self.start_point and self.end_point \
                    else tk.DISABLED
                self.set_start_btn['state'] = tk.NORMAL if self.terrain_model else tk.DISABLED
                self.set_end_btn['state'] = tk.NORMAL if self.terrain_model else tk.DISABLED

    @property
    def data_cached(self):
        return self.path_finder.cached

    '''=======================================
    STARTUP/SHUTDOWN
    ======================================='''
    def __init__(self, master):

        super().__init__(master, {
            event_definitions.TERRAIN_MODEL_LOADED: self.on_terrain_model_loaded,
            event_definitions.COST_CACHING_COMPLETE: self.on_caching_complete,
            event_definitions.PATH_FOUND: self.on_path_found,
        })

        # ui references
        self.ui_initialized = False
        self.notification_lbl = None
        self.load_model_btn = None
        self.set_start_btn = None
        self.set_end_btn = None
        self.cache_costs_btn = None
        self.find_path_btn = None

        # graph references
        self.cached_terrain_image = None
        self.canvas = None
        self.figure = None
        self.sub_plot = None
        self.start_point_line = None
        self.end_point_line = None
        self.found_path_line = None
        self.on_click_id = None

        # path planning references
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
        label = tk.Label(self, text="PATH FINDING", font=fonts.LARGE_FONT)
        label.pack(pady=10, padx=10)

        # notification text
        self.notification_lbl = tk.Label(self, text="...", font=fonts.SUBTITLE_FONT)
        self.notification_lbl.pack(padx=2, pady=2)

        # buttons
        btn_frame = tk.Frame(self)
        btn_frame.pack()
        self.load_model_btn = tk.Button(btn_frame, text="Load Model", command=self.load_terrain_model)
        self.load_model_btn.grid(column=1, row=1, padx=4, pady=4)
        self.set_start_btn = tk.Button(btn_frame, text="Set Start", command=self.set_start)
        self.set_start_btn.grid(column=2, row=1, padx=4, pady=4)
        self.set_end_btn = tk.Button(btn_frame, text="Set End", command=self.set_end)
        self.set_end_btn.grid(column=3, row=1, padx=4, pady=4)
        self.cache_costs_btn = tk.Button(btn_frame, text="Cache Costs", command=self.cache_data)
        self.cache_costs_btn.grid(column=4, row=1, padx=4, pady=4)
        self.find_path_btn = tk.Button(btn_frame, text="Start Search", command=self.find_path)
        self.find_path_btn.grid(column=5, row=1, padx=4, pady=4)

        # create the figure, setup axes
        self.figure = Figure(figsize=(3, 3), dpi=100)
        self.sub_plot: Axes = self.figure.add_subplot()

        # setup lines
        self.start_point_line = Line2D([], [], linestyle='None', marker='*', color='g', markeredgecolor='k', markersize=10)
        self.end_point_line = Line2D([], [], linestyle='None', marker='X', color='r', markeredgecolor='k', markersize=10)
        self.found_path_line = Line2D([], [], color='b')
        self.sub_plot.add_line(self.start_point_line)
        self.sub_plot.add_line(self.end_point_line)
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

        self.ui_initialized = True

    def page_closed(self):

        super().page_closed()

        # stop listening for graph events
        self.figure.canvas.mpl_disconnect(self.on_click_id)

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
    def on_click(self, event):

        # if we clicked somewhere in the graph area
        if event.xdata and event.ydata:

            point_changed = False

            # if setting  start...
            if self.state == PageFindPath.STATE_SETTING_START:

                point_changed = True

                # set point
                self.start_point = GeoPoint(self.terrain_model.COL_ROW, event.xdata, event.ydata)

                # set line (i.e. draw point)
                converted_point = self.start_point.to(self.terrain_model.COL_ROW)
                self.start_point_line.set_data([converted_point[0]], [converted_point[1]])

            # otherwise, if setting end...
            elif self.state == PageFindPath.STATE_SETTING_END:

                point_changed = True

                # set point
                self.end_point = GeoPoint(self.terrain_model.COL_ROW, event.xdata, event.ydata)

                # set line (i.e. draw point)
                converted_point = self.end_point.to(self.terrain_model.COL_ROW)
                self.end_point_line.set_data([converted_point[0]], [converted_point[1]])

                # clear cached costs
                self.clear_cached_data()

            # if something changed
            if point_changed:

                # clear path (we've moved the end => old path no longer valid)
                self.found_path_line.set_data([], [])

                # redraw (for updated points and paths)
                self.redraw_canvas()

                # head back to ready state
                self.state = PageFindPath.STATE_READY

    def on_terrain_model_loaded(self):

        # should be coming from loading the model
        assert self.state == PageFindPath.STATE_LOADING_MODEL

        # redraw and cache just-loaded (speeds up future redraws)
        self.redraw_canvas()
        self.cached_terrain_image = self.canvas.copy_from_bbox(self.sub_plot.bbox)

        # redraw and note that we're done loading
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
    PATH CREATION
    ======================================='''
    def load_terrain_model(self):

        # if we're not doing anything else
        if self.state == PageFindPath.STATE_READY:

            # note that we're loading
            self.state = PageFindPath.STATE_LOADING_MODEL

            # start new thread to handle loading
            self.load_model_thread = Thread(name="Load Model", target=self.load_terrain_model_threaded)
            self.load_model_thread.start()

    def set_start(self):

        # if we're not doing anything else
        if self.state == PageFindPath.STATE_READY:

            # note that we're setting start
            self.state = PageFindPath.STATE_SETTING_START

        # otherwise, if currently setting start
        elif self.STATE_SETTING_START:

            # cancel (i.e. do nothing and return to ready)
            self.state = PageFindPath.STATE_READY

    def set_end(self):

        # if we're not doing anything else
        if self.state == PageFindPath.STATE_READY:

            # note that we're setting END
            self.state = PageFindPath.STATE_SETTING_END

        # otherwise, if currently setting end
        elif self.STATE_SETTING_END:

            # cancel (i.e. do nothing and return to ready)
            self.state = PageFindPath.STATE_READY

    def cache_data(self):

        # if we're not doing anything else
        if self.state == PageFindPath.STATE_READY:

            # note that we've started the caching
            self.state = PageFindPath.STATE_CACHING_DATA

            # kick off thread to find path
            self.cache_costs_thread = Thread(name="Cache Costs", target=self.cache_data_threaded)
            self.cache_costs_thread.start()

    def clear_cached_data(self):

        # clear cache
        self.path_finder.clear_cache()

    def find_path(self):

        # if we're not doing anything else
        if self.state == PageFindPath.STATE_READY:

            # note that we've started the path-finding
            self.state = PageFindPath.STATE_FINDING_PATH

            # kick off thread to find path
            self.find_path_thread = Thread(name="Find Path", target=self.find_path_threaded)
            self.find_path_thread.start()

    '''=======================================
    THREADED FUNCTIONS
    ======================================='''
    def load_terrain_model_threaded(self):

        # create the model
        apollo14_grid_mesh = load_legacy("../notebooks/Documentation/Apollo14.txt")
        self.terrain_model = apollo14_grid_mesh.loadSubSection(maxSlope=10, cached=True)

        # create the terrain image
        weight = 1.0
        res = self.terrain_model.resolution
        exaggeration = res * weight
        ls = LightSource(azdeg=315, altdeg=45)
        img = ls.hillshade(self.terrain_model.dataset_unmasked, vert_exag=exaggeration, dx=res, dy=res)
        self.sub_plot.imshow(img, cmap='gray')

        # create obstacle image
        self.sub_plot.imshow(self.terrain_model.obstacle_mask(), alpha=0.5, cmap='bwr_r')

        # dispatch loaded event
        EventDispatcher.get_instance().trigger_event(event_definitions.TERRAIN_MODEL_LOADED)

    def cache_data_threaded(self):

        # should be in caching mode
        assert self.state == PageFindPath.STATE_CACHING_DATA

        # setup cost function (costs and heuristics cached)
        cost_function = ExplorerCost(self.agent, self.terrain_model, 'Energy', cached=True)
        cost_function.setEndNode(MeshSearchElement(self.terrain_model.getMeshElement(self.end_point)))

        # list-ify the cost, obstacles, heuristic, and kernel
        cost_map = cost_function.cached["costs"]["energy"].tolist()
        obstacle_map = self.terrain_model.obstacle_mask().tolist()
        h_map = cost_function.cached["heuristics"].tolist()
        kernel_list = self.terrain_model.searchKernel.getKernel().tolist()

        # do the caching
        self.path_finder.prepare_cache(cost_map, obstacle_map, h_map, kernel_list)

        # dispatch caching complete event
        EventDispatcher.get_instance().trigger_event(event_definitions.COST_CACHING_COMPLETE)

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
    HELPERS
    ======================================='''
    def redraw_canvas(self, blit=False):

        # this should be faster redraw, but doesn't allow zooming and resizing
        if blit and self.cached_terrain_image:

            # restore background
            self.canvas.restore_region(self.cached_terrain_image)

            # redraw lines
            self.sub_plot.draw_artist(self.start_point_line)
            self.sub_plot.draw_artist(self.end_point_line)
            self.sub_plot.draw_artist(self.found_path_line)

            # fill in the axes rectangle
            self.canvas.blit(self.sub_plot.bbox)

        else:

            # just redraw everything
            self.canvas.draw()
