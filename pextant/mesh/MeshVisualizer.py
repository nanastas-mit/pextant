from bokeh.io import push_notebook, show, output_notebook
import matplotlib.pyplot as plt
import numpy as np
from bokeh.io import push_notebook, show, output_notebook
from bokeh.plotting import figure

from pextant.lib.geoshapely import GeoPolygon

class TriExpandViz(object):
    def __init__(self, env_model, start_point, end_point, counter_interval=10):
        self.mesh = env_model.dataset.mesh
        self.env_model = env_model
        #self.points = GeoPolygon([start_point, end_point])
        self.y, self.x = self.mesh.vertices[:, :2].transpose()
        self.zfaces = self.mesh.triangles_center[:, 2]
        self.counter = 0
        self.counter_interval = counter_interval

    def draw(self, x = (), y=()):
        #px,py = self.points.to(self.env_model.ROW_COL)
        plt.tripcolor(self.x, self.y, self.mesh.faces, facecolors=self.zfaces, edgecolors='k')
        if len(x) != 0:
            plt.plot(x, y)
        plt.axis('equal')
        plt.show()

    def addcount(self):
        self.counter += 1

        if self.counter % self.counter_interval == 0:
            print(self.counter)

        if self.counter % self.counter_interval == 0:
            self.draw()

    def add(self, state, cost):
        self.zfaces[state] = cost

class ExpandViz(object):
    def __init__(self, env_model, counter_interval=1000):
        self.env_model = env_model
        self.expandedgrid = np.zeros((env_model.y_size, env_model.x_size))
        self.counter = 0
        self.counter_interval = counter_interval
        self.expanded = []

    #cmap = 'viridis'
    def draw(self):
        expanded = np.array(self.expanded).transpose()
        gp_expanded = GeoPolygon(self.env_model.ROW_COL,*expanded)
        upper_left, lower_right = gp_expanded.geoEnvelope()
        upper_row, left_col = upper_left.to(self.env_model.ROW_COL)
        lower_row, right_col = lower_right.to(self.env_model.ROW_COL)
        plt.matshow(self.expandedgrid[upper_row:lower_row+1,left_col:right_col+1])
        print(((upper_row, lower_row), (left_col,right_col)))
        #print(waypoints.to(env_model.COL_ROW))
        #plt.scatter(*waypoints.to(env_model.COL_ROW), c='r')
        plt.show()

    def drawsolution(self, rawpoints):
        np_rawpoints = GeoPolygon(self.env_model.ROW_COL, *np.array(rawpoints).transpose())
        plt.matshow(self.env_model.dataset)
        #plt.scatter(*waypoints.to(env_model.COL_ROW), c='r')
        plt.scatter(*np_rawpoints.to(self.env_model.COL_ROW), c='b')
        plt.show()

    def addcount(self):
        self.counter += 1

        if self.counter % 1000 == 0:
            print(self.counter)

        if self.counter % self.counter_interval == 0:
            self.draw()

    def add(self, state, cost):
        self.expanded.append(np.array(state))
        self.expandedgrid[state] = cost

class MeshViz:
    def __init__(self, notebook=False):
        self.notebook = notebook
        if notebook:
            output_notebook()

    def viz(self, mesh, x=None, y=None, palette="Spectral11", viz=True, type="line"):
        dh, dw = mesh.shape
        size = max(dh, dw)
        self.mesh = mesh
        self.dh = dh
        self.dw = dw
        self.p = figure(webgl=True, title="MD2", x_axis_label='x', y_axis_label='y', x_range=[0, size], y_range=[0, size])
        self.p.image(image=[mesh[::-1, :]], x=0, y=0, dw=dw, dh=dh, palette=palette)
        if not x is None:
            if type=="line":
                self.p.line(x, self.dh - np.array(y), line_color="green", line_width=3)
            else:
                self.p.circle(x, self.dh - np.array(y), fill_color="yellow", line_color="black", size=10)
        if self.notebook and viz:
            self.t = show(self.p, notebook_handle = self.notebook)
        else:
            #self.t = show(self.p)
            pass

    def show(self):
        self.t = show(self.p, notebook_handle = self.notebook)

    def vizpoints(self, x, y):
        print(x)
        self.p.circle(y, self.dh - np.array(x), fill_color="yellow", size=10)
        push_notebook(handle=self.t)

class MeshVizM:
    def __init__(self):
        pass

    def viz(self, mesh, x=None, y=None):
        plt.matshow(mesh)
        plt.show()


if __name__ == '__main__':
    MeshViz().viz(np.zeros([4,4]))