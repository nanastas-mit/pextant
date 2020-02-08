import numpy as np
import pextant.backend_app.ui.fonts as fonts
import pextant.backend_app.events.event_definitions as event_definitions
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from pextant.backend_app.ui.page_base import PageBase
from pextant.backend_app.events.event_dispatcher import EventDispatcher
from threading import Thread

from pextant.EnvironmentalModel import load_legacy
from matplotlib.colors import LightSource
from pextant.lib.geoshapely import GeoPoint, GeoPolygon
from pextant.explorers import Astronaut
from pextant.solvers.astarMesh import astarSolver


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
    STATE_FINDING_PATH = 5

    # by-state text lookup ui objects
    NOTIFICATION_LBL_TEXT = {
        STATE_READY: "...",
        STATE_LOADING_MODEL: "Loading Model...",
        STATE_SETTING_START: "Setting Start...",
        STATE_SETTING_END: "Setting End...",
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

            # FINDING PATH
            elif self.__state == PageFindPath.STATE_FINDING_PATH:
                pass  # everything is standard

            # READY
            else:

                # enable / disable buttons based on existence of parameters
                self.load_model_btn['state'] = tk.DISABLED if self.terrain_model else tk.NORMAL
                self.find_path_btn['state'] = \
                    tk.NORMAL if self.terrain_model and self.start_point and self.end_point \
                    else tk.DISABLED
                self.set_start_btn['state'] = tk.NORMAL if self.terrain_model else tk.DISABLED
                self.set_end_btn['state'] = tk.NORMAL if self.terrain_model else tk.DISABLED

    '''=======================================
    STARTUP/SHUTDOWN
    ======================================='''
    def __init__(self, master):

        super().__init__(master, {
            event_definitions.TERRAIN_MODEL_LOADED: self.on_terrain_model_loaded,
            event_definitions.PATH_FOUND: self.on_path_found
        })

        # ui references
        self.ui_initialized = False
        self.notification_lbl = None
        self.load_model_btn = None
        self.set_start_btn = None
        self.set_end_btn = None
        self.find_path_btn = None

        # graph references
        self.canvas = None
        self.figure = None
        self.sub_plot = None
        self.start_point_line = None
        self.end_point_line = None
        self.search_path_line = None
        self.on_click_id = None

        # path planning references
        self.start_point = None
        self.end_point = None
        self.terrain_model = None

        # thread references
        self.load_model_thread = None
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
        self.load_model_btn = tk.Button(btn_frame, text="Load Model", command=self.load_model)
        self.load_model_btn.grid(column=1, row=1, padx=4, pady=4)
        self.set_start_btn = tk.Button(btn_frame, text="Set Start", command=self.set_start)
        self.set_start_btn.grid(column=2, row=1, padx=4, pady=4)
        self.set_end_btn = tk.Button(btn_frame, text="Set End", command=self.set_end)
        self.set_end_btn.grid(column=3, row=1, padx=4, pady=4)
        self.find_path_btn = tk.Button(btn_frame, text="Start Search", command=self.find_path)
        self.find_path_btn.grid(column=4, row=1, padx=4, pady=4)

        # create the figure, setup axes
        self.figure = Figure(figsize=(4, 4), dpi=100)
        self.sub_plot: Axes = self.figure.add_subplot()

        # setup lines
        self.start_point_line = Line2D([], [], linestyle='None', marker='*', color='g', markeredgecolor='k', markersize=10)
        self.end_point_line = Line2D([], [], linestyle='None', marker='X', color='r', markeredgecolor='k', markersize=10)
        self.search_path_line = Line2D([], [], color='b')
        self.sub_plot.add_line(self.start_point_line)
        self.sub_plot.add_line(self.end_point_line)
        self.sub_plot.add_line(self.search_path_line)

        # create rendering object
        self.canvas = FigureCanvasTkAgg(self.figure, self)
        self.canvas.draw()
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
        if self.find_path_thread:
            self.find_path_thread.join()

    '''=======================================
    UPDATES
    ======================================='''
    def page_update(self, delta_time):
        # super
        super().page_update(delta_time)

        self.dude = 1

        # redraw
        # self.canvas.draw()

    '''=======================================
    EVENT HANDLERS
    ======================================='''
    def on_click(self, event):

        # if we clicked somewhere in the graph area
        if event.xdata and event.ydata:

            # if setting  start...
            if self.state == PageFindPath.STATE_SETTING_START:

                # set point
                self.start_point = GeoPoint(self.terrain_model.COL_ROW, event.xdata, event.ydata)

                # set line (i.e. draw point)
                converted_point = self.start_point.to(self.terrain_model.COL_ROW)
                self.start_point_line.set_data([converted_point[0]], [converted_point[1]])
                self.canvas.draw()

                # we're done!
                self.state = PageFindPath.STATE_READY

            elif self.state == PageFindPath.STATE_SETTING_END:

                # set point
                self.end_point = GeoPoint(self.terrain_model.COL_ROW, event.xdata, event.ydata)

                # set line (i.e. draw point)
                converted_point = self.end_point.to(self.terrain_model.COL_ROW)
                self.end_point_line.set_data([converted_point[0]], [converted_point[1]])
                self.canvas.draw()

                # we're done!
                self.state = PageFindPath.STATE_READY

    def on_terrain_model_loaded(self):

        # should be coming from loading the model
        assert self.state == PageFindPath.STATE_LOADING_MODEL

        # redraw and note that we're done loading
        self.load_model_thread = None
        self.state = PageFindPath.STATE_READY
        self.canvas.draw()

    def on_path_found(self):

        # should be coming from finding path
        assert self.state == PageFindPath.STATE_FINDING_PATH

        # redraw and note that we're done path-finding
        self.find_path_thread = None
        self.state = PageFindPath.STATE_READY
        self.canvas.draw()

    '''=======================================
    PATH CREATION
    ======================================='''
    def load_model(self):

        # if we're not doing anything else
        if self.state == PageFindPath.STATE_READY:

            # note that we're loading
            self.state = PageFindPath.STATE_LOADING_MODEL

            # start new thread to handle loading
            self.load_model_thread = Thread(name="Load Model", target=self.load_model_run)
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

    def find_path(self):

        # if we're not doing anything else
        if self.state == PageFindPath.STATE_READY:

            # note that we've started the path-finding
            self.state = PageFindPath.STATE_FINDING_PATH

            # kick off thread to find path
            self.find_path_thread = Thread(name="Find Path", target=self.find_path_run)
            self.find_path_thread.start()

    '''=======================================
    THREADS
    ======================================='''
    def load_model_run(self):

        # create the model
        apollo14_grid_mesh = load_legacy("../notebooks/Documentation/Apollo14.txt")
        self.terrain_model = apollo14_grid_mesh.loadSubSection(maxSlope=10, cached=True)

        # create the image
        weight = 1.0
        res = self.terrain_model.resolution
        exaggeration = res * weight
        ls = LightSource(azdeg=315, altdeg=45)
        img = ls.hillshade(self.terrain_model.dataset_unmasked,
                           vert_exag=exaggeration, dx=res, dy=res)
        self.sub_plot.imshow(img, cmap='gray')

        # dispatch loaded event
        EventDispatcher.get_instance().trigger_event(event_definitions.TERRAIN_MODEL_LOADED)

    def find_path_run(self):

        # create the agent
        agent = Astronaut(80)

        # define list of waypoints (just 2 here - start and end)
        waypoints = GeoPolygon([self.start_point, self.end_point])

        # create the solver
        solver = astarSolver(self.terrain_model, agent, algorithm_type=astarSolver.AlgorithmType.CPP_NETWORKX)

        # TODO: split out set waypoints and solve, allow for cacheing of heuristicsHan
        out, _, _ = solver.solvemultipoint(waypoints)
        self.search_path_line.set_data(*out.coordinates().to(self.terrain_model.COL_ROW))

        # dispatch path found event
        EventDispatcher.get_instance().trigger_event(event_definitions.PATH_FOUND)
