import numpy as np
import pextant.backend_app.ui.fonts as fonts
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from pextant.backend_app.ui.page_base import PageBase


class PageAnimationTest(PageBase):

    def __init__(self, master):

        super().__init__(master, {})

        # UI setup
        # title
        label = tk.Label(self, text="PATH FINDING", font=fonts.LARGE_FONT)
        label.pack(pady=10, padx=10)

        # button
        self.do_animation = False
        toggle_anim_btn = tk.Button(self, text="Toggle Animation", command=self.toggle_anim)
        toggle_anim_btn.pack(pady=10, padx=10)

        self.elapsed_time = 0
        self.cached_bg = None

        # create figure and subplot
        self.figure = Figure(figsize=(5, 5), dpi=64)
        self.sub_plot: Axes = self.figure.add_subplot()
        self.sub_plot.set_xlim(0, 2*np.pi)
        self.sub_plot.set_ylim(-1, 1)

        # create rendering object
        self.canvas = FigureCanvasTkAgg(self.figure, self)
        self.redraw_canvas()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # add toolbar
        toolbar = NavigationToolbar2Tk(self.canvas, self)
        toolbar.update()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # add sine wave background
        t = np.arange(0.0, 2*np.pi, 0.001)
        s = np.sin(t)
        sin_line = Line2D(t, s)
        self.sub_plot.add_line(sin_line)
        self.cached_bg = self.canvas.copy_from_bbox(self.sub_plot.bbox)

        # add red dot
        self.red_dot = Line2D([0], [np.sin(0)], marker='o', color='r', alpha=1.0, markersize=10)
        self.sub_plot.add_line(self.red_dot)

    def page_update(self, delta_time):

        # super
        super().page_update(delta_time)

        if self.do_animation:
            # update red dot's data
            self.elapsed_time += delta_time
            if self.elapsed_time > 2*np.pi:
                self.elapsed_time -= 2*np.pi
            self.red_dot.set_data(self.elapsed_time, np.sin(self.elapsed_time))

            # redraw
            self.redraw_canvas()

    def toggle_anim(self):
        self.do_animation = not self.do_animation

    def redraw_canvas(self, blit=False):

        if blit and self.cached_bg:

            # restore background
            self.canvas.restore_region(self.cached_bg)

            # redraw lines
            self.sub_plot.draw_artist(self.red_dot)

            # fill in the axes rectangle
            self.canvas.blit(self.sub_plot.bbox)

        else:

            # just redraw everything
            self.canvas.draw()
